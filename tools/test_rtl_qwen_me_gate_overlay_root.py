#!/usr/bin/env python3
"""Regression for beab07a70: the Qwen ME partition gate must keep the INVOKED overlay root.

The closure loop builds a bench source tree whose tools/ directory is a symlink into another snapshot
(bench_src_a1/tools -> bsrc_m5_0/tools). Path(__file__).resolve() followed that link, so ROOT pointed at the
snapshot, the gate hashed and compiled the snapshot's RTL instead of the overlay's, and relative_to(ROOT) of the
invoked script raised ValueError (ot_qwen_tile_lsl_m5-m5-a0b143e7a). The gate must see the overlay's RTL bytes.
Mutant: restoring .resolve() makes test_root_is_invoked_overlay fail.
"""
import importlib.util
import pathlib
import shutil
import tempfile
import unittest

GATE = pathlib.Path(__file__).absolute().parent / "rtl_qwen_me_partition_gate_w12.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OverlayRoot(unittest.TestCase):
    def test_root_is_invoked_overlay(self):
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            snap, overlay = td / "bsrc_m5_0", td / "bench_src_a1"
            (snap / "tools").mkdir(parents=True)
            shutil.copy(GATE, snap / "tools" / GATE.name)
            (overlay / "rtl" / "hdc").mkdir(parents=True)
            (overlay / "tools").symlink_to(snap / "tools", target_is_directory=True)
            mod = load(overlay / "tools" / GATE.name, "gate_overlay_probe")
            self.assertEqual(mod.ROOT, overlay)
            self.assertTrue(all(str(p).startswith(str(overlay) + "/") for p in [mod.TB, *mod.RTL]))
            # the pin map the gate writes: every source and the script itself are inside ROOT
            invoked = overlay / "tools" / GATE.name
            for p in [mod.TB, *mod.RTL, invoked]:
                p.relative_to(mod.ROOT)


if __name__ == "__main__":
    unittest.main()
