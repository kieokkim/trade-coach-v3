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

### Decision 37: 샘플 모드 우선순위 버그 수정
**결정:** sample_mode가 명시적으로 선택되면 API 키 존재 여부와 무관하게 항상 우선 적용

**발견 과정:**
1. 실제 사용 테스트 중 "중급 트레이더 데모" 선택 시 승률 0.0%, 거래내역 없음으로 표시되는 문제 발견
2. API 직접 호출로 디버깅 → curl 테스트에서는 정상, session_id='default'로 호출했을 때만 빈 결과
3. new_data_check_node가 completed_nodes 2개에서 멈춤 (memory_load, new_data_check) → has_new_data=False
4. 근본 원인: .env에 실거래 BYBIT_API_KEY가 들어있어서, 사용자가 sample_mode를 선택해도 has_api_key=True로 판단해 실거래 모드로 강제 전환됨

**수정:**
- new_data_check_node: sample_mode 체크를 API 키 체크보다 먼저 수행
- bybit_fetch_node: sample_mode 있으면 거래소 클라이언트 호출 자체를 스킵

**교훈:** 사용자의 명시적 선택(UI에서 고른 모드)이 시스템 설정(.env의 키 존재 여부)보다 항상 우선해야 한다는 원칙을 코드로 강제. 이 버그는 .env에 실제 키를 넣어두는 사용자가 적어 v2.0부터 잠재해 있었지만 오늘 처음 발견됨.

### Decision 36: Observability - Langfuse 연동
**결정:** entry_reason_node, coaching_judge_node의 LLM 호출에 Langfuse trace 추가. 키 미설정 시 조용히 비활성화되어 기존 동작 영향 없음.

**목적:** 운영 중 LLM 비용/지연시간 추적, 멀티모델 비교(Decision 31) 결과를 실제 프로덕션 데이터로 지속 검증할 수 있는 기반 마련.

**구현:**
- `utils/observability.py` — `get_langfuse()` 싱글턴 + `trace_llm_call()` 헬퍼
- `nodes/entry_reason_node.py` — LLM 호출 시간 측정 + trace
- `nodes/coaching_judge_node.py` — 동일 패턴 적용

**설계 원칙:** Langfuse 키 없으면 import도 하지 않음 (lazy import). 운영 환경에서 langfuse 패키지 없어도 에러 없음.

---

## 2026-07-22

### Decision 38: 제품 스펙트럼 확정 — 행동 교정 축 / 자동매매 배제 / 코치형

**배경:** SalesCoach 방식 이식의 1단계. TradeCoach가 (a)기술적 매매신호·전략
자동화 (b)행동·심리 코칭(반복 실수 교정) (c)트레이딩 교육·이론 학습
(d)매매일지·기록관리 중 어디에 위치하는지 확정.

**판단:** (b) 행동·심리 코칭 축. ICT 이론은 목적이 아니라 진단에 쓰는
프레임(수단)이고, 복기뷰어·메모리는 그 진단을 위한 인프라. (a)는 명시적으로
배제(Read-Only API, 자동매매 영구 미구현). (d) 매매일지는 존재하나 그 자체가
목적이 아니라 반복 패턴 추적의 저장소.

**근거:**
- 개발 원칙 명시: "복기 기능은 자동매매보다 트레이더 행동 교정 목적"
- Agent Overview: "거래내역을 분석하여 반복 실수를 진단하고, ICT 이론 기반
  맞춤 코칭으로 트레이더의 행동 패턴을 교정" — 주어가 "행동 패턴 교정",
  ICT는 수단으로 걸림
- 차별화 핵심 질문 = "왜 같은 실수를 반복하는가", 결과물 = "내일 실행할 규칙 1개"
  — 교육(c)/저널링(d)이 아니라 교정 행동으로 수렴
