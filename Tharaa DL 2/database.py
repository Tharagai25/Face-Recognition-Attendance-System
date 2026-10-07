"""
SQLite storage for students and attendance.
Face encodings and optional JPEG thumbnails are stored as BLOBs (no image files on disk).
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "attendance.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                face_encoding BLOB NOT NULL,
                face_image BLOB,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                attend_date TEXT NOT NULL,
                attend_time TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'auto',
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                UNIQUE (student_id, attend_date)
            );
            """
        )


def add_student(
    student_id: str,
    name: str,
    face_encoding_bytes: bytes,
    face_image_bytes: bytes | None,
) -> None:
    student_id = student_id.strip()
    name = name.strip()
    if not student_id or not name:
        raise ValueError("Student ID and name are required.")
    created_at = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO students (student_id, name, face_encoding, face_image, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, name, face_encoding_bytes, face_image_bytes, created_at),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Student ID '{student_id}' is already registered.") from exc


def delete_student(student_id: str) -> bool:
    student_id = student_id.strip()
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        return cur.rowcount > 0


def list_students() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT student_id, name, created_at FROM students ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_student_encodings() -> list[tuple[str, str, bytes]]:
    """Returns (student_id, name, encoding_bytes) for all registered students."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT student_id, name, face_encoding FROM students"
        ).fetchall()
    return [(r["student_id"], r["name"], r["face_encoding"]) for r in rows]


def get_student_face_image(student_id: str) -> bytes | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT face_image FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
    if row and row["face_image"]:
        return row["face_image"]
    return None


def has_attendance_today(student_id: str, on_date: date | None = None) -> bool:
    d = (on_date or date.today()).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM attendance
            WHERE student_id = ? AND attend_date = ?
            """,
            (student_id, d),
        ).fetchone()
    return row is not None


def mark_attendance(student_id: str, method: str = "auto") -> dict[str, str]:
    """Mark attendance for today. Raises ValueError if duplicate or unknown student."""
    student_id = student_id.strip()
    today = date.today()
    d_str = today.isoformat()
    t_str = datetime.now().strftime("%H:%M:%S")

    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
        if not exists:
            raise ValueError(f"No registered student with ID '{student_id}'.")

        try:
            conn.execute(
                """
                INSERT INTO attendance (student_id, attend_date, attend_time, method)
                VALUES (?, ?, ?, ?)
                """,
                (student_id, d_str, t_str, method),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"Attendance for '{student_id}' was already recorded on {d_str}."
            ) from exc

    return {"student_id": student_id, "date": d_str, "time": t_str, "method": method}


def get_attendance(
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT a.id, a.student_id, s.name, a.attend_date, a.attend_time, a.method
        FROM attendance a
        JOIN students s ON s.student_id = a.student_id
        WHERE 1=1
    """
    params: list[str] = []
    if from_date:
        query += " AND a.attend_date >= ?"
        params.append(from_date.isoformat())
    if to_date:
        query += " AND a.attend_date <= ?"
        params.append(to_date.isoformat())
    query += " ORDER BY a.attend_date DESC, a.attend_time DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
