# TradeCoach — Decision Log

아키텍처 결정 이력. "왜 이렇게 설계했는가"를 기록합니다.

---

## 2026-05-14

### Decision 1: 별도 레포 분리 전략
**결정:** v2.1+ 기능을 `trade-coach-replay` 별도 레포에서 개발

**이유:**
- v2.0 안정성 유지 필요 (Nomad Coders 과제 제출 완료 버전)
- Kline API, plotly, ict/ 모듈 추가로 구조 대폭 변경 예상
- LangGraph 상태 구조가 커질수록 복잡도 급증

**트레이드오프:**
- 코드 중복 발생 가능 (nodes/, tools/ 등)
- 두 레포 간 버그 픽스 동기화 필요

**결론:** 실험 실패 시 v2.0 롤백 가능, 포트폴리오 정리 용이

---

### Decision 2: "Replay" 표현 범위 제한
**결정:** 현 단계에서 "Replay"를 "Trade Context Viewer"로 표현 제한

**이유:**
- 트레이더가 기대하는 Replay = TradingView Bar Replay 수준
  (candle-by-candle 진행, 사용자 직접 진입, rewind/play)
- 실제 v2.1 구현 = 진입 시점 캔들 복원 + 정적 차트 + LLM 코멘트
- 기대치 과잉 설정은 데모/포트폴리오에서 역효과

**용어 정리:**
| 단계 | 표현 |
|------|------|
| v2.1 | Trade Context Viewer (거래 복기 뷰어) |
| v2.3 | Replay Coach (candle-by-candle 복기) |
| 문서/README | "Replay" 단독 사용 금지 |

---

### Decision 3: ICT 패턴 탐지 범위 제한
**결정:** v2.1에서는 FVG 중심 기본 탐지만 구현

**이유:**
- 사용자 오해 가능 범위: OB / MSS / Liquidity Sweep / SMT / Breaker
- 실제 v2.1 구현: FVG rule-based 탐지만
- 과잉 약속은 포트폴리오 신뢰도 하락 원인

**표현 기준:**
| 단계 | 표현 |
|------|------|
| v2.1 | 기본 ICT 패턴(FVG 중심) 탐지 |
| v2.2 | ICT Detector (FVG/OB/MSS/Liquidity) |
| 문서 | "ICT 패턴 자동 감지" 단독 사용 금지 |

**원칙:** rule-based 먼저, LLM은 설명/코칭 역할만

---

### Decision 4: 셋업 라이브러리 범위 제한
**결정:** v2.1에서 "셋업 태깅 탭"으로 시작, A+ Setup Memory는 v3.0

**이유:**
- 진짜 셋업 라이브러리 = 패턴 임베딩 + 좋은 거래 clustering + 장기 메모리 평가
- v2.1에서 구현 불가 (인프라 미비)
- 과잉 약속 방지

**단계 구분:**
| 단계 | 기능 |
|------|------|
| v2.1 | 셋업 태깅 탭 (익절/손절 패턴 분류 기초) |
| v3.0 | A+ Setup Memory (유사도 분석, 장기 추적) |

---

### Decision 5: 자동 매매 미구현
**결정:** TradeCoach는 자동 매매 기능을 구현하지 않음

**이유:**
- 목적이 "트레이더 행동 교정"이지 "자동화"가 아님
- 자동 매매 연동은 법적 리스크 존재
- Read-Only API 권한으로 충분한 서비스 구현 가능

**결론:** 영구 제외

---

### Decision 6: 손익비(R:R) 대신 대체 KPI
**결정:** avg_rr 제거, 수익률/기대값/손절일관성으로 대체

**이유:**
- Bybit /v5/execution/list에 손절가(stopLoss) 데이터 없음
- exec_fee 기반 R:R 계산은 의미 없는 수치 (수익/수수료)
- 실제 데이터로 계산 가능한 KPI로 대체

**대체 KPI:**
| KPI | 계산 | 의미 |
|-----|------|------|
| avg_return_rate | closedPnl/execValue×100 | 투자금 대비 수익률 |
| expected_value | (승률×평균수익) - (패율×평균손실) | 전략 장기 수익성 |
| loss_consistency | 손실 표준편차/평균손실 | 손절 규율 |

