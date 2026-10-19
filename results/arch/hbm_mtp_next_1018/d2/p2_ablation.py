#!/usr/bin/env python3
"""HBM-MTP D2 (10-18): the P = 2 feature ablation on the D1 model (tools/hgi_sim/hbm_plane_model.py, unchanged).
D1 ablated each feature only at P = 6; the D2 build order needs the cycles each feature buys AT P = 2 (N = 6 verify
rows, DSpark gamma 5, tau 4.159, union = MTP-STATS P6 decorrelated mean, KV upper bound), plus two combinations:
  noVM      = P = 2 without the VM growth (verify columns swapped, as built)
  noVM_ATT  = P = 2 matrix-only lanes (no multi-query attention) and no VM growth
Step = verify + draft(P2) + seed(P2) + MH ctl - seed/head overlap credit (as hbm_plane_model.compose).

    PYTHONPATH=tools python3 results/arch/hbm_mtp_next_1018/d2/p2_ablation.py --out DIR [--jobs N]
"""
import argparse, json, multiprocessing as mp, sys
from pathlib import Path
from hgi_sim import hbm_plane_model as M

DROPS = {"base": (), "noSM": ("SM",), "noVM": ("VM",), "noATT": ("ATT",), "noFUSED": ("FUSED",), "noHC": ("HC",),
         "noCOLL": ("COLL",), "noIDX": ("IDX",), "noSU_DMA": ("SU_DMA",), "noVM_ATT": ("VM", "ATT")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--stats", type=Path, default=M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    a = ap.parse_args()
    st = M.load_stats(a.stats); u6 = st["verify_union"][M.N_MTP]["mean"]
    J = [("ds", f"ds|P2|{k}", "verify", dict(P=2, N=M.N_MTP, union=u6, kv="upper", drop=d)) for k, d in DROPS.items()]
    J.append(("ds", "ds|draft|P2", "draft", dict(P=2, overlap=True, union=u6)))
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.imap_unordered(M._any, J, chunksize=1))
    mh = M._mh_ctl(); d = res["ds|draft|P2"]; ov = d["overlap"]["credit"]
    out = dict(schema="opentallas.hbm_mtp_next_1018.d2_p2_ablation.v1", model="tools/hgi_sim/hbm_plane_model.py",
               union_mean_N6=u6, mh_ctl=mh, draft=d, rows={})
    base = res["ds|P2|base"]["cycles"]
    for k in DROPS:
        v = res[f"ds|P2|{k}"]["cycles"]; step = v + d["draft_cycles"] + d["seed_cycles"] + mh - ov
        out["rows"][k] = dict(verify_cycles=v, cycles_saved_by_feature=round(v - base, 1), step_cycles=round(step, 1),
                              ds_mtp_tok_s=round(M.TAU * M.CLK / step, 1), unit_busy=res[f"ds|P2|{k}"]["unit_busy"])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "p2_ablation.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: (v["ds_mtp_tok_s"], v["cycles_saved_by_feature"]) for k, v in out["rows"].items()}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
