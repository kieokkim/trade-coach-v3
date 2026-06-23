import logging
import os

logger = logging.getLogger(__name__)

_langfuse_client = None
_enabled = False


def get_langfuse():
    global _langfuse_client, _enabled
    if _langfuse_client is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        if not public_key or not secret_key:
            logger.info("Langfuse 키 없음 — observability 비활성화")
            _enabled = False
            return None
        try:
            from langfuse import Langfuse
            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            _enabled = True
        except Exception as e:
            logger.warning("Langfuse 초기화 실패: %s", e)
            _enabled = False
            return None
    return _langfuse_client


def trace_llm_call(
    node_name: str,
    input_text: str,
    output_text: str,
    model: str,
    elapsed: float,
    session_id: str = "default",
):
    client = get_langfuse()
    if not client:
        return
    try:
        trace = client.trace(name=node_name, session_id=session_id)
        trace.generation(
            name=f"{node_name}_llm",
            model=model,
            input=input_text[:2000],
            output=output_text[:2000],
            metadata={"elapsed_seconds": round(elapsed, 3)},
        )
    except Exception as e:
        logger.warning("Langfuse trace 실패: %s", e)
