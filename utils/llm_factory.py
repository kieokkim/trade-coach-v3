import logging
import os

from langchain.chat_models import init_chat_model

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.3):
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "groq":
        return init_chat_model(
            "groq:llama-3.1-8b-instant",
            temperature=temperature,
        )
    elif provider == "openai":
        return init_chat_model(
            "openai:gpt-4o-mini",
            temperature=temperature,
        )
    else:
        logger.warning("Unknown LLM_PROVIDER=%s, falling back to openai", provider)
        return init_chat_model("openai:gpt-4o-mini", temperature=temperature)
