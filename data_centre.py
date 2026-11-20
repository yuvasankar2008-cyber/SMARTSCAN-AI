"""HTTP ingestion and transparent quality analysis for external JSON records."""
from __future__ import annotations

import csv
import email.utils
import http.client
import io
import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

REQUEST_TIMEOUT_SECONDS = 10
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MIN_AUTO_REFRESH_SECONDS = 30
MAX_STORED_BATCHES = 10


class DataSourceError(Exception):
    """A safe, user-facing error from endpoint configuration or response handling."""

    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _retry_delay(retry_after: str | None) -> int:
    if retry_after:
        try:
            seconds = float(retry_after)
            if math.isfinite(seconds):
                return max(1, math.ceil(seconds))
        except ValueError:
            try:
                retry_time = email.utils.parsedate_to_datetime(retry_after)
                if retry_time.tzinfo is None:
                    retry_time = retry_time.replace(tzinfo=timezone.utc)
                return max(
                    1,
                    math.ceil((retry_time - datetime.now(timezone.utc)).total_seconds()),
                )
            except (TypeError, ValueError, OverflowError):
                pass
    return 60

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _ = req, fp, code, msg, headers, newurl
        return None


_SENSITIVE_QUERY_NAMES = {
    "api_key", "apikey", "access_token", "token", "authorization", "secret",
    "client_secret", "key",
}


def endpoint_has_inline_credentials(endpoint: str) -> bool:
    """Detect URL credentials so environment-configured URLs are never echoed to UI."""
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        has_userinfo = parsed.username is not None or parsed.password is not None
        query_names = {
            name.casefold()
            for name, _ in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        }
    except ValueError:
        return False
    return has_userinfo or bool(_SENSITIVE_QUERY_NAMES.intersection(query_names))


def _open_request(request: urllib.request.Request, timeout: int):
    opener = urllib.request.build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


def _validate_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        hostname, _ = parsed.hostname, parsed.port
    except ValueError as exc:
        raise DataSourceError("The API endpoint URL is invalid.") from exc
    if (any(ord(character) < 32 or character.isspace() for character in endpoint)
            or parsed.scheme not in {"http", "https"} or not hostname
            or parsed.username is not None or parsed.password is not None):
        raise DataSourceError(
            "Enter a valid HTTP or HTTPS API URL without embedded credentials."
        )
    if endpoint_has_inline_credentials(endpoint):
        raise DataSourceError(
            "Do not put credentials in the endpoint URL; configure a bearer token instead."
        )
    return endpoint


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON number: {value}")


def _parse_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite.")
    return number


def extract_records(payload: Any) -> list[dict[str, Any]]:
    """Accept an array, a {data: [...]} envelope, or a single record object."""
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and "data" in payload:
        records = payload["data"]
        if not isinstance(records, list):
            raise DataSourceError("The API response 'data' field must be an array.")
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise DataSourceError(
            "The API must return an array of records or an object containing a data array."
        )

    if any(not isinstance(record, dict) for record in records):
        raise DataSourceError("Every item in the API response must be a JSON object.")
    return records


