# TradeCoach v2.2

AI 기반 트레이딩 복기 코치

## 한 줄 소개

Bybit 거래내역을 자동 분석하고 ICT 이론 기반으로
반복 실수와 행동 패턴을 교정하는 AI 복기 코치.
"왜 같은 실수를 반복하는가"에 집중합니다.

---

## 핵심 기능

| 기능 | 설명 |
|------|------|
| 거래내역 자동 분석 | Bybit API 수집 + KPI 4가지 (승률 / 수익률 / 수익금 / 손절 일관성) |
| 거래 복기 뷰어 | Kline API 캔들 복원 + FVG / OB / 추세선 rule-based 탐지 오버레이 |
| A+ 채점 | ICT 기반 5가지 기준 자동 채점 (구조진입 / 반등확인 / 추세정렬 / 킬존 / 손절규율) |
| 진입 근거 추론 | 캔들 + ICT 패턴 기반 LLM 자동 추론 |
| AI-as-Judge | 코칭 결과를 트레이딩 철학 5가지로 자동 검수 |
| 세션 메모리 | SQLite 기반 약점 누적 추적 + 거래 태그 영구 저장 |
| 샘플 데이터 3종 | 초보 / 중급 / 고수 트레이더 시나리오 |

---

## 데모 모드

API 키 없이 3가지 트레이더 시나리오로 즉시 체험 가능:

- 👶 **초보**: 감에 의존, 불규칙한 손절
- 🧑 **중급**: ICT 기초 이해, 감정적 진입 잔존
- 🏆 **고수**: ICT 심층 이해, 이성적 판단

---

## 설치 및 실행

```bash
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env   # API 키 입력 후 저장
uv run streamlit run streamlit_app.py
```

---

## 환경 변수

```env
OPENAI_API_KEY=sk-...
BYBIT_API_KEY=...        # 선택 (없으면 샘플 데이터)
BYBIT_API_SECRET=...     # 선택
LLM_PROVIDER=openai      # openai 또는 groq
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| AI 파이프라인 | LangGraph / LangChain / OpenAI GPT-4o-mini |
| 거래소 연동 | Bybit V5 API (pybit) |
| 프론트엔드 | Streamlit / Plotly |
| 저장소 | SQLite |
| 런타임 | Python 3.13 / uv |

---

## 프로젝트 구조

```
trade-coach-v3/
├── graph.py               # LangGraph 파이프라인
├── pages/                 # Streamlit 멀티페이지
│   ├── 1_api_input.py     # 시작 페이지
│   ├── 2_loading.py       # 로딩
│   └── 3_main.py          # 복기 뷰어 + 대시보드
├── nodes/                 # LangGraph 노드
├── ict/                   # ICT 탐지 (rule-based)
├── market/                # Kline API
├── data/                  # 샘플 데이터 + 사전 캔들
└── docs/                  # 설계 문서
```

---

## 개발 로드맵

| 버전 | 상태 | 내용 |
|------|------|------|
| v2.0 | ✅ | MVP — KPI 분석 + ICT 코칭 + 세션 메모리 |
| v2.1 | ✅ | 복기 뷰어 — Kline 캔들 + FVG/OB 탐지 |
| v2.2 | ✅ | A+ 채점 + 진입 근거 추론 + AI-as-Judge |
| v2.3 | 🔜 | Replay Coach — candle-by-candle 복기 |
| v3.0 | 🔜 | 기간별 대시보드 + 장기 패턴 분석 |

---

## 문서

- `DECISION_LOG.md`: 아키텍처 결정 이력
- `FUTURE_ROADMAP.md`: 개발 계획
- `docs/`: 상세 설계 문서
