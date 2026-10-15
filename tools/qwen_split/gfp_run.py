#!/usr/bin/env python3
"""GLOBAL-FP-Q driver: build / collect every candidate, score with the one objective, write links.json per candidate,
the comparison JSON and same-scale figures.

usage: gfp_run.py OUT_DIR [--sa PKL ...] [--rtlmp DIR]
"""
import argparse, copy, json, math, pickle, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gfp_core as C  # noqa: E402
import gfp_candidates as G  # noqa: E402
import gfp_search as S  # noqa: E402

GROUP_COLOR = dict(tile='#d9d9d9', station='#9ecae1', head_column='#74c476', io_band='#bcbddc', kv_link='#fdae6b',
                   band_port='#fb6a4a', hub='#6baed6')
UNKNOWNS = [
    'words per transfer for every class (traffic = bits x activations/token is a lower bound)',
    'clock phi-R per moved instance / per MY tile; clock-trunk and reset re-derivation',
    'real cut <= 0.60 per channel (coarse 250-um L-route estimate only), halos, PDN, pin access',
    'port tiles internal latency and pass-through pin plan (Q-COMPUTE-ELEM r13 blocker) unchanged in all candidates',
    'compiler/ROM-image regeneration for the logical block remap (no RTL change; tile_id straps move with the map)',
]


def pmhs(base, die):
    from pair_mirror import build, interleave
    m, geom = build(base, keep_rows=(7, 8))
    return m, geom


class PinSwap:
    """Temporarily apply the PM-H-S interleaved tree-word pin plan to the tile master."""
    def __init__(self, die): self.tp = die.g.pins['qfd_tile_nk']
    def __enter__(self):
        from pair_mirror import interleave
        self.keep = {p: self.tp[p].copy() for p in ('n_a', 'n_b', 'n_y', 't_out')}; interleave(self.tp)
    def __exit__(self, *a):
        for p, v in self.keep.items(): self.tp[p][:] = v


