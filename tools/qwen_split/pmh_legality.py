#!/usr/bin/env python3
"""PM-H legality screen (GEO-Q, 2026-10-15): die x-grid / track phase of the MY and shifted R0 instances, inner-channel
track demand of the paired tree buses, and relay / clock-wire totals, for the pair-mirrored compute columns with the
head rows 7/8 kept (pair_mirror.build(keep_rows=(7, 8))).

Track phases are the ASAP7 die tracks (platform make_tracks.tcl): vertical M3 0.036/0.009, M5 0.048/0.012,
M7 0.064/0.016, M9 0.080/0.116.  A vertical-layer pin of an instance at X is on a die track when
(X + c - o) mod p == 0 (R0) or (X + W - c - o) mod p == 0 (MY), c = pin centre in the master.
Channel demand: every pair-internal bus bit runs pin -> pin across the inner channel; the y jog between its two face
pins must be taken on vertical layers inside the channel (the tiles obstruct M1..M7 over their bodies).  Cut = max over
y of (bits whose jog spans y) / (vertical tracks in the channel on the counted layers).  Assignment-pin geometry only.
"""
import argparse, collections, json, math
from pathlib import Path
import numpy as np
from orientation_search import Graph, load, totals, ctrl_movement
import pair_mirror as pm

TRK = {'M3': (36, 9), 'M5': (48, 12), 'M7': (64, 16), 'M9': (80, 116)}
VPITCH = {'M3': 0.036, 'M5': 0.048, 'M7': 0.064, 'M9': 0.080}


def grid_audit(d, model):
    """Per master / orientation: count of vertical-layer pins off the die track, by offset (nm)."""
    out = collections.defaultdict(collections.Counter)
    for i in model.values():
        M = d['masters'].get(i['m'])
        if not M or i['m'] not in ('qfd_tile_nk', 'qfd_xcst_s', 'qfd_xcst_n', 'qfd_xcol_w', 'qfd_xcol_e'):
            continue
        X = round(i['x'] * 1000); W = round(M['w'] * 1000)
        for p in M['pins']:
            if p['layer'] not in TRK:
                continue
            pit, o = TRK[p['layer']]; x0, x1 = round(p['rect'][0] * 1000), round(p['rect'][2] * 1000); c = (x0 + x1) // 2
            off = ((X + W - c - o) if i['o'] == 'MY' else (X + c - o)) % pit
            out[(i['m'], i['o'], p['layer'])]['on' if off == 0 else f'off{off}'] += 1
    return {f'{m}|{o}|{l}': dict(v) for (m, o, l), v in sorted(out.items())}


def snap(base, m):
    """Track-legal PM-H: moved R0 tiles/stations -24 nm (inner 16.440, gapR 64.800, origin back on the 144-nm phase of
    the baseline), MY stations -30 nm (X = 6 mod 36: their M3 ck/rst_n pins on the die M3 track; 30-nm gap to the tile).
    MY tiles stay at L + 64.776 (= 24 mod 48: the N-face M5 ck lands on the die M5 track)."""
    for n, i in m.items():
        if i['m'] not in ('qfd_tile_nk', 'qfd_xcst_s', 'qfd_xcst_n') or abs(i['x'] - base[n]['x']) < 1e-6:
            continue
        if i['o'] == 'R0':
            i['x'] = round(i['x'] - 0.024, 3)
        elif i['m'] != 'qfd_tile_nk':
            i['x'] = round(i['x'] - 0.030, 3)
    return m


