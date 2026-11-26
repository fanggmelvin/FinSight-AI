"""Configuration shared by the application and its OpenAI client."""
import os
from pathlib import Path

from dotenv import load_dotenv


def load_local_config():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


def live_ai_available():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return os.getenv("FINSIGHT_LIVE_AI", "0") == "1" and bool(key) and key != "your_openai_api_key_here"


def dataset_ai_available(*, demo=False):
    return live_ai_available() and (demo or os.getenv("FINSIGHT_AI_UPLOADS", "0") == "1")
