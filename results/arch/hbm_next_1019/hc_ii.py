#!/usr/bin/env python3
"""HBM-NEXT study (10-19), check (d): the HC row-speed risk.

D1 prices a further HC.HC_MIX row at II 250 (HCP W256 x6 mode, measured).  The static HC engine (codex/hc-static-engine
-1014 a35449ada, 128 MAC lanes) measured 4,385 cycles a further row (and 9,554 for one row vs the 1,160 price).
This re-times DS MTP (N = 6) and DS multi-user (N = P) on the UNCHANGED D1 model with the HC row II set to
II in {250, 600, 1000, 4385} and with HC rows dropped (per-position HC records: what the compiler falls back to when
the row form is slower).  Gives the II a P-lane HC engine must reach.

    PYTHONPATH=tools python3 results/arch/hbm_next_1019/hc_ii.py --out DIR [--jobs N]
"""
import argparse, json, multiprocessing as mp, sys
from pathlib import Path
from hgi_sim import hbm_plane_model as M
from hgi_sim import ds_mtp_verify as V

PS_ = (2, 4, 6)
IIS = (250, 600, 1000, 4385)


def jobs(st, drop):
    u6, uu = st["verify_union"][M.N_MTP]["mean"], st["users_union"]
    d = dict(drop=("HC",)) if drop else {}
    J = []
    for P in PS_:
        J.append(("ds", f"ds|MTP|P{P}", "verify", dict(P=P, N=M.N_MTP, union=u6, kv="upper", **d)))
        J.append(("ds", f"ds|MU|P{P}", "verify", dict(P=P, N=P, union=uu.get(P, 6.0 * P), users=True, **d)))
    return J


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--stats", type=Path, default=M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    a = ap.parse_args()
    st = M.load_stats(a.stats)
    mh = M._mh_ctl()
    M.d4g_env()
    with mp.get_context("fork").Pool(a.jobs) as pool:
        dr = dict(pool.imap_unordered(M._any, [("ds", f"ds|draft|P{P}", "draft",
                                                 dict(P=P, overlap=True, union=st["verify_union"][M.N_MTP]["mean"]))
                                                for P in PS_], chunksize=1))
    out = dict(schema="opentallas.hbm_next_1019.hc_ii.v1", model="tools/hgi_sim/hbm_plane_model.py (D1, unchanged)",
               rule=__doc__, hcp_ii_base=V.HCP_II, cases={})
    for case in [*(f"II{x}" for x in IIS), "noHCrows"]:
        if case.startswith("II"):
            V.HCP_II = float(case[2:])
        with mp.get_context("fork").Pool(a.jobs) as pool:            # fork: children inherit V.HCP_II
            res = dict(pool.imap_unordered(M._any, jobs(st, case == "noHCrows"), chunksize=1))
        row = {}
        for P in PS_:
            d = dr[f"ds|draft|P{P}"]
            v = res[f"ds|MTP|P{P}"]["cycles"]
            step = v + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
            mu = res[f"ds|MU|P{P}"]["cycles"]
            row[P] = dict(mtp_verify_cycles=v, ds_mtp_tok_s=round(M.TAU * M.CLK / step, 1), mu_step_cycles=mu,
                          mu_per_user_tok_s=round(M.CLK / mu, 1), mu_agg_tok_s=round(P * M.CLK / mu, 1),
                          hc_busy_mtp=res[f"ds|MTP|P{P}"]["unit_busy"].get("HC"),
                          hc_busy_mu=res[f"ds|MU|P{P}"]["unit_busy"].get("HC"))
        out["cases"][case] = row
        print(case, json.dumps({P: (r["ds_mtp_tok_s"], r["mu_agg_tok_s"], r["mu_per_user_tok_s"]) for P, r in row.items()}),
              flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "hc_ii.json").write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    sys.exit(main())
