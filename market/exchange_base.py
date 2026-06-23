from abc import ABC, abstractmethod


class ExchangeClient(ABC):
    @abstractmethod
    def fetch_trades(self, start_time_ms: int | None = None) -> list[dict]:
        """거래내역 조회 → Bybit V5 응답 구조로 정규화해서 반환."""

    @abstractmethod
    def fetch_candles(
        self, symbol: str, interval: str, start_ms: int, limit: int
    ) -> list[dict]:
        """캔들 조회 → 공통 캔들 dict 구조로 정규화."""

    @abstractmethod
    def check_permissions(self) -> dict:
        """API 키 권한 확인 → {valid, read_only, warning} 구조로 반환."""
