import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from market.bybit_client import BybitClient
from market.upbit_client import UpbitClient

logger = logging.getLogger(__name__)

SAMPLE_FILE_MAP = {
    "sample_1":     "data/sample_trades_1.json",
    "sample_2":     "data/sample_trades_2.json",
    "beginner":     "data/sample_trades_beginner.json",
    "intermediate": "data/sample_trades_intermediate.json",
    "expert":       "data/sample_trades_expert.json",
}

_ROOT = Path(__file__).parent.parent


def _sample_path(sample_mode: str) -> Path:
    return _ROOT / SAMPLE_FILE_MAP.get(sample_mode, "data/sample_trades_1.json")


def new_data_check_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("new_data_check_node start | session_id=%s", session_id)

    if state.get("input_type") == "journal":
        logger.info("new_data_check_node: journal mode, skip bybit | session_id=%s", session_id)
        return {"has_new_data": False}

    # 사용자의 명시적 샘플 모드 선택은 API 키 존재 여부보다 우선
    sample_mode = state.get("sample_mode", "")
    if sample_mode:
        logger.info(
            "new_data_check_node: sample_mode=%s 명시적 선택 → has_new_data=True | session_id=%s",
            sample_mode, session_id,
        )
        return {"has_new_data": True}

    exchange = state.get("exchange", "Bybit")
    has_api_key = (
        bool(os.getenv("UPBIT_ACCESS_KEY", "")) if exchange == "Upbit"
        else bool(os.getenv("BYBIT_API_KEY", ""))
    )
    if not has_api_key:
        logger.info("new_data_check_node: no API key → has_new_data=True | session_id=%s", session_id)
        return {"has_new_data": True}

    last_fetched_at = state.get("last_fetched_at", "")
    if not last_fetched_at:
        logger.info("new_data_check_node: first run, has_new_data=True | session_id=%s", session_id)
        return {"has_new_data": True}

    sample_mode = state.get("sample_mode", "sample_1")
    path = _sample_path(sample_mode)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        trades = data.get("result", {}).get("list", [])
        if not trades:
            return {"has_new_data": False}

        max_exec_ms = max(int(t.get("execTime", 0)) for t in trades)
        max_exec_dt = datetime.fromtimestamp(max_exec_ms / 1000, tz=timezone.utc)
        last_dt = datetime.fromisoformat(last_fetched_at.replace("Z", "+00:00"))

        has_new = max_exec_dt > last_dt
        logger.info(
            "new_data_check_node: max_exec=%s last=%s has_new_data=%s | session_id=%s",
            max_exec_dt.isoformat(), last_fetched_at, has_new, session_id,
        )
        return {"has_new_data": has_new}
    except Exception as e:
        logger.warning("new_data_check_node: comparison failed: %s", e)
        return {"has_new_data": True}


def _get_exchange_client(state: dict):
    exchange = state.get("exchange", "Bybit")
    if exchange == "Upbit":
        access_key = os.getenv("UPBIT_ACCESS_KEY", "")
        secret_key = os.getenv("UPBIT_SECRET_KEY", "")
        if access_key and secret_key:
            return UpbitClient(access_key, secret_key)
        return None

    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")
    if api_key and api_secret:
        return BybitClient(api_key, api_secret)
    return None


def bybit_fetch_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    sample_mode = state.get("sample_mode", "")

    trades = []
    if not sample_mode:
        client = _get_exchange_client(state)
        if client:
            trades = client.fetch_trades()

    if not trades:
        logger.info("exchange_fetch: loading sample | mode=%s", sample_mode or "sample_1")
        path = _sample_path(sample_mode or "sample_1")
        trades = _load_sample(path)

    now = datetime.now(tz=timezone.utc).isoformat()
    logger.info("exchange_fetch end | session_id=%s trades=%d", session_id, len(trades))
    return {"raw_trades": trades, "last_fetched_at": now}


def _load_sample(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info("bybit_fetch_node: loaded sample from %s", path.name)
        return data.get("result", {}).get("list", [])
    except Exception as e:
        logger.warning("bybit_fetch_node: failed to load sample (%s): %s", path, e)
        return []
