"""Unit tests for rule-based DU team recommendation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from du_team_recommendation import (
    DEFAULT_SIMILARITY_CACHE_PATH,
    _resolve_recommendation_cache_path,
    _scope_from_rows,
    recommend_teams,
)


class TeamRecommendationTests(unittest.TestCase):
    def test_default_cache_uses_artifact_resolver(self) -> None:
        resolved_path = Path("C:/temporary/similarity.joblib")
        with patch(
            "du_team_recommendation._resolve_prediction_artifact",
            return_value=resolved_path,
        ) as resolver:
            self.assertEqual(
                _resolve_recommendation_cache_path(DEFAULT_SIMILARITY_CACHE_PATH),
                resolved_path,
            )
        resolver.assert_called_once()

    def test_custom_cache_does_not_use_artifact_resolver(self) -> None:
        custom_path = Path("C:/temporary/custom-similarity.joblib")
        with patch("du_team_recommendation._resolve_prediction_artifact") as resolver:
            self.assertEqual(_resolve_recommendation_cache_path(custom_path), custom_path)
        resolver.assert_not_called()

    def test_scope_rows_read_tlf_and_data_columns(self) -> None:
        scope = _scope_from_rows(
            [{"Title": "AE Summary", "Type": "T", "Source Datasets  ": "ADAE, ADSL"}],
            [
                {"SDTM/ADaM": "ADaM", "Domain/Dataset Name": "ADAE"},
                {"SDTM/ADaM": "SDTM", "Domain/Dataset Name": "AE"},
            ],
        )
        self.assertEqual(scope["tlfs"][0]["name"], "AE Summary")
        self.assertEqual({item["name"] for item in scope["adams"]}, {"ADAE", "ADSL"})
        self.assertEqual(scope["sdtms"][0]["name"], "AE")

    def test_recommendation_prefers_scope_coverage_and_reuses_cache(self) -> None:
        scope = {
            "tlfs": [{"name": "Adverse Events Summary", "type": "T", "source": "ADAE"}],
            "adams": [{"name": "ADAE"}],
            "sdtms": [{"name": "AE"}],
        }
        history = [
            {
                "du_team": "Team A", "did": "DID-A", "completion_date": "2026-09-01",
                "tlfs": [{"name": "Adverse Events Summary", "type": "T", "source": "ADAE"}],
                "adams": [{"name": "ADAE"}], "sdtms": [{"name": "AE"}],
            },
            {
                "du_team": "Team B", "did": "DID-B", "completion_date": "2026-09-01",
                "tlfs": [{"name": "Demographics Summary", "type": "T", "source": "ADSL"}],
                "adams": [{"name": "ADSL"}], "sdtms": [{"name": "DM"}],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            cache_path = Path(directory) / "similarity.joblib"
            first = recommend_teams(scope, history, [], cache_path)
            second = recommend_teams(scope, history, [], cache_path)
        self.assertEqual(first["recommendations"][0]["du_team"], "Team A")
        self.assertEqual(first["recommendations"][0]["missing_adams"], [])
        self.assertEqual(second["cache"]["hits"], 2)


if __name__ == "__main__":
    unittest.main()