- 업계 프레임(웹서치)의 3분류(시장분석/교육/행동분석) 중 세 번째 버킷에 정확히
  대응, 그 안에서도 멘토형이 아니라 코치형(규율 채점·규칙위반 플래깅 중심)

**DCA 갭과의 접점:** 오늘 발견한 "DCA 적립식 투자자 커버 불가"는 버그가 아니라
타겟 페르소나 경계 확인. "반복 실수 패턴 교정"이라는 정의 자체가 매수-매도
사이클 있는 트레이더를 전제하므로, DCA(매도 없음)는 "복기할 실수" 개념이
성립하지 않는 사용자층. 인프라 수정이 아니라 v3.0 Style Layer에서 "이 코칭 축
자체가 적용되는 사용자인가"를 먼저 분기해야 한다는 근거.

---

### Decision 39: 2단계 엣지케이스 감사 — 구조적 결함 4건 확정

**배경:** 검증 기능 제외한 기본 파이프라인 e2e 확인 + 10개 항목 엣지케이스
감사(조사 전용, 코드 수정 없음, monkeypatch 재현).

**파이프라인 실측 매핑 (브리프 가정과 불일치):**
- 메인 그래프 = 13노드(브리프 "10노드" 아님), LLM 노드 4개(weakness_detect,
  fallback_classify, backtest_coach, coaching_judge). quiz_generate 노드는 없음.
- 복기 플로우 = 그래프 밖 별도 동기 실행(entry_reason_node, replay_coach_node
  2개 LLM). ICT패턴탐지·A+스코어링·bge-m3 RAG는 전부 이 복기 플로우 전용 —
  메인 그래프엔 없음. 전체 앱 LLM 호출 지점 = 6개.

**확정된 구조적 결함 (영향도 순):**

1. **get_candles/bybit_fetch_node의 "실패=데이터 없음=정상" 혼동** (항목 1·2·9
   공통). 만료 키/거래 0건/존재하지 않는 조회가 전부 더미·샘플 데이터 자동
   대체로 처리 → FVG/OB 탐지·A+ 점수·복기 코멘트까지 가짜 데이터 위에서 "정상
   동작"처럼 나옴. `if not candles: raise HTTPException(404)` 방어 코드가 있으나
   도달 불가능(죽은 코드) — SalesCoach report_date 조용한 실패보다 은밀.

2. **journal_entries 테이블이 생성된 적 없음** (항목 4·10 공통). db.py
   init_db()에 CREATE TABLE 부재, ALTER TABLE만 있고 try/except pass로 조용히
   실패. A+ "손절 규율" 기준이 예외 로그도 없이 항상 True 고정 → A+ 점수가
   구조적으로 "5기준"이 아니라 "4기준 + 무조건 통과 1기준". 즉 "A+ 5기준"이라는
   표현 자체가 현재 부정확.

3. **fallback_classify_node만 LLM 실패 방어 누락** (항목 6). 나머지 5개 LLM
   호출 지점은 전부 try 방어. 조건부 경로(concept_not_found=True)라 항상 타진
   않지만, 타는 순간 파이프라인 전체 500 + memory_save 스킵. 단일 파일 단일
   함수 수정으로 해결 가능.

4. **58% accuracy = 순환논리 재확인** (항목 8). orderId 접두어(fvg-/ob-/sweep-
   /random-)로 스크립트가 자체 부여한 라벨 vs rule-based score_aplus 간 비교.
   사람 라벨링 데이터 전무. 게다가 이 58%는 LLM 코칭 자체가 아니라 rule 채점만
   검증한 것 — 실제 LLM 산출물(coaching_judge/entry_reason/replay_coach)의 사람
   검증은 전무.

**방어 확인:** RAG 실패 처리(항목5, try/except+빈결과 graceful), 거래소 스키마
정규화(항목7, ExchangeClient ABC로 Upbit→Bybit 필드명 정규화).

