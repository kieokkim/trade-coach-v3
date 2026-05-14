NODE_LABELS: dict[str, tuple[str, str]] = {
    "memory_load":        ("⚙️", "과거 약점/세션 로드"),
    "new_data_check":     ("⚙️", "신규 거래 여부 확인"),
    "bybit_fetch":        ("⚙️", "거래내역 수집 중"),
    "preprocess":         ("⚙️", "데이터 정규화"),
    "journal_write":      ("🧠", "매매일지 작성 중"),
    "journal_analysis":   ("🧠", "KPI 분석 중"),
    "weakness_detect":    ("⚙️", "약점 태그 추출"),
    "performance_analysis": ("🧠", "성과 요약 중"),
    "backtest_coach":     ("🧠", "ICT 코칭 생성 중"),
    "quiz_generate":      ("🧠", "퀴즈 생성 중"),
    "memory_save":        ("⚙️", "세션 저장 중"),
}
