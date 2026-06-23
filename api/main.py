import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from graph import graph, DEFAULT_STATE
from ict.fvg_detector import detect_fvg
from ict.ob_detector import detect_ob
from ict.trend_detector import detect_trendline
from market.candles import get_candles
from nodes.entry_reason_node import entry_reason_node

logger = logging.getLogger(__name__)

app = FastAPI(title="TradeCoach API", version="2.3")


class AnalyzeRequest(BaseModel):
    session_id: str = "default"
    sample_mode: str | None = None
    exchange: str = "Bybit"


def _make_serializable(obj):
    """Non-JSON-serializable objects → safe types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    메인 파이프라인 실행 (memory_load → memory_save).
    기존 Streamlit pages/2_loading.py의 graph.stream() 로직을
    동기 실행 버전으로 변환.
    """
    state = {
        **DEFAULT_STATE,
        "session_id": req.session_id,
        "sample_mode": req.sample_mode or "",
        "exchange": req.exchange,
    }

    result = state.copy()
    completed_nodes = []

    try:
        for chunk in graph.stream(state, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                completed_nodes.append(node_name)
                if node_output:
                    result.update(node_output)
    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={
        "session_id": req.session_id,
        "completed_nodes": completed_nodes,
        "result": _make_serializable(result),
    })


class ReplayRequest(BaseModel):
    symbol: str
    entry_time_ms: int
    order_id: str = ""
    sample_mode: str = ""
    exchange: str = "Bybit"


class AplusRequest(BaseModel):
    symbol: str
    side: str
    direction: str = "Long"
    execPrice: float
    exitPrice: float = 0.0
    execTime: int
    closedPnl: float = 0.0
    stop_price: float = 0.0
    session_id: str = "default"
    sample_mode: str = ""
    exchange: str = "Bybit"


@app.post("/replay/candles")
def get_replay_candles(req: ReplayRequest):
    """캔들 + ICT 패턴 탐지 결과 반환."""
    candles = get_candles(
        req.symbol, req.entry_time_ms,
        order_id=req.order_id or None,
        sample_mode=req.sample_mode or False,
        exchange=req.exchange,
    )
    if not candles:
        raise HTTPException(status_code=404, detail="캔들 데이터 없음")

    return JSONResponse(content=_make_serializable({
        "candles": candles,
        "fvg_zones": detect_fvg(candles),
        "ob_zones": detect_ob(candles),
        "trend_info": detect_trendline(candles),
    }))


@app.post("/replay/aplus")
def get_aplus_score(req: AplusRequest):
    """A+ 채점 + 진입 근거 추론 + RAG 보강 코칭."""
    candles = get_candles(
        req.symbol, req.execTime,
        sample_mode=req.sample_mode or False,
        exchange=req.exchange,
    )
    if not candles:
        raise HTTPException(status_code=404, detail="캔들 데이터 없음")

    trade = {
        "symbol": req.symbol,
        "side": req.side,
        "direction": req.direction,
        "execPrice": str(req.execPrice),
        "exitPrice": str(req.exitPrice),
        "execTime": str(req.execTime),
        "closedPnl": str(req.closedPnl),
        "stop_price": str(req.stop_price),
    }

    try:
        result = entry_reason_node(
            candles=candles,
            ict_patterns={
                "fvg_zones": detect_fvg(candles),
                "ob_zones": detect_ob(candles),
                "trend_info": detect_trendline(candles),
            },
            trade=trade,
            session_id=req.session_id,
        )
    except Exception as e:
        logger.exception("A+ scoring failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content=_make_serializable(result))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
