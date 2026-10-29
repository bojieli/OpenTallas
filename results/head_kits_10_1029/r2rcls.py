import sys, inspect, re, collections
sys.path.insert(0, sys.argv[1])
import geom_rules as G
src = inspect.getsource(G.r2r_metrics)
src = src.replace("        if mx > R2R_MAX:\n            n_gt += 1", "        if mx > R2R_MAX:\n            n_gt += 1; OUT.append((mx, src, cap))")
src = src.replace("def r2r_metrics(D):", "def r2r_x(D, OUT):")
ns = dict(G.__dict__); exec(src, ns)
D = G.Design(sys.argv[2], (), False); OUT = []
ns['r2r_x'](D, OUT)
nm = lambda i: D.cells[i][6] if i in D.cells else str(i)
def cls(s): return re.sub(r'\\?\[[0-9]+\\?\]|[0-9]+', '#', s.split('/')[0].split('.')[0])
c = collections.Counter((cls(nm(s)), cls(nm(d))) for _, s, d in OUT)
for k, v in c.most_common(15): print(v, k)
