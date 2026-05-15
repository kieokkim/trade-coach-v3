import json
import logging
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage

from utils.llm_factory import get_llm

from db import get_db
from tools.concept_tool import search_ict_concept, CONCEPT_NOT_FOUND_PREFIX

logger = logging.getLogger(__name__)

_CONCEPTS_PATH = Path(__file__).parent.parent / "tools" / "ict_concepts.json"

TRADING_PHILOSOPHY = """\
[트레이딩 철학 — 반드시 준수]
1. 연속 3번 손절 시 즉시 중단한다.
2. 매 거래마다 최대 손실금액을 사전에 고정한다 (손해보지 않는 트레이딩).
3. 감정적 복수 매매(Revenge Trading)는 절대 하지 않는다.
4. 셋업이 없으면 진입하지 않는다 (No Setup = No Trade).
5. 손절선은 진입 전에 반드시 먼저 결정한다."""

# ─────────────────────────────── backtest_coach_node ────────────────────────

_COACH_SYSTEM = """\
당신은 ICT(Inner Circle Trader) 전문 트레이딩 코치입니다.
트레이더의 성과 요약, 약점 목록, ICT 개념 설명을 바탕으로 맞춤형 코칭 피드백을 한국어로 작성하세요.

작성 지침:
1. 1순위 약점이 실제 매매에서 어떻게 나타났는지 구체적으로 언급
2. 관련 ICT 개념을 실전에 적용하는 백테스트 전략 1가지 제시
3. 내일 당장 실행할 수 있는 구체적 규칙 1~2개 제시
4. 추가 약점이 있으면 각 1문장씩 간략히 언급

응답은 300자 이내의 평문(plain text)으로 작성하세요.

""" + TRADING_PHILOSOPHY

_coach_llm = None


def _get_coach_llm():
    global _coach_llm
    if _coach_llm is None:
        _coach_llm = get_llm(task="complex", temperature=0.3)
    return _coach_llm


def backtest_coach_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("backtest_coach_node start | session_id=%s", session_id)

    performance_summary: dict = state.get("performance_summary", {})
    weaknesses: list = state.get("weaknesses", [])

    if not weaknesses:
        return {"coaching_output": "현재 세션에서 특별한 약점이 감지되지 않았습니다. 현재 전략을 유지하세요."}

    primary_weakness = weaknesses[0]
    concept_info = search_ict_concept.invoke({"weakness_tag": primary_weakness})
    if concept_info.startswith(CONCEPT_NOT_FOUND_PREFIX):
        concept_info = ""

    context_parts: list[str] = []
    if performance_summary:
        context_parts.append(f"성과 요약: {json.dumps(performance_summary, ensure_ascii=False)}")
    context_parts.append(f"1순위 약점: {primary_weakness}")
    if len(weaknesses) > 1:
        context_parts.append(f"추가 약점: {', '.join(weaknesses[1:])}")
    if concept_info:
        context_parts.append(f"개념 설명:\n{concept_info}")

    try:
        msg = _get_coach_llm().invoke([
            {"role": "system", "content": _COACH_SYSTEM},
            {"role": "user", "content": "\n\n".join(context_parts)},
        ])
        coaching_output = msg.content.strip()
    except Exception as e:
        logger.warning("backtest_coach_node LLM error: %s | session_id=%s", e, session_id)
        coaching_output = f"약점: {', '.join(weaknesses)}. 내일 집중 개선 필요."

    logger.info("backtest_coach_node end | session_id=%s weaknesses=%s", session_id, weaknesses)
    return {"coaching_output": coaching_output}


# ──────────────────────────── fallback_classify_node ────────────────────────

_CLASSIFY_SYSTEM = """\
트레이딩 약점 태그를 보고 아래 3가지 중 하나만 정확히 반환하세요. 다른 문자는 출력하지 마세요.

ICT개념  - ICT 기술 개념이 부족해서 발생하는 약점 (예: 특정 패턴 미인식, 진입 기준 혼동)
심리     - 알고는 있지만 감정·충동·규율 부재로 발생하는 약점 (예: 충동매매, 손절 회피)
패턴     - 유저 고유의 반복 행동 데이터로만 판단 가능한 약점 (예: 특정 시간대 연속 손실)"""

_GENERATE_SYSTEM = """\
당신은 ICT(Inner Circle Trader) 전문 트레이딩 코치입니다.
주어진 트레이딩 약점 태그에 대한 ICT 개념 설명을 JSON으로 생성하세요.
반드시 아래 키를 포함하세요:
  정의: str
  핵심_포인트: list[str] (정확히 3개)
  실수_패턴: str
  개선_방법: str
  category: 항상 "auto_generated"으로 고정"""

_CATEGORY_MAP = {"ICT개념": "ict", "심리": "psychology", "패턴": "pattern"}

_classify_llm = None
_generate_llm = None


def _get_classify_llm():
    global _classify_llm
    if _classify_llm is None:
        _classify_llm = get_llm(temperature=0)
    return _classify_llm


