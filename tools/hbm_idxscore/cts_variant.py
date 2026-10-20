#!/usr/bin/env python3
"""L2H-IDXSCORE 2026-10-19: clone an r4 kit spec as a CTS-clustering variant (route.cts_sink), new kit name <kit>_<tag>.
r4a qe gate: pin_balance spreads the pin flops evenly over each face range (r2 -> r3 qe spread 36.5 -> 177.7 ps; r4a clk_e0
129.4 ps over 724 boundary sinks) and the default max-cap clustering hangs far pin-band flops on long leaf nets.
Usage: cts_variant.py KIT TAG  (TAG ncl = no sink clustering, c16 = size 16 / 20 um diameter clusters)"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
V = {"ncl": {"sink_clustering": False}, "c16": {"size": 16, "diameter_um": 20, "extra": "-sink_clustering_levels 2"}}
kit, tag = sys.argv[1], sys.argv[2]
s = json.loads((ROOT / "physical/ref_tile" / kit / "spec.json").read_text())
s["name"] = f"{kit}_{tag}"
s["route"]["cts_sink"] = V[tag]
s["structural_change"] += f" CTS variant {tag}: route.cts_sink {json.dumps(V[tag])} (pin-band boundary sinks)."
d = ROOT / "physical/ref_tile" / s["name"]; d.mkdir(exist_ok=True)
(d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
rd = (ROOT / "physical/ref_tile" / kit / "README.md")
if rd.exists():
    (d / "README.md").write_text(rd.read_text().replace(kit, s["name"]) + f"\nCTS variant {tag}: route.cts_sink {json.dumps(V[tag])}.\n")
print(d)
