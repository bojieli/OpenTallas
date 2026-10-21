#!/usr/bin/env python3
"""REFILL-2/S81 (10-21) parallel fallbacks of dsdv_sh_lk_s10g / s10h: k-means regional CTS (clock_split_km.tcl).

Why: the s10g / s10h --cts gates (10-21 04:25 / 04:36) FAILED only clock_rule: 14,318 sinks on one TritonCTS root,
pin-flop spread TT 147.2 / FF 129.9 ps (s10g) and TT 171.4 / FF 146.2 ps (s10h) > 80.  Fix (same recipe that took the
COLL lanes s8n 121.6 -> s8nk 83 ps): split the ck port net into K compact sink clusters with one local root each under a
balanced top tree.  q = K 24, r = K 32.  Same RTL, outline, macros, pins, PDN, layer contract and cycles.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
for base in ("s10g", "s10h"):
    for tag, k in (("q", 24), ("r", 32)):
        s = json.loads((ROOT / f"physical/ref_tile/dsdv_sh_lk_{base}/spec.json").read_text())
        name = f"dsdv_sh_lk_{base}{tag}"
        s["name"] = name
        s.setdefault("pre_cts_extra", [])
        if "physical/common_flow/clock_split_km.tcl" not in s["pre_cts_extra"]:
            s["pre_cts_extra"].append("physical/common_flow/clock_split_km.tcl")
        s.setdefault("orfs_vars", {})
        s["orfs_vars"]["OT_CKKM_K"] = str(k)
        s["orfs_vars"]["OT_CKKM_PORT"] = "ck"
        s["structural_change"] = __doc__.strip() + f"\n\n--- {base} base ---\n" + s["structural_change"]
        j = s["job"]
        j.update(tag=name, purpose=j["purpose"].replace(f"dsdv_sh_lk_{base}", name) + f"; k-means CTS K={k}")
        d = ROOT / "physical/ref_tile" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(d / "spec.json")
