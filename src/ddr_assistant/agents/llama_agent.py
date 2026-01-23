import os
import io
import base64
from PIL import Image
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from ddr_assistant.prompts.chat_prompts import SYSTEM_PROMPT, IMAGE_ANALYSIS_PROMPT
from ddr_assistant.tools.db_tools import query_drilling_db, get_db_schema
from ddr_assistant.utils.guardrails import GuardrailManager

class LlamaAgent:
    def __init__(self):
        self.vlm = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            groq_api_key=os.environ["GROQ_API_KEY"],
            temperature=0.3,
        )
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            groq_api_key=os.environ["GROQ_API_KEY"],
            temperature=0.1
        )
        self.tools = {
            "query_drilling_db": query_drilling_db,
            "get_db_schema": get_db_schema,
        }
        self.llm_with_tools = self.llm.bind_tools(list(self.tools.values()))
        self.messages = []
        self.guardrails = GuardrailManager()
        
        if "LANGCHAIN_PROJECT" not in os.environ:
            os.environ["LANGCHAIN_PROJECT"] = "ddr-assistant"

    def _image_to_base64(self, image: Image.Image) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def add_message(self, role: str, content: str, image: Image.Image = None):
        msg = {"role": role, "content": content}
        if image:
            msg["image"] = image
        self.messages.append(msg)

    def clear_history(self):
        self.messages = []

    def analyze_image(self, image: Image.Image, user_prompt: str = "") -> str:
        try:
            if user_prompt:
                is_safe, message = self.guardrails.validate_input(user_prompt)
                if not is_safe:
                    return message

            img_base64 = self._image_to_base64(image)
            prompt = user_prompt if user_prompt else IMAGE_ANALYSIS_PROMPT
            messages = [HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
            ])]
            response = self.vlm.invoke(messages).content
            
            _, safe_response = self.guardrails.validate_output(response)
            return safe_response
        except Exception as e:
            return f"Error: {e}"

    def chat(self, user_message: str) -> str:
        is_safe, validation_msg = self.guardrails.validate_input(user_message)
        if not is_safe:
            return validation_msg

        self.add_message("user", user_message)
        
        try:
            history_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in self.messages[:-1]])
            history_snippet = history_text[-1000:] if len(history_text) > 1000 else history_text
            
            full_system_prompt = f"{SYSTEM_PROMPT}\n\n[Recent History Context]\n...{history_snippet}"
            active_messages = [SystemMessage(content=full_system_prompt), HumanMessage(content=user_message)]

            for _ in range(5):
                response = self.llm_with_tools.invoke(active_messages)
                active_messages.append(response)

                if not response.tool_calls:
                    final_content = response.content
                    break

                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    if tool_name not in self.tools:
                        tool_result = f"Error: Tool {tool_name} not found."
                    else:
                        tool_func = self.tools[tool_name]
                        tool_result = tool_func.invoke(tool_call["args"])
                    active_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))
            else:
                final_content = "Tool execution limit reached."
            
            if not final_content:
                final_content = "I'm sorry, I couldn't generate a response."

            _, safe_final_content = self.guardrails.validate_output(final_content)
            
            self.add_message("assistant", safe_final_content)
            return safe_final_content

        except Exception as e:
            error_msg = f"Error: {e}"
            self.add_message("assistant", error_msg)
            return error_msg