"""Physical complement of the existing die-owned feedthrough stripe map.

Only types explicitly declaring die_ft_bands opt in. The same global map is
transformed back through every instance; one hardened type must have one map.
"""
import hashlib
import math
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
    # FTRES-FIX 11-10: complement the die's OWNERSHIP map (band_share_obs owner=True), not its GRT capacity stripes.
    # They differ only over a halved transition gcell (M6 over an M5-OBS core), where the die really has 0.5 a of the
    # tracks: the partition now reserves that, not 0.5 + 0.5 a.  Outside a band the die keeps 0 over hard cores
    # (band_region_adjust core_zero, 12.10c), so nothing is reserved there; a band's core_share sets its share over cores.
    for L,*rect in D.band_share_obs(P,regions,owner=True):
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
                core_zero=bool(D.FT_CORE_ZERO),
                basis='physical complement of die_trial band_share_obs(owner=True) plus die macro OBS',
                plan_sha256=hashlib.sha256(json.dumps(P.raw,sort_keys=True).encode()).hexdigest(),
                rectangles_um=[dict(layer=L,rect=list(r)) for L,*r in rows])


def tcl(receipt, macro_boxes=None):
    if receipt is None:return ''
    lines=['# Exact partition complement of the die-owned FT tracks.',
           'set ot_ft_blk [ord::get_db_block]',
           'set ot_ft_dbu [$ot_ft_blk getDbUnitsPerMicron]']
    rows=obstruction_rows(receipt, macro_boxes=macro_boxes)
    for layer,rect in rows:
        lines.append(f'set ot_ft_layer [[ord::get_db_tech] findLayer {layer}]')
        lines.append('odb::dbObstruction_create $ot_ft_blk $ot_ft_layer '+' '.join(
            f'[expr {{round({v:.3f}*$ot_ft_dbu)}}]' for v in rect))
    lines += sliver_tcl().splitlines()
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
    edgewins=pdn_windows_edge_pocket(receipt)
    if edgewins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_edge_pocket={len(edgewins)}"')
    streetwins=pdn_windows_street(receipt, boxes=macro_boxes, existing=wins+pdn_windows_strip(receipt))
    if streetwins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_street={len(streetwins)}"')
    m5wins=pdn_windows_m5_full(receipt, boxes=macro_boxes)
    if m5wins:
        lines.append(f'puts "OT_PARTITION_FT_RESERVE pdn_windows_m5_full={len(m5wins)}"')
    lines.append(f'puts "OT_PARTITION_FT_RESERVE rectangles={len(rows)}"')
    return '\n'.join(lines)+'\n'


