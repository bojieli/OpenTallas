"""Physical complement of the existing die-owned feedthrough stripe map.

Only types explicitly declaring die_ft_bands opt in. The same global map is
transformed back through every instance; one hardened type must have one map.
"""
import hashlib
import json


def _local(rect, part, width, height):
    x0,y0,x1,y1=rect;ox,oy=part['origin_um']
    x0,x1=x0-ox,x1-ox;y0,y1=y0-oy,y1-oy
    if part.get('orient','R0') in ('MY','R180'):x0,x1=width-x1,width-x0
    if part.get('orient','R0') in ('MX','R180'):y0,y1=height-y1,height-y0
    return tuple(round(v,3) for v in (x0,y0,x1,y1))


def reservation(P, typ):
    t=P.types[typ]
    if not t.get('die_ft_bands'):return None
    try:
        from . import die_trial as D
    except ImportError:
        import die_trial as D
    # band_region_adjust reserves every globally banded layer, including its
    # default share outside that layer's explicit bands. An opted-in type must
    # complement that entire placed die map, not only its own band layers.
    layers=sorted({row[0] for row in D.ft_band_rects(P)})
    if set(layers)-{'M4','M5','M6','M7'}:
        raise ValueError('partition FT complement is restricted to lower signal layers M4..M7')
    # Match die_trial.kit exactly, including its minimum default FT share.
    frac=min(float(q.get('ft_track_frac',.25)) for q in P.types.values())
    _,regions=D.band_region_adjust(P,round(1-frac,3))
    by={L:[] for L in layers}
    for L,*rect in D.band_share_obs(P,regions):
        if L in by:by[L].append(tuple(rect))
    for L in layers:by[L].extend(D.die_core_rects(P,L))
    w,h=t['outline_um'];maps=[]
    for name,part in sorted(P.parts.items()):
        if part['type']!=typ:continue
        if part.get('orient','R0') not in ('R0','MX','MY','R180'):
            raise ValueError('unsupported FT reservation instance orientation')
        ox,oy=part['origin_um'];rectangles=[]
        for L in layers:
            blocked=[]
            for a,b,c,d in by[L]:
                clip=(max(a,ox),max(b,oy),min(c,ox+w),min(d,oy+h))
                if clip[2]>clip[0]+1e-6 and clip[3]>clip[1]+1e-6:
                    blocked.append(_local(clip,part,w,h))
            # The die can route precisely outside its obstructions. Block that
            # complement in the partition, including exact transition behavior.
            rectangles.extend((L,*r) for r in D._uncovered(w,h,blocked))
        maps.append((name,sorted(rectangles)))
    if not maps:raise ValueError('explicit FT bands have no physical partition instance')
    if any(rectangles!=maps[0][1] for _,rectangles in maps[1:]):
        raise ValueError(f'{typ}: transformed FT maps differ across instances; one hardened view cannot reserve both')
    rows=maps[0][1]
    return dict(schema='opentallas.partition_ft_reservation.v1',type=typ,
                instances=[name for name,_ in maps], default_die_share=frac,
                basis='physical complement of die_trial band_share_obs plus die macro OBS',
                plan_sha256=hashlib.sha256(json.dumps(P.raw,sort_keys=True).encode()).hexdigest(),
                rectangles_um=[dict(layer=L,rect=list(r)) for L,*r in rows])


