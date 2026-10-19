"""Source-level contract tests for browser-side Posit Connect identity lookup."""

from __future__ import annotations

import unittest


class RscIdentityComponentTests(unittest.TestCase):
    def test_component_uses_the_posit_connect_current_user_endpoint(self) -> None:
        with open("rsc_identity_component.py", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("fetch('/__api__/me'", source)
        self.assertIn("credentials: 'same-origin'", source)
        self.assertIn("X-RSC-XSRF", source)

    def test_app_auto_loads_a_saved_token_after_resolving_an_ntid(self) -> None:
        with open("app.py", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("copilot_auto_connect_attempted_ntid", source)
        self.assertIn("load_saved_copilot_token()", source)