import os

from dotenv import load_dotenv


load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()


OWNER_TELEGRAM_ID = int(
    os.getenv(
        "OWNER_TELEGRAM_ID",
        "0"
    )
)


LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    ""
).strip()


LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://api.groq.com/openai/v1"
).strip()


LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama-3.1-8b-instant"
).strip()


DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "sovereign.db"
).strip()