# DIE-HBM-97 11-09 (q_b102__physical_v1 PDN-0179, 12 PDN-0178 M6 channels at x 578.952 along two gap columns): the
# receipt is in plan coordinates, but the placed macros can sit a site off them (gap rows end at 578.88, macro u_ra
# starts at 579.012).  The 0.132-um M6 sliver left between the reservation and the macro edge holds strap ends that
# have no M5/M7 landing.  After the reservation is built, every M6 FT obstruction whose x edge lies less than one strap
# pair + spacing (0.384 um) from a placed block's edge is closed up to that edge over their common height.  Probed
# (real pdngen, 2_3 tapcell DB): 13 -> 1 channel on q_b102__physical_v1 (272 slivers closed), and with the column rule's
# covering own rows -> PDNGEN OK; q_b011/b100/b100a6/b100pv1/b101/b101_nw/b103 PDNGEN OK, 0 slivers there.
# DIE-HBM-97 11-09 (q_b010 QN-alt / q_b010__physical_v1 / q_b000 PDN-0179, 3-6 PDN-0178 M6 channels): the same island,
# wider.  (a) q_b010 x 127.44-129.6: M6 FT rows of a macro-gap column end 2.16 um short of macro u_rb, M7 reserved over
# the gap; (b) q_b010 x 591.84-602.64 y 2913.57-2917.62: a 10.8-um hole between two M6 FT rows, M7 reserved 588.0-604.3;
# (c) q_b010__physical_v1 x 469.15-483.84 (VSS only): the M6 pocket between macro h1 and macro u_ra, where the one M7
# strap window (483.354-484.326) lands the first strap of the pair inside the pocket and the second over u_ra.  An M6
# strap piece in such a gap is bounded on both sides (block or M6 obstruction) and one of its nets has no M7 strap
# above it, so pdngen reports the channel and cannot repair it (M7 is reserved there).  Every M6 gap between two
# M6 blockers (blocks and M6 obstructions) over their common height is closed when it is a sliver (< ot_ft_sl, the
# rule above) or when, for either net, no strap of the top-grid M7 pair (core x0 + offset + k * pitch, first strap
# centred on it) lies wholly inside the gap clear of M7 obstructions AND no free M7 run in the gap is as wide as a
# strap pair (2w + sp, so pdngen's channel repair could not place one either).  Only M6 strap pieces that can never
# lift both nets to M7 are removed; M7, every gap where both nets land and every repairable gap are unchanged.
SLIVER_TCL = """set ot_ft_m6 [[ord::get_db_tech] findLayer M6]
set ot_ft_m7 [[ord::get_db_tech] findLayer M7]
set ot_ft_sl [expr {round(0.384*$ot_ft_dbu)}]
set ot_ft_core [$ot_ft_blk getCoreArea]
set ot_ft_s7 [list [expr {[$ot_ft_core xMin] + round(@OFF@*$ot_ft_dbu)}] [expr {round(@W@*$ot_ft_dbu)}] [expr {round(@SP@*$ot_ft_dbu)}] [expr {round(@PITCH@*$ot_ft_dbu)}]]
set ot_ft_bl {}; set ot_ft_o7 {}
foreach ot_i [$ot_ft_blk getInsts] { if {[[$ot_i getMaster] isBlock]} { set ot_b [$ot_i getBBox]
  lappend ot_ft_bl [list [$ot_b xMin] [$ot_b yMin] [$ot_b xMax] [$ot_b yMax] 1] } }
foreach ot_o [$ot_ft_blk getObstructions] {
  set ot_b [$ot_o getBBox]; set ot_l [$ot_b getTechLayer]
  set ot_r [list [$ot_b xMin] [$ot_b yMin] [$ot_b xMax] [$ot_b yMax] 0]
  if {$ot_l eq $ot_ft_m6} { lappend ot_ft_bl $ot_r } elseif {$ot_l eq $ot_ft_m7} { lappend ot_ft_o7 $ot_r }
}
set ot_ft_bl [lsort -integer -index 1 $ot_ft_bl]
proc ot_ft_m7_ok {o7 s7 x0 y0 x1 y1} {
  # 1 when BOTH straps of some top-grid M7 pair position land in [x0, x1] clear of the M7 obstructions over y0-y1,
  # or when M7 is free over at least one strap pair width there (repairable)
  lassign $s7 s0 w sp p
  set ob {}
  foreach r $o7 { lassign $r a b c d; if {$b < $y1 && $d > $y0 && $c > $x0 && $a < $x1} { lappend ob [list $a $c] } }
  set got {0 0}
  set k [expr {max(0, ($x0 - $s0) / $p - 1)}]
  while {1} {
    set s [expr {$s0 + $k * $p}]; incr k
    if {$s - $w > $x1} { break }
    foreach n {0 1} lo [list [expr {$s - $w / 2}] [expr {$s + $w / 2 + $sp}]] {
      set hi [expr {$lo + $w}]
      if {$lo < $x0 || $hi > $x1} { continue }
      set free 1
      foreach q $ob { if {[lindex $q 0] < $hi && [lindex $q 1] > $lo} { set free 0; break } }
      if {$free} { lset got $n 1 }
    }
    if {[lindex $got 0] && [lindex $got 1]} { return 1 }
  }
  # a net does not land: pdngen can still repair the channel with its own M7 strap pair where M7 is free over 2w+sp
  set cur $x0
  foreach q [lsort -integer -index 0 $ob] {
    lassign $q a c
    if {$a - $cur >= 2 * $w + $sp} { return 1 }
    if {$c > $cur} { set cur $c }
  }
  return [expr {$x1 - $cur >= 2 * $w + $sp}]
}
set ot_ft_add {}; set ot_ft_add7 0
foreach ot_r $ot_ft_bl {
  lassign $ot_r ox0 oy0 ox1 oy1 om
  foreach ot_q $ot_ft_bl {
    lassign $ot_q qx0 qy0 qx1 qy1 qm
    if {$qy0 >= $oy1} { break }
    if {$qy1 <= $oy0 || $qx0 <= $ox1} { continue }
    set ya [expr {max($oy0, $qy0)}]; set yb [expr {min($oy1, $qy1)}]
    if {$om != $qm && $qx0 - $ox1 < $ot_ft_sl} { lappend ot_ft_add [list $ox1 $ya $qx0 $yb]; continue }
    if {[ot_ft_m7_ok $ot_ft_o7 $ot_ft_s7 $ox1 $ya $qx0 $yb]} { continue }
    set ot_dup 0
    foreach ot_c $ot_ft_bl { lassign $ot_c cx0 cy0 cx1 cy1 cm
      if {$cy0 > $ya} { break }
      if {!$cm && $cx0 <= $ox1 && $cx1 >= $qx0 && $cy1 >= $yb} { set ot_dup 1; break } }
    if {!$ot_dup} { lappend ot_ft_add [list $ox1 $ya $qx0 $yb]; incr ot_ft_add7 }
  }
}
foreach ot_r $ot_ft_add { odb::dbObstruction_create $ot_ft_blk $ot_ft_m6 {*}$ot_r }
puts "OT_PARTITION_FT_RESERVE m6_sliver_close=[llength $ot_ft_add] m6_no_m7_close=$ot_ft_add7\""""


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


def sliver_tcl():
    """SLIVER_TCL with the top-grid M7 stripe (PDN_WIN_STRIPES_V) filled in."""
    off, w, sp, pitch = PDN_WIN_STRIPES_V['M7']
    return (SLIVER_TCL.replace('@OFF@', f'{off:g}').replace('@W@', f'{w:g}').replace('@SP@', f'{sp:g}')
            .replace('@PITCH@', f'{pitch:g}'))


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


# DIE-HBM-97/SUPDN 11-09 (HBM q_su20 a7 2_4_floorplan_pdn OOM-killed at 50 GB under --mem 48, q_su11 a10 41 GB, while
# q_su11__physical_v1 with the same macros took 8 GB): a column that reaches the outline margin (x0 < core_x0 or
# x1 > width - core_x0, e.g. q_su20 1995.84-2002.32 of a 2004.48 outline beside macro p0 ending at 1995.84) is not a gap
# between two macros, so the window premise does not hold.  Its window puts an M5 strap pair into the 4.32-um core-edge
# pocket, and the 2.27-um row stubs there become one pdngen repair channel per 4.32 um of pocket height (q_su20: 140 of
# 278 listed channels at x 1997.89; an M5 strap in the pocket is enough, the same stubs appear with no reservation at
# all; why individual rails stay unconnected is inferred, not traced).  pdngen repairs one channel per x range per round
# and each round re-runs makeVias; Shape::vias_ is never cleared in the OpenROAD source, and memory grows ~0.39 GB per
# round.  Real pdngen on the q_su20 2_3 DB: base 159 rounds, 57.1 GB, 2378 s; edge columns left plain 47 rounds, 13.2 GB,
# 570 s; both PDNGEN OK, 0 PDN-0178.  q_su11 a10: 41 GB -> 8.8 GB.  q_b101_nw (left edge columns): OK both ways, 1.6 GB.
PDN_CORE_INSET = 4.32


