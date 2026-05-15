import json
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "sample_trades.json")


def get_sample_trade() -> dict:
    with open(_DATA_PATH) as f:
        data = json.load(f)
    return data["result"]["list"][0]


def get_sample_trades() -> list[dict]:
    with open(_DATA_PATH) as f:
        data = json.load(f)
    return data["result"]["list"]