def _get_generate_llm():
    global _generate_llm
    if _generate_llm is None:
        _generate_llm = get_llm(temperature=0.3).bind(response_format={"type": "json_object"})
    return _generate_llm


def _classify_tag(tag: str) -> str:
    result = _get_classify_llm().invoke([
        {"role": "system", "content": _CLASSIFY_SYSTEM},
        {"role": "user", "content": f"약점 태그: {tag}"},
    ])
    return result.content.strip()


def _handle_ict(tag: str) -> str:
    gen = _get_generate_llm().invoke([
        {"role": "system", "content": _GENERATE_SYSTEM},
        {"role": "user", "content": f"약점 태그: {tag}"},
    ])
    concept_data: dict = json.loads(gen.content)
    concept_data["category"] = "auto_generated"

    concepts = json.loads(_CONCEPTS_PATH.read_text(encoding="utf-8"))
    concepts[tag] = concept_data
    _CONCEPTS_PATH.write_text(
        json.dumps(concepts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    import tools.concept_tool as _ct
    _ct._concepts = None  # 캐시 무효화

    points = "\n".join(f"  • {p}" for p in concept_data["핵심_포인트"])
    return (
        f"【{tag}】(자동 생성)\n"
        f"정의: {concept_data['정의']}\n\n"
        f"핵심 포인트:\n{points}\n\n"
        f"개선 방법: {concept_data['개선_방법']}"
    )


def _handle_psychology(tag: str) -> str:
    return (
        f"이 패턴은 ICT 기술보다 트레이딩 심리 문제입니다.\n\n"
        f"'{tag}' 약점은 기술적 지식 부족이 아닌 심리적 요인에서 비롯됩니다. "
        f"트레이딩 규칙 준수, 감정 관리, 일관성 유지에 집중하세요."
    )


def _handle_pattern(tag: str, session_id: str) -> str:
    today = date.today().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO weaknesses (session_id, weakness, count, last_seen)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(session_id, weakness)
                DO UPDATE SET count = count + 1, last_seen = excluded.last_seen
                """,
                (session_id, tag, today),
            )
    except Exception as e:
        logger.warning("_handle_pattern DB upsert failed: %s", e)
    return f"'{tag}' 패턴을 계속 모니터링하겠습니다. 충분한 데이터가 쌓이면 분석 결과를 제공합니다."


def fallback_classify_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("fallback_classify_node start | session_id=%s", session_id)

    weaknesses = state.get("weaknesses", [])
    messages = list(state.get("messages", []))

    if not weaknesses:
        return {"fallback_type": "", "messages": messages}

    tag = weaknesses[0]
    raw_category = _classify_tag(tag)
    fallback_type = _CATEGORY_MAP.get(raw_category, "pattern")

    if raw_category == "ICT개념":
        msg = _handle_ict(tag)
    elif raw_category == "심리":
        msg = _handle_psychology(tag)
    else:
        fallback_type = "pattern"
        msg = _handle_pattern(tag, session_id)

    messages.append(AIMessage(content=msg))
    logger.info(
        "fallback_classify_node end | session_id=%s tag=%s fallback_type=%s",
        session_id, tag, fallback_type,
    )
    return {"fallback_type": fallback_type, "messages": messages}


# ───────────────────────── generate_setup_suggestion ────────────────────────

_SETUP_SUGGESTION_SYSTEM = """\
당신은 ICT(Inner Circle Trader) 전문 트레이딩 코치입니다.
트레이더의 셋업별 수익률 데이터를 보고 개선 제안을 한국어 1~2문장으로 작성하세요.
가장 수익난 셋업을 강화하고, 가장 손실난 셋업의 개선점을 구체적으로 제시하세요.

""" + TRADING_PHILOSOPHY


def generate_setup_suggestion(
    win_count: int,
    loss_count: int,
    best_setup: str,
    worst_setup: str,
    setup_analysis: dict,
) -> str:
    total = win_count + loss_count
    win_rate = win_count / total if total > 0 else 0.0

    setup_summary = ", ".join(
        f"{k}: {v:.2f}%" for k, v in sorted(setup_analysis.items(), key=lambda x: -x[1])
    )
    user_content = (
        f"전체 {total}건 | 익절 {win_count}건 | 손절 {loss_count}건 | 승률 {win_rate:.1%}\n"
        f"셋업별 수익률: {setup_summary}\n"
        f"최고 셋업: {best_setup or '없음'} | 최악 셋업: {worst_setup or '없음'}"
    )

    try:
        msg = _get_coach_llm().invoke([
            {"role": "system", "content": _SETUP_SUGGESTION_SYSTEM},
            {"role": "user",   "content": user_content},
        ])
        return msg.content.strip()
    except Exception as e:
        logger.warning("generate_setup_suggestion LLM error: %s", e)
        if best_setup and worst_setup:
            return f"{best_setup} 셋업을 강화하고 {worst_setup} 셋업 진입 기준을 재점검하세요."
        return "데이터 부족으로 제안을 생성할 수 없습니다."
