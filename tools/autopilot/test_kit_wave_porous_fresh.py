"""POROUS-FRESH-1123: a kit with OT_POROUS_VIEWS refuses (or, on a composed launch tree, re-syncs) porous child views that the driver's map replaced."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW

BASE = "b" * 64
OLD = "9924dfc8290c" + "0" * 52
NEW = "1b7a030446b6" + "1" * 52


def tree(t, name, rows, files=()):
    d = Path(t) / name / KW.POROUS_REL
    d.mkdir(parents=True)
    (d / "map.json").write_text(json.dumps(rows))
    for f in files:
        (d / f).write_bytes(b"x")
    return Path(t) / name


def row(sha, f):
    return {"base_sha256": BASE, "sha256": sha, "file": f}


def check(root, exp):
    p = subprocess.run(["bash", "-c", KW.porous_check_cmd(root, exp)], capture_output=True, text=True)
    return p.returncode, p.stdout


class PorousFresh(unittest.TestCase):
    def test_wanted_only_with_env(self):
        self.assertTrue(KW.porous_wanted({"gen_env": {"OT_POROUS_VIEWS": "all"}}))
        self.assertFalse(KW.porous_wanted({"gen_env": {"OT_POROUS_VIEWS": " "}}))
        self.assertFalse(KW.porous_wanted({"gen_env": {}}))
        self.assertFalse(KW.porous_wanted({}))

    def test_stale_row_refused_fresh_passes(self):
        with tempfile.TemporaryDirectory() as t:
            drv = tree(t, "drv", {"hw.lef": row(NEW, "hw.lef.new.gz")}, ["hw.lef.new.gz"])
            exp = KW.porous_expected(drv / KW.POROUS_REL)
            self.assertEqual(exp, {"hw.lef": [BASE, NEW]})
            old = tree(t, "old", {"hw.lef": row(OLD, "hw.lef.old.gz"), "other.lef": row("c" * 64, "o.gz")}, ["hw.lef.old.gz", "o.gz"])
            rc, out = check(old, exp)
            self.assertEqual(rc, 3)
            self.assertIn("KW_POROUS_STALE 1 row(s): hw.lef 9924dfc8290c->1b7a030446b6", out)
            rc, out = check(drv, exp)
            self.assertEqual(rc, 0, out)
            self.assertIn("KW_POROUS_FRESH 1 rows", out)

    def test_other_base_is_not_stale(self):
        with tempfile.TemporaryDirectory() as t:
            other = tree(t, "o", {"hw.lef": {"base_sha256": "e" * 64, "sha256": OLD, "file": "f.gz"}}, ["f.gz"])
            self.assertEqual(check(other, {"hw.lef": [BASE, NEW]})[0], 0)

    def test_missing_view_file_refused(self):
        with tempfile.TemporaryDirectory() as t:
            r = tree(t, "r", {"hw.lef": row(NEW, "gone.gz")})
            rc, out = check(r, {"hw.lef": [BASE, NEW]})
            self.assertEqual(rc, 3)
            self.assertIn("file missing", out)

    def test_no_map_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(check(Path(t), {"hw.lef": [BASE, NEW]})[0], 0)

    def test_sync_replaces_hardlinked_file_without_touching_source(self):
        with tempfile.TemporaryDirectory() as t:
            drv = tree(t, "drv", {"hw.lef": row(NEW, "new.gz")}, ["new.gz"])
            rt = tree(t, "rt", {"hw.lef": row(OLD, "old.gz")}, ["old.gz"])
            launch = Path(t) / "launch" / KW.POROUS_REL
            launch.mkdir(parents=True)
            for f in ("map.json", "old.gz"):
                os.link(rt / KW.POROUS_REL / f, launch / f)
            rt_map = (rt / KW.POROUS_REL / "map.json").read_text()
            argv = KW.porous_sync_argv(Path(t) / "launch", "localhost", "hub", src=drv / KW.POROUS_REL)
            self.assertNotIn("--delete", argv)
            self.assertNotIn("--inplace", argv)
            subprocess.run(argv, check=True, capture_output=True)
            self.assertEqual((rt / KW.POROUS_REL / "map.json").read_text(), rt_map)
            self.assertTrue((launch / "new.gz").is_file() and (launch / "old.gz").is_file())
            self.assertEqual(check(Path(t) / "launch", {"hw.lef": [BASE, NEW]})[0], 0)

    def test_remote_dest(self):
        a = KW.porous_sync_argv("/k/L", "epyc7", "intel2", src="/d")
        self.assertEqual(a[-2:], ["/d/", "epyc7:/k/L/tools/die_plan/porous_views_data/"])

    def test_driver_map_has_the_eol_fixed_col_views(self):
        exp = KW.porous_expected()
        if not exp:
            self.skipTest("no porous map beside this driver")
        for n, s in (("ot_v41_rom_elem_q_qxpq_w10_gb_hw.lef", "1b7a030446b6"), ("ot_v41_rom_elem_q_qxpq_w10_gb_he.lef", "bbc42691a185"),
                     ("ot_s81_sstn_payload536.lef", "c7d3c35336b4")):
            self.assertTrue(exp[n][1].startswith(s), n)


if __name__ == "__main__":
    unittest.main()