---

## 2026-05-14 (Day 5 완료)

### Decision 7: 셋업 태깅 탭 데이터 소스 우선순위
**결정:** setup_analysis(그래프 상태) > journal_entries 파생 > raw_trades 파생 순으로 폴백

**이유:**
- bybit 모드에서는 preprocess_node가 symbol → setup 파생 → setup_analysis 존재
- journal 모드(CSV 직접 입력)도 setup 컬럼 있으면 setup_analysis 존재
- 두 경우 모두 setup_analysis가 가장 신뢰할 수 있는 데이터
- journal_entries 파생은 rr 필드 기반이므로 정확도 낮음 (폴백만 사용)

**트레이드오프:**
- 샘플 데이터에서 setup_analysis 비어있으면 symbol 기준 그룹화로 대체
- 셋업 이름이 BTC/ETH/SOL 등 심볼명으로 표시될 수 있음

---

### Decision 8: LLM 호출 위치 원칙 확정
**결정:** 모든 LLM 호출은 nodes/ 파일에서만. pages/는 node 함수를 호출만 함

**이유:**
- 테스트 가능성: nodes/ 단위로 dotenv 로드 후 독립 테스트 가능
- 재사용성: 같은 LLM 로직을 다른 페이지/그래프에서 호출 가능
- 책임 분리: UI 코드(pages/)와 비즈니스 로직(nodes/)을 분리

**적용 범위:**
| 페이지 | 호출 노드 |
|--------|-----------|
| Tab 2 복기 뷰어 | nodes/replay_coach_node.py |
| Tab 3 개선 제안 | nodes/coaching_nodes.generate_setup_suggestion |

---

### Decision 9: session_state 캐싱 정책
**결정:** Kline API 호출 결과는 `f"replay_{orderId}"` 키로 캐싱

**이유:**
- Bybit Kline API는 무료지만 반복 호출 시 UX 저하 (1~2초 지연)
- 같은 거래 재선택 시 API 재호출 불필요
- session_state는 브라우저 탭 단위로 유효 → 앱 재시작 시 자동 초기화

**범위:** Tab 2 복기 뷰어(`replay_` prefix), Tab 3 차트 태깅(`tag_candles_` prefix)

---

### Decision 10: 거짓돌파 탐지 v2.2로 연기
**결정:** 현재 브랜치(feature/replay-foundation)에서 거짓돌파(Fakeout) + 함정(Bull/Bear Trap) 탐지 미구현

**이유:**
- 거짓돌파는 직전 고점/저점 돌파 후 되돌림을 실시간으로 판단해야 함
- 봉 확정 여부 + 거래량 데이터 필요 (현재 Kline에 volume 있지만 로직 복잡)
- 오탐율이 높아 신뢰도 낮은 탐지는 오히려 코칭 품질 저하

**v2.2에서:** `ict/fakeout_detector.py` 구현 예정

---

### Decision 11: OB/추세선/채널 탐지 현재 브랜치 구현
**결정:** `ict/ob_detector.py`, `ict/trend_detector.py`를 `feature/replay-foundation`에서 구현

**이유:**
- OB는 3캔들 패턴으로 rule-based 구현 범위 내
- 추세선/채널은 고점/저점 연결로 단순 구현 가능
- 두 패턴 모두 FVG와 함께 복기 뷰어에서 즉시 활용 가능

**트레이드오프:**
- 오탐 가능성 있음 (캔들 수가 적으면 추세선 신뢰도 낮음)
- limit=50 캔들 기준, 데이터 부족 시 None 반환으로 처리

---

### Decision 12: 거짓돌파+함정 탐지 v2.2로 연기
**결정:** Fakeout/Bull Trap/Bear Trap 탐지를 현재 브랜치에서 미구현

**이유:**
- 봉 확정 여부 + 직전 고점/저점 비교 + 거래량 검증 필요
- 오탐율이 높아 신뢰도 낮은 탐지는 코칭 품질 저하 우려
- v2.2 `feature/ict-detector-engine`에서 구현 예정

