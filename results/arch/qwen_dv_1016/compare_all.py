#!/usr/bin/env python3
"""Side-by-side montage of Q-DV plans at ONE scale and ONE colour key; metrics from metr.py (same as the records).
    compare_all.py OUT.png name=model.json ...   (metrics json lines from metr.py via env QDV_METRICS)"""
import json, sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, '/home/ubuntu/scratch/qdv-1016'); import metr
COL = {'dv_reduce': '#d62728', 'dv_lane': '#ff7f0e', 'dv_gather': '#2ca02c', 'dv_ring': '#9467bd', 'dv_coll': '#8c564b',
       'dv_d2d': '#e377c2', 'head_chain': '#1f77b4', 'tree_spine': '#17becf', 'spine_local': '#7f7f7f', 'coll_fdi': '#bcbd22'}
FILL = {'qfd_c_b16': '#eef5ee', 'qfd_dv_slice': '#fde0c5', 'qfd_dv_slice2': '#fde0c5', 'qfd_dv_redstn': '#f4a6a6',
        'qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3': '#f8c9c9', 'qfd_sp_su64_sfu': '#f8c9c9', 'qfd_port_half_b2': '#f6dfb0'}
out = sys.argv[1]; M = [a.split('=', 1) for a in sys.argv[2:]]
W = H = 0
for _, f in M:
    I = json.load(open(f))['insts']; W = max(W, max(i['x'] + i['w'] for i in I)); H = max(H, max(i['y'] + i['h'] for i in I))
fig, axs = plt.subplots(1, len(M), figsize=(7.2 * len(M), 7.2 * H / W + 1.6))
for ax, (name, f) in zip(axs, M):
    d = json.load(open(f)); I = {i['n']: i for i in d['insts']}
    r = metr.st(f, 405.0); r200 = metr.st(f, 200.0); r.update(metr.cutm(f))
    cen = lambda i: (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)
    cl = lambda i, P: (min(max(P[0], i['x']), i['x'] + i['w']), min(max(P[1], i['y']), i['y'] + i['h']))
    for i in d['insts']:
        ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc=FILL.get(i['m'], '#e8e8f4'), ec='#666', lw=.3))
    for b, c, bits, eps in d['buses']:
        if c not in COL: continue
        p = [I[e] for e in eps if e in I]
        for a, q in (zip(p, p[1:]) if len(p) == 2 else [(p[0], t) for t in p[1:]]):
            A, Q = cl(a, cen(q)), cl(q, cen(a)); ax.plot([A[0], Q[0]], [A[1], Q[1]], color=COL[c], lw=max(.3, bits / 900), alpha=.75)
    ax.set_xlim(0, W + 50); ax.set_ylim(0, H + 50); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    lh = r['longest_hop']
    ax.set_title(f"{name}\ncut {r['worst_cut']}  |  stages@405 {r['stages405']:,}  @200 {r200['stages200']:,}\n"
                 f"bit-mm {r['bitmm'] / 1e6:.3f} M  |  {r['mm2']} mm2  |  longest {lh[0] / 1000:.1f} mm ({lh[1]})", fontsize=9)
for c, col in COL.items(): axs[0].plot([], [], color=col, lw=3, label=c)
axs[0].legend(loc='lower left', fontsize=6, ncol=2)
fig.suptitle('Qwen compute die: central reference q3h vs Q-DV distributed-vector plans (relay-skip planning models, same scale and colours)', fontsize=12)
fig.savefig(out, dpi=80, bbox_inches='tight'); print(out)