def channel_demand(g, model, layers=('M3', 'M5', 'M7'), pdn_frac=0.0):
    tiles = {n: i for n, i in model.items() if i['m'] == 'qfd_tile_nk'}
    # pairs: an MY tile and the R0 tile whose W face faces its (mirrored) W face across the inner channel
    by_row = collections.defaultdict(list)
    for n, i in tiles.items():
        by_row[round(i['y'], 3)].append(i)
    pairs = {}
    for row in by_row.values():
        row.sort(key=lambda i: i['x'])
        for a, b in zip(row, row[1:]):
            if a['o'] == 'MY' and b['o'] == 'R0':
                gap = b['x'] - (a['x'] + a['w'])
                if gap < 40:
                    pairs[(a['n'], b['n'])] = gap
    res = []
    for (ea, ob), gap in pairs.items():
        jogs = []; buses = []
        for r in g.data:
            names = [n for n, _ in r['ends']]
            if set(names) != {ea, ob}:
                continue
            pts = [g.place(n, loc, model) for n, loc in r['ends']]
            ys = np.stack([p[:, 1] for p in pts])
            lo, hi = ys.min(0), ys.max(0)
            jogs.append(np.stack([lo, hi], 1)); buses.append((r['b'], r['n'], float(np.abs(hi - lo).mean())))
        if not jogs:
            continue
        J = np.concatenate(jogs)
        ylo, yhi = J[:, 0].min(), J[:, 1].max()
        grid = np.arange(math.floor(ylo), math.ceil(yhi) + 1, 0.5)
        dem = ((J[:, 0][None, :] <= grid[:, None]) & (J[:, 1][None, :] >= grid[:, None]) & (J[:, 1] - J[:, 0] > 0.05)[None, :]).sum(1)
        cap = sum(int(gap / VPITCH[l]) for l in layers) * (1 - pdn_frac)
        span = yhi - ylo; hcap = span / 0.048 + span / 0.064            # M4 + M6 horizontal tracks over the pin span
        hbits = len(J)
        res.append(dict(pair=[ea, ob], inner_um=round(gap, 3), buses=buses, bits=int(len(J)),
                        max_vertical_bits=int(dem.max()), at_y=float(grid[dem.argmax()]) if len(grid) else None,
                        vertical_tracks=round(cap, 1), cut=round(float(dem.max()) / cap, 3) if cap else None,
                        horizontal_bits=int(hbits), horizontal_span_um=round(float(span), 3),
                        horizontal_tracks_m4_m6=round(float(hcap), 1), horizontal_cut=round(hbits / hcap, 3)))
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('input', type=Path); ap.add_argument('out', type=Path)
    a = ap.parse_args()
    d, sha = load(a.input); g = Graph(d, d['constraints']['per_hop_um'])
    base = {n: dict(i) for n, i in g.inst.items()}; ev0 = g.evaluate(base); t0 = totals(g, ev0)
    tp = g.pins['qfd_tile_nk']; orig = {p: tp[p].copy() for p in ('n_a', 'n_b', 'n_y', 't_out')}
    from placement_repack import validate
    out = dict(schema='opentallas.qwen.pmh-legality.v1', input_sha256=sha, source_commit=d.get('source_commit'),
               baseline=t0, candidates=[], qualification=False)
    for label, sn, plan in (('PM-H inner 16.464 (as proposed)', False, 'current_W_windows'),
                            ('PM-H-S snapped (inner 16.440, gapR 64.800, MY station -30 nm)', True, 'current_W_windows'),
                            ('PM-H-S snapped + interleaved tree words', True, 'interleave')):
        for p in orig: tp[p][:] = orig[p]
        if plan == 'interleave':
            pm.interleave(tp)
        m, geom = pm.build(base, keep_rows=(7, 8))
        if sn:
            m = snap(base, m); geom = dict(geom, inner_um=16.44, gapR_um=64.8, my_station_shift_nm=-30, r0_shift_nm=-24)
        errs = validate(list(m.values()), d['die'])
        ev = g.evaluate(m); t = totals(g, ev)
        ch = channel_demand(g, m)
        cuts = [c['cut'] for c in ch]
        ck = [r for r in ctrl_movement(g, base, m) if r['family'] == 'clock_trunk']
        rs = [r for r in ctrl_movement(g, base, m) if r['family'] == 'reset']
        rec = dict(name=label, geometry=geom, tree_pin_plan=plan, rectangle_errors=len(errs), totals=t,
                   delta=dict(bit_um=round(t['bit_um'] - t0['bit_um'], 1), pct=round(100 * (t['bit_um'] - t0['bit_um']) / t0['bit_um'], 3),
                              relay_bit_stages=t['relay_bit_stages'] - t0['relay_bit_stages']),
                   my_tiles=sum(1 for i in m.values() if i['m'] == 'qfd_tile_nk' and i['o'] == 'MY'),
                   my_stations=sum(1 for i in m.values() if i['m'] in ('qfd_xcst_s', 'qfd_xcst_n') and i['o'] == 'MY'),
                   my_xcol=sum(1 for i in m.values() if i['m'] in ('qfd_xcol_w', 'qfd_xcol_e') and i['o'] == 'MY'),
                   grid=grid_audit(d, m),
                   channel=dict(pairs=len(ch), max_cut=max(cuts) if cuts else None, max_horizontal_cut=max(c['horizontal_cut'] for c in ch) if ch else None, worst=max(ch, key=lambda c: c['cut']) if ch else None,
                                cut_hist=dict(collections.Counter(round(c, 2) for c in cuts))),
                   clock_trunk=dict(nets=len(ck), hpwl_delta_um=round(sum(r['hpwl_after'] - r['hpwl_before'] for r in ck), 3),
                                    longest_delta_max_um=round(max((r['longest_after'] - r['longest_before'] for r in ck), default=0), 3),
                                    longest_delta_min_um=round(min((r['longest_after'] - r['longest_before'] for r in ck), default=0), 3)),
                   reset=dict(nets=len(rs), hpwl_delta_um=round(sum(r['hpwl_after'] - r['hpwl_before'] for r in rs), 3)))
        out['candidates'].append(rec)
        print(json.dumps({k: rec[k] for k in ('name', 'rectangle_errors', 'delta', 'my_tiles', 'my_stations', 'my_xcol', 'clock_trunk', 'reset')}))
        print('  channel', json.dumps({k: v for k, v in rec['channel'].items() if k != 'worst'}), 'worst', json.dumps(rec['channel']['worst'])[:400])
        print('  grid', json.dumps(rec['grid']))
    for p in orig: tp[p][:] = orig[p]
    a.out.mkdir(parents=True, exist_ok=True); (a.out / 'pmh_legality.json').write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
