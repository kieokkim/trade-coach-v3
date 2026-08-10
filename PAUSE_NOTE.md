# PAUSE_NOTE — TradeCoach 보류 스냅샷 (2026-08-10)

> **이 문서는 봉인된 스냅샷입니다. 작성 이후 갱신하지 않습니다.**
> 6개월 뒤 이 레포를 다시 열었을 때 "지금 뭘 어디까지 했고 왜 멈췄는지"를
> 이 문서 하나로 복원하는 게 목적. 아카이브되는 ONBOARDING.md/FUTURE_ROADMAP.md의
> 고유 내용(용어 표, 완료 기능 목록)도 여기로 흡수했으므로 그 두 문서는 참조 불필요.

---

## 1. 보류 사유 + 되살림 조건

**TC-D48 요약** (전문은 `DECISION_LOG.md` TC-D48 참조):

TradeCoach 코칭 제품을 보류하고, ICT 자동매매 프로젝트 쪽 모니터링 에이전트를
별도 제품으로 신규 착수하기로 결정. 근거 3가지:

1. 봇이 실행 주체가 되면 코칭 대상의 심리 편향이 0 — 제품 정의(행동·심리 코칭)의
   적용 대상 자체가 사라짐.
2. 봇 진입 조건이 고정(sweep→FVG∩OB + 4h bias + 롱 전용)이라 거래가 전부 동일
   셋업 유형 — A+ 스코어링 점수 분산이 안 생겨 A+/非A+ 성과 비교가 성립하지 않음.
3. Phase B(A+ 검증)는 사용자 거래 데이터가 필요하고 Phase D(외부 배포)는 반드시
   B 이후 — 사용자는 D에서 온다. B←D←B 데드락.

**되살림 조건 (둘 다 충족 시에만 재개):**
- (a) 외부 재량 트레이더 사용자 1명 확보
- (b) 역사 데이터 기반 A+ 스코어링 검증 통과 (백테스트 상위 집합에 스코어링을
  돌려 forward return 예측력 측정)

**참고:** TC-D47(MVP 범위 확정 — 3단계 완주 + Streamlit 프론트 실구현 + 실거래
1회 이상 시험가동)은 보류 이전 시점의 목표 기록. ICT를 다른 rule 스타일로
교체 가능한지 탐색은 post-MVP였고, 이제는 TC-D48로 프로젝트 자체가 보류돼
자동 무효.

---

## 2. 코드 상태 (재개 시 여기부터 읽을 것)

> ONBOARDING.md를 대체함. ONBOARDING.md는 v2.0 기준(quiz_nodes.py 존재,
> 10노드 흐름도)이라 v2.3 현재와 다름 — quiz는 TC-D20에서 제거됐고 실제
> 메인 그래프는 13노드. 이 섹션이 정확한 버전.

### 브랜치/버전
- `feature/replay-coach` = v2.3 (현재 HEAD)
- `main`에 아직 머지 안 됨

### 아키텍처 개요
앱은 **FastAPI 백엔드(`api/main.py`) + Streamlit 프론트(`pages/`)** 2프로세스
구조. Streamlit은 로직을 직접 import하지 않고 `localhost:8000` API를 호출한다
(`streamlit run streamlit_app.py` + `uv run python api/main.py` 둘 다 필요).

- **메인 그래프**(LangGraph, `graph.py`): `POST /analyze` → `graph.stream()`
  동기 실행. `pages/2_loading.py`가 호출.
- **복기 플로우**(그래프 아님, 별도 동기 실행): `POST /replay/candles`,
  `POST /replay/aplus` → `entry_reason_node()` 직접 함수 호출. `pages/3_main.py`가
  호출. 단, `replay_coach_node()`(LLM 복기 코멘트)는 API를 거치지 않고
  `pages/3_main.py`가 **직접 import해서 인프로세스로 호출** — 같은 복기 플로우
  안에서도 entry_reason_node는 API 경유, replay_coach_node는 직접 호출로 경로가
  다르다(설계 통일 안 됨, 알려진 비대칭이지 버그 아님).

### 메인 그래프 노드 (13개, 순서대로)
```
START
 → memory_load          # DB에서 과거 약점/이력/last_fetched_at 로드
 → new_data_check       # 새 체결 데이터 존재 여부 판단
   ├─[no_new]→ END
   └─[has_new]→ bybit_fetch → preprocess → journal_write
       → journal_analysis → performance_analysis → weakness_detect
         ├─[concept_not_found]→ fallback_classify → progress_compare
         └─[정상]────────────────────────────→ progress_compare
       → backtest_coach → coaching_judge → memory_save → END
```
라우팅 함수: `route_new_data`, `route_after_weakness`, `route_after_fallback`
(`graph.py`).

