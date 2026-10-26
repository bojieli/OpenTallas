#!/usr/bin/env python3
"""Face assignment search for the four 514-bit qfd_tile_nk tree words (n_a, n_b, n_y, t_out).

source_pin_plan.apply_tile puts all four on the W face (M4, 56-um windows around h/2).  Every east-neighbour
tree edge then lands on the far (W) face of the receiving tile and must cross that tile's body at die level
(tile obs_top=7, so only M8/M9 are available over it).  This tool re-scores the WHOLE current graph for every
W/E/N/S face combination of the four words (same 96-nm M4/M5 pitch and window shape, tap/rst/tie/tile_id and all
clock entries unchanged), and reports die bit-um, over-tile M8/M9 bit crossings, relay stages and the intra-tile
displacement bound of each moved word.  Proposal only: never route, cut, timing or clock qualification.
"""
import argparse, copy, itertools, json, math
from pathlib import Path
import numpy as np
from orientation_search import Graph, load, totals

PORTS = ('n_a', 'n_b', 'n_y', 't_out')
W, H = 449.28, 1442.88
PITCH = 0.096


def window(face, j, n=514):
    """Return local pin centres for word j on a face: 514 pins at 96 nm, centred at the same per-word offset
    the current plan uses (h/2 + (j-1.5)*56 on W/E; w/2 + (j-1.5)*56 on N/S, M5)."""
    k = np.arange(n) * PITCH; k = k - k.mean()
    if face in ('W', 'E'):
        c = H / 2 + (j - 1.5) * 56.0
        # E face carries tap (697..746), rst/tile_id/ties (681..690): keep E words clear of 676..751.
        if face == 'E':
            c = {0: 560.0, 1: 616.0, 2: 812.0, 3: 868.0}[j]
        x = np.full(n, 0.096 if face == 'W' else W - 0.096)
        return np.stack([x, c + k], 1)
    c = W / 2 + (j - 1.5) * 56.0
    if face == 'N':  # N face has ck at w/2 (224.6): shift words to stay clear
        c = {0: 60.0, 1: 116.0, 2: 333.0, 3: 389.0}[j]
    y = np.full(n, H - 0.096 if face == 'N' else 0.096)
    return np.stack([c + k, y], 1)


def over_tile_bits(g, model):
    """Bits whose per-bit pin span covers more than half of a tile body at die level (M8/M9 over-the-block)."""
    tiles = [(i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h']) for i in model.values() if i['m'] == 'qfd_tile_nk']
    T = np.array(tiles); total = 0
    for r in g.data:
        if r['c'] not in ('tree_block', 'tree_spine', 'tap'):
            continue
        pts = np.stack([g.place(n, loc, model) for n, loc in r['ends']])
        lo = pts.min(0); hi = pts.max(0)  # bits x 2
        for b in range(0, r['n'], 64):  # sample every 64th bit (words are uniform)
            x0, y0 = lo[b]; x1, y1 = hi[b]
            ys = pts[:, b, 1]
            # horizontal crossings: tile fully inside x-span and containing an endpoint y
            hx = (((np.minimum(T[:, 2], x1) - np.maximum(T[:, 0], x0)) > 0.5 * (T[:, 2] - T[:, 0])) & (((T[:, 1] <= ys[:, None]) & (T[:, 3] >= ys[:, None])).any(0))).sum()
            xs = pts[:, b, 0]
            vy = (((np.minimum(T[:, 3], y1) - np.maximum(T[:, 1], y0)) > 0.5 * (T[:, 3] - T[:, 1])) & (((T[:, 0] <= xs[:, None]) & (T[:, 2] >= xs[:, None])).any(0))).sum()
            total += int(hx + vy) * min(64, r['n'] - b)
    return total


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('input', type=Path); ap.add_argument('out', type=Path); a = ap.parse_args()
    d, sha = load(a.input); g = Graph(d, d['constraints']['per_hop_um'])
    model = {n: dict(i) for n, i in g.inst.items()}
    orig = {p: g.pins['qfd_tile_nk'][p].copy() for p in PORTS}
    ev0 = g.evaluate(model); t0 = totals(g, ev0); x0 = over_tile_bits(g, model)
    fam0 = {}
    for k, e in enumerate(ev0): fam0[g.data[k]['c']] = fam0.get(g.data[k]['c'], 0) + e[0]
    rows = []
    for faces in itertools.product('WENS', repeat=4):
        for j, (p, f) in enumerate(zip(PORTS, faces)):
            g.pins['qfd_tile_nk'][p][:] = window(f, j)
        ev = g.evaluate(model); t = totals(g, ev)
        fam = {}
        for k, e in enumerate(ev): fam[g.data[k]['c']] = fam.get(g.data[k]['c'], 0) + e[0]
        shift = {p: round(float(np.abs(g.pins['qfd_tile_nk'][p] - orig[p]).sum(1).mean()), 1) for p in PORTS}
        rows.append(dict(faces=dict(zip(PORTS, faces)), bit_um=t['bit_um'], delta_bit_um=round(t['bit_um'] - t0['bit_um'], 1),
                         delta_pct=round(100 * (t['bit_um'] - t0['bit_um']) / t0['bit_um'], 3), worst_pair_um=t['worst_pair_um'],
                         relay_bit_stages=t['relay_bit_stages'], delta_relay_bit_stages=t['relay_bit_stages'] - t0['relay_bit_stages'],
                         family_delta_bit_um={k: round(fam[k] - fam0[k], 1) for k in fam if abs(fam[k] - fam0[k]) > 1},
                         intra_tile_shift_um_per_bit=shift,
                         intra_tile_bound_bit_um=round(sum(shift[p] for p in PORTS) * 514 * 768, 1)))
    rows.sort(key=lambda r: r['bit_um'])
    for r in rows[:8] + [x for x in rows if set(x['faces'].values()) == {'W'}]:
        for j, (p, f) in enumerate(r['faces'].items()):
            g.pins['qfd_tile_nk'][p][:] = window(f, j)
        r['over_tile_bit_crossings'] = over_tile_bits(g, model)
    for p in PORTS: g.pins['qfd_tile_nk'][p][:] = orig[p]
    out = dict(schema='opentallas.qwen.tile-tree-face-search.v1', input_sha256=sha, source_commit=d.get('source_commit'),
               baseline=dict(t0, over_tile_bit_crossings=x0, family_bit_um={k: round(v, 1) for k, v in fam0.items()}),
               all_W_window_model_check=[x for x in rows if set(x['faces'].values()) == {'W'}][0],
               ranked=rows[:24], combos=len(rows), qualification=False,
               unknowns=['Intra-tile wire from moved pin to node/leaf logic: bounded by intra_tile_shift (logic not yet placed for the new tile).',
                         'E/N face windows chosen clear of tap/rst/tie/tile_id/ck; actual M4/M5 access/OBS not checked.',
                         'Over-tile crossings sampled every 64th bit; M8/M9 track supply not modelled.',
                         'Tile compression successor (481.68x1400.22, TX198) changes outline; re-run on its LEF when frozen.'])
    a.out.mkdir(parents=True, exist_ok=True); (a.out / 'tile_tree_faces.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(baseline=out['baseline'], allW=out['all_W_window_model_check'], top=rows[:8]), indent=1))


if __name__ == '__main__':
    main()
