#!/usr/bin/env python3
"""S81 selected72 die G8 floorplan (S81-G8 10-21): the G7 construction (dv_floorplan72_g7.py) on the full reticle.

OWNER 10-21: every release die may use the full 33 x 26 mm reticle; the 0.5 mm margin is dropped; a ~0.1 mm seal ring
stays inside the outline.  S81 keeps 72 frames and the qualified 241-stage map (483869b91): frame count, frame slots and
the map are unchanged.  The extra room is spent on closure margin only (the die does not get denser):

  * die 32648 x 25952.4 -> 33000 x 26000; every block >= SEAL (100) from the outline (G7: 86.4 street, no seal ring).
    G7 is constructed at W7 = 33000 - 2 x (SEAL - 86.4) and translated by (SEAL - 86.4) in x and y, so every
    edge-referenced column (frames, SerDes A/B) keeps its G7 neighbours and the centre region gains 324.8 um.
  * slice row (slices s_*, MU end parents, top row eng/gunit/seqhost/bk_col): every street of the row -- frame column
    h10_10 | slice c0 | .. | c5 | end-parent col 0 | col 1 -- widens 86.4 -> 172.8 (relay channels for <= 405 um
    registered hops + the landing rings at every region crossing).  Top-row blocks move with the slice column under them.
  * service/attention group (16 x svc_full 1728 x 3801.6, G4 svc_full lineage): column streets 86.4 -> 129.6; the group
    stays centred under the ctrl row; the svc -> slice street gets the whole 20.4 um of vertical room (86.4 -> 106.8).
  * end slots: all four MU end parents 2851.2 x 6825.6 (s_0S lepw_mu 2505.6 -> 2851.2, = the lepw_mab/lepe slots; the
    end-parent column pitch was already 2851.2, so no neighbour moves); per-region clock trees: bind overlay
    release72/apply_ep_clock_g8.py gives each of the 12 end-parent clock ports its own die-top clock input.
  * Engram eng_00 (dsdv_eng_rr) keeps its slot above s_6S; its streets to s_6S/end-parent col 0/gunit widen with the row.
  * SerDes: 10 real slots (W 6: link_0_0..5, E 4: link_1_0..3) + the E column-B copy-A/B pair reserve link_1_4/1_5
    (blockage) exactly as G7.
Vertical room is the binding direction: 26000 - 2 x 100 = 25800 vs G7's 25779.6 of content; no slot shrinks anywhere.
"""
import argparse, json
from pathlib import Path
from dv_floorplan72_g7 import construct7, H7

W8, H8 = 33000.0, 26000.0
SEAL = 100.0
GAP = 86.4
SL_STREET = 172.8          # slice-row streets (G7 86.4)
SVC_STREET = 129.6         # service-group column streets (G7 86.4)
EP_W = 2851.2
SLICE_W = 1252.8


