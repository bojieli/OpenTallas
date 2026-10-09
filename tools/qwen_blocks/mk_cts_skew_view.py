#!/usr/bin/env python3
"""Make a CTS-only copy of a memory-compiler macro view that declares a clock-tree insertion target on its clock pin
(liberty max/min_clock_tree_path), so OpenROAD CTS ("sink ... has insertion delay") lands the macro clock pin EARLY by
that amount relative to the register tree (deliberate useful skew for a macro whose clk->q exceeds the cycle).
Only the flow reads this view; sign-off STA reads the original view (no clock_tree_path arcs).
usage: mk_cts_skew_view.py SRC_DIR DST_DIR PS"""
import re, shutil, sys
from pathlib import Path
src, dst, ps = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
name = src.name
dst.mkdir(parents=True, exist_ok=True)
arc = ("      timing () {{\n        timing_type : {t};\n        timing_sense : positive_unate;\n"
       "        cell_rise (scalar) {{ values (\"{v}\"); }}\n        cell_fall (scalar) {{ values (\"{v}\"); }}\n      }}\n")
for f in src.iterdir():
    if f.suffix == ".lib":
        txt = f.read_text()
        m = re.search(r"pin \(clk\) \{\n(.*?\n)(    \}\n)", txt, re.S)
        assert m, f
        add = arc.format(t="max_clock_tree_path", v=f"{ps:.1f}") + arc.format(t="min_clock_tree_path", v=f"{ps:.1f}")
        txt = txt[:m.end(1)] + add + txt[m.end(1):]
        (dst / f.name).write_text(txt)
    elif f.suffix in (".lef", ".json", ".v"):
        shutil.copy(f, dst / f.name)
(dst / "README").write_text(f"CTS-only view of {name}: liberty clock-tree insertion {ps} ps on clk (tools/qwen_blocks/mk_cts_skew_view.py); sign-off uses ../{name}\n")
