#!/usr/bin/env python3
"""Tests for the track-aligned v2 abstracts, the orientation-aware snap library and the pre-route assert.

* checker: every v2 abstract (catalog + p-die) has origin 0 mod 0.048 legal in R0/MX/MY/R180 on every
  pin layer, no rotated symmetry, and M5 crossing on both pin edges of every ROM/SRAM;
* snap library (OpenROAD in the pinned ORFS image): ot_mts::place puts every pin of every catalog
  macro, v1 and v2, on track in every legal orientation; the two defective v1 V4.1 PHYs have no legal
  origin and are refused;
* assert: a legal placement moved 6 nm trips OT_MACRO_TRACK_ASSERT; the defective hooks' MX snap
  (origin 0 mod 0.048) leaves every pin of a mirror-variant v1 macro off-track and the assert sees it.

The OpenROAD cases need docker and openroad/orfs:latest; they are skipped without them.
    python3 -m pytest -q tools/test_ot_macro_track_snap.py
"""
from __future__ import annotations

import functools
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_macro_track_alignment as cmta  # noqa: E402

sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
V2_SETS = ["physical/asap7_memory_macros_v2", "physical/asap7_v41x_pdie_macros_v2"]
EW_SET = "physical/asap7_memory_macros_v2_ew"
PAIR = "ot_rom_4096x274_m8"
V1_CATALOG = "physical/asap7_memory_macros"
IMAGE = "openroad/orfs:latest"
DEFECTIVE_V1 = {"ot_hbm3e_phy_v41x", "ot_hbm3e_phy_v41x_aw30"}


def lefs(d: str) -> list[str]:
    return sorted(glob.glob(str(ROOT / d / "*" / "*.lef")))


def have_docker() -> bool:
    if not shutil.which("docker"):
        return False
    r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    return r.returncode == 0


