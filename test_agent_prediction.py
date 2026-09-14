"""Tests for effort-prediction routing in the Q&A agent."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import agent


PREDICTION = {
    "person": "Chen, Zhenchao (Riven)",
    "did": "C5001001_59",
    "study": "C5001001",
    "prediction_type": "total_hours",
    "as_of_date": "2026-09-11",
    "p50_hours": 14.0,
    "p80_hours": 40.0,
    "p90_hours": 80.0,
    "model_version": "did-effort-ridge-v1",
    "person_completed_did_count": 123,
    "similarity_features": {
        "similar_did_count_ge_85": 3,
        "overall_prior_coverage": 1.0,
        "tlf_unseen_count": 0,
        "adam_unseen_count": 0,
        "sdtm_unseen_count": 0,
    },
    "similar_historical_dids": [
        {
            "did": "C5001001_19",
            "study": "C5001001",
            "completion_date": "2026-08-01",
            "actual_hours": 14.4,
            "overall_similarity": 1.0,
            "tlf_semantic_similarity": 1.0,
            "adam_similarity": 1.0,
            "sdtm_similarity": 1.0,
        }
    ],
    "warnings": [],
}


class AgentPredictionTests(unittest.TestCase):
    def test_prediction_intent_does_not_match_historical_hours(self) -> None:
        self.assertTrue(
            agent._is_effort_prediction_question(
                "预测 Riven 完成 C5001001_59 需要多少工时？"
            )
        )
        self.assertTrue(
            agent._is_effort_prediction_question(
                "Predict Riven's effort for C5001001_59"
            )
        )
        self.assertFalse(
            agent._is_effort_prediction_question(
                "Riven在C5001001_59已经花了多少小时？"
            )
        )

    @patch("agent.predict_effort", return_value=PREDICTION)
    @patch("agent._chat")
    def test_ask_routes_prediction_without_schema_or_cypher(
        self, mock_chat, mock_predict
    ) -> None:
        result = agent.ask("预测 Riven 完成 C5001001_59 需要多少工时？")

        mock_chat.assert_not_called()
        mock_predict.assert_called_once_with(
            person="Riven", did="C5001001_59", as_of_date=None
        )
        self.assertEqual(result["cypher"], "")
        self.assertEqual(result["prediction"]["p50_hours"], 14.0)
        self.assertIn("建议排期（P80）：**40.0 小时**", result["answer"])
        self.assertIn("预测可信度：**高**", result["answer"])
        self.assertIn("人员匹配：输入 `Riven`", result["answer"])
        self.assertIn("TLF 标题近似度 100%", result["answer"])
        self.assertIn("ADaM 相似度 100%", result["answer"])
        self.assertIn("SDTM 相似度 100%", result["answer"])
        self.assertNotIn("总体相似度", result["answer"])
        self.assertEqual(result["usage"]["total_tokens"], 0)

    def test_local_parameter_extraction_supports_english(self) -> None:
        parameters, usage = agent.extract_effort_prediction_parameters(
            "Predict Riven's effort for C5001001_59"
        )

        self.assertEqual(parameters["person"], "Riven")
        self.assertEqual(parameters["did"], "C5001001_59")
        self.assertEqual(usage["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