---

## 2026-05-15

### Decision 13: v3.0 A+ Setup Memory 잠정 보류
**결정:** v3.0으로 계획했던 임베딩 기반 A+ Setup Memory를 잠정 보류

**이유:**
- 임베딩 기반 유사도 검색, 거래 클러스터링은 현재 SQLite 구조로 구현 한계
- v2.2에서 rule-based 채점 방식의 A+ 코칭으로 핵심 가치를 먼저 구현

**대체:** v2.2에서 A+ 셋업 채점 (rule-based 기준 + LLM 피드백)으로 구현

---

### Decision 14: 캔들 기반 진입 근거 자동 추론
**결정:** 수동 셋업 태깅 대신 캔들 패턴 + ICT 감지 결과를 LLM에 넘겨 진입 근거 자동 추론

**이유:**
- 사용자가 직접 태그를 달지 않아도 복기 코칭이 가능해야 함
- FVG/OB/추세선 감지 결과가 이미 있어서 LLM 추론의 입력으로 활용 가능

**구현:** replay_coach_node 확장 또는 별도 entry_reason_node 추가

**트레이드오프:** LLM 추론이라 오판 가능성 있음 → 사용자가 결과를 확인/수정할 수 있는 UI 필요

---

### Decision 15: 샘플 캔들 데이터 사전 생성
**결정:** data/sample_candles.json 사전 생성, 샘플 모드에서 API 호출 없이 작동

**이유:**
- 샘플 데이터의 execTime이 가상의 시점이라 Bybit Kline API 호출 시 빈 결과 반환
- Streamlit Cloud 환경에서 외부 API 호출 실패 시 앱 크래시 발생

**구현:** orderId를 키로 캔들 50개를 값으로 저장, market/candles.py에서 sample_mode 여부에 따라 분기

---

### Decision 16: 매매일지 "추론 불가" 개선
**결정:** journal_write_node 프롬프트를 캔들 + ICT 패턴 데이터 기반 추론으로 변경

**이유:**
- 기존 방식: 거래내역만 보고 진입 근거 추론 → 데이터 부족으로 "추론 불가" 반복
- 개선 방향: 캔들 데이터와 ICT 패턴 확보 후 LLM이 추론

**단기 수정:** 데이터 없을 때 "추론 불가" 대신 체결가/시간대/손익 팩트만 서술

**장기 수정:** Decision 14와 연계하여 캔들 기반 추론으로 완전 대체 (v2.2)

---

### Decision 17: A+ 채점 기준 ICT 이론 기반으로 재설계
**결정:** 기존 4가지 기준에서 ICT 이론 기반 5가지로 교체

**제거된 기준:**
- 손절 위치 (has_structure와 중복, Bybit API에 손절가 데이터 없음)
- 감정 없음 (orderId random- 체크는 샘플 데이터에서만 작동)

**새 기준:**
| # | 기준 | 로직 |
|---|------|------|
| 1 | 구조 진입 | 진입가가 FVG/OB 구간 내 |
| 2 | 반등 확인 | 직전 2캔들 저점이 구간 하단 ±0.5% 내 |
| 3 | 추세 정렬 | direction과 channel_type 일치 |
| 4 | 킬존 | UTC 02-05(런던) 또는 07-10(뉴욕) 세션 |
| 5 | 손절 규율 | 당일 journal_entries 손절 3회 미만 |

---

### Decision 18: AI-as-Judge 패턴 도입
**결정:** backtest_coach_node 출력을 별도 LLM이 트레이딩 철학 5가지로 검수

**위치:** `backtest_coach → coaching_judge → quiz_generate`

**이유:**
- 코칭 품질 자동 검증 + Option C(AI-as-judge) 과제 요건 충족
- temperature=0 고정으로 일관된 판정
- judge 실패해도 파이프라인 중단 없음 (사용자에게 보완 제안만 표시)

---