def figure(die, cands, path, top=8):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection
    n = len(cands); cols = min(3, n); rows = math.ceil(n / cols)
    W, H = die.die['w'], die.die['h']
    fig, axes = plt.subplots(rows, cols, figsize=(6.4 * cols, 5.6 * rows), squeeze=False)
    for ax in axes.ravel(): ax.axis('off')
    for ax, c in zip(axes.ravel(), cands):
        m, ev, r = c['model'], c['ev'], c['metrics']; die = c.get('die', die)
        ax.axis('on')
        ax.add_patch(Rectangle((0, 0), W, H, fc='white', ec='black', lw=1.0))
        for i in m.values():
            g = C.group_of(i['n'], i['m'])
            ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc=GROUP_COLOR[g], ec='none' if g in ('tile', 'station') else '#333', lw=.3))
        segs, ws, cs = [], [], []
        scored = []
        for k, rec in enumerate(die.recs):
            hp, L, cen = ev[k][0], ev[k][1], ev[k][2]
            st = C.stages(L)
            col = '#1a9850' if st == 1 else '#fdae61' if st <= 5 else '#f46d43' if st <= 20 else '#a50026'
            for j in range(1, len(cen)):
                segs.append([cen[0], cen[j]]); ws.append(0.15 + 1.6 * math.log2(1 + rec['n']) / 12); cs.append(col)
            scored.append((rec['n'] * L, rec['b'], cen, st))
        ax.add_collection(LineCollection(segs, linewidths=ws, colors=cs, alpha=.75))
        for _, name, cen, st in sorted(scored, key=lambda t: -t[0])[:top]:
            mid = (cen[0] + cen[-1]) / 2
            ax.annotate(f'{name} {st}st', mid, fontsize=5, color='#222', ha='center',
                        bbox=dict(boxstyle='round,pad=0.1', fc='white', ec='none', alpha=.7))
        ax.set_xlim(-300, W + 300); ax.set_ylim(-300, H + 300); ax.set_aspect('equal')
        ax.set_title(f"{c['name']}\nME loop {r['me_loop']} st (bd {r['bd']} + red {r['red']} + {r['vm_to_tap']})  |  "
                     f"{r['bit_um'] / 1e9:.3f} G bit-um  |  relays {r['relay_flops'] / 1e6:.2f} M\n"
                     f"exposed {r['exposed_stage_cycles_per_token']:,} stage-cyc/token  |  cut~{r['congestion']['worst_cut']}", fontsize=7)
        ax.tick_params(labelsize=5)
    handles = [plt.Line2D([], [], color=c_, lw=2, label=l) for c_, l in
               (('#1a9850', '<= 490 um (1 stage)'), ('#fdae61', '2-5 stages'), ('#f46d43', '6-20 stages'), ('#a50026', '> 20 stages'))]
    handles += [Rectangle((0, 0), 1, 1, fc=v, label=k) for k, v in GROUP_COLOR.items()]
    fig.legend(handles=handles, loc='lower center', ncol=11, fontsize=6, frameon=False)
    fig.suptitle('Qwen compute die, all candidates at the same scale (die 32.41 x 25.94 mm). Lines join per-bus pin centroids; '
                 'width ~ log2(bits); colour = stages at 490-um reach. Assignment-pin geometry, no route.', fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(path.with_suffix('.png'), dpi=150); fig.savefig(path.with_suffix('.svg')); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('out', type=Path); ap.add_argument('--sa', nargs='*', default=[])
    ap.add_argument('--rtlmp', type=Path); ap.add_argument('--rtlmp-coarse', type=Path); ap.add_argument('--swap-iters', type=int, default=0)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True); (a.out / 'links').mkdir(exist_ok=True)
    die = C.Die(); C.attach_ports(die); base = die.base
    B = G.Blocks(die); FR = S.FastReduction(die, B)
    cands = []

    def add(name, desc, model, P=None, pins=None, info=None, cost=None, view=None):
        die_ = view or die
        if pins:
            with PinSwap(die):
                r, ev = C.score(die_, model, P, name)
                lj = C.links_json(die_, model, ev, name, r, P, UNKNOWNS)
        else:
            r, ev = C.score(die_, model, P, name)
            lj = C.links_json(die_, model, ev, name, r, P, UNKNOWNS)
        ovl = G.overlaps(model); outs = G.outside(model, die_.die)
        r.update(rectangle_errors=len(ovl) + len(outs), description=desc, geometry=info or {}, cost=cost or {})
        lj['metrics'] = {k: v for k, v in r.items() if k != 'long_links'}
        (a.out / 'links' / f'{name}.links.json').write_text(json.dumps(lj, separators=(',', ':')))
        rec = C.dataflow_record(die_, model, ev, f'qwen_gfp_{name}', f'GLOBAL-FP-Q {name}', P, note=desc)
        (a.out / 'explorer').mkdir(exist_ok=True)
        (a.out / 'explorer' / f'qwen_gfp_{name}.json').write_text(json.dumps(rec, separators=(',', ':')))
        cands.append(dict(name=name, model=model, ev=ev, metrics=r, die=die_))
        print(name, {k: r[k] for k in ('me_loop', 'bd', 'red', 'bit_um', 'relay_flops', 'exposed_stage_cycles_per_token', 'rectangle_errors')}, r['congestion']['worst_cut'], flush=True)

    def fast_P(model):
        ds = G.downstream_stages(die, model); P, *_ = FR.assign(model, ds); return P

    add('wide27', 'Current reference: wide27 + Band0/1 MX + adopted x3_mux MY / xs_tap MX (pin graph f6842ce4a)', base,
        cost=dict(cycles='reference', area='reference'))
    m_pm, g_pm = pmhs(base, die)
    add('pmhs', 'PM-H-S + interleaved tree words (GEO-Q / compute lead; blocked at C19 by xcst MY track phase)', m_pm, pins=True, info=g_pm,
        cost=dict(note='needs MY-legal station variant (two pins re-route of closed xcst_s/n)'))
    add('wide27_remap', 'wide27 geometry + logical block->slot remap and in-block symmetry (ROM image / compiler map only)', base, fast_P(base),
        cost=dict(hardware='none', compiler='block->slot map + tile_id straps'))
    if a.rtlmp and (a.rtlmp / 'placed.def').exists():
        import gfp_rtlmp as R
        m_r = R.read_back(die, a.rtlmp)
        add('rtlmp', 'OpenROAD rtl_macro_placer (Hier-RTLMP), nets = width x traffic, IO band + KV PHY fixed', m_r,
            cost=dict(note='raw RTL-MP output; rectangle errors / field grid not enforced by the tool'))
        add('rtlmp_remap', 'RTL-MP placement + logical block remap', m_r, fast_P(m_r))
    if a.rtlmp_coarse and (a.rtlmp_coarse / 'placed.def').exists():
        import gfp_rtlmp_coarse as RC
        m_c = RC.read_back(die, a.rtlmp_coarse)
        add('rtlmp_cluster', 'OpenROAD rtl_macro_placer (Hier-RTLMP) on 89 clusters (36 rigid field macros = 12 block columns x '
            '3 row bands, hub/band/KV instances free, IO band + KV PHY fixed), nets = width x traffic; + logical block remap',
            m_c, fast_P(m_c), cost=dict(note='raw tool output, no legaliser beyond RTL-MP; field macros keep tile pitch internally'))
    for stacked in (True, False):
        v_t, m_t, info_t = G.tri_spine(die, base, band_y=9000.0, stacked=stacked)
        ds_t = G.downstream_stages(v_t, m_t); P_t, *_ = FR.assign(m_t, ds_t)
        add('arch_trispine' + ('' if stacked else '_rigid'),
            'Architect T3: one port spine per band (band0 in a W-field gap at tile column 8, band1 under the VM, band2 in an '
            'E-field gap at column 40) so every block result stays inside its band; ' +
            ('band groups re-stacked 1 port wide (die +2.8 mm2)' if stacked else 'band groups rigid (die +56.9 mm2, OVER the 858 mm2 budget)'),
            m_t, P_t, info=info_t, cost=dict(die_delta_mm2=info_t['die_delta_mm2']), view=v_t)
    ws = 4924.8
    m_ns, info_ns = G.hub_layout(base, ws, G.plan_cluster(base, ws))
    P_ns = fast_P(m_ns)
    add('arch_htree', 'Architect: hub = H-tree root at the field centroid. Narrow spine 4.92 mm (VM width + 2 channels), band '
        'port groups stacked on the VM/SU axis (band1 under VM, band0 under band1, band2 over SU, res_ser facing the VM), '
        'activation root unchanged on the head row, IO band on the S edge, KV PHY N edge, + logical block remap',
        m_ns, P_ns, info=info_ns, cost=dict(area_mm2=0.0, die_shrink_option_mm2=info_ns['die_shrink_mm2'], hardware='hub groups re-homed; no new masters'))
    v_sh, m_sh, note_sh = G.split_head(die, m_ns)
    add('arch_splithead', 'arch_htree + head chain fed at the middle of each half (root forks to h_11/h_12 and h_35/h_36; '
        'inner quarters re-mastered xcol_e/xcol_w): tests whether the 24-hop registered head chain, not geometry, sets bd',
        m_sh, P_ns, info=info_ns, cost=note_sh, view=v_sh)
    if a.swap_iters:
        P_sw, _ = S.tile_swap_refine(die, m_ns, dict(P_ns), iters=a.swap_iters, log=lambda *_: None)
        add('arch_htree_tileswap', 'arch_htree + tile-level annealing of the logical map (free block shapes, objective '
            'sum path^4 + bit-um/1e7)', m_ns, P_sw, info=info_ns, cost=dict(note='trades bit-um/relays for ME-loop stages'))
    m_np, g_np = pmhs(m_ns, die)
    add('arch_htree_pmhs', 'arch_htree + PM-H-S pair-mirrored columns with interleaved tree words', m_np, fast_P(m_np), pins=True,
        info=dict(info_ns, **g_np), cost=dict(note='inherits the PM-H-S station MY blocker'))
    for p in a.sa:
        d = pickle.load(open(p, 'rb'))
        m_s, info_s = d['model'], d['info']
        P_s = d['d']['P']
        nm = 'sa_' + Path(p).stem.replace('best', 's')
        add(nm, f"Own annealer over legal hub slots + spine width + block remap (state {json.dumps(d['state'])})", m_s, P_s, info=info_s,
            cost=dict(die_shrink_option_mm2=info_s['die_shrink_mm2']))
    comp = dict(schema='opentallas.qwen.globalfp-comparison.v1', input=str(die.path), input_sha256=die.sha, reach_um=C.REACH,
                objective='exposed stage-cycles/token = 217 x ME loop + 73 x collective loop + 36 x KV loop; plus sum width x '
                          'length, traffic x length, bits over reach, relay flops, coarse worst cut',
                traffic_note=C.TRAFFIC_NOTE, unknowns=UNKNOWNS, qualification=False,
                candidates=[c['metrics'] for c in cands])
    (a.out / 'comparison.json').write_text(json.dumps(comp, indent=1, default=str))
    keep = {c['name']: c['model'] for c in cands}
    pickle.dump(keep, open(a.out / 'models.pkl', 'wb'))
    figure(die, cands, a.out / 'candidates')


if __name__ == '__main__':
    main()
