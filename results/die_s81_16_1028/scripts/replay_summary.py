#!/usr/bin/env python3
"""summarise replay.jsonl (old = die-s81-15 tools, new = + join budget) per region x mode"""
import collections, json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
by = collections.defaultdict(dict)
for r in rows:
    by[(r["pkl"].rsplit("/", 1)[-1], r["mode"])][r["tool"]] = r
for mode in ("hang", "merge"):
    ks = [k for k in by if k[1] == mode and len(by[k]) == 2]
    same = sum(1 for k in ks if by[k]["old"].get("h") and by[k]["old"].get("h") == by[k]["new"].get("h"))
    to = [k for k in ks if by[k]["old"].get("timeout")]
    fb = [k for k in ks if (by[k]["new"].get("st") or {}).get("join_fallbacks")]
    err = [k for k in ks if "err" in by[k]["old"] or "err" in by[k]["new"]]
    fin = [k for k in ks if not by[k]["old"].get("timeout") and "h" in by[k]["old"]]
    diff = [k for k in fin if by[k]["old"]["h"] != by[k]["new"].get("h")]
    so = sorted(by[k]["old"]["s"] for k in ks if "s" in by[k]["old"])
    sn = sorted(by[k]["new"]["s"] for k in ks if "s" in by[k]["new"])
    print(f"{mode}: regions {len(ks)}; old finished {len(fin)} (timeout>=120s {len(to)}), byte-identical where old finished "
          f"{same}/{len(fin)} (diff {len(diff)}: {[k[0] for k in diff][:5]}), new join_fallbacks in {len(fb)} regions, errors {len(err)}")
    if so and sn:
        print(f"   time s old p50/max {so[len(so)//2]}/{so[-1]} sum {round(sum(so))} | new p50/max {sn[len(sn)//2]}/{sn[-1]} sum {round(sum(sn))}")
    if fb:
        g = [by[k]["new"]["st"] for k in fb]
        print("   fallbacks total", sum(x["join_fallbacks"] for x in g), "worst gap ps", max(x["join_fallback_worst_gap_ps"] for x in g),
              "worst imb after", max(x["join_fallback_worst_imb"] for x in g))
        dfb = [k for k in fb if k in fin]
        print("   fallback regions where old finished <120 s:", len(dfb))
