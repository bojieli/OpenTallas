# FT-S81 10-23: input = cap24 plan.json (ep9 /srv/opentallas-scratch2/claude/stw-s81c-cap24-main/plan.json), env FT_S81_PLAN; quick estimate until tools/die_feedthrough census/plan land.
import json, sys, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(__import__('os').environ.get('FT_S81_PLAN', 'dump/plan.json'))); C = json.load(open(__import__('os').environ.get('FT_S81_CENSUS', 'census_1500.json')))
fig, ax = plt.subplots(figsize=(16.5, 13))
cm = plt.get_cmap('viridis')
for b in P['blocks']:
    if b['w'] * b['h'] < 0.5e6: 
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fc='0.85', ec='0.5', lw=0.3)); continue
    c = C['blocks'].get(b['name']); t = (c['H_bits'] + c['V_bits']) if c else 0
    ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fc=cm(min(t / 10000, 1)) if t else 'white', ec='k', lw=0.5, alpha=0.8))
    ax.text(b['x'] + b['w'] / 2, b['y'] + b['h'] / 2, f"{b['name']}\n{t//1000}k" if t else b['name'], ha='center', va='center', fontsize=5, color='w' if t > 5000 else 'k')
for L in P['links']:
    if L['c'] not in ('x_frame', 'ret', 'xtier', 'unit', 'idx', 'coll'): continue
    (_, _, sx, sy, _), (_, _, dx, dy, _) = L['e'][0], L['e'][1]
    ax.plot([sx, dx, dx], [sy, sy, dy], lw=0.15, color='r', alpha=0.4)
ax.set_xlim(0, 33000); ax.set_ylim(0, 26000); ax.set_aspect('equal')
ax.set_title('S81 cap24: ft crossing bits per big block (direct Manhattan L-path, colour 0..10k bits), red = long lanes')
plt.savefig(sys.argv[1], dpi=110, bbox_inches='tight')
