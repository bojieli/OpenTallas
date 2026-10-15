#!/usr/bin/env python3
"""Pair-mirrored compute columns: a coherent structural alternative to the single-face tile tree plan.

All four 514-bit tile tree words sit on the tile W face (source_pin_plan.apply_tile) while the registered tap faces
E onto its station column.  Every column-pair tree edge (L0 t_out->n_b, L1 n_y->n_a) therefore crosses a whole tile.
Here each column pair (2k, 2k+1) of each 24-column half becomes [gapL | even tile MY | inner | odd tile R0 | gapR]:
the even tile's tree words face the odd tile's across a narrow inner channel, both taps face outward to their own
station/DVM column (station MY on the left side so tap_d still faces the tile).  Pair pitch stays 2 x 522.288 um, the
field extent, tile count, masters, rows and die area are unchanged.  Every incident bus (tree, tap, corridor, head
chain, spine words, clocks/resets) is re-scored on the current generated per-bit pins.  Geometry proposal only.
"""
import argparse, collections, copy, json, math
from pathlib import Path
import numpy as np
from orientation_search import Graph, load, totals, regressions, ctrl_movement, family_split
from tile_tree_faces import over_tile_bits

TW, PITCH = 449.28, 522.288


def build(base, xcol_w=64.776, inner=None, keep_rows=()):
    """keep_rows: tile rows (with their stations and the head-row DVM columns) left at the current uniform pitch."""
    m = copy.deepcopy(base)
    tiles = [i for i in m.values() if i['m'] == 'qfd_tile_nk']
    xs = sorted({i['x'] for i in tiles})
    assert len(xs) == 48
    halves = [xs[:24], xs[24:]]
    gap_total = 2 * PITCH - 2 * TW
    inner = gap_total - 2 * xcol_w if inner is None else inner
    gapL = (gap_total - inner) / 2
    newx = {}; col_side = {}
    for half in halves:
        for k in range(12):
            L = half[2 * k]
            assert abs(half[2 * k + 1] - L - PITCH) < 1e-3
            ex = L + gapL; ox = ex + TW + inner
            newx[half[2 * k]] = (ex, 'MY', ex - 0.0, 'L')          # even tile: MY, its column left of it
            newx[half[2 * k + 1]] = (ox, 'R0', ox + TW, 'R')        # odd tile: R0, its column right of it
    moved = []
    for i in m.values():
        if i['m'] == 'qfd_tile_nk' and int(i['n'].split('_')[2]) not in keep_rows:
            ox = i['x']; nx, o, _, _ = newx[ox]; i['x'] = round(nx, 3); i['o'] = o
    # station / DVM column instances sit at old tile x + 449.28
    colmap = {round(x + TW, 3): x for x in xs}
    for i in m.values():
        if i['m'] in ('qfd_xcst_s', 'qfd_xcst_n', 'qfd_xcol_w', 'qfd_xcol_e'):
            if keep_rows and (i['n'].startswith('h_') or int(i['n'].split('_')[2]) in keep_rows):
                continue
            tx = colmap[round(i['x'], 3)]; nx, o, edge, side = newx[tx]
            if side == 'L':
                i['x'] = round(nx - i['w'], 3); i['o'] = 'MY'      # abut the even tile's W (tap) face
            else:
                i['x'] = round(edge, 3)                           # abut the odd tile's E (tap) face, unchanged form
    return m, dict(inner_um=round(inner, 3), gapL_um=round(gapL, 3), gapR_um=round(gapL, 3), kept_rows=list(keep_rows))


def interleave(tp, h=1442.88, pitch=0.096):
    """Bitwise interleave the facing word pairs on the tile W face: (t_out[k], n_b[k]) and (n_y[k], n_a[k]) one
    track apart, so a mirrored neighbour's t_out[k] lands one track from this tile's n_b[k] (and n_y on n_a)."""
    n = 514; k = np.arange(2 * n) * pitch
    for (p, q), c in ((('t_out', 'n_b'), h / 2 + 5.0 + 49.344), (('n_y', 'n_a'), h / 2 - 5.0 - 49.344)):
        y = c + k - k.mean()
        tp[p][:, 0] = 0.096; tp[p][:, 1] = y[0::2]
        tp[q][:, 0] = 0.096; tp[q][:, 1] = y[1::2]