### 복기 플로우 (메인 그래프 밖, `api/main.py` + `pages/3_main.py`에서 별도 동기 실행)
```
get_candles (market/candles.py)
 → detect_fvg / detect_ob / detect_trendline (ict/*.py)
 → entry_reason_node (score_aplus + LLM 진입근거 추론, API 경유)
 → replay_coach_node (LLM 복기 코멘트, 직접 호출)
```
`entry_reason_node`는 내부에서 `nodes/stop_loss_node.py::analyze_stop_loss`를
호출.

### LLM 호출지점 6개 (전부 `nodes/`, `utils/llm_factory.py::get_llm` 경유)
| # | 함수 | 노드 | 소속 |
|---|------|------|------|
| 1 | `_generate_action_rule` | `journal_analysis_node` | 메인 그래프 |
| 2 | `_classify_tag` / `_handle_ict`(2단 호출) | `fallback_classify_node` | 메인 그래프 |
| 3 | `_get_coach_llm().invoke(...)` | `backtest_coach_node` | 메인 그래프 |
| 4 | `llm.invoke(...)` | `coaching_judge_node` | 메인 그래프 |
| 5 | `llm.invoke(...)` | `entry_reason_node` | 복기 플로우 |
| 6 | `_get_llm().invoke(...)` | `replay_coach_node` | 복기 플로우 |

(참고: `coaching_nodes.py::generate_setup_suggestion`도 LLM을 호출하지만 위 6개
노드와 달리 그래프/복기 플로우 어디에도 안 속한 애드혹 함수 — `pages/3_main.py`
Tab 3 "셋업 태깅 탭"에서 직접 호출. 총 LLM 호출 지점은 7곳이지만 "노드"로
셀 수 있는 건 6개.)

### 실제 파일 구조
```
trade-coach-v3/
├── graph.py                    # TradeCoachState + LangGraph 그래프 정의
├── config.py                   # KPI 경고 임계값 상수
├── db.py                       # SQLite 초기화 + get_db()
├── streamlit_app.py            # 진입 페이지 라우팅 (graph.invoke 직접 호출 안 함, 주석 처리됨)
├── final_notebook.ipynb        # QA 노트북 — 수정 금지
├── api/
│   └── main.py                 # FastAPI: /analyze, /replay/candles, /replay/aplus
├── nodes/                      # 메인 그래프 노드 + 복기 플로우 함수
│   ├── analysis_nodes.py       # journal_analysis_node, weakness_detect_node
│   ├── coaching_nodes.py       # backtest_coach_node, fallback_classify_node, generate_setup_suggestion
│   ├── coaching_judge_node.py  # coaching_judge_node (AI-as-Judge)
│   ├── entry_reason_node.py    # entry_reason_node, score_aplus (복기)
│   ├── fetch_nodes.py          # new_data_check_node, bybit_fetch_node
│   ├── journal_nodes.py        # journal_write_node (rule-based, LLM 없음)
│   ├── memory_nodes.py         # memory_save_node
│   ├── performance_nodes.py    # performance_analysis_node
│   ├── preprocess_nodes.py     # preprocess_node
│   ├── progress_compare_node.py# progress_compare_node
│   ├── replay_coach_node.py    # replay_coach_node (복기)
│   └── stop_loss_node.py       # analyze_stop_loss (entry_reason_node이 호출)
├── ict/                        # rule-based ICT 탐지
│   ├── fvg_detector.py / ob_detector.py / trend_detector.py
├── market/                     # 캔들 수집 (거래소 추상화)
│   ├── candles.py              # get_candles, CandleFetchError
│   ├── bybit_client.py / upbit_client.py / exchange_base.py
├── tools/                      # LangChain tool + RAG
│   ├── concept_tool.py / ict_rag.py / ict_search_text.py
├── utils/
│   ├── llm_factory.py          # get_llm(), LLM_PROVIDER 환경변수로 정적 분기
│   ├── api_safety.py / chart.py / constants.py / observability.py / styles.py
├── pages/                      # Streamlit 멀티페이지
│   ├── 1_api_input.py / 2_loading.py / 3_main.py
├── data/                       # 샘플 데이터(초보/중급/고수 3종) + 사전 캔들 + chroma_db
├── scripts/                    # eval/백필/샘플생성 스크립트
└── archive/                    # 이전 세션 산출물 보관 (nodes/data 구버전 등)
```