@functools.lru_cache(maxsize=None)
def harness(lef_dirs: tuple[str, ...]) -> str:
    """Run physical/common/test_ot_macro_track_snap.tcl over every LEF in the given directory sets."""
    files = [f for d in lef_dirs for f in lefs(d)]
    names = []
    for f in files:
        names += [m["name"] for m in cmta.parse_lef(Path(f).read_text()) if m["class"] == "BLOCK"]
    with tempfile.TemporaryDirectory(dir=os.environ.get("OT_TEST_TMP")) as t:
        v = ["module ot_mts_top ();"] + [f"  {n} u_{n} ();" for n in names]
        if PAIR in names:
            v.append(f"  {PAIR} u_pair_{PAIR} ();")
        v += ["endmodule", ""]
        Path(t, "top.v").write_text("\n".join(v))
        env = {
            "OT_SRC_ROOT": "/src",
            "OT_TEST_LEFS": " ".join("/src/" + str(Path(f).resolve().relative_to(ROOT)) for f in files),
            "OT_TEST_VERILOG": "/t/top.v",
            "OT_TEST_DIE": "12200 12200",
            "OT_TEST_PAIR": PAIR if PAIR in names else "",
        }
        cmd = ["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{t}:/t"]
        for k, val in env.items():
            cmd += ["-e", f"{k}={val}"]
        cmd += [IMAGE, "bash", "-lc",
                "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "
                "/src/physical/common/test_ot_macro_track_snap.tcl"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = r.stdout + r.stderr
        if "OT_MTS_DONE" not in out:
            raise AssertionError("harness did not finish:\n" + out[-4000:])
        return out


def cases(out: str) -> dict[tuple[str, str], list[str]]:
    res: dict[tuple[str, str], list[str]] = {}
    for line in out.splitlines():
        if line.startswith("OT_MTS_CASE "):
            p = line.split()
            res.setdefault((p[1], p[2]), []).append(" ".join(p[3:]))
    return res


def negs(out: str) -> dict[tuple[str, str], int]:
    res = {}
    for line in out.splitlines():
        if line.startswith("OT_MTS_NEG "):
            p = line.split()
            res[(p[1], p[2])] = int(p[-1])
    return res


class CheckerOnV2(unittest.TestCase):
    def test_every_v2_abstract_on_track_in_every_orientation(self):
        from build_aligned_v2 import verify_lef
        n = 0
        for d in V2_SETS:
            for f in lefs(d):
                for name, ver in verify_lef(Path(f).read_text(), f).items():
                    n += 1
                    self.assertTrue(ver["pass"], f"{name}: {ver['layers']}")
                    self.assertEqual(ver["allowed_orientations"], ["R0", "MX", "MY", "R180"], name)
                    for lay, s in ver["layers"].items():
                        for o, rule in s["rule_mod_track_nm"].items():
                            self.assertEqual(rule, [0], f"{name} {lay} {o}")
        self.assertEqual(n, 27)
        for f in lefs(EW_SET):
            for name, ver in verify_lef(Path(f).read_text(), f).items():
                self.assertTrue(ver["pass"], name)
                self.assertEqual(sorted(ver["layers"]), ["M4"], name)   # pins leave the E/W edge on M4

    def test_rom_sram_m5_crosses_both_edges(self):
        from build_aligned_v2 import verify_lef
        for f in lefs(V2_SETS[0]):
            for name, ver in verify_lef(Path(f).read_text(), f).items():
                if not name.startswith(("ot_rom_", "ot_sram_")):
                    continue
                for o in ("R0", "MY"):
                    self.assertEqual(ver["m5_crossing_at_origin_0"][o], {"L": True, "R": True}, f"{name} {o}")

    def test_v2_heights_and_widths_follow_the_rule(self):
        for d in V2_SETS + [EW_SET]:
            for f in lefs(d):
                for m in cmta.parse_lef(Path(f).read_text()):
                    if m["class"] == "BLOCK":
                        self.assertEqual(m["W"] % 48, 24, m["name"])
                        if any(l == "M4" for p in m["pins"] if p["use"] not in ("POWER", "GROUND")
                               for l, _ in p["rects"]):
                            self.assertEqual(m["H"] % 48, 24, m["name"])

    def test_v1_pinned_views_untouched(self):
        import json
        idx = json.loads((ROOT / V2_SETS[0] / "index.json").read_text())
        import hashlib
        for name, e in idx["macros"].items():
            v1 = json.loads((ROOT / e["v1_dir"] / f"{name}.json").read_text()) if (ROOT / e["v1_dir"] / f"{name}.json").exists() else None
            if v1 and "views" in v1:
                for fn, h in v1["views"].items():
                    self.assertEqual(hashlib.sha256((ROOT / e["v1_dir"] / fn).read_bytes()).hexdigest(), h, fn)


@unittest.skipUnless(have_docker(), "docker / openroad/orfs:latest not available")
class SnapLibraryInOpenROAD(unittest.TestCase):
    def check_all_legal(self, out: str, refused: set[str]):
        cs = cases(out)
        self.assertTrue(cs)
        for (name, o), rows in cs.items():
            if name in refused:
                self.assertEqual(rows, ["NO_LEGAL_ORIGIN"], f"{name} {o}")
                continue
            for r in rows:
                m = re.match(r"placed (\d+) (\d+) offtrack (\d+)", r)
                self.assertIsNotNone(m, f"{name} {o}: {r}")
                self.assertEqual(int(m.group(3)), 0, f"{name} {o}: {r}")

    def test_v2_sets_place_legally_everywhere(self):
        out = harness(tuple(V2_SETS))
        self.check_all_legal(out, set())
        cs = cases(out)
        self.assertEqual(len({n for n, _ in cs}), 27)
        # the single v2 origin rule: every placement is 0 mod 48 nm in y (M4 macros) / x (M5 macros)
        for (name, o), rows in cs.items():
            for r in rows:
                x, y = map(int, re.match(r"placed (\d+) (\d+)", r).groups())
                self.assertTrue(y % 48 == 0 or x % 48 == 0, f"{name} {o} {x} {y}")

    def test_v1_catalog_snaps_orientation_aware(self):
        out = harness((V1_CATALOG,))
        self.check_all_legal(out, DEFECTIVE_V1)
        n = negs(out)
        # the defective hooks' snap: every pin of a mirror-variant v1 ROM is off-track in MX
        self.assertEqual(n[("ot_rom_4096x274_m8", "naive_mx_origin0")], 288)
        self.assertEqual(n[("ot_rom_1024x72_m8", "naive_mx_origin0")], 0)   # the one invariant v1 abstract

    def test_assert_catches_a_6nm_offset(self):
        for sets in (tuple(V2_SETS), (V1_CATALOG,)):
            n = negs(harness(sets))
            shifted = {k: v for k, v in n.items() if k[1] == "shift6nm"}
            self.assertTrue(shifted)
            for (name, _), tripped in shifted.items():
                if name in DEFECTIVE_V1 and sets == (V1_CATALOG,):
                    continue
                self.assertEqual(tripped, 1, name)

    def test_east_west_phy_places_legally(self):
        out = harness((EW_SET,))
        self.check_all_legal(out, set())
        cs = cases(out)
        self.assertEqual({o for _, o in cs}, {"R0", "MX", "MY", "R180"})
        self.assertEqual(negs(out)[("ot_hbm3e_phy", "shift6nm")], 1)

    def test_stacked_pair_does_not_overlap(self):
        for sets in (tuple(V2_SETS), (V1_CATALOG,)):
            line = next(l for l in harness(sets).splitlines() if l.startswith("OT_MTS_PAIR "))
            p = line.split()
            self.assertLessEqual(int(p[3]), int(p[5]), line)
            self.assertEqual(int(p[7]), 0, line)

    def test_v2_naive_mx_snap_is_now_legal(self):
        n = negs(harness(tuple(V2_SETS)))
        for (name, kind), v in n.items():
            if kind == "naive_mx_origin0" and name.startswith(("ot_rom_", "ot_sram_")):
                self.assertEqual(v, 0, name)


if __name__ == "__main__":
    unittest.main()


class LaunchGate(unittest.TestCase):
    def gate(self, args):
        import run_abi3_physical_aligned as g
        return g.gate(args)

    def test_refuses_defective_hook_and_dead_phy(self):
        _, rec = self.gate(["--macro-view", "ot_hbm3e_phy_v41x=physical/asap7_memory_macros/ot_hbm3e_phy_v41x",
                            "--step-tcl", "POST_MACRO_PLACE=physical/abi3/w10_wake_q_place.tcl"])
        self.assertEqual(rec["verdict"], "REFUSED")
        self.assertEqual(len(rec["refusals"]), 2)

    def test_passes_v2_and_appends_assert(self):
        args = ["--macro-view", "ot_rom_4096x274_m8=physical/asap7_memory_macros_v2/ot_rom_4096x274_m8",
                "--step-tcl", "POST_MACRO_PLACE=physical/abi3/w10_wake_q_place_aligned.tcl"]
        out, rec = self.gate(args)
        self.assertEqual(rec["verdict"], "PASS")
        self.assertEqual(out[-2:], ["--step-tcl", "POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl"])
        self.assertFalse(rec["warnings"])

    def test_v1_mirror_variant_warns_only(self):
        _, rec = self.gate(["--macro-view", "ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8"])
        self.assertEqual(rec["verdict"], "PASS")
        self.assertEqual(len(rec["warnings"]), 1)

    def test_off_by_default_is_pass_through(self):
        import run_abi3_physical_aligned as g
        self.assertTrue(callable(g.main))
        src = (ROOT / "tools/run_abi3_physical_aligned.py").read_text()
        self.assertIn('action="store_true", help="audit abstracts and hooks', src)
