"""Focused tests for the registry-driven fixed result layer."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import agent
import fixed_results


class FixedResultTests(unittest.TestCase):
    def _run(self, intent: str, parameters: dict[str, object]) -> tuple[dict, list[str]]:
        queries: list[str] = []

        def chat(_system: str, _user: str) -> tuple[str, dict[str, int]]:
            return json.dumps(parameters), {
                "prompt_tokens": 3,
                "completion_tokens": 2,
                "total_tokens": 5,
            }

        def query(cypher: str) -> list[dict]:
            queries.append(cypher)
            if "AS matches" in cypher:
                return [{"matches": 2 if "C100_2" in cypher else 1}]
            return [{"label": "sample", "hours": 2.0}]

        result = fixed_results.run_fixed_result(
            intent,
            "test request",
            [],
            None,
            {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            chat,
            query,
            resolve_person=lambda name: name,
        )
        return result, queries

    def test_registry_has_all_catalog_intents_and_only_read_queries(self) -> None:
        self.assertEqual(len(fixed_results.REGISTRY), 26)
        parameters = {
            "person_monthly_hours": {"person": "A"},
            "person_did_effort": {"person": "A"},
            "person_delivery_summary": {"person": "A"},
            "person_domain_experience": {"person": "A"},
            "person_efficiency_comparison": {"person": "A"},
            "person_assignment_list": {"person": "A"},
            "personal_workload_mix": {"person": "A"},
            "delivery_priority_list": {"manager": "M"},
            "delivery_overlap_timeline": {"manager": "M"},
            "did_person_contribution": {"did": "C100_1"},
            "did_lot_breakdown": {"did": "C100_1"},
            "did_task_composition": {"did": "C100_1"},
            "did_comparison": {"did_1": "C100_1", "did_2": "C100_2"},
            "delivery_search_results": {"keyword": "final"},
            "study_delivery_timeline": {"study": "C100"},
            "study_task_composition": {"study": "C100"},
            "study_people_and_roles": {"study": "C100"},
            "study_tlf_ranking": {},
            "study_portfolio_table": {},
            "team_member_workload": {"manager": "M"},
            "team_capacity_timeline": {"manager": "M"},
            "lead_contribution_summary": {"ta_lead": "L"},
            "tlf_search_results": {"tlf_keyword": "ae"},
            "expert_recommendation": {"keyword": "ae"},
            "collaboration_network_table": {"manager": "M"},
            "delivery_location_detail": {"did": "C100_1"},
        }
        forbidden = (" CREATE ", " MERGE ", " DELETE ", " SET ", " REMOVE ", " DROP ")
        for intent, values in parameters.items():
            with self.subTest(intent=intent):
                result, queries = self._run(intent, values)
                self.assertEqual(result["response_type"], "fixed_result")
                self.assertEqual(result["intent"], intent)
                self.assertEqual(result["table"]["rows"][0]["hours"], 2.0)
                self.assertEqual(result["usage"]["total_tokens"], 7)
                self.assertTrue(queries[-1].lstrip().startswith("MATCH"))
                self.assertFalse(any(word in queries[-1].upper() for word in forbidden))

    def test_person_is_resolved_and_quotes_are_escaped(self) -> None:
        resolved: list[str] = []

        def resolve(name: str) -> str:
            resolved.append(name)
            return "O'Reilly"

        result = fixed_results.run_fixed_result(
            "person_monthly_hours",
            "hours",
            [],
            None,
            {},
            lambda *_: ('{"person":"nickname"}', {}),
            lambda cypher: [{"month": "2026-09", "hours": 1.0}],
            resolve,
        )
        self.assertEqual(resolved, ["nickname"])
        self.assertIn("O\\'Reilly", result["cypher"])

    def test_low_confidence_classification_falls_back(self) -> None:
        intent, usage = fixed_results.classify(
            "unclear request",
            [],
            lambda *_: ('{"intent":"person_monthly_hours","confidence":"low"}', {"total_tokens": 1}),
        )
        self.assertEqual(intent, "neo4j_query")
        self.assertEqual(usage["total_tokens"], 1)

    def test_invalid_or_missing_parameters_do_not_execute(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid DID"):
            self._run("did_person_contribution", {"did": "bad value"})
        with self.assertRaisesRegex(ValueError, "needs a DID, study, keyword, or status"):
            self._run("delivery_search_results", {})

    def test_did_must_exist_exactly_once_before_template_executes(self) -> None:
        executed: list[str] = []
        with self.assertRaisesRegex(ValueError, "not uniquely found"):
            fixed_results.run_fixed_result(
                "did_lot_breakdown",
                "DID detail",
                [],
                None,
                {},
                lambda *_: ('{"did":"C100_1"}', {}),
                lambda cypher: executed.append(cypher) or [{"matches": 0}],
            )
        self.assertEqual(len(executed), 1)
        self.assertIn("count(DISTINCT d)", executed[0])

    @patch("agent.resolve_person_name", side_effect=lambda name: name)
    @patch("agent.run_cypher", return_value=[{"month": "2026-09", "hours": 5.0}])
    @patch("agent._chat")
    def test_agent_uses_registry_query_not_generated_cypher(
        self, chat, run_cypher, _resolve
    ) -> None:
        chat.side_effect = [
            ('{"intent":"person_monthly_hours"}', {"total_tokens": 2}),
            ('{"person":"Riven"}', {"total_tokens": 3}),
        ]
        with patch("agent.generate_cypher") as generated:
            result = agent.ask("Riven monthly recorded hours")
        self.assertEqual(result["response_type"], "fixed_result")
        self.assertEqual(result["intent"], "person_monthly_hours")
        self.assertEqual(chat.call_count, 2)
        generated.assert_not_called()
        self.assertIn("TIME_ON", run_cypher.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
