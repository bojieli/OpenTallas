"""KW-FIX-46 11-12: a BAD visual verdict on an attempt that lives in the GRT-arm dir still holds the row (WAIT-FORM)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "q_su21", "plan": "/x/die_plan.json", "src": "/s/src_a", "core_kit": "ck",
        "gen_env": {"OT_FLOW_TAG": "f", "OT_POROUS_VIEWS": "all"}}


class FormWaitArmTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.row = root / "hbm_q_su21_b65"
        self.arm = root / "hbm_q_su21_b65_grtarm-off"
        for d, sp in ((self.row / "a1", SPEC), (self.arm / "a2", dict(SPEC, gen_env=dict(SPEC["gen_env"], OT_GRT_TRANSITION_MODE="off")))):
            d.mkdir(parents=True)
            (d / "spec.json").write_text(json.dumps(sp))
        self.rec = {"die": "hbm", "item": "q_su21", "event": "hcut1111", "attempt": 1, "status": "FAIL", "class": "FLOW",
                    "dir": str(self.row / "a1")}
        self.arm_rec = {"die": "hbm", "item": "q_su21", "event": "hcut1111", "attempt": 2, "status": "ROUTE-HELD",
                        "dir": str(self.arm / "a2")}
        self.st = {"items": {"hbm|q_su21|b65": self.rec, "hbm|q_su21|b65|grtarm-off": self.arm_rec}}
        self.cfg = {"dies": {"hbm": {"gen_hosts": []}}}
        self.p = [mock.patch.object(K, "type_block_sha", lambda *a, **k: "tb1"),
                  mock.patch.object(K, "WAIT_FORM_LOG", str(root / "wf.tsv")),
                  mock.patch.object(K.Path, "home", lambda: root)]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        self.td.cleanup()

    def wait(self, verdict, cand=SPEC):
        with mock.patch.object(K, "geom_verdicts", lambda: {("hbm", "q_su21"): verdict}), \
                mock.patch.object(K, "spec_for", lambda *a, **k: dict(cand)):
            return K.form_wait(self.cfg, self.st, "hbm", "q_su21", self.rec)

    def test_bad_on_arm_attempt_holds(self):
        self.assertEqual(K.verdict_attempt_dir(self.st, "hbm", "q_su21", self.rec, 2), self.arm / "a2")
        self.assertTrue(self.wait((2, "BAD")))

    def test_bad_on_own_attempt_holds(self):
        self.assertTrue(self.wait((1, "BAD")))

    def test_changed_form_releases(self):
        self.assertFalse(self.wait((2, "BAD"), dict(SPEC, core_kit="ck2")))

    def test_good_releases(self):
        self.assertFalse(self.wait((2, "GOOD")))

    def test_unknown_later_attempt_uses_newest_own_spec(self):
        self.assertEqual(K.verdict_attempt_dir(self.st, "hbm", "q_su21", self.rec, 5), self.row / "a1")
        self.assertTrue(self.wait((5, "BAD")))

    def test_other_event_attempt_not_used(self):
        other = Path(self.td.name) / "hbm_q_su21_old"
        (other / "a3").mkdir(parents=True)
        (other / "a3" / "spec.json").write_text(json.dumps(dict(SPEC, core_kit="old")))
        self.st["items"]["hbm|q_su21|old"] = {"die": "hbm", "item": "q_su21", "event": "d44v", "dir": str(other / "a3")}
        self.assertEqual(K.verdict_attempt_dir(self.st, "hbm", "q_su21", self.rec, 3), self.row / "a1")

    def test_arm_env_is_not_form(self):
        a = K.form_fp(dict(SPEC, gen_env=dict(SPEC["gen_env"], OT_GRT_TRANSITION_MODE="off")), None)
        self.assertEqual(a, K.form_fp(SPEC, None))


if __name__ == "__main__":
    unittest.main()
