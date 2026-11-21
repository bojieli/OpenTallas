"""KW-FIX-46 11-12: a visual verdict binds to (row, attempt, form fingerprint); a reused attempt number inherits it only on the same form."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "PHY_NC", "event": "hcut1111", "plan": "/x/die_plan.json", "src": "/s/src_a", "core_kit": "ck", "gen_env": {}}
T_VERDICT = "2026-11-12 01:20"
TS = time.mktime(time.strptime(T_VERDICT, "%Y-%m-%d %H:%M"))


class VerdictFormTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "coord" / "autopilot").mkdir(parents=True)
        (self.root / "coord" / "lanes").mkdir(parents=True)
        self.review = self.root / "coord" / "lanes" / "GEOM-REVIEW.md"
        self.adir = self.root / "hbm_PHY_NC_b864" / "a4"
        self.adir.mkdir(parents=True)
        self.cfg = {"dies": {"hbm": {"gen_hosts": []}}}
        self.p = [mock.patch.object(K, "type_block_sha", lambda *a, **k: "tb1"),
                  mock.patch.object(K.Path, "home", lambda: self.root)]
        for x in self.p:
            x.start()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})
        K._GEOM_CACHE.update(mtime=None, v={}, ts={})

    def tearDown(self):
        for x in self.p:
            x.stop()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})
        K._GEOM_CACHE.update(mtime=None, v={}, ts={})
        self.td.cleanup()

    def verdict(self, v="BAD", when=T_VERDICT, attempt=4):
        with open(self.review, "a") as f:
            f.write(f"- {when} PST GEOM VERDICT [GEOM-VIS-1 viewed] hbm/PHY_NC attempt_{attempt} 3_place (epyc9): {v}. text\n")
        st = os.stat(self.review)
        os.utime(self.review, (st.st_atime, st.st_mtime + 1))          # new mtime: the caches re-read

    def build(self, started, spec=SPEC):
        (self.adir / "spec.json").write_text(json.dumps(spec))
        return {"die": "hbm", "item": "PHY_NC", "kind": "type", "attempt": 4, "started": started, "dir": str(self.adir)}

    def hold(self, rec):
        return K.visual_hold(self.cfg, rec)

    def test_line_time_parsed(self):
        self.assertEqual(K.verdict_line_ts(f"- {T_VERDICT} PST GEOM VERDICT x"), TS)
        self.assertIsNone(K.verdict_line_ts("GEOM VERDICT without a time"))

    def test_verdict_on_this_build_applies_and_binds(self):
        rec = self.build(TS - 3600)
        self.verdict("BAD")
        self.assertTrue(self.hold(rec).startswith("WAIT-FORM"))
        self.assertEqual(K.verdict_form("hbm", "PHY_NC", 4, TS), K.form_fp(SPEC, self.adir / "spec.json"))

    def test_reused_number_same_form_inherits(self):
        self.verdict("BAD")
        self.hold(self.build(TS - 3600))                                    # rated build: form bound
        self.assertTrue(self.hold(self.build(TS + 48000)).startswith("WAIT-FORM"))

    def test_reused_number_other_form_waits_for_review(self):
        self.verdict("BAD")
        self.hold(self.build(TS - 3600))
        h = self.hold(self.build(TS + 48000, dict(SPEC, core_kit="ck2")))
        self.assertTrue(h.startswith("WAIT-VISUAL") and "earlier build" in h, h)

    def test_accept_not_inherited_by_other_form(self):
        self.verdict("GOOD")
        self.assertIsNone(self.hold(self.build(TS - 3600)))
        self.assertTrue(self.hold(self.build(TS + 48000, dict(SPEC, core_kit="ck2"))).startswith("WAIT-VISUAL"))

    def test_unbound_older_verdict_waits_for_review(self):
        self.verdict("BAD")                                                 # the rated build was never seen by the wave
        self.assertTrue(self.hold(self.build(TS + 48000)).startswith("WAIT-VISUAL"))

    def test_no_verdict_still_waits(self):
        self.assertTrue(self.hold(self.build(TS)).startswith("WAIT-VISUAL"))

    def test_form_wait_uses_bound_form(self):
        self.verdict("BAD")
        self.hold(self.build(TS - 3600))                                    # bind the rated form
        rec = self.build(TS + 48000, dict(SPEC, core_kit="ck2"))           # a newer build overwrote the attempt dir
        rec.update(status="FAIL", **{"class": "FLOW"}, event="hcut1111")
        st = {"items": {"hbm|PHY_NC|b864": rec}}
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC)):
            self.assertTrue(K.form_wait(self.cfg, st, "hbm", "PHY_NC", rec))     # candidate = the rated (BAD) form
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC, core_kit="ck3")):
            self.assertFalse(K.form_wait(self.cfg, st, "hbm", "PHY_NC", rec))

    def test_form_wait_unbound_overwritten_spec_never_holds(self):
        self.verdict("BAD")
        rec = self.build(TS + 48000)
        os.utime(self.adir / "spec.json", (TS + 48000, TS + 48000))
        rec.update(status="FAIL", **{"class": "FLOW"}, event="hcut1111")
        st = {"items": {"hbm|PHY_NC|b864": rec}}
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC)):
            self.assertFalse(K.form_wait(self.cfg, st, "hbm", "PHY_NC", rec))

    def test_form_wait_rated_spec_unchanged_still_holds(self):
        rec = self.build(TS - 3600)
        os.utime(self.adir / "spec.json", (TS - 3600, TS - 3600))
        self.verdict("BAD")
        rec.update(status="FAIL", **{"class": "FLOW"}, event="hcut1111")
        st = {"items": {"hbm|PHY_NC|b864": rec}}
        with mock.patch.object(K, "spec_for", lambda *a, **k: dict(SPEC)):
            self.assertTrue(K.form_wait(self.cfg, st, "hbm", "PHY_NC", rec))


if __name__ == "__main__":
    unittest.main()
