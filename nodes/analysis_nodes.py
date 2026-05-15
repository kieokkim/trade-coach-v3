import io
import logging
from datetime import datetime, timezone

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from utils.llm_factory import get_llm

from db import get_db
from tools.concept_tool import search_ict_concept, CONCEPT_NOT_FOUND_PREFIX

logger = logging.getLogger(__name__)

_llm = None

_ACTION_RULE_SYSTEM = """\
당신은 트레이딩 코치입니다. 트레이더의 성과 지표를 보고 내일 당장 실행할 구체적인 규칙을 한국어로 한 문장 작성하세요.
금지 또는 의무 형식으로 작성하세요. 예: "OB 셋업에서 반드시 손절을 지정하세요" 또는 "FVG 셋업 외에는 진입하지 마세요".
규칙 문장 하나만 출력하세요."""


def _get_hour(exec_time_ms) -> int:
    try:
        return datetime.fromtimestamp(int(exec_time_ms) / 1000, tz=timezone.utc).hour
    except Exception:
        return 0


def _has_consecutive_loss(journal: list, n: int = 3) -> bool:
    count = 0
    for t in journal:
        if t.get("result") == "loss":
            count += 1
            if count >= n:
                return True
        else:
            count = 0
    return False


ICT_WEAKNESS_RULES = [
    # (태그명, 조건 함수, 설명)
    ("과매매_감지",
     lambda s, j: len(j) >= 3 and
                  len([t for t in j if t.get("result") == "loss"]) >= 2,
     "하루 손절 2회 이상 감지"),

    ("킬존외_진입",
     lambda s, j: any(
         not (2 <= _get_hour(t.get("execTime", 0)) <= 5 or
              7 <= _get_hour(t.get("execTime", 0)) <= 10)
         for t in j if t.get("result") == "loss"
     ),
     "런던/뉴욕 킬존 외 시간대 손실 거래"),

    ("손절_불규칙",
     lambda s, j: float(s.get("loss_consistency", 0)) > 2.0,
     "손절 크기가 들쭉날쭉"),

    ("기대값_음수",
     lambda s, j: float(s.get("expected_value", 0)) < 0,
     "전략의 장기 기대값이 음수"),

    ("승률_낮음",
     lambda s, j: float(s.get("win_rate", 1)) < 0.4,
     "승률 40% 미만"),

    ("수익률_낮음",
     lambda s, j: float(s.get("avg_return_rate", 1)) < 1.0,
     "평균 수익률 1% 미만"),

    ("연속손실_패턴",
     lambda s, j: _has_consecutive_loss(j, n=3),
     "3회 이상 연속 손절"),
]


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(temperature=0.3)
    return _llm


# ─────────────────────────── pandas 통계 계산 ──────────────────────────────

def _compute_stats(journal_data: str) -> dict:
    try:
        df = pd.read_csv(io.StringIO(journal_data))
    except Exception as e:
        logger.warning("_compute_stats: CSV parse failed: %s", e)
        return {"error": str(e)}

    df.columns = [c.strip().lower() for c in df.columns]

    if df.empty:
        return {"error": "empty dataframe"}

    df["result"] = df["result"].astype(str).str.strip().str.lower()
    total = len(df)
    win_mask = df["result"] == "win"
    loss_mask = df["result"] == "loss"
    win_rate = float(win_mask.sum() / total) if total > 0 else 0.0

    # return_rate: closed_pnl/exec_value*100 우선, fallback rr
    if "closed_pnl" in df.columns and "exec_value" in df.columns:
        pnl = pd.to_numeric(df["closed_pnl"], errors="coerce").fillna(0.0)
        ev  = pd.to_numeric(df["exec_value"],  errors="coerce").fillna(0.0)
        df["return_rate"] = pnl.where(ev == 0, pnl / ev.replace(0, float("nan")) * 100).fillna(0.0)
    elif "rr" in df.columns:
        df["return_rate"] = pd.to_numeric(df["rr"], errors="coerce").fillna(0.0)
    else:
        df["return_rate"] = 0.0

    avg_return_rate = float(df["return_rate"].mean())

    win_ret  = df.loc[win_mask,  "return_rate"]
    loss_ret = df.loc[loss_mask, "return_rate"]
    avg_win      = float(win_ret.mean())       if len(win_ret)  > 0 else 0.0
    avg_loss_abs = float(loss_ret.abs().mean()) if len(loss_ret) > 0 else 0.0
    expected_value = win_rate * avg_win - (1 - win_rate) * avg_loss_abs

    if len(loss_ret) >= 2:
        la = loss_ret.abs()
        loss_consistency = float(la.std() / la.mean()) if la.mean() != 0 else 0.0
    else:
        loss_consistency = 0.0

    # max consecutive losses
    max_dd = cur_dd = 0
    for r in df["result"].tolist():
        if r == "loss":
            cur_dd += 1
            max_dd = max(max_dd, cur_dd)
        else:
            cur_dd = 0

    setup_analysis: dict = {}
    best_setup = worst_setup = ""
    if "setup" in df.columns:
        df["setup"] = df["setup"].astype(str).str.strip()
        grp = df.groupby("setup")["return_rate"].mean()
        setup_analysis = {k: round(float(v), 4) for k, v in grp.items()}
        if setup_analysis:
            best_setup  = max(setup_analysis, key=setup_analysis.get)
            worst_setup = min(setup_analysis, key=setup_analysis.get)

    return {
        "win_rate":         round(win_rate, 4),
        "avg_return_rate":  round(avg_return_rate, 4),
        "expected_value":   round(expected_value, 4),
        "loss_consistency": round(loss_consistency, 4),
        "max_drawdown":     int(max_dd),
        "best_setup":       best_setup,
        "worst_setup":      worst_setup,
        "trade_count":      total,
        "setup_analysis":   setup_analysis,
    }


