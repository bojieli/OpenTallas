#!/usr/bin/env python3
"""DIE-S81-16 ESTIMATE plan_s10 -> plan_s11: early core taps (instances) and their DME sink delay (model ps = early/1.78)."""
import collections, json, sys
sys.path.insert(0, "tools/die_plan")
import schema as S
ratio = 1.78
for pl in sys.argv[1:]:
    R = S.load(pl); P = S.Plan(R)
    cnt = collections.Counter(x["type"] for x in R["partitions"])
    hist = collections.Counter(); tot = 0; by_mod = collections.defaultdict(list)
    for tn in R["partition_types"]:
        hc = {c["inst"]: c.get("module") for c in R["partition_types"][tn].get("hard_cores", [])}
        for nm, _, _, tp in S.core_taps(P, tn):
            e = S.core_tap_early_ps(P, tp, "TT")
            if e <= 0:
                continue
            m = next((v for k, v in hc.items() if tp["name"].startswith(k + ".")), "?")
            n = cnt[tn]; tot += n; by_mod[m] += [e] * n
            hist[min(int(e / ratio // 50) * 50, 400)] += n
    print(pl.split("/")[-1], "early instance taps", tot, "model-ps hist (50-ps bins, sink delay)", dict(sorted(hist.items())))
    for m, v in sorted(by_mod.items(), key=lambda kv: -len(kv[1]))[:8]:
        v.sort(); print("   ", m, len(v), "early TT p50/max", round(v[len(v) // 2], 1), round(v[-1], 1), "sink", round(v[len(v) // 2] / ratio, 1))
