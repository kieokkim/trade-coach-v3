# Coaching Notes — TradeCoach

## 1~2단계 전체 완료 — 다음은 v3.0 로드맵 논의

> 이 파일은 Claude 웹(메모리 보유)에서 받은 전략 코칭을 Claude Code 세션에
> 전달하기 위한 동기화 파일입니다. 새 세션 시작 시 CLAUDE.md, DECISION_LOG.md와
> 함께 읽어주세요.

---

## 코칭 배경 (2026-06)

발표자(현업 AI 컨설턴트) + 시장 채용공고 분석 기반 피드백 요약:

- 이 분야는 연차보다 산출물의 "깊이"로 평가받는다
- Eval(평가) 설계 능력이 가장 베끼기 어려운 차별점이다
  ("특정 프롬프트가 좋은지 나쁜지 점수를 매겨 검증하는 방법,
  여러 모델로 비교 평가하는 방법을 알아야 한다")
- 보안(prompt injection 방어, API 권한 분리)도 실무 채용 공고 공통 요구사항
- Agent Harness 개념 — 인프라를 직접 짜지 말고 검증된 하네스(LangGraph) 위에
  도메인 로직만 얹는 게 맞는 전략 (이미 하고 있음, 재인식 필요)
- 프로젝트 양보다 깊이가 강한 신호: 같은 프로젝트를 오래 운영하며
  버그를 발견·수정·회고한 기록이 "판단력"을 증명함

---

## Claude Code 작업 방식 — 멘토 모드

새로운 기술/개념을 이 프로젝트에 처음 도입할 때(Eval, RAG, FastAPI, Observability 등):

1. 코드를 먼저 작성하지 않는다
2. 먼저 "이 개념이 뭔지, 왜 필요한지"를 비개발자 눈높이로 쉬운 비유를 들어 설명한다
3. 이 프로젝트의 어느 부분에 구체적으로 적용되는지 짚어준다
4. 사용자가 이해했다고 확인하면 그제서야 코드를 작성한다
5. 작성 후 "이 코드가 방금 설명한 개념을 어떻게 구현했는지" 다시 연결해서 설명한다

기술적으로 익숙하지 않은 비전공자 출신 학습자임을 항상 고려한다.
평소 반복 작업(파일 생성, 포맷팅, 단순 버그 수정)은 토큰 절약 모드 유지.
새 개념 도입 시점에만 "설명해줘 모드로" 요청 시 멘토 모드로 전환.

---

## ✅ 1단계 완료 (2026-06)

### 1. A+ 채점 Eval 검증 (✅ 완료, 2026-06)

방향 전환: 처음엔 AI-as-Judge(코칭 문장 검증)를 계획했으나,
코칭은 정성적이라 자율성을 해치는 검증이라 판단.
대신 A+ 채점(rule-based 정량 판단)을 검증 대상으로 재정의.
"채점이 정확해야 그 위의 코칭도 정확한 근거를 갖는다"는 논리.

검증 방법: 샘플 데이터의 orderId 패턴(fvg-/ob-/sweep-/random-)을
Ground Truth로 활용. 사람이 매번 차트를 보고 판단하는 대신,
샘플 설계 시점에 이미 정해둔 의도를 정답으로 써서 자동 검증.

발견한 문제 (look-ahead bias):
- 1차 검증: random 거래(의도적으로 근거 없는 진입) 81%가
  "구조 진입"으로 오판정 (정확도 19%)
- 원인: structure_entry 판정이 진입 시점 이후에 생긴 FVG/OB까지
  포함해서 검사 → 미래 정보로 과거를 판단하는 데이터 누수
- 퀀트 분야의 data snooping/survivorship bias와 본질적으로 같은 함정

1차 수정 후 발견한 2차 문제:
- 진입 이전 구조만 필터링하자 random은 개선(19→33%)됐지만
  fvg/ob 정확도가 회귀(100→71%, 100→67%)
- 원인: 검증 함수 자체가 "구조가 존재하는가"와
  "가격이 그 구조 안에 있는가"를 혼동
- 수정 도구를 만드는 과정에서도 같은 유형의 논리 오류가 반복됨을 확인

최종 결과:
- fvg 100%, ob 100% 회복
- 전체 정확도 47.2% → 58.3%
- random 잔여 FP(33%)는 버그가 아니라 실제 시장에서
  감으로 진입해도 우연히 구조와 겹치는 자연적 노이즈로 판단

```
포트폴리오 Before/After:
  Before: A+ 채점이 진입 전후 구조를 구분 없이 판정 → random 81% 오판정
  After:  look-ahead bias 수정 + 샘플 캔들 구조 보장
          → fvg/ob 100%, 전체 58.3% (3단계 트러블슈팅)
  트러블슈팅 과정:
    1차 발견 → random FP 81% (look-ahead bias)
    1차 수정 → random 개선(19→33%) but fvg/ob 회귀(100→71%, 67%)
    2차 발견 → 검증 함수 논리 오류 ("존재" vs "가격 포함")
    2차 수정 → 샘플 캔들에 구조 주입 + 가격 포함 검증
    최종 결과 → fvg/ob 100% 회복, 전체 58.3%
```

산출물:
- scripts/eval_aplus_validation.py (자동 검증 스크립트)
- scripts/generate_sample_candles.py (구조 검증 + 주입 로직 추가)
- nodes/entry_reason_node.py (fvg_before/ob_before 필터)
- DECISION_LOG.md TC-D30

### 2. 멀티모델 비교 평가 (✅ 완료)

결과: Groq(llama-3.3-70b) > OpenAI(gpt-4o-mini)
- 응답시간 2.5배 빠름, 기준언급 더 풍부
- 단서: 작은 모델(llama-3.1-8b)은 이전에 rate limit+루프 문제 있었음
  → "Groq 우수"가 아니라 "모델 크기가 핵심"

산출물: scripts/eval_multimodel_comparison.py, TC-D31

### 3. 보안 — Bybit API 권한 분리 (✅ 완료)

결과: 본인 실제 API 키에서 거래 권한 7개 탐지 성공
(실전에서 바로 가치 증명됨)

산출물: utils/api_safety.py, scripts/test_api_safety.py, TC-D32

---

## ✅ 2단계 완료 (2026-06)

### 4. RAG 레이어 (✅ 완료)

결과: 4단계 가설 검증으로 임베딩 모델 한계 발견
(MiniLM 0% → bge-m3 100%). entry_reason_node 코칭에 연결 완료.

산출물: tools/ict_rag.py, tools/ict_search_text.py, TC-D33

### 5. FastAPI 백엔드 분리 (✅ 완료)

결과: /analyze, /replay/candles, /replay/aplus 4개 엔드포인트.
실시간 노드 로그는 의도적으로 포기, 구조 분리를 우선시.

산출물: api/main.py, TC-D35

### 6. Observability (✅ 완료)

결과: Langfuse lazy import 설계 — 키 없으면 기존 동작 100% 유지.

산출물: utils/observability.py, TC-D36

---

## 완료된 기능 — Before/After

### progress_compare_node (✅ 완료, 2026-06)

Before: 트레이더가 혼자 복기하면 지난 세션과 비교해서
        나아졌는지 스스로 알 수 없음. 세션 메모리가
        기록만 하고 "변화 인지" 로직이 없었음.

After: weaknesses 테이블의 last_seen 날짜 기준으로
       가장 최근 두 날짜의 약점 분포를 비교해서
       resolved(해소)/new(신규)/persistent(지속)로 자동 분류.
       backtest_coach 프롬프트에 비교 결과를 주입해서
       "해소된 약점은 칭찬, 신규는 경고, 지속은 집중 코칭"하도록 연결.

트러블슈팅 — 레거시 데이터 오염:
  발견: 실제 DB로 비교를 돌렸을 때 'BTC_개선필요' 같은
        종목명 기반 태그가 'new'로 잘못 분류됨
  원인: v2.2에서 약점 태그를 ICT 개념 기반으로 전환했지만(TC-D17)
        DB에 이미 저장된 v2.0~v2.1 시절 레거시 데이터가 남아있었음
  해결: DELETE FROM weaknesses WHERE weakness LIKE '%_개선필요'
        실행 후 재검증 → 깨끗한 ICT 기반 비교 결과 확인
  교훈: 기능 변경 시 코드만 바꾸는 게 아니라 기존 DB 데이터의
        하위호환성도 함께 점검해야 함

구현 위치:
  nodes/progress_compare_node.py (rule-based, LLM 미사용)
  graph.py (weakness_detect → progress_compare → backtest_coach)
  nodes/coaching_nodes.py (comparison 텍스트 프롬프트 주입)
  pages/3_main.py (사이드바 "📈 지난 세션 대비" 섹션)

포트폴리오 반영: KPI 후보로 "재방문 사용자의 약점 재발률"
  측정 가능해짐 — 다음 단계에서 실제 수치화 필요

---

## 보류 — 지금 단계에서 하지 않아도 되는 것

Voice agent(Whisper), Fine-tuning(RFT/DPO/SFT), Browser agent, MCP 등은
시니어/특화 포지션 요구사항. 1~2단계를 먼저 채우는 게 우선.

---

## 포트폴리오 반영 — Before/After 수치 포맷

AX 컨설팅 산출물 사례 분석 결과, "Before → After 수치"가 설득력의 핵심.
TradeCoach에 적용된 포맷:

```
Before: 복기를 혼자 하면 같은 실수 반복 여부를 알 수 없음
After:  세션마다 약점 태깅 → 누적 추적 → 반복 패턴 감지
```

향후 모든 신규 기능 추가 시 이 포맷으로 트러블슈팅/설계판단 섹션에 기록할 것.

---

## 한 단계 위의 서비스 방향 (장기 비전, 참고용)

현재 자동화 수준(1단계: 수작업 → 자동화)에서 다음 단계로:

```
2단계: 누적된 약점 데이터에서 "킬존 진입 실패가 반복된다" 같은
       패턴을 자동 감지해 다음 거래 전 경고 생성
3단계: 100건 이상 거래가 쌓이면 "월요일 오전 승률이 낮다" 같은
       행동 경제학적 패턴 도출 → 코칭이 개인화됨
```

v3.0 Market Scanner보다 이 방향(데이터 기반 개인화)이
핵심 가치에 더 가까울 수 있음 — 추후 로드맵 논의 시 고려.
