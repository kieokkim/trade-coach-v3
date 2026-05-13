# TradeCoach — Next Branch Plan

> 새 레포(trade-coach-replay) 기준 브랜치 전략
> 결정 이유: DECISION_LOG.md 참고

---

## 레포 구조

| 레포 | 역할 | 상태 |
|------|------|------|
| `kieokkim/trade-coach` | v2.0 안정 버전 | ✅ main 태그 v2.0 |
| `kieokkim/trade-coach-replay` | v2.1+ 개발 | 🔄 진행 중 |

---

## 현재 브랜치

```
trade-coach-replay/
  main                           ← v2.0 코드 복제 기준점
  └── feature/replay-foundation  ← 현재 작업 중
```

---

## v2.1 작업 순서 (5일 플랜)

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
ict/fvg_detector.py    # FVG rule-based 탐지 (기본 ICT 패턴)
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

## v2.2 이후 브랜치

```bash
# v2.1 완료 후
git checkout main
git merge feature/replay-foundation
git tag v2.1

# v2.2: OB/MSS/Liquidity 탐지
git checkout -b feature/ict-detector-engine

# v2.3: bar-by-bar Replay (이 단계부터 "Replay" 표현 사용)
git checkout -b feature/replay-coach

# v3.0: A+ Setup Memory
git checkout -b feature/aplus-setup-memory
```

---

## 브랜치 관리 원칙

1. 각 버전은 이전 버전 main 머지 후 생성
2. `main`은 항상 작동하는 안정 버전 유지
3. 실험적 작업은 `feature/` 브랜치에서만
4. 머지 전 회귀 테스트 체크리스트 통과 필수

---

## 완료 정의 (v2.1 DoD)

- [ ] 거래 선택 → 캔들차트 (마커 포함)
- [ ] FVG 구간 오버레이 (기본 ICT 패턴)
- [ ] LLM 복기 코멘트 출력
- [ ] 멀티페이지 흐름 정상
- [ ] 셋업 태깅 탭 기초 작동
- [ ] 재방문 시 신규 데이터만 추가
- [ ] final_notebook.ipynb QA 통과
- [ ] git tag v2.1 푸시 완료
