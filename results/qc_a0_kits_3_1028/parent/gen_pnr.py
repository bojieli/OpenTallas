#!/usr/bin/env python3
"""QC-A0-KITS-3 parent CTS trial kit: one native ck (centre entry), Codex child fixtures placed at the fixture origins.
    python3 gen_pnr.py nk|nl"""
import json, re, sys
from pathlib import Path
t = sys.argv[1]
R = Path(__file__).resolve().parent; d = R / t
F = Path("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/a0_child_fixture")
ch = json.load(open(F / f"parent_{t}_children.json"))
v = (d / f"run/results/asap7/a0_{t}_1ck/base/1_2_yosys.v").read_text()
insts = {}
for m in re.finditer(r"^\s*(ot_qwen_tile_\w+)\s+\\(\S+)\s*\(", v, re.M):
    insts[m.group(2)] = m.group(1)
def norm(n): return n.replace("genblk5.", "")
mp, used = [], set()
for c in ch:
    hit = [n for n in insts if norm(n) == norm(c["inst"]) and insts[n] == c["module"]]
    if len(hit) != 1: raise SystemExit(f"no unique netlist inst for {c[inst]}: {hit}")
    used.add(hit[0]); mp.append((hit[0], c))
if set(insts) - used: raise SystemExit(f"unplaced children {sorted(set(insts)-used)}")
lines = ["# GENERATED gen_pnr.py: fixture child origins (at_exact), orient"]
for n, c in mp:
    lines.append("place_macro -macro_name {%s} -location {%.4f %.4f} -orientation %s" % (n.replace("[", "\\[").replace("]", "\\]"), c["at"][0], c["at"][1], c["orient"]))
(d / "macro_place.tcl").write_text("\n".join(lines) + "\n")
x = 0.012 + 0.048 * round((228.96 - 0.012) / 0.048)
(d / "io.tcl").write_text(
    "# GENERATED gen_pnr.py: native ck = ONE centre entry on M5 (track-snapped), data pins on the E face (UNCHECKED vs plan)\n"
    "place_pin -pin_name ck -layer M5 -location {%.3f 578.88} -pin_size {0.024 0.192}\n"
    "place_pins -hor_layers M4 -ver_layers M5 -exclude left:* -exclude top:* -exclude bottom:*\n" % x)
cfg = (d / "config.mk").read_text()
cfg = re.sub(r"^export (ADDITIONAL_LIBS|TC_LIB_FILES|BC_LIB_FILES|ADDITIONAL_LEFS) = .*\n", "", cfg, flags=re.M)
mods = sorted({c["module"] for c in ch})
cfg += "export ADDITIONAL_LEFS = " + " ".join(f"/work/macros/{m}.lef" for m in mods) + "\n"
cfg += "export ADDITIONAL_LIBS = " + " ".join(f"/work/macros/{m}_tt.lib" for m in mods) + "\n"
cfg += "export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) " + " ".join(f"/work/macros/{m}_tt.lib" for m in mods) + "\n"
cfg += "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) " + " ".join(f"/work/macros/{m}_ff.lib" for m in mods) + "\n"
cfg += """export MACRO_PLACEMENT_TCL = /work/macro_place.tcl
export IO_CONSTRAINTS = /work/io.tcl
export PDN_TCL = /work/pdn.tcl
export SET_RC_TCL = /work/setRC_rcx.tcl
export MACRO_PLACE_HALO = 0 0
export GPL_ROUTABILITY_DRIVEN = 0
export GPL_TIMING_DRIVEN = 0
export SKIP_CTS_REPAIR_TIMING = 1
export SKIP_LAST_GASP = 1
"""
(d / "config_pnr.mk").write_text(cfg)
print(t, len(mp), "children placed; ck x", x)
