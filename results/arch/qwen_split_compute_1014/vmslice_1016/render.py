#!/usr/bin/env python3
"""Readout PNG per variant: blocks (slices filled), every slice/VM-external data leg as an L-line (width ~ bits),
port-local rb legs green, cut lines > 0.60 (main cuts.py v3/M6 + C_B16 cluster) as red bars, numbers in the title."""
import json, sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/ubuntu/wt/q-vmslice-1016/results/arch/qwen_tp8_1012')
import cuts as C
def render(model, out, title, pref):
    d = json.load(open(model)); I = {i['n']: i for i in d['insts']}
    c = lambda n: (I[n]['x'] + I[n]['w'] / 2, I[n]['y'] + I[n]['h'] / 2)
    fig, ax = plt.subplots(figsize=(17, 12))
    for i in d['insts']:
        m = i['m']; slc = m.endswith('_model') or i['n'] in ('sp_vector_memory', 'sp_su64_sfu')
        if m.startswith(('qfd_rly', 'qkd_rly', 'qfd_rst_rep', 'qfd_xcst', 'qfd_tile')): 
            if m.startswith(('qfd_tile','qfd_xcst')): ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fill=False, ec='#cfd8dc', lw=0.2))
            continue
        fc = '#ffcc80' if 'vm' in i['n'] or i['n'] == 'sp_vector_memory' else '#b3e5fc' if i['n'].startswith(('su_', 'sp_su64')) else 'none'
        ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc=fc, ec='#455a64' if slc else '#90a4ae', lw=1.2 if slc else 0.5, alpha=0.9))
        if slc or i['w'] * i['h'] > 4e5 and not m.startswith('qfd_c_b16'):
            ax.text(i['x'] + i['w'] / 2, i['y'] + i['h'] / 2, i['n'].replace('sp_', ''), ha='center', va='center', fontsize=7)
    for b, cl, w, eps in d['buses']:
        if cl in ('clock_trunk', 'reset'): continue
        a = eps[0]
        for q in eps[1:]:
            if a not in I or q not in I: continue
            ends = (a, q)
            if not any(e.startswith(pref) for e in ends): continue
            local = b.startswith('b2_rb_')
            p0, p1 = c(a), c(q)
            col = '#2e7d32' if local else '#1565c0'
            ax.plot([p0[0], p1[0], p1[0]], [p0[1], p0[1], p1[1]], color=col, lw=max(0.6, w / 900), alpha=0.55)
    C.CLUSTER = tuple(C.CLUSTER) + ('qfd_c_b16',); C.CAP_MODE = 'v3'; C.CLUSTER_PLAN = 'M6'
    A = C.Net(model); fine = A.fine(top=60)
    for f in fine:
        if f['util'] <= 0.6: continue
        lo, hi = f['win']
        if f['ax'] == 'x': ax.plot([f['pos'], f['pos']], [lo, hi], color='red', lw=4, alpha=0.8)
        else: ax.plot([lo, hi], [f['pos'], f['pos']], color='red', lw=4, alpha=0.8)
        if f['util'] > 1.0: ax.text((f['pos'] if f['ax'] == 'x' else (lo + hi) / 2) + 150, ((lo + hi) / 2 if f['ax'] == 'x' else f['pos']) + 150, f"{f['util']:.2f}", color='red', fontsize=8)
    W = max(i['x'] + i['w'] for i in I.values()); H = max(i['y'] + i['h'] for i in I.values())
    ax.set_xlim(0, W + 50); ax.set_ylim(0, H + 50); ax.set_aspect('equal')
    ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(out, dpi=110); plt.close(fig)
if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2], sys.argv[3], tuple(sys.argv[4].split(',')))
