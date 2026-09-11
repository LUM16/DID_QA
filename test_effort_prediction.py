"""Unit tests for the DID effort prediction pipeline."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from effort_prediction import (
    TARGET_QUERY,
    TRAINING_QUERY,
    build_feature_row,
    clean_training_records,
    predict_record,
    quality_report,
    train_model,
)


def make_record(index: int, person: str = "Person A") -> dict:
    completion = date(2024, 1, 1) + timedelta(days=index * 14)
    task_count = 5 + index % 5
    return {
        "person": person,
        "did": f"DID-{index:03d}",
        "study": f"STUDY-{index // 2}",
        "completion_date": completion.isoformat(),
        "actual_hours": 4.0 * task_count + (index % 3),
        "task_count": task_count,
        "task_generation_count": task_count,
        "task_qc_count": 0,
        "tlf_count": 2,
        "tlf_generation_count": 2,
        "tlf_qc_count": 0,
        "adam_count": 1,
        "adam_generation_count": 1,
        "adam_qc_count": 0,
        "sdtm_count": 1,
        "sdtm_generation_count": 1,
        "sdtm_qc_count": 0,
        "ta": "Oncology",
        "study_type": "Phase 3",
        "reporting_event": "Primary",
        "draft_or_final": "Final",
        "tlfs": [
            {
                "name": f"TLF-{index % 4}",
                "generation": person,
                "qc": None,
            }
        ],
        "adams": [{"name": "ADSL", "generation": person, "qc": None}],
        "sdtms": [{"name": "DM", "generation": person, "qc": None}],
        "work_on_rel_count": 1,
        "study_count": 1,
        "time_record_count": 1,
    }


class EffortPredictionTests(unittest.TestCase):
    def test_queries_support_csr_work_on_property_names(self) -> None:
        for query in (TRAINING_QUERY, TARGET_QUERY):
            self.assertIn("wo.CSR_TLF_Num_Total", query)
            self.assertIn("wo.CSR_ADaM_Num_Total", query)
            self.assertIn("wo.CSR_SDTM_Num_Total", query)
            self.assertIn("(item:ADaM)", query)
            self.assertNotIn("(item:ADAM)", query)

    def test_features_only_use_strictly_earlier_history(self) -> None:
        previous = make_record(0)
        same_day = make_record(1)
        same_day["completion_date"] = previous["completion_date"]
        target = make_record(2)
        target["completion_date"] = "2024-01-10"

        features, similar = build_feature_row(target, [previous, same_day])

        self.assertEqual(features["person_completed_count"], 2.0)
        self.assertEqual(len(similar), 2)

        target["completion_date"] = previous["completion_date"]
        features, _ = build_feature_row(target, [previous, same_day])
        self.assertEqual(features["person_completed_count"], 0.0)

    def test_quality_and_cleaning_reject_invalid_rows(self) -> None:
        valid = make_record(0)
        invalid = make_record(1)
        invalid["actual_hours"] = 0

        report = quality_report([valid, invalid])
        cleaned = clean_training_records([valid, invalid])

        self.assertEqual(report["non_positive_actual_hours"], 1)
        self.assertEqual(len(cleaned), 1)

    def test_train_save_and_predict(self) -> None:
        records = [
            make_record(index, "Person A" if index % 2 == 0 else "Person B")
            for index in range(30)
        ]
        target = make_record(31, "Person A")
        target.pop("completion_date")
        target.pop("actual_hours")

        with tempfile.TemporaryDirectory() as directory:
            model_path = Path(directory) / "model.joblib"
            training = train_model(records, model_path, minimum_records=20)
            result = predict_record(target, model_path, as_of_date="2026-01-01")
            self.assertTrue(model_path.exists())

        self.assertEqual(training["eligible_records"], 30)
        self.assertGreaterEqual(result["p80_hours"], result["p50_hours"])
        self.assertGreaterEqual(result["p90_hours"], result["p80_hours"])
        self.assertEqual(result["prediction_type"], "total_hours")


if __name__ == "__main__":
    unittest.main()