def _generate_action_rule(stats: dict) -> str:
    try:
        summary = (
            f"승률: {stats.get('win_rate', 0):.1%}, "
            f"평균수익률: {stats.get('avg_return_rate', 0):.2f}%, "
            f"기대값: {stats.get('expected_value', 0):.2f}%, "
            f"손절일관성: {stats.get('loss_consistency', 0):.2f}, "
            f"최악셋업: {stats.get('worst_setup', '') or '없음'}"
        )
        msg = _get_llm().invoke([
            SystemMessage(content=_ACTION_RULE_SYSTEM),
            HumanMessage(content=summary),
        ])
        return msg.content.strip()
    except Exception as e:
        logger.warning("_generate_action_rule LLM error: %s", e)
        return ""


# ─────────────────────────── 노드 함수 ────────────────────────────────────

def journal_analysis_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("journal_analysis_node start | session_id=%s", session_id)

    journal_data: str = state.get("journal_data", "")
    if not journal_data.strip():
        logger.warning("journal_analysis_node: journal_data empty | session_id=%s", session_id)
        return {"stats": {"error": "no data"}, "setup_analysis": {}, "action_rule": ""}

    stats = _compute_stats(journal_data)
    action_rule = _generate_action_rule(stats) if "error" not in stats else ""

    logger.info(
        "journal_analysis_node end | session_id=%s stats_keys=%s",
        session_id, list(stats.keys()),
    )
    return {
        "stats":          stats,
        "setup_analysis": stats.get("setup_analysis", {}),
        "action_rule":    action_rule,
    }


# ─────────────────────── 약점 감지 + DB 우선순위 정렬 ─────────────────────

def _sort_by_recurrence(weaknesses: list[str], session_id: str) -> list[str]:
    if len(weaknesses) <= 1:
        return weaknesses
    try:
        with get_db() as conn:
            counts = {}
            for w in weaknesses:
                row = conn.execute(
                    "SELECT count FROM weaknesses WHERE session_id=? AND weakness=?",
                    (session_id, w),
                ).fetchone()
                counts[w] = row["count"] if row else 0
        return sorted(weaknesses, key=lambda w: counts.get(w, 0), reverse=True)
    except Exception:
        return weaknesses


def weakness_detect_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("weakness_detect_node start | session_id=%s", session_id)

    stats           = state.get("stats", {})
    past            = state.get("past_weaknesses", [])
    journal_entries = state.get("journal_entries", [])

    if "error" in stats:
        logger.warning("weakness_detect_node: stats contains error, skipping")
        return {"weaknesses": [], "concept_not_found": False}

    current: list[str] = []
    for tag, condition, _ in ICT_WEAKNESS_RULES:
        try:
            if condition(stats, journal_entries):
                current.append(tag)
        except Exception as e:
            logger.warning("weakness rule error [%s]: %s", tag, e)

    recurring = [w for w in current if w in past]
    new_ones  = [w for w in current if w not in past]
    weaknesses = _sort_by_recurrence(recurring, session_id) + new_ones

    # concept 존재 여부 확인 (fallback 라우팅용)
    concept_not_found = False
    if weaknesses:
        concept_info = search_ict_concept.invoke({"weakness_tag": weaknesses[0]})
        concept_not_found = concept_info.startswith(CONCEPT_NOT_FOUND_PREFIX)

    logger.info(
        "weakness_detect_node end | session_id=%s weaknesses=%s",
        session_id, weaknesses,
    )
    return {"weaknesses": weaknesses, "concept_not_found": concept_not_found}
