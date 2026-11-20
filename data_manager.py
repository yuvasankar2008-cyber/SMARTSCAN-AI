"""Collects and validates simulation or CSV records before SQLite storage."""
from __future__ import annotations

import hashlib
import io
import csv
import uuid
from datetime import datetime, timezone
from typing import Iterable, Any

from data_validator import validate_records, parse_bool
from database_manager import DatabaseManager


class DataManager:
    def __init__(self, db_path: str | None = None):
        self.database = DatabaseManager(db_path) if db_path else DatabaseManager()

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def new_experiment(self, name: str = "Simulation Experiment",
                       source: str = "Internal simulation",
                       scenario: str = "") -> str:
        experiment_id = "EXP-" + uuid.uuid4().hex[:12].upper()
        self.database.create_experiment(
            experiment_id, name, source, scenario, self.utc_now()
        )
        return experiment_id

    @staticmethod
    def normalize_record(record: dict[str, Any], experiment_id: str,
                         source: str) -> dict[str, Any]:
        normalized = dict(record)
        normalized["Experiment_ID"] = experiment_id
        normalized["Source"] = source
        normalized["Timestamp"] = normalized.get("Timestamp") or normalized.get("timestamp") or DataManager.utc_now()
        for key in ("round", "Round"):
            if key in normalized and "Round" not in normalized:
                normalized["Round"] = normalized[key]
        for key in ("selected_sector", "Selected_Sector"):
            if key in normalized and "Selected_Sector" not in normalized:
                normalized["Selected_Sector"] = normalized[key]
        aliases = {
            "detected": "Detected", "predicted_active": "Predicted_Active",
            "prediction_correct": "Prediction_Correct", "false_alarm": "False_Alarm",
            "cumulative_reward": "Cumulative_Reward",
        }
        for alias, canonical in aliases.items():
            if alias in normalized and canonical not in normalized:
                normalized[canonical] = normalized[alias]
        for column in ("Detected", "Predicted_Active", "Prediction_Correct", "False_Alarm"):
            if column in normalized:
                parsed = parse_bool(normalized[column])
                if parsed is not None:
                    normalized[column] = parsed
        if "Cumulative_Reward" in normalized:
            try:
                normalized["Cumulative_Reward"] = float(normalized["Cumulative_Reward"])
            except (TypeError, ValueError):
                pass
        canonical = "|".join(str(normalized.get(field, "")) for field in (
            "Experiment_ID", "Round", "Selected_Sector",
            "Detected", "Predicted_Active", "Prediction_Correct",
            "False_Alarm", "Cumulative_Reward",
        ))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        normalized["Record_ID"] = str(normalized.get("Record_ID") or
                                      normalized.get("record_id") or "REC-" + digest.upper())
        return normalized

    def collect(self, records: Iterable[dict[str, Any]], experiment_id: str,
                source: str) -> dict[str, Any]:
        normalized = [self.normalize_record(record, experiment_id, source)
                      for record in records]
        validation = validate_records(normalized, experiment_id)
        accepted = validation["valid_records"] + validation["warning_records"]
        inserted = self.database.insert_records(accepted)
        for record in validation["rejected_records"]:
            record_id = record.get("Record_ID")
            if record_id:
                rejected_record = dict(record)
                rejected_record["_validation_status"] = "REJECTED"
                self.database.insert_records([rejected_record])
        validation["inserted"] = inserted
        return validation

    def collect_simulation_history(self, sim: Any, experiment_id: str) -> dict[str, Any]:
        rows = []
        for item in sim.history:
            rows.append({
                "Round": item["round"],
                "Selected_Sector": item["selected"],
                "Detected": item["detected"],
                "Predicted_Active": item["predicted_active"],
                "Prediction_Correct": item["prediction_correct"],
                "False_Alarm": item["false_alarm"],
                "Cumulative_Reward": item["reward"],
                "Timestamp": self.utc_now(),
            })
        return self.collect(rows, experiment_id, "Internal simulation")

    def import_csv(self, csv_text: str, experiment_name: str = "CSV Upload") -> dict[str, Any]:
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            return {
                "experiment_id": None,
                "total_received": 0,
                "valid_records": [],
                "warning_records": [],
                "rejected_records": [],
                "valid": 0,
                "warning": 0,
                "rejected": 0,
                "duplicate_records": 0,
                "missing_values": 0,
                "data_quality": 0.0,
                "report": [{"Row": 1, "Status": "REJECTED",
                            "Errors": "CSV file is empty or has no header.",
                            "Warnings": ""}],
                "method": "Data quality = 100 × (VALID + WARNING records) / received records.",
            }
        experiment_id = self.new_experiment(experiment_name, "CSV upload")
        result = self.collect(list(reader), experiment_id, "CSV upload")
        result["experiment_id"] = experiment_id
        return result