def tcl(receipt):
    if receipt is None:return ''
    lines=['# Exact partition complement of the die-owned FT tracks.',
           'set ot_ft_blk [ord::get_db_block]',
           'set ot_ft_dbu [$ot_ft_blk getDbUnitsPerMicron]']
    rows=obstruction_rows(receipt)
    for layer,rect in rows:
        lines.append(f'set ot_ft_layer [[ord::get_db_tech] findLayer {layer}]')
        lines.append('odb::dbObstruction_create $ot_ft_blk $ot_ft_layer '+' '.join(
            f'[expr {{round({v:.3f}*$ot_ft_dbu)}}]' for v in rect))
    wins=pdn_windows(receipt)
    if wins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows={len(wins)}"')
    vwins=pdn_windows_v(receipt)
    if vwins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_v={len(vwins)}"')
    cwins=pdn_windows_comb(receipt)
    if cwins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_comb={len(cwins)}"')
    colwins=pdn_windows_col(receipt)
    if colwins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_col={len(colwins)} col_fill_m6={len(pdn_col_fill(receipt))}"')
    lines.append(f'puts "OT_PARTITION_FT_RESERVE rectangles={len(rows)}"')
    return '\n'.join(lines)+'\n'


# DIE-HBM-90 11-07 (HBM transit types q_spu0 / q_spu1 2_4_floorplan_pdn [ERROR PDN-0179] "Unable to repair all
# channels", 131 PDN-0178 channels on M2): the reservation blocks M4 in full-width horizontal bands (the die FT tracks,
# 2.7 um of every 10.8 um on q_spu0).  The PDN reaches the M1/M2 rails only through M2->M5 via stacks, and a stack
# cannot cross a blocked M4 band, so every row under a band has no via anywhere along its length.  Row bridge: vertical
# M3 straps (M3 is never reserved) cross every rail and carry it out of the band to horizontal M4 straps placed in the
# unreserved M4 gaps (pdngen drops strap segments that fall in an obstruction), which connect to the M5 straps.  All
# bridge metal stays outside the reservation (probed: 0 PDN shapes inside an obstruction, PDNGEN OK on q_spu0).
BRIDGE_M3 = dict(width=0.09, spacing=0.072, pitch=4.32, offset=1.08)     # ASAP7 M3 legal width 0.09
BRIDGE_M4 = dict(width=0.12, spacing=0.072, pitch=4.32, offset=2.16)     # ASAP7 M4 legal width 0.12; pitch < min gap


# DIE-HBM-91 11-08 (HBM q_b013 / q_b013__physical_v1 PDN-0179 with the row bridge on): over y 943.9-2912.2 the die
# reserves ALL of M6 (one full-width rect), and each 103.68-um street between two stacked
# ot_hbm_hc_bank128_pair_core (OBS M1-M5) also has ALL of M4 reserved.  The street is then a PDN island: its M3 bridge
# straps and M5 straps are cut by the cores above and below, M4 has no gap and M6 has no gap, so no via stack reaches
# M6/M7 (base: 5 PDN-0178 M3 channels, one per street, then PDN-0179; M4 windows only: 103 M5 channels).  A TALL
# full-width band (> PDN_WIN_MIN) on a PDN layer keeps one window at every PDN_WIN_EVERY-th strap position of that
# layer's PDN stripe (M4: the row-bridge strap, M6: the PG_M6 strap), where the strap lands.  The die FT router sees
# the strap in the abstract and routes around it: ~0.6 um of every 21.6 um of M4 and ~1.0 um of every 21.6 um of M6
# in such a band (3-5 %).  Bands no taller than PDN_WIN_MIN (q_spu0: 2.7 um) are unchanged.
PDN_WIN_MIN = 8.64
PDN_WIN_EVERY = 5
PDN_WIN_MARGIN = 0.15                         # > the stripe spacing (0.072 M4, 0.096 M6) on each side of the pair


def _pair_shift(width):
    # DIE-HBM-94 11-08 (q_b011 + pv1 PDN-0179, M6 VSS only): pdngen's stripe offset is the CENTRE of the first strap and the first
    # strap is VSS, so the pair spans [s - w/2, s - w/2 + 2w + spacing].  For the 288-nm M6/M7 straps the old window [s, s + 2w + sp]
    # left only 6 nm on the VSS side, the VSS strap was cut and only VDD survived (measured on q_b011: M7 VDD full height at x 25.968,
    # VSS only 32-nm stubs).  Shift the M7 windows by w/2 (real pdngen on the failing DB: PDN-0179 gone).  Only the vertical M7 windows
    # are shifted; M6 horizontal windows and M4/M5 keep their positions (unchanged kits, not re-probed here).
    return width / 2