**의미:** SalesCoach 제0원칙 2단계("실패를 안다")를 TradeCoach는 아직 완주하지
못한 상태임을 진단. 특히 결함 1은 "입력이 조용히 사라지는 경우"를 graceful
degradation 점검 대상에 넣어야 한다는 SalesCoach Decision 27의 교훈이 여기서도
그대로 재현됨.

※ 이 감사 이후 Decision 37(샘플모드 우선순위 수정)이 new_data_check_node/
bybit_fetch_node를 이미 수정했음을 확인. 결함1/9(실패=데이터없음=정상 혼동)와
Decision 37은 같은 함수를 다루지만 다른 버그 — Decision 37은 sample_mode가
API키 존재로 오버라이드되던 문제, 결함1/9는 dummy candle 자동대체가 실패/
빈데이터를 구분 안 하는 문제. Decision 37 이후에도 결함1/9가 남아있는지는
STEP1에서 재확인 필요.

---

### Decision 40: 분석철학 명명 — "ICT 룰 기반 행동 트레이딩 애널리틱스 · Unsupervised"

**배경:** 3단계. 업계 트렌드 웹서치 후 TradeCoach의 현재 접근(ICT rule 패턴탐지
+ AI-as-Judge + RAG 코칭)을 과장 없이 위치시키기.

**명명:** "ICT 룰 기반 행동 트레이딩 애널리틱스 — Unsupervised(사람검증 부재)"
(Rule-Diagnosed Behavioral Trading Analytics, Unverified Judgment Layer)

**SalesCoach와의 대구:**
| | 판단 구조 | 검증 상태 |
|---|---|---|
| SalesCoach | 통계 rule(유의성+효과크기) | Supervised — anchor_set 사람검증 완료 |
| TradeCoach | 이론 rule(ICT 패턴탐지+A+스코어링) | Unsupervised — 사람검증 전무, 58%는 순환논리 |

**근거:** SalesCoach는 "Augmented Analytics + Supervised AI"로 명명했으나,
TradeCoach를 같은 틀로 부를 수 없음 — Decision 39에서 확인된 대로 A+ "5기준"이
실제론 4+1(무조건통과)이고, 58% 지표는 순환 비교이며, LLM 코칭 텍스트의 사람
검증은 전무. "Supervised"라 부를 근거가 없음.

**교훈:** 이 검증 비대칭 자체가 포트폴리오에서 정직하게 말할 수 있는 소재.
"같은 철학(rule=판단/LLM=설명)을 두 도메인에 적용했을 때, 한쪽은 검증까지
마쳤고 한쪽은 아직 검증 이전 단계임을 구분해서 안다"는 것이 제0원칙("자신의
한계를 아는 에이전트")의 실천.

---

### Decision 41: 차별점 재검토 — "저N 진단 가능성"은 차별점이 아니라 가설

**배경:** 3단계에서 "TradeCoach가 시장의 패턴마이닝을 안 따른다"를 차별점처럼
서술했으나, 사용자 검토로 이것이 독창적 선택이 아니라 데이터 수집 불가라는
결핍에서 나온 것임이 지적됨.

**판단:** 지금 시점에서 이것은 "차별점"이 아니라 "차별점의 후보(가설)". 경쟁력
없는 차별점은 의미 없음.

**분석:**
- 시장의 데이터 기반 접근은 구조적으로 초기 사용자(적은 거래 건수)를 못 다룸
  — 업계 자료: 기본 패턴 50건·의미있는 행동분석 200건·틸트 감지 150~200건 필요.
- ICT rule 기반 진단은 이론적으로 거래 1건 단위 판정 가능(통계적 유의성 불필요).
  이것이 "저N에서 작동하는" 잠재적 강점의 출발점.
- 그러나 이것이 경쟁력이 되려면 두 조건 필요, 둘 다 현재 미충족:
  ① ICT 이론 자체의 타당성이 검증돼야 함 (현재 사람검증 전무 — Decision 40)
  ② 저N에서 실제로 안전하게 작동해야 함 (현재 A+ 5기준 중 1개가 테이블 부재로
     항상 통과 — Decision 39 결함 2. "거래 1건도 안전하게 진단한다"는 주장이
     지금 코드로는 성립 안 함)

