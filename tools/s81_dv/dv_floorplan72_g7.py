#!/usr/bin/env python3
"""S81 selected72 die G7 floorplan (S81-LINK5B L5B-G7 10-21): G5 construction (dv_floorplan72_g4.py --wb-rows 2 3) + the
G6 leftovers that need slots, all by ENLARGING / MOVING (no slot shrinks):

  * COORD decision 4.4 (L2 index readers beside their HBM controllers): the 8 readers idx_00..07 leave the north top row
    for the two south pockets beside the HBM PHY.  To make the pockets 2 reader rows tall, every block above the ctrl row
    (service group, slices, end parents, top row) moves up DY = 907.2 and the die grows 25200 -> 25952.4 (reticle 26000;
    the old top row had 154.8 spare).  W pocket (x >= column-B 8307.36, freed by G5's --wb-rows 2 3): readers 00..03 in
    2 columns x 2 rows; E pocket: the E column-B copy-A/B reserves link_1_4/1_5 move to rows 2/3 (mirror of G5), readers
    04..07 in 2 columns x 2 rows from x = PHY right edge + 86.4.  Readers for the far controllers sit in the column
    nearer the PHY; the iq/is chain stays neighbour to neighbour inside each pocket.
  * S81-RTLGAP/eng ccefda9d5 (+ S81-COLLECT ra512 lookup): 16 inline reader taps etap_00..15 (216 x 648, one row in the
    new 907.2 strip between the ctrl row and the service group, y 1976.2; W taps 00..07 from x 11677, E taps 08..15
    ending at the PHY right edge) -- each reader <-> ctrl lane becomes two registered segments of <= ~3.3 mm; Engram
    cluster eng_00 1296 x 1209.6 in the top row above s_6S (column-6 rung partner, f_ks from s_7N ~5 mm).
  * S81-RTLGAP/l20 7cac7629d: bk_sel (+10 x ot_sram_1r1w_1024x256 174.7 x 70.5 = 0.123 mm2 TX store) slot 907.2 x 3283.2
    -> 907.2 x 4190.4 (+907.2 up into the space the die growth opened; the G6 slot already had the area).
  * iqf moves into the W pocket (free column-B column, beside irg_00..03): iq_qf 98 -> few stations, iq_src s_3S -> pocket
    (one 513-b query per job either way; total query path shorter than leaving iqf in the top row).
Everything else = G5 placement shifted as above; street >= 86.4 between every pair and to the die edge is asserted.
"""
import argparse, json
from pathlib import Path
from dv_floorplan72_g4 import construct, SERDES

DY = 907.2
H7 = 25952.4
GAP = 86.4
TAP = (216.0, 648.0)
ENG = (1296.0, 1209.6)
BKSEL_H = 3283.2 + DY
SHIFT = ('svc_full_', 'slice_', 'end_parent_', 'gunit_00', 'seqhost_00', 'bk_col_00', 'iqf_00')
TAP_Y = 1976.2