PDN_WIN_STRIPES = {'M4': (2.16, 0.12, 0.072, 4.32),      # offset, width, spacing, pitch = BRIDGE_M4
                   'M6': (1.968, 0.288, 0.096, 4.32)}    # = gen_phys PG_M6 / the top-grid M6 stripe


# DIE-HBM-92-SU 11-08 (HBM q_su21 / q_su30 / q_su31 PDN-0179 "Unable to repair all channels", 54 PDN-0178 channels on
# M6): the die reserves M7 (the PDN pin layer, vertical) in WIDE vertical bands, e.g. one 251-um block over the SU lane1
# macro column of q_su21.  The macro-edge channels under it (core edge to the first macro, the 78-um gap between the two
# macro groups) then have no M7 strap anywhere, and the M6 straps there are cut every 10.8 um by the die M6 FT bands, so
# pdngen cannot repair the channel.  Bisect on the q_su21 tapcell odb: dropping the M6 or the M7 reservation -> PDNGEN OK;
# M4 or M5 -> unchanged.  A WIDE band (> PDN_WIN_MIN) on the vertical PDN pin layer keeps one strap window at every
# PDN_WIN_EVERY_V-th M7 strap of the top grid (real core grid: core x0 + offset + k * pitch), the first strap inside the
# band included, so every channel at least PDN_WIN_EVERY_V M7 pitches wide gets an M7 strap (q_su21: 1, 2, 3 -> PDNGEN OK;
# skipping the strap nearest the band edge -> 27 channels left).  M7 cost in such a band: 0.972 of every 17.28 um (5.6 %).
PDN_WIN_EVERY_V = 2
PDN_WIN_STRIPES_V = {'M7': (4.128, 0.288, 0.096, 8.64)}  # = gen_phys PDN top-grid M7 stripe (offset, width, spacing, pitch)


