"""KW-FIX-46 11-12: a kit that fails the same tool error on two attempts in a row holds as FLOW-REPEAT until its form changes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "PHY_NC", "event": "hcut1111", "plan": "/x/die_plan.json", "src": "/s/src_a", "core_kit": "ck",
        "gen_env": {"OT_FLOW_TAG": "f"}}
ERR = "Error: floorplan.tcl, 91 IFP-0002"
WHY = "tool / Tcl error @place: " + ERR


class FlowRepeatTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.row = root / "hbm_PHY_NC_b864"
        (root / "coord" / "autopilot").mkdir(parents=True)
        for n in (1, 2):
            self.attempt(n, ERR)
        self.rec = {"die": "hbm", "item": "PHY_NC", "event": "hcut1111", "attempt": 2, "status": "FAIL", "class": "FLOW",
                    "reason": WHY, "dir": str(self.row / "a2")}
        self.st = {"items": {"hbm|PHY_NC|b864": self.rec}}
        self.cfg = {"dies": {"hbm": {"gen_hosts": [], "retry": ["PHY_NC@2"]}}}
        self.p = [mock.patch.object(K, "type_block_sha", lambda *a, **k: "tb1"),
                  mock.patch.object(K.Path, "home", lambda: root)]
        for x in self.p:
            x.start()

    def attempt(self, n, err, spec=SPEC, stage="place"):
        d = self.row / f"a{n}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(spec))
        (d / "result.json").write_text(json.dumps({"stage": stage, "verdict": "FAIL", "errors": err, "tail": ""}))

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.td.cleanup()

    def rep(self, cand=SPEC):
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(cand)):
            return K.flow_repeat(self.cfg, self.st, "hbm", "PHY_NC", self.rec)

    def test_classify_reads_the_same_reason(self):
        self.assertEqual(K.attempt_fail_sig(self.row / "a1"), ("FLOW", WHY))

    def test_same_error_twice_holds(self):
        self.assertTrue(self.rep())
        self.assertIn("PHY_NC", (Path(self.td.name) / "coord" / "autopilot" / K.FLOW_REPEAT_LOG).read_text())

    def test_changed_form_releases(self):
        self.assertFalse(self.rep(dict(SPEC, core_kit="ck2")))

    def test_different_error_releases(self):
        self.attempt(1, "Error: macro_place.tcl, 12 MPL-0034")
        self.assertFalse(self.rep())

    def test_first_attempt_never_held(self):
        self.rec["attempt"] = 1
        self.rec["dir"] = str(self.row / "a1")
        self.assertFalse(self.rep())

    def test_previous_pass_releases(self):
        (self.row / "a1" / "result.json").write_text(json.dumps({"stage": "geom", "verdict": "PASS"}))
        self.assertFalse(self.rep())

    def test_other_event_previous_attempt_is_no_repeat(self):
        self.attempt(1, ERR, dict(SPEC, event="d44v"))
        self.assertFalse(self.rep())

    def test_infra_and_timing_not_held(self):
        for cls in ("INFRA", "TIMING", "ROUTING"):
            self.rec["class"] = cls
            self.assertFalse(self.rep(), cls)

    def test_flow_fix_retry_releases(self):
        self.cfg["dies"]["hbm"]["retry_fix"] = {"PHY_NC@2": "FLOW-FIX: c87611d612d9 gen_phys edge core margin landed"}
        self.assertFalse(self.rep())
        self.cfg["dies"]["hbm"]["retry_fix"] = {"PHY_NC@2": "retry"}
        self.assertTrue(self.rep())

    def test_unreadable_spec_never_holds(self):
        (self.row / "a2" / "spec.json").unlink()
        self.assertFalse(self.rep())


if __name__ == "__main__":
    unittest.main()
