#!/usr/bin/env python3
"""S81 selected72 die G4 floorplan (S81-LINK5 L5-G4 10-21): G3 construction (dv_floorplan72_g3.py) + the owner-approved
5th lane pair (10-21 06:00) on s_0N:
  * W side (side 0) column B: link_0_4 / link_0_5 become REAL SerDes slots 518.4 x 3844.8 (master ot_pdie_serdes, plan
    instances lk_WN2 / lk_WN3, pins + links like link_0_0..3).  E side link_1_4 / link_1_5 stay blockage reserves
    (copy-A/B pair reserve).
  * end_parent_1 (= s_0N) becomes the copy-A/B parent ot_s81sl_slice_lepw_mab_mu_72: 2505.6 -> 2851.2 wide (s_0S stays
    2505.6); end-parent column 0 pitch follows the widest member, so column 1 and every E-side / centre block move by
    +345.6 / +172.8: die width grows 32302.4 -> 32648.0 (reticle 33 x 26 mm), every street and channel kept (no squeeze).

G3 docstring follows.
S81 selected72 die G3 floorplan (LEAD-S81-G3 10-21): G2 construction (dv_floorplan72.py) with the slot errors fixed.

Changes vs G2 (placement_r3), all by enlarging / moving, never by shrinking a slot:
  * SerDes: real column ot_pdie_serdes (s81lk_serdes_col_lp7a/b) is 518.4 x 3844.8, not the 259.2 x 3596.4 PHY-bb slot.
    Per side: column A = the 4 real link_<s>_0..3 slots, rows from y 86.4 at pitch 3844.8 + 86.4; column B beside it =
    2 reserved slots link_<s>_4/5 (5th lane pair + copy-A/B pair; owner has not decided the 5th link -> blockage only,
    no master, no pins).  6 SerDes slots per side.
  * Die width grows 32000 -> W (default 32302.4) so both reserve columns + the 2x8 service group keep >= 86.4 streets;
    die height grows 25000 -> H (default 25200) for the taller service group, idx readers and the moved ctrl row.
    Reticle 26 x 33 mm.  Centre-referenced fixed blocks (phy_hbm, ctrl row) shift by dW/2 to stay under the services.
  * Service slot 1728 x 3801.6 (x16; S81-SVCSEQ-1021: svc_rs 1555.2 + 86.4 landed + attw NT1 2160); ctrl row moved up
    43.2, service group bottom = ctrl top + 86.4 street.
  * E-end MU72 parents (end_parent_2/3 = s_7S lepe_nh_mu_72 / s_7N lepe_mu_72): 2505.6 -> 2851.2 wide (lep MY at the
    slice ri_e/ro_e height, both lanes beside the lep, FAM-S81-LEPENH); W-end lepw parents stay 2505.6.
  * idx readers 1036.8 x 1209.6 (S81-IDXRD-1021 --idxrd 4 reader); seqhost 475.2 x 993.6 (seq_host_h / s10h lk,
    S81-SEQHP-1021; the larger of the two candidates, so either closes in place).
Every other block keeps its G2 envelope and relative position; relay channels are the >= 86.4 streets between blocks
(dv_route72 plans stations <= 350 um along them).
"""
import argparse, copy, json
from pathlib import Path

SERDES = (518.4, 3844.8)
SVC = (1728.0, 3801.6)
EP_W = {0: 2505.6, 1: 2851.2}          # end-parent column 0 = lepw (s_0S/s_0N), column 1 = lepe (s_7S/s_7N)
EP_W_INST = {0: 2505.6, 1: 2851.2, 2: 2851.2, 3: 2851.2}   # G4: end_parent_1 = s_0N -> lepw_mab_mu_72 (copy-A/B) 2851.2
EP_COL_W = {0: max(EP_W_INST[0], EP_W_INST[1]), 1: max(EP_W_INST[2], EP_W_INST[3])}
REAL_W_LINKS = (4, 5)                  # G4: W column B slots that are real SerDes (5th lane pair); E column B stays reserve
IDX = (1036.8, 1209.6)
SEQHOST = (475.2, 993.6)
CTRL_UP = 43.2


