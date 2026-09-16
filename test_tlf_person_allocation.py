"""Tests for snapshot-only TLF person allocation."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from tlf_person_allocation import (
    DEFAULT_TLF_PERSON_SNAPSHOT_PATH,
    _resolve_snapshot_path,
    allocate_tlf_people,
    load_person_tlf_snapshot,
    refresh_person_tlf_snapshot,
    resolve_team_lead_name,
)


def evidence(person: str, role: str, did: str, title: str = "AE Summary") -> dict:
    return {
        "person": person, "team_lead_name": "Team A", "did": did,
        "completion_date": "2026-09-01", "tlf_name": title, "tlf_type": "T",
        "tlf_source": "ADAE",
        "generation": person if role == "generation" else "",
        "qc": person if role == "qc" else "",
    }


class TlfPersonAllocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path.cwd() / ".test-tlf-person-allocation"
        self.workspace.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        for path in self.workspace.glob("*"):
            path.unlink()
        self.workspace.rmdir()

    def test_snapshot_roundtrip(self) -> None:
        path = self.workspace / "snapshot.joblib"
        with patch(
            "tlf_person_allocation._read_query",
            side_effect=[
                [{"team_lead_name": "Team A"}],
                [evidence("Gen", "generation", "D1")],
                [{"person": "Gen", "active_did_count": 2}],
            ],
        ):
            saved = refresh_person_tlf_snapshot(path)
        history, workload, details = load_person_tlf_snapshot(path)
        self.assertEqual(history[0]["person"], "Gen")
        self.assertEqual(workload[0]["active_did_count"], 2)
        self.assertEqual(saved["history_row_count"], details["history_row_count"])

    def test_default_snapshot_uses_lfs_resolver(self) -> None:
        resolved = Path("C:/temporary/tlf-snapshot.joblib")
        with patch("tlf_person_allocation.Path.exists", return_value=True), patch(
            "tlf_person_allocation._resolve_prediction_artifact", return_value=resolved
        ):
            self.assertEqual(_resolve_snapshot_path(DEFAULT_TLF_PERSON_SNAPSHOT_PATH), resolved)

    def test_team_resolver_accepts_only_actual_candidate(self) -> None:
        good = resolve_team_lead_name(
            "team a", ["Team A"],
            chat_fn=lambda *_args, **_kwargs: ('{"team_lead_name":"Team A"}', {}),
        )
        self.assertEqual(good["team_lead_name"], "Team A")
        with self.assertRaisesRegex(ValueError, "exact Team_Lead_Name"):
            resolve_team_lead_name(
                "team a", ["Team A"],
                chat_fn=lambda *_args, **_kwargs: ('{"team_lead_name":"Invented Team"}', {}),
            )

    def test_distinct_primaries_and_two_backups(self) -> None:
        rows = [
            evidence("G1", "generation", "D1"), evidence("G2", "generation", "D2"),
            evidence("G3", "generation", "D3"), evidence("Q1", "qc", "D4"),
            evidence("Q2", "qc", "D5"), evidence("Q3", "qc", "D6"),
        ]
        result = allocate_tlf_people(
            [{"name": "AE Summary", "type": "T", "source": "ADAE"}],
            "Team A", rows, [], self.workspace / "cache.joblib",
        )
        allocation = result["allocations"][0]
        self.assertNotEqual(
            allocation["generation"]["primary"]["person"], allocation["qc"]["primary"]["person"]
        )
        self.assertEqual(len(allocation["generation"]["backups"]), 2)
        self.assertEqual(len(allocation["qc"]["backups"]), 2)

    def test_workload_and_balancing_change_later_primary(self) -> None:
        rows = [
            evidence("Busy", "generation", "D1", "AE Summary"),
            evidence("Free", "generation", "D2", "AE Summary"),
        ]
        workloads = [{"person": "Busy", "active_did_count": 10}, {"person": "Free", "active_did_count": 0}]
        result = allocate_tlf_people(
            [{"name": "AE Summary", "type": "T", "source": "ADAE"}],
            "Team A", rows, workloads, self.workspace / "cache.joblib",
        )
        self.assertEqual(result["allocations"][0]["generation"]["primary"]["person"], "Free")
        balanced = allocate_tlf_people(
            [
                {"name": "AE Summary", "type": "T", "source": "ADAE"},
                {"name": "Lab Summary", "type": "T", "source": "ADAE"},
            ],
            "Team A",
            [
                evidence("Alpha", "generation", "D3", "AE Summary"),
                evidence("Beta", "generation", "D4", "AE Summary"),
                evidence("Alpha", "generation", "D5", "Lab Summary"),
                evidence("Beta", "generation", "D6", "Lab Summary"),
            ],
            [],
            self.workspace / "balanced-cache.joblib",
        )
        self.assertEqual(balanced["allocations"][0]["generation"]["primary"]["person"], "Alpha")
        self.assertEqual(balanced["allocations"][1]["generation"]["primary"]["person"], "Beta")

    def test_same_person_qc_requires_review_when_no_distinct_qc_evidence(self) -> None:
        rows = [evidence("Only", "generation", "D1"), evidence("Only", "qc", "D2")]
        result = allocate_tlf_people(
            [{"name": "AE Summary", "type": "T", "source": "ADAE"}],
            "Team A", rows, [], self.workspace / "cache.joblib",
        )
        allocation = result["allocations"][0]
        self.assertTrue(allocation["lead_review_required"])
        self.assertEqual(allocation["generation"]["primary"]["person"], "Only")
        self.assertEqual(allocation["qc"]["primary"]["person"], "Only")


if __name__ == "__main__":
    unittest.main()
