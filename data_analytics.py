"""Transparent statistical summaries and labelled synthetic model evaluation."""
from __future__ import annotations

import math
import random
from collections import Counter
from datetime import datetime
from typing import Iterable, Any


def safe_divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def confusion_matrix(records: Iterable[dict[str, Any]],
                     ground_truth_field: str = "Detected",
                     prediction_field: str = "Predicted_Active") -> dict[str, Any]:
    tp = tn = fp = fn = 0
    labelled = 0
    for record in records:
        actual = _bool(record.get(ground_truth_field))
        predicted = _bool(record.get(prediction_field))
        if actual is None or predicted is None:
            continue
        labelled += 1
        if actual and predicted:
            tp += 1
        elif not actual and not predicted:
            tn += 1
        elif actual and not predicted:
            fn += 1
        else:
            fp += 1
    metrics = calculate_metrics(tp, tn, fp, fn)
    return {"TP": tp, "TN": tn, "FP": fp, "FN": fn,
            "labelled": labelled, **metrics}


def calculate_metrics(tp: int, tn: int, fp: int, fn: int) -> dict[str, float | None]:
    total = tp + tn + fp + fn
    accuracy = safe_divide(tp + tn, total)
    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and (precision + recall):
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def calculate_accuracy(tp: int, tn: int, fp: int, fn: int) -> float | None:
    return safe_divide(tp + tn, tp + tn + fp + fn)


def _bool(value: Any) -> bool | None:
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


def numeric_summary(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float | None]]:
    rows = list(records)
    fields = set()
    for row in rows:
        fields.update(row)
    summary = {}
    for field in sorted(fields):
        values = []
        for row in rows:
            value = row.get(field)
            if isinstance(value, bool) or value is None:
                continue
            try:
                number = float(value)
                if math.isfinite(number):
                    values.append(number)
            except (TypeError, ValueError):
                continue
        if not values:
            continue
        average = sum(values) / len(values)
        if len(values) > 1:
            variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
            stddev = math.sqrt(variance)
        else:
            stddev = 0.0
        summary[field] = {
            "count": len(values),
            "average": average,
            "min": min(values),
            "max": max(values),
            "stddev": stddev,
        }
    return summary


def analyze_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    missing = sum(
        value is None or (isinstance(value, str) and not value.strip())
        for row in rows for value in row.values()
    )
    round_counts = Counter(str(row.get("Round", "Missing")) for row in rows)
    sector_counts = Counter(str(row.get("Selected_Sector", "Missing")) for row in rows)
    return {
        "total_records": len(rows),
        "missing_values": missing,
        "numeric": numeric_summary(rows),
        "round_distribution": dict(round_counts),
        "sector_distribution": dict(sector_counts),
        "time_trend": time_trend(rows),
        "evaluation": confusion_matrix(rows),
    }


def time_trend(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    reward_by_time: dict[str, list[float]] = {}
    for row in records:
        timestamp = str(row.get("Timestamp") or "")
        day = timestamp[:10] if len(timestamp) >= 10 else "Unknown"
        counts[day] += 1
        try:
            reward = float(row.get("Cumulative_Reward", 0))
        except (TypeError, ValueError):
            continue
        reward_by_time.setdefault(day, []).append(reward)
    output = []
    for day in sorted(counts):
        rewards = reward_by_time.get(day, [])
        output.append({
            "date": day,
            "record_count": counts[day],
            "average_reward": sum(rewards) / len(rewards) if rewards else None,
        })
    return output


def trend_insights(records: Iterable[dict[str, Any]],
                   missing_values: int = 0,
                   duplicate_records: int = 0) -> list[str]:
    rows = list(records)
    if not rows:
        return ["No records are available for the selected experiment."]
    insights = [f"{len(rows)} records belong to the selected experiment."]
    trend = time_trend(rows)
    if len(trend) >= 2:
        change = trend[-1]["record_count"] - trend[-2]["record_count"]
        direction = "increasing" if change > 0 else "decreasing" if change < 0 else "unchanged"
        insights.append(
            f"Record count is {direction} from {trend[-2]['record_count']} to "
            f"{trend[-1]['record_count']} across the latest two dates."
        )
    if missing_values:
        insights.append(f"{missing_values} missing values were detected.")
    if duplicate_records:
        insights.append(f"{duplicate_records} duplicate records were detected.")
    sectors = Counter(str(row.get("Selected_Sector", "Unknown")) for row in rows)
    if sectors:
        sector, count = sectors.most_common(1)[0]
        insights.append(f"The most frequent selected sector is {sector} ({count} records).")
    return insights


def evaluate_model(records: Iterable[dict[str, Any]], test_fraction: float = 0.25,
                   seed: int = 42) -> dict[str, Any]:
    rows = [row for row in records
            if _bool(row.get("Detected")) is not None
            and _bool(row.get("Predicted_Active")) is not None]
    if len(rows) < 4:
        return {"status": "INSUFFICIENT DATA", "sample_size": len(rows),
                "test_sample_size": 0, "class_distribution": {},
                "confusion_matrix": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
                "accuracy": None, "precision": None, "recall": None, "f1": None,
                "baseline": None, "meaningful": False}
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    rng.shuffle(indices)
    test_size = max(1, int(len(indices) * test_fraction))
    train_indices = indices[test_size:]
    test = [rows[index] for index in indices[:test_size]]
    distribution = dict(Counter(
        "Active" if _bool(row.get("Detected")) else "Inactive" for row in test
    ))
    matrix = confusion_matrix(test)
    majority = Counter(
        _bool(rows[index].get("Detected")) for index in train_indices
    ).most_common(1)[0][0]
    baseline_correct = sum(_bool(row.get("Detected")) == majority for row in test)
    baseline = safe_divide(baseline_correct, len(test))
    return {"status": "EVALUATED", "sample_size": len(rows),
            "test_sample_size": len(test), "class_distribution": distribution,
            "confusion_matrix": matrix, "accuracy": matrix["accuracy"],
            "precision": matrix["precision"], "recall": matrix["recall"],
            "f1": matrix["f1"], "baseline": baseline,
            "meaningful": len(test) >= 10 and len(distribution) >= 2,
            "seed": seed, "test_fraction": test_fraction}
