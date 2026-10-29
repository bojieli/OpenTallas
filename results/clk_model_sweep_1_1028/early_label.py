"""CLK-MODEL-SWEEP-1: how much of a die's intra skew_diag is planned core-tap earliness.  Per partition, max over tap pairs
of the NOMINAL early-arrival spread (same-type arrivals, CPPR-free) on raw tap arrivals (the skew_diag label) vs the same with every plan
early core tap's arrival + its declared early_ps (arrival minus planned target).  usage: TOOLS PROOF PLAN OUT"""
import json, sys, collections
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
from pathlib import Path
proof, plan, out = Path(sys.argv[2]), json.load(open(sys.argv[3])), sys.argv[4]
res = {}
for C in ("TT", "FF"):
    t = json.loads((proof / f"tap_arrivals_{C}.json").read_text())
    taps = {x["port"]: x for x in t["taps"]}
    ecm = R.early_core_map(plan, taps)
    by = collections.defaultdict(list)
    for p, x in taps.items():
        e = float(ecm[p][0]["early_ps"][C]) if p in ecm else 0.0
        by[x["part"]].append((p, x["late_ps"], x["early_ps"], e))
    rows = []
    for part, v in by.items():
        raw = max(e for _, _, e, _ in v) - min(e for _, _, e, _ in v)          # nominal (early-early) spread, CPPR-free
        adj = max(e + k for _, _, e, k in v) - min(e + k for _, _, e, k in v)
        rows.append((raw, adj, part, sum(1 for *_, k in v if k)))
    rows.sort(reverse=True)
    ra = sorted(rows, key=lambda r: -r[1])
    res[C] = dict(early_core_taps=len(ecm), parts=len(rows), worst_raw=rows[0][:4], worst_adjusted=ra[0][:4],
                  top_raw=[r[:4] for r in rows[:8]], top_adj=[r[:4] for r in ra[:8]])
    print(C, json.dumps({k: res[C][k] for k in ("early_core_taps", "parts", "worst_raw", "worst_adjusted")}))
json.dump(res, open(out, "w"), indent=1)
