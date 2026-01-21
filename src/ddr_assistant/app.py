import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

from ddr_assistant.utils.db_manager import DatabaseManager
from ddr_assistant.utils.batch_processor import BatchProcessor
from ddr_assistant.agents.llama_agent import LlamaAgent

load_dotenv()

st.set_page_config(
    page_title="DDR Assistant Chat",
    page_icon="🤖",
    layout="wide",
)

DATA_DIR = Path("data/PDF_version_1000")

if "agent" not in st.session_state:
    st.session_state.agent = LlamaAgent()

if "initialized" not in st.session_state:
    st.session_state.initialized = False

if "pending_image" not in st.session_state:
    st.session_state.pending_image = None

db_manager = DatabaseManager()
batch_processor = BatchProcessor(DATA_DIR, db_manager)
agent = st.session_state.agent

def initialize_data():
    if st.session_state.initialized:
        return

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, filename):
        status_text.text(f"Processing: {filename}")
        progress_bar.progress((current + 1) / total)

    status, message = batch_processor.initialize_data(update_progress)
    
    status_text.empty()
    progress_bar.empty()
    
    if status == "error": st.error(message)
    elif status == "warning": st.warning(message)
    elif status == "info": st.info(message)
    elif status == "success": st.success(message)
    
    st.session_state.initialized = True

with st.sidebar:
    st.title("⚙️ Settings")

    if not os.environ.get("GROQ_API_KEY"):
        st.error("⚠️ GROQ_API_KEY not found!")
    else:
        st.success("✅ API Key loaded")

    st.divider()
    st.markdown("### 📊 Database Status")
    # initialize_data()
    # st.rerun()

    st.divider()
    st.markdown("### 📷 Image Analysis")
    uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Preview", use_container_width=True)
        st.session_state.pending_image = image

        if st.button("🔍 Analyze Image", type="primary", use_container_width=True):
            with st.spinner("Analyzing..."):
                analysis = agent.analyze_image(image)
                agent.add_message("user", f"[Image: {uploaded_file.name}]", image)
                agent.add_message("assistant", f"**📸 Analysis:**\n\n{analysis}")
                st.session_state.pending_image = None
                st.rerun()

    st.divider()
    if st.button("Show Database Schema"):
        schema_info = """
**Available Tables:**
1. **report_metadata**: report_id, operator, rig_name, wellbore_name, report_period, summary_activities, file_name, etc.
2. **operations**: report_id, activity, state, remark
3. **drilling_fluid**: report_id, parameter, value
4. **gas_readings**: report_id, depth, gas components
"""
        agent.add_message("assistant", schema_info)
        st.rerun()

    if st.button("🗑️ Clear Chat History"):
        agent.clear_history()
        st.rerun()

st.title("💬 DDR Assistant Chat")

for message in agent.messages:
    with st.chat_message(message["role"]):
        if "image" in message:
            st.image(message["image"], use_container_width=True)
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question..."):
    if st.session_state.pending_image:
        with st.chat_message("user"):
            st.image(st.session_state.pending_image, use_container_width=True)
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                analysis = agent.analyze_image(st.session_state.pending_image, prompt)
                st.markdown(f"**📸 Analysis:**\n\n{analysis}")

        agent.add_message("user", prompt, st.session_state.pending_image)
        agent.add_message("assistant", f"**📸 Analysis:**\n\n{analysis}")
        st.session_state.pending_image = None
        st.rerun()
    else:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent.chat(prompt)
                st.markdown(response)
        
        st.rerun()