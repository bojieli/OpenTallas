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
PDN_WIN_STRIPES = {'M4': (2.16, 0.12, 0.072, 4.32),      # offset, width, spacing, pitch = BRIDGE_M4
                   'M6': (1.968, 0.288, 0.096, 4.32)}    # = gen_phys PG_M6 / the top-grid M6 stripe


def _full(row, width):
    x0, y0, x1, y1 = row['rect']
    return row['layer'] in PDN_WIN_STRIPES and x0 <= 1e-6 and x1 >= width - 1e-6


def _width(receipt, width):
    return width if width is not None else max((r['rect'][2] for r in receipt['rectangles_um']), default=0.0)


def pdn_windows(receipt, width=None, core_y0=4.32):
    """[(layer, y0, y1)] PDN strap windows cut out of tall full-width M4/M6 bands (see PDN_WIN_MIN)."""
    if receipt is None:
        return []
    width = _width(receipt, width)
    out = []
    for r in receipt['rectangles_um']:
        if not _full(r, width):
            continue
        y0, y1 = r['rect'][1], r['rect'][3]
        if y1 - y0 <= PDN_WIN_MIN:
            continue
        off, wd, sp, pitch = PDN_WIN_STRIPES[r['layer']]
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
            out.append((r['layer'], round(lo, 3), round(hi, 3)))
    return out


def obstruction_rows(receipt, width=None, core_y0=4.32):
    """[(layer, rect)] the obstructions to create: the receipt rectangles, tall full-width M4/M6 bands split at
    pdn_windows."""
    width = _width(receipt, width)
    wins = pdn_windows(receipt, width, core_y0)
    out = []
    for r in receipt['rectangles_um']:
        x0, y0, x1, y1 = r['rect']
        mine = sorted((a, b) for L, a, b in wins if L == r['layer'] and y0 < a and b < y1) if _full(r, width) else []
        cur = y0
        for a, b in mine:
            out.append((r['layer'], [x0, cur, x1, a]))
            cur = b
        out.append((r['layer'], [x0, cur, x1, y1]))
    return out


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