def construct7(template, W=32648.0, H=H7):
    d = construct(template, W, 25200.0, wb_rows=(2, 3))
    bs = d['best']['blocks']; by = {b['name']: b for b in bs}
    for b in bs:
        if b['name'].startswith(SHIFT):
            b['y'] = round(b['y'] + DY, 6)
    sw_, sh_ = SERDES; lp = sh_ + GAP; ly0 = 86.4
    for r in d['reserves']:                       # E column-B copy-A/B reserves -> rows 2/3 (mirror of G5 W)
        j = int(r['name'][-1]); r['y'] = round(ly0 + (j - 2) * lp, 6)
        r['scope'] += ' (G7: rows 2/3, frees the E pocket)'
    phy = by['phy_hbm']; ctrl_top = max(b['y'] + b['h'] for b in bs if b['name'].startswith('ctrl_'))
    colB_W = d['serdes']['column_B_x'][0]
    iw, ih = by['idx_00']['w'], by['idx_00']['h']
    rows = (86.4, 86.4 + ih + GAP)                # row 1 (PHY level), row 2
    wcol = (colB_W + (iw + GAP), colB_W + 2 * (iw + GAP))       # W: column nearer the PHY = wcol[1]
    ex0 = phy['x'] + phy['w'] + GAP
    ecol = (ex0, ex0 + iw + GAP)                  # E: column nearer the PHY = ecol[0]
    place = {'idx_00': (wcol[0], rows[1]), 'idx_01': (wcol[0], rows[0]), 'idx_02': (wcol[1], rows[0]), 'idx_03': (wcol[1], rows[1]),
             'idx_04': (ecol[0], rows[1]), 'idx_05': (ecol[0], rows[0]), 'idx_06': (ecol[1], rows[0]), 'idx_07': (ecol[1], rows[1])}
    for n, (x, y) in place.items():
        by[n].update(x=round(x, 6), y=round(y, 6),
                     scope='G7 L2 index reader beside its HBM controllers (south pocket; COORD decision 4.4)')
    by['iqf_00'].update(x=round(colB_W, 6), y=86.4, scope='G7 iqf in the W pocket beside the reader chain head irg_00')
    by['bk_sel_00']['h'] = BKSEL_H
    by['bk_sel_00']['scope'] = 'G7 bk_sel_vmtx (L20 split: +10 x ot_sram_1r1w_1024x256 TX/IDX store) 907.2 x 4190.4'
    tw, th = TAP; pitch = tw + GAP
    wx0 = wcol[1] + iw + GAP
    ex_end = phy['x'] + phy['w']
    for k in range(16):
        x = wx0 + k * pitch if k < 8 else ex_end - tw - (15 - k) * pitch
        bs.append(dict(name=f'etap_{k:02}', x=round(x, 6), y=TAP_Y, w=tw, h=th, kind='unit',
                       scope=f'G7 Engram reader tap (dsdv_eng_tap{"_w" if k == 0 else ""} sid {k}) inline on irg_{k // 2:02} <-> ctrl_{k:02}'))
    s6 = by['slice_11']; top = by['gunit_00']['y']
    bs.append(dict(name='eng_00', x=s6['x'], y=top, w=ENG[0], h=ENG[1], kind='unit',
                   scope='G7 Engram row-read cluster dsdv_eng_rr (S81-RTLGAP/eng, ra512 lookup) above s_6S (column-6 rung)'))
    allr = bs + d['reserves']
    for b in allr:
        assert min(b['x'], b['y']) >= GAP - 1e-6 and b['x'] + b['w'] <= W - GAP + 1e-6 and b['y'] + b['h'] <= H - GAP + 1e-6, b
    for i, b in enumerate(allr):
        for c in allr[i + 1:]:
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            assert sep >= GAP - 0.25, (b['name'], c['name'], round(sep, 3))
    assert TAP_Y >= ctrl_top + GAP - 1e-6
    svc_bot = min(b['y'] for b in bs if b['name'].startswith('svc_full_'))
    assert TAP_Y + th <= svc_bot - GAP + 1e-6 and rows[1] + ih <= svc_bot - GAP + 1e-6, (svc_bot,)
    d['die'] = [W, H]
    d['scope'] = 'OWNER72 SELECTED IMPLEMENTATION G7 CONSTRUCTION (G5 + readers beside ctrls, Engram taps/cluster, bk_sel L20), not routed closure'
    d['g7_changes'] = dict(shift_up_um=DY, die=[W, H], readers={n: [round(x, 3), round(y, 3)] for n, (x, y) in place.items()},
                           e_reserves_rows=[2, 3], taps=dict(slot=list(TAP), y=TAP_Y, w_first_x=round(wx0, 3), e_last_right=ex_end),
                           eng=dict(slot=list(ENG), above='slice_11 (s_6S)'), bk_sel_h=BKSEL_H, iqf='W pocket column B (x 8307.36, y 86.4)')
    return d


def main():
    a = argparse.ArgumentParser(); a.add_argument('template'); a.add_argument('out'); v = a.parse_args()
    d = construct7(json.load(open(v.template))); Path(v.out).write_text(json.dumps(d, indent=1))
    print('SELECTED72_G7_CONSTRUCTED', len(d['best']['blocks']), 'reserves', len(d['reserves']), 'die', d['die'])


if __name__ == '__main__':
    main()
