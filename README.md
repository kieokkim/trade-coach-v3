# TradeCoach v2.3

AI 기반 트레이딩 복기 코치

## 한 줄 소개

Bybit 거래내역을 자동 분석하고 ICT 이론 기반으로
반복 실수와 행동 패턴을 교정하는 AI 복기 코치.
"왜 같은 실수를 반복하는가"에 집중합니다.

---

## 왜 만들었나

유튜브로 트레이딩을 독학하면서 한 가지 문제를 발견했습니다.
혼자 공부하면 배울 수 있지만, 내가 제대로 하고 있는지
피드백해줄 사람이 없습니다.

ICT(Inner Circle Trader) 기술적 분석은 감이 아니라
근거에 의한 트레이딩을 강조합니다.
FVG, Order Block, 킬존 같은 개념들은
진입 근거를 명확히 설명할 수 있어야 제대로 된 트레이딩입니다.

> "왜 여기서 들어갔어?"
> "FVG가 있었고, 킬존이었고, OB 재테스트가 있었어."

ICT는 rule-based 분석이기 때문에 AI 코칭이 가능합니다.
TradeCoach는 이 아이디어에서 시작했습니다.

---

## 코칭의 관점에서

TradeCoach는 세 가지 질문에 답합니다.

**1. 지금 내 트레이딩 실력은?**
승률·수익률·손절 일관성을 수치가 아닌 행동 패턴으로 해석합니다.

**2. 그때 내 진입은 옳았나?**
진입 시점 캔들을 복원하고 A+ 채점으로
"구조는 맞았는데 킬존을 놓쳤다"처럼 구체적 피드백을 줍니다.

**3. 같은 실수를 반복하고 있나?**
세션마다 약점을 누적 추적하고
내일 당장 실행할 수 있는 규칙 1개를 제시합니다.

---

## 핵심 기능

| 기능 | 설명 |
|------|------|
| 거래내역 자동 분석 | Bybit API 수집 + KPI 4가지 (승률 / 수익률 / 수익금 / 손절 일관성) |
| 거래 복기 뷰어 | Kline API 캔들 복원 + FVG / OB / 추세선 rule-based 탐지 오버레이 |
| A+ 채점 | ICT 기반 5가지 기준 자동 채점 (구조진입 / 반등확인 / 추세정렬 / 킬존 / 손절규율) |
| 진입 근거 추론 | 캔들 + ICT 패턴 기반 LLM 자동 추론 |
| AI-as-Judge | 코칭 결과를 트레이딩 철학 5가지로 자동 검수 |
| 손절가/RR 분석 | 복기 뷰어에서 손절가 직접 입력 → RR 자동 계산 + 구조적 손절 위치 판단 |
| 포지션 사이징 | 고정 손실 기반 적정 수량 계산 (기본값 + 거래별 override) |
| 조기 청산 탐지 | 수익 거래 홀딩 시간이 손실 거래의 50% 미만이면 약점 태깅 |
| 세션 메모리 | SQLite 기반 약점 누적 추적 + 거래 태그 영구 저장 |
| 샘플 데이터 3종 | 초보 / 중급 / 고수 시나리오 (실제 Bybit 시장가 기반) |

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
| v2.3 | ✅ | 손절가/RR + 포지션 사이징 + 조기 청산 탐지 + 샘플 데이터 시장가 기반 재생성 |
| v3.0 | 🔜 | Market Scanner — 실시간 셋업 감지 + 알림 시스템 + 스타일 레이어 기초 |
| v4.0 | 🔜 | Trade Journal — 진입 시점 근거 기록 + 청산 감지 자동 복기 + 진입 의도 교차 검증 |

---

## 문서

- `DECISION_LOG.md`: 아키텍처 결정 이력
- `FUTURE_ROADMAP.md`: 개발 계획
- `docs/`: 상세 설계 문서
