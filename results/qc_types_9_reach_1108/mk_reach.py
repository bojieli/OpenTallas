#!/usr/bin/env python3
"""QC-TYPES-9/REACH 11-08: plan event plan_qc53v4w = v4u2 + FACE-REACH stations on the hc cw_n out buses.

Class SETUP-AT-GRT (hc0/hc1/hc2): u_u_xh<k>.n_d -> u_bout_cw_n<k> is one 1.2-1.4 mm hop (TT -106..-145 ps,
348-473 endpoints per row).  The xh leaf sits by the S face (b_hw_i, 1573 bits) and cw_n<k> leaves at the N face.
Fix: N FIRM internal stations per cw_n<k> (R3-INTERNAL, native: materialised by the bind, lane fixed_cycles +N,
internal_source_cycles = N so the receiver gets no pad).  Every hop <= budgets.ft_station_max_um (405 um).

Source centroids are measured on placed DBs (mean of the u_u_xh<k>.n_d flops, type frame):
  hc0 sle_hc0__cl929603c0__cl38badc56 a14 3_place.odb  (379.7, 88.4)
  hc1 slw_hc1__cl68f9248e__cl144ee7b3 a11 3_place.odb  (158.4, 156.0)
  hc2 slw_hc2__cla3497502__cldc737267 vFR probe        (93.1, 131.7)
usage: mk_reach.py BASE_PLAN BASE_ASBUILT OUT_PLAN OUT_ASBUILT REPORT [N]
"""
import json, math, sys
from pathlib import Path

SRC = {'0': (379.7, 88.4), '1': (158.4, 156.0), '2': (93.1, 131.7)}


def main(argv):
    base, ab_in, out_plan, out_ab, report = argv[:5]
    n = int(argv[5]) if len(argv) > 5 else 3
    p = json.loads(Path(base).read_text())
    smax = float(p['budgets']['ft_station_max_um'])
    types, rows = [], []
    for tn, t in sorted(p['partition_types'].items()):
        k = next((k for k in SRC if tn.startswith((f'sle_hc{k}__', f'slw_hc{k}__'))), None)
        if k is None:
            continue
        bus = next(b for b in t['buses'] if b['name'] == f'cw_n{k}')
        assert bus['dir'] == 'out' and bus['face'] == 'N', (tn, bus)
        assert not any(e.get('conn') == f'bus:cw_n{k}' for e in t.get('internal_stations', [])), tn
        W, H = t['outline_um']
        pin = (round((bus['window_um'][0] + bus['window_um'][1]) / 2, 3), H)
        sx, sy = SRC[k]
        # plan convention (native_istations.source_entries): OUT geometry is written face -> core
        regs = [[round(pin[0] + (sx - pin[0]) * j / (n + 1), 3), round(pin[1] + (sy - pin[1]) * j / (n + 1), 3)]
                for j in range(1, n + 1)]
        pts = [pin] + [tuple(r) for r in regs] + [(sx, sy)]
        hop = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))
        assert hop <= smax, (tn, hop)
        t.setdefault('internal_stations', []).append(dict(
            conn=f'bus:cw_n{k}', from_um=[pin[0], pin[1]], to_um=[sx, sy], regs_um=regs, bits=int(bus['width']),
            launch=bus['leaf'], capture='face flop',
            note=f'FACE-REACH (QC-TYPES-9 11-08): xh{k}.n_d -> N face {hop * (n + 1):.0f} um, {n} FIRM station(s) '
                 f'(data + epoch), hop {hop:.0f} um; counted in the lane fixed_cycles (PIN CYCLES +{n})'))
        types.append(tn)
        rows.append(dict(type=tn, bus=f'cw_n{k}', stations=n, hop_um=round(hop, 1), regs_um=regs))
    # lanes sourced at those buses: +n fixed cycles (source stations, receiver 0)
    ptype = {x['name']: x['type'] for x in p['partitions']}
    ports = {x['id']: x for x in p['ports']}
    lanes = []
    for ln in p['lanes']:
        s = ports[ln['ports'][0]]['src']
        if s['part'] in ptype and ptype[s['part']] in types and s['bus'].startswith('cw_n'):
            assert s['bus'] == 'cw_n' + ptype[s['part']].split('_hc')[1][0]
            ln['fixed_cycles'] = int(ln.get('fixed_cycles', 0)) + n
            lanes.append(ln['id'])
    p['note'] = (p.get('note', '') + f' | plan_qc53v4w (QC-TYPES-9/REACH 11-08): v4u2 + FACE-REACH {n} native stations on '
                 f'cw_n0/1/2 of {len(types)} hc types, {len(lanes)} lanes fixed_cycles +{n} (PIN CYCLES)')
    Path(out_plan).write_text(json.dumps(p) + '\n')
    ab = json.loads(Path(ab_in).read_text())
    assert not ab.get('internal_stations_types')
    ab['internal_stations_types'] = types
    Path(out_ab).write_text(json.dumps(ab, indent=1) + '\n')
    Path(report).write_text(json.dumps(dict(stations=n, types=rows, lanes=lanes, pin_cycles={l: n for l in lanes}),
                                       indent=1) + '\n')
    print(json.dumps(dict(types=len(types), lanes=len(lanes), worst_hop=max(r['hop_um'] for r in rows))))


if __name__ == '__main__':
    main(sys.argv[1:])