def construct(template, W=32648.0, H=25200.0, wb_rows=(0, 1)):
    d = copy.deepcopy(template); allb = {b['name']: b for b in d['rectangles'] + d['fixed']}; bs = []
    for j in REAL_W_LINKS:                 # G4: new real W SerDes slots (template has only link_<s>_0..3)
        allb[f'link_0_{j}'] = dict(copy.deepcopy(allb['link_0_0']), name=f'link_0_{j}')
    dW = W - 32000.0; gap = 86.4

    def put(name, x, y, w=None, h=None, **kw):
        b = copy.deepcopy(allb[name]); b.update(x=round(x, 6), y=round(y, 6))
        if w is not None: b['w'] = w
        if h is not None: b['h'] = h
        b.update(kw); bs.append(b); return b
    fw = 1436.832; pitch = fw + gap; h9 = 3369.6; h10 = 3672.; n9 = n10 = 0
    for side in range(2):
        for c in range(5):
            x = 86.4 + c * pitch; x = x if side == 0 else W - x - fw; y = 86.4
            for row in range(7):
                if row == 3: name = f'h10_{n10:02}'; n10 += 1; h = h10
                else: name = f'h9_{n9:02}'; n9 += 1; h = h9
                put(name, x, y); y += h + gap
    xextra = 86.4 + 5 * pitch
    # SerDes column A (4 real slots) and column B (2 reserves) per side
    sw_, sh_ = SERDES; lp = sh_ + gap; ly0 = 86.4
    colA = {0: xextra, 1: W - xextra - sw_}
    colB = {0: xextra + sw_ + gap, 1: W - xextra - sw_ - gap - sw_}
    link_top = ly0 + 4 * sh_ + 3 * gap
    extra_y = 2000. + 4 * 3596.4 + 3 * gap + 172.8          # unchanged G2 h10 extra row (above the taller column A)
    assert extra_y >= link_top + 172.8 - 1e-6, (extra_y, link_top)
    for side in range(2):
        xe = xextra if side == 0 else W - xextra - fw
        put(f'h10_{n10:02}', xe, extra_y); n10 += 1
        for j in range(4):
            put(f'link_{side}_{j}', colA[side], ly0 + j * lp, sw_, sh_,
                scope='G3 real SerDes column slot (s81lk_serdes_col_lp7a/b 518.4 x 3844.8)')
    # G5 (L5B-G4 10-21, --wb-rows 2 3): W column B real slots move up beside lk_WN0/1 (column A rows 2/3 = link_0_2/0_3),
    # the rows nearest s_0N -> the s_0N <-> lk_WN2/3 links shorten ~8 mm (y 7948.8..15724.8 in column B is free).
    for j, r in zip(REAL_W_LINKS, wb_rows):
        put(f'link_0_{j}', colB[0], ly0 + r * lp, sw_, sh_,
            scope='G4 real SerDes column-B slot (5th lane pair, s_0N pair B; ot_pdie_serdes 518.4 x 3844.8)')
    assert (n9, n10) == (60, 12)
    # ctrl row (fixed, centre-referenced) up 43.2 and shifted dW/2; service group bottom = ctrl top + 86.4
    ctrl_top = None
    for b in d['fixed']:
        if b['name'].startswith('ctrl_'):
            nb = put(b['name'], b['x'] + dW / 2, b['y'] + CTRL_UP); ctrl_top = max(ctrl_top or 0, nb['y'] + nb['h'])
        elif b['name'] == 'phy_hbm':
            put(b['name'], b['x'] + dW / 2, b['y'])
    svw, svh = SVC; gw = 8 * svw + 7 * gap; gx = (W - gw) / 2; gy = round(ctrl_top + gap, 6)
    for i in range(16):
        put(f'svc_full_{i}', gx + (i // 2) * (svw + gap), gy + (i % 2) * (svh + gap), svw, svh)
    sx = xextra + fw + gap; sy = gy + 2 * svh + gap + 86.4; vp = 6825.6 + gap
    for i in range(12):
        put(f'slice_{i:02}', sx + (i // 2) * (1252.8 + gap), sy + (i % 2) * vp)
    ex = sx + 6 * (1252.8 + gap)
    for i in range(4):
        col = i // 2; x = ex + (0 if col == 0 else EP_COL_W[0] + gap)
        put(f'end_parent_{i}', x, sy + (i % 2) * vp, EP_W_INST[i], 6825.6,
            scope=('NEW unhardened MU72 assembly ' + ('lepw (lep R0)' if i == 0 else
                   'G4 lepw_mab_mu_72 copy-A/B parent (5th lane pair B: +2 safe8 lanes, 2851.2 wide)' if i == 1 else
                   'lepe G3: lep MY at slice ri_e/ro_e height, lanes beside lep (2851.2 wide)')))
    put('bk_sel_00', xextra, extra_y + h10 + 172.8)
    top = sy + 2 * 6825.6 + gap + 172.8
    for i in range(8):
        put(f'idx_{i:02}', sx + i * (IDX[0] + gap), top, IDX[0], IDX[1])
    xx = sx + 8 * (IDX[0] + gap)
    for name in ('gunit_00', 'seqhost_00', 'bk_col_00', 'iqf_00'):
        b = put(name, xx, top, *(SEQHOST if name == 'seqhost_00' else (None, None)))
        xx += b['w'] + gap
    assert len(bs) == len(allb), (len(bs), len(allb), sorted(set(allb) - {b['name'] for b in bs}))
    res = []
    for side in range(2):
        for j, yy in ((4, ly0), (5, ly0 + lp)):
            if side == 0 and j in REAL_W_LINKS:
                continue
            res.append(dict(name=f'link_{side}_{j}', w=sw_, h=sh_, x=round(colB[side], 6), y=round(yy, 6), kind='reserve',
                            scope='G4 copy-A/B pair reserve (518.4 x 3844.8 SerDes slot, E column B): '
                                  'placement + routing blockage only, no master/pins'))
    allr = bs + res
    assert len({b['name'] for b in allr}) == len(allr)
    for i, b in enumerate(allr):
        assert min(b['x'], b['y']) >= 86.4 - 1e-6 and b['x'] + b['w'] <= W - 86.4 + 1e-6 and b['y'] + b['h'] <= H - 86.4 + 1e-6, b
        for c in allr[i + 1:]:
            # every pair separated by >= one 86.4 street (no squeezing)
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            assert sep >= gap - 0.25, (b['name'], c['name'], round(sep, 3))
    return dict(reserves=res, scope='OWNER72 SELECTED IMPLEMENTATION G4 CONSTRUCTION (G3 + 5th lane pair on s_0N), not routed closure', die=[W, H],
                clearance=gap, best=dict(blocks=bs, unplaced=[], trial=dict(strategy='G3 selected construction', placed=len(bs), unplaced=0)),
                service_group=dict(at=[gx, gy], outline=[gw, 2 * svh + gap], slot=list(SVC), order='even lower/odd upper; original sgN/S/E/W faces'),
                serdes=dict(slot=list(SERDES), column_A_x=colA, column_B_x=colB, real_per_side={0: 6, 1: 4}, reserved_per_side={0: 0, 1: 2}),
                g4_changes=dict(real_w_column_b=[f'link_0_{j}' for j in REAL_W_LINKS], end_parent_w=EP_W_INST,
                                end_parent_1='s_0N -> ot_s81sl_slice_lepw_mab_mu_72', die=[W, H], die_growth_vs_g3_um=round(W - 32302.4, 3)),
                g3_slot_changes=dict(serdes=list(SERDES), svc=list(SVC), ctrl_row_up_um=CTRL_UP, end_parent_w=EP_W, idx=list(IDX),
                                     seqhost=list(SEQHOST), die=[W, H], die_growth_um=[round(dW, 3), round(H - 25000, 3)]),
                obligations=['MU parents actual child/source reassembly (G3 lepe geometry in physical/ref_tile/s81_mu72_assembly)',
                             'service parent source and clocks/reset integration', 'actual pin projection and relay legalization/cycle pricing',
                             'E column B copy-A/B pair reserves are blockages only'])


def main():
    a = argparse.ArgumentParser(); a.add_argument('template'); a.add_argument('out')
    a.add_argument('--die', nargs=2, type=float, default=[32648.0, 25200.0])
    a.add_argument('--wb-rows', nargs=2, type=int, default=[0, 1], help='column-A row index of the two W column-B real slots (G5: 2 3)')
    v = a.parse_args()
    d = construct(json.load(open(v.template)), *v.die, wb_rows=tuple(v.wb_rows)); Path(v.out).write_text(json.dumps(d, indent=1))
    print('SELECTED72_G4_CONSTRUCTED', len(d['best']['blocks']), 'reserves', len(d['reserves']), 'die', d['die'])


if __name__ == '__main__':
    main()
