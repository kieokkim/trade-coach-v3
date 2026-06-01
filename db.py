import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "tradecoach.db"

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    logger.info("get_db: opening connection to %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
        logger.info("get_db: commit ok")
    except Exception as e:
        logger.warning("get_db: rollback due to %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()
        logger.info("get_db: connection closed")


def init_db() -> None:
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS weaknesses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                weakness    TEXT    NOT NULL,
                count       INTEGER DEFAULT 1,
                last_seen   DATE    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trade_history (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT    NOT NULL,
                date           DATE    NOT NULL,
                win_rate       FLOAT   NOT NULL,
                avg_rr         FLOAT   NOT NULL,
                max_drawdown   INTEGER,
                main_weakness  TEXT,
                trade_count    INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS quiz_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                concept      TEXT    NOT NULL,
                passed       BOOLEAN NOT NULL,
                retry_count  INTEGER DEFAULT 0,
                date         DATE    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS performance_snapshots (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL,
                period          TEXT,
                period_start    DATE,
                win_rate        FLOAT,
                avg_return_rate FLOAT,
                expected_value  FLOAT,
                loss_consistency FLOAT,
                profit_rate     FLOAT,
                top_weakness    TEXT,
                action_rule     TEXT
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_weaknesses_session_tag
                ON weaknesses (session_id, weakness);

            CREATE INDEX IF NOT EXISTS idx_trade_history_session_date
                ON trade_history (session_id, date);

            CREATE INDEX IF NOT EXISTS idx_quiz_results_session_concept
                ON quiz_results (session_id, concept);
        """)

        # trade_history 신규 KPI 컬럼 (마이그레이션)
        for col_ddl in [
            "ALTER TABLE trade_history ADD COLUMN avg_return_rate FLOAT",
            "ALTER TABLE trade_history ADD COLUMN expected_value  FLOAT",
            "ALTER TABLE trade_history ADD COLUMN loss_consistency FLOAT",
            "ALTER TABLE trade_history ADD COLUMN last_fetched_at TEXT",
        ]:
            try:
                conn.execute(col_ddl)
            except Exception:
                pass

        # weaknesses category 컬럼
        try:
            conn.execute("ALTER TABLE weaknesses ADD COLUMN category TEXT DEFAULT 'ict'")
        except Exception:
            pass

        # journal_entries ict_tag 컬럼
        try:
            conn.execute("ALTER TABLE journal_entries ADD COLUMN ict_tag TEXT DEFAULT ''")
        except Exception:
            pass

        # trade_tags 포지션 사이징 컬럼
        for col_ddl in [
            "ALTER TABLE trade_tags ADD COLUMN fixed_loss  FLOAT DEFAULT 0.0",
            "ALTER TABLE trade_tags ADD COLUMN ideal_qty   FLOAT DEFAULT 0.0",
            "ALTER TABLE trade_tags ADD COLUMN actual_qty  FLOAT DEFAULT 0.0",
            "ALTER TABLE trade_tags ADD COLUMN stop_price  REAL  DEFAULT 0",
        ]:
            try:
                conn.execute(col_ddl)
            except Exception:
                pass

        # trade_tags 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_tags (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT    NOT NULL,
                order_id       TEXT    NOT NULL,
                symbol         TEXT,
                ict_tag        TEXT    DEFAULT '',
                user_confirmed INTEGER DEFAULT 0,
                created_at     TEXT,
                UNIQUE(session_id, order_id)
            )
        """)


def save_trade_tag(
    session_id: str,
    order_id: str,
    symbol: str,
    ict_tag: str,
    user_confirmed: int = 0,
    fixed_loss: float = 0.0,
    ideal_qty: float = 0.0,
    actual_qty: float = 0.0,
    stop_price: float = 0.0,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO trade_tags (session_id, order_id, symbol, ict_tag, user_confirmed,
                                    fixed_loss, ideal_qty, actual_qty, stop_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, order_id) DO UPDATE SET
                ict_tag=excluded.ict_tag,
                user_confirmed=excluded.user_confirmed,
                fixed_loss=CASE WHEN excluded.fixed_loss   > 0 THEN excluded.fixed_loss   ELSE trade_tags.fixed_loss   END,
                ideal_qty=CASE WHEN excluded.ideal_qty     > 0 THEN excluded.ideal_qty    ELSE trade_tags.ideal_qty    END,
                actual_qty=CASE WHEN excluded.actual_qty   > 0 THEN excluded.actual_qty   ELSE trade_tags.actual_qty   END,
                stop_price=CASE WHEN excluded.stop_price   > 0 THEN excluded.stop_price   ELSE trade_tags.stop_price   END
            """,
            (session_id, order_id, symbol, ict_tag, user_confirmed,
             fixed_loss, ideal_qty, actual_qty, stop_price, datetime.utcnow().isoformat()),
        )


def load_trade_tags(session_id: str) -> dict:
    """orderId → {"tag": str, "confirmed": int, "stop_price": float} 딕셔너리 반환"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT order_id, ict_tag, user_confirmed, stop_price FROM trade_tags WHERE session_id=?",
            (session_id,),
        ).fetchall()
    return {
        r["order_id"]: {
            "tag":        r["ict_tag"],
            "confirmed":  r["user_confirmed"],
            "stop_price": float(r["stop_price"] or 0.0),
        }
        for r in rows
    }
