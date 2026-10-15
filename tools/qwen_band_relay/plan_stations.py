#!/usr/bin/env python3
"""q15 r13 BAND relay successor: station plan.

Inputs: the actual c17 pin plan of qfd_sp_band_lanes (physical/ref_tile/qfd_sp_band_lanes_quarter/assigned_pins.tcl), the
CLOSED qfd_bl_lane LEF (pin faces) and the existing 16 lane origins (unchanged), lanes mirrored MX so the tw/ty face
points at the N-face ports.  For every lane and every bus group (TW, TY, TT, CP = {c, pw}, S = {rst, lnk, b0}) find two
relay station points s1, s2 in std-cell free space (outside lane bodies + 3 um) minimising the worst Manhattan hop
max(port->s1, s1->s2, s2->lane pin) over the group's bits (binary search, 6 um grid).  Stations are then clustered into
local std-cell clock roots (Manhattan radius RADIUS around the first member).  Writes results/rtl/qwen_band_relay_1015/
station_plan.json (stations, roots, hop table) used by the RTL root map and the kit placement hook.
Hop lengths are wire-plan estimates (Manhattan, no detour); timing is measured by the gate, not claimed here."""
import json, re, sys, collections
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
RADIUS = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
W, H = 881.28, 1131.84
LW, LH = 259.2, 151.2
LANES = [(25.92, 25.92), (311.04, 25.92), (596.16, 25.92), (25.92, 203.04), (311.04, 203.04), (596.16, 203.04),
         (25.92, 380.16), (311.04, 380.16), (596.16, 380.16), (25.92, 557.28), (311.04, 557.28), (596.16, 557.28),
         (25.92, 734.4), (311.04, 734.4), (596.16, 734.4), (25.92, 911.52)]
pins = {}
for line in (ROOT / 'physical/ref_tile/qfd_sp_band_lanes_quarter/assigned_pins.tcl').read_text().splitlines():
    m = re.search(r'\{(\w+)\[?(\d*)\]?\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}', line)
    if m:
        pins[(m.group(1), int(m.group(2) or 0))] = (float(m.group(3)), float(m.group(4)))
lef = (ROOT / 'physical/ref_tile/qfd_bl_lane_rr/views/qfd_bl_lane/qfd_bl_lane.lef').read_text()
lpin = {}
for n, b in re.findall(r'PIN (\S+)\n(.*?)END \1', lef, re.S):
    m = re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', b)
    if m:
        x0, y0, x1, y1 = map(float, m.groups())
        mm = re.match(r'(\w+)(?:\[(\d+)\])?', n)
        lpin[(mm.group(1), int(mm.group(2) or 0))] = ((x0 + x1) / 2, (y0 + y1) / 2)
def lp(l, name, i=0):           # lane l pin, lane mirrored MX (y -> LH - y)
    x, y = lpin[(name, i)]
    return (LANES[l][0] + x, LANES[l][1] + LH - y)
G = 6.0
X, Y = np.meshgrid(np.arange(3, W - 3, G), np.arange(3, H - 3, G)); X = X.ravel(); Y = Y.ravel()
ok = np.ones_like(X, bool)
for lx, ly in LANES:
    ok &= ~((X >= lx - 3) & (X <= lx + LW + 3) & (Y >= ly - 3) & (Y <= ly + LH + 3))
X = X[ok]; Y = Y[ok]
def groups(l):
    g = collections.defaultdict(list)
    for k in range(8):
        for j in range(32):
            b = 32 * (16 * k + l) + j
            g['TW'].append((pins[('tw', b)], lp(l, 'tw', 32 * k + j)))
            g['TY'].append((lp(l, 'ty', 32 * k + j), pins[('ty', b)]))
    for k in range(3):
        for j in range(32):
            g['TT'].append((pins[('tt', 32 * (16 * k + l) + j)], lp(l, 'tt', 32 * k + j)))
    g['TT'] += [(pins[('tt', 1536)], lp(l, 'tt', 96)), (pins[('tt', 1537)], lp(l, 'tt', 97))]
    for j in range(26):
        g['CP'].append((pins[('c', j)], lp(l, 'c', j)))
    for j in range(32):
        g['CP'].append((lp(l, 'pw', j), pins[('pw', 32 * l + j)]))
    g['S'] = [(pins[('rst_n', 0)], lp(l, 'rst_n')), (pins[('b0', 0)], lp(l, 'b0'))] + \
             [(pins[('lnk', i)], lp(l, 'lnk', i)) for i in range(6)]
    return g
