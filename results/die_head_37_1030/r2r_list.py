"""Read-only: list every r2r capture > 405 um (exact geom_rules.r2r_metrics math) as src -> capture, plus xy."""
import sys, inspect, json, re
sys.path.insert(0, sys.argv[1])
import geom_rules as G
src = inspect.getsource(G.r2r_metrics)
src = src.replace("        if mx > R2R_MAX:\n            n_gt += 1",
                  "        if mx > R2R_MAX:\n            n_gt += 1\n            LONG.append((round(mx,1), src, cap))")
assert "LONG.append" in src
G.LONG = []
exec(compile(src, "r2r", "exec"), G.__dict__)
D = G.Design(sys.argv[2], (), False)
m = G.r2r_metrics(D)
nm = lambda i: D.cells[i][6]
xy = lambda i: tuple(round(v, 1) for v in G.ctr(D.cells[i]))
rows = sorted(G.LONG, reverse=True)
print(json.dumps(dict(r2r_max=m["r2r_max"], n=len(rows))))
cls = {}
for d, s, c in rows:
    print(f"{d}\t{nm(s)}{xy(s)}\t->\t{nm(c)}{xy(c)}")
