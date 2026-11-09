"""KW-FIX-35-CV 11-08: the tick exports counted child views itself (SIGNED IN COUNT BUT NO WAVE VIEW, hourly per die)
and overlays the hub sidecar into prov_view_sources at read time."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import counted_child_views as C  # noqa: E402
import kit_wave as K  # noqa: E402


class FakeAP:
    DRY = False

    def __init__(self, active=False):
        self.launched, self.logs, self.active = [], [], active

    def launch_unit(self, unit, logfile, argv):
        self.launched.append((unit, str(logfile), list(argv)))
        return True

    def unit_active(self, unit):
        return self.active

    def log(self, s):
        self.logs.append(s)


def die_cfg(td, pvs=None):
    cache = Path(td) / "cache.json"
    cache.write_text(json.dumps({"plans": {"hbm/plan.json": {"die": "hbm", "signed_cores": {
        "ra": ["epyc2:/a/signoff.json RE-SIGN"], "h1": ["epyc2:/b/signoff.json RE-SIGN"], "nope": []}}}}))
    return {"gen_host": "epyc5", "plan": "/p/die_plan.json", "event": "d44v", "count_cache": str(cache),
            "_plan_flags": {"q_b100": "planned", "q_x": "hard"},
            "_plan_deps": {"q_b100": ["ra", "h1", "un"], "q_x": ["other"]},
            "prov_view_sources": pvs or {}}


CAND = {"host": "epyc4", "dir": "/srv/opentallas-scratch3/claude/kw32-views/hbm/abc/ra",
        "job": "COUNTED ra epyc2:/a/signoff.json (KW-FIX-32 export_view)"}


class NoView(unittest.TestCase):
    def test_count_noview_matches_prelint(self):
        with tempfile.TemporaryDirectory() as td:
            d = die_cfg(td, {"h1": [dict(CAND, dir="/v/h1")]})
            self.assertEqual(K.count_noview(d, K.count_signed_modules(d, "hbm")), ["ra"])
            self.assertIn("SIGNED IN COUNT BUT NO WAVE VIEW 1 (ra)", K.prelint(d, "hbm", set(), {})["q_b100"][0])
            self.assertEqual(K.count_noview(d, None), [])


class Overlay(unittest.TestCase):
    def test_sidecar_first_and_prelint_reads_signed_view(self):
        with tempfile.TemporaryDirectory() as td:
            old = {"host": "intel1", "dir": "/old/ra", "job": "die-config"}
            cfg = {"dies": {"hbm": die_cfg(td, {"ra": [old, dict(CAND)]}), "s81": {"prov_view_sources": {}}}}
            (Path(td) / K.AUTO_VIEWS_FILE).write_text(json.dumps({"dies": {
                "hbm": {"modules": {"ra": [CAND], "h1": [dict(CAND, dir="/v/h1")], "bad": [{"dir": "/x"}]}},
                "ghost": {"modules": {"m": [CAND]}}}}))
            out = K.merge_auto_views(cfg, td)
            self.assertEqual(out, {"hbm": ["h1", "ra"]})
            ra = cfg["dies"]["hbm"]["prov_view_sources"]["ra"]
            self.assertEqual([c["dir"] for c in ra], [CAND["dir"], "/old/ra"])     # first, deduplicated by dir
            self.assertTrue(ra[0]["counted"])
            self.assertNotIn("bad", cfg["dies"]["hbm"]["prov_view_sources"])
            self.assertIn("signed+view 2", K.prelint(cfg["dies"]["hbm"], "hbm", set(), {})["q_b100"][0])

    def test_opt_out_and_missing_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"dies": {"hbm": dict(die_cfg(td), auto_child_views=False)}}
            self.assertEqual(K.merge_auto_views(cfg, td), {})
            (Path(td) / K.AUTO_VIEWS_FILE).write_text(json.dumps({"dies": {"hbm": {"modules": {"ra": [CAND]}}}}))
            self.assertEqual(K.merge_auto_views(cfg, td), {})
            self.assertEqual(cfg["dies"]["hbm"]["prov_view_sources"], {})


class Step(unittest.TestCase):
    def test_launch_hourly_only_noview_modules(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"dies": {"hbm": die_cfg(td), "s81": {"prov_view_sources": {}}}}   # s81: plan not read -> skip
            ap, st = FakeAP(), {}
            self.assertEqual(list(K.auto_views_step(ap, cfg, st, td, now=10000)), ["hbm"])
            unit, log, argv = ap.launched[0]
            self.assertEqual(argv[argv.index("--only") + 1:], ["h1", "ra"])
            self.assertIn("--export", argv)
            self.assertEqual(argv[argv.index("--publish") + 1], str(Path(td) / K.AUTO_VIEWS_FILE))
            jc = json.loads((Path(td) / "auto_views/hbm/config.json").read_text())
            self.assertEqual(jc, {"dies": {"hbm": {"gen_host": "epyc5", "plan": "/p/die_plan.json", "event": "d44v"}}})
            self.assertEqual(st["auto_views"]["hbm"]["modules"], ["h1", "ra"])
            self.assertEqual(K.auto_views_step(ap, cfg, st, td, now=10000 + 3599), {})   # within the hour
            self.assertEqual(K.auto_views_step(FakeAP(active=True), cfg, st, td, now=10000 + 3601), {})  # still running
            self.assertEqual(list(K.auto_views_step(ap, cfg, st, td, now=10000 + 3601)), ["hbm"])

    def test_no_launch_when_all_children_have_views_or_opt_out(self):
        with tempfile.TemporaryDirectory() as td:
            pvs = {"ra": [CAND], "h1": [dict(CAND, dir="/v/h1")]}
            ap = FakeAP()
            self.assertEqual(K.auto_views_step(ap, {"dies": {"hbm": die_cfg(td, pvs)}}, {}, td, now=1e9), {})
            cfg = {"dies": {"hbm": die_cfg(td)}, "auto_child_views": False}
            self.assertEqual(K.auto_views_step(ap, cfg, {}, td, now=1e9), {})
            self.assertEqual(ap.launched, [])

    def test_dry_run_launches_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            ap = FakeAP()
            ap.DRY = True
            st = {}
            self.assertEqual(K.auto_views_step(ap, {"dies": {"hbm": die_cfg(td)}}, st, td, now=1e9), {})
            self.assertEqual((ap.launched, st.get("auto_views")), ([], {}))
            self.assertTrue(any("would AUTO-VIEWS hbm" in s for s in ap.logs))


class LefOnly(unittest.TestCase):
    def test_needs_parent_plus_missing_lef_takes_lef_from_odb(self):
        lef = "view file m.lef not found in kit/views, base or signoff dir"
        np = "signoff.json verdict 'LOCAL_PASS_NEEDS_PARENT' is not SIGNED"
        self.assertTrue(C.lef_only({"problems": [lef]}, "m"))
        self.assertTrue(C.lef_only({"problems": [lef, np]}, "m"))
        self.assertFalse(C.lef_only({"problems": [np]}, "m"))                 # no lef problem: needs_parent_only path
        self.assertFalse(C.lef_only({"problems": [lef, "tt lib older than odb"]}, "m"))
        self.assertTrue(C.needs_parent_only({"problems": [np]}))
        self.assertFalse(C.needs_parent_only({"problems": [lef, np]}))


class Publish(unittest.TestCase):
    def test_publish_merges_and_keeps_earlier_modules(self):
        with tempfile.TemporaryDirectory() as td:
            side = Path(td) / "auto.json"
            c1 = dict(CAND, module="ra", plan_pin_match=True, extra="x")
            m1 = {"die": "hbm", "generated": "g1", "modules": {"ra": {"candidates": [c1]}, "h1": {"candidates": []}}}
            self.assertEqual(C.publish_manifest(side, m1), ["ra"])
            m2 = {"die": "hbm", "generated": "g2", "modules": {"h1": {"candidates": [dict(CAND, dir="/v/h1")]},
                                                                "ra": {"candidates": []}}, "missing": {"z": ["t"]}}
            self.assertEqual(C.publish_manifest(side, m2), ["h1"])
            C.publish_manifest(side, {"die": "s81", "modules": {"k": {"candidates": [dict(CAND, dir="/v/k")]}}})
            s = json.loads(side.read_text())
            self.assertEqual(sorted(s["dies"]["hbm"]["modules"]), ["h1", "ra"])     # ra kept from run 1
            self.assertEqual(s["dies"]["hbm"]["missing"], ["z"])
            self.assertTrue(s["dies"]["hbm"]["modules"]["ra"][0]["counted"])
            self.assertNotIn("extra", s["dies"]["hbm"]["modules"]["ra"][0])
            self.assertIn("s81", s["dies"])
            cfg = {"dies": {"hbm": {"prov_view_sources": {}}}}
            side2 = Path(td) / K.AUTO_VIEWS_FILE
            side2.write_text(side.read_text())
            self.assertEqual(K.merge_auto_views(cfg, td), {"hbm": ["h1", "ra"]})   # tool output is overlay input


if __name__ == "__main__":
    unittest.main()
