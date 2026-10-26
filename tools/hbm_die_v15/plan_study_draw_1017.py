#!/usr/bin/env python3
"""H-PLANSTUDY (10-17): draw the three HBM die plans (a) d4f, (b) per-quadrant, (c) 8-SM at the same scale.
Blocks coloured by function; plan-graph links drawn as L-routes, width ~ bits; cross-quadrant classes in red.

    python3 tools/hbm_die_v15/plan_study_draw_1017.py results/arch/hbm_plan_study_1017
"""
import json, re, sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

KIND = [('sm_', '#9ecae1', 'SM'), ('xq_', '#c6dbef', 'SM pair store'), ('pc_', '#fdd0a2', 'PC'), ('phy_', '#fdae6b', 'HBM PHY'),
        ('vmb_', '#a1d99b', 'VM bank'), ('vmh_', '#31a354', 'VM hub'), ('dbk_', '#74c476', 'DMA back'),
        ('su_', '#dadaeb', 'SU slice'), ('sucore_', '#756bb1', 'SU core'), ('sucx_', '#756bb1', None), ('sfu_', '#fcbba1', 'SFU group'),
        ('sfucore_', '#fb6a4a', 'SFU core'), ('sfus_', '#ef3b2c', 'SFU store'), ('hc_eng', '#8c6d31', 'HC engine'), ('hce_', '#8c6d31', None),
        ('hc_', '#e7cb94', 'HC'), ('coll_', '#636363', 'COLL'), ('cij_', '#636363', None), ('ep_', '#bdbdbd', 'SerDes ep/lk'), ('lk_', '#969696', None),
        ('idx', '#e377c2', 'IDX'), ('tkm', '#f7b6d2', 'top-k merge'), ('quant', '#bcbddc', None), ('host', '#ffff99', 'host'),
        ('pleaf', '#ffff99', None)]
XCLS = {'VM_RING', 'COLL_RING', 'COLL_EP', 'EP_SERDES', 'HC_ENG'}
FAM = {'SM_X': '#3182bd', 'SM_OUT': '#3182bd', 'KV_DESC': '#3182bd', 'SM_HBM': '#e6550d', 'HBM_K': '#e6550d',
       'HBM_VM': '#e6550d', 'VM_HBM': '#e6550d'}


def colour(n):
    for p, c, _ in KIND:
        if n.startswith(p):
            return c
    return '#eeeeee'


def quadrant_of(n):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import plan_study_1017 as PS
    return PS.inst_quadrant(n)


def draw(ax, P, G, W, H, title, quads=None):
    for n, r in P.items():
        ax.add_patch(Rectangle((r['x'] / 1000, r['y'] / 1000), r['w'] / 1000, r['h'] / 1000, fc=colour(n), ec='#555555', lw=0.3))
        if r['w'] * r['h'] > 2.5e6 or n.startswith(('tkm', 'coll_', 'vmh_', 'hce_', 'idxs_', 'sucore_')):
            ax.text((r['x'] + r['w'] / 2) / 1000, (r['y'] + r['h'] / 2) / 1000, re.sub(r'^(su|sm)_', r'\1', n), fontsize=3.2,
                    ha='center', va='center')
    for l in G['links']:
        if l['src'] not in P or l['dst'] not in P:
            continue
        a, b = P[l['src']], P[l['dst']]
        x0, y0 = (a['x'] + a['w'] / 2) / 1000, (a['y'] + a['h'] / 2) / 1000
        x1, y1 = (b['x'] + b['w'] / 2) / 1000, (b['y'] + b['h'] / 2) / 1000
        c = l['cls']
        cross = c in XCLS
        col = '#d62728' if cross else FAM.get(c, '#2ca02c')
        lw = max(0.15, min(2.2, l['bits'] / 1500))
        ax.plot([x0, x1, x1], [y0, y0, y1], color=col, lw=lw, alpha=0.55 if cross else 0.25, solid_capstyle='butt')
    if quads:
        for q, (x, y, w, h) in quads.items():
            ax.add_patch(Rectangle((x / 1000, y / 1000), w / 1000, h / 1000, fill=False, ec='#d62728', lw=0.8, ls='--'))
            ax.text(x / 1000 + 0.3, y / 1000 + h / 1000 - 0.6, f'quadrant {q}', fontsize=5, color='#d62728')
    ax.add_patch(Rectangle((0, 0), W / 1000, H / 1000, fill=False, ec='k', lw=1.0))
    ax.set_xlim(-0.5, 23.5); ax.set_ylim(-0.5, 33.0); ax.set_aspect('equal')
    ax.set_title(title, fontsize=6.5)
    ax.tick_params(labelsize=5); ax.set_xlabel('mm', fontsize=5)


