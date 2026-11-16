#!/usr/bin/env python3
"""LAUNCH-ALL-1116 (COORD 11-16, OWNER 11-13 "no launch limits"): every eligible row launches in the same tick; the only bounds are the
in-flight caps and ot-run admission.  max_launch_per_tick is ignored; the pilot cap defaults to unlimited; AP_MAX_SUBMIT defaults high."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def cfg(die="qwen_compute", **kw):
    d = {"enabled": True, "event": "e", "plan": "/p/die_plan.json", "gen_host": "epyc2", "src": "/s", "hosts": ["epyc2"],
         "die_max_inflight": 100000}
    c = {"enabled": True, "max_inflight": 100000, "dies": {die: d}}
    c.update(kw)
    return c


def plan(c, n, die="qwen_compute"):
    status = {"epyc2": {"admit": 400, "run": 0, "load": 1, "cores": 128}}
    picks = [{"item": f"qc_{i}", "kind": "type", "replicas": 1} for i in range(n)]
    with mock.patch.object(KW, "gate", side_effect=lambda c, die, *a: (die == "qwen_compute", "ok")), mock.patch.object(KW, "stop_reason", return_value=""), \
            mock.patch.object(KW, "select", return_value=(picks, {})):
        return KW.plan_dies(None, c, {"items": {}}, [], status, "intel2", probe=False)[1]


class LaunchAll(unittest.TestCase):
    def test_n_eligible_rows_launch_in_one_tick(self):
        self.assertEqual(len(plan(cfg(), 37)), 37)

    def test_max_launch_per_tick_in_the_config_is_ignored(self):
        self.assertEqual(len(plan(cfg(max_launch_per_tick=1), 9)), 9)

    def test_no_default_per_tick_cap(self):
        self.assertNotIn("max_launch_per_tick", KW.DEFAULTS)
        self.assertEqual(len(plan({"enabled": True, "dies": {"qwen_compute": dict(cfg()["dies"]["qwen_compute"], die_max_inflight=100)}}, 30)), 30)

    def test_in_flight_cap_still_bounds(self):
        c = cfg(max_inflight=5)
        self.assertEqual(len(plan(c, 20)), 5)

    def test_pilot_cap_default_is_unlimited(self):
        d = {"pilot_mode": "hold"}
        picked = [{"item": f"qc_{i}", "kind": "type"} for i in range(10)]
        out = KW.pilot_gate(picked, {}, d, "qwen_compute", {"items": {}})
        self.assertEqual(len(out[0] if isinstance(out, tuple) else out), 10)

    def test_autopilot_submit_budget_default(self):
        import autopilot as AP
        self.assertGreaterEqual(AP.MAX_SUBMIT_PER_TICK, 1000)


if __name__ == "__main__":
    unittest.main()
