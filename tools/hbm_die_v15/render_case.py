#!/usr/bin/env python3
"""Render layout images for visual inspection (OWNER RULE 20:45 PT 10-15) -- H-DIE.
    render_case.py kit  KIT_DIR OUT.png                # ref_tile kit: outline, core, macros (+20 um halo), pin faces, clock entry
    render_case.py die  CASE_DIR OUT.png [--grt RPT]   # die_case: plan blocks, case views by master, relays, clock repeaters
"""
import json, re, sys
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]


def kit(kd, out):
    f = json.loads((Path(kd) / 'floorplan.json').read_text())
    x0, y0, w, h = f['die']
    c = f['core']
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=2))
    ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fill=False, ls='--', color='gray'))
    for b in f.get('blocks', []):
        ax.add_patch(Rectangle((b['x'] - 5.4, b['y'] - 5.4), b['w'] + 10.8, b['h'] + 10.8, color='orange', alpha=0.25))
        ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], color='tab:orange'))
        ax.text(b['x'] + 2, b['y'] + b['h'] / 2, b['master'][:28], fontsize=7)
    for face, plist in f['pins'].items():
        n = len(plist)
        for i, p in enumerate(plist):
            t = (i + 0.5) / n
            xy = {'N': (t * w, h), 'S': (t * w, 0), 'W': (0, t * h), 'E': (w, t * h)}[face]
            col = 'red' if p == f.get('clock_port') else 'tab:blue'
            ax.plot(*xy, 's', color=col, ms=6 if col == 'red' else 3)
        ax.text(*{'N': (w / 2, h + 3), 'S': (w / 2, -8), 'W': (-30, h / 2), 'E': (w + 3, h / 2)}[face],
                f'{face}: ' + ','.join(plist)[:60] + ('...' if len(','.join(plist)) > 60 else ''), fontsize=6)
    ax.set_xlim(-35, w + 35); ax.set_ylim(-15, h + 15); ax.set_aspect('equal')
    ax.set_title(f"{f['name']} {w}x{h} um  ({f['why']})", fontsize=9)
    fig.savefig(out, dpi=110, bbox_inches='tight')


def die(cd, out, grt=None):
    cd = Path(cd)
    m = json.loads((cd / 'manifest.json').read_text())
    P = json.loads((ROOT / m['plan']).read_text())
    W, H = m['die_um']
    col = {'ot_hbm3e_phy_rc_e8p5': 'tab:gray', 'ot_hbm_svc_pc_ctrl_leaf': 'tab:red', 'ot_hbm_svc_sm_group': 'tab:orange',
           'ot_hbm_accel_smh_static': 'tab:blue', 'hfd_stn_v15_cc1182': 'tab:green'}
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for n, b in P.items():
        if isinstance(b, dict) and 'x' in b:
            ax.add_patch(Rectangle((b['x'], b['y']), b['w'], b['h'], fill=False, lw=0.3, color='k'))
            if b['w'] * b['h'] > 4e5:
                ax.text(b['x'] + 20, b['y'] + 20, n, fontsize=4, color='0.4')
    cnt = Counter()
    for l, v in m['placement'].items():
        ax.add_patch(Rectangle((v['x'], v['y']), v['w'], v['h'], color=col.get(v['m'], 'k'), alpha=0.55, lw=0))
        cnt[v['m']] += 1
    tcl = (cd / 'run.tcl').read_text()
    bx, by, sx, sy = [], [], [], []
    for mm in re.finditer(r'place_inst -name (dk([hs])_\S+) -location \{([\d.]+) ([\d.]+)\}', tcl):
        (bx if mm.group(2) == 'h' else sx).append(float(mm.group(3)))
        (by if mm.group(2) == 'h' else sy).append(float(mm.group(4)))
    ax.plot(bx, by, '.', ms=1.2, color='purple', label=f'hbm clock repeaters ({len(bx)})')
    ax.plot(sx, sy, '.', ms=1.2, color='cyan', label=f'stream clock repeaters ({len(sx)})')
    for k, c in col.items():
        ax.plot([], [], 's', color=c, label=f'{k} ({cnt[k]})')
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect('equal'); ax.legend(loc='upper right', fontsize=7)
    t = f"{cd.name}: {sum(cnt.values())} views, {m['signal_nets']} nets"
    if grt and Path(grt).exists():
        t += '  ' + ' '.join(re.findall(r'Total.*', Path(grt).read_text())[-1:])
    ax.set_title(t, fontsize=9)
    fig.savefig(out, dpi=120, bbox_inches='tight')


if __name__ == '__main__':
    if sys.argv[1] == 'kit':
        kit(sys.argv[2], sys.argv[3])
    else:
        die(sys.argv[2], sys.argv[3], sys.argv[5] if len(sys.argv) > 5 else None)
