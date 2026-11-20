"""Validation rules for SMARTSCAN educational simulation records."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Iterable, Any


REQUIRED_COLUMNS = (
    "Round",
    "Selected_Sector",
    "Detected",
    "Predicted_Active",
    "Prediction_Correct",
    "False_Alarm",
    "Cumulative_Reward",
)


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().casefold()
        if text in ("true", "1", "yes", "y"):
            return True
        if text in ("false", "0", "no", "n"):
            return False
    return None


def parse_timestamp(value: Any) -> str | None:
    if is_missing(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
        return text
    return None


def canonical_record(record: dict[str, Any]) -> str:
    if record.get("Record_ID"):
        return str(record["Record_ID"])
    fields = ("Experiment_ID", "Round", "Selected_Sector", "Detected",
              "Predicted_Active", "Prediction_Correct", "False_Alarm",
              "Cumulative_Reward", "Timestamp")
    return "|".join("" if is_missing(record.get(field)) else str(record[field])
                    for field in fields)


def validate_records(records: Iterable[dict[str, Any]], experiment_id: str | None = None,
                     required_columns: Iterable[str] = REQUIRED_COLUMNS) -> dict[str, Any]:
    """Return VALID/WARNING/REJECTED records and transparent quality counts.

    Quality percentage = 100 * (valid + warning records) / received records.
    Rejected records contain structural or invalid-value failures.
    """
    rows = list(records)
    missing_required = [name for name in required_columns
                        if not any(name in row for row in rows)]
    seen: set[str] = set()
    valid, warning, rejected, report = [], [], [], []
    missing_values = 0
    duplicate_records = 0

    for index, original in enumerate(rows):
        record = dict(original)
        errors, warnings = [], []

        if missing_required:
            errors.append("Missing required columns: " + ", ".join(missing_required))

        for column in required_columns:
            if column not in record or is_missing(record[column]):
                missing_values += 1
                errors.append(f"Missing value: {column}")

        if "Round" in record and not is_missing(record["Round"]):
            try:
                round_number = int(record["Round"])
                if isinstance(record["Round"], float) and not record["Round"].is_integer():
                    raise ValueError
                if isinstance(record["Round"], str) and not record["Round"].strip().isdigit():
                    raise ValueError
                if round_number < 1:
                    errors.append("Invalid round number")
            except (TypeError, ValueError):
                errors.append("Invalid round number")

        for column in ("Detected", "Predicted_Active", "Prediction_Correct", "False_Alarm"):
            if column in record and not is_missing(record[column]):
                parsed = parse_bool(record[column])
                if parsed is None:
                    errors.append(f"Invalid boolean value: {column}")

        if "Cumulative_Reward" in record and not is_missing(record["Cumulative_Reward"]):
            try:
                float(record["Cumulative_Reward"])
            except (TypeError, ValueError):
                errors.append("Invalid cumulative reward")

        if "Timestamp" in record and not is_missing(record["Timestamp"]):
            if parse_timestamp(record["Timestamp"]) is None:
                errors.append("Invalid timestamp")
        elif "Timestamp" not in record:
            warnings.append("Timestamp is missing")

        if "Experiment_ID" in record:
            if is_missing(record["Experiment_ID"]):
                errors.append("Missing value: Experiment_ID")
            elif experiment_id and str(record["Experiment_ID"]) != str(experiment_id):
                errors.append("Incorrect experiment ID")

        if "Selected_Sector" in record and not is_missing(record["Selected_Sector"]):
            sector = str(record["Selected_Sector"]).strip()
            if not sector:
                errors.append("Missing value: Selected_Sector")

        canonical = canonical_record(record)
        if canonical in seen:
            duplicate_records += 1
            warnings.append("Duplicate record")
        seen.add(canonical)

        item = dict(record)
        item["_validation_errors"] = errors
        item["_validation_warnings"] = warnings
        if errors:
            item["_validation_status"] = "REJECTED"
            rejected.append(item)
            status = "REJECTED"
        elif warnings:
            item["_validation_status"] = "WARNING"
            warning.append(item)
            status = "WARNING"
        else:
            item["_validation_status"] = "VALID"
            valid.append(item)
            status = "VALID"
        report.append({
            "Row": index + 1,
            "Status": status,
            "Errors": "; ".join(errors),
            "Warnings": "; ".join(warnings),
        })

    received = len(rows)
    accepted = len(valid) + len(warning)
    return {
        "total_received": received,
        "valid_records": valid,
        "warning_records": warning,
        "rejected_records": rejected,
        "valid": len(valid),
        "warning": len(warning),
        "rejected": len(rejected),
        "duplicate_records": duplicate_records,
        "missing_values": missing_values,
        "data_quality": round(100 * accepted / received, 2) if received else 100.0,
        "report": report,
        "method": "Data quality = 100 × (VALID + WARNING records) / received records.",
    }


def records_to_csv(records: Iterable[dict[str, Any]]) -> str:
    rows = list(records)
    if not rows:
        return ""
    fields = list(dict.fromkeys(field for row in rows for field in row
                                if not field.startswith("_")))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: row.get(key, "") for key in fields} for row in rows)
    return output.getvalue()