**결정:** 두 조건을 다음 과제로 명시. 충족 전까지 포지셔닝에서 이 항목은
"차별점"이 아니라 "결핍에서 나온 설계이며, 강점이 될 가능성은 있으나 아직
증명되지 않음"으로 정직하게 표기.

---

### Decision 42: 사람검증 부재 — 채우지 않고 재설계로 해결

**배경:** Decision 40에서 확인된 "사람검증 부재"를 (A)부재를 채운다 vs (B)부재가
필요없는 시스템으로 재설계 중 무엇으로 풀지 결정.

**선행 제약:** SalesCoach 방식(전 직장 동료를 2번째 라벨러로)을 그대로 못 씀 —
사용자 본인이 타겟 페르소나(ICT 단기 트레이더)와 불일치(DCA 매수자)라 스스로가
ICT 판정의 신뢰할 라벨러가 못 됨. "본인이 라벨링" 경로는 처음부터 막힘.

**결정: (B) 재설계.** rule 판정 레이어와 LLM 코칭 레이어를 UI/구조상 명시적으로
분리하는 방향.
- **rule 탐지/스코어링 레이어**(FVG·OB·A+ 조건 충족 여부) = "ICT 정의대로 코드가
  정확히 구현됐는가"는 code review + 공개 ICT 교재 예시(정답 알려진 차트)로
  spec conformance 검증 가능. 사람 라벨러 불필요, 검증 종류가 다를 뿐.
- **LLM 코칭 레이어**(backtest_coach/coaching_judge/entry_reason/replay_coach) =
  "이 조언이 실제로 유용한가"는 구조적으로 사람 판단 필요. 이 층은 UI에서 "AI
  추론·미검증"으로 명시하고, 외부 라벨러 확보는 이후 후속 과제.

**근거(순서):** (A)를 시작해도 "정확히 뭘 검증해달라고 할지"가 층 분리 없이는
애매. 층을 나눠야 외부 라벨러에게 "이 부분만 봐달라"고 구체적으로 요청 가능.
따라서 층 분리(B)가 외부 라벨러(A)보다 선행.

**구현 방향(Decision 43에서 UI로 실체화):** 제품 UI에 "이 층은 코드검증됨 / 이 층은
미검증"을 명시적으로 표시 — SalesCoach의 NO_QUERY_POSSIBLE 가드처럼 "자신의
한계를 아는 에이전트"를 문서가 아니라 UI에 반영.

**다음 과제:** ①공개 ICT 교재 예시로 rule 레이어 spec conformance 테스트 셋 구축
②A+ 5기준 버그(journal_entries) 수정으로 저N 안전성 확보 ③이후 LLM 코칭 레이어
외부 라벨러 확보.

---

### Decision 43: 복기뷰어 UI 재설계 — 캔들 표준색 + 존 무채색 + rule/LLM 시각분리

**배경:** 4단계. 실사용 스크린샷 4장 + ICT 차트 레퍼런스 5장 + 트레이딩저널
대시보드 레퍼런스 2장 검토 후 단일 HTML 목업 반복 제작(v1~v7).

**스크린샷에서 구분한 버그 / 설계결함:**
- 버그: ①LLM 실패 시 raw SDK 에러(Missing credentials...)가 코칭 자리에 그대로
  노출 ②FVG/OB 존이 발생 시각 무시하고 차트 왼쪽 끝부터 전체 폭에 렌더링(무지개
  줄무늬화) ③"추세" 필드 빈 대시인데 기울기 숫자는 이미 계산됨(표시 누락)
- 설계결함: ①WIN/LOSS(결과)와 Bull/Bear(방향)가 같은 초록/빨강 → 축 충돌
  ②rule 산출물(약점 태그)과 LLM 산출물(코칭 문장)이 시각적으로 구분 안 됨

