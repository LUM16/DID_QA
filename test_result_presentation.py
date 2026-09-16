"""Tests for safe post-query result presentation."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import agent
from result_presentation import select_result_presentation, validate_presentation_selection


class ResultPresentationTests(unittest.TestCase):
    def test_chart_selection_uses_only_returned_fields_and_keeps_table_fallback(self) -> None:
        rows = [{"month": "2026-08", "hours": 10.5}, {"month": "2026-09", "hours": 12.0}]

        result, usage, warning = select_result_presentation(
            "Show the monthly trend",
            rows,
            lambda *_: (
                json.dumps(
                    {
                        "display_type": "line",
                        "x_field": "month",
                        "y_fields": ["hours"],
                        "series_field": None,
                        "table_fields": ["month", "hours"],
                    }
                ),
                {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            ),
        )

        self.assertEqual(result["chart_type"], "line")
        self.assertEqual(result["table"]["rows"], rows)
        self.assertEqual(result["data_note"], "Recorded TIME_ON hours.")
        self.assertEqual(usage["total_tokens"], 5)
        self.assertIsNone(warning)

    def test_invalid_fields_or_nonfinite_chart_values_are_rejected(self) -> None:
        self.assertIsNone(
            validate_presentation_selection(
                {
                    "display_type": "bar",
                    "x_field": "person",
                    "y_fields": ["invented_hours"],
                    "series_field": None,
                    "table_fields": ["person"],
                },
                [{"person": "A", "hours": 1.0}],
            )
        )
        self.assertIsNone(
            validate_presentation_selection(
                {
                    "display_type": "bar",
                    "x_field": "person",
                    "y_fields": ["hours"],
                    "series_field": None,
                    "table_fields": ["person", "hours"],
                },
                [{"person": "A", "hours": float("nan")}],
            )
        )

    def test_table_selection_uses_deterministic_task_count_note(self) -> None:
        rows = [{"person": "A", "task_count": 4}]
        result, _, warning = select_result_presentation(
            "Show assignments",
            rows,
            lambda *_: (
                '{"display_type":"kpi_table","table_fields":["person","task_count"]}',
                {},
            ),
        )
        self.assertEqual(result["display_type"], "kpi_table")
        self.assertEqual(result["data_note"], "Assigned task count.")
        self.assertIn("table", result)
        self.assertIsNone(warning)

    def test_line_chart_requires_a_month_or_date_x_field(self) -> None:
        self.assertIsNone(
            validate_presentation_selection(
                {
                    "display_type": "line",
                    "x_field": "person",
                    "y_fields": ["hours"],
                    "series_field": None,
                    "table_fields": ["person", "hours"],
                },
                [{"person": "A", "hours": 2.0}],
            )
        )

    @patch("agent.run_cypher", return_value=[{"study": "C100", "delivery_count": 2}])
    @patch("agent._chat")
    def test_failed_presentation_selection_does_not_fail_generic_qa(
        self, mock_chat, mock_run_cypher
    ) -> None:
        mock_chat.side_effect = [
            ("```cypher\nMATCH (s:Study) RETURN s.Name AS study, 2 AS delivery_count\n```", {}),
            ("C100 has two deliveries.", {"total_tokens": 4}),
            RuntimeError("presentation service unavailable"),
        ]
        with patch(
            "agent.classify_effort_prediction_intent",
            return_value=(False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
        ):
            result = agent.ask("List study delivery counts", schema={"labels": []})

        self.assertIsNone(result["error"])
        self.assertEqual(result["answer"], "C100 has two deliveries.")
        self.assertEqual(result["rows"], [{"study": "C100", "delivery_count": 2}])
        self.assertIsNone(result["visualization"])
        self.assertEqual(
            result["presentation_warning"],
            "Presentation is unavailable; showing the text answer only.",
        )
        mock_run_cypher.assert_called_once()


if __name__ == "__main__":
    unittest.main()
