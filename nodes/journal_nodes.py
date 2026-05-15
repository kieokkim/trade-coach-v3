import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _format_journal_entry(trade):
    ms = int(trade.get("execTime", 0))
    t  = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    kt = t.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    h  = t.hour
    session = ("런던 세션" if 2 <= h <= 5 else
               "뉴욕 세션" if 7 <= h <= 10 else
               "뉴욕 오후" if 13 <= h <= 16 else "세션 외")
    pnl    = float(trade.get("closedPnl", 0))
    result = "win" if pnl > 0 else "loss"
    return {
        "date":         kt,
        "symbol":       trade.get("symbol", ""),
        "direction":    trade.get("direction", "Long"),
        "result":       result,
        "entry_reason": f"{kt} {session} {trade.get('symbol')} {trade.get('direction', 'Long')} 진입. 진입가 {trade.get('execPrice')}.",
        "exit_reason":  f"청산가 {trade.get('exitPrice', '')}, 실현손익 ${pnl:+.2f} ({'익절' if pnl > 0 else '손절'}).",
        "reflection":   f"{session} {'킬존 내' if session != '세션 외' else '킬존 외'} {'익절' if pnl > 0 else '손절'} 마감.",
        "rr":           float(trade.get("rr", 0)),
        "execTime":     ms,
        "closedPnl":    pnl,
    }


def journal_write_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("journal_write_node start | session_id=%s", session_id)

    closed = [t for t in state.get("raw_trades", [])
              if t.get("closedPnl", "0") != "0"]

    entries = [_format_journal_entry(t) for t in closed]

    logger.info("journal_write_node end | session_id=%s entries=%d", session_id, len(entries))
    return {"journal_entries": entries, "journal_data": "rule-based"}
