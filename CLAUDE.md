# CLAUDE.md — TradeCoach v2.1 코딩 행동 지침

Behavioral guidelines for Claude Code. Merge with task-specific instructions as needed.

---

## 1. Think Before Coding

- 구현 전 가정을 명시하고 불확실하면 질문
- 더 단순한 방법이 있으면 먼저 제안
- 멀티스텝 작업은 계획 먼저 제시

## 2. Simplicity First

- 요청된 것만 구현, 추가 기능 금지
- 단일 사용 코드에 추상화 금지
- 200줄이 50줄로 가능하면 다시 작성

## 3. Surgical Changes

- 기존 코드 스타일 유지
- 내가 만든 변경으로 생긴 orphan만 정리
- 관련 없는 코드 개선 금지

## 4. Goal-Driven Execution

- 성공 기준을 먼저 정의
- 멀티스텝은 계획 → 검증 순서로

---

## TradeCoach v2.1 작업 규칙

### 공통 조건 (모든 작업에 적용)
- 기준 파일: `graph.py` + `nodes/*.py` (실제 로직)
- 수정 금지: `final_notebook.ipynb`
- 노드 파일에 `logger = logging.getLogger(__name__)` 필수
- 작업 완료 후 `git add -A && git commit`

### v2.1 신규 원칙
- ICT 탐지는 rule-based 우선 (LLM 차트 해석 최소화)
- 캔들 데이터는 `market/candles.py`로 중앙화
- Streamlit 페이지는 `pages/` 폴더에서만 작업
- 복기 플로우는 메인 그래프와 독립 실행

### 커밋 컨벤션
- `feat:` 새 기능
- `fix:` 버그 수정
- `refactor:` 기능 변경 없는 개선
- `docs:` 문서 수정
- `chore:` 빌드/설정 변경

### 보안
- `.env` 절대 커밋 금지
- `tradecoach.db` `.gitignore` 등록
