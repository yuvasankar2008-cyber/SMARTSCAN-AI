"""SQLite persistence for SMARTSCAN simulation and uploaded experiment records."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Any


ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = ROOT / "data" / "smartscan.db"


class ClosingConnection(sqlite3.Connection):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


class DatabaseManager:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), factory=ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS experiments (
                    Experiment_ID TEXT PRIMARY KEY,
                    Name TEXT NOT NULL,
                    Source TEXT NOT NULL,
                    Scenario TEXT,
                    Created_At TEXT NOT NULL,
                    Updated_At TEXT NOT NULL,
                    Metadata TEXT
                );
                CREATE TABLE IF NOT EXISTS records (
                    Record_ID TEXT PRIMARY KEY,
                    Experiment_ID TEXT NOT NULL,
                    Timestamp TEXT,
                    Source TEXT NOT NULL,
                    Round INTEGER,
                    Selected_Sector TEXT,
                    Detected INTEGER,
                    Predicted_Active INTEGER,
                    Prediction_Correct INTEGER,
                    False_Alarm INTEGER,
                    Cumulative_Reward REAL,
                    Processing_Status TEXT NOT NULL,
                    Raw_JSON TEXT,
                    FOREIGN KEY (Experiment_ID) REFERENCES experiments(Experiment_ID)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_records_experiment
                    ON records(Experiment_ID);
                CREATE INDEX IF NOT EXISTS idx_records_timestamp
                    ON records(Timestamp);
            """)

    def create_experiment(self, experiment_id: str, name: str, source: str,
                          scenario: str = "", created_at: str = "",
                          metadata: str = "") -> dict[str, Any]:
        now = created_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO experiments "
                "(Experiment_ID, Name, Source, Scenario, Created_At, Updated_At, Metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (experiment_id, name, source, scenario, now, now, metadata),
            )
        return self.get_experiment(experiment_id) or {}

    def insert_experiment(self, *args, **kwargs):
        return self.create_experiment(*args, **kwargs)

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM experiments WHERE Experiment_ID = ?", (experiment_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_experiments(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM experiments ORDER BY Created_At DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_experiments(self) -> list[dict[str, Any]]:
        return self.list_experiments()

    def insert_record(self, record: dict[str, Any]) -> bool:
        return self.insert_records([record]) == 1

    def insert_records(self, records: Iterable[dict[str, Any]]) -> int:
        import json
        inserted = 0
        with self.connect() as connection:
            for record in records:
                experiment_id = record.get("Experiment_ID")
                if not experiment_id:
                    continue
                raw = {key: value for key, value in record.items()
                       if not str(key).startswith("_")}
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO records "
                    "(Record_ID, Experiment_ID, Timestamp, Source, Round, Selected_Sector, "
                    "Detected, Predicted_Active, Prediction_Correct, False_Alarm, "
                    "Cumulative_Reward, Processing_Status, Raw_JSON) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(record.get("Record_ID") or ""),
                        str(experiment_id),
                        record.get("Timestamp"),
                        record.get("Source", "Internal simulation"),
                        record.get("Round"),
                        record.get("Selected_Sector"),
                        int(bool(record.get("Detected"))) if isinstance(record.get("Detected"), bool)
                        else record.get("Detected"),
                        int(bool(record.get("Predicted_Active"))) if isinstance(record.get("Predicted_Active"), bool)
                        else record.get("Predicted_Active"),
                        int(bool(record.get("Prediction_Correct"))) if isinstance(record.get("Prediction_Correct"), bool)
                        else record.get("Prediction_Correct"),
                        int(bool(record.get("False_Alarm"))) if isinstance(record.get("False_Alarm"), bool)
                        else record.get("False_Alarm"),
                        record.get("Cumulative_Reward"),
                        record.get("_validation_status", record.get("Processing_Status", "VALID")),
                        json.dumps(raw, ensure_ascii=False, default=str),
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def get_records(self, experiment_id: str | None = None, date_from: str = "",
                    date_to: str = "", source: str = "") -> list[dict[str, Any]]:
        clauses, params = [], []
        if experiment_id:
            clauses.append("Experiment_ID = ?")
            params.append(experiment_id)
        if date_from:
            clauses.append("Timestamp >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("Timestamp <= ?")
            params.append(date_to)
        if source:
            clauses.append("Source = ?")
            params.append(source)
        query = "SELECT * FROM records"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY Timestamp DESC, Round DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def retrieve_records(self, *args, **kwargs):
        return self.get_records(*args, **kwargs)

    def delete_experiment(self, experiment_id: str) -> bool:
        with self.connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            cursor = connection.execute(
                "DELETE FROM experiments WHERE Experiment_ID = ?", (experiment_id,)
            )
        return cursor.rowcount > 0
