#!/usr/bin/env python3
"""HBM-NEXT study (10-19), check (b): VM capacity at P lanes.  DS MTP (N = 6) and DS multi-user (N = P) at P = 2, 4, 6
on the UNCHANGED D1 model with the VM as built (2^18 words: verify / user columns swapped per layer, drop VM) vs grown
(N resident columns, +(N - 1) x ~30k words; the D1 headline).
    PYTHONPATH=tools python3 results/arch/hbm_next_1019/vm_cap.py --out DIR
"""
import argparse, json, multiprocessing as mp, sys
from pathlib import Path
from hgi_sim import hbm_plane_model as M

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    st = M.load_stats(M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    u6, uu = st["verify_union"][M.N_MTP]["mean"], st["users_union"]
    J = []
    for P in (2, 4, 6):
        J.append(("ds", f"ds|MTP_noVM|P{P}", "verify", dict(P=P, N=M.N_MTP, union=u6, kv="upper", drop=("VM",))))
        J.append(("ds", f"ds|MU_noVM|P{P}", "verify", dict(P=P, N=P, union=uu.get(P, 6.0 * P), users=True, drop=("VM",))))
        J.append(("ds", f"ds|draft|P{P}", "draft", dict(P=P, overlap=True, union=u6)))
    M.d4g_env()
    with mp.get_context("fork").Pool(a.jobs) as pool:
        res = dict(pool.imap_unordered(M._any, J, chunksize=1))
    mh = M._mh_ctl(); out = dict(schema="opentallas.hbm_next_1019.vm_cap.v1", rule=__doc__, P={})
    for P in (2, 4, 6):
        d = res[f"ds|draft|P{P}"]; v = res[f"ds|MTP_noVM|P{P}"]["cycles"]
        step = v + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
        mu = res[f"ds|MU_noVM|P{P}"]["cycles"]
        out["P"][P] = dict(mtp_noVM_verify=v, ds_mtp_noVM_tok_s=round(M.TAU * M.CLK / step, 1), mu_noVM_cycles=mu,
                           mu_noVM_per_user=round(M.CLK / mu, 1), mu_noVM_agg=round(P * M.CLK / mu, 1),
                           busy_mtp=res[f"ds|MTP_noVM|P{P}"]["unit_busy"], busy_mu=res[f"ds|MU_noVM|P{P}"]["unit_busy"])
        print(P, out["P"][P]["ds_mtp_noVM_tok_s"], out["P"][P]["mu_noVM_agg"], out["P"][P]["mu_noVM_per_user"], flush=True)
    a.out.mkdir(parents=True, exist_ok=True); (a.out / "vm_cap.json").write_text(json.dumps(out, indent=1, default=str) + "\n")

if __name__ == "__main__":
    sys.exit(main())
