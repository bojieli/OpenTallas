#!/usr/bin/env python3
import json, copy, glob, sys, importlib.util
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import hops as H, optimize as O
R = '/home/ubuntu/scratch/s81-p8/resite'
spec = importlib.util.spec_from_file_location('gen', f'{R}/gen.py'); gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)
d = json.load(open(f'{R}/orig.json'))
dp = json.load(open('/home/ubuntu/wt/s81-p6-1023/physical/die_plan/s81/die_plan.json'))['partition_types']
opt = {}
for f in glob.glob(f'{R}/opt_*.json'):
    opt.update(json.load(open(f)))
cand = copy.deepcopy(d)
cand['sources'] = {k: v + ' ; S81-P8-C re-site proposal (tools in scratch/s81-p8/resite/tools)' for k, v in d['sources'].items()}
rep = []
P = rep.append
P('S81-P8-C frame-band macro re-site PROPOSAL (2026-10-23)  -- no P&R run; model estimates')
P('Model: connectivity from the plan RTL rtl/dsrom_sys/s81_dv/frame_lp/plan/col_<M>_l4_lp_plan.sv (bit-level, assigns +')
P('  seam_w_pl/pad N=0 merged as wires; reset forest / lprc pads / ck/rs/rsi excluded), macro pins from the view LEFs')
P('  (bf_col via the dsfd_bf_col_kit pin map), port bits at their die_plan window position (lsb_low, boundary flop on the face).')
P('  Soft register nodes (u_y_* relays, lpl_*_r seams, pads N>=1) sit at the L1-minimax centre of their terminals')
P('  (= midpoint of source and sink for a 2-terminal relay), pushed out of macro boxes; hop = max Manhattan pin-to-pin over the')
P('  bits of an instance pair.  r0 bands are scored against EVERY r0 plan type (p1..p6 windows differ); worst type reported.')
P('  Fixed: ROMs, q elements (qxpq), bf_col views, bf_front_roots.  Movable: qbank N/S, cfg7(_bfp), sstn base/payload,')
P('  nodes, rstg, cfifo, xo stations.  Legal: 8.64 lattice, >= 8.64 from outline, no overlap, facing gaps >= 13.8,')
P('  not on the 30-um boundary-flop strip of any bus/ft window.')
P('Validation (h9_r1 current sites): model reproduces the measured placed >750 macro hops: bs7->e7 1055 (meas 1055), s5->bs5 916 (916),')
P('  s6->t3 972 (972), rg0->o1 1212 (1206), n13->o1 1195 (1191), c8_0->s8 767 (767), e7->bn7 753 (753). Soft relay hops come out')
P('  shorter than measured (GPL stacked them, e.g. xa_4_0->bs6 meas 928, model 640) - the relay-midpoint assumption.')
P('')
for M in ('col_h9', 'col_h10'):
    for k in range(3):
        b = f'{M}_r{k}'; v = opt[b]
        lst = cand['masters'][M][f'r{k}']
        moved = []
        for e in lst:
            n = e['inst'].split('.', 1)[1].replace('.u_view', '')
            new = v['after_sites'][n]
            if abs(new[0] - e['origin_um'][0]) > 1e-6 or abs(new[1] - e['origin_um'][1]) > 1e-6:
                moved.append((e['inst'], e['module'], tuple(e['origin_um']), tuple(new)))
                e['origin_um'] = [round(new[0], 4), round(new[1], 4)]
        errs = gen.check(lst, b) + gen.gap_check(lst, b)
        lat = [e['inst'] for e in lst if any(abs(c / 8.64 - round(c / 8.64)) > 1e-6 for c in e['origin_um'])]
        ex_after = [e for e in v['after'] if e['excl']]
        ne_after = [e for e in v['after'] if not e['excl']]
        P(f'== {b}  ({", ".join(v["ptypes"])})')
        P(f'  max hop before {v["before_max"]:.0f} um -> after {ne_after[0]["hop"] if ne_after else 0:.0f} um (excluding stage-bound x-bus hops)'
          + (f'; stage-bound x hops before {max(e["hop"] for e in v["before"] if any(x.startswith("u_xo") for x in (e["a"], e["b"]))):.0f} after {ex_after[0]["hop"]:.0f}' if ex_after else ''))
        P(f'  total bit-distance {v["before_bitdist"]:.3g} -> {v["after_bitdist"]:.3g} bit-um;  moved macros: {len(moved)};  legality errors: {len(errs)} {errs[:3]}; off-lattice: {len(lat)}')
        for inst, mod, o, n in moved:
            P(f'    {inst:24s} {mod:26s} ({o[0]:7.2f},{o[1]:7.2f}) -> ({n[0]:7.2f},{n[1]:7.2f})')
        bef = {}
        for e in v['before']:
            key = (e['a'], e['b'])
            if e['hop'] > 750 and key not in bef:
                bef[key] = e
        P(f'  before: {len(bef)} instance pairs > 750 um (worst plan type):')
        for e in list(bef.values())[:14]:
            P(f'    {e["hop"]:6.0f} {e["bits"]:5d} b  {e["a"]}.{",".join(e["la"][:2])} -> {e["b"]}.{",".join(e["lb"][:2])}  [{e["ptype"]}]')
        rem = {}
        for e in v['after']:
            key = (e['a'], e['b'])
            if e['hop'] > 750 and key not in rem:
                rem[key] = e
        P(f'  after: {len(rem)} instance pairs still > 750 um -> need an RTL stage:')
        for e in rem.values():
            P(f'    {e["hop"]:6.0f} {e["bits"]:5d} b  {e["a"]}.{",".join(e["la"][:2])} -> {e["b"]}.{",".join(e["lb"][:2])}  [{e["ptype"]}]' + ('  (stage-bound)' if e['excl'] else ''))
        P('')
        # PNG: old vs new, arrows for > 600 connections after
        models = [H.Model(M, k, lst, dp[p]) for p in v['ptypes'][:1]]
        m = models[0]; m.solve()
        fig, axs = plt.subplots(1, 2, figsize=(20, 9))
        old_sites = {e['inst'].split('.', 1)[1].replace('.u_view', ''): tuple(e['origin_um']) for e in d['masters'][M][f'r{k}']}
        movedn = {x[0].split('.', 1)[1].replace('.u_view', '') for x in moved}
        for ax, which in ((axs[0], 'before'), (axs[1], 'after')):
            if which == 'before':
                m.site = dict(old_sites); m.spos = {}; m.solve()
            else:
                m.site = {kk: tuple(vv) for kk, vv in v['after_sites'].items()}; m.spos = {}; m.solve()
            ax.add_patch(Rectangle((0, 0), *gen.OUTLINE, fill=False, lw=2))
            pt = dp[v['ptypes'][0]]
            for bb in pt['buses']:
                w0, w1 = bb['window_um']; f = bb['face']
                xy = {'N': ((w0, 1226.88), (w1, 1226.88)), 'S': ((w0, 0), (w1, 0)), 'E': ((1442.88, w0), (1442.88, w1)), 'W': ((0, w0), (0, w1))}[f]
                ax.plot([xy[0][0], xy[1][0]], [xy[0][1], xy[1][1]], lw=6, color='#2ca02c' if bb['dir'] == 'in' else '#d62728', alpha=0.6)
            for n, s in m.site.items():
                e = m.macros[n]
                col = {'ot_rom_4096x72_m8': '#8172b3', 'ot_v41_rom_elem_q_qxpq_w10': '#4c72b0', 'ot_v41_bf_col': '#dd8452', 'dsfd_bf_front_roots': '#c44e52'}.get(e['module'], '#55a868')
                ec = 'red' if n in movedn else 'k'
                ax.add_patch(Rectangle(s, *e['size_um'], fc=col, ec=ec, lw=1.2 if n in movedn else 0.3, alpha=0.75))
                if e['module'] != 'ot_rom_4096x72_m8':
                    ax.text(s[0] + 1, s[1] + 1, n[2:], fontsize=5)
            for a, t_, gr in m.hops():
                if a > 600:
                    pa = m.base(gr['a']) + gr['ao'].mean(0); pb = m.base(gr['b']) + gr['bo'].mean(0)
                    c = 'red' if a > 750 else 'orange'
                    ax.annotate('', xy=pb, xytext=pa, arrowprops=dict(arrowstyle='->', color=c, lw=0.6 + 1.5 * min(gr['bits'], 600) / 600))
            for n, (x, y) in m.spos.items():
                ax.plot(x, y, '.', ms=2, color='gray')
            mx = max(a for a, *_ in m.hops())
            ax.set_xlim(-20, gen.OUTLINE[0] + 20); ax.set_ylim(-20, gen.OUTLINE[1] + 20); ax.set_aspect('equal')
            ax.set_title(f'{b} {which} [{v["ptypes"][0]}]: max hop {mx:.0f} um; arrows >600 (red >750); red-edged = moved; gray dots = modelled soft relays', fontsize=8)
        fig.savefig(f'{R}/{b}_resite.png', dpi=110, bbox_inches='tight'); plt.close(fig)
cand['errors'] = []
for M, bands in cand['masters'].items():
    for kb, lst in bands.items():
        cand['errors'] += gen.check(lst, f'{M}_{kb}') + gen.gap_check(lst, f'{M}_{kb}')
P(f'candidate legality (frame_band_macros.py check + gap_check, all bands): {len(cand["errors"])} errors')
json.dump(cand, open(f'{R}/resite_candidate.json', 'w'), indent=1)
open(f'{R}/resite_report.txt', 'w').write('\n'.join(rep) + '\n')
print('\n'.join(rep))