**최종 디자인 결정 (레퍼런스 반영으로 v1→v2에서 방향 수정):**
- **캔들은 표준 초록/빨강 유지, 존(FVG/OB)은 무채색 콜아웃.** v1에서 캔들을
  틸/카퍼로 바꿨으나, 실제 ICT 차트가 표준 캔들색 + 무채색 존을 쓴다는 걸
  레퍼런스로 확인 후 수정. 색충돌은 "존에 색을 안 입히면" 원천 해소. 초록/빨강은
  캔들 상승·하락 + WIN/LOSS + PASS/FAIL에 통일(모두 "좋음/나쁨" 축이라 일관).
- **OB=실선 박스, FVG=점선 경계** — 색이 아니라 선 스타일로 구분(흑백에서도
  구별, 실제 ICT 툴 관례).
- **존은 발생 시각부터 오른쪽 유효구간만 렌더** (버그2 수정). 이 거래 관련 존
  1~2개만 콜아웃 라벨링, 나머지 탐지 존은 지우지 않되 옅게 처리(레퍼런스가 한
  차트에 1~2개만 콜아웃하는 관례 반영).
- **rule/LLM 레이어 시각 분리** (Decision 42의 UI 실체화): rule 산출값엔
  "코드검증" 배지, LLM 산출값엔 세리프체 + 점선 보더 + "AI 추론·미검증" 배지.
  숫자=모노스페이스, 서술=세리프로 rule/LLM 경계를 폰트로도 표현.
- **A+ 채점에서 버그를 감추지 않음** — 손절규율(테이블 부재)·사이징(손절가
  미입력) 2기준을 "데이터 없음 — 채점 보류"(회색·물음표)로 정직 표시. Decision 42
  "부재를 재설계로 해결" 원칙을 채점 UI에 직접 구현.
- **킬존 세로 밴드**(런던 02–05/뉴욕 07–10) — 진입 12:00이 두 밴드 모두 지난
  뒤임이 시각적으로 보여 "킬존외_진입" 약점 근거가 차트에서 직접 확인됨.
- **일별 손익 캘린더 + 복기 기록 로그를 2분할 같은 열 배치.** 캘린더는 실측 12건
  날짜별 손익(4/26 2건 합산 +$70.94), 로그는 BTC-001만 "A+ 완료"·나머지 11건
  "미복기"로 실제 상태 정직 반영.
- **복기뷰어 다중 거래 탭 + 드래그앤드롭.** 로그에서 거래를 드래그하면 뷰어에
  탭이 추가되고, 각 탭 안에 차트/A+채점/진입근거·코칭 3개 내부탭. 미복기 거래는
  세 탭 전부 빈 상태 문구로 정직 표시.

**데이터 원칙:** 캔들 시세만 레이아웃 시연용 예시, FVG/OB 좌표·진입/청산가·추세
기울기·KPI·손익은 전부 실제 화면 값 사용. 없는 값은 "목표 미설정/데이터 없음"류로
정직 표시(숫자 조작 금지).

**교훈:** 진입가 83,844.50이 03:00 OB 하단 경계(83,844.5)와 정확히 일치 —
"구조적 진입"이 실제로 성립하는 사례를 데이터에서 발견해 콜아웃으로 살림. UI
작업이 데이터를 다시 보게 만들어 도메인 사실을 발견한 케이스.

---

### Decision 44: 스코프 혼동 발견 — 계좌 전체 vs 거래 1건이 별개 그래프

**배경:** 사이드바 "약점"·"AI 코칭"이 한 거래의 것인지 계좌 전체의 것인지
불명확하다는 사용자 지적.

