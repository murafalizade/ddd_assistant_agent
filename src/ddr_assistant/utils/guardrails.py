import re
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class GuardrailManager:
    def __init__(self):
        self.injection_patterns = [
            r"ignore all previous instructions",
            r"system prompt",
            r"you are now",
            r"forget everything",
            r"new rules",
            r"bypass",
            r"jailbreak"
        ]
        
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "phone": r"\+?\d{1,3}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}"
        }

    def validate_input(self, text: str) -> Tuple[bool, str]:
        for pattern in self.injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected: {pattern}")
                return False, "I cannot process this request as it violates safety guidelines."

        if len(text) > 4000:
            return False, "Input is too long. Please shorten your request."

        return True, text

    def validate_output(self, text: str) -> Tuple[bool, str]:
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                logger.warning(f"Potential {pii_type} detected in output.")

        return True, text

    def mask_pii(self, text: str) -> str:
        for pii_type, pattern in self.pii_patterns.items():
            text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text)
        return text
