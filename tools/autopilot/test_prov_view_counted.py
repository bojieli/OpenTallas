#!/usr/bin/env python3
"""KW-FIX-35-V 11-08: a child built on its COUNTED signed view is FINAL (the type counts on its own sign-off);
any other routed candidate stays PROVISIONAL.  Also the prelint count note reads the release count's cache."""
import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prov_view as P
import kit_wave as K

PINS = [dict(name="a", x=0.1, y=5.0, layer="M4"), dict(name="y", x=99.9, y=5.0, layer="M4"),
        dict(name="clk", x=50.0, y=0.1, layer="M5")]
DIRS = {"a": "INPUT", "y": "OUTPUT", "clk": "INPUT"}


def plan(d):
    json.dump({"pins": PINS}, open(os.path.join(d, "core_pins.json"), "w"))
    p = {"die": {"name": "qwen_compute", "period_ps": 833},
         "partition_types": {"T": {"hard_cores": [{"module": "core", "inst": "u_c", "outline_um": [100, 50],
                                                   "pins_file": "core_pins.json"}]}}}
    f = os.path.join(d, "plan.json")
    json.dump(p, open(f, "w"))
    return f


def candidate(root, meta, gates):
    c = os.path.join(root, "routed", "core", "c0")
    os.makedirs(c)
    open(os.path.join(c, "core.lef"), "w").write(P.contract_lef("core", 100, 50, PINS, DIRS, 5))
    for corner in ("tt", "ff"):
        open(os.path.join(c, f"core_{corner}.lib"), "w").write(
            P.contract_lib("core", corner, 100, 50, PINS, DIRS, {"clk": (0.0, 0.0)}, 833))
    json.dump(meta, open(os.path.join(c, "meta.json"), "w"))
    if gates is not None:
        json.dump(gates, open(os.path.join(c, "gates.json"), "w"))


def run(meta, gates):
    with tempfile.TemporaryDirectory() as d:
        pf = plan(d)
        out = os.path.join(d, "out")
        os.makedirs(out)
        candidate(out, meta, gates)
        a = argparse.Namespace(plan=pf, type="T", out=out, src=None, routed=os.path.join(out, "routed"), rtl=[])
        assert P.make(a) == 0
        return json.load(open(os.path.join(out, "provisional_views.json")))


GOOD = {"type": "core", "signoff": "SIGNED", "view_complete": True, "signoff_record": "/x/signoff/signoff.json"}
COUNTED = {"job": "COUNTED core epyc2:/x/signoff/signoff.json (KW-FIX-32 export_view)", "counted": True}


class CountedSignedView(unittest.TestCase):
    def test_counted_signed_view_is_final(self):
        m = run(COUNTED, GOOD)
        c = m["children"]["core"]
        self.assertEqual(m["status"], "FINAL")
        self.assertEqual((c["source"], c["final"], c["counted"]), ("signed", True, "/x/signoff/signoff.json"))
        self.assertEqual(c["final_sha256"], {"core_tt.lib": c["tt_sha256"], "core_ff.lib": c["ff_sha256"]})

    def test_needs_parent_view_is_final(self):
        self.assertEqual(run(COUNTED, dict(GOOD, signoff="LOCAL_PASS_NEEDS_PARENT"))["status"], "FINAL")

    def test_routed_unsigned_candidate_stays_provisional(self):
        m = run({"job": "a1b2c3", "drc": 0}, GOOD)       # no counted flag: a DRC-clean routed attempt
        self.assertEqual((m["status"], m["children"]["core"]["source"], m["children"]["core"]["final"]),
                         ("PROVISIONAL", "routed", False))

    def test_counted_flag_needs_signed_complete_export(self):
        for g in (None, dict(GOOD, signoff="FAIL"), dict(GOOD, view_complete=False), dict(GOOD, type="other")):
            m = run(COUNTED, g)
            self.assertEqual((m["status"], m["children"]["core"]["source"]), ("PROVISIONAL", "routed"), g)


class WaveSide(unittest.TestCase):
    def test_prov_counted(self):
        self.assertTrue(K.prov_counted({"job": "COUNTED core host:/p (KW-FIX-32 export_view)"}))
        self.assertTrue(K.prov_counted({"counted": True}))
        self.assertFalse(K.prov_counted({"job": "SIGNED dkv73/ahub_l"}))
        self.assertFalse(K.prov_counted({"job": "a1b2c3"}))

    def test_prelint_count_note_reads_count_cache(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "cache.json"
            cache.write_text(json.dumps({"plans": {"qwen_compute/plan.json": {"die": "qwen_compute", "signed_cores": {
                "sv": ["h:/a/signoff.json src x flow f RE-SIGN"], "nv": ["h:/b/signoff.json SIGNED-LEGACY"],
                "bad": []}}}}))
            dd = {"count_cache": str(cache), "_plan_flags": {"T": "planned"}, "_plan_deps": {"T": ["sv", "nv", "un"]},
                  "prov_view_sources": {"sv": [{"host": "h", "dir": "/v/sv", "job": "COUNTED sv h:/a (KW-FIX-32)"}],
                                        "nv": [{"host": "h", "dir": "/v/nv", "job": "SIGNED old"}]}}
            self.assertEqual(K.count_signed_modules(dd, "qwen_compute"), {"sv", "nv"})
            msg = K.prelint(dd, "qwen_compute", set(), {})["T"][0]
            self.assertTrue(msg.startswith("view: planned hard core without a signed view: sv,nv,un"), msg)
            self.assertIn("signed+view 1", msg)
            self.assertIn("SIGNED IN COUNT BUT NO WAVE VIEW 1 (nv)", msg)
            self.assertIn("unsigned 1 (un)", msg)

    def test_no_cache_no_claim(self):
        dd = {"count_cache": "/nonexistent/cache.json", "_plan_flags": {"T": "planned"}, "_plan_deps": {"T": ["x"]}}
        self.assertIsNone(K.count_signed_modules(dd, "qwen_compute"))
        self.assertNotIn("; count:", K.prelint(dd, "qwen_compute", set(), {})["T"][0])


if __name__ == "__main__":
    unittest.main()
