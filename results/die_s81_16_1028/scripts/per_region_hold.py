#!/usr/bin/env python3
"""DIE-S81-16: intra related-pair slack PER REGION (die_sta_related reports only the die worst).
Runs main tools/die_plan/die_sta_related.py unchanged (same args, same output json) and re-times the pairs of every
time_class() call grouped by the pair tag (partition) -> region (map part_region), with the same callable arguments.
usage: per_region_hold.py TOOLS MAP.json OUT.json -- <die_sta_related args>
The intra class rows are the calls whose pair count equals corners.<C>.classes.intra.pairs in the written json."""
import collections, json, sys
tools, mp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, tools)
import die_sta_related as R
reg = json.load(open(mp))["part_region"]
orig = R.time_class
calls = []


def wrap(pairs, *a, **k):
    res = orig(pairs, *a, **k)
    by = collections.defaultdict(list)
    for p in pairs:
        by[p[2]].append(p)
    rows = {}
    for tag, ps in by.items():
        k2 = dict(k); k2.pop("rec", None)
        r = orig(ps, *a, **k2)
        rows[tag] = (len(ps), r.get("worst_setup_slack_ps"), r.get("setup_neg_pairs"), r.get("worst_hold_slack_ps"),
                     r.get("hold_neg_pairs"), (r.get("kit_contract_hold") or {}).get("worst_hold_bound_ps"))
    calls.append(dict(n=len(pairs), rows=rows))
    return res


R.time_class = wrap
R.main(args)
out = args[args.index("--out") + 1]
J = json.load(open(out + "/die_sta_related.json"))
res = {}
for C in [c for c in ("TT", "FF") if c in J["corners"]]:
    n = J["corners"][C]["classes"]["intra"]["pairs"]
    cand = [c for c in calls if c["n"] == n]
    c = cand[("TT", "FF").index(C)] if len(cand) == 2 else cand[0]
    g = collections.defaultdict(lambda: dict(parts=0, pairs=0, setup=None, setup_neg=0, hold=None, hold_neg=0, kit_hold=None))
    for tag, (np_, s, sn, h, hn, kh) in c["rows"].items():
        r = g[reg.get(tag, tag)]
        r["parts"] += 1; r["pairs"] += np_; r["setup_neg"] += sn or 0; r["hold_neg"] += hn or 0
        for key, v in (("setup", s), ("hold", h), ("kit_hold", kh)):
            if v is not None and (r[key] is None or v < r[key]):
                r[key] = v
    res[C] = dict(sorted(g.items(), key=lambda kv: (kv[1]["hold"] if kv[1]["hold"] is not None else 1e9)))
json.dump(res, open(outp, "w"), indent=1)
for C, g in res.items():
    neg = [k for k, v in g.items() if (v["hold"] or 0) < 0]
    print(f"PER-REGION {C}: regions {len(g)}, hold<0 in {len(neg)}; worst 10:")
    for k in list(g)[:10]:
        v = g[k]
        print(f"  {k:12s} parts {v['parts']:3d} pairs {v['pairs']:6d} setup {v['setup']} (neg {v['setup_neg']}) "
              f"hold {v['hold']} (neg {v['hold_neg']})")