### TradeCoachState 핵심 필드 (`graph.py:22-53`, 총 30개 중 발췌)
| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | str | 세션 식별자 |
| `raw_trades` | list | Bybit/Upbit API 원본 체결 목록 |
| `journal_entries` | list | 거래별 매매일지 (인메모리 반환값 — DB 테이블과 동명이인, 아래 참조) |
| `stats` | dict | 승률/평균수익률/기대값/손절일관성 |
| `weaknesses` / `past_weaknesses` | list | 현재/과거 약점 태그 |
| `setup_analysis` | dict | 셋업별 수익률 |
| `action_rule` | str | 내일 실행할 규칙 1개 |
| `avg_return_rate` / `expected_value` / `loss_consistency` | float | 대체 KPI 3종(TC-D6) |
| `concept_not_found` | bool | fallback 라우팅 플래그 |
| `fallback_type` | str | `'ict'` \| `'psychology'` \| `'pattern'` |
| `coaching_output` | str | ICT 코칭 결과 텍스트 |
| `judge_result` / `judge_passed` / `judge_scores` | — | AI-as-Judge 검수 결과 |
| `exchange` | str | `'Bybit'` \| `'Upbit'` |
| `sample_mode` | str | `'beginner'`\|`'intermediate'`\|`'expert'` 등 |
| `progress_comparison` | dict | 세션 간 약점 변화 비교 |

전체 필드는 `graph.py:22-53` (`TradeCoachState` TypedDict) 참조.

### DB 테이블 (SQLite `tradecoach.db`, `db.py::init_db`)
- `weaknesses` — 세션별 약점 태그 누적
- `trade_history` — 세션별 KPI 스냅샷
- `quiz_results` — **고아 테이블.** TC-D20에서 퀴즈 기능 자체는 제거했지만
  스키마 정리는 범위 밖이라 남음. 읽기/쓰기 코드 전무, 매 init마다 빈 테이블만
  계속 생성됨.
- `performance_snapshots` — 성과 요약 스냅샷
- `user_settings` — key-value 설정
- `trade_tags` — 거래별 ICT 태그 + 포지션 사이징(고정손실/이상수량/실제수량/손절가)
- `journal_entries` — 거래별 일지(체결가/청산가/손절규율 판정용). **STEP2-C
  (2026-07-24)에서 신규 생성됨.** 그 전에는 `ALTER TABLE ... ADD COLUMN`만 있고
  `CREATE TABLE`이 없어 매 실행마다 조용히 실패하는 유령 테이블이었음
  (TC-D46/STEP2-C 경위는 DEVLOG.md 참조). 이름이 위 state 필드 `journal_entries`
  (인메모리)와 같아서 최초 혼동의 원인이었음 — 그래프 state 필드와 SQL 테이블은
  서로 다른 실체이니 혼동 주의.

---

## 3. 완료 기능 목록 (v2.0~v2.3, FUTURE_ROADMAP.md에서 흡수)

- **v2.0** — Bybit API 자동 수집(샘플 폴백), KPI 4가지, ICT 개념 25개 사전 기반
  약점 코칭, SQLite 세션 메모리
- **v2.1** — 거래 복기 뷰어(Trade Context Viewer): Kline 캔들 복원, FVG
  rule-based 탐지, LLM 복기 코멘트
- **v2.2** — OB/Liquidity Sweep/MSS 탐지, A+ 채점 5가지 기준(rule-based),
  캔들 기반 진입 근거 자동 추론, AI-as-Judge 코칭 검수, 롱/숏 방향 개념,
  ICT 기반 약점 태깅(종목명 제거), 샘플 데이터 3종, journal_write rule-based 전환
- **v2.3** — 손절가/RR 사용자 입력 + DB 영구저장, 포지션 사이징(기본값+거래별
  override), 조기 청산 패턴 탐지, execPrice 캔들 범위 검증+슬리피지 경고, 샘플
  데이터 실시장가 기반 재생성, 퀴즈 제거, A+ 채점 수동 실행 전환
- **STEP1/STEP2 (v2.3 이후, 브랜치 내 후속)** — fallback_classify try/except
  방어, 캔들 실패/빈데이터 구분(Bybit만), 복기뷰어 존 렌더링 클리핑,
  journal_entries 실제 영속화 + 손절규율 3치(pass/fail/unscored)화

