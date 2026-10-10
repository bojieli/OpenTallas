#!/usr/bin/env python3
"""hbm-phys-1010 [idx] (lead decision 2026-10-10, R25GQ): relay plan for the attention-root -> SU lane die buses that
replace the interim hfd_index_q b0..b5 transport stack (dropped from R25GQ).

Per quadrant q, R25GQ row r (r = 0: at_<q>_03_hi, r = 1: at_<q>_13_hi; R25GP rows 0,1 -> row 0 and 2,3 -> row 1, the same
lane split the index bands' merge made) drives hb_su_<q>.a lane r (bits 529r .. 529r+528) through a chain of
hfd_att_su_relay stations (43.2 x 108 um, 'i' on the W face / 'o' on the E face at the attention half's 'o' pin rows,
y 2.412 .. 103.788).  Path: the root's 'o' pin row -> a JOG um stub -> a vertical leg to the lane row on the SU face
(straight when the root row already faces the SU) -> the SU face.  The first relay abuts the root pin, the last abuts the
SU face, every die segment (relay out pin -> next relay in pin, Manhattan) <= STEP um (the SS wire reach is 504 um).
Every relay rectangle and wire leg is checked against the R25GQ instances (index stack removed).

usage: hbm_att_su_relay.py [--fp results/arch/r25gq_refloorplan_20261010/floorplan.json] [--out PLAN.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RW, RH = 43.2, 108.0                 # relay outline (um)
PIN_LO, PIN_HI = 2.412, 103.788      # 'o' / 'i' pin rows from the bottom edge (R0), = hfd_attn_half_hi 'o'
STEP = 480.0                         # max die segment (out pin -> next in pin), < the 504 um SS reach
JOG = 100.0                          # stub from the root face before the vertical leg
MARGIN = 20.0                        # lane row clearance from the SU face ends


def plan(fp: dict) -> dict:
    by = {i['name']: i for i in fp['instances']}
    obst = [i for i in fp['instances'] if not i['master'].startswith('hfd_index_q')]
    buses, relays = [], []
    for q in ('SW', 'SE', 'NW', 'NE'):
        su = by[f'hb_su_{q}']
        # lane r <- row by distance from the die centre (far row -> lane 0, the straight run; near row -> lane 1, the
        # jog to the SU face end nearest the centre).  Rows are numbered bottom-up in both halves (R25GP and R25GQ), so
        # this is at_<S>_03 / at_<N>_13 -> lane 0: the only assignment where ONE SU master (MX in N) gets the same
        # master-local lane rows in all four quadrants without the two buses crossing.
        yc = fp['die']['H'] / 2
        # the row's tile-chain root (the R25GP chain ta_at_*: W quadrants run c0 -> c3, root c3; E quadrants run
        # c3 -> c0, root c0), which must be the column next to the SU (fp places the E grid name-mirrored)
        rc = '3' if q[1] == 'W' else '0'
        rows = sorted(('0' + rc, '1' + rc), key=lambda rw: -abs(by[f'at_{q}_{rw}_hi']['y'] - yc))
        for r, row in enumerate(rows):
            at = by[f'at_{q}_{row}_hi']
            assert abs((at['x'] + at['w'] / 2) - (su['x'] + su['w'] / 2)) == min(
                abs((i['x'] + i['w'] / 2) - (su['x'] + su['w'] / 2)) for i in fp['instances']
                if i['name'].startswith(f'at_{q}_{row[0]}') and i['name'].endswith('_hi')), \
                f'{at["name"]} (chain root) is not the attention column next to hb_su_{q}: place the E grid name-mirrored'
            east = at['x'] < su['x']                       # travel direction
            mir_y = at['orient'] in ('MX', 'R180')
            plo = at['y'] + (at['h'] - PIN_HI if mir_y else PIN_LO)
            x0 = at['x'] + at['w'] if east else at['x']    # root pin face
            x1 = su['x'] if east else su['x'] + su['w']    # SU face
            lo, hi = su['y'] + MARGIN, su['y'] + su['h'] - MARGIN - (PIN_HI - PIN_LO)
            yt = min(max(plo, lo), hi)                      # lane pin row on the SU face
            sx = 1 if east else -1
            # polyline of the pin row (x, y): root face -> stub -> leg -> SU face
            pts = [(x0, plo)] + ([(x0 + sx * JOG, plo), (x0 + sx * JOG, yt)] if abs(yt - plo) > 1e-6 else []) + [(x1, yt)]
            segs = list(zip(pts, pts[1:]))
            L = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in segs)
            # relays at path distances s_k (relay occupies s_k .. s_k + RW along x legs); first at 0, last at L - RW
            n = max(2, math.ceil((L - RW) / (STEP + RW)) + 1)
            d = (L - RW) / (n - 1)

            def at_s(s):
                for a, b in segs:
                    ln = abs(b[0] - a[0]) + abs(b[1] - a[1])
                    if s <= ln + 1e-9:
                        f = s / ln if ln else 0.0
                        return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
                    s -= ln
                return pts[-1]
            chain = []
            for k in range(n):
                s = k * d
                px, py = at_s(s)
                if k == n - 1:
                    px, py = x1 - sx * RW, yt
                rx = px if east else px - RW
                ry = py - (RH - PIN_HI if mir_y else PIN_LO)
                o = {(True, False): 'R0', (False, False): 'MY', (True, True): 'MX', (False, True): 'R180'}[(east, mir_y)]
                chain.append(dict(name=f'rly_{q}_{r}_{k}', master='hfd_att_su_relay', x=round(rx, 3), y=round(ry, 3),
                                  w=RW, h=RH, orient=o))
            # segment lengths (out pin of k -> in pin of k+1, Manhattan)
            seg_len = []
            for a, b in zip(chain, chain[1:]):
                ax = a['x'] + RW if east else a['x']
                bx = b['x'] if east else b['x'] + RW
                seg_len.append(round(abs(bx - ax) + abs(b['y'] - a['y']), 3))
            first = abs((chain[0]['x'] if east else chain[0]['x'] + RW) - x0)
            last = abs((chain[-1]['x'] + RW if east else chain[-1]['x']) - x1)
            assert max(seg_len) <= STEP + 1e-6 and first < 1e-6 and last < 1e-6, (q, r, seg_len, first, last)
            hits = []
            for c in chain:
                for o_ in obst:
                    if (c['x'] < o_['x'] + o_['w'] - 1e-6 and o_['x'] < c['x'] + RW - 1e-6 and
                            c['y'] < o_['y'] + o_['h'] - 1e-6 and o_['y'] < c['y'] + RH - 1e-6):
                        hits.append((c['name'], o_['name']))
            for a, b in segs:                              # wire legs (pin band) against the instances
                xa, xb = sorted((a[0], b[0])); ya, yb = sorted((a[1], b[1]))
                yb += PIN_HI - PIN_LO
                for o_ in obst:
                    if o_['name'] in (at['name'], su['name']):
                        continue
                    if xa < o_['x'] + o_['w'] - 1e-6 and o_['x'] < xb - 1e-6 and ya < o_['y'] + o_['h'] - 1e-6 and \
                            o_['y'] < yb - 1e-6:
                        hits.append((f'leg {a}->{b}', o_['name']))
            assert not hits, (q, r, hits[:6])
            relays += chain
            buses.append(dict(bus=f'tr_{q}{r}', bits=529, src=f"{at['name']}.o", dst=f"{su['name']}.a[{529*r+528}:{529*r}]",
                              path_um=round(L, 3), relays=n, segments_um=seg_len, max_segment_um=max(seg_len),
                              su_lane_pin_row_um=dict(abs_y=round(yt, 3), su_local_y=round(yt - su['y'], 3), master_local_y=round(
                                                          (su['h'] - (yt - su['y']) - (PIN_HI - PIN_LO))
                                                          if su['orient'] in ('MX', 'R180') else yt - su['y'], 3),
                                                      face='W' if east else 'E'),
                              added_cycles=n))
    old = json.loads((ROOT / 'physical/hbm_accel_die_views/index_q/split_stages.json').read_text())['regs']['rows']
    return dict(schema='opentallas.hbm_att_su_relay_plan.v1', generator='tools/hbm_att_su_relay.py',
                floorplan=fp.get('preset'), master=dict(name='hfd_att_su_relay', w_um=RW, h_um=RH, bits=529,
                                                        pins=dict(i='W M4 y 2.412..103.788', o='E M4 y 2.412..103.788',
                                                                  ck='S', rst='S')),
                rule=dict(step_um=STEP, jog_um=JOG, ends='first relay abuts the root o pin, last abuts the SU a face'),
                removed=sorted(i['name'] for i in fp['instances'] if i['master'].startswith('hfd_index_q')),
                buses=buses, relays=relays, relay_count=len(relays),
                latency=dict(new_regs_per_row={b['bus']: b['relays'] for b in buses},
                             old_index_band_regs_per_row=old,
                             note='old = index band chain registers (a0/a1 -> SU lane 0, a2/a3 -> lane 1) before the '
                                  'die wire stages on tr_* / ao_*; new = the relays (the whole die path)'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fp', type=Path, default=ROOT / 'results/arch/r25gq_refloorplan_20261010/floorplan.json')
    ap.add_argument('--out', type=Path, default=ROOT / 'physical/hbm_accel_die_views/att_su_relay/relays_r25gq.json')
    a = ap.parse_args()
    p = plan(json.loads(a.fp.read_text()))
    a.out.write_text(json.dumps(p, indent=1) + '\n')
    print(json.dumps(dict(relays=p['relay_count'], per_bus={b['bus']: [b['relays'], b['max_segment_um'],
                                                                     b['su_lane_pin_row_um']['master_local_y'], b['src']]
                                                             for b in p['buses']})))


if __name__ == '__main__':
    main()
