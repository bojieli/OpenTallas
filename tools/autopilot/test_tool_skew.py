#!/usr/bin/env python3
"""tests for tool_skew.py and the kit_wave launch gate (no ssh, no ot-run: the autopilot host layer is faked)"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["OT_TOOL_SKEW_REMOTE"] = "0"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tool_skew as TS  # noqa: E402
import kit_wave as KW  # noqa: E402
from test_kit_wave import FakeAP, cfg  # noqa: E402


def tree(root, files):
    for rel, txt in files.items():
        p = Path(root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt)
    return str(root)


BASE = {"tools/die_plan/gen_phys.py": "a=1\n", "tools/die_plan/sdc_lint.py": "b=1\n", "tools/autopilot/kit_wave.py": "c=1\n"}


class Manifest(unittest.TestCase):
    def test_closure_skips_tests_caches_and_other_dirs(self):
        with tempfile.TemporaryDirectory() as t:
            tree(t, dict(BASE, **{"tools/die_plan/test_x.py": "x", "tools/die_plan/__pycache__/y.py": "y",
                                  "tools/fleet/ot_run.py": "z", "tools/die_plan/notes.md": "n", "tools/autopilot/run.sh": "s"}))
            self.assertEqual(sorted(TS.manifest(t)), sorted(list(BASE) + ["tools/autopilot/run.sh"]))

    def test_diff_kinds(self):
        a = {"m1": "1", "m2": "2", "m3": "3"}
        b = {"m1": "1", "m2": "x", "m4": "4"}
        self.assertEqual(TS.diff(b, a), {"m2": "differ", "m4": "only_die", "m3": "missing"})


class Allowlist(unittest.TestCase):
    SK = {"tools/die_plan/gen_phys.py": "differ", "tools/die_plan/new.py": "only_die"}

    def test_live_entry_allows_expired_does_not(self):
        al = {"tools/die_plan/gen_phys.py": {"expires": "2026-11-20", "why": "unmerged tap rows"}}
        r, a, e = TS.apply_allow(self.SK, al, "2026-11-16")
        self.assertEqual(r, {"tools/die_plan/new.py": "only_die"})
        self.assertEqual(a, {"tools/die_plan/gen_phys.py": "unmerged tap rows"})
        r, a, e = TS.apply_allow(self.SK, al, "2026-11-21")
        self.assertEqual(set(r), set(self.SK))
        self.assertEqual(e, {"tools/die_plan/gen_phys.py": "2026-11-20"})

    def test_glob_and_missing_expiry(self):
        r, a, e = TS.apply_allow(self.SK, {"tools/die_plan/*.py": {"expires": "2026-12-01"}}, "2026-11-16")
        self.assertEqual(r, {})
        r, a, e = TS.apply_allow(self.SK, {"tools/die_plan/*.py": {"why": "no date"}}, "2026-11-16")
        self.assertEqual(len(r), 2)
        self.assertEqual(len(e), 2)


class CheckDie(unittest.TestCase):
    def test_identical_tree_ok_changed_tree_refused(self):
        with tempfile.TemporaryDirectory() as t:
            m = tree(Path(t) / "main", BASE)
            same = tree(Path(t) / "same", BASE)
            self.assertTrue(TS.check_die("s81", same, m)["ok"])
            bad = tree(Path(t) / "bad", dict(BASE, **{"tools/die_plan/gen_phys.py": "a=2\n"}))
            res = TS.check_die("s81", bad, m, today="2026-11-16")
            self.assertFalse(res["ok"])
            self.assertEqual(res["refused"], {"tools/die_plan/gen_phys.py": "differ"})
            al = {"s81": {"tools/die_plan/gen_phys.py": {"expires": "2026-11-17"}}}
            self.assertTrue(TS.check_die("s81", bad, m, al, today="2026-11-16")["ok"])
            self.assertFalse(TS.check_die("s81", bad, m, al, today="2026-11-18")["ok"])
            self.assertFalse(TS.check_die("kv", bad, m, al, today="2026-11-16")["ok"], "allowlist is per die")

    def test_missing_module_is_stale_tree(self):
        with tempfile.TemporaryDirectory() as t:
            m = tree(Path(t) / "main", BASE)
            old = tree(Path(t) / "old", {k: v for k, v in BASE.items() if "sdc_lint" not in k})
            self.assertEqual(TS.check_die("s81", old, m)["refused"], {"tools/die_plan/sdc_lint.py": "missing"})

    def test_unreadable_tree_is_unmeasured_not_refused(self):
        with tempfile.TemporaryDirectory() as t:
            m = tree(Path(t) / "main", BASE)
            res = TS.check_die("s81", str(Path(t) / "nope"), m)
            self.assertTrue(res["ok"])
            self.assertFalse(res["measured"])

    def test_signature_changes_with_the_set(self):
        a = dict(refused={"x": "differ"})
        b = dict(refused={"x": "differ", "y": "missing"})
        self.assertNotEqual(TS.signature(a), TS.signature(b))
        self.assertEqual(TS.signature(a), TS.signature(dict(refused={"x": "differ"})))


class LaunchGate(unittest.TestCase):
    def setup(self, t, tool_skew=True, allow=None):
        main = tree(Path(t) / "main", BASE)
        if allow is not None:
            tree(main, {TS.ALLOW_REL: json.dumps(allow)})
        bad = tree(Path(t) / "bad", dict(BASE, **{"tools/die_plan/gen_phys.py": "a=2\n"}))
        c = cfg(src=bad, tool_skew_main=main)
        c["dies"]["qwen_kvsys"]["tool_skew"] = tool_skew
        return c

    def run_launch(self, c):
        with tempfile.TemporaryDirectory() as td:
            ap = FakeAP(td, "")
            ap.coord = []
            ap.coord_append = lambda rel, line: ap.coord.append((rel, line))
            st = {"items": {}}
            r = dict(item="kv3_hg_v1", kind="type", block_sha="abc", replicas=1)
            rec = KW.launch(ap, c, st, "qwen_kvsys", r, "intel2")
            rec2 = KW.launch(ap, c, st, "qwen_kvsys", dict(r, item="kv3_pc"), "intel2")
            return rec, rec2, ap, st

    def test_skewed_tree_refuses_and_posts_one_needs_lane(self):
        with tempfile.TemporaryDirectory() as t:
            rec, rec2, ap, st = self.run_launch(self.setup(t, True))
            self.assertIsNone(rec)
            self.assertIsNone(rec2)
            self.assertEqual(ap.units, [])
            self.assertEqual(len(ap.coord), 1)
            self.assertIn("NEEDS-LANE", ap.coord[0][1])
            self.assertIn("tools/die_plan/gen_phys.py", ap.coord[0][1])
            self.assertEqual(list(st["items"]), [])

    def test_allowlisted_module_launches(self):
        with tempfile.TemporaryDirectory() as t:
            al = {"qwen_kvsys": {"tools/die_plan/gen_phys.py": {"expires": "2999-01-01", "why": "x"}}}
            rec, rec2, ap, st = self.run_launch(self.setup(t, True, al))
            self.assertIsNotNone(rec)
            self.assertEqual(ap.coord, [])

    def test_opt_out_and_warn(self):
        with tempfile.TemporaryDirectory() as t:
            rec, _, ap, _ = self.run_launch(self.setup(t, False))
            self.assertIsNotNone(rec)
            self.assertEqual(ap.coord, [])
        with tempfile.TemporaryDirectory() as t:
            rec, _, ap, _ = self.run_launch(self.setup(t, "warn"))
            self.assertIsNotNone(rec)
            self.assertEqual(len(ap.coord), 1)


if __name__ == "__main__":
    unittest.main()
