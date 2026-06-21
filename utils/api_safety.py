import logging

from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)


def check_api_permissions(api_key: str, api_secret: str) -> dict:
    """Bybit API 키 권한 확인. 거래 권한이 있으면 경고."""
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=api_secret)
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
        logger.error("API key permission check failed: %s", e)
        return {
            "valid": False,
            "read_only": False,
            "permissions": {},
            "trade_permissions": [],
            "warning": f"API 키 검증 실패: {e}",
        }
