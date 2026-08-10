# TradeCoach 다음 실행 체크리스트 (2026-07-22 세션 이후)

이번 세션은 조사·설계·문서까지. 아래는 그걸 실물로 만드는 순서.
원칙: **버그 수정 세션과 UI 세션을 분리**(SalesCoach "세션당 한 트랙"). 코드 수정은
전부 eval/e2e 회귀 없음 확인 후 분리 커밋.

---

## STEP 0 — 문서 먼저 레포에 안착 (5분, 코드 아님)
- [ ] TradeCoach_DECISION_LOG.md → 레포 루트 DECISION_LOG.md 로 커밋 (`docs(decision-log):`)
- [ ] TradeCoach_DEVLOG.md → 레포 루트 DEVLOG.md 로 커밋 (`docs(devlog):`)
- [ ] tradecoach_mockup_v7.html → docs/mockups/ 등에 보관 커밋
- 이유: 이후 코딩 세션에서 Claude Code가 참조할 판단 근거가 레포 안에 있어야 함.

---

## STEP 1 — 진단 확정 (조사 세션, 코드 수정 없음) ★첫 프롬프트
2단계 감사는 "재현"까지 했지만 수정 전 마지막 확인 2건이 남음. 코드 고치기 전에
이것부터 조사로 확정 (SalesCoach "원인추적과 코드수정 분리" 규율).
- [ ] 결함1/9: get_candles가 "실패"와 "데이터 없음"을 구분 못 하는 지점을 정확히
      특정. 실패 신호를 어디서 삼키는지 (파일:라인), 더미 대체가 어느 조건에서
      발동하는지.
- [ ] 결함4/10: journal_entries 테이블이 애초에 어떤 설계였는지 확인
      (docs/05_MVP_DB_스키마_설계서 대조). "테이블을 만들 것"인지 "이 기준 자체를
      재설계할 것"인지 결정 근거 수집. A+ 손절규율 기준이 이 테이블 없이 다른
      데이터로 판정 가능한지도 조사.
- [ ] 백엔드 /replay/candles·/replay/aplus 응답 스키마에 존 발생시각(timestamp)이
      실제로 담기는지 확인 → UI 전체폭 버그가 프론트 문제인지 백엔드 문제인지 확정.
- 출력: 세 항목을 "수정방향 확정 / 재설계 필요 / 추가조사" 로 분류한 짧은 보고서.
  → 이 보고서를 보고 STEP 2 순서를 최종 확정.

---

## STEP 2 — 버그 수정 (코딩 세션, 트랙: fix)
STEP 1 보고서 기준으로 착수. 각각 분리 커밋, 수정 후 e2e 1회 + 관련 재현 스크립트로 확인.
- [ ] fix A — 결함6: fallback_classify_node에 try/except 추가
      (가장 작고 독립적, 먼저 처리해 워밍업). 다른 5개 LLM 노드 방어 패턴 그대로 복제.
- [ ] fix B — 결함1/9: API 실패와 데이터 없음 구분. 실패는 사용자에게 명시적
      에러, 데이터 없음은 명시적 "거래 없음" 안내. 더미 캔들 자동 대체는 데모
      모드에서만(명시적 플래그) 발동하게 격리. `if not candles: raise 404` 죽은
      코드 되살리기.
- [ ] fix C — 결함4/10: STEP1 결정에 따라 (a)journal_entries CREATE 추가 또는
      (b)A+ 손절규율 기준 로직 재설계. 어느 쪽이든 "데이터 없으면 조용히 True"가
      아니라 "데이터 없으면 미채점(unscored)"으로 — 목업 v7의 정직 표시와 일치시킴.
- [ ] LLM 실패 시 raw SDK 에러(Missing credentials...) 노출 → 사용자용 문구로 대체
      (entry_reason/replay_coach 표시 경로).
- 커밋 후: DEVLOG에 이 세션 발견→원인→조치→결과 4단 append.

---

## STEP 3 — UI 구현 (코딩 세션, 트랙: feat, STEP 2 이후)
목업 v7을 Streamlit으로. 스택 판단(TC-D8) 그대로.
- [ ] 색토큰·폰트·verify-badge CSS 주입 (st.markdown)
- [ ] Plotly 차트: add_shape(OB실선/FVG점선), add_vrect(킬존), add_annotation(콜아웃),
      존은 발생시각부터 렌더 (STEP1에서 백엔드가 시각 준다고 확정된 경우)
- [ ] A+ 채점 패널에 "데이터 없음=unscored" 3-verdict (STEP2 fix C와 짝)
- [ ] rule/LLM 레이어 시각 분리 (TC-D5·6 UI 실체화)
- [ ] 캘린더 + 로그 2분할, 계좌전체/거래1건 스코프 구분선 (TC-D7)
- [ ] 다중 거래 탭: st.session_state.open_trades + active_trade_id 수동 구현,
      드래그앤드롭 대신 로그행 "복기 열기" 버튼, 탭 결과 캐시(거래ID→결과 dict)

---

## STEP 4 — 정리 (문서, 별도 세션 아님)
- [ ] TC-D1~8 Tier 재검토·확정 (현재 잠정 배치)
- [ ] Claude 웹으로 "싱크" — 이번 진행을 Instruction과 대조, 차이 패치
- [ ] (여유 시) TradeCoach 포트폴리오 8단 구조 적용 — 소재는 이번 명명/감사/재설계 서사

---

## 트랙 구분 요약
- STEP1 = 조사 트랙 (수정 없음)
- STEP2 = fix 트랙
- STEP3 = feat 트랙
- 한 세션에 fix와 feat 섞지 말 것. STEP1 보고서가 STEP2/3 순서의 게이트.
