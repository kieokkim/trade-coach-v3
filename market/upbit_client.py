import logging
from datetime import datetime, timezone

import jwt
import requests
import uuid
import hashlib
from urllib.parse import urlencode, unquote

from market.exchange_base import ExchangeClient

logger = logging.getLogger(__name__)

_UPBIT_API_URL = "https://api.upbit.com"


class UpbitClient(ExchangeClient):
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key

    def _auth_header(self, query: dict | None = None) -> dict:
        payload = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
        }
        if query:
            query_string = unquote(urlencode(query, doseq=True)).encode("utf-8")
            m = hashlib.sha512()
            m.update(query_string)
            payload["query_hash"] = m.hexdigest()
            payload["query_hash_alg"] = "SHA512"

        token = jwt.encode(payload, self.secret_key)
        return {"Authorization": f"Bearer {token}"}

    def fetch_trades(self, start_time_ms: int | None = None) -> list[dict]:
        params = {"state": "done", "limit": 50, "order_by": "desc"}
        headers = self._auth_header(params)

        try:
            resp = requests.get(
                f"{_UPBIT_API_URL}/v1/orders/closed",
                params=params,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            orders = resp.json()
            logger.info("UpbitClient.fetch_trades: %d orders", len(orders))

            normalized = []
            for o in orders:
                trades = o.get("trades", [])
                exec_price = o.get("price") or (trades[0]["price"] if trades else "0")
                exec_qty = o.get("executed_volume", "0")
                created = o.get("created_at", "")
                try:
                    dt = datetime.fromisoformat(created)
                    exec_ms = str(int(dt.timestamp() * 1000))
                except Exception:
                    exec_ms = "0"

                market = o.get("market", "")
                symbol = market.replace("KRW-", "") + "KRW" if market.startswith("KRW-") else market

                normalized.append({
                    "symbol": symbol,
                    "side": "Buy" if o.get("side") == "bid" else "Sell",
                    "execPrice": str(exec_price),
                    "execQty": str(exec_qty),
                    "execTime": exec_ms,
                    "orderId": o.get("uuid", ""),
                    "orderType": o.get("ord_type", ""),
                    "leavesQty": "0",
                    "closedSize": str(exec_qty),
                    "execFee": str(o.get("paid_fee", "0")),
                })
            return normalized
        except Exception as e:
            logger.warning("UpbitClient.fetch_trades failed: %s", e)
            return []

    def fetch_candles(
        self, symbol: str, interval: str, start_ms: int, limit: int
    ) -> list[dict]:
        market = f"KRW-{symbol.replace('KRW', '')}" if "KRW" in symbol else symbol
        interval_min = int(interval) if interval.isdigit() else 15

        to_dt = datetime.fromtimestamp(
            (start_ms + interval_min * 60 * 1000 * limit) / 1000,
            tz=timezone.utc,
        )
        to_str = to_dt.strftime("%Y-%m-%dT%H:%M:%S")

        try:
            resp = requests.get(
                f"{_UPBIT_API_URL}/v1/candles/minutes/{interval_min}",
                params={"market": market, "to": to_str, "count": min(limit, 200)},
                timeout=10,
            )
            resp.raise_for_status()
            raw = resp.json()

            candles = [
                {
                    "timestamp": int(
                        datetime.fromisoformat(
                            c["candle_date_time_utc"]
                        ).replace(tzinfo=timezone.utc).timestamp() * 1000
                    ),
                    "open": float(c["opening_price"]),
                    "high": float(c["high_price"]),
                    "low": float(c["low_price"]),
                    "close": float(c["trade_price"]),
                    "volume": float(c["candle_acc_trade_volume"]),
                }
                for c in raw
            ]
            candles.sort(key=lambda x: x["timestamp"])
            logger.info("UpbitClient.fetch_candles: %d candles for %s", len(candles), market)
            return candles
        except Exception as e:
            logger.warning("UpbitClient.fetch_candles failed: %s", e)
            return []

    def check_permissions(self) -> dict:
        return {
            "valid": True,
            "read_only": None,
            "warning": (
                "Upbit는 키 발급 시 권한을 직접 지정합니다. "
                "조회 권한만 체크했는지 발급 페이지에서 확인하세요."
            ),
        }
