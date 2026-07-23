# TradeCoach Dev Log

세션 단위 작업 기록. 결정 근거는 DECISION_LOG.md, 여기는 "무슨 세션이 있었고
어떻게 흘러갔는지"의 흐름 기록. SalesCoach DEVLOG와 동일 포맷(발견→원인→조치→결과).

---

## 2026-07-22: SalesCoach 방식 이식 킥오프 — 스펙트럼 확인 → 감사 → 명명 → UI 목업 (Decision 1~8)

**발견:** TRADECOACH_KICKOFF_BRIEF.md 기준 4단계를 순서대로 진행. 1단계에서
제품이 행동 교정 축(코치형)임을 확정하고, 2단계 엣지케이스 감사에서 happy path는
정상이나 4개의 구조적 결함을 재현 확인 — ①실패=데이터없음=정상 혼동(더미 캔들
자동 대체) ②journal_entries 테이블 미생성으로 A+ 손절규율 기준이 항상 통과
③fallback_classify_node LLM 실패 무방비 ④58% = 순환논리 재확인. 브리프의 "10노드"
가정과 달리 실제는 메인 13노드 + 복기 별도 그래프 구조였음.

**원인:** 감사는 조사 전용 세션(monkeypatch 재현, 코드 미변경)으로 진행.
결함 1·9는 get_candles가 "실패"와 "데이터 없음"을 구분 안 하는 단일 분기가
근본원인, 결함 4·10은 journal_entries 테이블 CREATE 누락(ALTER만 있고 try/except
pass로 조용히 실패)이 공통 근본원인. 3단계 명명 과정에서 "저N 진단 가능성"을
차별점처럼 서술했으나 사용자 지적으로 "결핍에서 나온 가설"임을 재규정, 사람검증
부재는 채우기보다 rule/LLM 층 분리 재설계로 방향 확정.

**조치:** 코드 변경 없음(전 세션 조사·설계·문서). DECISION_LOG.md 신설(Decision
1~8, SalesCoach의 Tier 색인 포맷 이식). 4단계 UI 목업을 단일 HTML로 v1~v7 반복 —
캔들 표준색+존 무채색(v1의 캔들 틸/카퍼를 레퍼런스 보고 수정), rule/LLM 레이어
시각분리, 존 발생시각 렌더링(전체폭 버그 수정 반영), A+ 채점의 데이터부재 정직
표시, 캘린더+로그 2분할, 다중 거래 탭+드래그앤드롭, 계좌전체/거래1건 스코프 구분선.
마지막에 스택 판단(Streamlit+Plotly+커스텀CSS 유지, 드래그앤드롭만 클릭 대체 권장).

**결과:** 브리프 4단계 전부 완주. 산출물 = DECISION_LOG.md(신규),
tradecoach_mockup_v7.html(최종 목업), 2단계 감사 보고서. 다음 코딩 세션 우선순위:
(1) 결함 9/1 — API 실패와 데이터 없음 구분 (2) 결함 4/10 — journal_entries 테이블
생성 또는 A+ 손절규율 로직 재설계 (3) 결함 6 — fallback_classify_node try/except
추가 (4) 백엔드 /replay 응답에 존 발생시각 포함 여부 확인. UI 구현 시 드래그앤드롭
→ 클릭 버튼 대체 + 다중 탭 st.session_state 수동 구현 + 탭 결과 캐시.

**미결(다음 세션 판단 대기):**
- DECISION_LOG.md의 Decision 1~8 Tier 재검토(현재 D1~5 Tier1/D6~8 Tier2 잠정 배치)
- TradeCoach 포트폴리오 8단 구조 적용(SalesCoach 완료분과 동일 구조, 소재는
  이번 명명·감사·재설계 서사 활용)
- v3.0 Style Layer에서 DCA 페르소나 분기 설계(오늘 발견한 커버 갭 근거)
- Decision 37과 결함1/9의 관계는 STEP1 조사에서 재확인 필요 — 병합 시 발견됨.

---

## 2026-07-22: STEP1 진단 확정 세션 (Decision 46)

**발견:** 결함4/10이 예상보다 큼(이름 충돌·유령 테이블), 존 렌더링은 백엔드
문제가 아니라 프론트 필터링 부재였음.

**원인:** journal_entries 이름이 두 그래프(메인/복기)에서 각각 다른 실체를
가리킴. 스키마 설계서에 애초에 해당 테이블 없음.

**조치:** 코드 변경 없음(조사만). 수정 세션 순서 재조정 — A/B/존필터링을 한
세션으로, C(손절규율 재설계)는 설계결정 선행 필요해 분리.

**결과:** Decision 46 기록. 다음 세션 = A+B+존필터링 코딩(즉시 착수 가능),
C는 trade_tags/trade_history 스키마 확인 후 별도 착수.

---

## 2026-07-23: STEP2a 코딩 세션 — fallback 방어 + 실패/빈데이터 구분 + 존 렌더링 필터링

**발견:** 세 항목 모두 Decision 46에서 확정한 방향대로 구현 가능했음. 다만
Fix B 범위를 bybit_client.py로 한정해서 UpbitClient.fetch_candles는 여전히
예외를 삼켜 [] 반환 — Upbit 경로는 실패/빈데이터 구분이 아직 안 됨.

**원인:** (착수 시점에 이미 원인 특정된 항목들이라 조사 아님) Fix A는
fallback_classify_node에 다른 5개 LLM 노드와 다르게 try/except가 없었던 게
원인. Fix B는 BybitClient.fetch_candles가 실패/빈응답을 동일하게 [] 처리한
게 원인. Fix C는 존 rect의 x1이 항상 차트 끝까지였던 게 원인(발생시각은
이미 정확히 쓰고 있었음 — Decision 46에서 확인한 대로).

**조치:**
- fix(coaching-nodes): _classify_tag/_handle_ict/fallback_classify_node에
  try/except 추가, 실패 시 pattern 분류로 폴백
- fix(candles): BybitClient.fetch_candles 예외 전파로 전환,
  market/candles.py::get_candles가 실패(CandleFetchError)/빈데이터([])를
  분기, 더미 생성은 sample_mode 전용으로 제한, api/main.py 404를
  실제 도달 가능하게 하고 실패는 503으로 분리
- fix(replay-viewer): 존 x1을 발생시각+90분 고정폭으로 클리핑, 진입가를
  감싸는 존 최대 2개만 강조, 색을 무채색으로 전환

**결과:** 3개 커밋 전부 로컬에 완료(push 안 함). 재현 확인: Fix A는
LLM mock 실패 후 예외 전파 없이 pattern 폴백 확인, Fix B는 (a)키없음
(b)네트워크예외 (c)진짜빈데이터 세 케이스 모두 의도대로 분기 확인, Fix C는
BTC-001 실거래 데이터로 90분 클리핑 + 진입가 포함 존 1개 정확히 강조되는
것 확인(픽셀 스크린샷 비교는 브라우저 확장 미설치로 생략, 로직 검증만).
다음 세션: 손절규율(C, Decision 46의 별도 트랙) — journal_entries 저장
위치 설계 결정 선행, Upbit 캔들 경로 실패/빈데이터 구분도 아직 미해결로
남음.