def chain_stages(g, m, ev0, ev):
    """End-to-end head-chain relay stages per half (xs_tap -> far column), plus register hops."""
    out = {}
    for k, r in enumerate(g.data):
        if r['c'] == 'head_chain' and r['n'] > 1:
            xs = np.mean([g.place(n, loc, m)[:, 0].mean() for n, loc in r['ends']])
            half = 'west' if xs < 16000 else 'east'
            o = out.setdefault(half, dict(hops=0, relays_before=0, relays_after=0, um_before=0.0, um_after=0.0))
            o['hops'] += 1; o['relays_before'] += ev0[k][2]; o['relays_after'] += ev[k][2]
            o['um_before'] = round(o['um_before'] + ev0[k][1], 3); o['um_after'] = round(o['um_after'] + ev[k][1], 3)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('input', type=Path); ap.add_argument('out', type=Path); a = ap.parse_args()
    d, sha = load(a.input); g = Graph(d, d['constraints']['per_hop_um'])
    base = {n: dict(i) for n, i in g.inst.items()}; ev0 = g.evaluate(base); t0 = totals(g, ev0); x0 = over_tile_bits(g, base)
    from placement_repack import validate
    res = dict(schema='opentallas.qwen.pair-mirror-columns.v1', input_sha256=sha, source_commit=d.get('source_commit'),
               baseline=dict(t0, over_tile_bit_crossings=x0), candidates=[], qualification=False)
    tp = g.pins['qfd_tile_nk']; orig = {p: tp[p].copy() for p in ('n_a', 'n_b', 'n_y', 't_out')}
    for label, kw, plan in (('pair_mirror_xcol_outer', {}, 'current_W_windows'), ('pair_mirror_interleaved', {}, 'interleave'),
                            ('pair_mirror_keep_head_rows', dict(keep_rows=(7, 8)), 'current_W_windows'),
                            ('pair_mirror_keep_head_rows_interleaved', dict(keep_rows=(7, 8)), 'interleave'),
                            ('interleave_only_no_mirror', None, 'interleave')):
        for p in orig: tp[p][:] = orig[p]
        if plan == 'interleave':
            interleave(tp)
        if kw is None:
            m, geom = copy.deepcopy(base), dict(note='current placement, tile pin plan only')
        else:
            m, geom = build(base, **kw)
        geom['tile_tree_pin_plan'] = plan
        errs = validate(list(m.values()), d['die'])
        # station / xcol orientation choice for the left (MY) side: keep MY only if it is not worse than R0
        ev = g.evaluate(m); t = totals(g, ev)
        hc = [(g.data[k]['b'], ev0[k][1], ev[k][1], ev0[k][2], ev[k][2]) for k in range(len(ev)) if g.data[k]['c'] == 'head_chain' and g.data[k]['n'] > 1]
        res['candidates'].append(dict(name=label, geometry=geom, rectangle_errors=errs[:20], rectangle_error_count=len(errs), totals=t,
            over_tile_bit_crossings=over_tile_bits(g, m),
            delta=dict(bit_um=round(t['bit_um'] - t0['bit_um'], 1), pct=round(100 * (t['bit_um'] - t0['bit_um']) / t0['bit_um'], 3),
                       relay_bit_stages=t['relay_bit_stages'] - t0['relay_bit_stages'], worst_pair_um=round(t['worst_pair_um'] - t0['worst_pair_um'], 3)),
            families=family_split(g, ev0, ev), buses=regressions(g, ev0, ev, 10),
            head_chain=dict(hops=len(hc), max_hop_before=round(max(h[1] for h in hc), 3), max_hop_after=round(max(h[2] for h in hc), 3),
                            relay_stages_before=sum(h[3] for h in hc), relay_stages_after=sum(h[4] for h in hc)),
            head_chain_end_to_end=chain_stages(g, m, ev0, ev),
            clock_reset_changed=len(ctrl_movement(g, base, m)),
            clock_trunk_hpwl_delta_um=round(sum(r['hpwl_after'] - r['hpwl_before'] for r in ctrl_movement(g, base, m) if r['family'] == 'clock_trunk'), 3),
            qualification=False))
    for p in orig: tp[p][:] = orig[p]
    a.out.mkdir(parents=True, exist_ok=True); (a.out / 'pair_mirror.json').write_text(json.dumps(res, indent=1) + '\n')
    for c in res['candidates']:
        print(json.dumps({k: c[k] for k in ('name', 'geometry', 'rectangle_error_count', 'totals', 'over_tile_bit_crossings', 'delta', 'head_chain', 'head_chain_end_to_end', 'clock_reset_changed', 'clock_trunk_hpwl_delta_um')}))
        print({k: v for k, v in c['families'].items() if v['before'] != v['after']})
        print('stage incr', len(c['buses']['stage_increases']), [(x['bus'], x['bits'], x['stages_before'], x['stages_after']) for x in c['buses']['stage_increases'][:12]])
        print('regress', [(x['bus'], x['bits'], x['delta_bit_um']) for x in c['buses']['regressions'][:8]])
    print('baseline', res['baseline'])
    for p in orig: tp[p][:] = orig[p]
    figure(a.out / 'pair_mirror_zoom', g, [('Reference wide27 (all tiles R0, tree words on W face)', base, 'current_W_windows'),
           ('PM: pair-mirrored columns (even MY, 16.464-um inner channel)', build(base)[0], 'current_W_windows'),
           ('PM-H: pair-mirrored, head rows 7/8 kept', build(base, keep_rows=(7, 8))[0], 'current_W_windows')])