### Decision 19: coaching_nodes.py direction 미추가
**결정:** `backtest_coach_node`, `generate_setup_suggestion`은 direction 컨텍스트 추가 불필요

**이유:**
- 포트폴리오 레벨 데이터(weaknesses, setup_analysis)를 입력받으며 per-trade `trade` dict가 없어 direction 추가 위치 없음
- `replay_coach_node`와 `entry_reason_node`는 `trade` dict를 직접 받으므로 해당 파일에만 적용

---

## 2026-05-28

### Decision 20: 퀴즈 기능 제거
**결정:** `quiz_generate_node` 및 관련 UI 전체 제거

**이유:**
- 퀴즈는 교육 플랫폼 기능이지 복기 코치 기능이 아님
- TradeCoach의 본질은 "거래 복기를 통한 반복 실수 교정"
- 구색 맞추기 기능은 핵심 집중도를 낮춤

**영향:**
- `graph.py`에서 quiz_generate 노드/엣지 제거
- `pages/3_main.py` 퀴즈 섹션 제거

---

### Decision 21: 손절가/RR 사용자 입력 기능 추가
**결정:** 복기 뷰어에서 손절가를 직접 입력받아 RR 계산

**이유:**
- Bybit API에 손절가 데이터 없음
- 손절 위치는 진입 근거 다음으로 코칭에서 가장 중요한 요소
- 사용자 입력 기반으로 구조적 손절 위치 판단 가능

**구현:**
- 복기 뷰어 내 손절가 입력 필드
- RR = (청산가 - 진입가) / (진입가 - 손절가) 자동 계산
- 손절이 FVG/OB 하단 바깥인지 rule-based 판단
- A+ 채점 기준 3번(손절 위치) 실제 데이터로 교체

---

### Decision 22: 조기 청산 패턴 탐지 추가
**결정:** 수익 거래에서 조기 청산 여부를 탐지

**이유:**
- "수익이 나도 너무 빨리 닫는" 패턴이 장기 수익에 악영향
- 홀딩 시간 + 수익률 조합으로 탐지 가능

**구현:** `weakness_detect_node`에 early_exit 규칙 추가

---

### Decision 23: v2.3 보류 항목
**결정:** 아래 항목은 v3.0으로 연기
- MSS/Liquidity Sweep 탐지
- 상위 타임프레임 편향 분석
- Next.js 프론트엔드 전환

**이유:** v2.3은 복기 뷰어 완성도에 집중

---

### Decision 24: A+ 채점 수동 실행 전환
**결정:** 복기 시작 시 자동 실행 → 손절가 입력 후 버튼으로 수동 실행

**이유:**
- 손절가 없이 채점하면 stop_position 기준이 의미 없음
- 사용자가 데이터를 충분히 입력한 후 채점하는 것이 코칭 품질 향상
- cache_key에 stop_price + fixed_loss 포함해서 재채점 가능

**구현:** "🏆 A+ 채점 시작" 버튼으로 명시적 실행, `cache_key_aplus = f"aplus_{order_id}_{stop_price}_{fixed_loss}"`

---

### Decision 25: 포지션 사이징 계산기 추가
**결정:** 복기 뷰어에 고정 손실 기반 적정 수량 계산기 추가

**공식:** 적정 수량 = 고정 손실 금액 / |진입가 - 손절가|

**이유:**
- 리스크 관리에서 손절 위치만큼 포지션 크기가 중요
- Bybit API에 포지션 크기 기준 데이터 없어서 사용자 입력으로 보완
- 실제/적정 비율이 2배 이상이면 과다 포지션으로 약점 태깅

**구현:** 복기 뷰어 포지션 사이징 섹션 + `포지션_과다` 약점 규칙 + trade_tags DB 저장

---

### Decision 26: 조기 청산 패턴 탐지 추가
**결정:** 수익 거래 평균 홀딩 시간이 손실 거래의 50% 미만이면 탐지

**이유:**
- 수익은 짧게, 손실은 길게 들고 있는 패턴이 장기 수익에 악영향
- 홀딩 시간 데이터로 행동 패턴 객관화 가능

