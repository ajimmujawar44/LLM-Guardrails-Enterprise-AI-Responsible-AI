
import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL =  os.getenv("GEMINI_MODEL", "gemini-3.6-flash")  # Default to gemini-3.5-flash if not set

# Validate API key
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Please add it to your .env file."
    )

