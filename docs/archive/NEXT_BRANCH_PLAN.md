# TradeCoach — Next Branch Plan

> `trade-coach-v3` 기준 브랜치 전략
> 결정 이유: DECISION_LOG.md 참고

---

## 레포 구조

| 레포 | 역할 | 상태 |
|------|------|------|
| `kieokkim/trade-coach` | v2.0 안정 버전 | ✅ main 태그 v2.0 |
| `kieokkim/trade-coach-v3` | v2.1+ 개발 | 🔄 v2.2 완료 |

---

## 브랜치 현황

```
trade-coach-v3/
  main                              ← v2.0 코드 기준점
  ├── feature/replay-foundation     ← v2.1 ✅ 완료
  └── feature/ict-detector-engine   ← v2.2 ✅ 완료
```

---

## v2.1 작업 순서 (5일 플랜) ✅ 완료

### Day 1 — Kline 데이터 수집
```
market/candles.py   # Bybit Kline API (Public, 인증 불필요)
market/__init__.py
```
완료 기준: entry_time으로 전후 50개 캔들 조회 성공

### Day 2 — 멀티페이지 + 캔들차트
```
pages/1_api_input.py   # 시작 페이지
pages/2_loading.py     # 로딩 페이지
pages/3_main.py        # 메인 탭 3개
plotly 캔들차트 + 진입/청산 마커
```
완료 기준: 시작→로딩→메인 페이지 흐름 정상

### Day 3 — FVG 탐지 + 오버레이
```
ict/fvg_detector.py    # FVG rule-based 탐지
ict/__init__.py
캔들차트에 FVG 구간 오버레이
```
완료 기준: 샘플 캔들에서 FVG 탐지 + 차트 표시

### Day 4 — LLM 복기 코멘트
```
nodes/replay_coach_node.py
```
완료 기준: 거래 선택 → 복기 코멘트 전체 플로우

### Day 5 — 셋업 태깅 탭 + 통합 테스트
```
Tab 3 셋업 태깅 탭 기초
전체 QA
```
완료 기준: 7단계 사용자 시나리오 전체 작동

---

## 다음 브랜치

```bash
# v2.3: candle-by-candle Replay Coach (이 단계부터 "Replay" 표현 사용)
git checkout -b feature/replay-coach

# v3.0: 기간별 대시보드 + 장기 패턴 분석
git checkout -b feature/dashboard-v2
```

### feature/replay-coach (v2.3 예정)
- 캔들 단계적 표시 (bar-by-bar)
- "왜 MSS 확인 전에 진입했나요?" 질문 플로우
- AI 복기 피드백

### feature/dashboard-v2 (기간별 대시보드)
- 기간별 성과 대시보드 (주간/월간)
- 장기 반복 약점 추적
- 패턴 임베딩 + A+ 셋업 유사도 분석

---

## 브랜치 관리 원칙

1. 각 버전은 이전 버전 main 머지 후 생성
2. `main`은 항상 작동하는 안정 버전 유지
3. 실험적 작업은 `feature/` 브랜치에서만
4. 머지 전 회귀 테스트 체크리스트 통과 필수

---

## 완료 정의 (v2.2 DoD) ✅

- [x] OB / MSS / Liquidity 탐지
- [x] A+ 채점 5가지 기준 (ICT 기반 rule-based)
- [x] 캔들 기반 진입 근거 자동 추론
- [x] AI-as-Judge 코칭 검수
- [x] 롱/숏 방향 개념 추가
- [x] ICT 기반 약점 태깅 (종목명 제거)
- [x] 샘플 데이터 3종 (초보/중급/고수)
- [x] journal_write rule-based 전환