**발견:** Decision 39의 파이프라인 매핑으로 답이 나옴 — weakness_detect는 메인
13노드 그래프 안(계좌 전체 거래 이력 종합)에서 돌고, 특정 거래의 진입근거·코칭
(entry_reason_node/replay_coach_node)은 복기 플로우라는 별도 그래프에서 거래
1건 단위로 돎. 즉 "약점·코칭(계좌 전체)"과 "복기뷰어 탭 내용(거래 1건)"은 서로
다른 파이프라인 산출물인데 UI에 스코프 구분이 없었음. 다중 탭 도입으로 사이드바가
탭 전환과 무관하게 고정되는 이유가 사용자에게 설명 안 되던 상태.

**결정:** UI 라벨로 해소. KPI·약점 행과 복기뷰어 사이에 스코프 구분선 삽입
("↑ 계좌 전체·최근 12건 종합 / ↓ 열려있는 탭의 거래 1건"). 코드 구조 변경 아님 —
실제 파이프라인 구조를 UI가 정직하게 드러내도록 한 것.

**의미:** UI 재설계가 실제 아키텍처(두 그래프 분리)를 노출시킨 사례. 이 스코프
구분은 나중에 층 분리(Decision 42)와도 연결 — 계좌 전체 진단과 거래별 진단이
다른 검증 지위를 가질 수 있음.

---

### Decision 45: 스택 판단 — 프레임워크 전환 불필요

**배경:** 4단계 마지막. v7 목업이 현재 스택(Streamlit)으로 재현 가능한지 vs
프레임워크 전환 필요한지 판단.

**결정: 전환 불필요. Streamlit + Plotly + 커스텀 CSS 유지.**

**근거:** 스크린샷의 모드바 아이콘으로 앱이 이미 Plotly 캔들차트를 쓰는 것 확인.
목업 요소 대부분이 Plotly 기존 기능 범위:
- 색토큰·폰트구분·verify-badge = st.markdown 스타일 주입(SalesCoach와 동일)
- 콜아웃(리더라인+라벨) = Plotly add_annotation(showarrow, ax/ay)
- OB/FVG 존 = add_shape(rect/line, dash), 킬존 = add_vrect, 우측 가격축 = 기본값
- 캘린더 = 정적 HTML/CSS 그리드(st.markdown unsafe_allow_html)
- A+ 패널·코칭카드·3-way 내부탭 = st.tabs

**손봐야 할 지점 (스택 문제 아니라 설계 문제):**
1. **드래그앤드롭 → 클릭 오픈 권장.** Streamlit은 위젯 간 HTML5 네이티브 드래그
   미지원. 진짜 드래그는 React 커스텀 컴포넌트 필요(사실상 별도 프론트 개발) —
   유일하게 "전환 없이 된다"고 말하기 애매한 지점. 로그 행에 "복기 열기" 버튼으로
   대체하면 결과(탭 추가) 동일하고 st.session_state로 끝남.
2. **다중 거래 탭 바 = st.tabs 대신 수동 구현.** st.tabs는 렌더 시점 고정
   리스트라 추가/닫기 부적합. session_state.open_trades + active_trade_id 상태 +
   st.columns로 탭바 수동 구성. 프레임워크 전환 아니라 Python 로직 추가.
3. **백엔드 확인 필요.** /replay/candles, /replay/aplus 응답에 존 발생 시각이
   실제로 담겨있는지 — 전체폭 스트레치 버그가 프론트만 문제인지 백엔드가 zone
   시작 시각을 안 주는지는 코드 확인 필요(다음 코딩 세션 첫 항목).
4. **탭 전환 시 재계산 방지.** 열어본 거래 재방문 시 FVG/OB 재탐지·A+ 재채점
   반복은 낭비 → session_state 딕셔너리(거래ID→결과) 캐시 설계.

**결론:** SalesCoach와 같은 결론 — 스택 전환 없이 커스텀 CSS + Plotly로 목업
대부분 재현 가능. 유일하게 손 많이 가는 드래그앤드롭은 클릭 방식으로 회피.
