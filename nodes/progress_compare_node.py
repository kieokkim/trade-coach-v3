import logging

from db import get_db

logger = logging.getLogger(__name__)


def progress_compare_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")

    try:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT DISTINCT date(last_seen) as d
                   FROM weaknesses WHERE session_id=?
                   ORDER BY d DESC LIMIT 2""",
                (session_id,),
            ).fetchall()

        if len(rows) < 2:
            return {"progress_comparison": None}

        latest_date, prev_date = rows[0]["d"], rows[1]["d"]

        with get_db() as conn:
            latest = {r["weakness"] for r in conn.execute(
                "SELECT weakness FROM weaknesses WHERE session_id=? AND date(last_seen)=?",
                (session_id, latest_date),
            ).fetchall()}
            prev = {r["weakness"] for r in conn.execute(
                "SELECT weakness FROM weaknesses WHERE session_id=? AND date(last_seen)=?",
                (session_id, prev_date),
            ).fetchall()}

        resolved = prev - latest
        new_issues = latest - prev
        persistent = latest & prev

        logger.info(
            "progress_compare_node | session_id=%s resolved=%d new=%d persistent=%d",
            session_id, len(resolved), len(new_issues), len(persistent),
        )

        return {
            "progress_comparison": {
                "resolved": list(resolved),
                "new": list(new_issues),
                "persistent": list(persistent),
                "latest_date": latest_date,
                "prev_date": prev_date,
            }
        }
    except Exception as e:
        logger.warning("progress_compare_node error: %s", e)
        return {"progress_comparison": None}
