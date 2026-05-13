# TradeCoach — Future Roadmap

> 현재 레포(`trade-coach-replay`)는 v2.1 개발 목적입니다.
> ⚠️ 표현 주의: "Replay"는 v2.3 이후 단계입니다. v2.1은 "거래 복기 뷰어"입니다.

---

## 왜 새 레포로 분리했는가

v2.1 이후 기능은 v2.0 구조를 크게 변경합니다:
- `market/` 모듈 신규 (OHLCV 인프라)
- `ict/` 모듈 신규 (ICT 탐지 엔진)
- Streamlit 멀티페이지 구조 재편
- plotly 차트 렌더링

v2.0 안정성을 유지하면서 새 기능을 개발하기 위해 별도 레포로 분리했습니다.
자세한 결정 이유는 `DECISION_LOG.md`를 참고하세요.

---

## 사용자 시나리오 (v2.1 목표)

```
1. 시작 페이지: Bybit API 키 입력 또는 샘플 모드 선택
2. 로딩 페이지: 거래내역 자동 수집 진행 상태
3. 메인 페이지:
   Tab 1 (병렬1) 📊 KPI 대시보드
     - 승률 / 평균 수익률 / 기대값 / 손절 일관성
   Tab 2 (병렬2) 📋 거래내역 리스트
     - 복기할 거래 선택
     - → 거래 복기 뷰어 (Trade Context Viewer):
         캔들차트 + 기본 ICT 패턴(FVG 중심) 감지 + LLM 복기 코멘트
   Tab 3 (병렬3) 📚 셋업 태깅 탭
     - 익절/손절 패턴 기초 분류 및 조언
7. 재방문: 신규 거래내역만 자동 추가 수집
```

---

## 단계별 로드맵

### v2.0 — MVP 안정화 ✅ 완료
**레포:** `kieokkim/trade-coach` (태그: v2.0)

- Bybit API 자동 수집 (샘플 폴백)
- KPI 4가지: 승률 / 평균 수익률 / 기대값 / 손절 일관성
- ICT 개념 25개 사전 기반 약점 코칭
- SQLite 세션 메모리 + Streamlit UI

---

### v2.1 — 거래 복기 뷰어 (Trade Context Viewer) 🔄 진행 중
**레포:** `kieokkim/trade-coach-replay`
**브랜치:** `feature/replay-foundation`

> ⚠️ TradingView Bar Replay 수준의 candle-by-candle 인터랙션은 v2.3에서 구현합니다.
> 이 단계는 정적 캔들차트 + 기본 ICT 감지입니다.

추가 예정:
```
market/candles.py        # Bybit Kline API 수집
ict/fvg_detector.py      # FVG rule-based 탐지 (기본 ICT 패턴)
nodes/replay_coach_node.py  # LLM 복기 코멘트
pages/1_api_input.py     # 시작 페이지
pages/2_loading.py       # 로딩 페이지
pages/3_main.py          # 메인 탭 3개
```

완료 기준:
- 거래 선택 → 캔들차트 (진입/청산 마커)
- FVG 구간 오버레이
- LLM 복기 코멘트 1개

---

### v2.2 — ICT Detector Engine
**브랜치:** `feature/ict-detector-engine`

```
ict/ob_detector.py     # Order Block
ict/liquidity.py       # Liquidity Sweep
ict/mss.py             # MSS / BOS
```

원칙: deterministic rule-based 우선, LLM 해석 최소화

---

### v2.3 — Replay Coach
**브랜치:** `feature/replay-coach`

> 이 단계부터 "Replay"라는 표현 사용 적절

- 캔들 단계적 표시 (bar-by-bar)
- "왜 MSS 확인 전에 진입했나요?" 질문 플로우
- AI 복기 피드백

---

### v3.0 — A+ Setup Memory
**브랜치:** `feature/aplus-setup-memory`

> v2.1의 "셋업 태깅 탭"을 확장한 단계

- 패턴 임베딩 + 좋은 거래 clustering
- 과거 A+ 셋업과 현재 진입 유사도 분석
- 장기 반복 약점 추적

---

## 용어 사용 기준

| 단계 | 올바른 표현 | 잘못된 표현 |
|------|-----------|-----------|
| v2.1 | 거래 복기 뷰어, Trade Context Viewer | Replay, 실시간 복기 |
| v2.1 | 기본 ICT 패턴(FVG 중심) 감지 | ICT 패턴 자동 감지 |
| v2.1 | 셋업 태깅 탭 | 셋업 라이브러리, A+ Setup |
| v2.3+ | Replay Coach | (v2.1에서 사용 금지) |
| v3.0 | A+ Setup Memory | (v2.1에서 사용 금지) |

---

## 개발 원칙

1. v2.0 MVP를 깨뜨리지 않음 (별도 레포)
2. ICT 탐지는 rule-based 우선, LLM은 설명/코칭 역할
3. 복기 기능은 "자동매매"보다 "트레이더 행동 교정" 목적
4. 자동 매매 기능 영구 미구현 (Read-Only API)
5. 표현 범위는 실제 구현 수준에 맞게 제한
