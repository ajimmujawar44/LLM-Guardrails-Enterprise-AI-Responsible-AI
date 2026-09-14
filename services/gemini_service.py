"""
Gemini Service
--------------
This module handles communication with Google Gemini.

Responsibilities:
1. Load Gemini API configuration
2. Create Gemini client
3. Send user prompts to Gemini
4. Return Gemini's text response

Guardrails should be handled separately in:
- guardrails.py
- output_guardrails.py
"""

from google import genai
from config import GEMINI_API_KEY


# ============================================================
# Gemini Client
# ============================================================

client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# Gemini Model
# ============================================================

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# Generate Response
# ============================================================

def generate_response(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the generated response.

    Parameters
    ----------
    prompt : str
        User's input prompt.

    Returns
    -------
    str
        Gemini generated response.
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        if response.text:
            return response.text.strip()

        return "Gemini returned an empty response."

    except Exception as e:
        return f"Gemini API error: {str(e)}"