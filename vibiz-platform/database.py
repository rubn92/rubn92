import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "vibiz.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA_PATH.read_text())


# ── USERS ──

def create_user(email: str, password_hash: str) -> int | None:
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def update_user_plan(user_id: int, plan: str, stripe_customer_id: str = None,
                     stripe_subscription_id: str = None):
    with get_db() as conn:
        conn.execute(
            """UPDATE users SET plan=?, stripe_customer_id=COALESCE(?,stripe_customer_id),
               stripe_subscription_id=COALESCE(?,stripe_subscription_id)
               WHERE id=?""",
            (plan, stripe_customer_id, stripe_subscription_id, user_id),
        )


def increment_analyses(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET analyses_used = analyses_used + 1 WHERE id = ?",
            (user_id,),
        )


# ── PROJECTS ──

def save_project(user_id: int, url: str, title: str, report: dict) -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO projects (user_id, url, title, report) VALUES (?, ?, ?, ?)",
            (user_id, url, title, json.dumps(report, ensure_ascii=False)),
        )
        return cur.lastrowid


def get_project(project_id: int, user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["report"] = json.loads(d["report"])
    return d


def get_user_projects(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, url, title, created_at FROM projects WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_project(project_id: int, user_id: int):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM projects WHERE id=? AND user_id=?",
            (project_id, user_id),
        )