**보류된 계획(v3.0~v5.0):** Market Scanner / Trade Journal / Personal Coach —
TC-D48로 전부 보류. 상세는 과거 `FUTURE_ROADMAP.md`(git history) 참조.

---

## 4. 용어 사용 기준 (다른 문서에 없는 고유 내용, FUTURE_ROADMAP.md에서 흡수)

- **"Replay" 단독 사용 금지.** 실제는 정적 캔들 복원(Trade Context Viewer) —
  TradingView Bar Replay 수준의 candle-by-candle 인터랙션이 아님 (TC-D2).
- **"자동 감지" 과장 금지.** 기본 ICT 패턴(FVG/OB/추세선) rule 탐지가 정확한
  표현 — "ICT 패턴 자동 감지"처럼 포괄적으로 쓰지 말 것 (TC-D3).
- **"A+ 정확도 58%" 사용 금지.** 샘플 생성 스크립트가 자체 부여한 라벨과 rule
  채점을 비교한 순환 검증이라 무효 (TC-D39/TC-D40 — DECISION_LOG.md 참조).
- **"멀티 프로바이더 아키텍처" 과장 금지.** `utils/llm_factory.py`는
  `LLM_PROVIDER` 환경변수로 배포시점에 openai/groq 중 정적으로 하나만 선택하는
  구조 — 런타임 동적 라우팅이 아님.

---

## 5. 마지막 검증 상태 (재개 시 최우선 확인)

**STEP2-C**(journal_entries 영속화 + 손절규율 3치)는 **스크래치 DB 로직
검증만 완료.** `db.init_db()` 후 `journal_write_node`/`score_aplus`를 직접
호출하는 방식으로 (1)중복 삽입 방지 (2)데이터 0건→None (3)손절 1건→True
(4)손절 3건→False (5)다른 session_id→다시 None, 4가지 분기를 확인함.

**실 API 키 기반 live e2e는 미실행.** 재개 시 가장 먼저 할 일:
1. `.env`에 실 `BYBIT_API_KEY`/`BYBIT_API_SECRET` 설정
2. `api/main.py` 기동 → `/analyze` 풀 파이프라인 1회 실행
3. `tradecoach.db`에서 `SELECT * FROM journal_entries` 로 실거래 기반 삽입 확인
4. `/replay/aplus`로 해당 거래 A+ 채점 재확인 (stop_discipline이 None이 아니라
   실제 True/False로 나오는지)

---

## 6. 알려진 결함 (동결 — 재개 전까지 고치지 않음)

### 결함 A: Upbit 캔들 경로 실패/빈데이터 미구분

**발견:** STEP2a 세션(2026-07-23) 재현 확인 중 `market/upbit_client.py`의
`fetch_candles`가 여전히 예외를 삼켜 `[]`를 반환하는 것을 확인.

**원인:** 같은 세션의 Fix B(결함1/9 — 실패/빈데이터 구분) 범위를
`market/bybit_client.py`로만 한정했음. Upbit 클라이언트는 손대지 않음.

**조치:** 동결. 고치지 않음 — 지금 고쳐도 실 Upbit 계정으로 live 검증할
경로가 없어 (STEP2-C와 같은 이유로) 확인 불가능.

**결과:** `exchange="Upbit"`로 캔들 조회 시 API 실패와 진짜 빈데이터가
여전히 동일하게 `[]`로 뭉뚱그려짐 — 결함1/9(더미 캔들 자동대체로 "실패=정상"
혼동)가 Upbit 경로에서만 재발 가능. Bybit 경로는 STEP2a에서 수정 완료
(CandleFetchError 분리).

### 결함 B: quiz_results 고아 테이블

**발견:** 이 문서 작성 중 `db.py::init_db`가 `quiz_results` 테이블/인덱스를
여전히 생성하는 것을 확인. 레포 전체에 이 테이블을 읽거나 쓰는 코드가 없음.

**원인:** TC-D20(퀴즈 기능 제거)의 범위가 `quiz_generate_node`와 UI 제거였고,
DB 스키마 정리는 범위 밖으로 남아 반영 안 됨.

**조치:** 동결. 고치지 않음 — 삭제해도 회귀 위험은 없지만 이번 세션(PAUSE_NOTE
작성) 범위 밖.

**결과:** 실질적 영향 없음(빈 테이블만 계속 생성됨). 재개 시 또는 다음
레포정리 세션에서 `DROP TABLE` 후보.
