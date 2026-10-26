#!/usr/bin/env python3
"""PATH-KV-GRT1 10-25: whole-bus channel-assignment feasibility for the KV W column N-S feedthroughs.

Question (PATH-KV lead decision 19:23): can a lane RE-ROUTE of whole buses between the W hgi column (hgi_v6/v7/v8)
and the W hg column (hg/hg_v1/hg_v3) bring every core-free N-S channel to <= ~0.8 of the die-share capacity
(STRICT model: head cores block through M7, so N-S ft bits only cross a row boundary in the core-free x channels)?

Exhaustive search: every movable pass-through bus (hub_Wi <-> io_W3 / sys side, endpoints outside both columns) is
assigned to one channel of either column (a bus never straddles a core: one port = one window); fixed loads stay
(astk / hg-local buses, hgi-local smalls).  Reports the minimum achievable max channel utilisation per scenario.
usage: w_chan_feasibility.py PLAN OUT.json

RESULT on plan e6326d34 (w_chan_feasibility.json): at the die_trial 25 % share NO whole-bus assignment reaches 1.0, let
alone 0.8 -- best 1.133 (S0); the fdi fork at hub_Wi, a 2-way L2048 split and even one extra 103.68-um hgi channel
only reach 1.105-1.132, because the hg channels have <= 373 b of room at 1.0 (184 b at 0.8) for 522-1044-b buses and
L663 (1044 b) alone exceeds any channel (944 b).  The same windows fit at a channel share of 0.35 (0.81) / 0.40 (0.71)
/ 0.50 (G2 part-probe own-logic model --adjust 0.5) with no re-route at all.
"""
import json, sys
from pathlib import Path

CAP = 0.25 * (1 / 0.048 + 1 / 0.064)          # die-share bits/um/direction (M5+M7 at 25 %), as chan_budget.py
CH = [(0, 17.28), (233.28, 336.96), (552.96, 656.64), (872.64, 976.32), (1192.32, 1278.72)]
X0 = {"hg": 1900.8, "hgi": 3179.52}
MOVABLE = ["L663", "L751", "L1524", "L2048", "L350", "L354"]


def loads(d, col, r):
    """per-channel bits on the boundary col_WN_r | col_WN_r+1, split into fixed + movable (by lane)."""
    a, b = f"{col}_WN_{r}", f"{col}_WN_{r + 1}"
    lane_of = {p: l["id"] for l in d["lanes"] for p in l["ports"]}
    fixed, mov = [0] * len(CH), {}
    for pr in d["ports"]:
        if {pr["src"]["part"], pr["dst"]["part"]} != {a, b}:
            continue
        m = sum(pr["window_um"]) / 2 - X0[col]
        k = next(i for i, (u, v) in enumerate(CH) if u - 1 <= m <= v + 1)
        lid = lane_of[pr["id"]]
        if lid in MOVABLE:
            mov[lid] = (pr["width"], col, k)
        else:
            fixed[k] += pr["width"]
    return fixed, mov


def solve(fixed, items, bins):
    """min over assignments of max(load/cap) (branch and bound, largest bus first); items = [(name, bits)],
    bins = [(col, k, cap_bits)]"""
    items = sorted(items, key=lambda x: -x[1])
    keys = [b[:2] for b in bins]
    cap = {b[:2]: b[2] for b in bins}
    ld0 = {k: fixed.get(k, 0) for k in keys}
    best = [max(ld0[k] / cap[k] for k in keys) if not items else 9e9, None, None]
    asg = []

    def rec(i, ld, cur):
        if cur >= best[0] - 1e-12:
            return
        if i == len(items):
            best[0], best[1], best[2] = cur, list(asg), dict(ld)
            return
        n, w = items[i]
        for k in sorted(keys, key=lambda k: (ld[k] + w) / cap[k]):
            u = (ld[k] + w) / cap[k]
            if max(cur, u) >= best[0] - 1e-12:
                continue
            ld[k] += w
            asg.append(k)
            rec(i + 1, ld, max(cur, u))
            asg.pop()
            ld[k] -= w

    rec(0, dict(ld0), max(ld0[k] / cap[k] for k in keys))
    u, a, ld = best
    return dict(max_util=round(u, 3), assign={n: f"{c}.c{k}" for (n, _), (c, k) in zip(items, a)},
                util={f"{c}.c{k}": round(ld[(c, k)] / cap[(c, k)], 2) for c, k in keys})


def main():
    d = json.loads(Path(sys.argv[1]).read_text())
    fh, mh = loads(d, "hg", 3)
    fi, mi = loads(d, "hgi", 3)
    mov = {**mh, **mi}
    fixed = {("hg", k): v for k, v in enumerate(fh)}
    fixed.update({("hgi", k): v for k, v in enumerate(fi)})
    out = dict(schema="opentallas.kv_w_chan_feasibility.v1", boundary="row 3|4 (all row boundaries identical)",
               cap_bits_per_um=round(CAP, 3), fixed_bits={f"{c}.c{k}": v for (c, k), v in fixed.items()},
               movable={k: v[0] for k, v in mov.items()}, scenarios={})

    def bins_for(share=0.25, extra_hgi_um=0.0):
        cap = share * (1 / 0.048 + 1 / 0.064)
        bs = [(c, k, (v - u) * cap) for c in ("hg", "hgi") for k, (u, v) in enumerate(CH)]
        if extra_hgi_um:
            bs.append(("hgi", 5, extra_hgi_um * cap))
        return bs

    whole = [(k, v[0]) for k, v in mov.items()]
    fdi_fork = [x for x in whole if x[0] != "L663"] + [("L663E", 522), ("L663W", 523)]
    fork_split = [x for x in fdi_fork if x[0] != "L2048"] + [("L2048a", 262), ("L2048b", 261)]
    sc = out["scenarios"]
    sc["S0_whole_buses"] = solve(fixed, whole, bins_for())
    sc["S1_fdi_fork_at_hub_Wi"] = solve(fixed, fdi_fork, bins_for())
    sc["S2_fdi_fork+L2048_split2"] = solve(fixed, fork_split, bins_for())
    sc["S3_whole+hgi_one_more_103.68um_channel"] = solve({**fixed, ("hgi", 5): 0}, whole, bins_for(extra_hgi_um=103.68))
    sc["S4_fdi_fork+hgi_one_more_channel"] = solve({**fixed, ("hgi", 5): 0}, fdi_fork, bins_for(extra_hgi_um=103.68))
    for sh in (0.30, 0.35, 0.40, 0.50):
        sc[f"S5_whole_buses_channel_share_{sh:.2f}"] = solve(fixed, whole, bins_for(share=sh))
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
    for k, v in sc.items():
        print(f"{k:45s} max_util {v['max_util']:.3f}  {v['assign']}")


if __name__ == "__main__":
    main()
