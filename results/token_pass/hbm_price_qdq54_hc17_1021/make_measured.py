#!/usr/bin/env python3
"""TOKb-HBMPRICE 10-21: measured-law inputs for the HBM d4g census (tools/hgi_sim/toksim_hbm_census_1019.py --measured).

base_h9b.json   = measured_rel.json (TOKSIM-HBM) with SM.MATVEC <- units_variants/smhbm_h9b_bound.json  (= scenario meas_h9b)
priced_h9b.json = base_h9b + the two coordinator-approved HBM latency costs (no numerics change):
  QDQ  FUSED.QDQ_FP8: measured 58 edges at RL 7 (bench VM model = 7 edges at the quant pins) -> RL 54 (hb_quant_NW
       ot_hgi_qdq_host_split_r3 + transport ctl_r4s): every beat's read answer returns RL_NEW - RL_OLD = 47 edges later;
       the 16-beat record is pipelined (RLI ring), so record latency first-read -> record_done = 58 + 47 = 105.
  HC   HC.HC_MIX: measured 1055 on GEN2e3 root (TAILC 0: tail inside the root, L 496 at SDIV 7). Release root binds the
       hardened tail child (TAILC 1, TE 2) with tail k4 (TSDIV 17 TTPIPE 1 TSKP 2: CAP 699, L 989 -> TX = 989 - 496 = 493);
       the emit moves TE + TX = 2 + 493 = 495 edges (root TE 2 -> 495; RTL lockstep PASS 48 '+495', claude/hc13-tail-k4-1021
       dbb4b616d) -> 1055 + 495 = 1550.
Edges are 833 ps core/stream edges (1.2 GHz).
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
M = ROOT / "results/token_pass/measured_hbm_1019"
RL_OLD, RL_NEW = 7, 54
TAIL_L_K2, TAIL_L_K4, TE_TAILC = 496, 989, 2
D_QDQ = RL_NEW - RL_OLD                          # 47
D_HC = TE_TAILC + (TAIL_L_K4 - TAIL_L_K2)        # 495
out = Path(sys.argv[1])
m = json.loads((M / "measured_rel.json").read_text())
h9 = json.loads((M / "units_variants/smhbm_h9b_bound.json").read_text())
for d, cl in h9["designs"].items():
    for c, law in cl.items():
        m["designs"][d][c] = dict(law, group="smhbm_h9b_bound")
        m["sources"][f"{d}/{c}"] = "units_variants/smhbm_h9b_bound.json"
(out / "base_h9b.json").write_text(json.dumps(m, indent=1) + "\n")


def bump(law, delta, model):
    law = json.loads(json.dumps(law))
    for sk, e in law["shapes"].items():
        if e.get("cycles") is not None:
            e["cycles_before_hbmprice"] = e["cycles"]
            e["cycles"] = e["cycles"] + delta
    if law.get("ratio") is not None:                 # unmatched shapes (none expected) keep the per-record delta
        law["ratio_before_hbmprice"] = law["ratio"]
        law["ratio"] = round(law["ratio"] + delta / model, 4)
    return law


ds = m["designs"]["ds_ar"]
ds["FUSED.QDQ_FP8"] = dict(bump(ds["FUSED.QDQ_FP8"], D_QDQ, 25.0), hbmprice=f"RL {RL_OLD} -> {RL_NEW}: +{D_QDQ} edges a record")
ds["HC.HC_MIX"] = dict(bump(ds["HC.HC_MIX"], D_HC, 1162.9), hbmprice=f"tail k4 TSDIV 17 + TAILC TE: +{D_HC} edges a record")
for d in m["designs"]:
    for c in m["designs"][d]:
        if d != "ds_ar" and ("QDQ" in c or c.startswith("HC.")):
            raise SystemExit(f"unexpected {d}/{c}: price it")
(out / "priced_h9b.json").write_text(json.dumps(m, indent=1) + "\n")
print("deltas", dict(qdq=D_QDQ, hc=D_HC))
