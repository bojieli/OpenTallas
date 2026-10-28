#!/usr/bin/env python3
"""DIE-S81-16 (COORD 15:2x): classify the worst N intra FF hold pairs into terms, ESTIMATE only, fixes nothing.
Runs main die_sta_related.py unchanged; wraps time_class to get the exact arguments of the FF intra call, then for each
pair takes the min-hold endpoint combo (same endpoint_slacks formula) and splits
  hold = data_min (clkq_min - hold) - unc_h - ocv_h - [ nominal skew (ec+latB - ea-latA) + uncredited spread (lc-ec-cr) ]
nominal skew is split further: tree early-early (ec-ea) and endpoint latency (latB-latA, core-tap declared insertion).
usage: hold_classify.py TOOLS OUT.json N -- <die_sta_related args>"""
import collections, inspect, json, sys
tools, outp, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, tools)
import die_sta_related as R
orig, calls = R.time_class, []
sig = inspect.signature(orig)


def wrap(*a, **k):
    calls.append(sig.bind(*a, **k).arguments)
    return orig(*a, **k)


R.time_class = wrap
R.main(args)
out = args[args.index("--out") + 1]
J = json.load(open(out + "/die_sta_related.json"))
n = J["corners"]["FF"]["classes"]["intra"]["pairs"]
cand = [c for c in calls if len(c["pairs"]) == n]
C = cand[-1]                      # corners run TT then FF
taps, rng, reg, ocv, views = C["taps"], C["rng"], C["reg"], C.get("ocv"), C.get("views")
meta = json.load(open(args[0] + "/tap_arrivals_FF.json"))
nst, nlate, nearly = meta["node_stages"], meta["node_late_ps"], meta["node_early_ps"]
ecm = set(C.get("kit_offset") or {})
rows = []
for a, b, tag in C["pairs"]:
    A, B = taps[a], taps[b]
    node = R.pair_node(A, B)
    la, ea, lc, ec = R.arr4(A, B, node)
    cr = R.credit(rng, node, la, ea, lc, ec)
    ma_l = views[a] if views else [R.budget_model(reg, 0.0)]
    mb_l = views[b] if views else [R.budget_model(reg, 0.0)]
    best = None
    for ma in ma_l:
        for mb in mb_l:
            h = (ea + ma["lat_early"] + ma["clkq_min"]) - (lc + mb["lat_late"] + mb["hold"]) - C["unc_h"] + cr
            if best is None or h < best[0]:
                best = (h, ma, mb)
    h, ma, mb = best
    oh = ocv(a, b, "hold") if ocv else 0.0
    h -= oh
    nd = node
    while nd not in nst and len(nd) > 1:
        nd = nd[:-1]
    rows.append(dict(h=h, a=a, b=b, tag=tag, node=node, data=ma["clkq_min"] - mb["hold"], unc=C["unc_h"], ocv=oh,
                     tree_skew=ec - ea, lat_skew=mb["lat_late"] - ma["lat_early"], spread=lc - ec, credit=cr,
                     unc_spread=lc - ec - cr, launch_spread=la - ea, rng_node=rng.get(nd, 0.0),
                     a_core=a in ecm, b_core=b in ecm, ma=ma["name"], mb=mb["name"],
                     st_a=A.get("stages_from_root", 0) - nst.get(nd, 0), st_b=B.get("stages_from_root", 0) - nst.get(nd, 0),
                     dist=abs(A["xy_um"][0] - B["xy_um"][0]) + abs(A["xy_um"][1] - B["xy_um"][1]),
                     lca_depth=len(node)))
rows.sort(key=lambda r: r["h"])
ws = rows[:N]
neg = [r for r in rows if r["h"] < 0]


def agg(rs):
    k = ("h", "data", "unc", "ocv", "tree_skew", "lat_skew", "unc_spread", "spread", "credit", "launch_spread", "st_a",
         "st_b", "dist")
    return {x: dict(mean=round(sum(r[x] for r in rs) / len(rs), 1), min=round(min(r[x] for r in rs), 1),
                    max=round(max(r[x] for r in rs), 1)) for x in k}


def dominant(r):
    t = dict(clock_skew_nominal=r["tree_skew"] + r["lat_skew"], uncredited_spread=r["unc_spread"], ocv_aocv=r["ocv"],
             unc=r["unc"])
    return max(t, key=t.get)


res = dict(pairs=len(rows), hold_neg=len(neg), worst=round(rows[0]["h"], 2), N=N, worst_N=agg(ws), all_neg=agg(neg) if neg else None,
           dominant_worst_N=collections.Counter(dominant(r) for r in ws),
           dominant_all_neg=collections.Counter(dominant(r) for r in neg),
           core_tap_involved_worst_N=dict(launch=sum(r["a_core"] for r in ws), capture=sum(r["b_core"] for r in ws)),
           core_tap_involved_all_neg=dict(launch=sum(r["a_core"] for r in neg), capture=sum(r["b_core"] for r in neg)),
           regions_worst_N=collections.Counter(r["tag"] for r in ws).most_common(12),
           neg_if_no_skew=sum(1 for r in neg if r["h"] + r["tree_skew"] + r["lat_skew"] < 0),
           neg_if_no_unc_spread=sum(1 for r in neg if r["h"] + r["unc_spread"] < 0),
           neg_if_no_ocv=sum(1 for r in neg if r["h"] + r["ocv"] < 0),
           neg_if_spread_and_ocv_gone=sum(1 for r in neg if r["h"] + r["unc_spread"] + r["ocv"] < 0),
           neg_if_skew_and_spread_gone=sum(1 for r in neg if r["h"] + r["unc_spread"] + r["tree_skew"] + r["lat_skew"] < 0),
           neg_h_quantiles={q: round(sorted(r["h"] for r in neg)[int(q / 100 * (len(neg) - 1))], 1) for q in (1, 5, 25, 50, 75, 95)} if neg else None,
           neg_with_h_ge={x: sum(1 for r in neg if r["h"] >= -x) for x in (10, 25, 50, 100, 200)},
           neg_core_tap_pairs_worst=round(min([r["h"] for r in neg if r["a_core"] or r["b_core"]] or [0]), 1),
           neg_no_core_tap_worst=round(min([r["h"] for r in neg if not (r["a_core"] or r["b_core"])] or [0]), 1),
           neg_no_core_tap_count=sum(1 for r in neg if not (r["a_core"] or r["b_core"])),
           rows=[{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for r in ws])
json.dump(res, open(outp, "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str))
for r in ws[:12]:
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items() if k != "node"})
