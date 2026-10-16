#!/usr/bin/env python3
"""Pin-to-pin bus overlay of the compact660_v5 plan (H-DIE 2026-10-15): every planned link drawn between its two PLANNED
PIN windows (compact660_v5.pins.json), not block centres; colour = relay stages at the 480-um reach (ceil(d/480)-1),
width ~ log2(bits).  Also writes the per-class stage table (centre model vs pin model).
    bus_overlay_pins.py OUT.png OUT.json [PLAN_DIR TAG PREFIX]"""
import json, math, sys
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / (sys.argv[3] if len(sys.argv) > 3 else 'results/arch/hbm_die_v15/compact660_v5')
TAG = sys.argv[4] if len(sys.argv) > 4 else 'compact660_v5'
PRE = sys.argv[5] if len(sys.argv) > 5 else 'compact'
pins = json.loads((D / f'pins/{TAG}.pins.json').read_text())
P = json.loads((D / f'{PRE}.P.json').read_text()); g = json.loads((D / f'{PRE}.graph.json').read_text())
W, H = pins['die_outline_um']
pin = {}
for b, v in pins['blocks'].items():
    for f, fv in v['faces'].items():
        for p in fv['pins']:
            pin.setdefault((p['link'], b), (p['x'], p['y']))
st = lambda d: max(0, math.ceil(d / 480) - 1)
fig, ax = plt.subplots(figsize=(16, 11))
for n, b in P.items():
    if isinstance(b, dict) and 'x' in b:
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fill=True, color='0.92', ec='0.5', lw=0.3))
cm = plt.get_cmap('RdYlGn_r')
agg = defaultdict(lambda: dict(links=0, bits=0, max_pin=0, sum_pin=0, sum_ctr=0))
for l in sorted(g['links'], key=lambda l: l['bits']):
    a, b = l['src'], l['dst']; pa, pb = pin.get((l['id'], a)), pin.get((l['id'], b))
    if not pa or not pb:
        continue
    d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]); s = st(d)
    ca = (P[a]['x'] + P[a]['w'] / 2, P[a]['y'] + P[a]['h'] / 2); cb = (P[b]['x'] + P[b]['w'] / 2, P[b]['y'] + P[b]['h'] / 2)
    r = agg[l['cls']]; r['links'] += 1; r['bits'] += l['bits']; r['max_pin'] = max(r['max_pin'], s)
    r['sum_pin'] += s * l['bits']; r['sum_ctr'] += st(abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])) * l['bits']
    ax.plot([pa[0], pa[0], pb[0]], [pa[1], pb[1], pb[1]], color=cm(min(s, 12) / 12), lw=0.3 + math.log2(max(l['bits'], 2)) / 3,
            alpha=0.8)
sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(0, 12)); fig.colorbar(sm, ax=ax, label='relay stages (pin to pin, 480 um)')
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal')
ax.set_title(f'{TAG} buses PIN-TO-PIN (L routes between planned pin windows); width ~ log2 bits', fontsize=9)
fig.savefig(sys.argv[1], dpi=110, bbox_inches='tight')
tab = {k: dict(links=v['links'], bits=v['bits'], max_stages_pin=v['max_pin'], mean_stages_pin=round(v['sum_pin'] / v['bits'], 1),
               mean_stages_centre_model=round(v['sum_ctr'] / v['bits'], 1)) for k, v in sorted(agg.items(), key=lambda t: -t[1]['bits'])}
Path(sys.argv[2]).write_text(json.dumps(tab, indent=1) + '\n')
