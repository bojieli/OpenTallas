#!/usr/bin/env python3
"""S81 release head die H1 floorplan (S81-HEAD / HD-FP, 10-21; spec results/arch/s81_head_1021/SPEC.md sections 1, 2, 4).

Parametric construction (tile outline, channels, level counts are arguments, so HD-TILE's fallback outline only re-runs
this script).  Everything is placed by construction, then streets >= 86.4 between every pair and to the die edge are
asserted (no squeezing: the die grows to fit).

Geometry, W -> E:
  W SerDes column A | A' (lep 1296 wide + lane/corridor) | W SerDes column B | B' (lane + 216 corridor) | U-turn channel |
  W tile array (COLS columns, column 0 next to the spine, tiles MY = flowing west) | spo lane | spr lane |
  E tile array (R0 = flowing east) | U-turn channel | E B' | E column B | E A' | E column A
Geometry, S -> N:
  S half (LEVELS_S row pairs; level 0 next to the ctl; out row = the upper row of the pair) | ctl band | N half
  (LEVELS_N row pairs; level 0 next to the ctl; out row = the lower row).
  spo_<H>k sits on the out row of level k (spo lane), spr_<H>k on the return row (spr lane), so spo.oe / spr.iw cross the
  other spine lane where it has no node.  S half spine nodes are MX (i on N, o on S).

Spec reconciliation (recorded in facts.spec_reconciliation): spec v1 section 2 says "13 levels per half" AND "52 chains of
<= 5 tiles a row (253 of 260 slots)" AND die ~13 x 20.5 mm.  13 levels per half with 10-tile row-pair chains is 520 slots
(~40 mm tall, over the 33 mm reticle).  The only construction that meets 260 slots, <= 5 tiles a row, row-pair U-turn chains
and the die target is 13 levels IN TOTAL: N 7 + S 6 levels, 26 chains x 10 slots, 13 spo + 13 spr nodes.  The 7 empty slots
are the return-row column-0 slot (next to the spr) of the 7 outermost chains.

SerDes: W column A rows 0..4 = lk_HOST0, lk_WN2, lk_WN3, lk_WN0, lk_WN1 (lep pairs B/A around the lep at band height);
W column B = lk_HOST1, lk_DW0 (rows 0, 1), lk_DW1 (row 3).  E column A rows 0..4 = lk_M0..lk_M4; E column B = lk_DE0,
lk_M5 (rows 0, 1), lk_DE1, lk_DE2 (rows 3, 4).  Column B leaves row 2 (the ctl band height) open: every ctl <-> lane/lep
core link crosses there.  Each lane sits beside its SerDes, at the slot end nearest the ctl band.
"""
import argparse
import json
from pathlib import Path

GAP = 86.4                     # minimum street (block-block, block-edge)
SERDES = (518.4, 3844.8)       # ot_pdie_serdes slot (G7)
RETICLE = (26000.0, 33000.0)


def snap(v, q=0.0216):
    return round(round(v / q) * q, 4)