def far(P):
    P = np.array(P)
    return np.max(np.abs(X[:, None] - P[None, :, 0]) + np.abs(Y[:, None] - P[None, :, 1]), axis=1)
stations, hops = [], {}
for l in range(16):
    for gname, P in groups(l).items():
        a = far([p[0] for p in P]); z = far([p[1] for p in P])
        lo, hi, best = 0.0, 3000.0, None
        while hi - lo > 2:
            h = (lo + hi) / 2
            i1 = np.where(a <= h)[0]; i2 = np.where(z <= h)[0]; good = False
            if len(i1) and len(i2):
                d = np.abs(X[i1][:, None] - X[i2][None, :]) + np.abs(Y[i1][:, None] - Y[i2][None, :])
                m = np.unravel_index(np.argmin(d), d.shape)
                if d[m] <= h:
                    good = True
                    best = (h, (float(X[i1[m[0]]]), float(Y[i1[m[0]]])), (float(X[i2[m[1]]]), float(Y[i2[m[1]]])))
            hi, lo = (h, lo) if good else (hi, h)
        s1, s2 = best[1], best[2]
        h1 = max(abs(p[0][0] - s1[0]) + abs(p[0][1] - s1[1]) for p in P)
        h3 = max(abs(p[1][0] - s2[0]) + abs(p[1][1] - s2[1]) for p in P)
        h2 = abs(s1[0] - s2[0]) + abs(s1[1] - s2[1])
        direct = max(abs(p[0][0] - p[1][0]) + abs(p[0][1] - p[1][1]) for p in P)
        hops[f'{l}.{gname}'] = dict(hop1=round(h1, 1), hop2=round(h2, 1), hop3=round(h3, 1), direct_max=round(direct, 1), bits=len(P))
        stations += [dict(lane=l, group=gname, stage=1, xy=s1, bits=len(P)), dict(lane=l, group=gname, stage=2, xy=s2, bits=len(P))]
roots = []
for s in sorted(stations, key=lambda s: (s['xy'][1], s['xy'][0])):
    for i, r in enumerate(roots):
        if abs(r['seed'][0] - s['xy'][0]) + abs(r['seed'][1] - s['xy'][1]) <= RADIUS:
            r['members'].append(s); s['root'] = i; break
    else:
        s['root'] = len(roots); roots.append(dict(seed=s['xy'], members=[s]))
rout = []
for i, r in enumerate(roots):
    xs = [m['xy'][0] for m in r['members']]; ys = [m['xy'][1] for m in r['members']]
    rout.append(dict(root=i, port=f'ck_st[{i}]', centroid=(round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)),
                     sinks=sum(m['bits'] for m in r['members']), stations=len(r['members']),
                     extent_um=round(max(xs) - min(xs) + max(ys) - min(ys), 1)))
worst = max(max(v['hop1'], v['hop2'], v['hop3']) for v in hops.values())
out = dict(schema='opentallas.qwen_band_relay.station_plan.v1', lanes_orient='MX', lanes=LANES, radius_um=RADIUS,
           groups={'TW': 'tw 256 N face -> lane', 'TY': 'ty 256 lane -> N face', 'TT': 'tt 98 E face -> lane',
                   'CP': 'c 26 E face -> lane + pw 32 lane -> E face', 'S': 'rst, b0, lnk 6 S face -> lane'},
           worst_hop_um=round(worst, 1), worst_direct_um=max(v['direct_max'] for v in hops.values()),
           n_roots=len(rout), roots=rout, stations=stations, hops=hops)
dst = ROOT / 'results/rtl/qwen_band_relay_1015/station_plan.json'
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(out, indent=1) + '\n')
print(f'roots {len(rout)} worst hop {worst:.1f} um (direct single-cycle predecessor worst {out["worst_direct_um"]} um); '
      f'max sinks/root {max(r["sinks"] for r in rout)}, max extent {max(r["extent_um"] for r in rout)} um -> {dst}')
