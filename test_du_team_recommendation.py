"""Unit tests for rule-based DU team recommendation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from du_team_recommendation import _scope_from_rows, recommend_teams


class TeamRecommendationTests(unittest.TestCase):
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