def figure(path, g, panels, window=(0, 2200, 8000, 15500)):
    """To-scale zoom (first four columns, rows 5..9) of tiles, stations, DVM columns and tree/tap/corridor pin legs."""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    x0, x1, y0, y1 = window
    fig, axes = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 9), squeeze=False)
    colors = dict(tree_block='#d95f02', tap='#1b9e77', corridor='#7570b3', head_chain='#e7298a')
    for ax, (title, m, plan) in zip(axes[0], panels):
        tp = g.pins['qfd_tile_nk']; keep = {p: tp[p].copy() for p in ('n_a', 'n_b', 'n_y', 't_out')}
        if plan == 'interleave': interleave(tp)
        for i in m.values():
            if i['x'] > x1 or i['x'] + i['w'] < x0 or i['y'] > y1 or i['y'] + i['h'] < y0: continue
            fc = {'qfd_tile_nk': '#dddddd', 'qfd_xcst_s': '#9ecae1', 'qfd_xcst_n': '#9ecae1', 'qfd_xcol_w': '#a1d99b', 'qfd_xcol_e': '#a1d99b'}.get(i['m'], '#fdd0a2')
            ax.add_patch(Rectangle((i['x'], i['y']), i['w'], i['h'], fc=fc, ec='k', lw=.4))
            if i['m'] == 'qfd_tile_nk': ax.text(i['x'] + i['w'] / 2, i['y'] + i['h'] / 2, f"{i['n']}\n{i['o']}", ha='center', va='center', fontsize=6, clip_on=True)
        for r in g.data:
            if r['c'] not in colors: continue
            pts = [g.place(n, loc, m).mean(0) for n, loc in r['ends']]
            if not any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pts): continue
            xs, ys = zip(*pts); ax.plot(xs, ys, color=colors[r['c']], lw=.8 if r['c'] != 'tree_block' else 1.2, alpha=.85)
        for p in keep: tp[p][:] = keep[p]
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=8); ax.tick_params(labelsize=6)
    handles = [plt.Line2D([], [], color=c, label=k) for k, c in colors.items()]
    fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=7)
    fig.suptitle('Qwen compute field, columns 0-3 rows 5-9, actual dimensions (um). Lines join per-word pin centroids; proposal only, no route/clock/cut qualification.', fontsize=7)
    fig.savefig(path.with_suffix('.svg')); fig.savefig(path.with_suffix('.png'), dpi=130); plt.close(fig)


if __name__ == '__main__':
    main()
