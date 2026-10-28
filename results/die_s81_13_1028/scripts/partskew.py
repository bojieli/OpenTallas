"""per-partition in-region skew (FF): plain taps max late - min early; with core taps at late + declared FF insertion"""
import json, sys, collections
P = json.load(open(sys.argv[1])); pt = {q["name"]: q["type"] for q in P["partitions"]}
ins = {}
for q, ty in pt.items():
    for i, tp in enumerate(P["partition_types"][ty]["clock"].get("taps", [])):
        if tp.get("kind") == "core": ins[(q, "clk_c%d" % i)] = tp.get("insertion_ff_ps") or 0.0
for f in sys.argv[2:]:
    A = json.load(open(f)); by = collections.defaultdict(list)
    for r in A["taps"]:
        port = r["port"].split("__")[-1]; add = ins.get((r["part"], port), 0.0)
        by[r["part"]].append((r["late_ps"] + add, r["early_ps"] + add, port.startswith("clk_c")))
    sk = sorted(((max(x[0] for x in v) - min(x[1] for x in v)), p) for p, v in by.items())
    pl = sorted((max(x[0] for x in v if not x[2]) - min(x[1] for x in v if not x[2]), p) for p, v in by.items() if sum(not x[2] for x in v) > 1)
    n = len(sk)
    print(f, "parts", n, "skew(all incl core+ins) p50", round(sk[n // 2][0]), "p90", round(sk[9 * n // 10][0]), "max", [(round(a), b) for a, b in sk[-4:]],
          ">80", sum(a > 80 for a, _ in sk), "| plain-only p50", round(pl[len(pl) // 2][0]), "max", [(round(a), b) for a, b in pl[-3:]], ">80", sum(a > 80 for a, _ in pl))
