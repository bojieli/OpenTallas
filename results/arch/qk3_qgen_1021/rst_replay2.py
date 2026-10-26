# QK3-QGEN: replay _rst_tree_build (from SRC's b3r2, or --file) on an OT_RESET_DUMP2; on a failure, report free sites near it
import sys, os, json, math
src, dump = sys.argv[1:3]; fil = sys.argv[3] if len(sys.argv) > 3 else None
sys.path.insert(0, src + '/tools')
os.environ.setdefault('OT_RST_NET_UM', '380'); os.environ.setdefault('OT_RST_OK_UM', '405'); os.environ.setdefault('OT_RST_REP_VIEW', 'closed')
import importlib.util
spec = importlib.util.spec_from_file_location('b3r2x', fil or (src + '/tools/qwen_rom_fulldie_b3r2.py'))
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
def T(x):
    return tuple(T(e) for e in x) if isinstance(x, list) else x
d = json.load(open(dump))
nets = []
for n in d['nets']:
    n = dict(n); n['drv'] = (n['drv'][0], n['drv'][1], tuple(n['drv'][2])); n['sinks'] = [(s[0], s[1], tuple(s[2])) for s in n['sinks']]
    n['sink_groups'] = {(a, b): T(g) for a, b, g in n.get('sink_groups') or []}
    nets.append(n)
rects = [tuple(r) for r in d['rects']]
OCC = []
orig = B._RstOcc.__init__
def init(self, *a, **k):
    orig(self, *a, **k); OCC.append(self)
B._RstOcc.__init__ = init
import re
try:
    cells, wires, per, errors = B._rst_tree_build(nets, rects, d['W'], d['H'], d['gx'], d['gy'])
    print('BUILD OK errors', len(errors), {k: (v['levels'], v.get('pad_p8'), v.get('pad_rep'), v.get('pad_on_edge'), v['max_net_um']) for k, v in per.items()})
except Exception as e:
    msg = str(e); print('BUILD EXC', msg[:400])
    m = re.search(r'child \[([\d.]+), ([\d.]+)\]', msg)
    if m and OCC:
        occ = OCC[-1]; x, y = float(m[1]), float(m[2])
        W, H = B.RST_W, B.RST_H
        free = 0; tot = 0
        for i in range(-60, 61):
            for j in range(-60, 61):
                cx, cy = x + i * 6, y + j * 6
                if abs(cx - x) + abs(cy - y) > 340: continue
                tot += 1
                r = (cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2)
                free += occ.free(r, B.RST_GAP_UM)
        rst = sum(1 for r in occ.g.get((int(x // 250), int(y // 250)), []) if abs((r[2] - r[0]) - W) < 1e-6 and abs((r[3] - r[1]) - H) < 1e-6)
        print(f'free probe sites within 340 um: {free}/{tot}; rst-size frames in the 250-um bucket: {rst}; occ rects in bucket {len(occ.g.get((int(x // 250), int(y // 250)), []))}')
        big = sorted({r for r in occ.g.get((int(x // 250), int(y // 250)), []) if (r[2] - r[0]) * (r[3] - r[1]) > 1000}, key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))[:6]
        print('big rects in bucket', [tuple(round(q, 1) for q in r) for r in big])
    if m and OCC:
        occ = OCC[-1]
        for lim in (400, 800, 1600, 3200, 6400):
            s = occ.site(x, y, None, lim=lim, budget=2000000)
            if s:
                print('nearest free rst site from child', s, 'dist', round(abs(s[0] + W / 2 - x) + abs(s[1] + H / 2 - y), 1), 'lim', lim)
                n = 0; pts = []
                while n < 60:
                    t = occ.site(s[0], s[1], None, lim=380, budget=200000)
                    if not t: break
                    occ.add((t[0], t[1], t[0] + W, t[1] + H)); n += 1; pts.append(t)
                print('cells that fit within 380 of it:', n, 'spread', (round(min(p[0] for p in pts),1), round(max(p[0] for p in pts),1), round(min(p[1] for p in pts),1), round(max(p[1] for p in pts),1)) if pts else None)
                break
