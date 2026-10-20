#!/usr/bin/env python3
"""LH-REPRICE3 (10-19, successor of d4g_reprice3_1019): REPRICE3 + the evidence owed since its 08:05 checkpoint.

Runs tools/hgi_sim/d4g_reprice3_1019.py unchanged (all REPRICE3 TERMS, measured-controller BW floor, bank-client
budgets) and adds, as explicit TERMS:
  gen2e_su     GEN2e SU LG tap bank-client relays to the 18/15 source profile (708d112f3: bank0 read 4/3, bank1 read
               5/2, both write 3/4, bankface 1 + core 6/3 + own 4 => READ_RETURN 18 / WRITE_RETURN 15) instead of the
               1017 kits' 10/7: +8 an SU-executed record reading VM, +8 an SU-executed record writing VM (latency
               fully exposed once a record; priced -- GEN2e is still PRE-RELAY, depths are the planned profile).
  hbm_bridge   HBM-BW SAFE successor edge bridge (native cold-bridge proof 277b256 / II1 / +1): +1 edge on every record
               with an HBM-space operand (SM, ATT, DMA from HBM, SU with an HBM source).  Successor scenario only.
Grade notes (no value change): att_merge DS = SU merge RTL bench PASS (TW4 78bf1fdc8, function) with the model
latency -> 'priced'; COLL VM_RT 74 (+g4 10 = 84) is CODEX-COLL-SAFE's measured E+84 (n1s0/n2s1 v74 SRAM rings), already
inside the composed banklat row.
Area (not a cycle term): d4g GEN2e die 20,200 x 31,773.52 um = 641.83 mm2 (grants_d4g.json) + BW SAFE successor
+181,099.93 um2/PC x 64 PC + smh_xs_ring +101,616.8 um2 x 256 SM tiles (16 SM x NC 8 x NP 2) + hcoll_gq_issue_sram
+98,836.4 um2 x 4 quadrants; reticle 26 x 33 mm = 858 mm2.

  PYTHONPATH=tools python3 -m hgi_sim.d4g_reprice3b_1019 --bw 45.03 --out current.json
  PYTHONPATH=tools python3 -m hgi_sim.d4g_reprice3b_1019 --bw 90.67 --bridge 1 --out successor.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import d4g_reprice3_1019 as R3

GEN2E_SU = dict(read=18 - 10, write=15 - 7)
DIE_MM2 = 20200.0 * 31773.52 / 1e6
RETICLE_MM2 = 26.0 * 33.0
AREA_ADD_UM2 = {
    "hbm_bw_safe_pc_ctrl": (181099.93, 64, "codex/hbm-bw-safe-1019 432x475.2 vs h9b/c 155.52 square; 64 GEN2e PCs (conditional)"),
    "smh_xs_ring_1019": (101616.8, 256, "codex/hbm-smhxs-ring-rg2-1019 432x345.6 vs 302.4x157.68; one xs per SM tile, 16 SM x 16"),
    "hcoll_gq_issue_sram_1019": (98836.4, 4, "codex/hbm-gqissue-sram-1019 432x345.6 vs 224.64 square; one per quadrant"),
}


def _hbm_operand(r):
    return any(getattr(d, "space", None) == "HBM" for d in (getattr(r, "desc", None) or {}).values())


def main():
    bridge = 0
    argv = list(sys.argv[1:])
    if "--bridge" in argv:
        i = argv.index("--bridge")
        bridge = int(argv[i + 1])
        del argv[i:i + 2]
    out = Path(argv[argv.index("--out") + 1])
    bw = float(argv[argv.index("--bw") + 1]) if "--bw" in argv else 45.03
    sys.argv = [sys.argv[0]] + argv
    orig_main = R.main

    def main_hook():
        R.TERMS["gen2e_su"] = (dict(GEN2E_SU), "priced", "+8 an SU-executed record reading VM (tap READ_RETURN 18 vs 10), "
                               "+8 writing VM (WRITE_RETURN 15 vs 7); exposed once a record",
                               "GEN2e sourceprofile 708d112f3 (TW5-GEN2E 09:54), HBM-BANKLAT-SU rt18 (TW5-BANKLATSU)")
        if bridge:
            R.TERMS["hbm_bridge"] = (bridge, "measured", f"+{bridge} edge a record with an HBM-space operand "
                                     "(successor cold bridge +1)", "HBM-BW predicate-truth native bridge 277b256/II1/+1 "
                                     "(lanes/HBM-BW.md 11:21; successor not adopted)")
        m = R.TERMS["att_merge"]
        R.TERMS["att_merge"] = (m[0], "priced", m[2], m[3] + "; SU merge RTL bench PASS + 4 mutants FAIL TW4 78bf1fdc8 "
                                "(function; latency = model)")
        for t in ("gen2e_su", "hbm_bridge"):
            if t in R.TERMS and t not in R.COMPOSED:
                R.COMPOSED.append(t)
        inner = R.rp_added                                   # already REPRICE3's patched adder

        def rp_added(r, c, kn):
            add = inner(r, c, kn)
            rp = kn.get("rp") or set()
            if "gen2e_su" in rp and R.Q.su_exec(r):
                v = (GEN2E_SU["read"] if R._reads_vm(r) else 0) + (GEN2E_SU["write"] if R._writes_vm(r) else 0)
                if v:
                    add += v
                    R._add("gen2e_su", v)
            if "hbm_bridge" in rp and _hbm_operand(r):
                add += bridge
                R._add("hbm_bridge", bridge)
            return add
        R.rp_added = rp_added
        return orig_main()

    R.main = main_hook
    rc = R3.main()
    doc = json.loads(out.read_text())
    adds = {k: dict(um2_each=v[0], n=v[1], mm2=round(v[0] * v[1] / 1e6, 3), source=v[2]) for k, v in AREA_ADD_UM2.items()}
    tot = round(DIE_MM2 + sum(a["mm2"] for a in adds.values()), 2)
    doc["lane"] = "LH-REPRICE3"
    doc["tool"] = "tools/hgi_sim/d4g_reprice3b_1019.py (wraps d4g_reprice3_1019.py)"
    doc["scenario"] = dict(bw_bytes_per_edge_per_sm=bw, hbm_bridge=bridge, gen2e_su=GEN2E_SU)
    doc["area"] = dict(base_die_mm2=round(DIE_MM2, 2), base_source="hd4g-gen2e results/arch/hbm_die_d4g/grants_d4g.json die_um",
                       adds=adds, total_mm2=tot, reticle_mm2=RETICLE_MM2, margin_mm2=round(RETICLE_MM2 - tot, 2),
                       note="outline deltas (slot growth), conservative; die height 31.77 of 33 mm -> growth goes in width")
    doc["accepted"] = dict(ds_ar_tok_s=1973.3, ds_ar_tok_s_alt=1955.7, note="owner 10-16 accepted demonstrated rate")
    c = doc["table"]["info_banklat_all"]
    doc["composed_banklat"] = dict(ds_ar_tok_s=c["ds_ar_tok_s"], qwen_tok_s=c["qwen_tok_s"],
                                   ds_vs_1973_3_pct=round(100 * (c["ds_ar_tok_s"] / 1973.3 - 1), 2),
                                   ds_vs_1955_7_pct=round(100 * (c["ds_ar_tok_s"] / 1955.7 - 1), 2))
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
