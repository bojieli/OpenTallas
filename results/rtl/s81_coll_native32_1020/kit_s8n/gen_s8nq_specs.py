#!/usr/bin/env python3
"""S81-COLL-1021 (10-21) successors of dscoll_lane_{w,e}_s8nk: k-means regional CTS with K=24 (s8nq) / K=32 (s8nr).

Why: the s8n / s8nk --cts gates (10-21 01:53-02:09, ep6) FAILED only clock_rule (pin-flop spread > 80 ps within the one
region): s8n TritonCTS TT 121.6 / 118.3 ps (E / W); s8nk K=16 TT 83.0 / 87.8, FF 69.6 / 86.6 ps.  All else passed: census
max 32, trial GRT overflow 0, setup/hold WNS >= 0 at the placement STA.  The pin_balance bit order (group_max 1) spreads the
four wide buses over the full W/E faces (99% of 583 um), so the boundary flops form a 2 x 583 um perimeter ring 726 um apart;
K=16 arcs (~90 um of ring each) left a ~85 ps tail.  The fix splits the ring into shorter arcs (K=24 ~ 60 um, K=32 ~ 45 um)
with one local root each under the balanced top tree, so each leaf tree is small and the top tree balances equal-load
roots.  Same RTL, outline, macros, pins / bit order, PDN, layer contract and cycles; no timing constraint relaxed.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-coll-1021"

if __name__ == "__main__":
    for side in ("w", "e"):
        for tag, k in (("s8nq", 24), ("s8nr", 32)):
            s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_s8nk/spec.json").read_text())
            name = f"dscoll_lane_{side}_{tag}"
            s["name"] = name
            s["orfs_vars"]["OT_CKKM_K"] = str(k)
            s["structural_change"] = __doc__.strip() + "\n\n--- s8nk base ---\n" + s["structural_change"]
            j = s["job"]
            j.update(owner="Claude:S81-COLL-1021", branch=BR, tag=tag,
                     views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
                     purpose=j["purpose"].replace("K=16", f"K={k}"))
            d = ROOT / "physical/ref_tile" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print("wrote", d / "spec.json")
