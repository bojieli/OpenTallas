"""LOOP-LVT 2026-10-10: an OT_MULTI_VT route under option B (corner WC reads TT) still repaired setup against the LVT
(and SLVT) SS liberties: the asap7 platform config.mk appends every OTHER_VT with
`WC_NLDM_LIB_FILES += $(subst PLACEHOLDER,<vt>,$(WC_NLDM_LIB_FILES_T))` (the SS template) after the design config.
run_abi3_physical now writes `override export WC_NLDM_LIB_FILES = $(TC_NLDM_LIB_FILES)`, tt_overlay backports it to old
snapshots (and to checked-in config.mk), and route_corner_check fails any setup corner that read a non-TT library of ANY
VT.  The make evaluation of the real platform config runs in the ORFS image when docker has it (skipped otherwise)."""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import route_corner_check as rcc
import tt_overlay as overlay

HERE = Path(__file__).resolve().parent
RUN_ABI3 = HERE.parent / "run_abi3_physical.py"
IMAGE = "openroad/orfs:asap7lock"
WC_TT = "export WC_NLDM_LIB_FILES = $(TC_NLDM_LIB_FILES)"
OVERRIDE = "override " + WC_TT

OLD_SNAPSHOT = '''import os
import re


def apply_cts_fix_hooks(config, case):
    return config


def write(config, case):
    config = apply_cts_fix_hooks(config, case)
    (case / "config.mk").write_text("\\n".join(config) + "\\n", encoding="utf-8")
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ConfigWriterOverride(unittest.TestCase):
    def test_main_writer_overrides_only_the_tt_line(self):
        f = load(RUN_ABI3, "run_abi3_lvt").ot_tt_lib_override
        cfg = ["export CORNER = WC", WC_TT, "export ASAP7_USE_VT = RVT LVT", "export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)"]
        out = f(cfg)
        self.assertEqual(out[1], OVERRIDE)
        self.assertEqual(out[:1] + out[2:], cfg[:1] + cfg[2:])
        self.assertEqual(f(["export WC_NLDM_LIB_FILES = /x/a_SS.lib"]), ["export WC_NLDM_LIB_FILES = /x/a_SS.lib"])

    def test_main_snapshot_is_left_alone(self):
        s = RUN_ABI3.read_text()
        s2, msg, ok = overlay.ensure_lib_override(s)
        self.assertTrue(ok)
        self.assertEqual((s2, msg), (s, []))

    def test_old_snapshot_patched_idempotent_and_effective(self):
        s, msg, ok = overlay.ensure_lib_override(OLD_SNAPSHOT)
        self.assertTrue(ok and msg)
        self.assertEqual(overlay.ensure_lib_override(s), (s, [], True))
        mod = {}
        exec(compile(s, "snap", "exec"), mod)
        d = Path(tempfile.mkdtemp())
        mod["write"](["export CORNER = WC", WC_TT], d)
        self.assertEqual((d / "config.mk").read_text().split("\n")[1], OVERRIDE)

    def test_snapshot_without_anchor_fails(self):
        self.assertFalse(overlay.ensure_lib_override("def f():\n    pass\n")[2])


class DirectConfigOverride(unittest.TestCase):
    def test_direct_config_gets_override_once(self):
        src = Path(tempfile.mkdtemp())
        f = src / "physical/x/config.mk"
        f.parent.mkdir(parents=True)
        f.write_text("export CORNERS = WC BC\nexport WC_LIB_FILES = $(WC_NLDM_LIB_FILES) /src/m/m_ss.lib\n")
        env = {"OT_ORFS_CORNER": "TC", "OT_ORFS_CORNER_OVERRIDE": "", "OT_TTB_CORNER_MARK": ""}
        with patch.dict(os.environ, env):
            overlay.ensure_direct_configs(src)
            once = f.read_text()
            overlay.ensure_direct_configs(src)
        self.assertEqual(f.read_text(), once)
        self.assertIn("export WC_LIB_FILES = $(TC_NLDM_LIB_FILES) /src/m/m_tt.lib", once)
        self.assertEqual(once.count(OVERRIDE), 1)
        g = src / "physical/y/config.mk"
        g.parent.mkdir(parents=True)
        g.write_text("export CORNER = BC\n")
        with patch.dict(os.environ, env):
            overlay.ensure_direct_configs(src)
        self.assertEqual(g.read_text(), "export CORNER = BC\n")


def write_log(root, rel, libs):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(f"read_liberty {c and f'-corner {c} ' or ''}/p/lib/NLDM/asap7sc7p5t_{k}_{vt}_{t}_nldm_211120.lib.gz\n"
                         for c, k, vt, t in libs))


CTS = "routes/lbl/logs/asap7/n/base/4_1_cts.log"


class CornerCheckAnyVt(unittest.TestCase):
    def test_lvt_ss_in_single_corner_warns(self):
        r = tempfile.mkdtemp()           # the qfd sys_v lvt r3 load: RVT TT + LVT TT + LVT SS + FF
        write_log(r, CTS, [(None, "AO", "RVT", "TT"), (None, "AO", "LVT", "TT"), (None, "AO", "LVT", "SS"),
                           (None, "AO", "RVT", "FF"), (None, "AO", "LVT", "FF")])
        ok, lines = rcc.check(r)
        self.assertTrue(ok)             # TT + SS only: pessimistic repair, verdict STA authoritative
        self.assertTrue(lines[0].startswith("WARN"))
        self.assertIn("SS+TT", lines[0])

    def test_lvt_or_slvt_ss_in_wc_scene_warns(self):
        for vt in ("LVT", "SLVT"):
            r = tempfile.mkdtemp()
            write_log(r, CTS, [("WC", "AO", "RVT", "TT"), ("WC", "AO", vt, "SS"), ("BC", "AO", "RVT", "FF")])
            self.assertTrue(rcc.check(r)[0], vt)
            r = tempfile.mkdtemp()      # no TT views in the setup scene at all: still a failure
            write_log(r, CTS, [("WC", "AO", "RVT", "SS"), ("WC", "AO", vt, "SS"), ("BC", "AO", "RVT", "FF")])
            self.assertFalse(rcc.check(r)[0], vt)

    def test_all_vt_tt_passes(self):
        r = tempfile.mkdtemp()
        write_log(r, CTS, [("WC", "AO", v, "TT") for v in ("RVT", "LVT", "SLVT")] +
                  [("BC", "AO", v, "FF") for v in ("RVT", "LVT", "SLVT")])
        self.assertTrue(rcc.check(r)[0])


def have_image():
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@unittest.skipUnless(have_image(), f"docker image {IMAGE} not available")
class PlatformMakeEvaluation(unittest.TestCase):
    """Evaluate the REAL asap7 platform config.mk after a design config, as ORFS does (design config first)."""
    MK = ("include $(DESIGN_CONFIG)\nPLATFORM_DIR = /OpenROAD-flow-scripts/flow/platforms/asap7\n"
          "include $(PLATFORM_DIR)/config.mk\nprint-%: ; @echo '$($*)'\n")

    def libs(self, vts, wc_line):
        d = tempfile.mkdtemp()
        Path(d, "Makefile").write_text(self.MK)
        Path(d, "design.mk").write_text(f"export ASAP7_USE_VT = {vts}\nexport CORNER = WC\n{wc_line}\n")
        out = subprocess.run(["docker", "run", "--rm", "-v", f"{d}:/m", "-w", "/m", IMAGE, "make", "-s", "-f", "Makefile",
                              "DESIGN_CONFIG=/m/design.mk", "print-LIB_FILES"],
                             capture_output=True, text=True, timeout=300, check=True).stdout.split()
        shutil.rmtree(d, ignore_errors=True)
        return [os.path.basename(x) for x in out if "_nldm_" in x]

    def test_before_and_after(self):
        for vts in ("RVT", "RVT LVT", "RVT LVT SLVT"):
            after = self.libs(vts, OVERRIDE)
            self.assertTrue(after and all("_TT_" in x for x in after), (vts, after))
            for vt in vts.split():
                self.assertEqual(sum(f"_{vt}_TT_" in x for x in after), 5, (vts, vt, after))
            before = self.libs(vts, WC_TT)
            n_ss = sum("_SS_" in x for x in before)
            self.assertEqual(n_ss, 5 * (len(vts.split()) - 1), (vts, before))   # the bug: every OTHER_VT read at SS


if __name__ == "__main__":
    unittest.main()
