#!/usr/bin/env python3
"""H-D4G GEN2 10-18: grant slots for the COLLQ + ring-B instances (l6_collq.py) in results/arch/hbm_die_d4g/grants_d4g.json.

Per quadrant q, all abutting the COLL engine slot coll_<q> (hb_coll_<q>) at the 21.6-um clearance (>= 20 um, as
d4g_sfuplan.py checks), so no new empty area opens on the COLL links:
  collgi_<q>  237.6 x 237.6  ot_hgi_coll_gq_issue   (kit hcoll_gq_issue_1018: N host + ISA from hb_coll, E rings, W/S VM banks)
  collgl_<q>  237.6 x 237.6  ot_hgi_coll_gq_land    (kit hcoll_gq_land_1018), beside gi (ld_* 600 b) and the ring B stop
  collb_<q>   129.6 x 129.6  ot_hgi_coll_ring_b_stop (kit hcoll_ring_b_stop_1018), beside gi (rb_* 291 b) / gl (pb_* 524 b)
  collrs_<q>  345.6 x 345.6  ot_hbm_idx_vm_share2_static (6,584 pins -> 5.3/um over 90 % of the perimeter)
  collks<p>_<q> 129.6 x 129.6 ot_hgi_coll_kq_share2_leaf (kit hcoll_kqs_leaf_1018), p = bank pair 0..3 (HBM-NSFIX/KQS 10-18:
              the kq share is 4 hardened leaves with registered faces, +2 edges; was one 345.6 combinational collks_<q>).
              Placed at the WRITER end (abutting coll_<q> / collgl_<q>): A and B both start there, so only the merged 2,248-b
              word runs the 3-8 mm to the banks (leaves beside the bank pairs would carry 4,496 b over that distance).
rs / ks sit on the coll face toward the quadrant VM banks where it is free (they carry the bank-side relay chains).
Candidates are scanned along the coll slot's faces (21.6-um steps); a slot must clear every other grant slot and every
plan block (plan/d4g_phy/compact.P.json) that is not the coll block itself by >= 20 um and stay inside the quadrant.
Idempotent: existing coll{gi,gl,b,rs,ks}_<q> slots are replaced.
    d4g_gen2_grants_collq.py [--grants G] [--plan P] [--report R]"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/hbm_die_d4g'
Q = ['SW', 'SE', 'NW', 'NE']
CLR, STEP = 21.6, 21.6
NEW = [('collgi', 'ot_hgi_coll_gq_issue', 237.6, 'tile', 'hcoll_gq_issue_1018'),
       ('collgl', 'ot_hgi_coll_gq_land', 237.6, 'tile', 'hcoll_gq_land_1018'),
       ('collb', 'ot_hgi_coll_ring_b_stop', 129.6, 'tile', 'hcoll_ring_b_stop_1018'),
       ('collrs', 'ot_hbm_idx_vm_share2_static', 345.6, 'tile', None),
       ] + [(f'collks{p}', 'ot_hgi_coll_kq_share2_leaf', 129.6, 'tile', 'hcoll_kqs_leaf_1018') for p in range(4)]
LEGACY = ['collks']   # pre-KQS single combinational collks_<q> slot: removed


def rect(s):
    return (s['origin']['x'], s['origin']['y'], s['origin']['x'] + s['outline']['w'], s['origin']['y'] + s['outline']['h'])


def gap(a, b):
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def cdist(a, b):
    return abs((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2) + abs((a[1] + a[3]) / 2 - (b[1] + b[3]) / 2)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--grants', default=str(D / 'grants_d4g.json'))
    ap.add_argument('--plan', default=str(D / 'plan/d4g_phy/compact.P.json'))
    ap.add_argument('--report', default=str(D / 'collq/gen2_collq_slots.json'))
    a = ap.parse_args()
    g = json.loads(Path(a.grants).read_text()); P = json.loads(Path(a.plan).read_text())
    g['slots'] = [s for s in g['slots'] if not any(s['name'] == f'{k}_{q}' for k in [n for n, *_ in NEW] + LEGACY for q in Q)]
    die = next(s for s in g['slots'] if s['kind'] == 'die'); W, H = die['outline']['w'], die['outline']['h']
    obst = {s['name']: rect(s) for s in g['slots'] if s['kind'] != 'die' and s.get('origin') and s.get('outline')}
    pblk = {n: (r['x'], r['y'], r['x'] + r['w'], r['y'] + r['h']) for n, r in P.items() if isinstance(r, dict) and 'x' in r}
    rep = {}
    for q in Q:
        cs = next(s for s in g['slots'] if s['name'] == f'coll_{q}'); C = rect(cs)
        qx = (0, W / 2) if q[1] == 'W' else (W / 2, W); qy = (0, H / 2) if q[0] == 'S' else (H / 2, H)
        banks = [pblk[n] for n in pblk if n.startswith(f'vmb_{q}')]
        bc = (sum((b[0] + b[2]) / 2 for b in banks) / len(banks), sum((b[1] + b[3]) / 2 for b in banks) / len(banks))
        placed = {}
        obs = [r for n, r in obst.items()] + [r for n, r in pblk.items() if n != f'coll_{q}' and
                                                                  not (abs(r[0] - C[0]) < 1 and abs(r[1] - C[1]) < 1)]

        def ok(r):
            if r[0] < qx[0] or r[2] > qx[1] or r[1] < qy[0] or r[3] > qy[1]:
                return False
            return all(gap(r, o) >= 20.0 for o in obs + list(placed.values()))

        def cands(anchor, sz):
            """positions abutting anchor at CLR on each face, scanned along the face"""
            x0, y0, x1, y1 = anchor
            out = []
            for k in range(int((x1 - x0 + sz) / STEP) + 1):
                x = x0 - sz + k * STEP
                out += [(x, y1 + CLR, x + sz, y1 + CLR + sz), (x, y0 - CLR - sz, x + sz, y0 - CLR)]
            for k in range(int((y1 - y0 + sz) / STEP) + 1):
                y = y0 - sz + k * STEP
                out += [(x1 + CLR, y, x1 + CLR + sz, y + sz), (x0 - CLR - sz, y, x0 - CLR, y + sz)]
            return [tuple(round(v, 3) for v in r) for r in out]

        for name, cell, sz, kind, kit in NEW:
            best = None
            anchors = [C] + ([placed['collgl']] if name.startswith('collks') else []) +                       ([placed['collgi']] if name in ('collgl', 'collb') else []) + \
                      ([placed['collgl']] if name == 'collb' and 'collgl' in placed else [])
            for anc in anchors:
                for r in cands(anc, sz):
                    if not ok(r):
                        continue
                    if name.startswith('collks'):
                        pb = [pblk[f'vmb_{q}{2 * int(name[-1]) + j}'] for j in (0, 1)]
                        pc = (sum((b[0] + b[2]) / 2 for b in pb) / 2, sum((b[1] + b[3]) / 2 for b in pb) / 2)
                        cost = cdist(r, C) + cdist(r, placed['collgl']) +                             0.25 * (abs((r[0] + r[2]) / 2 - pc[0]) + abs((r[1] + r[3]) / 2 - pc[1]))
                    elif name == 'collrs':
                        cost = cdist(r, C) + 0.25 * (abs((r[0] + r[2]) / 2 - bc[0]) + abs((r[1] + r[3]) / 2 - bc[1]))
                    elif name == 'collgi':
                        cost = cdist(r, C)
                    else:
                        cost = cdist(r, placed['collgi']) + (cdist(r, placed['collgl']) if name == 'collb' else 0)
                    if best is None or cost < best[0]:
                        best = (cost, r)
            if best is None:
                raise SystemExit(f'{name}_{q}: no free abutting position')
            placed[name] = best[1]
        for name, cell, sz, kind, kit in NEW:
            r = placed[name]
            g['slots'].append(dict(name=f'{name}_{q}', cell=cell, kind=kind, parent='die', outline=dict(w=sz, h=sz),
                                   origin=dict(x=r[0], y=r[1], orient='R0'),
                                   clock_entry=dict(pin='clk', face='N', layer='M5', offset=round(sz / 2, 3)),
                                   pg_layer='M7', strap_layer='M8', signal_max_layer='M7', layer_cap='M5',
                                   io_budget=dict(in_delay_frac=0.2, out_delay_frac=0.2), version=1,
                                   grant='d4g_gen2_collq_1018', rtl_owner='HBM-COLLQ / HBM-RTL4',
                                   kit=f'physical/ref_tile/{kit}' if kit else None, pins=[], pin_status='FACES_ONLY',
                                   notes=f'H-D4G GEN2 10-18: COLLQ / ring-B slot abutting coll_{q} at {CLR} um '
                                         '(tools/hbm_die_v16/d4g_gen2_grants_collq.py)'))
        rep[q] = {k: dict(origin=[placed[k][0], placed[k][1]], size=placed[k][2] - placed[k][0],
                          gap_to_coll=round(gap(placed[k], C), 1)) for k in placed}
        rep[q]['coll'] = list(C)
    # check: 0 overlaps / clearance >= 20 among all slots
    S = [(s['name'], rect(s)) for s in g['slots'] if s['kind'] != 'die' and s.get('origin') and s.get('outline')]
    newn = {f'{k}_{q}' for k, *_ in NEW for q in Q}
    bad = [(a_, b_, round(gap(ra, rb), 1)) for i, (a_, ra) in enumerate(S) for b_, rb in S[i + 1:]
           if (a_ in newn or b_ in newn) and gap(ra, rb) < 20.0]
    rep['clearance_violations'] = bad
    Path(a.grants).write_text(json.dumps(g, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    for q in Q:
        print(q, {k: v['origin'] for k, v in rep[q].items() if k != 'coll'})
    print('clearance_violations', len(bad))
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
