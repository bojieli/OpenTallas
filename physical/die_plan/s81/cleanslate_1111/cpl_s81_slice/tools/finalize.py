#!/usr/bin/env python3
"""CPL-S81-SLICE finalize: per type pick the best arrangement (hand_greedy+SA vs current+SA), score before/after
(bit-mm, worst cut H/V, face-entry, route_supply p99 with re-sited stations/taps, station EQ check), render after PNG,
write rows.  usage: finalize.py PLAN TYPE..."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl  # noqa: E402
import common  # noqa: E402
import search  # noqa: E402
import cplrender  # noqa: E402

P, conns = cpl.load(sys.argv[1])
cfg = cpl.rs_cfg()
SR, FI, PN = os.environ.get("SRCH", "srch"), os.environ.get("FIN", "fin"), os.environ.get("PNG", "png")
INTENT = os.environ.get("INTENT") == "1"
os.makedirs(PN, exist_ok=True)
os.makedirs(FI, exist_ok=True)


def metrics(M, S, pl):
    wv, wh = M.worst_cut(pl)
    ep, ew = M.entry(pl)
    r = cpl.rs_summary(M.rs(pl, cfg, conns, resite=True))
    return dict(bitmm=round(M.bitmm(pl), 1), cutV=round(wv[3], 3), cutV_at=wv[0], cutH=round(wh[3], 3), cutH_at=wh[0],
                entry=round(ep, 3), entry_worst=ew, rs_p99=r.get("p99"), rs_region=r.get("region"),
                rs_dir=r.get("dir"), cost=round(S.cost(pl)[0], 4), legal=S.legal(pl))


for n in sys.argv[2:]:
    M = common.model(P, conns, n)
    S = search.Search(M)
    if INTENT:
        S.set_intent()
    if os.environ.get("CGATE") == "1":
        S.set_gate(sys.argv[1], taps=True)
    res = json.load(open("%s/%s.json" % (SR, n)))
    pl0 = S.pl0
    m0 = metrics(M, S, pl0)
    cands = []
    for r in res["runs"]:
        pl = [tuple(x) for x in r["pl"]]
        cands.append((r["start"], pl, metrics(M, S, pl)))
    # pick: lowest cost among legal ones whose route_supply p99 is not worse than the plan by more than 0.02
    # and whose worst full cut does not rise above max(plan worst cut, 0.5); score = cost + rs_p99 (route supply
    # weighs as much as the bit-mm/entry cost, so a near-tie in cost goes to the better-supplied arrangement)
    wc0 = max(0.5, m0["cutV"], m0["cutH"])
    ok = [c for c in cands if c[2]["legal"] and (c[2]["rs_p99"] or 0) <= (m0["rs_p99"] or 0) + 0.02
          and max(c[2]["cutV"], c[2]["cutH"]) <= wc0 + 1e-6]

    def score(m):
        return m["cost"] + (m["rs_p99"] or 0)
    best = min(ok, key=lambda c: score(c[2])) if ok else None
    row = dict(type=n, bound_src=M.bound_src, edge=S.edge, gap=S.gap, before=m0, rule="legal, rs_p99<=plan+0.02, "
               "worst cut<=max(plan,0.5), min cost+rs_p99, adopt if below plan by >1e-3",
               cands={c[0]: c[2] for c in cands}, pick=best[0] if best else None)
    if best and score(best[2]) < score(m0) - 1e-3:
        pl = best[1]
        row["after"] = best[2]
        row["delta"] = {M.cores[i]["inst"]: [round(pl[i][0], 3), round(pl[i][1], 3), pl[i][2]]
                        for i in range(len(pl)) if tuple(pl[i]) != tuple(pl0[i])}
        cplrender.render(M, pl, "%s/%s_after.png" % (PN, n), "%s AFTER (%s) bit-mm %.0f (was %.0f)" % (
            n, best[0], best[2]["bitmm"], m0["bitmm"]), scores={"before": m0, "after": best[2]}, ref=pl0)
    else:
        row["after"] = None
        row["delta"] = {}
    cplrender.render(M, pl0, "%s/%s_before.png" % (PN, n), "%s BEFORE (plan 99f40d35) bit-mm %.0f" % (n, m0["bitmm"]),
                     scores={"before": m0})
    json.dump(row, open("%s/%s.json" % (FI, n), "w"), indent=1)
    print(json.dumps({k: row[k] for k in ("type", "pick")}), "before", {k: m0[k] for k in ("bitmm", "cutV", "cutH", "entry", "rs_p99")},
          "after", {k: row["after"][k] for k in ("bitmm", "cutV", "cutH", "entry", "rs_p99")} if row["after"] else None,
          "moved", len(row["delta"]), flush=True)
