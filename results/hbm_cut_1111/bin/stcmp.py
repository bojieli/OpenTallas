import csv, sys
def load(p): return {r["type"]: r for r in csv.DictReader(open(p), delimiter="\t")}
a, b = load(sys.argv[1]), load(sys.argv[2])
for t in sorted(b):
    ra, rb = a.get(t, {}), b[t]
    k = lambda r, c: int(r.get(c) or 0)
    if any(k(ra, c) != k(rb, c) for c in ("plan_stations", "phantom_n", "missing_gt_reach_n", "misattr_n", "viasoft_n")) or t not in a:
        print(t, "stations", k(ra, "plan_stations"), "->", k(rb, "plan_stations"), "phantom", k(ra, "phantom_n"), "->", k(rb, "phantom_n"),
              "miss>405", k(ra, "missing_gt_reach_n"), "->", k(rb, "missing_gt_reach_n"), "misattr", k(ra, "misattr_n"), "->", k(rb, "misattr_n"))
