# TradeCoach v2.1

AI 기반 트레이딩 복기 코치.  
Bybit API로 매매내역을 자동 수집하고  
**캔들 복기 뷰어 + FVG 탐지 + LLM 코칭 루프**를 제공합니다.

---

## 핵심 기능 (v2.1)

| 기능 | 설명 |
|------|------|
| 🔑 API 연결 / 샘플 체험 | Bybit API Key 입력 또는 샘플 데이터로 즉시 시작 |
| 📊 KPI 대시보드 | 승률 / 평균 수익률 / 기대값 / 손절 일관성 |
| 📈 캔들 복기 뷰어 | 진입 전후 캔들 + 진입/청산 마커 (Plotly) |
| 🟡 FVG 탐지 (rule-based) | Fair Value Gap 자동 탐지 + 차트 오버레이 |
| 🤖 LLM 복기 코멘트 | ICT 관점 진단 + 개선 제안 (GPT-4o-mini) |
| 📚 셋업 태깅 | 셋업별 수익률 분석 + 개선 제안 생성 |

---

## 설치

```bash
# Python 3.13 필요
uv venv && source .venv/bin/activate
uv sync
```

## 환경 설정

```bash
cp .env.example .env
# .env에 키 입력:
# OPENAI_API_KEY=sk-...
# BYBIT_API_KEY=...      (선택 — 없으면 샘플 데이터 모드)
# BYBIT_API_SECRET=...   (선택)
```

## 실행

```bash
# 멀티페이지 Streamlit 앱
uv run streamlit run streamlit_app.py
```

앱이 열리면 자동으로 **API 입력 페이지**로 이동합니다.

```
1. API Key 입력 또는 "샘플 데이터로 체험하기" 클릭
2. 로딩 화면에서 데이터 수집 + 분석 진행
3. 메인 대시보드 3탭 확인
   - Tab 1: KPI 대시보드
   - Tab 2: 거래내역 리스트 + 복기 뷰어 (캔들차트 + FVG + LLM 코멘트)
   - Tab 3: 셋업 태깅 (수익률 분석 + 개선 제안)
```

---

## 스크린샷

> _[placeholder] 1_api_input 페이지_

> _[placeholder] 2_loading 페이지 (progress bar)_

> _[placeholder] Tab 2 복기 뷰어 (캔들차트 + FVG 오버레이 + LLM 코멘트)_

> _[placeholder] Tab 3 셋업 태깅 (bar_chart + 개선 제안)_

---

## 프로젝트 구조

```
trade-coach-v3/
├── streamlit_app.py        # 진입점 → pages/1_api_input.py 리다이렉트
├── pages/
│   ├── 1_api_input.py      # API 연결 / 샘플 시작
│   ├── 2_loading.py        # 데이터 수집 + graph.invoke
│   └── 3_main.py           # KPI / 복기 뷰어 / 셋업 태깅
├── graph.py                # TradeCoachState + LangGraph 정의
├── nodes/                  # 노드 구현
│   ├── fetch_nodes.py
│   ├── preprocess_nodes.py
│   ├── analysis_nodes.py
│   ├── coaching_nodes.py   # backtest_coach + setup suggestion
│   ├── replay_coach_node.py  # LLM 복기 코멘트
│   └── ...
├── ict/
│   └── fvg_detector.py     # Rule-based FVG 탐지
├── market/
│   └── candles.py          # Bybit Kline API
├── utils/
│   └── chart.py            # Plotly 캔들차트 렌더러
├── data/
│   └── sample_trades.json  # 샘플 거래 데이터
├── tools/
└── db.py
```

---

## 개발 로드맵

| 버전 | 목표 | 상태 |
|------|------|------|
| v2.0 | MVP 안정화 | ✅ 완료 |
| v2.1 | Replay Foundation — 복기 뷰어 + FVG 탐지 | ✅ 완료 |
| v2.2 | ICT Detector — OB/MSS/Liquidity 추가 탐지 | 🔜 예정 |
| v2.3 | Replay Coach — candle-by-candle 복기 | 🔜 예정 |
| v3.0 | A+ Setup Memory — 개인 셋업 라이브러리 | 🔜 예정 |

---

## 문서 체계

| 문서 | 역할 |
|------|------|
| `DECISION_LOG.md` | 아키텍처 결정 이력 |
| `FUTURE_ROADMAP.md` | v2.2~v3 개발 계획 |
| `docs/09_프로젝트_작업_지침_v2.1.docx` | 코딩 원칙 / 브랜치 전략 |
| `docs/01_LangGraph_상세_노드_설계서_v2.1.docx` | 노드 설계 명세 |
