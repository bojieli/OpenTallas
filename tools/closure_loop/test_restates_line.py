"""drive-0212 2026-10-09 (coordinator APPROVED): a check that only restates the TT/FF line never blocks the hold ECO."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402

PRE = "python3 -c 'import json; r=json.load(open(\"{RUN}/routes/{LABEL}/corner_sta.json\")); assert "
OWNER = {"name": "owner_TT_FF_nonnegative",
         "cmd": PRE + "r[\"setup_tt\"][\"worst_slack_ps\"] >= 0 and r[\"hold_ff\"][\"worst_slack_ps\"] >= 0' "}
SS15 = {"name": "owner_SS_FF_15ps",
        "cmd": PRE + "r[\"setup_ss\"][\"worst_slack_ps\"] >= 15 and r[\"hold_ff\"][\"worst_slack_ps\"] >= 15' "}


class Restates(unittest.TestCase):
    def test_detect(self):
        self.assertTrue(cl.restates_line(OWNER))
        self.assertTrue(cl.restates_line({"cmd": PRE + "r[\"hold_ff\"][\"worst_slack_ps\"] >= 0' "}))
        self.assertTrue(cl.restates_line({"cmd": "anything", "restates_line": True}))
        self.assertFalse(cl.restates_line(SS15))                         # stricter than the line
        self.assertFalse(cl.restates_line({"cmd": PRE + "r[\"setup_tt\"][\"worst_slack_ps\"] >= 0 and r[\"drc\"] == 0' "}))
        self.assertFalse(cl.restates_line({"cmd": PRE + "r[\"hold_ff\"][\"worst_slack_ps\"] >= 0 or "
                                                        "r[\"setup_tt\"][\"worst_slack_ps\"] >= 0' "}))
        self.assertFalse(cl.restates_line({"cmd": "grep -q 'corner WC reads the TT' {RUN}/routes/{LABEL}/flow.log"}))

    def test_blocking_checks_and_hold_only(self):
        j = {"spec": {"verdict": {"checks": [OWNER, SS15]}}, "failed_checks": ["owner_TT_FF_nonnegative"]}
        self.assertEqual(cl.blocking_checks(j), [])
        m = {"ss_ps": 15.99, "ff_ps": -59.47, "drc": 0}
        self.assertTrue(cl.hold_only(j, m, cl.blocking_checks(j)))
        j["failed_checks"].append("owner_SS_FF_15ps")
        self.assertFalse(cl.hold_only(j, m, cl.blocking_checks(j)))

    def test_verdict_does_not_count_it(self):
        # qfd_emb_pc_00-0ebf67a31-tc: TT +15.99 / FF -59.47 / DRC 0 and only the restating check failed -> hold ECO
        j = {"name": "j", "run": "/r", "host": "h", "events": [], "status": "READY", "benches": {},
             "spec": {"name": "j", "block": "b", "source": {"commit": "abc"}, "stages": {"route": {"cmd": "x"}},
                      "verdict": {"corner_sta": "x", "drc_metrics": "y", "checks": [OWNER]}}}
        started = []
        with patch.object(cl, "adoption_held", return_value=False), \
                patch.object(cl, "get_metrics", return_value={"ss_ps": 15.99, "ff_ps": -59.47, "drc": 0}), \
                patch.object(cl, "remote_ok", return_value=(False, "AssertionError")), \
                patch.object(cl, "benches_done", return_value=True), \
                patch.object(cl, "ssh", return_value=type("R", (), {"stdout": "", "stderr": "", "returncode": 0})()), \
                patch.object(cl, "start_hold_eco", side_effect=lambda j, f, m: started.append(m) or True), \
                patch.object(cl, "routed_ioref", return_value=None, create=True), \
                patch.object(cl, "log"), patch.object(cl, "ledger", create=True):
            try:
                cl.do_verdict(j, None, [])
            except Exception as ex:  # noqa: BLE001  (later verdict plumbing is not under test)
                self.fail(f"do_verdict raised {ex!r}")
        self.assertEqual(j["failed_checks"], [])
        self.assertTrue(j["checks"]["owner_TT_FF_nonnegative"].get("restates_line"))
        self.assertEqual(len(started), 1)


if __name__ == "__main__":
    unittest.main()