**구현:** `_has_early_exit()` + `조기청산_패턴` 규칙, journal_write_node에서 buy/sell 페어링으로 execTime(진입)/exitTime(청산) 파생

---

### Decision 27: execPrice 캔들 범위 검증 도입
**결정:** `validate_price_in_candle()` 함수로 execPrice가 해당 캔들 범위 안에 있는지 검증

**이유:**
- 실제 Bybit API 거래내역 연동 시 에이전트 신뢰도 핵심
- 슬리피지 발생 시 사용자에게 명시적 경고
- 샘플/실제 데이터 모두 동일한 검증 로직 적용

**트레이드오프:**
- 샘플 데이터는 클램핑으로 범위 내 강제 설정
- 실제 데이터는 클램핑 없이 경고만 표시 (원본 유지)
- Sell은 Sell 시점 캔들 기준으로 별도 검증

**구현:** `market/candles.py`에 `normalize_exec_time()` + `validate_price_in_candle()` 추가, 복기 차트 후 경고 표시

---

### Decision 28: 포지션 사이징 레이어 구조
**결정:** 기본값(전체) + 거래별 override 2단계 구조

**공식:** 적정 수량 = 고정 손실 금액 / |진입가 - 손절가|

**이유:**
- ICT 철학: 매 거래 손실금액 사전 고정 → 기본값 설정이 정석
- 입문자는 거래별로 다르게 실험 → override 필요
- user_settings 테이블로 기본값 영구 저장

**UI 위치:** 복기 뷰어 상위 expander → 항상 접근 가능

**구현:** `db.py`에 `user_settings` 테이블 + `get_setting/save_setting`, trade_tags에 `fixed_loss/ideal_qty/actual_qty` 컬럼

---

### Decision 29: 샘플 데이터 실제 시장가 기반 재생성
**결정:** execPrice를 실제 Bybit Kline API 기반으로 하드픽스

**이유:**
- 시간대와 가격 미스매칭 시 에이전트 신뢰도 저하
- Buy: 해당 캔들 open 가격 기준
- Sell: Buy execPrice + closedPnl / orderQty 역산, Sell 시점 캔들 범위로 클램핑
- closedPnl도 실제 클램핑된 가격 기준으로 재계산

**구현:** `scripts/generate_sample_trades.py` (Buy/Sell 각각 Bybit API 조회 + 클램핑), `scripts/generate_sample_candles.py` (캔들 재생성)

---

### Decision 30: A+ 채점 Eval 검증 - look-ahead bias 발견 및 수정
**결정:** structure_entry 판정에 진입 시점 이전 구조만 사용하도록 제한

**발견 과정:**
1. 샘플 데이터 orderId 패턴(fvg-/ob-/sweep-/random-)을 Ground Truth로 활용한 자동 검증 스크립트 작성
2. 1차 검증: random 거래 81%가 "구조 진입"으로 오판정 (정확도 19%)
3. 원인: FVG/OB 탐지가 진입 시점 이후 구조까지 포함 (데이터 누수)
4. 1차 수정 후 재검증: random 개선(19→33%)했으나 fvg/ob 회귀(100→71%, 67%)
5. 2차 원인: 검증 함수 자체가 "구조 존재"와 "가격이 구조 안"을 혼동
6. 2차 수정: 가격 포함 여부까지 검증하도록 보정
7. 최종 결과: fvg 100%, ob 100% 회복, 전체 정확도 47.2%→58.3%

**잔여 이슈:**
- random 정확도 33% (개선 후 그대로) — 버그가 아니라 실제 시장의 자연적 FVG/OB 발생 노이즈로 판단
- sweep 패턴 50% — 별도 검증 로직 필요 (Liquidity Sweep 미구현 상태)

**구현:** `nodes/entry_reason_node.py` (fvg_before/ob_before 필터), `scripts/generate_sample_candles.py` (구조 검증+주입), `scripts/eval_aplus_validation.py` (자동 검증)

---

### Decision 31: 멀티모델 비교 평가 - Groq llama-3.3-70b 채택 검토
**결정:** entry_reason_node 비교 결과, Groq(llama-3.3-70b-versatile)가 OpenAI(gpt-4o-mini) 대비 응답속도 2.5배, 품질지표(기준언급) 우위 확인