def construct(T=648.0, TH=None, chx=108.0, chy=108.0, cols=5, levels_n=7, levels_s=6, tiles=253,
              node=(216.0, 648.0), ctl=(1512.0, 2592.0), lep=(1296.0, 2592.0), lane=(518.4, 1123.2),
              corr=216.0, ch_out=648.0, ch_sp=216.0, ch_lane=108.0, ch_ctl=216.0):
    TH = TH or T
    PX, PY = T + chx, TH + chy
    SW, SH = SERDES
    nw, nh = node
    blocks = []

    def add(name, master, kind, group, x, y, w, h, orient='R0', **kw):
        blocks.append(dict(name=name, master=master, kind=kind, group=group, x=snap(x), y=snap(y), w=w, h=h,
                           reg=False, orient=orient, **kw))
        return blocks[-1]

    # ---------------------------------------------------------------- x layout
    x = GAP
    xA_W = x; x += SW + GAP
    xAp_W = x; wAp_W = max(lep[0], lane[0] + corr); x += wAp_W + GAP
    xB_W = x; x += SW + GAP
    xBp_W = x; wBp = lane[0] + corr; x += wBp + ch_out - GAP     # ch_out measured block to block
    x += GAP
    xarrW = x                                   # left edge of the W array (outermost column)
    arr_w = cols * T + (cols - 1) * chx
    x += arr_w + ch_sp
    x_spo = x; x += nw + ch_lane
    x_spr = x; x += nw + ch_sp
    xarrE = x; x += arr_w + ch_out
    xBp_E = x; x += wBp + GAP
    xB_E = x; x += SW + GAP
    wAp_E = lane[0] + corr
    xAp_E = x; x += wAp_E + GAP
    xA_E = x; x += SW + GAP
    W = snap(x)
    # ---------------------------------------------------------------- y layout
    rows_s = 2 * levels_s; rows_n = 2 * levels_n
    y0_s = GAP
    s_top = y0_s + rows_s * TH + (rows_s - 1) * chy
    ctl_y = s_top + ch_ctl
    y0_n = ctl_y + ctl[1] + ch_ctl
    n_top = y0_n + rows_n * TH + (rows_n - 1) * chy
    H = n_top + GAP
    H = max(H, 5 * SH + 6 * GAP)
    H = snap(H)
    band = (s_top, y0_n)                        # ctl band (no tiles)
    band_c = (ctl_y + ctl[1] / 2)

    def row_y(half, j):
        return (y0_n if half == 'N' else y0_s) + j * PY

    def level_rows(half, L):                    # (out row y, return row y)
        if half == 'N':
            return row_y('N', 2 * L), row_y('N', 2 * L + 1)
        return row_y('S', rows_s - 1 - 2 * L), row_y('S', rows_s - 2 - 2 * L)

    # ---------------------------------------------------------------- spine + tiles
    levels = [('N', L) for L in range(levels_n)] + [('S', L) for L in range(levels_s)]
    nslot = len(levels) * 2 * 2 * cols
    assert tiles <= nslot, (tiles, nslot)
    # empty slots: return-row column-0 slot of the outermost chains (N/S alternating from the far end, W then E)
    far = []
    for k in range(max(levels_n, levels_s) - 1, -1, -1):
        for half, nl in (('N', levels_n), ('S', levels_s)):
            if k < nl:
                far += [(half, k, 'W'), (half, k, 'E')]
    empty = set(far[:nslot - tiles])
    bundle = 0
    chains = []
    for half, L in levels:
        yo, yr = level_rows(half, L)
        grp = f'cl{half}{L:02d}'
        add(f'spo_{half}{L}', 'ot_s81hd_spo', 'spine', grp + 'W', x_spo, yo, nw, nh, 'MX' if half == 'S' else 'R0')
        add(f'spr_{half}{L}', 'ot_s81hd_spr', 'spine', grp + 'E', x_spr, yr, nw, nh, 'MX' if half == 'S' else 'R0')
        for side in 'WE':
            seq = []
            # out row: column 0 -> cols-1 (outward), return row: cols-1 -> 0 (inward)
            for leg, yy, cs in (('o', yo, range(cols)), ('r', yr, range(cols - 1, -1, -1))):
                for c in cs:
                    if leg == 'r' and c == 0 and (half, L, side) in empty:
                        continue
                    if side == 'W':
                        xx = xarrW + (cols - 1 - c) * PX
                        orient = 'MY' if leg == 'o' else 'R0'     # W out row flows west, return row east
                    else:
                        xx = xarrE + c * PX
                        orient = 'R0' if leg == 'o' else 'MY'
                    nm = f't_{half}{L:02d}{side}{leg}{c}'
                    add(nm, 'ot_s81hd_tile', 'tile', grp + side, xx, yy, T, TH, orient, bundle=None, flow='W' if orient == 'MY' else 'E')
                    seq.append(nm)
            chains.append(dict(half=half, level=L, side=side, tiles=seq, short=(half, L, side) in empty))
    # bundle index in chain order (N levels 0.., then S levels 0..; W then E; along the chain)
    by = {b['name']: b for b in blocks}
    for ch in chains:
        for nm in ch['tiles']:
            by[nm]['bundle'] = bundle; bundle += 1
    assert bundle == tiles, bundle
    # ---------------------------------------------------------------- ctl
    xc = (x_spo + x_spr + nw) / 2
    add('ctl', 'ot_s81hd_ctl', 'ctl', 'clctl', xc - ctl[0] / 2, ctl_y, ctl[0], ctl[1])
    # ---------------------------------------------------------------- SerDes columns
    s = (H - 2 * GAP - 5 * SH) / 4
    s = int(s / 21.6) * 21.6
    ys = [GAP + r * (SH + s) for r in range(5)]
    assert ys[4] + SH <= H - GAP + 1e-6
    serdes = {}
    def sd(name, col, xcol, r, side):
        serdes[name] = dict(col=col, row=r, side=side)
        return add(name, 'ot_pdie_serdes', 'link', 'edge', xcol, ys[r], SW, SH, scope=f'{side} column {col} row {r}')
    for r, n in enumerate(('lk_HOST0', 'lk_WN2', 'lk_WN3', 'lk_WN0', 'lk_WN1')):
        sd(n, 'A', xA_W, r, 'W')
    for r, n in ((0, 'lk_HOST1'), (1, 'lk_DW0'), (3, 'lk_DW1')):
        sd(n, 'B', xB_W, r, 'W')
    for r in range(5):
        sd(f'lk_M{r}', 'A', xA_E, r, 'E')
    for r, n in ((0, 'lk_DE0'), (1, 'lk_M5'), (3, 'lk_DE1'), (4, 'lk_DE2')):
        sd(n, 'B', xB_E, r, 'E')
    # column B leaves row 2 open over the whole ctl band
    assert ys[1] + SH + GAP <= band[0] and band[1] + GAP <= ys[3], (ys, band)
    # ---------------------------------------------------------------- lanes + lep
    lw, lh = lane

    def lane_y(r):
        lo, hi = ys[r], ys[r] + SH
        if hi <= band[0] + 1e-6:
            return hi - lh                       # below the band: top end of the slot
        if lo >= band[1] - 1e-6:
            return lo                            # above: bottom end
        return min(max(band_c - lh / 2, lo), hi - lh)

    lanes = {}
    def ln(name, sdn, xcol, wcol, side, role):
        r = serdes[sdn]['row']
        xx = xcol if side == 'W' else xcol + wcol - lw      # adjacent to its SerDes (outer side of the column)
        lanes[name] = dict(serdes=sdn, role=role)
        return add(name, 'ot_s81hd_lane', 'lane', f'cl_{name}', xx, lane_y(r), lw, lh, role=role, serdes=sdn)
    ln('ln_host0', 'lk_HOST0', xAp_W, wAp_W, 'W', 'host')
    ln('ln_host1', 'lk_HOST1', xBp_W, wBp, 'W', 'host')
    ln('ln_draft0', 'lk_DW0', xBp_W, wBp, 'W', 'draft')
    ln('ln_draft1', 'lk_DW1', xBp_W, wBp, 'W', 'draft')
    for r in range(5):
        ln(f'ln_mesh{r}', f'lk_M{r}', xAp_E, wAp_E, 'E', 'mesh')
    ln('ln_draft2', 'lk_DE0', xBp_E, wBp, 'E', 'draft')
    ln('ln_mesh5', 'lk_M5', xBp_E, wBp, 'E', 'mesh')
    ln('ln_draft3', 'lk_DE1', xBp_E, wBp, 'E', 'draft')
    ln('ln_draft4', 'lk_DE2', xBp_E, wBp, 'E', 'draft')
    add('lep', 'ot_s81hd_lep', 'lep', 'cllep', xAp_W, band_c - lep[1] / 2, lep[0], lep[1])
    # ---------------------------------------------------------------- array through-route guards
    # Geometry-only reserves over every horizontal channel between two tile rows, spanning one tile array exactly:
    # the tile arrays are no through-route for die wires (ctl <-> lane/lep core links and SerDes links stay in the edge
    # corridors and the ctl band); chain links (W/E faces at row mid-height), U-turns (outer channel) and the spine lanes
    # are untouched.  dv_route72 treats them as obstacles; rvcase as placement blockage + M1-M6 obstruction (nothing of
    # the die belongs there: chain region crossings land in the spine channels, U-turn stations in the outer channel).
    reserves = []
    for half, nrow, y0 in (('S', rows_s, y0_s), ('N', rows_n, y0_n)):
        for j in range(nrow - 1):
            yb = y0 + j * PY + TH
            for side, xa in (('W', xarrW), ('E', xarrE)):
                reserves.append(dict(name=f'arr_ch_{half}{j:02d}{side}', kind='reserve', x=snap(xa), y=snap(yb), w=round(arr_w, 4), h=chy,
                                     scope='H1 tile-array row channel: routing/placement guard (no through-route), no master/pins'))
    # ---------------------------------------------------------------- checks
    for b in blocks:
        assert min(b['x'], b['y']) >= GAP - 1e-6 and b['x'] + b['w'] <= W - GAP + 1e-6 and b['y'] + b['h'] <= H - GAP + 1e-6, b['name']
    srt = sorted(blocks, key=lambda b: b['x'])
    for i, b in enumerate(srt):
        for c in srt[i + 1:]:
            if c['x'] - (b['x'] + b['w']) >= GAP:
                break
            sep = max(c['x'] - (b['x'] + b['w']), b['x'] - (c['x'] + c['w']), c['y'] - (b['y'] + b['h']), b['y'] - (c['y'] + c['h']))
            assert sep >= GAP - 0.01, (b['name'], c['name'], round(sep, 3))
    assert W <= RETICLE[0] and H <= RETICLE[1], (W, H)
    params = dict(tile=[T, TH], chx=chx, chy=chy, cols=cols, levels_n=levels_n, levels_s=levels_s, tiles=tiles, slots=nslot,
                  node=list(node), ctl=list(ctl), lep=list(lep), lane=list(lane), corridor=corr, ch_out=ch_out, ch_sp=ch_sp,
                  ch_lane=ch_lane, ch_ctl=ch_ctl, street=GAP, serdes_slot=list(SERDES), serdes_row_street=round(s, 3))
    return dict(scope='S81 HEAD DIE H1 CONSTRUCTION (HD-FP 10-21): floorplan only, not routed closure',
                die=[W, H], die_mm2=round(W * H / 1e6, 3), reticle=list(RETICLE), params=params,
                band=[round(band[0], 4), round(band[1], 4)], spine_x=dict(spo=snap(x_spo), spr=snap(x_spr)),
                serdes=dict(rows_y=[round(v, 4) for v in ys], column_x=dict(W_A=xA_W, W_B=snap(xB_W), E_B=snap(xB_E), E_A=snap(xA_E)), slots=serdes),
                lanes=lanes, chains=chains, empty_slots=[f'{h}{L:02d}{s_}r0' for h, L, s_ in sorted(empty)],
                spec_reconciliation=('spec v1 s2 "13 levels per half" conflicts with 260 slots / <=5 tiles a row / die ~13 x 20.5 mm; '
                                     f'built {levels_n} N + {levels_s} S = {levels_n + levels_s} levels, {len(chains)} chains x {2 * cols} slots, '
                                     f'{levels_n + levels_s} spo + {levels_n + levels_s} spr'),
                best=dict(blocks=blocks), reserves=reserves)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('out')
    a.add_argument('--tile', type=float, default=648.0, help='tile outline width (HD-TILE fallback may grow it)')
    a.add_argument('--tile-h', type=float, default=None)
    a.add_argument('--chx', type=float, default=108.0); a.add_argument('--chy', type=float, default=108.0)
    a.add_argument('--cols', type=int, default=5)
    a.add_argument('--levels-n', type=int, default=7); a.add_argument('--levels-s', type=int, default=6)
    a.add_argument('--tiles', type=int, default=253)
    a.add_argument('--ctl', type=float, nargs=2, default=(1512.0, 2592.0))
    v = a.parse_args()
    d = construct(T=v.tile, TH=v.tile_h, chx=v.chx, chy=v.chy, cols=v.cols, levels_n=v.levels_n, levels_s=v.levels_s,
                  tiles=v.tiles, ctl=tuple(v.ctl))
    Path(v.out).parent.mkdir(parents=True, exist_ok=True)
    Path(v.out).write_text(json.dumps(d, indent=1))
    from collections import Counter
    print('HEAD_H1_CONSTRUCTED', dict(Counter(b['master'] for b in d['best']['blocks'])), 'die', d['die'], d['die_mm2'], 'mm2')


if __name__ == '__main__':
    main()
