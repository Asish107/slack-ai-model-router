import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    base_url: str = "https://openrouter.ai/api/v1"
    app_name: str = os.getenv("OPENROUTER_APP_NAME", "Slack AI Model Router")
    fast_model: str = os.getenv("FAST_MODEL", "~google/gemini-flash-latest")
    mid_model: str = os.getenv("MID_MODEL", "openai/gpt-5.6-terra")
    frontier_model: str = os.getenv("FRONTIER_MODEL", "~openai/gpt-latest")
    creative_model: str = os.getenv(
        "CREATIVE_MODEL", "anthropic/claude-sonnet-4.6"
    )
    timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "12"))