**검증 방법:**
entry_reason_node를 그대로 재사용해서 LLM_PROVIDER만 교체. expert 샘플 5건에 대해 응답시간/기준언급수/길이/루프여부 측정.

**결과 (5건 기준):**
- 응답시간: OpenAI 2.82s / Groq 1.13s
- 기준 언급(구조/추세/킬존 등 7개 중): OpenAI 4.6 / Groq 5.4
- 평균 길이: OpenAI 256자 / Groq 309자
- 루프/너무짧음: 둘 다 0건

**중요 단서:**
이전(v2.2~v2.3) journal_write_node에서 Groq의 작은 모델(llama-3.1-8b-instant)은 rate limit + 루프 버그가 있었음. 지금 결과는 더 큰 모델(llama-3.3-70b-versatile) 기준이라 "Groq가 항상 우수하다"가 아니라 "모델 크기가 품질을 좌우한다"는 결론이 더 정확함.

**한계:**
표본 5건은 파일럿 수준. 응답시간은 네트워크 상태에 따라 변동 가능. 통계적 확정을 위해선 표본 확대 필요.

**향후 결정:**
- entry_reason_node, backtest_coach 등 task="complex" 노드는 Groq llama-3.3-70b를 기본값으로 전환 검토
- journal_write 등 task="default" 노드는 기존 작은 모델 유지 (단순 팩트 서술이라 모델 크기 영향 적음)

**구현:** `scripts/eval_multimodel_comparison.py` (자동 비교 스크립트)

---

### Decision 32: Bybit API 권한 분리 - read-only 강제
**결정:** API 키 입력 시 get_api_key_information()으로 권한 확인, 거래 관련 권한(Order/Trade/Withdraw) 감지 시 경고 + 사용자 확인 요구

**검증:** 실제 본인 .env 키로 테스트한 결과 7개 거래 권한(ContractTrade:Order, Spot:SpotTrade, Options:OptionsTrade, DerivativesTrade, FiatP2POrder 등) 정확히 탐지됨. 이는 실제로 분석 전용 용도에 맞지 않는 키였음을 발견한 것으로, 보안 설계의 실효성을 그 자리에서 증명함.

**구현:** `utils/api_safety.py`, `pages/1_api_input.py`, `scripts/test_api_safety.py`

---

### Decision 33: RAG 임베딩 모델 - bge-m3 채택
**결정:** ICT 개념 검색 임베딩 모델을 paraphrase-multilingual-MiniLM-L12-v2 → BAAI/bge-m3로 교체

**발견 과정:**
1. 1차 인덱싱(MiniLM) 직후 모든 질의가 "프리미엄_디스카운트"로 독점됨
2. 가설 1: 데이터 노이즈(ICT개념+약점태그 혼재) → 분리해도 해결 안 됨
3. 가설 2: 한국어보다 영어 검색 텍스트가 나을 것 → A/B 검증 결과 한국어 0% / 영어 0%, 둘 다 실패 (언어는 원인이 아니었음)
4. 진짜 원인: MiniLM 모델 자체가 ICT 도메인 한국어 검색에 부적합
5. 모델 3종 비교(MiniLM/e5-large/bge-m3) → bge-m3가 정확도 100%, 속도도 e5-large보다 2.4배 빠름

**결과 (5건 기준):**
| 모델 | 정확도 | 로딩 시간 |
|------|--------|-----------|
| MiniLM (기존) | 0% | 10.4s |
| e5-large | 80% | 183.8s |
| **bge-m3 (채택)** | **100%** | **75.9s** |

**교훈:**
"이게 원인일 것이다"는 가설을 순서대로 검증하면서 틀린 가설(데이터 노이즈, 언어 문제)을 하나씩 제거하고 진짜 원인(모델 선택)에 도달함. RAG 품질 문제는 데이터/프롬프트보다 임베딩 모델 선택이 핵심일 수 있음을 확인.

