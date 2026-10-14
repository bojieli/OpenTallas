#!/usr/bin/env python3
"""Regression for the overlay-ROOT trap (fc64b8c6d / beab07a70) across EVERY tools/rtl_*gate*.py.

The closure loop builds bench source trees whose tools/ directory is a symlink into another snapshot
(bench_src_a1/tools -> bsrc_m5_0/tools). A gate that computes ROOT = Path(__file__).resolve().parents[1] follows that
link: it then hashes and compiles the snapshot's RTL instead of the overlay's, and relative_to(ROOT) of overlay paths
raises. Every gate must keep the INVOKED logical path (Path(__file__).absolute()).

Pattern: build a temp overlay whose tools/ is a symlink to the real tools/, load each gate from the overlay path, and
require gate.ROOT == overlay. Mutant: restoring .resolve() in any gate makes its case fail (ROOT = the real checkout).
Gates whose import needs a missing input are still judged statically (no resolve() of __file__ anywhere).
"""
import importlib.util
import pathlib
import re
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).absolute().parent
GATES = sorted(TOOLS.glob("rtl_*gate*.py"))
RESOLVED_FILE = re.compile(r"Path\(\s*__file__\s*\)\s*\.resolve\(")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(name, None)
    return mod


class OverlayRootAllGates(unittest.TestCase):
    def test_gates_found(self):
        self.assertGreaterEqual(len(GATES), 17)

    def test_no_gate_resolves_its_own_path(self):
        bad = [g.name for g in GATES if RESOLVED_FILE.search(g.read_text())]
        self.assertEqual(bad, [], "gates that resolve() past a symlinked tools/ overlay")

    def test_root_is_invoked_overlay(self):
        with tempfile.TemporaryDirectory() as td:
            overlay = pathlib.Path(td) / "bench_src_a1"
            overlay.mkdir()
            (overlay / "tools").symlink_to(TOOLS, target_is_directory=True)
            loaded = 0
            for g in GATES:
                with self.subTest(gate=g.name):
                    try:
                        mod = load(overlay / "tools" / g.name, "gate_overlay_probe_" + g.stem)
                    except (Exception, SystemExit):  # import needs inputs a sparse/CI tree lacks: static check covers it
                        continue
                    if not hasattr(mod, "ROOT"):
                        continue
                    loaded += 1
                    self.assertEqual(pathlib.Path(mod.ROOT), overlay)
            self.assertGreater(loaded, 0)


if __name__ == "__main__":
    unittest.main()
