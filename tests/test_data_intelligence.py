import csv
import io
import tempfile
import unittest
from pathlib import Path

from data_manager import DataManager
from data_validator import validate_records
from database_manager import DatabaseManager
from data_analytics import calculate_metrics, evaluate_model


class DataIntelligenceTests(unittest.TestCase):
    def test_database_creation_insertion_retrieval_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            db = DatabaseManager(path)
            db.create_experiment("EXP-A", "A", "Internal simulation")
            record = {
                "Record_ID": "REC-1", "Experiment_ID": "EXP-A",
                "Timestamp": "2026-01-01T00:00:00Z", "Source": "Internal simulation",
                "Round": 1, "Selected_Sector": "Alpha", "Detected": True,
                "Predicted_Active": True, "Prediction_Correct": True,
                "False_Alarm": False, "Cumulative_Reward": 30,
                "_validation_status": "VALID",
            }
            self.assertEqual(db.insert_record(record), True)
            self.assertEqual(len(db.get_records("EXP-A")), 1)
            reopened = DatabaseManager(path)
            self.assertEqual(len(reopened.get_records("EXP-A")), 1)

    def test_duplicate_prevention_and_experiment_separation(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DatabaseManager(Path(directory) / "test.db")
            db.create_experiment("EXP-A", "A", "Internal simulation")
            db.create_experiment("EXP-B", "B", "CSV upload")
            record = {"Record_ID": "REC-X", "Experiment_ID": "EXP-A",
                      "Round": 1, "Source": "Internal simulation",
                      "_validation_status": "VALID"}
            db.insert_record(record)
            db.insert_record(record)
            record_b = dict(record, Record_ID="REC-Y", Experiment_ID="EXP-B")
            db.insert_record(record_b)
            self.assertEqual(len(db.get_records("EXP-A")), 1)
            self.assertEqual(len(db.get_records("EXP-B")), 1)

    def test_csv_validation_missing_invalid_and_duplicate_records(self):
        rows = [
            {"Round": 1, "Selected_Sector": "Alpha", "Detected": "true",
             "Predicted_Active": "true", "Prediction_Correct": "true",
             "False_Alarm": "false", "Cumulative_Reward": "10"},
            {"Round": 0, "Selected_Sector": "Bravo", "Detected": "maybe",
             "Predicted_Active": "", "Prediction_Correct": "false",
             "False_Alarm": "false", "Cumulative_Reward": "bad"},
            {"Round": 1, "Selected_Sector": "Alpha", "Detected": "true",
             "Predicted_Active": "true", "Prediction_Correct": "true",
             "False_Alarm": "false", "Cumulative_Reward": "10"},
        ]
        result = validate_records(rows)
        self.assertEqual(result["total_received"], 3)
        self.assertGreater(result["missing_values"], 0)
        self.assertGreater(result["rejected"], 0)
        self.assertGreaterEqual(result["duplicate_records"], 1)

    def test_csv_import_and_retrieval(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = DataManager(str(Path(directory) / "test.db"))
            text = "Round,Selected_Sector,Detected,Predicted_Active,Prediction_Correct,False_Alarm,Cumulative_Reward\n"
            text += "1,Alpha,true,true,true,false,30\n"
            result = manager.import_csv(text)
            self.assertEqual(result["total_received"], 1)
            experiment_id = result["experiment_id"]
            self.assertIsNotNone(experiment_id)
            self.assertEqual(len(manager.database.get_records(experiment_id)), 1)

    def test_zero_denominator_and_accuracy_calculation(self):
        metrics = calculate_metrics(0, 0, 0, 0)
        self.assertIsNone(metrics["accuracy"])
        self.assertIsNone(metrics["precision"])
        self.assertIsNone(metrics["recall"])
        self.assertIsNone(metrics["f1"])
        metrics = calculate_metrics(1, 2, 1, 1)
        self.assertAlmostEqual(metrics["accuracy"], 3 / 5)
        self.assertAlmostEqual(metrics["precision"], 1 / 2)
        self.assertAlmostEqual(metrics["recall"], 1 / 2)

    def test_evaluation_empty_insufficient_and_sufficient(self):
        empty = evaluate_model([])
        self.assertEqual(empty["status"], "INSUFFICIENT DATA")
        rows = [
            {"Detected": i % 2 == 0, "Predicted_Active": i % 2 == 0}
            for i in range(20)
        ]
        result = evaluate_model(rows, seed=7)
        self.assertEqual(result["status"], "EVALUATED")
        self.assertEqual(result["sample_size"], 20)
        self.assertGreater(result["test_sample_size"], 0)
        self.assertTrue(result["confusion_matrix"]["TP"] >= 0)


if __name__ == "__main__":
    unittest.main()
