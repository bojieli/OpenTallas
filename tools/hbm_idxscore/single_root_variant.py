#!/usr/bin/env python3
"""L2H-IDXSCORE 2026-10-19: clone an r4 qw4c / qe4 kit as a ONE-ROOT variant (top ot_hbm_idx_score_q{w,e}_r4s, clock clk
centre-fed at the row seam), optional CTS clustering tag.  Usage: single_root_variant.py KIT NEWNAME [ncl|c16]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V = {"ncl": {"sink_clustering": False}, "c16": {"size": 16, "diameter_um": 20, "extra": "-sink_clustering_levels 2"}}
kit, new = sys.argv[1], sys.argv[2]
tag = sys.argv[3] if len(sys.argv) > 3 else None
s = json.loads((ROOT / "physical/ref_tile" / kit / "spec.json").read_text())
qw = s["top"].startswith("ot_hbm_idx_score_qw")
s["name"] = new
s["top"] = s["top"] + "s"
s["sources"] = ["rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_qwe_r4s.sv"] + s["sources"]
for k in ("clock", "clock_ports", "clock_data_paths", "clock_relationship", "clock_entry_domains"):
    s.pop(k, None)
s["clock_port"] = "clk"
old = ["clk_w0", "clk_w1"] if qw else ["clk_e0", "clk_e1"]
pr = s["pin_ranges"]
row = s["outline"]["h"] / 2
lo = pr[old[0]][0]
for o in old:
    pr.pop(o, None)
    s["pins"]["W"].remove(o)
s["pins"]["W"].insert(0, "clk")
# centre feed: the seam. qw W face is free between key_lines0's top (row 0 control section) and key_lines1's bottom; put
# clk just above rst_n (row 0 upper gap, ~ROW-15) -- qe W face is free at the seam (between r0_bus top and r1_qv)
pr["clk"] = [round(row - 1.08 - 0.54, 3), round(row - 0.54, 3)] if not qw else [round(lo, 3), round(lo + 1.08, 3)]
if not qw:
    pr["rst_n"] = [round(row, 3), round(row + 1.08, 3)]
if tag:
    s["route"]["cts_sink"] = V[tag]
s["structural_change"] += (" ONE-ROOT variant (L2H-IDXSCORE 10-19): top " + s["top"] + ", single clock clk centre-fed at the row seam"
                           + (f", CTS {tag} {json.dumps(V[tag])}" if tag else "") + ".")
d = ROOT / "physical/ref_tile" / new; d.mkdir(exist_ok=True)
(d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
rd = ROOT / "physical/ref_tile" / kit / "README.md"
if rd.exists():
    (d / "README.md").write_text(rd.read_text().replace(kit, new) + "\nONE-ROOT variant: item 7 = one centre-fed root at the row "
                                 "seam (two-root r4a-c: row-1 roots 88-287 ps, row-1 domain sinks placed across the seam).\n")
print(d)
