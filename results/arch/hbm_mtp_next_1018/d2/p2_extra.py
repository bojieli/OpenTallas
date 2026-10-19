#!/usr/bin/env python3
"""HBM-MTP D2 (10-18): two more P = 2 points on the D1 model for the build order.
  rows_only_noVM : phase-1 die = row field on every unit, SM / attention lanes NOT built (sm serial, att_k 1), VM as built
                   (columns swapped); draft = the P = 1 rows-on draft (no lanes)
  MU_noVM        : 2 independent DS users (N = P = 2) without VM growth (the second user's column swapped)
    PYTHONPATH=tools python3 results/arch/hbm_mtp_next_1018/d2/p2_extra.py --out DIR
"""
import argparse, json, multiprocessing as mp, sys
from pathlib import Path
from hgi_sim import hbm_plane_model as M


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    st = M.load_stats(M.ROOT / "results/arch/hbm_mtp_next_1018/stats/summary.json")
    u6 = st["verify_union"][M.N_MTP]["mean"]; uu2 = st["users_union"][2]
    J = [("ds", "rows_only_noVM", "verify", dict(P=2, N=M.N_MTP, union=u6, kv="upper", drop=("SM", "VM"))),
         ("ds", "MU_noVM", "verify", dict(P=2, N=2, union=uu2, users=True, drop=("VM",))),
         ("ds", "MU", "verify", dict(P=2, N=2, union=uu2, users=True)),
         ("ds", "draft_rows_P1", "draft", dict(P=1, rows_on=True))]
    with mp.Pool(4) as pool:
        res = dict(pool.imap_unordered(M._any, J, chunksize=1))
    mh = M._mh_ctl(); d = res["draft_rows_P1"]
    v = res["rows_only_noVM"]["cycles"]; step = v + d["draft_cycles"] + d["seed_cycles"] + mh
    out = dict(schema="opentallas.hbm_mtp_next_1018.d2_p2_extra.v1", model="tools/hgi_sim/hbm_plane_model.py",
               rows_only_noVM=dict(verify_cycles=v, step_cycles=round(step, 1), ds_mtp_tok_s=round(M.TAU * M.CLK / step, 1),
                                   draft=d, unit_busy=res["rows_only_noVM"]["unit_busy"]))
    for k in ("MU", "MU_noVM"):
        c = res[k]["cycles"]
        out[k] = dict(cycles=c, aggregate_tok_s=round(2 * M.CLK / c, 1), per_user_tok_s=round(M.CLK / c, 1))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "p2_extra.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: (v.get("ds_mtp_tok_s") or v.get("aggregate_tok_s")) for k, v in out.items() if isinstance(v, dict)}))


if __name__ == "__main__":
    sys.exit(main())
