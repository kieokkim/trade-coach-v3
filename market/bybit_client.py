import hashlib
import hmac
import logging
import time

import requests
from pybit.unified_trading import HTTP

from market.exchange_base import ExchangeClient

logger = logging.getLogger(__name__)

_BYBIT_EXEC_URL = "https://api.bybit.com/v5/execution/list"


class BybitClient(ExchangeClient):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def fetch_trades(self, start_time_ms: int | None = None) -> list[dict]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        query_str = "category=linear&limit=50"
        sign_payload = f"{timestamp}{self.api_key}{recv_window}{query_str}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            sign_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
        }

        try:
            resp = requests.get(
                _BYBIT_EXEC_URL,
                params={"category": "linear", "limit": 50},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("BybitClient.fetch_trades: retCode=%s", data.get("retCode"))
            return data.get("result", {}).get("list", [])
        except Exception as e:
            logger.warning("BybitClient.fetch_trades failed: %s", e)
            return []

    def fetch_candles(
        self, symbol: str, interval: str, start_ms: int, limit: int
    ) -> list[dict]:
        session = HTTP(testnet=False)
        try:
            response = session.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                start=start_ms,
                limit=limit,
            )
            candles = [
                {
                    "timestamp": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                }
                for c in response["result"]["list"]
            ]
            candles.sort(key=lambda x: x["timestamp"])
            logger.info("BybitClient.fetch_candles: %d candles for %s", len(candles), symbol)
            return candles
        except Exception as e:
            logger.warning("BybitClient.fetch_candles failed: %s", e)
            return []

    def check_permissions(self) -> dict:
        try:
            session = HTTP(
                testnet=False, api_key=self.api_key, api_secret=self.api_secret
            )
            resp = session.get_api_key_information()
            result = resp.get("result", {})
            permissions = result.get("permissions", {})

            trade_permissions = []
            for category, perms in permissions.items():
                if isinstance(perms, list):
                    for p in perms:
                        if any(kw in p for kw in ("Order", "Trade", "Withdraw")):
                            trade_permissions.append(f"{category}:{p}")

            is_read_only = len(trade_permissions) == 0
            warning = ""
            if not is_read_only:
                warning = (
                    f"⚠️ 거래 권한이 감지됐습니다: {', '.join(trade_permissions)}. "
                    f"TradeCoach는 분석 전용 도구입니다. "
                    f"read-only 권한의 API 키 사용을 강력히 권장합니다."
                )
                logger.warning("API key has trade permissions: %s", trade_permissions)

            return {
                "valid": True,
                "read_only": is_read_only,
                "permissions": permissions,
                "trade_permissions": trade_permissions,
                "warning": warning,
            }
        except Exception as e:
            logger.error("BybitClient.check_permissions failed: %s", e)
            return {
                "valid": False,
                "read_only": False,
                "permissions": {},
                "trade_permissions": [],
                "warning": f"API 키 검증 실패: {e}",
            }