**구현:** `tools/ict_rag.py` (_EMBED_MODEL), `scripts/eval_rag_lang_comparison.py`, `scripts/eval_rag_model_comparison.py`

---

## 2026-06-23

### Decision 34: 거래소 추상화 레이어 + Upbit 지원 추가
**결정:** ExchangeClient 추상 인터페이스(fetch_trades, fetch_candles, check_permissions)를 도입해 Bybit 전용 구조를 거래소 독립적으로 일반화하고 Upbit 지원 추가

**구현:**
- `market/exchange_base.py` — ABC 인터페이스
- `market/bybit_client.py` — 기존 Bybit 로직 캡슐화
- `market/upbit_client.py` — Upbit REST API 연동, 응답을 Bybit V5 구조로 정규화해서 기존 파이프라인 재사용
- `nodes/fetch_nodes.py` — bybit_fetch_node 함수명 유지하되 내부에서 exchange 상태값 기준으로 클라이언트 분기 (graph.py 노드 등록 변경 없이 회귀 위험 최소화)
- `utils/api_safety.py` — BybitClient.check_permissions()로 위임

**Upbit 권한 확인 방식의 차이:**
Bybit은 API로 권한 조회가 가능하지만 Upbit은 키 발급 시점에 권한이 고정되는 구조라 별도 조회 API가 없음. 대신 발급 페이지에서 직접 확인하라는 안내 문구로 대체.

**검증:** 거래소 추상화 도입 후 Bybit 샘플 모드 회귀 테스트 (beginner 12쌍 거래 정상 조회) 통과.

### Decision 35: FastAPI 백엔드 분리
**결정:** Streamlit이 LangGraph 파이프라인을 직접 호출하던 구조를 FastAPI 엔드포인트로 분리. 프론트엔드/백엔드 책임 경계 명확화.

**구현:**
- `api/main.py` — `/health`, `/analyze`, `/replay/candles`, `/replay/aplus`
- `pages/2_loading.py`, `pages/3_main.py` — requests 기반 API 클라이언트로 전환
- `replay_coach_node`, `validate_price_in_candle`은 API화하지 않고 직접 호출 유지 (자주 쓰이는 핵심 흐름만 분리, 과도한 추상화 지양)

**트레이드오프 — 실시간 노드 로그 포기:**
graph.stream()의 노드별 실시간 UI 업데이트를 API 단순 호출(동기, 일괄 응답)로 전환하면서 실시간성을 의도적으로 희생. 이유: 채용 시장에서 "프론트/백엔드 분리 설계 능력"이 "실시간 UX"보다 더 직접적인 차별화 신호로 판단. 필요 시 SSE/WebSocket으로 향후 업그레이드 가능하도록 구조 분리만 먼저 확보.

**부수 효과:**
os.environ 조작(TC_SAMPLE_FILE, BYBIT_API_KEY 임시 제거/복원) 코드 완전 제거. 상태 관리 책임이 Streamlit에서 API 서버로 명확히 이전됨.

**검증:** `scripts/test_api_integration.py`로 4개 엔드포인트 전체 통합 테스트 통과 (13노드/24거래, 50캔들/8FVG/17OB, A+ 4/5).

### Decision 36: Observability - Langfuse 연동
**결정:** entry_reason_node, coaching_judge_node의 LLM 호출에 Langfuse trace 추가. 키 미설정 시 조용히 비활성화되어 기존 동작 영향 없음.

**목적:** 운영 중 LLM 비용/지연시간 추적, 멀티모델 비교(Decision 31) 결과를 실제 프로덕션 데이터로 지속 검증할 수 있는 기반 마련.

**구현:**
- `utils/observability.py` — `get_langfuse()` 싱글턴 + `trace_llm_call()` 헬퍼
- `nodes/entry_reason_node.py` — LLM 호출 시간 측정 + trace
- `nodes/coaching_judge_node.py` — 동일 패턴 적용

**설계 원칙:** Langfuse 키 없으면 import도 하지 않음 (lazy import). 운영 환경에서 langfuse 패키지 없어도 에러 없음.
