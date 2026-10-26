#!/usr/bin/env python3
"""TYPE-REDUCE-2/HBM: old per-slot table (grey) vs new template (blue), strap pins red x, core frame.
    python3 render_templates.py OUT.png  (run from the repo root; reads groups.json next to this script)"""
import json, os, subprocess, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '../..'))
PD = os.path.join(ROOT, 'physical/die_plan/hbm_arch/B2n')
G = json.load(open(os.path.join(HERE, 'groups.json')))
pick = [k for k in G['groups'] if 'members' in G['groups'][k]]
pick = [k for k in pick if k.startswith(('score_hcol_h0', 'score_tail'))] + \
       [k for k in pick if k.startswith(('sfu_lane', 'pg_lane_exp'))][:4]
fig, axs = plt.subplots(2, 3, figsize=(18, 11)); axs = axs.flat
for ax, k in zip(axs, pick):
    g = G['groups'][k]; w, h = map(float, g['outline'].split('x'))
    new = json.load(open(os.path.join(PD, g['pins_file'])))
    for m in g['members'][:6]:
        old = json.loads(subprocess.check_output(['git', '-C', ROOT, 'show', f"{G['base']}:physical/die_plan/hbm_arch/B2n/{m['old_pins']}"]))
        ax.plot([p['x'] for p in old], [p['y'] for p in old], '.', ms=1, color='0.6')
    ax.plot([p['x'] for p in new if not p['name'].startswith('strap_')], [p['y'] for p in new if not p['name'].startswith('strap_')], '.', ms=1.5, color='tab:blue')
    s = [p for p in new if p['name'].startswith('strap_')]
    ax.plot([p['x'] for p in s], [p['y'] for p in s], 'x', ms=6, color='red')
    ax.add_patch(plt.Rectangle((0, 0), w, h, fill=False))
    ax.set_xlim(-10, w + 10); ax.set_ylim(-10, h + 10); ax.set_aspect('equal')
    mx = max(x['max'] for x in g['members'])
    ax.set_title(f"{k}\n{len(g['members'])} inst, {g['tables_before']} tables -> 1, max move {mx:g} um, straps {sorted(g['straps'])}", fontsize=7)
fig.tight_layout(); fig.savefig(sys.argv[1], dpi=110)
