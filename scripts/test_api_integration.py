import sys
import time

import requests

API_BASE = "http://localhost:8000"
SESSION_ID = f"integration_test_{int(time.time())}"


def wait_for_server(timeout=10):
    for _ in range(timeout):
        try:
            requests.get(f"{API_BASE}/health", timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def test_health():
    resp = requests.get(f"{API_BASE}/health", timeout=5)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("✅ /health: OK")


def test_analyze():
    resp = requests.post(f"{API_BASE}/analyze", json={
        "session_id": SESSION_ID,
        "sample_mode": "beginner",
    }, timeout=120)
    assert resp.status_code == 200, f"analyze failed: {resp.text}"
    data = resp.json()
    assert len(data["completed_nodes"]) > 0
    assert "raw_trades" in data["result"]
    assert "stats" in data["result"]
    assert "weaknesses" in data["result"]
    print(f"✅ /analyze: {len(data['completed_nodes'])} nodes, "
          f"{len(data['result']['raw_trades'])} trades")
    return data["result"]


def test_replay_candles(result):
    buy_trades = [t for t in result["raw_trades"] if t["side"] == "Buy"]
    assert buy_trades, "no Buy trades found"
    trade = buy_trades[0]

    resp = requests.post(f"{API_BASE}/replay/candles", json={
        "symbol": trade["symbol"],
        "entry_time_ms": int(trade["execTime"]),
        "order_id": trade.get("orderId", ""),
        "sample_mode": "beginner",
    }, timeout=30)
    assert resp.status_code == 200, f"replay/candles failed: {resp.text}"
    data = resp.json()
    assert len(data["candles"]) > 0
    assert "fvg_zones" in data
    assert "ob_zones" in data
    assert "trend_info" in data
    print(f"✅ /replay/candles: {len(data['candles'])} candles, "
          f"{len(data['fvg_zones'])} FVG, {len(data['ob_zones'])} OB")
    return data, trade


def test_replay_aplus(trade):
    resp = requests.post(f"{API_BASE}/replay/aplus", json={
        "symbol": trade["symbol"],
        "side": trade["side"],
        "execPrice": float(trade["execPrice"]),
        "exitPrice": float(trade["execPrice"]) - 100,
        "execTime": int(trade["execTime"]),
        "closedPnl": -10.0,
        "sample_mode": "beginner",
    }, timeout=30)
    assert resp.status_code == 200, f"replay/aplus failed: {resp.text}"
    data = resp.json()
    assert "aplus_score" in data
    assert "aplus_breakdown" in data
    assert "entry_reason" in data
    assert "coaching" in data
    print(f"✅ /replay/aplus: score {data['aplus_score']}/5")


if __name__ == "__main__":
    print(f"API server: {API_BASE}")
    if not wait_for_server():
        print("❌ API 서버가 실행되지 않았습니다. "
              "`uv run python api/main.py`로 먼저 실행해주세요.")
        sys.exit(1)

    test_health()
    result = test_analyze()
    _, trade = test_replay_candles(result)
    test_replay_aplus(trade)
    print("\n🎉 전체 통합 테스트 통과")