def _gap_columns(rects):
    """[(layer, rect)] tall narrow M5 columns with at least PDN_WIN_COL_ROWS M4 rects of their own x extent inside,
    strictly inside the core in x (an outline-edge column is not a macro gap)."""
    out = []
    # the outline width is the right end of the rows that start at the left outline edge (the full-width FT bands); a
    # receipt without such a row has no known right edge and only the left-edge test applies
    width = max((q[2] for _, q in rects if q[0] <= 1e-6), default=None)
    for layer, rect in rects:
        if layer not in PDN_WIN_COMB:
            continue
        x0, y0, x1, y1 = rect
        if x1 - x0 > PDN_WIN_MIN + 1e-6 or y1 - y0 <= 2 * PDN_WIN_MIN + 1e-6:
            continue
        if x0 < PDN_CORE_INSET - 1e-6 or (width is not None and x1 > width - PDN_CORE_INSET + 1e-6):
            continue
        # own rows: the column's x extent, or (q_b102__physical_v1 572.832-578.88 rows over the 574.29-578.88 column) a row
        # that covers it and is at most twice its width; wider rows (q_b101 0-8.64 over the 2.7-um 5.94-8.64) are streets
        own = sum(1 for L, q in rects if L == 'M4' and q[0] <= x0 + 1e-3 and q[2] >= x1 - 1e-3
                  and q[2] - q[0] <= 2 * (x1 - x0) + 1e-6
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


# DIE-HBM-97/SUPDN 11-09 (q_b001__physical_v1 a11 PDN-0179, 57 PDN-0178 M4 channels x 4.32-25.9, y 28-944): the die reserves
# the whole strip between the outline and the first macro column (M5 x 0-25.92, y 17.28-285.12 and two more, beside
# ot_hbm_hc_bank128_pair_core OBS through M6 at x 25.92) together with M4 rows of the same x extent every 10.8 um.  This is
# the q_b011 pocket above, but wider than PDN_WIN_MIN, so _gap_columns never sees it: each 8.1-um pocket between two M4 rows
# has M4 straps and no M5 over its whole width.  The narrow edge exclusion above does not apply either: at 13-22 um of core
# width this strip is a real pocket, not the 4.32-um core margin.  One M5 strap-pair window at the middle in-core strap
# position feeds it (M5-M6 on the free M6 between the die M6 rows, M6-M7 on the M7 straps left over the strip); no M6 fill
# and no window through the end rows are needed.  Real pdngen on the a11 2_3 DB: window at the first / middle strap / every
# strap -> PDNGEN OK, 0 PDN-0178, 8-8.7 GB, about 6 min each (a11 failed PDN-0179 after 16 min, 12.9 GB).  The width limit
# is what was measured (17.28 and 25.92 um columns); wider edge columns (q_b001 0-138.24) did not fail and stay whole.
# Cost: 0.612 um of M5 per column.
PDN_WIN_EDGE_POCKET_MAX = 4 * PDN_WIN_MIN


def _edge_pockets(rects):
    """[(layer, rect)] M5 columns wider than PDN_WIN_MIN that reach the outline margin and carry their own M4 rows."""
    width = max((q[2] for _, q in rects if q[0] <= 1e-6), default=None)
    out = []
    for layer, rect in rects:
        if layer not in PDN_WIN_COMB:
            continue
        x0, y0, x1, y1 = rect
        if not PDN_WIN_MIN + 1e-6 < x1 - x0 <= PDN_WIN_EDGE_POCKET_MAX + 1e-6 or y1 - y0 <= 2 * PDN_WIN_MIN + 1e-6:
            continue
        if x0 >= PDN_CORE_INSET - 1e-6 and (width is None or x1 <= width - PDN_CORE_INSET + 1e-6):
            continue
        own = sum(1 for L, q in rects if L == 'M4' and q[0] <= x0 + 1e-3 and q[2] >= x1 - 1e-3
                  and q[2] - q[0] <= 2 * (x1 - x0) + 1e-6
                  and q[1] >= y0 - 1e-6 and q[3] <= y1 + 1e-6)
        if own >= PDN_WIN_COL_ROWS:
            out.append((layer, rect))
    return out


def pdn_windows_edge_pocket(receipt, core_x0=PDN_CORE_INSET):
    """[(layer, x0, x1, rect)] one M5 strap-pair window at the middle in-core strap position of each _edge_pockets column."""
    if receipt is None:
        return []
    rects = [(r['layer'], tuple(r['rect'])) for r in receipt['rectangles_um']]
    width = max((q[2] for _, q in rects if q[0] <= 1e-6), default=None)
    out = []
    for layer, rect in _edge_pockets(rects):
        x0, _, x1, _ = rect
        off, wd, sp, pitch = PDN_WIN_COMB[layer]
        k = max(0, int((x0 - core_x0 - off) // pitch))
        fits = []
        while True:
            s = core_x0 + off + k * pitch
            k += 1
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if lo < x0 + PDN_WIN_MARGIN:
                continue
            if hi > x1 - PDN_WIN_MARGIN or (width is not None and hi > width - core_x0):
                break
            fits.append((lo, hi))
        if fits:
            lo, hi = fits[len(fits) // 2]
            out.append((layer, round(lo, 3), round(hi, 3), rect))
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
PDN_WIN_PARTIAL_MIN_UM = 100.0


def _full(row, width):
    x0, y0, x1, y1 = row['rect']
    if row['layer'] not in PDN_WIN_STRIPES:
        return False
    if x0 <= PDN_WIN_FULL_TOL and x1 >= width - PDN_WIN_FULL_TOL:
        return True
    # DIE-HBM-97 11-09: a TALL band bounded by macros (q_b100__physical_v1 M6 0-259.2 x 423-527 of a 734.4 outline) is a band too
    return y1 - y0 > PDN_WIN_MIN + 1e-6 and x1 - x0 >= PDN_WIN_PARTIAL_MIN_UM


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
    bands = _bands(receipt, width)
    for L, y0, y1 in bands:
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


# DIE-HBM-97 11-09 (q_b100__physical_v1 / q_b101 / q_b101_nw PDN-0179, M5 channels in a strip): a tall macro-bounded
# M6 band (pdn_windows above) can end in a narrow STRIP between two macro rows (q_b100__physical_v1 y 515.4-527.0 between
# ot_hbm_idx_score_hcol_h1 and u_ra/u_rb, all OBS to M6) where the die reserves M4 and M6 across the band and M5 as
# columns + teeth.  The M5 strap pieces under the teeth reach neither M4, M6 nor the macros: islands.  One M6 strap-pair
# window at the lowest strap position inside the strip's M4 reservation joins them (bisect: removing the band's M6
# clears the strip; a window near the band edge above the teeth does not).
def _m4_strips(rows):
    """[(x0, y0, x1, y1)] wide M4 rows, with abutting rows of one stack (q_b101_nw y 1302.048 / 1303.02 / 1311.12, each
    alone thinner than a strap pair or not holding the M5 teeth) merged into one strip of at most 2 * PDN_WIN_MIN."""
    return _thin_runs(rows, 'M4')


def _thin_runs(rows, layer):
    m4 = sorted(tuple(r['rect']) for r in rows if r['layer'] == layer and r['rect'][2] - r['rect'][0] >= PDN_WIN_PARTIAL_MIN_UM
                and r['rect'][3] - r['rect'][1] <= 2 * PDN_WIN_MIN)
    m4.sort(key=lambda b: (b[1], b[0]))
    runs = []
    for b in m4:
        for run in runs:
            if abs(run[3] - b[1]) < 1e-6 and min(run[2], b[2]) - max(run[0], b[0]) >= 0.9 * min(run[2] - run[0], b[2] - b[0]) \
                    and b[3] - run[1] <= 2 * PDN_WIN_MIN + 1e-6:
                run[:] = [min(run[0], b[0]), run[1], max(run[2], b[2]), b[3]]
                break
        else:
            runs.append(list(b))
    return [tuple(r) for r in runs]


def pdn_windows_strip(receipt, width=None, core_y0=4.32, strips=None):
    """[(layer, y0, y1)] one M6 window per narrow (<= 2 * PDN_WIN_MIN), wide M4 strip lying wholly under wide M6."""
    if receipt is None:
        return []
    width = _width(receipt, width)
    off, wd, sp, pitch = PDN_WIN_STRIPES['M6']
    rows = receipt['rectangles_um']
    out = []
    m6s = [r['rect'] for r in rows if r['layer'] == 'M6' and r['rect'][2] - r['rect'][0] >= PDN_WIN_PARTIAL_MIN_UM]
    # DIE-HBM-97 11-09 (q_b102__physical_v1 y 4.32-11.07 core bottom, y 1116.72-1123.2 teeth): a thin stack of wide M6
    # rows with no M4 under it blocks every M6 strap position of its span just the same
    m6w = [tuple(r) for r in m6s]
    m6runs = [b for b in _thin_runs(rows, 'M6') if b[3] - b[1] <= 2 * PDN_WIN_MIN + 1e-6
              and not any(q[0] < b[2] and q[2] > b[0] and (abs(q[1] - b[3]) < 1e-6 or abs(q[3] - b[1]) < 1e-6)
                          for q in m6w)]   # an isolated stack only; a taller stack is pdn_windows' tall band
    m4s = _m4_strips(rows)
    done = []                              # M4 strips that got a window: an M6 run over one adds nothing
    for x0, y0, x1, y1 in m4s + [b for b in m6runs if b not in m4s]:
        if (x0, y0, x1, y1) not in m4s and any(q[0] < x1 and q[2] > x0 and q[1] < y1 and q[3] > y0 for q in done):
            continue
        # the strip's whole height is under cuttable (band) M6 over at least 90 % of its width
        cov = sorted((max(r[1], y0), min(r[3], y1)) for r in m6s
                     if r[1] < y1 and r[3] > y0 and min(r[2], x1) - max(r[0], x0) >= 0.9 * (x1 - x0))
        cur = y0
        for a_, b_ in cov:
            if a_ > cur + 1e-6:
                break
            cur = max(cur, b_)
        if cur < y1 - 1e-6 and (x0, y0, x1, y1) in m4s:   # an M6 run is its own cover
            continue
        k = math.ceil((y0 + 2 * PDN_WIN_MARGIN - core_y0 - off) / pitch - 1e-9)
        s = core_y0 + off + k * pitch
        lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
        if hi <= y1 - PDN_WIN_MARGIN:
            w = ('M6', round(lo, 3), round(hi, 3))
            if w not in out:
                out.append(w)
            done.append((x0, y0, x1, y1))
            if strips is not None:
                strips.append((x0, y0, x1, y1))
    return out


def pdn_windows_strip_m5(receipt, width=None, core_x0=4.32):
    """[(layer, x0, x1, rect)] M5 strap windows through the M5 columns/teeth inside a pdn_windows_strip strip, so the strap
    pieces under them (between the lower macro and the column, q_b101 y 1301.7-1302.0) reach the strip's M6 window."""
    if receipt is None:
        return []
    strips = []
    pdn_windows_strip(receipt, width, strips=strips)
    off, wd, sp, pitch = PDN_WIN_COMB['M5']
    out = []
    for r in receipt['rectangles_um']:
        if r['layer'] != 'M5':
            continue
        x0, y0, x1, y1 = r['rect']
        # inside the strip, or mostly so (q_b101_nw x 358.56 y 295.92-306.72: a column piece entering the strip from below
        # holds the strap between the tooth above and the strip's M6 window)
        if x1 - x0 > PDN_WIN_MIN + 1e-6 or not any(min(y1, sy1) - max(y0, sy0) >= 0.5 * (y1 - y0) - 1e-6
                                                   and sx0 <= x0 and x1 <= sx1 for sx0, sy0, sx1, sy1 in strips):
            continue
        k = max(0, int((x0 - core_x0 - off) // pitch) - 1)
        while True:
            s = core_x0 + off + k * pitch
            k += 1
            lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
            if hi <= x0:
                continue
            if lo >= x1:
                break
            # a strap pair over the column edge is clipped to the column (the piece under it must escape too)
            out.append(('M5', round(max(lo, x0), 3), round(min(hi, x1), 3), tuple(r['rect'])))
    return out


# DIE-HBM-97 11-10 (q_b000 / q_b000__physical_v1 PDN-0179, M3 channels in the 8.64-um streets of the abutted bank128_pair
# stack): the street between two stacked macros has all of M4 reserved, so its M3 bridge straps have no M4 strap to land on.
# pdn_windows only cuts tall bands on a 21.6-um grid, which an 8.64-um street can miss (q_b000 pv1: the streets at y 1926.72
# and 2203.2 get a window and pass, y 1373.76 and 1650.24 get none and fail).  On the q_b000 tapcell DB, one M4 strap-pair
# window per street gave 0 PDN-0178 / 0 PDN-0179; extending or merging the M4 rows did not.  Streets come from the plan's
# hard cores, not the receipt, so partition_ft_reservation.json and every kit without such a street stay byte-identical.
def macro_boxes(typ):
    """[(x0, y0, x1, y1)] of the type's hard cores in type coordinates."""
    return [(c['origin_um'][0], c['origin_um'][1], c['origin_um'][0] + c['outline_um'][0], c['origin_um'][1] + c['outline_um'][1])
            for c in typ.get('hard_cores', ()) if c.get('origin_um') and c.get('outline_um')]


# DIE-HBM-97 11-10 (q_b102 PDN-0179, PDN-0178 "Remaining channel (235.284, 445.896) - (244.236, 447.048) on M5"): the
# same island one layer pair up.  In the 3.456-um street between the stacked hcol macros k2h0 (top 445.824) and k2h1
# (449.28) the die reserves M6 over the lower 1.296 um across the whole street, M4 over the rest, and an M5 tooth
# (239.76-246.51, from 447.12) over the street's west end.  The M5 strap pair at x 243.984 is then a piece 445.824-447.12,
# capped by the lower macro and the tooth: its one M6 strap position (446.928) lies in the reserved M6 row, and the M4
# bridge straps (442.8, 447.12) miss it, so it has no partner on either side and pdngen cannot repair the channel (M6 is
# reserved inside it).  M6 over M5 gets the street rule too, on the lower layer's real pieces: every M5 strap-pair piece
# of the street (the street's y-span at an M5 strap x, cut by the M5 reservation over that x) that holds no strap of the
# M6 grid nor of the M4 bridge grid clear of the reservation of that layer is an island, and its street gets one M6
# strap-pair window (the usual pair + PDN_WIN_MARGIN, inside a reserved row if one fits, else overlapping one).  M4 over
# M3 keeps the wholly-reserved test: the M3 bridges are not cut inside a street, so their piece is the whole street.  On
# the q_b102 tapcell DB the one M6 window (446.778-447.75) gave 0 PDN-0178 / 0 PDN-0179.  M7 needs no street rule: a
# horizontal street is crossed by the vertical M7 grid, and M6 pieces under reserved M7 are closed by SLIVER_TCL.
# DIE-HBM-PDN-1 11-11 (q_b103 PDN-0179, 20 PDN-0178 M5 channels 8.95 x 2.8 um at y 195.84-198.65 along the 11.62-um street between
# hcol h1 (top 195.74) and the h0 ra/rb row above (bottom 207.36); q_b102/q_b103 share the layout): the same M5 islands as
# the 3.456-um q_b102 street, but the street rule stopped at PDN_WIN_MIN (8.64 um).  Streets up to 2 * PDN_WIN_MIN get it
# too; the rule still adds a window only where _m5_street_islands finds an island piece (M6) or M4 is wholly reserved.
PDN_STREET_MAX = 2 * PDN_WIN_MIN
STREET_LAYERS = ('M4', 'M6')               # strap layer over the layer it partners in a street: M4 over M3, M6 over M5


def _strap_spans(layer, lo, hi, core):
    """[(a, b)] the two straps (VSS, VDD) of every grid pair of a PDN_WIN_STRIPES/PDN_WIN_COMB layer near [lo, hi]."""
    off, wd, sp, pitch = PDN_WIN_STRIPES[layer] if layer in PDN_WIN_STRIPES else PDN_WIN_COMB[layer]
    out = []
    for k in range(math.floor((lo - core - off) / pitch) - 1, math.ceil((hi - core - off) / pitch) + 1):
        s = core + off + k * pitch                 # pdngen: the offset is the centre of the first strap
        out += [(s - wd / 2, s + wd / 2), (s + wd / 2 + sp, s + 1.5 * wd + sp)]
    return out


def _m5_street_islands(rects, y0, y1, xa, xb, bridge, core_x0=4.32, core_y0=4.32, wins=()):
    """[(x, y0, y1)] M5 strap pieces of the street [xa, xb] x [y0, y1] with no clear M6 strap (and no clear M4 bridge
    strap when the row bridge is on) inside their y-span; a strap inside a window of wins [(layer, y0, y1)] is clear."""
    def cut(layer, a, b):
        return [r for r in rects if r[0] == layer and r[1] < b - 1e-6 and r[3] > a + 1e-6]
    out = []
    for xs0, xs1 in _strap_spans('M5', xa, xb, core_x0):
        if xs0 < xa - 1e-6 or xs1 > xb + 1e-6:
            continue
        cur, pieces = y0, []
        for r in sorted(cut('M5', xs0, xs1), key=lambda q: q[2]):
            if r[2] < y1 - 1e-6 and r[4] > cur + 1e-6:
                if r[2] > cur + 1e-6:
                    pieces.append((cur, r[2]))
                cur = max(cur, r[4])
        if y1 > cur + 1e-6:
            pieces.append((cur, y1))
        for p0, p1 in pieces:
            land = False
            for layer in ('M6', 'M4') if bridge else ('M6',):
                blk = cut(layer, xs0, xs1)
                if any(a >= p0 - 1e-6 and b <= p1 + 1e-6 and (not any(r[2] < b - 1e-6 and r[4] > a + 1e-6 for r in blk)
                       or any(L == layer and w0 <= a + 1e-6 and w1 >= b - 1e-6 for L, w0, w1 in wins))
                       for a, b in _strap_spans(layer, p0, p1, core_y0)):
                    land = True
                    break
            if not land:
                out.append((round(xs0, 3), round(p0, 3), round(p1, 3)))
    return out


# DIE-HBM-98 11-11 (q_b002 a10 PDN-0179, 304 PDN-0178 M4 channels across the tile; plan p11t_taps_cyc 29333b2b): the plan's
# M5 + M7 die_ft_bands give the die ALL of M5 and M7 over the type (die_share 1.0, core_share 1.0, the full 380.16-um
# width), so the partition reserves M5 everywhere except over the hard cores, where macro OBS blocks M5 anyway.  The tile
# then has no M5 strap anywhere: the M1/M2 rails and the M3/M4 row bridge have no layer up to M6/M7 (M7 is windowed by
# pdn_windows_v), and every M4 strap piece is an unrepairable channel.  core_zero (FTRES-FIX) does not change it: both
# arms reserve M7 1,641,066 um^2 (the whole outline) and M5 981,227 um^2 on this plan.  When the free M5 left inside the
# core area outside the hard cores is below PDN_M5_FREE_MIN of that area, every M5 rect wider than PDN_WIN_MIN keeps one
# strap-pair window at every PDN_WIN_EVERY_M5-th M5 strap of the top grid (core x0 + offset + k * pitch, k on ONE global
# phase so the windows of stacked rects line up into one strap through columns and street rows).  Cost in such a type:
# 0.462 um of M5 per 17.28 um (2.7 %), which the die FT router sees in the abstract.  Types with free M5 are unchanged.
PDN_WIN_EVERY_M5 = 4
PDN_M5_FREE_MIN = 0.01


def _m5_wholly_reserved(receipt, width, boxes, core=PDN_CORE_INSET):
    try:
        from . import die_trial as D
    except ImportError:
        import die_trial as D
    height = max(r['rect'][3] for r in receipt['rectangles_um'])
    cx0, cy0, cx1, cy1 = core, core, width - core, height - core
    blk = [tuple(r['rect']) for r in receipt['rectangles_um'] if r['layer'] == 'M5'] + [tuple(b) for b in boxes]
    blk = [(max(a, cx0) - cx0, max(b, cy0) - cy0, min(c, cx1) - cx0, min(d, cy1) - cy0) for a, b, c, d in blk]
    blk = [q for q in blk if q[2] > q[0] + 1e-9 and q[3] > q[1] + 1e-9]
    free = sum((c - a) * (d - b) for a, b, c, d in D._uncovered(cx1 - cx0, cy1 - cy0, blk))
    return free < PDN_M5_FREE_MIN * (cx1 - cx0) * (cy1 - cy0)


# DIE-HBM-PDN-1 11-11 (q_b011__physical_v1 PDN-0179, 117 PDN-0178 M4 channels, 113 of them with no free M5 anywhere in the
# channel; q_b011 and the other ra-column types would follow): the same starvation as above, but LOCAL.  The die reserves
# M5 over whole strips beside the hard cores (q_b011: x 276.48-380.16 beside every bank macro, x 239.76-380.16 beside every
# hcol h1, x 0-25.76 along the west edge, 194-292 um tall), while some other part of the type keeps free M5, so the
# type-wide test (_m5_wholly_reserved) does not fire.  Every M4 bridge strap that lands in an M4 gap between the FT rows
# of such a strip has no M4-M5 via and pdngen reports a channel it cannot repair.  A wide, tall M5 rect with an M4 gap
# inside it (PDN_POCKET_MIN) and no strap window from any other rule keeps the same every-PDN_WIN_EVERY_M5 window grid.
# Wide M5 rects that hold no M4 gap, short rows (streets, teeth) and rects another rule already windowed are unchanged.
PDN_POCKET_MIN = 2.0
PDN_ROW_MIN = 4.32                              # thinner rows keep their M5 whole: a strap piece in them has no partner layer


def _m5_windowed(receipt):
    """{rect: [(lo, hi)]} the strap windows the comb / column / strip / edge-pocket rules cut into each M5 receipt rect."""
    out = {}
    for fn in (pdn_windows_comb, pdn_windows_col, pdn_windows_strip_m5, pdn_windows_edge_pocket):
        for L, lo, hi, rr in fn(receipt):
            if L == 'M5':
                out.setdefault(tuple(rr), []).append((lo, hi))
    return out


def _m5_starved_rects(receipt):
    """{rect: None | [(lo, hi)]} the wide, tall M5 receipt rects holding an M4 gap (a y-run of at least PDN_POCKET_MIN not
    covered by an M4 row spanning 90 % of the rect's width, at least one such row present) and no strap window from the
    comb / column / strip / edge-pocket rules (None: the global window grid), plus the short wide rows (PDN_ROW_MIN to
    2 * PDN_WIN_MIN tall, no wider than the strip + PDN_WIN_MIN) that stack on a starved or already windowed strip: they
    carry the strip's windows on (the grid, or the windows of the strip they stack on) so its straps run through them."""
    rects = [tuple(r['rect']) for r in receipt['rectangles_um'] if r['layer'] == 'M5']
    m4 = [tuple(r['rect']) for r in receipt['rectangles_um'] if r['layer'] == 'M4']
    done = _m5_windowed(receipt)
    out = {}
    for x0, y0, x1, y1 in rects:
        if x1 - x0 <= PDN_WIN_MIN + 1e-6 or y1 - y0 <= 2 * PDN_WIN_MIN + 1e-6 or (x0, y0, x1, y1) in done:
            continue
        rows = sorted((max(b[1], y0), min(b[3], y1)) for b in m4 if b[1] < y1 and b[3] > y0 and b[0] < x1 and b[2] > x0
                      and min(b[2], x1) - max(b[0], x0) >= 0.9 * (x1 - x0))
        if not rows:
            continue                            # no FT M4 pattern in the rect: not the strip case
        cur, gap = rows[0][1], False
        for a, b in rows[1:]:
            gap = gap or a - cur >= PDN_POCKET_MIN - 1e-6
            cur = max(cur, b)
        if gap or rows[0][0] - y0 >= PDN_POCKET_MIN - 1e-6 or y1 - cur >= PDN_POCKET_MIN - 1e-6:
            out[(x0, y0, x1, y1)] = None
    if out:
        todo = [q for q in rects if q not in out and q not in done and q[2] - q[0] > PDN_WIN_MIN + 1e-6
                and PDN_ROW_MIN - 1e-6 <= q[3] - q[1] <= 2 * PDN_WIN_MIN + 1e-6]
        grow = True
        while grow:
            grow = False
            for q in todo:
                if q in out:
                    continue
                for t in sorted(set(out) | set(done)):
                    if ((abs(q[3] - t[1]) < 1e-6 or abs(q[1] - t[3]) < 1e-6) and min(q[2], t[2]) - max(q[0], t[0]) > PDN_WIN_MIN
                            and q[0] >= t[0] - PDN_WIN_MIN and q[2] <= t[2] + PDN_WIN_MIN):
                        out[q] = list(done[t]) if t in done else out[t]
                        grow = True
                        break
    return out


def pdn_windows_m5_full(receipt, width=None, core_x0=PDN_CORE_INSET, boxes=None):
    """[(layer, x0, x1, rect)] M5 strap-pair windows on a global every-PDN_WIN_EVERY_M5 grid: in every wide M5 rect when
    the receipt leaves no free M5 outside the hard cores, else only in the starved rects (_m5_starved_rects).  Macro boxes
    required; without them nothing changes."""
    if receipt is None or not boxes or not any(r['layer'] == 'M5' for r in receipt['rectangles_um']):
        return []
    width = _width(receipt, width)
    only = None if _m5_wholly_reserved(receipt, width, boxes) else _m5_starved_rects(receipt)
    if only is not None and not only:
        return []
    off, wd, sp, pitch = PDN_WIN_COMB['M5']
    lo_of = lambda k: core_x0 + off + k * pitch - PDN_WIN_MARGIN
    hi_of = lambda k: core_x0 + off + k * pitch + 2 * wd + sp + PDN_WIN_MARGIN
    # the strap next to each hard-core x edge too (q_b002 probe, grid only: 129 M4 channels left in x 276.4-280.7, the
    # 6.2 um between the bank macros' right edge 276.48 and the first grid window 282.714); same set for every rect
    edge = set()
    for bx0, _, bx1, _ in boxes:
        edge.add(math.ceil((bx1 + PDN_WIN_MARGIN - core_x0 - off) / pitch - 1e-9))               # first window clear right of it
        edge.add(math.floor((bx0 - PDN_WIN_MARGIN - core_x0 - off - 2 * wd - sp) / pitch + 1e-9))  # last window clear left of it
    out = []
    for r in receipt['rectangles_um']:
        if r['layer'] != 'M5':
            continue
        x0, y0, x1, y1 = r['rect']
        if x1 - x0 <= PDN_WIN_MIN + 1e-6 or (only is not None and (x0, y0, x1, y1) not in only):
            continue
        if only is not None and only[(x0, y0, x1, y1)] is not None:       # a row stacked on a windowed strip: that strip's windows
            for lo, hi in sorted(only[(x0, y0, x1, y1)]):
                if lo >= x0 - 1e-9 and hi <= x1 + 1e-9:
                    out.append(('M5', lo, hi, tuple(r['rect'])))
            continue
        k = max(0, int((x0 - core_x0 - off) // pitch))
        while True:
            kk, k = k, k + 1
            lo, hi = lo_of(kk), hi_of(kk)
            if lo < x0 + PDN_WIN_MARGIN or lo < core_x0:
                continue
            if hi > x1 - PDN_WIN_MARGIN or hi > width - core_x0:
                break
            if kk % PDN_WIN_EVERY_M5 and kk not in edge:
                continue
            out.append(('M5', round(lo, 3), round(hi, 3), tuple(r['rect'])))
    return out


def pdn_windows_street(receipt, width=None, core_y0=4.32, boxes=None, existing=()):
    """[(layer, y0, y1)] one strap window per macro street and STREET_LAYERS layer whose lower layer has no partner
    there (M4: the street wholly reserved on M4; M6: an M5 island piece, _m5_street_islands) and no window yet."""
    if receipt is None or not boxes:
        return []
    streets = {}
    for a in boxes:
        for b in boxes:
            xa, xb = max(a[0], b[0]), min(a[2], b[2])
            if 0 < b[1] - a[3] <= PDN_STREET_MAX + 1e-6 and xb - xa >= 0.5 * min(a[2] - a[0], b[2] - b[0]):
                old = streets.get((a[3], b[1]))
                streets[(a[3], b[1])] = (min(xa, old[0]), max(xb, old[1])) if old else (xa, xb)
    rects = [(r['layer'], *r['rect']) for r in receipt['rectangles_um']]
    bridge = blocks_rows(receipt, _width(receipt, width))
    out = []
    for layer in STREET_LAYERS:
        off, wd, sp, pitch = PDN_WIN_STRIPES[layer]
        rows = sorted((r['rect'] for r in receipt['rectangles_um']
                       if r['layer'] == layer and r['rect'][2] - r['rect'][0] >= PDN_WIN_PARTIAL_MIN_UM), key=lambda q: (q[1], q[0]))
        for (y0, y1), (xa, xb) in sorted(streets.items()):
            cov = [r for r in rows if r[1] < y1 - 1e-6 and r[3] > y0 + 1e-6 and r[0] <= xa + 1e-6 and r[2] >= xb - 1e-6]
            if not cov or any(L == layer and a < y1 and b > y0 for L, a, b in list(existing) + out):
                continue
            if layer == 'M4':
                cur = y0
                for r in cov:
                    if r[1] > cur + 1e-6:
                        break
                    cur = max(cur, r[3])
                if cur < y1 - 1e-6:
                    continue
            elif not _m5_street_islands(rects, y0, y1, xa, xb, bridge, core_y0=core_y0, wins=list(existing) + out):
                continue
            fits = []
            for k in range(math.floor((y0 - core_y0 - off) / pitch), math.ceil((y1 - core_y0 - off) / pitch) + 1):
                s = core_y0 + off + k * pitch
                lo, hi = s - PDN_WIN_MARGIN, s + 2 * wd + sp + PDN_WIN_MARGIN
                if lo >= y0 + PDN_WIN_MARGIN - 1e-6 and hi <= y1 - PDN_WIN_MARGIN + 1e-6:
                    fits.append((lo, hi))
            inside = [w for w in fits if any(w[0] >= r[1] + PDN_WIN_MARGIN - 1e-6 and w[1] <= r[3] - PDN_WIN_MARGIN + 1e-6 for r in cov)]
            over = [w for w in fits if any(w[0] < r[3] - 1e-6 and w[1] > r[1] + 1e-6 for r in cov)]
            pick = (inside or over or fits)[:1]
            out += [(layer, round(lo, 3), round(hi, 3)) for lo, hi in pick]
    return out


def obstruction_rows(receipt, width=None, core_y0=4.32, macro_boxes=None):
    """[(layer, rect)] the obstructions to create: the receipt rectangles, tall full-width M4/M6 bands split at
    pdn_windows."""
    width = _width(receipt, width)
    swins = pdn_windows_strip(receipt, width, core_y0)
    wins = pdn_windows(receipt, width, core_y0) + swins
    stwins = pdn_windows_street(receipt, width, core_y0, macro_boxes, wins)
    wins = wins + stwins
    vwins = pdn_windows_v(receipt) + pdn_windows_comb(receipt) + pdn_windows_col(receipt) + pdn_windows_strip_m5(receipt, width) + pdn_windows_edge_pocket(receipt) \
        + pdn_windows_m5_full(receipt, width, boxes=macro_boxes)
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
        if _full(r, width):
            mine = sorted((max(a, y0), min(b, y1)) for L, a, b in wins if L == r['layer'] and a < y1 and b > y0)
        elif r['layer'] == 'M6' and x1 - x0 >= PDN_WIN_PARTIAL_MIN_UM:      # strip + street windows cut the wide partial M6 rows too
            mine = sorted((max(a, y0), min(b, y1)) for L, a, b in swins + stwins if L == 'M6' and a < y1 and b > y0)
        elif r['layer'] == 'M4' and x1 - x0 >= PDN_WIN_PARTIAL_MIN_UM:      # street windows cut the wide partial M4 rows too
            mine = sorted((max(a, y0), min(b, y1)) for L, a, b in stwins if L == 'M4' and a < y1 and b > y0)
        else:
            mine = []
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
