"""Unit tests for the DID effort prediction pipeline."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from effort_prediction import (
    TARGET_QUERY,
    TRAINING_QUERY,
    _load_similarity_cache,
    _save_similarity_cache,
    _similarity_candidates,
    _tlf_semantic_similarity,
    _title_similarity,
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
    def test_title_similarity_matches_reworded_tlf_titles(self) -> None:
        similar = _title_similarity(
            "Summary of Treatment-Emergent Adverse Events",
            "Treatment Emergent Adverse Event Summary",
        )
        unrelated = _title_similarity(
            "Summary of Treatment-Emergent Adverse Events",
            "Participant Disposition by Country",
        )

        self.assertGreater(similar, 0.70)
        self.assertLess(unrelated, 0.30)

    def test_tlf_semantic_matching_is_one_to_one(self) -> None:
        target = [
            {"name": "Adverse Event Summary", "type": "Table", "source": "ADAE"},
            {"name": "Adverse Events Summary", "type": "Table", "source": "ADAE"},
        ]
        history = [
            {"name": "Summary of Adverse Events", "type": "Table", "source": "ADAE"}
        ]

        score, coverage = _tlf_semantic_similarity(target, history)

        self.assertLessEqual(score, 0.5)
        self.assertEqual(coverage, 0.5)

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
        self.assertIn("max_tlf_semantic_similarity", features)
        self.assertIn("tlf_semantic_similarity", similar[0])

        target["completion_date"] = previous["completion_date"]
        features, _ = build_feature_row(target, [previous, same_day])
        self.assertEqual(features["person_completed_count"], 0.0)

    def test_repeated_similarity_features_summarize_history(self) -> None:
        history = [make_record(index) for index in range(4)]
        hours = [10.0, 20.0, 30.0, 40.0]
        task_counts = [2.0, 4.0, 5.0, 8.0]
        for row, actual_hours, task_count in zip(history, hours, task_counts):
            row["actual_hours"] = actual_hours
            row["task_count"] = task_count
            row["tlfs"][0]["name"] = "Adverse Event Summary"

        target = make_record(10)
        target["tlfs"][0]["name"] = "Adverse Event Summary"
        features, similar = build_feature_row(target, history)

        self.assertEqual(len(similar), 4)
        self.assertEqual(features["top3_combined_similarity_mean"], 1.0)
        self.assertEqual(features["top5_combined_similarity_mean"], 1.0)
        self.assertEqual(features["similar_did_count_ge_70"], 4.0)
        self.assertEqual(features["similar_did_count_ge_85"], 4.0)
        self.assertAlmostEqual(features["weighted_similar_hours"], 25.0)
        self.assertAlmostEqual(features["weighted_similar_hours_per_task"], 5.25)
        self.assertEqual(features["latest_similar_hours"], 40.0)
        self.assertAlmostEqual(features["similar_hours_trend"], 10.0)

    def test_candidate_filter_keeps_only_recent_unrelated_history(self) -> None:
        history = [make_record(index) for index in range(80)]
        for index, row in enumerate(history):
            row["study"] = f"HISTORY-{index}"
            row["ta"] = f"TA-{index}"
            row["tlfs"][0]["name"] = f"TLF-{index}"
            row["adams"][0]["name"] = f"ADAM-{index}"
            row["sdtms"][0]["name"] = f"SDTM-{index}"
        target = make_record(100)
        target["study"] = "TARGET-STUDY"
        target["ta"] = "TARGET-TA"
        target["tlfs"][0]["name"] = "TARGET-TLF"
        target["adams"][0]["name"] = "TARGET-ADAM"
        target["sdtms"][0]["name"] = "TARGET-SDTM"

        candidates = _similarity_candidates(target, history)

        self.assertEqual(len(candidates), 50)
        self.assertEqual(candidates[-1]["did"], history[-1]["did"])

    def test_similarity_cache_persists_pair_results(self) -> None:
        target = make_record(5)
        history = make_record(1)

        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "similarity.joblib"
            cache = _load_similarity_cache(cache_path)
            build_feature_row(target, [history], cache)
            self.assertEqual(cache["misses"], 1)
            _save_similarity_cache(cache, cache_path)

            reloaded = _load_similarity_cache(cache_path)
            build_feature_row(target, [history], reloaded)

        self.assertEqual(reloaded["hits"], 1)
        self.assertEqual(reloaded["misses"], 0)

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
        self.assertIn("similar_hours_trend", result["similarity_features"])

if __name__ == "__main__":
    unittest.main()