def quad_boxes(P, W, keep):
    out = {}
    for q in keep:
        xs = [r for n, r in P.items() if quadrant_of(n) == q and not n.startswith(('phy_', 'pc_', 'lk_', 'ep_'))]
        xs = [r for n, r in P.items() if quadrant_of(n) == q and not n.startswith(('phy_', 'pc_', 'lk_', 'ep_', 'idxs_', 'pleaf_'))]
        x0 = min(r['x'] for r in xs); y0 = min(r['y'] for r in xs)
        x1 = max(r['x'] + r['w'] for r in xs); y1 = max(r['y'] + r['h'] for r in xs)
        out[q] = (x0 - 40, y0 - 40, x1 - x0 + 80, y1 - y0 + 80)
    return out


def main():
    d = Path(sys.argv[1])
    S = json.loads((d / 'plans.json').read_text())
    pr = json.loads((d / 'price.json').read_text()) if (d / 'price.json').exists() else None
    spec = [('a', 'plan_a', '(a) d4f as is (run9 lanes)', None),
            ('b_inner', 'plan_b_inner', '(b) d4f, per-quadrant services', ('SW', 'SE', 'NW', 'NE')),
            ('c_inner', 'plan_c_inner', '(c) 8 SM / 1 stack / 2 quadrants', ('SW', 'SE'))]
    fig, axs = plt.subplots(1, 3, figsize=(15, 8.2), dpi=220)
    for ax, (k, sub, name, quads) in zip(axs, spec):
        P = json.loads((d / sub / 'compact.P.json').read_text()); G = json.loads((d / sub / 'compact.graph.json').read_text())
        W, H = json.loads((d / sub / 'compact.metrics.json').read_text())['die_um']
        e = S[k]['plan']; b = S[k]['bus']
        cut = e['cut_phy_unmasked']
        dep = b['equal_age_depth']
        t = (f"{name}\n{W / 1000:.2f} x {H / 1000:.2f} mm = {W * H / 1e6:.0f} mm2; cut {max(cut['worst_v']['ratio'], cut['worst_h']['ratio']):.2f}; "
             f"graph bit-mm {e['sum_bits_mm'] / 1e6:.2f} M\nrelay tiles ~{b['relay_tiles_calibrated'] / 1000:.1f} k; longest {b['longest'][0] / 1000:.1f} mm / {b['longest'][2]} st; "
             f"depth str/hbm/ser {dep.get('stream')}/{dep.get('hbm')}/{dep.get('serial')}")
        draw(ax, P, G, W, H, t, quad_boxes(P, W, quads) if quads else None)
        fig2, ax2 = plt.subplots(figsize=(6, 8.4), dpi=260)
        draw(ax2, P, G, W, H, t, quad_boxes(P, W, quads) if quads else None)
        fig2.tight_layout(); fig2.savefig(d / f'plan_{k.split("_")[0]}.png'); plt.close(fig2)
    handles = [Rectangle((0, 0), 1, 1, fc=c, ec='#555555', lw=0.3, label=lab) for _, c, lab in KIND if lab]
    fig.legend(handles=handles, loc='lower center', ncol=11, fontsize=6, frameon=False)
    fig.suptitle('H-PLANSTUDY 10-17: HBM die plans at the same scale (lines = plan-graph links; red = cross-quadrant classes '
                 'VM/COLL ring, COLL->SerDes, HC engine; blue = SM x/out; orange = HBM)', fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97)); fig.savefig(d / 'plans_abc.png')
    print('wrote', d / 'plans_abc.png')


if __name__ == '__main__':
    main()