def fetch_records(endpoint: str, token: str = "",
                  timeout: int = REQUEST_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
    """Fetch and validate a bounded JSON response; never substitutes sample data."""
    if timeout <= 0:
        raise DataSourceError("The request timeout must be greater than zero.")
    url = _validate_endpoint(endpoint)
    if any(ord(character) < 32 or ord(character) > 126 for character in token):
        raise DataSourceError("The configured bearer token contains invalid characters.")

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with _open_request(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        status = exc.code
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        exc.close()
        if status in (401, 403):
            raise DataSourceError(
                f"Authentication failed (HTTP {status}); verify the bearer token."
            ) from None
        if status == 429:
            delay = _retry_delay(retry_after)
            raise DataSourceError(
                f"The API rate limit was reached (HTTP 429); retry after at least {delay} seconds.",
                retry_after_seconds=delay,
            ) from None
        raise DataSourceError(f"The API returned HTTP {status}.") from None
    except (socket.timeout, TimeoutError):
        raise DataSourceError(
            f"The API request timed out after {timeout} seconds."
        ) from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise DataSourceError(
                f"The API request timed out after {timeout} seconds."
            ) from None
        raise DataSourceError("Could not connect to the configured API endpoint.") from None
    except http.client.HTTPException:
        raise DataSourceError("The API returned an incomplete or invalid HTTP response.") from None
    except OSError:
        raise DataSourceError("Could not read a response from the API endpoint.") from None

    if len(body) > MAX_RESPONSE_BYTES:
        raise DataSourceError("The API response exceeds the 5 MB size limit.")
    try:
        payload = json.loads(
            body.decode("utf-8"),
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise DataSourceError("The API response was not valid UTF-8 JSON.") from None
    return extract_records(payload)


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _quartile(sorted_values: list[float], fraction: float) -> float:
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _finite_number(value: int | float) -> float | None:
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def analyze_records(records: list[dict[str, Any]], batch_id: str,
                    analyzed_at: str | None = None) -> dict[str, Any]:
    """Summarize quality and IQR outliers; this is not a predictive AI model."""
    field_names = list(dict.fromkeys(
        field for record in records for field in record
    ))
    fields = []
    missing_total = 0
    for field in field_names:
        missing_count = sum(
            field not in record or _is_missing(record[field]) for record in records
        )
        missing_total += missing_count
        type_counts: dict[str, int] = {}
        for record in records:
            if field in record:
                kind = _value_type(record[field])
                type_counts[kind] = type_counts.get(kind, 0) + 1
        fields.append({
            "name": field,
            "types": type_counts,
            "missing": missing_count,
            "present": len(records) - missing_count,
        })

    canonical_records = [
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for record in records
    ]
    duplicate_count = len(canonical_records) - len(set(canonical_records))
    outliers = []
    for field in field_names:
        numeric_values = []
        for index, record in enumerate(records):
            if field not in record or isinstance(record[field], bool):
                continue
            value = record[field]
            if isinstance(value, (int, float)):
                finite_value = _finite_number(value)
                if finite_value is not None:
                    numeric_values.append((index, finite_value))
        if len(numeric_values) < 4:
            continue
        sorted_values = sorted(value for _, value in numeric_values)
        q1 = _quartile(sorted_values, 0.25)
        q3 = _quartile(sorted_values, 0.75)
        spread = q3 - q1
        lower = q1 - 1.5 * spread
        upper = q3 + 1.5 * spread
        flagged = [
            {"record_index": index, "value": value}
            for index, value in numeric_values if value < lower or value > upper
        ]
        if flagged:
            outliers.append({
                "field": field,
                "method": "1.5 × IQR fences; linear-interpolated quartiles",
                "lower_fence": lower,
                "upper_fence": upper,
                "records": flagged,
            })

    warnings = []
    if not records:
        warnings.append("The successful response contained no records.")
    if missing_total:
        warnings.append(f"{missing_total} field value(s) are missing, null, or blank.")
    if duplicate_count:
        warnings.append(f"{duplicate_count} exact duplicate record(s) were found.")
    if outliers:
        warnings.append(f"Potential statistical outliers were found in {len(outliers)} field(s).")

    return {
        "batch_id": batch_id,
        "status": "Complete",
        "analyzed_at": analyzed_at or datetime.now(timezone.utc).isoformat(),
        "processed_records": len(records),
        "missing_values": missing_total,
        "duplicate_records": duplicate_count,
        "fields": fields,
        "outliers": outliers,
        "warnings": warnings,
        "validation_errors": [],
        "method": (
            "Missing means absent, null, or blank string. Duplicates are exact "
            "JSON-object matches regardless of key order. Numeric outliers use "
            "the 1.5 × IQR rule with linear-interpolated quartiles; fields need "
            "at least four numeric values. These are descriptive checks, not AI predictions."
        ),
    }


def _parse_timestamp(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return float(value)
        except (OverflowError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return None


def ordered_record_rows(records: list[dict[str, Any]], batch_id: str) -> list[dict[str, Any]]:
    """Return display-only rows newest-first when a recognized timestamp exists."""
    timestamp_keys = ("timestamp", "time", "created_at", "updated_at", "datetime", "date")
    rows = []
    for index, record in enumerate(records):
        timestamp = None
        for key in timestamp_keys:
            if key in record:
                timestamp = _parse_timestamp(record[key])
                if timestamp is not None:
                    break
        source_id = next(
            (record[key] for key in ("id", "record_id", "uuid", "key")
             if key in record and record[key] is not None
             and not isinstance(record[key], (dict, list))),
            None,
        )
        data_type = next(
            (record[key] for key in ("data_type", "type")
             if key in record and record[key] is not None
             and not isinstance(record[key], (dict, list))),
            "JSON object",
        )
        rows.append({
            "Record ID": str(source_id) if source_id is not None else f"{batch_id[:8]}-{index + 1:04d}",
            "Timestamp": next(
                (record[key] for key in timestamp_keys if key in record), ""
            ),
            "Data type": str(data_type),
            "Fields": ", ".join(record.keys()),
            "_index": index,
            "_sort_timestamp": timestamp,
            "record": record,
        })
    return sorted(
        rows,
        key=lambda row: (
            row["_sort_timestamp"] is not None,
            row["_sort_timestamp"] if row["_sort_timestamp"] is not None else float("-inf"),
            -row["_index"],
        ),
        reverse=True,
    )


def records_to_csv(records: list[dict[str, Any]]) -> str:
    """Export heterogeneous JSON objects with nested values kept as JSON text."""
    fields = list(dict.fromkeys(field for record in records for field in record))
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    if fields:
        writer.writeheader()
        for record in records:
            row = {
                field: (
                    json.dumps(record[field], ensure_ascii=False, sort_keys=True)
                    if isinstance(record.get(field), (dict, list))
                    else record.get(field, "")
                )
                for field in fields
            }
            writer.writerow(row)
    return output.getvalue()


def sample_records() -> list[dict[str, Any]]:
    """Small, fictional data-centre sample for an explicitly selected demo mode."""
    return [
        {"id": "demo-001", "timestamp": "2026-01-20T09:00:00Z", "rack": "A1", "temperature_c": 22.4, "load_pct": 48},
        {"id": "demo-002", "timestamp": "2026-01-20T09:01:00Z", "rack": "A2", "temperature_c": 23.1, "load_pct": 52},
        {"id": "demo-003", "timestamp": "2026-01-20T09:02:00Z", "rack": "B1", "temperature_c": 22.8, "load_pct": 49},
        {"id": "demo-004", "timestamp": "2026-01-20T09:03:00Z", "rack": "B2", "temperature_c": 91.2, "load_pct": 97},
        {"id": "demo-005", "timestamp": "2026-01-20T09:04:00Z", "rack": "C1", "temperature_c": None, "load_pct": 55},
        {"id": "demo-002", "timestamp": "2026-01-20T09:01:00Z", "rack": "A2", "temperature_c": 23.1, "load_pct": 52},
    ]
