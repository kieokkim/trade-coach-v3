NODE_LABELS: dict[str, tuple[str, str, str]] = {
    "memory_load":          ("⚙️", "memory_load",          "과거 세션 로드"),
    "new_data_check":       ("⚙️", "new_data_check",       "신규 거래 확인"),
    "bybit_fetch":          ("⚙️", "bybit_fetch",          "거래내역 수집"),
    "preprocess":           ("⚙️", "preprocess",           "데이터 정규화"),
    "journal_write":        ("🧠", "journal_write",        "매매일지 LLM"),
    "journal_analysis":     ("🧠", "journal_analysis",     "KPI 분석 LLM"),
    "weakness_detect":      ("⚙️", "weakness_detect",      "약점 태그 추출"),
    "performance_analysis": ("🧠", "performance_analysis", "성과 요약 LLM"),
    "backtest_coach":       ("🧠", "backtest_coach",       "ICT 코칭 LLM"),
    "coaching_judge":       ("🧠", "coaching_judge",       "코칭 검수 LLM"),
    "quiz_generate":        ("🧠", "quiz_generate",        "퀴즈 생성 LLM"),
    "memory_save":          ("⚙️", "memory_save",          "세션 저장"),
}


def sidebar_pipeline_md(completed: list[str], current: str | None) -> str:
    lines = ["**🤖 에이전트 파이프라인**\n"]
    for key, (icon, name, desc) in NODE_LABELS.items():
        if key == current:
            lines.append(f"▶️ `{name}`  \n**{desc}**")
        elif key in completed:
            lines.append(f"✅ `{name}`  \n{desc}")
        else:
            lines.append(f"○ `{name}`  \n{desc}")
    return "\n\n".join(lines)
