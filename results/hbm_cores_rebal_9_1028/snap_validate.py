#!/usr/bin/env python3
"""HBM-CORES-REBAL-9: apply gen_core_kit_hbm.snap_macro_placement to a kit copy's macro_placement.tcl and rerun the
FG2 (f) macro_pin_grid check (kit_contract at claude/fg2-macrogrid-1028@129d10d63d) on it.
usage: snap_validate.py KIT_COPY WT KIT_CONTRACT_DIR"""
import re, sys
from pathlib import Path
kd, wt, kcd = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path[:0] = [str(wt / "physical/die_plan/hbm_arch_cores"), str(wt / "tools/die_plan"), kcd]
import gen_core_kit_hbm as GK
import kit_contract_fg2f as KC
tcl = (kd / "macro_placement.tcl").read_text()
rows = re.findall(r"^  \{(.*?)\} (\S+) (\S+) (\S+) (\S+)$", tcl, re.M)
pl = [dict(inst=i, macro=m, xy_um=[float(x), float(y)], orient=o) for i, m, x, y, o in rows]
ol = [float(v) for v in re.search(r"DIE_AREA\s*=\s*0\s+0\s+(\S+)\s+(\S+)", (kd / "config.mk").read_text()).groups()]
lef = lambda m: (kd / "macros" / f"{m}.lef").read_text()
err0, info0 = KC.macro_pin_grid(kd)
print("BEFORE", info0, "failing macros", len(err0))
new, moves = GK.snap_macro_placement(pl, (kd / "make_tracks.tcl").read_text(), lef, ol)
print("outline", ol, "moves", len(moves), sorted({(m["dx_nm"], m["dy_nm"], m["orient"]) for m in moves}))
lines = ["foreach {inst master x y orient} {"] + [f"  {{{p['inst']}}} {p['macro']} {p['xy_um'][0]:g} {p['xy_um'][1]:g} {p['orient']}" for p in new]
body = tcl.split("} {\n", 1)[1] if "} {\n" in tcl else None
(kd / "macro_placement.tcl").write_text("\n".join(lines) + "\n} {\n" + tcl.rsplit("} {\n", 1)[1])
err, info = KC.macro_pin_grid(kd)
print("AFTER", info, "failing macros", len(err), err[:1])
again, m2 = GK.snap_macro_placement(new, (kd / "make_tracks.tcl").read_text(), lef, ol)
print("idempotent", not m2 and again == new)
