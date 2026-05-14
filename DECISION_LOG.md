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
