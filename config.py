import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower().strip()

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Google Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Groq Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "Ты — вежливый, умный и полезный ассистент в Telegram. Ты отвечаешь четко, понятно и доброжелательно на любые вопросы."
).strip()

try:
    MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
except ValueError:
    MAX_HISTORY_MESSAGES = 10
