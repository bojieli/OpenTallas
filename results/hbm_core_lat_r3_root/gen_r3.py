#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 driver: gen_core_kit_hbm.main with the RTL top renamed <module>__rtl (kit copy only) so the
hand-checked superset-face wrapper can take the plan module name.  Usage: gen_r3.py WT MODULE RTLFILE -- gen args"""
import sys, re, tempfile
from pathlib import Path
wt, module, rtlfile = sys.argv[1:4]
args = sys.argv[sys.argv.index("--") + 1:]
src = (Path(wt) / rtlfile).read_text()
new, n = re.subn(r"(?m)^(\s*module\s+)" + re.escape(module) + r"\b", lambda m: m[1] + module + "__rtl", src, count=1)
assert n == 1, "top module not found"
tmp = Path(tempfile.mkdtemp()) / Path(rtlfile).name
tmp.write_text(new)
sys.path.insert(0, str(Path(wt) / "physical/die_plan/hbm_arch_cores"))
sys.argv = ["gen_core_kit_hbm.py"] + args
import gen_core_kit_hbm as G
G.main(source_overrides={rtlfile: str(tmp)})
