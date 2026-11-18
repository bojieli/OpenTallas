"""HOLD-TAP-1: replace the rise-only arrival readout of a combo GRT script by die_trial.clock_edge_readout (T/F/N/M rows, both
source edges, polarity-resolved), so the proof carries measured fall arrivals (FLOW-ONEMODEL-2).  usage: edge_readout_patch.py TOOLS CTREE_V COMBO_TCL CORNER"""
import sys
sys.path.insert(0, sys.argv[1])
import die_trial as D
v, tcl, corner = sys.argv[2:5]
try:
    lines = D.clock_edge_readout(open(v).read(), f"/out/arr_{corner}.txt", period="833.333", cells="ck_*", tap_slew=True, prefix="ck_")
except Exception:
    lines = D.clock_edge_readout(v, f"/out/arr_{corner}.txt", period="833.333", cells="ck_*", tap_slew=True, prefix="ck_")
L = open(tcl).read().split("\n")
a = next(i for i, l in enumerate(L) if l.startswith("set fh [open /out/arr_"))
b = next(i for i in range(a, len(L)) if L[i].strip() == "close $fh")
L[a:b + 1] = lines
open(tcl, "w").write("\n".join(L))
print("readout patched: lines", a, "-", b, "->", len(lines), "odd cells", lines[0].count(" 1"))
