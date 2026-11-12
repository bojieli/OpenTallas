# HBM-GEOM-2 11-12 kshare pin-file re-face (DIE-HBM-100; data HBM-CORES-B; partner faces from the t40c plan
# internal_stations + bound q_hub RTL).  usage: kshare_refc.py VARIANT SRC OUT
#   abcr (v8e478a 445.824 x 506.304, u_vmks_Q1 nw/ne R0): c_k_wdata / c_kr_data slices by ctl partner
#       ([255:0] p04 far W -> W, [511:256] p05 N -> N, [1023:512] p06/p07 E -> E); g_kr_data (svg W) -> W;
#       w_k_wdata (wbk SW) -> S.
#   pfr (v700685 354.24 x 453.6, u_vmks_Q0/Q2/Q3 nw/ne, ne Q0 MY): w_k_* (wbk: core-frame E for 4 of 6
#       instances) S -> E; c_k_wdata (ctl partners E/N, mixed) E -> N.
# Every face is spread evenly over [8.64, len - 8.64] on its single pin layer (E/W M4, N/S M5, as today;
# symmetric tracks, offset pitch/2), keeping today's along-face order for staying pins; track use <= 0.70 per layer.
import json, re, sys, collections
var, src, out = sys.argv[1:4]
DIM = {'abcr': (445.824, 506.304), 'pfr': (354.24, 453.6)}[var]
W, H = DIM
PITCH = {'M4': 0.048, 'M5': 0.048, 'M6': 0.064, 'M7': 0.064}
LAYS = {'W': ('M4',), 'E': ('M4',), 'N': ('M5',), 'S': ('M5',)}   # single layer as today: M6/M7 core pins land off the plan tracks in G0
J = json.load(open(src))
def face(p):
    return 'W' if p['x'] < 0.5 else 'E' if p['x'] > W - 0.5 else 'S' if p['y'] < 0.5 else 'N' if p['y'] > H - 0.5 else 'I'
def bit(p):
    m = re.search(r'\[(\d+)\]', p['name']); return int(m.group(1)) if m else 0
def base(p):
    return re.sub(r'\[.*', '', p['name'])
def target(p):
    f, b, n = face(p), bit(p), base(p)
    if var == 'abcr':
        if n in ('c_k_wdata', 'c_kr_data'):
            return 'W' if b < 256 else 'N' if b < 512 else 'E'
        if n == 'g_kr_data': return 'W'
        if n == 'w_k_wdata': return 'S'
    else:
        if n.startswith('w_k_'): return 'E'
        if n == 'c_k_wdata': return 'N'
    return f
HINT = {'abcr': {'W': 400.0, 'N': 300.0, 'E': 100.0, 'S': 0.0}, 'pfr': {'E': 400.0, 'N': 0.0}}[var]
old = collections.Counter(face(p) for p in J)
tgt = {id(p): target(p) for p in J}
rep = {}
for f in 'WENS':
    ps = [p for p in J if tgt[id(p)] == f]
    if not ps:
        rep[f] = dict(old=old[f], new=0); continue
    ps.sort(key=lambda p: ((p['y'] if f in 'EW' else p['x']) if face(p) == f else HINT[f], base(p), bit(p)))
    L = H if f in 'EW' else W
    lo, hi = 8.64, L - 8.64
    la = LAYS[f]
    # pin i goes on layer la[i % len(la)]
    use = {}
    for li, ln in enumerate(la):
        sub = ps[li::len(la)]; pit = PITCH[ln]; ntr = int((hi - lo) / pit)
        use[ln] = round(len(sub) / ntr, 3)
        assert len(sub) / ntr <= 0.70, (f, ln, len(sub), ntr)
        for i, p in enumerate(sub):
            k = int((lo + (i + 0.5) * (hi - lo) / len(sub)) / pit)
            c = round(pit / 2 + k * pit, 4)
            if f == 'W': p['x'], p['y'] = 0.096, c
            if f == 'E': p['x'], p['y'] = round(W - 0.096, 4), c
            if f == 'S': p['x'], p['y'] = c, 0.096
            if f == 'N': p['x'], p['y'] = c, round(H - 0.096, 4)
            p['layer'] = ln
    rep[f] = dict(old=old[f], new=len(ps), per_um=round(len(ps) / (hi - lo), 2), track_use=use)
k = collections.Counter((p['layer'], round(p['x'], 3), round(p['y'], 3)) for p in J)
assert not [v for v in k.values() if v > 1], 'duplicate pin sites'
json.dump(J, open(out, 'w'), indent=1)
print(var, json.dumps(rep))