def pdn_windows_v(receipt, core_x0=4.32):
    """[(layer, x0, x1, rect)] vertical PDN strap windows cut out of wide M7 reservation rectangles."""
    if receipt is None:
        return []
    out = []
    for r in receipt['rectangles_um']:
        if r['layer'] not in PDN_WIN_STRIPES_V:
            continue
        x0, y0, x1, y1 = r['rect']
        if x1 - x0 <= PDN_WIN_MIN:
            continue
        off, wd, sp, pitch = PDN_WIN_STRIPES_V[r['layer']]
        step = PDN_WIN_EVERY_V * pitch
        k = max(0, int((x0 - core_x0 - off) // pitch))
        first = None
        while True:
            s = core_x0 + off + k * pitch
            k += 1
            s -= _pair_shift(wd)
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if lo < x0 + PDN_WIN_MARGIN:
                continue
            if hi > x1 - PDN_WIN_MARGIN:
                break
            if first is None:
                first = s
            if round((s - first) / pitch) % PDN_WIN_EVERY_V:
                continue
            out.append((r['layer'], round(lo, 3), round(hi, 3), tuple(r['rect'])))
    return out


# DIE-HBM-93 11-08 (q_b002, q_b013__physical_v1, one PDN-0178 M5 VSS channel x 45.2-62.6, y 2514-2607 between two bank
# macros): the die reserves M5 as tall columns plus a short tooth row closing the top of the pocket.  The M5 straps of the
# gaps between columns end at the tooth, under the only free M6 rows, so they get no M5-M6 via.  A tooth taller than
# PDN_WIN_MIN keeps one strap-pair window at each M5 strap that is not under a column (removing the teeth: PDNGEN OK).
PDN_WIN_COMB = {'M5': (2.064, 0.12, 0.072, 4.32)}    # = gen_phys PDN top-grid M5 stripe (offset, width, spacing, pitch)


def pdn_windows_comb(receipt, core_x0=4.32):
    """[(layer, x0, x1, rect)] strap windows cut out of narrow, taller-than-PDN_WIN_MIN M5 tooth rows."""
    if receipt is None:
        return []
    rects = [(r['layer'], tuple(r['rect'])) for r in receipt['rectangles_um']]
    out = []
    for layer, rect in rects:
        if layer not in PDN_WIN_COMB:
            continue
        x0, y0, x1, y1 = rect
        if x1 - x0 > PDN_WIN_MIN + 1e-6 or not PDN_WIN_MIN + 1e-6 < y1 - y0 <= 2 * PDN_WIN_MIN:   # columns stay whole
            continue
        off, wd, sp, pitch = PDN_WIN_COMB[layer]
        k = max(0, int((x0 - core_x0 - off) // pitch))
        while True:
            s = core_x0 + off + k * pitch
            k += 1
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if lo < x0 + PDN_WIN_MARGIN:
                continue
            if hi > x1 - PDN_WIN_MARGIN:
                break
            if any(L == layer and q != rect and q[0] < hi and q[2] > lo and (abs(q[3] - y0) < 1e-6 or abs(q[1] - y1) < 1e-6)
                   for L, q in rects):
                continue            # a column continues this strap position: the window could not reach the pocket
            out.append((layer, round(lo, 3), round(hi, 3), rect))
    return out


# DIE-HBM-96/97 11-09 (q_b011 a5, q_b103 a10 PDN-0179, 2-3 PDN-0178 M4 channels each about 6 x 9 um inside ONE column):
# the die reserves a tall narrow M5 column (q_b011 x 123.552-129.6, 6.048 um) together with M4 rows of exactly the same
# x extent every 10.8 um.  Each 8.1-um pocket between two of those M4 rows has M4 straps but M5 reserved over its whole
# width, so it gets no M4-M5 via (real pdngen on the 2_3 tapcell DB: dropping the column's 83 M4 rects -> worse; dropping
# its 4 M5 rects -> all 3 M4 channels gone).  Such a column (M5, no wider than PDN_WIN_MIN, taller than 2 * PDN_WIN_MIN,
# with at least PDN_WIN_COL_ROWS M4 rects of its own x extent inside its height) keeps one M5 strap-pair window at each
# M5 strap position that fits, through its full height and on through the M5 rects stacked on its ends (the street rows
# that close it), and the column's M6 is reserved whole (pdn_col_fill).  Plain FT columns (no own M4 rows, e.g. the
# 2.7-um columns) are unchanged.  Cost: about 0.612 um of M5 per window in that column and its end rows; the gap's M6.
# Real pdngen, q_b011 a5 2_3: window only -> 1 M6 VDD channel; window + M6 fill without the end rows -> 3 M5 channels;
# window through the end rows + M6 fill -> PDNGEN OK.
PDN_WIN_COL_ROWS = 2


def _gap_columns(rects):
    """[(layer, rect)] tall narrow M5 columns with at least PDN_WIN_COL_ROWS M4 rects of their own x extent inside."""
    out = []
    for layer, rect in rects:
        if layer not in PDN_WIN_COMB:
            continue
        x0, y0, x1, y1 = rect
        if x1 - x0 > PDN_WIN_MIN + 1e-6 or y1 - y0 <= 2 * PDN_WIN_MIN + 1e-6:
            continue
        own = sum(1 for L, q in rects if L == 'M4' and abs(q[0] - x0) < 1e-3 and abs(q[2] - x1) < 1e-3
                  and q[1] >= y0 - 1e-6 and q[3] <= y1 + 1e-6)
        if own >= PDN_WIN_COL_ROWS:
            out.append((layer, rect))
    return out


def pdn_windows_col(receipt, core_x0=4.32):
    """[(layer, x0, x1, rect)] M5 strap windows through tall narrow M5 columns that carry their own M4 rows."""
    if receipt is None:
        return []
    rects = [(r['layer'], tuple(r['rect'])) for r in receipt['rectangles_um']]
    out = []
    for layer, rect in _gap_columns(rects):
        x0, y0, x1, y1 = rect
        off, wd, sp, pitch = PDN_WIN_COMB[layer]
        k = max(0, int((x0 - core_x0 - off) // pitch))
        while True:
            s = core_x0 + off + k * pitch
            k += 1
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if lo < x0 + PDN_WIN_MARGIN:
                continue
            if hi > x1 - PDN_WIN_MARGIN:
                break
            out.append((layer, round(lo, 3), round(hi, 3), rect))
            # the strap must leave the column: carry the same window through every M5 rect stacked on its ends
            # (q_b011: street rows 124.74-246.24 close both ends; without this the window strap is an island, its M6
            # VDD in the pocket has no M7 landing, and 1 M6 channel stays)
            for up in (True, False):
                edge, seen = (y1 if up else y0), {rect}
                while True:
                    nxt = [q for L, q in rects if L == layer and q not in seen and q[0] < hi and q[2] > lo
                           and abs((q[1] if up else q[3]) - edge) < 1e-6]
                    if not nxt:
                        break
                    for q in nxt:
                        seen.add(q)
                        out.append((layer, round(max(lo, q[0]), 3), round(min(hi, q[2]), 3), q))
                    edge = max(q[3] for q in nxt) if up else min(q[1] for q in nxt)
    return out


def pdn_col_fill(receipt):
    """[(layer, rect)] M6 fill over each column that got a pdn_windows_col window: the column sits in the gap between two
    macros whose OBS reach M6, so an M6 strap piece in it has no M7 landing on the 8.64-um M7 grid (q_b011: the VDD strap
    of the pair over the gap edge lands on the macro; 1 M6 VDD channel).  With the gap's M6 reserved the pocket feeds
    through the M5 window strap instead.  The partition cannot use that M6 (macro OBS on both sides)."""
    if receipt is None:
        return []
    cols = {rr for _, _, _, rr in pdn_windows_col(receipt)}
    rects = [(r['layer'], tuple(r['rect'])) for r in receipt['rectangles_um']]
    return [('M6', list(rect)) for _, rect in _gap_columns(rects) if rect in cols]


# DIE-HBM-92-SU 11-08 (q_su30__physical_v1, 2 PDN-0178 M5 channels over the pretree macro): the die can reserve a tall
# M6 block as a stack of abutting rows (8.1 / 2.7 um, alternately ending at x 2062.8 and 2064.96 of a 2064.96 outline).
# Each row alone is thin and not exactly full-width, so the tall-band rule never fired.  Rows that reach both outline
# edges within PDN_WIN_FULL_TOL count as full width, and abutting full rows of one layer merge into one band.
PDN_WIN_FULL_TOL = 4.32


def _full(row, width):
    x0, y0, x1, y1 = row['rect']
    return row['layer'] in PDN_WIN_STRIPES and x0 <= PDN_WIN_FULL_TOL and x1 >= width - PDN_WIN_FULL_TOL


def _bands(receipt, width):
    """[(layer, y0, y1)] maximal y-runs of abutting full-width rows per PDN layer."""
    rows = sorted((r['layer'], r['rect'][1], r['rect'][3]) for r in receipt['rectangles_um'] if _full(r, width))
    out = []
    for L, y0, y1 in rows:
        if out and out[-1][0] == L and y0 <= out[-1][2] + 1e-6:
            out[-1][2] = max(out[-1][2], y1)
        else:
            out.append([L, y0, y1])
    return [tuple(b) for b in out]


def _width(receipt, width):
    return width if width is not None else max((r['rect'][2] for r in receipt['rectangles_um']), default=0.0)


def pdn_windows(receipt, width=None, core_y0=4.32):
    """[(layer, y0, y1)] PDN strap windows cut out of tall full-width M4/M6 bands (see PDN_WIN_MIN)."""
    if receipt is None:
        return []
    width = _width(receipt, width)
    out = []
    for L, y0, y1 in _bands(receipt, width):
        if y1 - y0 <= PDN_WIN_MIN:
            continue
        off, wd, sp, pitch = PDN_WIN_STRIPES[L]
        step = PDN_WIN_EVERY * pitch
        k = max(0, int((y0 - core_y0 - off) // step))
        while True:
            s = core_y0 + off + k * step
            k += 1
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if lo < y0 + pitch:
                continue
            if hi > y1 - pitch:
                break
            out.append((L, round(lo, 3), round(hi, 3)))
    return out


def obstruction_rows(receipt, width=None, core_y0=4.32):
    """[(layer, rect)] the obstructions to create: the receipt rectangles, tall full-width M4/M6 bands split at
    pdn_windows."""
    width = _width(receipt, width)
    wins = pdn_windows(receipt, width, core_y0)
    vwins = pdn_windows_v(receipt) + pdn_windows_comb(receipt) + pdn_windows_col(receipt)
    out = []
    for r in receipt['rectangles_um']:
        x0, y0, x1, y1 = r['rect']
        vmine = sorted({(a, b) for L, a, b, rr in vwins if L == r['layer'] and rr == tuple(r['rect'])})
        if vmine:
            cur = x0
            for a, b in vmine:
                if a > cur + 1e-9:
                    out.append((r['layer'], [cur, y0, a, y1]))
                cur = max(cur, b)
            if x1 > cur + 1e-9:
                out.append((r['layer'], [cur, y0, x1, y1]))
            continue
        # a window of a merged band may straddle the rows it is made of: cut the overlap out of every row
        mine = sorted((max(a, y0), min(b, y1)) for L, a, b in wins
                      if L == r['layer'] and a < y1 and b > y0) if _full(r, width) else []
        cur = y0
        for a, b in mine:
            if a > cur + 1e-9:
                out.append((r['layer'], [x0, cur, x1, a]))
            cur = max(cur, b)
        if y1 > cur + 1e-9:
            out.append((r['layer'], [x0, cur, x1, y1]))
    return out + pdn_col_fill(receipt)


def blocks_rows(receipt, width):
    """True when an M4 reservation rectangle spans the whole outline width: rows under it get no M2->M5 via."""
    if receipt is None:
        return False
    return any(r['layer'] == 'M4' and r['rect'][0] <= 1e-6 and r['rect'][2] >= width - 1e-6
               for r in receipt['rectangles_um'])


def row_bridge_tcl(receipt, width, grid='top'):
    if not blocks_rows(receipt, width):
        return ''
    b3, b4 = BRIDGE_M3, BRIDGE_M4
    return '\n'.join([
        '# PDN row bridge (DIE-HBM-90 11-07): M4 FT bands span the width; M3 straps carry the rails to M4 straps in the gaps.',
        'add_pdn_stripe -grid {%s} -layer {M3} -width {%g} -spacing {%g} -pitch {%g} -offset {%g}' % (
            grid, b3['width'], b3['spacing'], b3['pitch'], b3['offset']),
        'add_pdn_stripe -grid {%s} -layer {M4} -width {%g} -spacing {%g} -pitch {%g} -offset {%g}' % (
            grid, b4['width'], b4['spacing'], b4['pitch'], b4['offset']),
        'add_pdn_connect -grid {%s} -layers {M2 M3}' % grid,
        'add_pdn_connect -grid {%s} -layers {M3 M4}' % grid,
        'add_pdn_connect -grid {%s} -layers {M4 M5}' % grid,
        'puts "OT_PARTITION_FT_RESERVE row bridge M3/M4 on"']) + '\n'
