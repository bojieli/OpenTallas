"""FLOW-LECGATE-R1 11-21: routed LEC is a binding gate under R-MINIMAL (it was ADVISORY/async: PASS + export with no LEC run)."""
import json

import pytest

import signoff_chain
import unittest

import test_signoff_chain as _t


@pytest.fixture(autouse=True)
def _minimal_profile(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "minimal")
    monkeypatch.delenv("OT_CHAIN_LEC", raising=False)
    monkeypatch.setattr(signoff_chain, "signed", lambda physical: True)
    monkeypatch.setattr(signoff_chain, "signoff_gates", lambda physical: {"setup_tt": "PASS", "hold_ff": "PASS", "drc": "PASS"})
    monkeypatch.setattr(signoff_chain, "_profile_module", lambda: type("P", (), {"judge": staticmethod(
        lambda physical: {"reasons": [], "advisories": [], "achieved_period_ps": 833, "gates": {}, "verdict": "SIGNED"})}))


class MinimalLecGate(unittest.TestCase):
    vehicle = _t.ChainTest.vehicle
    runner = _t.ChainTest.runner

    def verdict(self, k):
        return json.loads(max(k.glob("autopilot_chain*.json")).read_text())

    def test_minimal_runs_routed_lec_and_passes(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b)
        self.assertEqual(signoff_chain.continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertTrue(any("--netlist" in c for c in calls))
        v = self.verdict(k)
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["gates"]["routed_lec"], "PASS")

    def test_minimal_lec_not_equivalent_is_not_pass(self):
        k, b = self.vehicle()
        run, calls = self.runner(k, b, verdict="NOT_EQUIVALENT")
        self.assertNotEqual(signoff_chain.continue_kit(k, "runner.sh", "route", 48, 8, run), 0)
        self.assertEqual(self.verdict(k)["verdict"], "LEC_FAIL")

    def test_async_env_cannot_skip_lec(self):
        import os
        os.environ["OT_CHAIN_LEC"] = "async"
        try:
            k, b = self.vehicle()
            run, calls = self.runner(k, b)
            signoff_chain.continue_kit(k, "runner.sh", "route", 48, 8, run)
            self.assertTrue(any("--netlist" in c for c in calls))
        finally:
            del os.environ["OT_CHAIN_LEC"]
