"""odd/even leaf-row offset: per driver ckm_d_i_j_k late arrival; pair (i, 2m) vs (i, 2m+1) (same leaf node)."""
import sys, re, statistics, json
out = {}
for f in sys.argv[1:]:
    a = {}
    for l in open(f):
        p = l.split()
        if p and p[0] == "D":
            m = re.match(r"ckm_d_(\d+)_(\d+)_(\d+)$", p[1])
            if m: a[tuple(map(int, m.groups()))] = float(p[2])
    d = [a[(i, j + 1, k)] - a[(i, j, k)] for (i, j, k) in a if j % 2 == 0 and (i, j + 1, k) in a]
    ev = [v for (i, j, k), v in a.items() if j % 2 == 0]; od = [v for (i, j, k), v in a.items() if j % 2 == 1]
    out[f] = dict(n_pairs=len(d), odd_minus_even_median_ps=round(statistics.median(d), 3), min=round(min(d), 3), max=round(max(d), 3),
                  spread_all=round(max(a.values()) - min(a.values()), 3), spread_even=round(max(ev) - min(ev), 3), spread_odd=round(max(od) - min(od), 3))
    print(f, out[f])
json.dump(out, open("oddeven.json", "w"), indent=1)
