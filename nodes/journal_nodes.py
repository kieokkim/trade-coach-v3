import io
import logging
import re

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from utils.llm_factory import get_llm

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(task="default", temperature=0.1).bind(max_tokens=200)
    return _llm


_JOURNAL_SYSTEM = """\
당신은 선물 트레이딩 매매일지 작성자입니다.
제공된 거래 데이터를 바탕으로 매매일지를 작성하세요.

규칙:
- 추론하거나 상상하지 말 것
- 제공된 데이터(체결가, 시간, 손익, 방향)에 있는 사실만 서술
- 데이터가 없는 항목은 "데이터 없음"으로 표기
- 각 항목은 1~2문장으로 간결하게
- 반복하지 말 것
- 응답은 반드시 5문장 이내
"""


def _extract_field(text: str, label: str) -> str:
    """'라벨: 값' 형태에서 값 추출."""
    pattern = rf"{label}[:\s]+(.+?)(?=\n(?:진입 근거|청산 근거|회고)|$)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    for line in text.split("\n"):
        if label in line:
            val = line.split(":", 1)[-1].strip()
            if val:
                return val
    return ""


def _build_user_prompt(row: pd.Series) -> tuple[str, dict]:
    """단일 거래 row에서 user prompt 문자열과 fallback용 base dict 반환."""
    symbol = str(row.get("setup", row.get("symbol", ""))).strip() or "데이터 없음"
    date = str(row.get("date", "")).strip()
    result = str(row.get("result", "")).strip().lower()
    direction = str(row.get("direction", "")).strip() or "데이터 없음"
    entry_price = str(row.get("entry_price", "")).strip() or "데이터 없음"
    exit_price = str(row.get("exit_price", "")).strip() or "데이터 없음"
    exec_time_kst = date or "데이터 없음"

    try:
        closed_pnl = float(row.get("closed_pnl", row.get("rr", 0)) or 0)
    except (ValueError, TypeError):
        closed_pnl = 0.0

    result_label = "익절" if closed_pnl > 0 else "손절"

    prompt = (
        f"거래 데이터:\n"
        f"- 종목: {symbol}\n"
        f"- 방향: {direction}\n"
        f"- 진입가: {entry_price} / 청산가: {exit_price}\n"
        f"- 체결시각: {exec_time_kst}\n"
        f"- 실현손익: {closed_pnl}\n"
        f"- 결과: {result_label}\n\n"
        f"아래 형식으로 작성하세요:\n"
        f"진입 근거: (체결가와 시간대 기반 사실만)\n"
        f"청산 근거: (청산가와 손익 기반 사실만)\n"
        f"회고: (결과에 대한 객관적 서술 1문장)"
    )

    base = {
        "date":       date,
        "symbol":     symbol,
        "result":     result,
        "rr":         float(row.get("rr", 0) or 0),
        "_entry_fb":  f"{entry_price}에 진입, {exec_time_kst}",
        "_exit_fb":   f"청산가 {exit_price}, 실현손익 {closed_pnl}",
        "_refl_fb":   f"{result_label} 거래 (손익: {closed_pnl}).",
    }
    return prompt, base


def journal_write_node(state: dict) -> dict:
    """preprocess 이후 정규화된 journal_data 기반으로 거래별 매매일지 자동 작성."""
    session_id = state.get("session_id", "default")
    logger.info("journal_write_node start | session_id=%s", session_id)

    journal_data: str = state.get("journal_data", "")
    if not journal_data.strip():
        logger.warning("journal_write_node: journal_data is empty | session_id=%s", session_id)
        return {"journal_entries": []}

    try:
        df = pd.read_csv(io.StringIO(journal_data))
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        logger.warning("journal_write_node: CSV parse failed: %s", e)
        return {"journal_entries": []}

    entries: list[dict] = []
    for _, row in df.iterrows():
        prompt, base = _build_user_prompt(row)
        try:
            msg = _get_llm().invoke([
                SystemMessage(content=_JOURNAL_SYSTEM),
                HumanMessage(content=prompt),
            ])
            text = msg.content.strip()
            entry = {
                "date":         base["date"],
                "symbol":       base["symbol"],
                "result":       base["result"],
                "rr":           base["rr"],
                "entry_reason": _extract_field(text, "진입 근거"),
                "exit_reason":  _extract_field(text, "청산 근거"),
                "reflection":   _extract_field(text, "회고"),
            }
        except Exception as e:
            logger.warning("journal_write_node LLM error | symbol=%s: %s", base["symbol"], e)
            entry = {
                "date":         base["date"],
                "symbol":       base["symbol"],
                "result":       base["result"],
                "rr":           base["rr"],
                "entry_reason": base["_entry_fb"],
                "exit_reason":  base["_exit_fb"],
                "reflection":   base["_refl_fb"],
            }
        entries.append(entry)

    logger.info("journal_write_node end | session_id=%s entries=%d", session_id, len(entries))
    return {"journal_entries": entries}
