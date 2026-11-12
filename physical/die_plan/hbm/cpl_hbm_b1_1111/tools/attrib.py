"""route_supply net attribution: which recorded nets put H/V demand on a region. usage (cwd = wt):
attrib.py PLAN REFDIR TYPE X0 X1 Y0 Y1 [N]"""
import sys, collections
sys.path.insert(0, "tools/die_plan")
import route_supply as rs
plan, ref, tn, X0, X1, Y0, Y1 = sys.argv[1:8]; X0, X1, Y0, Y1 = map(float, (X0, X1, Y0, Y1)); N = int(sys.argv[8]) if len(sys.argv) > 8 else 15
rs.DEFAULTS["record_nets"] = True
keep = {}
GR = []
_gi = rs.Grid.__init__
def _ini(self, *a, **k):
    _gi(self, *a, **k); GR.append(self)
rs.Grid.__init__ = _ini
orig = rs.analyze_type
def wrap(name, *a, **k):
    r = orig(name, *a, **k)
    if r is not None and name == tn: keep["r"] = r
    return r
rs.analyze_type = wrap
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    rs.main([plan, "--die", "hbm", "--repo", ".", "--ref-dirs", ref, "--types", tn, "--out", "/tmp/attrib_rs"])
rec = [x for g in GR if g.rec for x in g.rec]; b = 10.8
agg = collections.defaultdict(lambda: [0.0, 0.0, 0])
for cat, label, x0, x1, y0, y1, n in rec:
    w, h = max(x1 - x0, b), max(y1 - y0, b)
    ix = max(0, min(x0 + w, X1) - max(x0, X0)); iy = max(0, min(y0 + h, Y1) - max(y0, Y0))
    if ix <= 0 or iy <= 0: continue
    frac = ix * iy / ((X1 - X0) * (Y1 - Y0))
    lab = label if isinstance(label, tuple) else (label,)
    key = (cat,) + tuple(str(v)[-34:] for v in lab[:3])
    a = agg[key]; a[0] += n * (x1 - x0) / (w * h) * b * frac; a[1] += n * (y1 - y0) / (w * h) * b * frac; a[2] += 1
tot = [sum(v[0] for v in agg.values()), sum(v[1] for v in agg.values())]
print("region tracks H %.1f V %.1f" % tuple(tot))
for k, v in sorted(agg.items(), key=lambda kv: -kv[1][0])[:N]: print("H %6.2f V %6.2f n%4d %s" % (v[0], v[1], v[2], k))
