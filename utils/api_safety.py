import logging

from market.bybit_client import BybitClient

logger = logging.getLogger(__name__)


def check_api_permissions(api_key: str, api_secret: str) -> dict:
    """Bybit API 키 권한 확인. 거래 권한이 있으면 경고."""
    return BybitClient(api_key, api_secret).check_permissions()