def construct8(template, W=W8, H=H8, seal=SEAL):
    off = seal - GAP
    W7 = W - 2 * off
    d = construct7(template, W7, H7)
    bs = d['best']['blocks']; by = {b['name']: b for b in bs}; res = d['reserves']
    for b in bs + res:
        b['x'] = round(b['x'] + off, 6); b['y'] = round(b['y'] + off, 6)
    # --- vertical: the 20.4 um spare -> svc -> slice street (everything from the slice row up moves up)
    dy = round((H - seal) - max(b['y'] + b['h'] for b in bs), 6)
    assert dy >= 0, dy
    svc_top = max(b['y'] + b['h'] for b in bs if b['name'].startswith('svc_full_'))
    upper = [b for b in bs if b['name'].startswith(('slice_', 'end_parent_', 'gunit_00', 'seqhost_00', 'bk_col_00', 'eng_00'))]
    for b in upper:
        assert b['y'] > svc_top, b['name']
        b['y'] = round(b['y'] + dy, 6)
    # --- slice row streets 86.4 -> 172.8 (piecewise x map over the column left edges, frame column h10_10 first)
    cols = sorted({round(by[f'slice_{i:02}']['x'], 6) for i in range(12)} |
                  {round(by[f'end_parent_{i}']['x'], 6) for i in range(4)})
    assert len(cols) == 8, cols
    dS = SL_STREET - GAP

    def shift_x(x):                        # number of street boundaries left of x (h10_10 | c0 boundary counts for every column)
        return sum(1 for c in cols if c <= x + 1e-6) * dS
    for b in upper:
        cx = b['x'] if not b['name'].startswith(('gunit', 'seqhost', 'bk_col', 'eng')) else b['x'] + 1e-3
        b['x'] = round(b['x'] + shift_x(cx), 6)
    for i in range(4):
        by[f'end_parent_{i}']['w'] = EP_W
        by[f'end_parent_{i}']['scope'] = by[f'end_parent_{i}'].get('scope', '') + ' | G8: 2851.2 end slot, per-region clock trees (12 die-top roots)'
    # --- service group column streets 86.4 -> 129.6, group re-centred under the ctrl row
    svc = [by[f'svc_full_{i}'] for i in range(16)]
    gw = 8 * svc[0]['w'] + 7 * SVC_STREET
    gx = (W - gw) / 2
    for i, b in enumerate(svc):
        b['x'] = round(gx + (i // 2) * (b['w'] + SVC_STREET), 6)
    ctrl = [b for b in bs if b['name'].startswith('ctrl_')]
    ccx = (min(b['x'] for b in ctrl) + max(b['x'] + b['w'] for b in ctrl)) / 2
    assert abs(ccx - W / 2) < 1.0, (ccx, W / 2)
    # --- checks: seal ring, >= 86.4 between every pair, the widened streets really are wide
    allr = bs + res
    for b in allr:
        assert min(b['x'], b['y']) >= seal - 1e-6 and b['x'] + b['w'] <= W - seal + 1e-6 and b['y'] + b['h'] <= H - seal + 1e-6, b
    for i, b in enumerate(allr):
        for c in allr[i + 1:]:
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            assert sep >= GAP - 0.25, (b['name'], c['name'], round(sep, 3))
    row = sorted([by[f'slice_{i:02}'] for i in range(0, 12, 2)] + [by['end_parent_0'], by['end_parent_2']], key=lambda b: b['x'])
    streets = [round(row[k + 1]['x'] - (row[k]['x'] + row[k]['w']), 3) for k in range(len(row) - 1)]
    h10w = by['h10_10']; streets.insert(0, round(row[0]['x'] - (h10w['x'] + h10w['w']), 3))
    assert min(streets) >= SL_STREET - 0.25, streets
    e_right = row[-1]['x'] + row[-1]['w']; e_gap = round(by['h10_11']['x'] - e_right, 3)
    assert e_gap >= GAP - 0.25, e_gap
    svc_streets = sorted({round(svc[2 * (k + 1)]['x'] - (svc[2 * k]['x'] + svc[2 * k]['w']), 3) for k in range(7)})
    side = (round(svc[0]['x'] - (d['serdes']['column_B_x'][0] + off + 518.4), 3),
            round((d['serdes']['column_B_x'][1] + off) - (svc[-1]['x'] + svc[-1]['w']), 3))
    slice_bot = min(b['y'] for b in upper if b['name'].startswith('slice_'))
    svc_slice = round(slice_bot - svc_top, 3)
    d['die'] = [W, H]
    d['scope'] = ('OWNER72 SELECTED IMPLEMENTATION G8 CONSTRUCTION (G7 + full reticle 33 x 26 mm, 0.1 mm seal ring; extra room '
                  '= wider streets / end slots, not density), not routed closure')
    d['g8_changes'] = dict(
        die=[W, H], seal_ring_um=seal, g7_translate_um=off, g7_constructed_at=[W7, H7],
        slice_row_streets_um=streets, slice_row_east_street_um=e_gap, svc_column_streets_um=svc_streets,
        svc_side_streets_um=list(side), svc_to_slice_street_um=svc_slice, end_parent_w=EP_W,
        unchanged=['72 frames (60 h9 + 12 h10) at G7 slots (+translate)', 'SerDes 10 real + 2 copy-A/B reserves',
                   'ctrl row / PHY / taps / readers / iqf / bk_sel (+translate)', 'qualified 241-stage map 483869b91'])
    return d


def main():
    a = argparse.ArgumentParser(); a.add_argument('template'); a.add_argument('out'); v = a.parse_args()
    d = construct8(json.load(open(v.template))); Path(v.out).write_text(json.dumps(d, indent=1))
    print('SELECTED72_G8_CONSTRUCTED', len(d['best']['blocks']), 'reserves', len(d['reserves']), 'die', d['die'],
          json.dumps({k: d['g8_changes'][k] for k in ('slice_row_streets_um', 'slice_row_east_street_um', 'svc_column_streets_um',
                                                       'svc_side_streets_um', 'svc_to_slice_street_um')}))


if __name__ == '__main__':
    main()
