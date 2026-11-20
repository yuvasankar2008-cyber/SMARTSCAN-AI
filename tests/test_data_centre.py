import json
import socket
import unittest
import urllib.error
from unittest.mock import patch

from data_centre import (
    DataSourceError,
    analyze_records,
    endpoint_has_inline_credentials,
    extract_records,
    fetch_records,
    ordered_record_rows,
    records_to_csv,
    sample_records,
)


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        _ = _exc_type, _exc_value, _traceback
        return False

    def read(self, size=-1):
        return self.body[:size]


class DataCentreTests(unittest.TestCase):
    def fetch_payload(self, payload):
        body = json.dumps(payload).encode("utf-8")
        with patch("data_centre._open_request", return_value=FakeResponse(body)):
            return fetch_records("https://data.example.test/records")

    def test_fetch_accepts_array_and_data_envelope(self):
        self.assertEqual(self.fetch_payload([{"id": 1}]), [{"id": 1}])
        self.assertEqual(self.fetch_payload({"data": [{"id": 2}]}), [{"id": 2}])

    def test_fetch_accepts_single_object_and_empty_dataset(self):
        self.assertEqual(self.fetch_payload({"id": "one"}), [{"id": "one"}])
        self.assertEqual(self.fetch_payload([]), [])
        self.assertEqual(self.fetch_payload({"data": []}), [])

    def test_bearer_token_is_sent_only_as_authorization_header(self):
        with patch(
            "data_centre._open_request",
            return_value=FakeResponse(b'[{"ok":true}]'),
        ) as open_request:
            self.assertEqual(
                fetch_records("https://data.example.test/records", token="test-token"),
                [{"ok": True}],
            )
        request = open_request.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertNotIn("test-token", request.full_url)

    def test_authentication_failure_is_safe_and_explicit(self):
        error = urllib.error.HTTPError(
            "https://data.example.test/records", 401, "Unauthorized", {}, None
        )
        with patch("data_centre._open_request", side_effect=error):
            with self.assertRaisesRegex(DataSourceError, "Authentication failed"):
                fetch_records("https://data.example.test/records", token="private-token")
        error.close()

    def test_timeout_and_http_errors_are_reported(self):
        with patch("data_centre._open_request", side_effect=socket.timeout("private")):
            with self.assertRaisesRegex(DataSourceError, "timed out"):
                fetch_records("https://data.example.test/records")
        rate_limit = urllib.error.HTTPError(
            "https://data.example.test/records", 429, "Too Many Requests",
            {"Retry-After": "9"}, None
        )
        with patch("data_centre._open_request", side_effect=rate_limit):
            with self.assertRaisesRegex(DataSourceError, "rate limit") as raised:
                fetch_records("https://data.example.test/records")
        self.assertEqual(raised.exception.retry_after_seconds, 9)
        rate_limit.close()

    def test_malformed_json_and_invalid_response_shapes_are_rejected(self):
        with patch("data_centre._open_request", return_value=FakeResponse(b"{invalid")):
            with self.assertRaisesRegex(DataSourceError, "valid UTF-8 JSON"):
                fetch_records("https://data.example.test/records")
        with patch(
            "data_centre._open_request",
            return_value=FakeResponse(b'{"value":1e999}'),
        ):
            with self.assertRaisesRegex(DataSourceError, "valid UTF-8 JSON"):
                fetch_records("https://data.example.test/records")
        for payload in (None, "records", {"data": {}}, [{"id": 1}, "not an object"]):
            with self.subTest(payload=payload):
                with self.assertRaises(DataSourceError):
                    extract_records(payload)

    def test_endpoint_and_token_validation(self):
        self.assertTrue(endpoint_has_inline_credentials(
            "https://data.example.test/records?api_key=private"
        ))
        self.assertFalse(endpoint_has_inline_credentials(
            "https://data.example.test/records?region=north"
        ))
        with self.assertRaisesRegex(DataSourceError, "HTTP or HTTPS"):
            fetch_records("file:///private/data.json")
        with self.assertRaisesRegex(DataSourceError, "credentials in the endpoint URL"):
            fetch_records("https://data.example.test/records?api_key=private")
        with self.assertRaisesRegex(DataSourceError, "invalid characters"):
            fetch_records("https://data.example.test/records", token="bad\nheader")

    def test_analysis_reports_missing_duplicates_fields_and_iqr_outliers(self):
        records = sample_records()
        analysis = analyze_records(records, "batch-123", "2026-01-20T10:00:00+00:00")
        self.assertEqual(analysis["batch_id"], "batch-123")
        self.assertEqual(analysis["status"], "Complete")
        self.assertEqual(analysis["processed_records"], len(records))
        self.assertEqual(analysis["duplicate_records"], 1)
        self.assertGreater(analysis["missing_values"], 0)
        self.assertEqual(analysis["analyzed_at"], "2026-01-20T10:00:00+00:00")
        self.assertIn("temperature_c", [field["name"] for field in analysis["fields"]])
        self.assertIn("1.5 × IQR", analysis["outliers"][0]["method"])
        self.assertTrue(any("duplicate" in warning for warning in analysis["warnings"]))
        self.assertIn("not AI predictions", analysis["method"])

    def test_analysis_handles_empty_batch_and_key_order_insensitive_duplicates(self):
        self.assertEqual(analyze_records([], "empty")["warnings"], [
            "The successful response contained no records."
        ])
        result = analyze_records([{"a": 1, "b": 2}, {"b": 2, "a": 1}], "dupes")
        self.assertEqual(result["duplicate_records"], 1)

    def test_records_are_sorted_by_timestamp_and_csv_preserves_nested_json(self):
        records = [
            {"id": "old", "timestamp": "2026-01-01T00:00:00Z"},
            {"id": "new", "timestamp": "2026-01-03T00:00:00Z", "meta": {"ok": True}},
            {"id": "undated"},
        ]
        rows = ordered_record_rows(records, "batch")
        self.assertEqual([row["Record ID"] for row in rows], ["new", "old", "undated"])
        csv_text = records_to_csv(records)
        self.assertIn("id,timestamp,meta", csv_text)
        self.assertIn('"{""ok"": true}"', csv_text)


if __name__ == "__main__":
    unittest.main()
