#!/usr/bin/env python3
"""QC-S28-DIEVIEW: per-family before/after from two qc_die_audit.py audit.tsv files.

    python3 -I qc_die_compare.py BEFORE.tsv AFTER.tsv OUT.tsv
Family = type stem (sle_/slw_ merged, __cl/__pv and _vN dropped).  Per family: types, instances, route p99 max and
median, types with p99 > 1.0 / > 0.8, taps over the cap, max sinks per tap, station/ft hops > 405, stale station ends
(> 60 um), soft fill range, slot / natural range, and the per-type rows that changed."""
import csv
import re
import statistics
import sys
from collections import defaultdict


def fam(t):
    f = re.sub(r"__.*", "", t)
    f = re.sub(r"_v\d+$", "", f)
    return re.sub(r"^(sle|slw)_", "sl_", f)


def load(p):
    return {r["type"]: r for r in csv.DictReader(open(p), delimiter="\t")}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summ(rows):
    p = [v for v in (num(r["route_p99"]) for r in rows) if v is not None]
    return dict(types=len(rows), inst=sum(int(r["instances"]) for r in rows),
                p99_max=max(p) if p else None, p99_med=round(statistics.median(p), 3) if p else None,
                p99_gt1=sum(1 for v in p if v > 1.0), p99_gt08=sum(1 for v in p if v > 0.8),
                taps_over=sum(int(r["taps_over_cap"]) for r in rows),
                max_sinks=max(int(r["max_sinks_tap"]) for r in rows),
                hops=sum(int(r["hops_gt405"]) for r in rows), stale=sum(int(r.get("stale_gt60", 0) or 0) for r in rows))


def main():
    b, a, out = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3]
    fb, fa = defaultdict(list), defaultdict(list)
    for t, r in b.items():
        fb[fam(t)].append(r)
    for t, r in a.items():
        fa[fam(t)].append(r)
    keys = ["types", "inst", "p99_max", "p99_med", "p99_gt1", "p99_gt08", "taps_over", "max_sinks", "hops", "stale"]
    with open(out, "w") as f:
        f.write("family\t" + "\t".join(f"{k}_before\t{k}_after" for k in keys) + "\n")
        for k in sorted(set(fb) | set(fa)):
            sb, sa = summ(fb.get(k, [])) if fb.get(k) else {}, summ(fa.get(k, [])) if fa.get(k) else {}
            f.write(k + "\t" + "\t".join(f"{sb.get(c, '')}\t{sa.get(c, '')}" for c in keys) + "\n")
    tot_b, tot_a = summ(list(b.values())), summ(list(a.values()))
    print("DIE before", tot_b)
    print("DIE after ", tot_a)
    ch = []
    for t in sorted(set(a) & set(b)):
        d = [c for c in ("W", "H", "route_p99", "taps", "max_sinks_tap", "taps_over_cap", "hops_gt405", "stale_gt60",
                         "min_street_V", "min_street_H", "ring_bands") if a[t].get(c) != b[t].get(c)]
        if d:
            ch.append(t + ": " + ", ".join(f"{c} {b[t].get(c)}->{a[t].get(c)}" for c in d))
    print(f"{len(ch)} types changed")
    for c in ch:
        print("  " + c)


if __name__ == "__main__":
    main()
