"""render_die.py REPO PLAN OUTPREFIX : whole-die reset render (partitions, die wavefront hops, every type's relay tree in
die frame; the six column types in colour with their chain drawn thick; hd_lep0N core rst_n pins + relay sites) plus
zoom crops of the west shims, east shims/turns and hd_lep0N."""
import json, sys
sys.path.insert(0, sys.argv[1] + '/tools/die_plan')
import schema as S, reset_tree as RT
sys.path.append('/home/ubuntu/.local/lib/python3.14/site-packages')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = S.Plan(json.load(open(sys.argv[2])), sys.argv[2]); pre = sys.argv[3]
COL = {'hd_spn_wshim_tx': '#d62728', 'hd_spn_wshim_rx': '#ff7f0e', 'hd_spn_eshim_tx': '#2ca02c',
       'hd_spn_eshim_rx': '#17becf', 'hd_turn_a': '#9467bd', 'hd_turn_b': '#e377c2'}
W = RT.wf_plan(P); sol = RT.wf_solve(P); OUTP = {}
trees = {}
for tn in W['types']:
    trees[tn] = RT.for_type(P, tn)
def draw(ax, lw_scale=1.0, labels=False):
    ax.add_patch(Rectangle((0, 0), P.W, P.H, fill=False, ec='k', lw=1))
    for p, pr in P.parts.items():
        tn = pr['type']; x0, y0, x1, y1 = P.part_box(p) if hasattr(P, 'part_box') else (*pr['origin_um'], pr['origin_um'][0]+P.types[tn]['outline_um'][0], pr['origin_um'][1]+P.types[tn]['outline_um'][1])
        c = COL.get(tn)
        ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=(c if c else '#f2f2f2'), alpha=0.18 if c else 1.0,
                               ec=(c if c else '#bbb'), lw=0.6*lw_scale))
        if labels and c:
            ax.text((x0+x1)/2, (y0+y1)/2, p, fontsize=4, ha='center', va='center', color=c)
        if tn == 'hd_lep0N':
            for hc in P.types[tn].get('hard_cores', []):
                if hc.get('module') != 'ot_s81hd_lep_pair': continue
                (ox, oy), (cw, ch) = hc['origin_um'], hc['outline_um']
                a = P.to_die(p, (ox, oy)); b = P.to_die(p, (ox+cw, oy+ch))
                ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0]-a[0]), abs(b[1]-a[1]), fc='#ccc', ec='#888', lw=0.4))
    for p, pr in P.parts.items():
        tn = pr['type']
        if tn not in trees: continue
        T = trees[tn]; c = COL.get(tn)
        xy = {r['q']: r['xy'] for r in T['relays']}; xy['rst_root_n'] = T['root']
        for r in T['relays']:
            if r['d'] not in xy: continue
            a = P.to_die(p, xy[r['d']]); b = P.to_die(p, r['xy'])
            ax.plot([a[0], b[0]], [a[1], b[1]], '-', color=c or '#999', lw=(1.2 if c else 0.25)*lw_scale, zorder=3 if c else 2)
        if c:
            pts = [P.to_die(p, r['xy']) for r in T['relays']]
            ax.scatter([q[0] for q in pts], [q[1] for q in pts], s=4*lw_scale, color=c, zorder=4)
            e = P.to_die(p, T['root']); ax.plot(*e, 's', color='k', ms=3*lw_scale, zorder=5)
        for cr in T.get('core_resets', []):
            a = P.to_die(p, cr['pin_um']); b = P.to_die(p, cr['xy'])
            ax.plot([a[0], b[0]], [a[1], b[1]], '-', color='#000', lw=1.5*lw_scale, zorder=6)
            ax.plot(*a, 'x', color='#000', ms=4*lw_scale, zorder=6)
    for p, pr in sol['parent'].items():
        if pr is None: continue
        q = pr[0]; tq = P.parts[q]['type']; k = sol['outs'][tq].index(pr[1])
        op = OUTP.setdefault(tq, RT.out_pins(P, tq)); o = P.to_die(q, op[k][1:]) if k < len(op) else None
        tn = P.parts[p]['type']
        if tn not in W['types'] or o is None: continue
        i = P.to_die(p, W['types'][tn]['in_um'])
        ax.annotate('', xy=i, xytext=o, arrowprops=dict(arrowstyle='->', color='#0000cc', lw=0.7*lw_scale), zorder=7)
fig, ax = plt.subplots(figsize=(24, 24*P.H/P.W)); draw(ax)
ax.set_aspect('equal'); ax.set_xlim(-50, P.W+50); ax.set_ylim(-50, P.H+50)
ax.set_title(f"{sys.argv[2].split('/')[-1]}: die reset wavefront (blue arrows = parent rst_o -> child IN), relay trees (grey), "
             f"COLUMN types in colour (wshim_tx red, wshim_rx orange, eshim_tx green, eshim_rx cyan, turn_a purple, turn_b pink; "
             f"black square = entry), lep pair rst_n pin->relay (black x/line). max release {W['max_release']}, unreachable {len(W['unreachable'])}", fontsize=9)
fig.savefig(pre + '_die.png', dpi=110, bbox_inches='tight'); plt.close(fig)
# zooms: bounding boxes of column-type instances (west / east) and lep0N
def bb(pred):
    xs, ys = [], []
    for p, pr in P.parts.items():
        if pred(p, pr['type']):
            x0, y0 = pr['origin_um']; w, h = P.types[pr['type']]['outline_um']; xs += [x0, x0+w]; ys += [y0, y0+h]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None
zooms = {'west': bb(lambda p, t: t in ('hd_spn_wshim_tx', 'hd_spn_wshim_rx')),
         'east': bb(lambda p, t: t in ('hd_spn_eshim_tx', 'hd_spn_eshim_rx')),
         'turns': bb(lambda p, t: t in ('hd_turn_a', 'hd_turn_b')),
         'lep0N': bb(lambda p, t: t == 'hd_lep0N')}
for nm, b in zooms.items():
    if not b: continue
    x0, y0, x1, y1 = b; m = 300
    fig, ax = plt.subplots(figsize=(16, 16*max(y1-y0+2*m, 1)/max(x1-x0+2*m, 1)))
    draw(ax, 2.0, labels=True); ax.set_aspect('equal'); ax.set_xlim(x0-m, x1+m); ax.set_ylim(y0-m, y1+m)
    ax.set_title(f'{nm} zoom ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})', fontsize=9)
    fig.savefig(f'{pre}_{nm}.png', dpi=100, bbox_inches='tight'); plt.close(fig)
print('RENDER_DONE', pre)
