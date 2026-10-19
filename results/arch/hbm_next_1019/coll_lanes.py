#!/usr/bin/env python3
"""HBM-NEXT study (10-19), check (a): the collective / network ceiling at P lanes.

The d4g price delivers every off-die collective over the die's COLL delivery lanes: D = (G - 1) f / lanes cycles,
f = ceil(bytes / G / 64), G = 192, lanes = 4 (ds_die_split.deliver; d4g_quadrant adders).  At 4 lanes that is
256 B/cycle = 307 GB/s into a die.  The die's SerDes is 32 x 100G = 400 GB/s raw a direction (ds_switch_planes);
after framing (64-B min frame + 40 B overhead, payload_eff >= 0.8 at P >= 2 for the large classes) about 320-385 GB/s.
So the SerDes admits at most ~5 delivery lanes' worth; 8 lanes would be port-drain bound.

This re-times DS AR, DS MTP (N = 6) and DS multi-user (N = P) on the UNCHANGED D1 model
(tools/hgi_sim/hbm_plane_model.py) with the COLL delivery lanes set to L in {4, 5, 8}:
  L = 4  the d4g die (reproduction check: must equal D1's run.json),
  L = 5  the widest COLL the per-die SerDes can feed (the honest "COLL widened" point),
  L = 8  on-die only, NOT feedable by 400 GB/s SerDes (info: what the on-die COLL alone could buy).

    PYTHONPATH=tools python3 results/arch/hbm_next_1019/coll_lanes.py --out DIR [--jobs N]
"""
import argparse, json, multiprocessing as mp, sys
from pathlib import Path
from hgi_sim import hbm_plane_model as M
from hgi_sim import plan_study_price_1017 as PS

PS_ = (2, 4, 6)


def jobs(st):
    u6, uu = st["verify_union"][M.N_MTP]["mean"], st["users_union"]
    J = [("ds", "ds|AR", "verify", dict(P=1, N=1))]
    for P in PS_:
        J.append(("ds", f"ds|MTP|P{P}", "verify", dict(P=P, N=M.N_MTP, union=u6, kv="upper")))
        J.append(("ds", f"ds|draft|P{P}", "draft", dict(P=P, overlap=True, union=u6)))
        J.append(("ds", f"ds|MU|P{P}", "verify", dict(P=P, N=P, union=uu.get(P, 6.0 * P), users=True)))
    return J


def run_lanes(L, st, n):
    M.d4g_env()
    PS.VARIANTS["b"]["split"]["lanes"] = L
    M._ENV["kn"]["lanes"] = L
    M._ENV["vb"] = PS.VARIANTS["b"]
    with mp.get_context("fork").Pool(n) as pool:                     # fork: children inherit the patched env
        return dict(pool.imap_unordered(M._any, jobs(st), chunksize=1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=10); ap.add_argument("--lanes", default="4,5,8")
    ap.add_argument("--stats", type=Path, default=M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    a = ap.parse_args()
    st = M.load_stats(a.stats)
    mh = M._mh_ctl()
    out = dict(schema="opentallas.hbm_next_1019.coll_lanes.v1", model="tools/hgi_sim/hbm_plane_model.py (D1, unchanged)",
               rule=__doc__, by_lanes={})
    for L in (int(x) for x in a.lanes.split(",")):
        res = run_lanes(L, st, a.jobs)
        ar = res["ds|AR"]["cycles"]
        row = dict(ds_ar_cycles=ar, ds_ar_tok_s=round(M.CLK / ar, 1), P={})
        for P in PS_:
            d = res[f"ds|draft|P{P}"]
            v = res[f"ds|MTP|P{P}"]["cycles"]
            step = v + d["draft_cycles"] + d["seed_cycles"] + mh - d["overlap"]["credit"]
            mu = res[f"ds|MU|P{P}"]["cycles"]
            row["P"][P] = dict(mtp_verify_cycles=v, mtp_step_cycles=round(step, 1),
                               ds_mtp_tok_s=round(M.TAU * M.CLK / step, 1),
                               mu_step_cycles=mu, mu_per_user_tok_s=round(M.CLK / mu, 1),
                               mu_agg_tok_s=round(P * M.CLK / mu, 1),
                               mtp_busy=res[f"ds|MTP|P{P}"]["unit_busy"], mu_busy=res[f"ds|MU|P{P}"]["unit_busy"])
        out["by_lanes"][L] = row
        print(L, json.dumps({P: (r["ds_mtp_tok_s"], r["mu_agg_tok_s"], r["mu_per_user_tok_s"]) for P, r in row["P"].items()}),
              row["ds_ar_tok_s"], flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "coll_lanes.json").write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    sys.exit(main())
