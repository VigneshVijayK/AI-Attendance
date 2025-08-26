from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from config import DB_PATH


@dataclass
class Employee:
    id: int
    name: str
    face_encoding: List[float]


@dataclass
class Camera:
    id: int
    name: str
    type: str  # "usb" | "onvif" | "rtsp"
    rtsp_url: Optional[str]
    status: str  # "online" | "offline" | "disabled"


@contextmanager
def connect_db() -> Iterable[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                face_encoding TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                in_time TEXT,
                out_time TEXT,
                status TEXT,
                FOREIGN KEY(emp_id) REFERENCES employees(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                rtsp_url TEXT,
                status TEXT NOT NULL DEFAULT 'offline'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS unknown_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_path TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL
            )
            """
        )


def add_employee(name: str, face_encoding: List[float]) -> int:
    payload = json.dumps(face_encoding)
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO employees(name, face_encoding) VALUES(?, ?)", (name, payload)
        )
        return cur.lastrowid


def fetch_employees() -> List[Employee]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM employees").fetchall()
        result: List[Employee] = []
        for r in rows:
            result.append(Employee(id=r["id"], name=r["name"], face_encoding=json.loads(r["face_encoding"])) )
        return result


def upsert_attendance_check_in(emp_id: int, dt: datetime) -> int:
    d = dt.date().isoformat()
    t = dt.time().isoformat(timespec="seconds")
    with connect_db() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, in_time FROM attendance WHERE emp_id=? AND date=?",
            (emp_id, d),
        ).fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO attendance(emp_id, date, in_time, status) VALUES(?, ?, ?, ?)",
                (emp_id, d, t, "present"),
            )
            return cur.lastrowid
        return int(row["id"])  # already exists


def set_attendance_check_out(emp_id: int, dt: datetime) -> None:
    d = dt.date().isoformat()
    t = dt.time().isoformat(timespec="seconds")
    with connect_db() as conn:
        conn.execute(
            "UPDATE attendance SET out_time=? WHERE emp_id=? AND date=?",
            (t, emp_id, d),
        )


def add_attendance(emp_id: int, date_str: str, in_time: Optional[str], out_time: Optional[str], status: str) -> int:
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO attendance(emp_id, date, in_time, out_time, status) VALUES(?, ?, ?, ?, ?)",
            (emp_id, date_str, in_time, out_time, status),
        )
        return cur.lastrowid


def delete_attendance(att_id: int) -> None:
    with connect_db() as conn:
        conn.execute("DELETE FROM attendance WHERE id=?", (att_id,))


def add_camera(name: str, type: str, rtsp_url: Optional[str]) -> int:
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO cameras(name, type, rtsp_url, status) VALUES(?, ?, ?, 'offline')",
            (name, type, rtsp_url),
        )
        return cur.lastrowid


def update_camera_status(camera_id: int, status: str) -> None:
    with connect_db() as conn:
        conn.execute("UPDATE cameras SET status=? WHERE id=?", (status, camera_id))


def update_camera(camera_id: int, *, type: Optional[str] = None, rtsp_url: Optional[str] = None, status: Optional[str] = None) -> None:
    fields = []
    values: List[object] = []
    if type is not None:
        fields.append("type=?")
        values.append(type)
    if rtsp_url is not None:
        fields.append("rtsp_url=?")
        values.append(rtsp_url)
    if status is not None:
        fields.append("status=?")
        values.append(status)
    if not fields:
        return
    values.append(camera_id)
    with connect_db() as conn:
        conn.execute(f"UPDATE cameras SET {', '.join(fields)} WHERE id=?", values)


def delete_camera(camera_id: int) -> None:
    with connect_db() as conn:
        conn.execute("DELETE FROM cameras WHERE id=?", (camera_id,))


def fetch_cameras() -> List[Camera]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM cameras").fetchall()
        result: List[Camera] = []
        for r in rows:
            result.append(
                Camera(
                    id=r["id"],
                    name=r["name"],
                    type=r["type"],
                    rtsp_url=r["rtsp_url"],
                    status=r["status"],
                )
            )
        return result


def log_unknown(snapshot_path: str, dt: datetime) -> int:
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO unknown_log(snapshot_path, date, time) VALUES(?, ?, ?)",
            (snapshot_path, dt.date().isoformat(), dt.time().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def fetch_unknowns() -> List[dict]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM unknown_log ORDER BY date DESC, time DESC").fetchall()
        return [dict(row) for row in rows]


def delete_unknown(unknown_id: int) -> None:
    with connect_db() as conn:
        conn.execute("DELETE FROM unknown_log WHERE id=?", (unknown_id,))


def export_unknowns_to_excel(xlsx_path: Path) -> None:
    import pandas as pd
    with connect_db() as conn:
        df = pd.read_sql_query(
            "SELECT id, snapshot_path, date, time FROM unknown_log ORDER BY date DESC, time DESC",
            conn,
        )
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(xlsx_path, index=False)


def export_attendance_to_csv(csv_path: Path) -> None:
    import pandas as pd

    with connect_db() as conn:
        df = pd.read_sql_query(
            """
            SELECT a.id, e.name as employee, a.date, a.in_time, a.out_time, a.status
            FROM attendance a INNER JOIN employees e ON a.emp_id = e.id
            ORDER BY a.date DESC, e.name ASC
            """,
            conn,
        )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def export_attendance_to_excel(xlsx_path: Path) -> None:
    import pandas as pd

    with connect_db() as conn:
        df = pd.read_sql_query(
            """
            SELECT a.id, e.name as employee, a.date, a.in_time, a.out_time, a.status
            FROM attendance a INNER JOIN employees e ON a.emp_id = e.id
            ORDER BY a.date DESC, e.name ASC
            """,
            conn,
        )
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(xlsx_path, index=False)


def delete_employee(emp_id: int) -> None:
    with connect_db() as conn:
        conn.execute("DELETE FROM attendance WHERE emp_id=?", (emp_id,))
        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))

