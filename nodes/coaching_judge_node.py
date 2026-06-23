import json
import logging
import os
import re
import time

from utils.llm_factory import get_llm
from utils.observability import trace_llm_call

logger = logging.getLogger(__name__)

PHILOSOPHY_CHECKLIST = """
1. 하루 3번 이상 손절 시 당일 거래 중단 언급 여부
2. 최대 손실금액 사전 고정 언급 여부
3. Revenge Trading 경고 포함 여부
4. No Setup = No Trade 원칙 포함 여부
5. 손절선 사전 결정 언급 여부
"""

_PROMPT_TEMPLATE = """아래 트레이딩 코칭 내용을 검수하세요.

코칭 내용:
{coaching}

검수 기준 (각 항목 pass/fail):
{checklist}

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "scores": {{
    "daily_stop": true,
    "fixed_loss": true,
    "no_revenge": true,
    "no_setup_no_trade": true,
    "stop_first": true
  }},
  "passed": true,
  "feedback": "미충족 항목 보완 제안 1~2문장. 모두 통과면 '철학 기준 충족'"
}}"""


def coaching_judge_node(state: dict) -> dict:
    coaching = state.get("coaching_output", "")
    if not coaching:
        return {"judge_result": "", "judge_passed": False, "judge_scores": {}}

    prompt = _PROMPT_TEMPLATE.format(
        coaching=coaching,
        checklist=PHILOSOPHY_CHECKLIST,
    )

    session_id = state.get("session_id", "default")
    try:
        llm = get_llm(task="default", temperature=0).bind(max_tokens=300)
        _start = time.time()
        resp = llm.invoke([{"role": "user", "content": prompt}])
        _elapsed = time.time() - _start
        text = re.sub(r"```json|```", "", resp.content.strip()).strip()
        result = json.loads(text)
        trace_llm_call(
            node_name="coaching_judge_node",
            input_text=prompt,
            output_text=resp.content,
            model=os.getenv("LLM_PROVIDER", "openai"),
            elapsed=_elapsed,
            session_id=session_id,
        )
        logger.info(
            "coaching_judge_node: passed=%s scores=%s",
            result.get("passed"), result.get("scores"),
        )
        return {
            "judge_result": result.get("feedback", ""),
            "judge_passed": bool(result.get("passed", False)),
            "judge_scores": result.get("scores", {}),
        }
    except Exception as e:
        logger.warning("coaching_judge_node error: %s", e)
        return {"judge_result": "", "judge_passed": True, "judge_scores": {}}
