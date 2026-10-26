import sys, os, json, re, collections, math
src, dump, fil = sys.argv[1:4]
sys.path.insert(0, src + '/tools')
os.environ.setdefault('OT_RST_NET_UM', '380'); os.environ.setdefault('OT_RST_OK_UM', '405'); os.environ.setdefault('OT_RST_REP_VIEW', 'closed')
import importlib.util
spec = importlib.util.spec_from_file_location('b3r2x', fil); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
def T(x): return tuple(T(e) for e in x) if isinstance(x, list) else x
d = json.load(open(dump)); nets = []
for n in d['nets']:
    n = dict(n); n['drv'] = (n['drv'][0], n['drv'][1], tuple(n['drv'][2])); n['sinks'] = [(s[0], s[1], tuple(s[2])) for s in n['sinks']]
    n['sink_groups'] = {(a, b): T(g) for a, b, g in n.get('sink_groups') or []}; nets.append(n)
OCC = []; orig = B._RstOcc.__init__
def init(self, *a, **k): orig(self, *a, **k); OCC.append(self)
B._RstOcc.__init__ = init
CALLS = []; ro = B._rst_pad_route
def rr(occ, a, b, n, R, margin=1500.0):
    r = ro(occ, a, b, n, R, margin); CALLS.append((a, b, n, R, r is not None)); return r
B._rst_pad_route = rr
try:
    B._rst_tree_build(nets, [tuple(r) for r in d['rects']], d['W'], d['H'], d['gx'], d['gy']); print('OK')
except Exception as e:
    print('EXC', str(e)[:200])
print('route calls', len(CALLS), 'ok', sum(c[4] for c in CALLS), 'last', CALLS[-1][:4] if CALLS else None)
occ = OCC[-1]; a, b, n, R, _ = CALLS[-1]
w, h, g = B.RST_W, B.RST_H, B.RST_GAP_UM
for margin in (1500, 3000, 6000):
    sx, sy = w + g + occ.gx, h + g + occ.gy
    x0, x1 = max(0.0, min(a[0], b[0]) - margin), min(occ.W, max(a[0], b[0]) + margin)
    y0, y1 = max(0.0, min(a[1], b[1]) - margin), min(occ.H, max(a[1], b[1]) + margin)
    c = []
    y = y0
    while y + h <= y1:
        x = x0
        while x + w <= x1:
            cx = round(math.floor(x / occ.gx + 1e-9) * occ.gx, 6); cy = round(math.floor(y / occ.gy + 1e-9) * occ.gy, 6)
            if occ.free((cx, cy, cx + w, cy + h), g): c.append((cx + w / 2, cy + h / 2))
            x += sx
        y += sy
    dmin = sorted(abs(p[0] - b[0]) + abs(p[1] - b[1]) for p in c)[:5]
    print('margin', margin, 'cands', len(c), 'nearest to child', [round(q) for q in dmin])
