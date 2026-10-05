#!/usr/bin/env python3
"""Macro-packed floorplans of the Qwen3-8B O4 ROM die and HBM-weight comparator die (rung 3).

For each design this places every memory macro the die needs as a real ASAP7
LEF view (ROM, SRAM, HBM3E PHY abstracts), snapped to the PDN lattice, with
halos, pin-facing orientation and logic channels sized from synthesised cell
area; reserves the regions that have no view yet (UCIe PHY, collective); and
lays out registered transport corridors. It then checks legality (inside the
die, no overlap, lattice, halo, orientation) and prices every cross-region
connection against the adopted clock with the routed wire-delay fit of
tools/chip_assembly.floorplans.wire_delay_model: registers the RTL already
provides versus registers the distance needs, and the cycles that adds to
the token.

Inputs (source-pinned in the record): the integer ROM placement
(qwen_o4_rom_placement.json), the RTL inventory (qwen_o4_die_inventory.json),
the cluster and unit syntheses, the ASAP7 macro views and qwen3_budget.json.

Outputs per design: <out>/<design>.json (geometry, checks, budgets),
<design>_macros.def (every macro PLACED/FIXED), <design>.svg, and for the ROM
die the neighbourhood macro-placement TCL the route cut uses.

Not established: routability of the die (rung 5), timing of any path (only
distances are priced), power integrity, or any N6 area.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from chip_assembly import floorplans as CAF  # noqa: E402

OUT_DIR = ROOT / 'results/floorplan/qwen_o4'
INPUTS = ['results/floorplan/qwen_o4_rom_placement.json', 'results/floorplan/qwen_o4_die_inventory.json',
          'results/floorplan/qwen_o4_cluster_synth.json', 'results/floorplan/qwen_o4_unit_areas.json',
          'physical/asap7_memory_macros/index.json', 'results/arch/qwen3_budget.json',
          'physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.lef',
          'physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.lef',
          'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.lef',
          'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.lef',
          'docs/QWEN_O4_HBM_WEIGHT_SUPPLY.md']

# die: the 815 mm2 reticle-class outline shared with docs/V41_PHYSICAL_FLOORPLAN.md
DIE_W, DIE_H = 31800.0, 815e6 / 31800.0
SNAP_X, SNAP_Y = 0.432, 2.16          # macro origin lattice (PDN strap pitch / 8 rows)
HALO_X, HALO_Y = 4.32, 2.16            # macro keep-out for pin escape
CLOCK_NS = 1e9 / 1098640000.0
UNC_NS = 0.060
LOGIC_UTIL = 0.50                      # std-cell density in logic channels (replaced by routed records)
CORRIDOR_UM = 60.0                     # registered transport corridor width
EDGE_KEEP = 20.0
# KV ring slice in every tile: the O4 ledger ring (kv_prefetch_buffer_bytes, FP8) spread over
# 6,144 groups is 3,141 B a group; 128-bit FP8 words, two groups a 256-bit macro word, 256 deep
KV_MACRO = 'ot_sram_1r1w_128x256_m1_r2c2'
KV_PER_TILE = 4

MV = {}                                # macro views (w, h) from the catalogue


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def snap(v, q):
    return round(math.ceil(v / q - 1e-9) * q, 3)


class Plan:
    def __init__(self, name):
        self.name = name
        self.macros = []               # dict(inst, macro, x, y, orient, w, h, region)
        self.regions = []              # dict(name, kind, x, y, w, h, ...)

    def macro(self, inst, macro, x, y, orient, region):
        w, h = MV[macro]
        self.macros.append(dict(inst=inst, macro=macro, x=round(x, 3), y=round(y, 3), orient=orient,
                                w=w, h=h, region=region))

    def region(self, name, kind, x, y, w, h, **kw):
        r = dict(name=name, kind=kind, x=round(x, 3), y=round(y, 3), w=round(w, 3), h=round(h, 3))
        r.update(kw)
        self.regions.append(r)
        return r


# --------------------------------------------------------------------------- tiles
def rom_tile(logic_um2, scale_macros=0):
    """Neighbourhood of 4 groups x 16 lanes: 2 pair columns x 11 code banks.

    Each pair's 11 banks split into two stacks (6 + 5); four stacks stand
    between logic channels. Every ROM macro has data pins on BOTH vertical
    edges in its lowest 14 um (LEF), so every stack faces a channel on each
    side; bank outputs, their select/OR and the matvec MEM_PIPE capture sit in
    the channel beside the pins. Scale banks (result-port tiles) cap the
    short stacks.
    """
    mw, mh = MV['ot_rom_4096x266_m8']
    pitch_y = snap(mh + 2 * HALO_Y, SNAP_Y)
    stacks = [6, 5, 6, 5]
    extra = [0, 0, 0, 0]
    for i in range(scale_macros):
        extra[(1, 3, 0, 2)[i % 4]] += 1
    rows = max(s + e for s, e in zip(stacks, extra))
    kw, kh = MV[KV_MACRO]
    kv_y = snap(rows * pitch_y + HALO_Y, SNAP_Y)
    h = snap(kv_y + kh + 2 * HALO_Y, SNAP_Y)
    chan_area = logic_um2 / LOGIC_UTIL
    # four channels per tile period (edge channels are shared with the neighbour)
    c = snap(chan_area / (4 * h), SNAP_X)
    col_w = snap(mw + 2 * HALO_X, SNAP_X)
    w = snap(4 * col_w + 4 * c, SNAP_X)
    macros = []
    x = c / 2
    for s in range(4):
        orient = 'R0'
        for r in range(stacks[s] + extra[s]):
            kind = 'code' if r < stacks[s] else 'scale'
            macros.append(dict(stack=s, row=r, kind=kind, x=snap(x + HALO_X, SNAP_X),
                               y=snap(HALO_Y + r * pitch_y, SNAP_Y), orient=orient))
        x += col_w + c
    kv_pitch = w / KV_PER_TILE
    for i in range(KV_PER_TILE):
        macros.append(dict(stack=None, row=None, kind='kv', macro=KV_MACRO,
                           x=snap(i * kv_pitch + (kv_pitch - kw) / 2, SNAP_X), y=kv_y, orient='R0'))
    return dict(w=w, h=h, channel_um=c, column_um=col_w, pitch_y=pitch_y, stacks=stacks,
                scale_extra=extra, macros=macros, macro='ot_rom_4096x266_m8',
                logic_um2=logic_um2, util=LOGIC_UTIL)


def stream_tile(logic_um2):
    """HBM-comparator neighbourhood: code ROM replaced by a weight-window SRAM.

    One ot_sram_1r1w_1024x256 per group-pair column: 1,024 words of the
    column's 256-bit slice, i.e. two 512-word windows (docs/QWEN_O4_HBM_WEIGHT_SUPPLY.md:
    a gate/up K round needs a 512-word window; one fills while one drains).
    The tile's KV ring slice is the same as the ROM tile's.
    """
    mw, mh = MV['ot_sram_1r1w_1024x256_m2_r2c2']
    kw, kh = MV[KV_MACRO]
    col_w = snap(mw + 2 * HALO_X, SNAP_X)
    w = snap(2 * col_w, SNAP_X)
    chan_area = logic_um2 / LOGIC_UTIL
    band = snap(chan_area / w, SNAP_Y)
    wy = snap(band + HALO_Y, SNAP_Y)
    macros = [dict(stack=i, row=0, kind='window', x=snap(i * col_w + HALO_X, SNAP_X), y=wy, orient='R0')
              for i in range(2)]
    kv_y = snap(wy + mh + 2 * HALO_Y, SNAP_Y)
    per_row = max(1, int(w // (kw + 2 * HALO_X)))
    for i in range(KV_PER_TILE):
        r, c = divmod(i, per_row)
        macros.append(dict(stack=None, row=None, kind='kv', macro=KV_MACRO,
                           x=snap(HALO_X + c * (kw + 2 * HALO_X), SNAP_X),
                           y=snap(kv_y + r * (kh + 2 * HALO_Y), SNAP_Y), orient='R0'))
    rows = -(-KV_PER_TILE // per_row)
    h = snap(kv_y + rows * (kh + 2 * HALO_Y) + HALO_Y, SNAP_Y)
    return dict(w=w, h=h, band_um=band, macros=macros,
                macro='ot_sram_1r1w_1024x256_m2_r2c2', logic_um2=logic_um2, util=LOGIC_UTIL)


PLACE_PROC = r"""set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} {
    dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName]
  }
}
proc ot_place {name x y orient} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}
"""


def placement_tcl(entries, path, header):
    lines = [f'# Written by tools/qwen_o4_floorplan.py: {header}', PLACE_PROC]
    for inst, x, y, orient in entries:
        lines.append(f'ot_place {{{inst}}} {x} {y} {orient}')
    lines.append(f'puts "ot_place: {len(entries)} macros placed"')
    Path(path).write_text('\n'.join(lines) + '\n')


def neighbourhood_tcl(tile, path):
    """Macro placement for the route cut (ORFS MACRO_PLACEMENT_TCL), names after flattening."""
    code_i = {0: 0, 1: 0}
    scale_g = 0
    entries = []
    for m in tile['macros']:
        if m['kind'] == 'kv':
            continue
        if m['kind'] == 'code':
            pair = m['stack'] // 2
            b = code_i[pair]
            code_i[pair] += 1
            inst = f'g_pair[{pair}].g_bank[{b}].u_rom'
        else:
            inst = f'g_scale.g_grp[{scale_g}].g_bank[0].u_rom'
            scale_g += 1
        entries.append((inst, m['x'], m['y'], m['orient']))
    placement_tcl(entries, path, 'ROM/MAC neighbourhood macro placement (um)')


# --------------------------------------------------------------------------- dies
def phy_strips(p):
    """Four HBM3E PHY+controller abstracts: two on each long (north/south) edge."""
    pw, ph = MV['ot_hbm3e_phy']
    xs = [snap(DIE_W / 4 - pw / 2, SNAP_X), snap(3 * DIE_W / 4 - pw / 2, SNAP_X)]
    for i, x in enumerate(xs):
        p.macro(f'u_hbm_s{i}', 'ot_hbm3e_phy', x, snap(EDGE_KEEP, SNAP_Y), 'R0', 'hbm_south')
        p.macro(f'u_hbm_n{i}', 'ot_hbm3e_phy', x, snap(DIE_H - EDGE_KEEP - ph - SNAP_Y, SNAP_Y), 'MX', 'hbm_north')
    return ph


def service_band(p, y0, depth, north, sram_count, label):
    """HBM service band behind a PHY row: controllers' fabric plus SRAM macros in rows."""
    mw, mh = MV['ot_sram_1r1w_1024x256_m2_r2c2']
    pitch_x = snap(mw + 2 * HALO_X, SNAP_X)
    pitch_y = snap(mh + 2 * HALO_Y, SNAP_Y)
    per_row = int((DIE_W - 2 * EDGE_KEEP) // pitch_x)
    rows = -(-sram_count // per_row)
    placed = 0
    for r in range(rows):
        for c in range(per_row):
            if placed == sram_count:
                break
            y = y0 + HALO_Y + r * pitch_y if not north else y0 + depth - (r + 1) * pitch_y + HALO_Y
            p.macro(f'u_{label}_sram{placed}', 'ot_sram_1r1w_1024x256_m2_r2c2',
                    snap(EDGE_KEEP + c * pitch_x + HALO_X, SNAP_X), snap(y, SNAP_Y), 'R0', label)
            placed += 1
    return rows * pitch_y


def build_die(design, cfg):
    p = Plan(design)
    p.region('die', 'die', 0, 0, DIE_W, DIE_H)
    ph = phy_strips(p)
    # --- service bands (KV ring / weight service) behind the PHY rows
    y_s0 = snap(EDGE_KEEP + ph + 4 * SNAP_Y, SNAP_Y)
    half = cfg['service_srams'] // 2
    depth_s = service_band(p, y_s0, 0, False, half, 'svc_south')
    depth_s = snap(depth_s + cfg['service_logic_um2'] / 2 / (DIE_W - 2 * EDGE_KEEP) / LOGIC_UTIL, SNAP_Y)
    p.region('svc_south', 'service', EDGE_KEEP, y_s0, DIE_W - 2 * EDGE_KEEP, depth_s,
             holds=cfg['service_holds'])
    y_n1 = snap(DIE_H - EDGE_KEEP - ph - 4 * SNAP_Y, SNAP_Y)
    depth_n = depth_s
    service_band(p, y_n1 - depth_n, depth_n, True, cfg['service_srams'] - half, 'svc_north')
    p.region('svc_north', 'service', EDGE_KEEP, y_n1 - depth_n, DIE_W - 2 * EDGE_KEEP, depth_n,
             holds=cfg['service_holds'])
    core_y0 = snap(y_s0 + depth_s + CORRIDOR_UM, SNAP_Y)
    core_y1 = y_n1 - depth_n - CORRIDOR_UM
    # --- west: UCIe PHY reservation (no view) and the collective engine
    ucie_w = cfg['ucie_mm2'] * 1e6 / 12000.0
    p.region('ucie_phy', 'reservation', EDGE_KEEP, DIE_H / 2 - 6000, ucie_w, 12000,
             note='ledger 10 mm2 (qwen3_budget ucie.link.phy_mm2_per_die); no LEF view exists')
    coll_w = 300.0
    p.region('collective', 'logic', EDGE_KEEP + ucie_w, DIE_H / 2 - 6000, coll_w, 12000,
             holds='ot_rom_oneshot_allreduce die engine (16 FP32 adders), link flow control')
    west = snap(EDGE_KEEP + ucie_w + coll_w + CORRIDOR_UM, SNAP_X)
    if cfg.get('frame_only'):
        east = DIE_W - EDGE_KEEP
        p.region('compute_array_reserved_for_W9', 'reservation', west, core_y0, east - west, core_y1 - core_y0,
                 note='GPU-style SM / tensor-core array owned by W9 (user design rule 2026-09-29); '
                      'W5 supplies only the frame: shoreline, stacks, service bands, UCIe')
        return p, dict(core_y0=core_y0, core_y1=core_y1, west=west, east=east,
                       compute_area_mm2=round((east - west) * (core_y1 - core_y0) / 1e6, 2),
                       service_band_mm2=round(2 * (DIE_W - 2 * EDGE_KEEP) * depth_s / 1e6, 2),
                       fits=None, tiles_needed=None, tiles_capacity=None, spine_used=0.0)
    # --- central spine: the narrowest multiple of the port-tile width whose blocks fit the core height
    core_h = core_y1 - core_y0
    spine = None
    for k in range(1, 12):
        cand = cfg['spine_fn'](snap(k * cfg['spine_unit_um'], SNAP_X))
        if sum(b['height_um'] for b in cand['blocks']) <= core_h:
            spine = cand
            break
    if spine is None:
        spine = cand
    spine_w = spine['width_um']
    sx = snap(DIE_W / 2 - spine_w / 2, SNAP_X)
    p.region('spine', 'spine', sx, core_y0, spine_w, core_h, holds=spine['holds'])
    y = core_y0
    for blk in spine['blocks']:
        hgt = blk['height_um']
        p.region(blk['name'], blk['kind'], sx, y, spine_w, hgt, **{k: v for k, v in blk.items()
                                                                     if k not in ('name', 'kind', 'height_um', 'place')})
        if blk.get('place'):
            blk['place'](p, sx, y, spine_w, hgt)
        y += hgt
    spine_used = y - core_y0
    # --- tile arrays west and east of the spine
    t = cfg['tile']
    arrays = []
    for side, x0, x1 in (('west', west, sx - CORRIDOR_UM), ('east', sx + spine_w + CORRIDOR_UM,
                                                               DIE_W - EDGE_KEEP)):
        # corridors every 4 tile columns and every 8 tile rows
        cols = rows = 0
        xw = x1 - x0
        yh = core_y1 - core_y0
        cols = int((xw + CORRIDOR_UM) // (4 * t['w'] + CORRIDOR_UM)) * 4
        rem = xw - (cols // 4) * (4 * t['w'] + CORRIDOR_UM)
        cols += max(0, min(3, int(rem // t['w'])))
        rows = int((yh + CORRIDOR_UM) // (8 * t['h'] + CORRIDOR_UM)) * 8
        remy = yh - (rows // 8) * (8 * t['h'] + CORRIDOR_UM)
        rows += max(0, min(7, int(remy // t['h'])))
        arrays.append(dict(side=side, x0=x0, y0=core_y0, cols=cols, rows=rows, tiles=cols * rows))
    need = cfg['tiles_in_array']
    have = sum(a['tiles'] for a in arrays)
    placed = 0
    for a in arrays:
        for r in range(a['rows']):
            for c in range(a['cols']):
                if placed == need:
                    break
                tx = a['x0'] + c * t['w'] + (c // 4) * CORRIDOR_UM
                ty = a['y0'] + r * t['h'] + (r // 8) * CORRIDOR_UM
                if a['side'] == 'west':
                    tx = a['x0'] + (a['cols'] - 1 - c) * t['w'] + ((a['cols'] - 1 - c) // 4) * CORRIDOR_UM
                for i, m in enumerate(t['macros']):
                    p.macro(f'u_t{placed}_m{i}', m.get('macro', t['macro']), snap(tx + m['x'], SNAP_X), snap(ty + m['y'], SNAP_Y),
                            m['orient'], f"tile_{a['side']}")
                placed += 1
        p.region(f"tiles_{a['side']}", 'tile_array', a['x0'], a['y0'],
                 a['cols'] * t['w'] + ((a['cols'] - 1) // 4) * CORRIDOR_UM,
                 a['rows'] * t['h'] + ((a['rows'] - 1) // 8) * CORRIDOR_UM,
                 cols=a['cols'], rows=a['rows'], capacity_tiles=a['tiles'])
    return p, dict(core_y0=core_y0, core_y1=core_y1, west=west, spine_x=sx, spine_w=spine_w,
                   spine_used=spine_used, arrays=arrays, tiles_needed=need, tiles_capacity=have,
                   tiles_placed=placed, fits=placed == need and spine_used <= core_y1 - core_y0)


def block_of_macros(macro, count, label, cols_max=None):
    mw, mh = MV[macro]
    px, py = snap(mw + 2 * HALO_X, SNAP_X), snap(mh + 2 * HALO_Y, SNAP_Y)

    def place(p, x0, y0, w, h):
        per_row = max(1, int(w // px))
        for i in range(count):
            r, c = divmod(i, per_row)
            p.macro(f'u_{label}{i}', macro, snap(x0 + c * px + HALO_X, SNAP_X), snap(y0 + r * py + HALO_Y, SNAP_Y),
                    'R0', label)

    def height(w):
        per_row = max(1, int(w // px))
        return snap(-(-count // per_row) * py, SNAP_Y)
    return place, height


# --------------------------------------------------------------------------- checks
def legality(p):
    die = [r for r in p.regions if r['kind'] == 'die'][0]
    errs = []
    ms = sorted(p.macros, key=lambda m: m['x'])
    for m in ms:
        if m['x'] < 0 or m['y'] < 0 or m['x'] + m['w'] > die['w'] + 1e-6 or m['y'] + m['h'] > die['h'] + 1e-6:
            errs.append(f"outside die: {m['inst']}")
        if abs(m['x'] / SNAP_X - round(m['x'] / SNAP_X)) > 1e-6 or abs(m['y'] / SNAP_Y - round(m['y'] / SNAP_Y)) > 1e-6:
            errs.append(f"off lattice: {m['inst']}")
    # sweep for overlaps including halo (PHY abstracts carry their own keep-out)
    active = []
    overlaps = 0
    for m in ms:
        hx = 0 if m['macro'] == 'ot_hbm3e_phy' else HALO_X
        hy = 0 if m['macro'] == 'ot_hbm3e_phy' else HALO_Y
        x0 = m['x'] - hx
        active = [a for a in active if a[1] > x0 + 1e-6]
        for a in active:
            b = a[2]
            if (m['y'] - hy < b['y'] + b['h'] - 1e-6 and b['y'] < m['y'] + m['h'] + hy - 1e-6
                    and x0 < b['x'] + b['w'] - 1e-6):
                overlaps += 1
                if overlaps <= 5:
                    errs.append(f"overlap/halo: {m['inst']} vs {b['inst']}")
        active.append((x0, m['x'] + m['w'] + hx, m))
    # region overlaps among non-container regions
    rs = [r for r in p.regions if r['kind'] not in ('die', 'spine', 'tile_array')]
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            if a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']:
                if not (a['name'].startswith('spine_') or b['name'].startswith('spine_')):
                    errs.append(f"region overlap: {a['name']} vs {b['name']}")
    return dict(macros=len(p.macros), overlaps_including_halo=overlaps, errors=errs[:20],
                legal=not errs)


def tree_budget(tile, geom, reach):
    """Register cycles the split tree offers versus what the placed distances need.

    Groups are laid out so that level-l partners are the nearest sibling blocks:
    levels 1-2 stay inside a tile (4 groups); from level 3 the partner block
    of 2^(l-2) tiles alternates x and y on the tile grid. After the last adding
    level (log2 S) the result holds its index down the remaining levels
    (TA + 1 = 4 registers each) and must reach its port tile in the spine.
    """
    tw, th = tile['w'], tile['h']
    out = {}
    for s_log in (6, 8, 10, 11):
        path = 0.0
        stages = 0
        rtl = 0
        bx, by = tw, th                      # current block size
        for lv in range(1, 14):
            if lv <= 2:
                d = 0.0
            else:
                if lv % 2:
                    d = bx
                    bx *= 2
                else:
                    d = by
                    by *= 2
            if lv <= s_log:
                rtl += 1
                stages += max(1, math.ceil(d / reach)) if d > 0 else 1
                path += d
            else:
                rtl += 4
        # compaction: the sub-tree root still has to reach the spine port tile
        far_x = max(abs((a['x0'] + (a['cols'] * tw if a['side'] == 'east' else 0)) - DIE_W / 2) for a in geom['arrays'])
        comp = far_x + (geom['core_y1'] - geom['core_y0']) / 2 - path
        comp = max(0.0, comp)
        stages += math.ceil(comp / reach) + (13 - s_log)
        path += comp
        out[f's{1 << s_log}'] = dict(path_um=round(path, 1), stages=stages, rtl_cycles=rtl)
    return out


# ASAP7 signal pitches (nm) of the layers above the memory macros' M1-M4 obstruction
UPPER_PITCH_NM = {'M5': 48, 'M6': 64, 'M7': 64, 'M8': 80, 'M9': 80}
SIGNAL_SHARE = 0.5          # the rest to PDN straps, vias and blockage


def bisection(conns):
    """Wires crossing the die's vertical bisection versus M5-M9 track capacity over it.

    Memory macros obstruct only M1-M4 (LEF OBS), so M5-M9 run over the ROM
    stacks. Horizontal layers M6, M8 cross a vertical cut line. Streams that
    leave the spine westward and eastward split between the halves.
    """
    per_um = sum(1000.0 / UPPER_PITCH_NM[l] for l in ('M6', 'M8')) * SIGNAL_SHARE
    cap = per_um * DIE_H
    demand = sum(c['bits'] for c in conns if c['per_token'] > 0 or 'fill' in c['name'] or 'stream' in c['name'])
    return dict(tracks_per_um=round(per_um, 2), cut_um=round(DIE_H, 1), capacity_wires=int(cap),
                demand_wires_upper_bound=int(demand), utilisation=round(demand / cap, 4),
                kv_operand_if_centralised_wires=6144 * 512 // 2,
                kv_centralised_utilisation=round(6144 * 512 / 2 / cap, 3),
                note='demand counts every priced stream once at full width (an upper bound); the '
                     'centralised-KV line shows why the ring slice must live in the tiles')


def wire_budget(geom, conns):
    wm = CAF.wire_delay_model()
    period_ps = CLOCK_NS * 1e3
    reach = (period_ps - UNC_NS * 1e3 - wm['overhead_ps']) / wm['ps_per_um']
    rows = []
    for c in conns:
        stages = c.pop('stages_override', None) or max(1, math.ceil(c['distance_um'] / reach))
        added = max(0, stages - c['rtl_cycles'])
        rows.append(dict(c, stages_needed=stages, added_cycles=added,
                         added_cycles_per_token=added * c['per_token'],
                         bit_mm=c['bits'] * c['distance_um'] / 1e3))
    return dict(model=dict(ps_per_um=wm['ps_per_um'], overhead_ps=wm['overhead_ps'], points=wm['points']),
                period_ps=round(period_ps, 3), uncertainty_ps=UNC_NS * 1e3,
                reach_um_per_cycle=round(reach, 1), connections=rows,
                added_cycles_per_token=sum(r['added_cycles_per_token'] for r in rows))


# --------------------------------------------------------------------------- outputs
def write_def(p, path):
    lines = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f'DESIGN {p.name} ;',
             'UNITS DISTANCE MICRONS 1000 ;',
             f'DIEAREA ( 0 0 ) ( {int(round(DIE_W * 1000))} {int(round(DIE_H * 1000))} ) ;',
             f'COMPONENTS {len(p.macros)} ;']
    for m in p.macros:
        orient = {'R0': 'N', 'MX': 'FS', 'MY': 'FN', 'R180': 'S'}[m['orient']]
        lines.append(f"- {m['inst']} {m['macro']} + FIXED ( {int(round(m['x'] * 1000))} "
                     f"{int(round(m['y'] * 1000))} ) {orient} ;")
    lines += ['END COMPONENTS', 'END DESIGN']
    Path(path).write_text('\n'.join(lines) + '\n')
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_svg(p, path, tile_regions_only=True):
    s = 0.03
    W, H = DIE_W * s, DIE_H * s
    col = {'die': '#f7f7f4', 'service': '#cfe3f5', 'reservation': '#f5d0c5', 'logic': '#e6d8f2',
           'spine': '#fff3c4', 'tile_array': '#e4f2de', 'vm': '#ffd98a', 'su': '#f2c3e0',
           'ports': '#b6e0b0', 'rom': '#d8d8d8', 'seq': '#c9c9f0', 'tree': '#fde2b5'}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.1f} {H:.1f}" font-family="sans-serif" font-size="9">']
    for r in p.regions:
        out.append(f'<rect x="{r["x"] * s:.1f}" y="{(DIE_H - r["y"] - r["h"]) * s:.1f}" width="{r["w"] * s:.1f}" '
                   f'height="{r["h"] * s:.1f}" fill="{col.get(r["kind"], "#eee")}" stroke="#555" stroke-width="0.4">'
                   f'<title>{r["name"]}</title></rect>')
    for m in p.macros:
        if m['macro'] == 'ot_hbm3e_phy':
            out.append(f'<rect x="{m["x"] * s:.1f}" y="{(DIE_H - m["y"] - m["h"]) * s:.1f}" width="{m["w"] * s:.1f}" '
                       f'height="{m["h"] * s:.1f}" fill="#7aa6d6" stroke="#234"><title>{m["inst"]}</title></rect>')
    for r in p.regions:
        if r['kind'] not in ('die',) and r['w'] * s > 40:
            out.append(f'<text x="{(r["x"] + 60) * s:.1f}" y="{(DIE_H - r["y"] - r["h"] / 2) * s:.1f}">{r["name"]}</text>')
    out.append('</svg>')
    Path(path).write_text('\n'.join(out) + '\n')


# --------------------------------------------------------------------------- designs
def designs(inputs):
    rp, inv, cs, ua, cat, budget = inputs
    for n, m in cat['macros'].items():
        MV[n] = (m['width_um'], m['height_um'])
    MV['ot_hbm3e_phy'] = (12000.096, 833.49)
    units = {u['module']: u['area_um2'] for u in ua['units']}
    fmul = units['ot_hdc_fmul']
    plain = cs['clusters']['rommac_plain']['cell_area_um2']
    port = cs['clusters']['rommac_port']['cell_area_um2']
    vm_logic = cs['clusters']['vm_cut']['cell_area_um2']
    area = budget['area']
    code_banks = rp['code_rom']['banks_per_column']
    assert code_banks == 11, 'tile geometry is drawn for 11 code banks a pair column'
    scale_rep = rp['scale_rom']['rtl_compatible']['banks_per_port_group']
    emb_macros = rp['embedding_rom']['macros'] + rp['embedding_rom']['scale_macros']
    crom_macros = rp['constant_rom']['macros']
    ports = rp['scale_rom']['result_port_groups']
    port_tiles = ports // 4
    tiles = 6144 // 4
    kv_bytes = area['kv_prefetch_buffer_bytes']
    kv_srams = math.ceil(kv_bytes * 8 / MV_CAP['ot_sram_1r1w_1024x256_m2_r2c2'])
    vm_elems = 177808
    vm_macros = 8 * 4 * math.ceil(math.ceil(vm_elems / 16) / 8 / 512)
    profiles = {}
    lane_copy_um2_per_lane = 8449.0 / 16          # routed ot_hdc_lane_copy (qwen3_budget lane_copy_basis)
    m5_reduce_mm2 = 178.66                          # results/arch/qwen_m5_area_latency_tradeoff.json
    for prof, lg, extra_note in (
            ('rtl_as_instantiated', plain, 'every tile carries its 64 post-scale fmuls as the RTL instantiates them'),
            ('reachable_pruned', plain - 64 * fmul, 'fmuls only in the 24 result-port tiles (needs an RTL parameter)'),
            ('m5_ledger_copies', plain - 64 * fmul + 4 * 64 * lane_copy_um2_per_lane * LOGIC_UTIL
             + m5_reduce_mm2 * 1e6 / tiles * LOGIC_UTIL,
             'reachable profile + 4 MAC-only lane copies a lane (routed 8,449 um2 / 16 lanes) + measured m=5 '
             'reducer/scale copies (+178.66 mm2 a die, linear tile replication)')):
        profiles[prof] = dict(tile_logic_um2=lg, note=extra_note)
    return dict(units=units, plain=plain, port=port, vm_logic=vm_logic, scale_rep=scale_rep,
                emb_macros=emb_macros, crom_macros=crom_macros, ports=ports, port_tiles=port_tiles,
                tiles=tiles, kv_srams=kv_srams, vm_macros=vm_macros, profiles=profiles, fmul=fmul)


MV_CAP = {}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out-dir', type=Path, default=OUT_DIR)
    args = ap.parse_args()
    rp, inv, cs, ua, cat, budget = (json.loads((ROOT / f).read_text()) for f in INPUTS[:6])
    for n, m in cat['macros'].items():
        MV_CAP[n] = m['capacity_bits']
    globals()['cs'] = cs
    d = designs((rp, inv, cs, ua, cat, budget))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    wm = CAF.wire_delay_model()
    reach = (CLOCK_NS * 1e3 - UNC_NS * 1e3 - wm['overhead_ps']) / wm['ps_per_um']
    records = {}
    for design in ('rom_die', 'hbm_die'):
        for prof, pv in d['profiles'].items():
            if design == 'hbm_die':
                if prof != 'rtl_as_instantiated':
                    continue
                p, geom = build_die('qwen_o4_hbm_die_frame', dict(
                    frame_only=True, service_srams=0, service_logic_um2=2 * 10e6,
                    service_holds='HBM3E controllers\' fabric, per-PC arbiters and weight/KV stream heads for '
                                  '128 PCs (reservation 10 mm2 a band)',
                    ucie_mm2=budget['ucie']['link']['phy_mm2_per_die']))
                leg = legality(p)
                rec = dict(design='hbm_die', profile='frame', profile_note='die frame only (W9 owns compute)',
                           geometry=geom, legality=leg,
                           macro_counts={mn: sum(1 for m in p.macros if m['macro'] == mn)
                                         for mn in sorted({m['macro'] for m in p.macros})},
                           shoreline=dict(stacks=4, phy_edge_mm=4 * 12.0, free_edge_mm=round(2 * DIE_W / 1e3 + DIE_H / 1e3, 2),
                                          edges='two PHY+controller abstracts on each long (north/south) edge; '
                                                'the west edge faces the other die (UCIe)'),
                           weight_supply=dict(bytes_per_cycle=3277, bytes_consumed_per_cycle_by_rom_engine=98304,
                                              window_mib_per_die=48,
                                              note='docs/QWEN_O4_HBM_WEIGHT_SUPPLY.md; the consumer is W9\'s array'),
                           regions=p.regions)
                records['hbm_die.frame'] = rec
                stem = args.out_dir / 'hbm_die_frame'
                rec['def_sha256'] = write_def(p, str(stem) + '_macros.def')
                write_svg(p, str(stem) + '.svg')
                continue
            logic = pv['tile_logic_um2']
            if design == 'rom_die':
                tile = rom_tile(logic)
                # the die's scale image lives in the spine scale block; the port tile's own
                # scale banks exist only in the route cut
                port_tile = rom_tile(d['port'])
            else:
                # the comparator tile keeps the matvec logic; its window SRAM replaces the code ROM
                tile = stream_tile(logic)
                port_tile = stream_tile(d['port'])
            def spine_fn(spine_w, design=design, port_tile=port_tile):
                blocks = []
                # result-port tiles (groups 0..95) with their replicated scale images
                scale_place, scale_h = block_of_macros('ot_rom_4096x266_m8', d['ports'] * d['scale_rep'], 'scale')
                per_row_tiles = max(1, int(spine_w // port_tile['w']))
                pt_rows = -(-d['port_tiles'] // per_row_tiles)

                def place_ports(p, x0, y0, w, h, tile=port_tile, n=d['port_tiles'], per=per_row_tiles):
                    for i in range(n):
                        r, c = divmod(i, per)
                        for j, m in enumerate(tile['macros']):
                            p.macro(f'u_port{i}_m{j}', m.get('macro', tile['macro']), snap(x0 + c * tile['w'] + m['x'], SNAP_X),
                                    snap(y0 + r * tile['h'] + m['y'], SNAP_Y), m['orient'], 'port_tiles')
                blocks.append(dict(name='spine_port_tiles', kind='ports', height_um=snap(pt_rows * port_tile['h'], SNAP_Y),
                                   place=place_ports, tiles=d['port_tiles'],
                                   holds='result-port neighbourhoods: groups 0..95, the only ones whose fmul / VM '
                                         'write / argmax leaves can be active'))
                blocks.append(dict(name='spine_scale_rom', kind='rom', height_um=scale_h(spine_w), place=scale_place,
                                   macros=d['ports'] * d['scale_rep'],
                                   holds=f"{d['scale_rep']} scale banks for each of the {d['ports']} port groups "
                                         '(RTL-compatible whole-image replica)'))
                vm_place, vm_h = block_of_macros('ot_sram_1r1w_512x128_m4_r2c2', d['vm_macros'], 'vm')
                blocks.append(dict(name='spine_vm', kind='vm', height_um=snap(vm_h(spine_w) + d['vm_logic'] * 3 / LOGIC_UTIL / spine_w, SNAP_Y),
                                   place=vm_place, macros=d['vm_macros'],
                                   holds='8 skew banks x 4 slices x 3 rows of 512x128 (VM_ELEMS 177,808 FP32) + steering'))
                if design == 'rom_die':
                    e_place, e_h = block_of_macros('ot_rom_4096x266_m8', d['emb_macros'], 'emb')
                    blocks.append(dict(name='spine_embedding_rom', kind='rom', height_um=e_h(spine_w), place=e_place,
                                       macros=d['emb_macros'], holds='INT8 embedding half-vocabulary + row scales'))
                c_place, c_h = block_of_macros('ot_rom_4096x72_m8', d['crom_macros'], 'crom')
                blocks.append(dict(name='spine_constants_sequencer', kind='seq',
                                   height_um=snap(c_h(spine_w) + 400.0, SNAP_Y), place=c_place, macros=d['crom_macros'],
                                   holds='constant ROM, program, sequencer, ot_rom_tp_seq'))
                su_mm2 = budget['area']['stream_unit_spill_mm2']
                blocks.append(dict(name='spine_stream_unit', kind='su', height_um=snap(su_mm2 * 1e6 / spine_w, SNAP_Y),
                                   holds=f'reservation: SW = 1,024 stream unit at the ledger {su_mm2} mm2 (RTL is SW = 1)'))
                blocks.append(dict(name='spine_tree_top', kind='tree', height_um=600.0,
                                   holds='split-tree levels 9..13 registers and result compaction toward the port tiles'))

                return dict(width_um=spine_w, blocks=blocks, holds='VM, SU, sequencer, ports, tree top')

            if design == 'rom_die':
                service_srams = 0
                service_logic = 2 * 5e6          # two bands x 5 mm2 of KV-service fabric (reservation)
                holds = 'per-PC KV arbiters, fill heads and staging (reservation 5 mm2 a band); the ring is in the tiles'
            else:
                service_srams = 0
                service_logic = 2 * 10e6
                holds = 'per-PC arbiters for weight + KV and stream heads for 128 PCs (reservation 10 mm2 a band)'
            cfg = dict(tile=tile, tiles_in_array=d['tiles'] - d['port_tiles'],
                       spine_fn=spine_fn, spine_unit_um=port_tile['w'],
                       service_srams=service_srams, service_logic_um2=service_logic, service_holds=holds,
                       ucie_mm2=budget['ucie']['link']['phy_mm2_per_die'])
            p, geom = build_die(f'qwen_o4_{design}_{prof}', cfg)
            leg = legality(p)
            # ------------------------------------------------------------ wire budget
            arr = geom['arrays']
            spine_w = geom['spine_w']
            far_x = max(abs((a['x0'] + (a['cols'] * tile['w'] if a['side'] == 'east' else 0)) - DIE_W / 2) for a in arr)
            core_h = geom['core_y1'] - geom['core_y0']
            far = far_x + core_h / 2                       # spine centre -> farthest tile corner (Manhattan)
            ucie_to_spine = DIE_W / 2 - EDGE_KEEP - spine_w / 2
            svc_to_far_tile = core_h + far_x / 2           # PHY-row service band -> farthest tile, via corridors
            tree = tree_budget(tile, geom, reach)
            conns = [
                dict(name='x operand: VM -> farthest group (mq_x)', bits=32 * 2048, distance_um=round(far, 1),
                     rtl_cycles=1, per_token=145 + 72,
                     note='ot_hdc_matvec: VM read returns at c+1 and mq_x captures at c+2, one cycle from the VM '
                          'macro to every group. Priced one way, which needs the VM to stream x (it knows the '
                          'address sequence) rather than tiles requesting it (a round trip, twice this). S '
                          'distinct elements a cycle (<= 2048) multicast to G/S groups; exposed once per matrix op'),
                dict(name='issue broadcast: sequencer -> farthest tile (instruction, go)', bits=900,
                     distance_um=round(far, 1), rtl_cycles=1, per_token=0,
                     note='same path and direction as the x stream, so it overlaps it (not added twice); the '
                          'die RTL is one ot_hdc_matvec whose single issue register drives every group'),
                dict(name='split tree + result compaction: farthest tile -> port tile (gate/up, S = 64)',
                     bits=16 * 32 * 96, distance_um=tree['s64']['path_um'], rtl_cycles=tree['s64']['rtl_cycles'],
                     per_token=36, stages_override=tree['s64']['stages'],
                     note='per-level partner distances on the placed grid; an adding level gives one register '
                          'cycle of wire, a holding level TA+1 = 4 (u_hold + lq)'),
                dict(name='split tree + result compaction: farthest tile -> port tile (o, down, S = 2048)',
                     bits=16 * 32 * 3, distance_um=tree['s2048']['path_um'], rtl_cycles=tree['s2048']['rtl_cycles'],
                     per_token=72, stages_override=tree['s2048']['stages'], note='as above'),
                dict(name='split tree + result compaction: farthest tile -> port tile (qkv, S = 256)',
                     bits=16 * 32 * 24, distance_um=tree['s256']['path_um'], rtl_cycles=tree['s256']['rtl_cycles'],
                     per_token=36, stages_override=tree['s256']['stages'], note='as above'),
                dict(name='split tree + result compaction (lm_head, S = 1024)',
                     bits=16 * 32 * 6, distance_um=tree['s1024']['path_um'], rtl_cycles=tree['s1024']['rtl_cycles'],
                     per_token=1, stages_override=tree['s1024']['stages'], note='as above'),
                dict(name='result write: port tile -> VM', bits=1536 * 32, distance_um=round(spine_w, 1),
                     rtl_cycles=2, per_token=145 + 72, note='the matvec output registers o_*1 and o_*'),
                dict(name='KV operand: tile KV slice -> mq_kv', bits=512 * 4, distance_um=round(tile['h'], 1),
                     rtl_cycles=1, per_token=72,
                     note='the ring slice sits in the tile (the KV operand of all 6,144 groups is 3.1 Mbit a '
                          'cycle and cannot cross the die); needs FP8 packing and a per-group KV port (gap G8)'),
                dict(name='KV fill: HBM service band -> farthest tile slice', bits=3277 * 8,
                     distance_um=round(svc_to_far_tile, 1), rtl_cycles=0, per_token=0,
                     note='prefetch one layer ahead (ot_hdc_kv_stream discipline): bandwidth-, not latency-bound'),
                dict(name='TP exchange: port tiles -> UCIe PHY and back', bits=16 * 32 * 3,
                     distance_um=round(ucie_to_spine, 1), rtl_cycles=0, per_token=2 * 73,
                     note='ot_rom_oneshot_allreduce LAT 11 models the link hop only; the crossing from the '
                          'spine to the west-edge PHY and back is not in the RTL'),
            ]
            if design == 'hbm_die':
                conns.append(dict(name='weight stream: service band -> farthest tile window', bits=256 * 8,
                                  distance_um=round(svc_to_far_tile, 1), rtl_cycles=0, per_token=0,
                                  note='prefetched into the tile windows ahead of use; bandwidth-, not '
                                       'latency-bound (HBM supplies 3,277 of the 98,304 B a cycle consumed)'))
            wb = wire_budget(geom, conns)
            wb['bisection'] = bisection(conns)
            # ------------------------------------------------------------ area ledger
            macro_area = sum(m['w'] * m['h'] for m in p.macros) / 1e6
            tile_area = tile['w'] * tile['h'] / 1e6
            rec = dict(design=design, profile=prof, profile_note=pv['note'], tile=dict(
                {k: v for k, v in tile.items() if k != 'macros'}, macros_per_tile=len(tile['macros']),
                area_mm2=round(tile_area, 5)), port_tile=dict(w=port_tile['w'], h=port_tile['h'],
                                                            macros=len(port_tile['macros'])),
                       geometry={k: v for k, v in geom.items()}, legality=leg,
                       macro_counts={mn: sum(1 for m in p.macros if m['macro'] == mn)
                                     for mn in sorted({m['macro'] for m in p.macros})},
                       macro_area_mm2=round(macro_area, 3), regions=p.regions, wire_budget=wb)
            key = f'{design}.{prof}'
            records[key] = rec
            stem = args.out_dir / f'{design}_{prof}'
            rec['def_sha256'] = write_def(p, str(stem) + '_macros.def')
            write_svg(p, str(stem) + '.svg')
            if design == 'rom_die' and prof == 'rtl_as_instantiated':
                rec['route_cut'] = dict(port=dict((k, v) for k, v in rom_tile(d['port'], scale_macros=4).items()
                                                  if k != 'macros'))
    # power density of the HBM service (qwen-die-cooling-binds): controller/PHY energy per token
    pw = budget['power_production']['scenarios']['B_proposed_production']
    power = {}
    for design, arm, pt in (('rom_die', 'rom', 'ar_batch1'), ('hbm_die', 'hbm_comparator', 'batch1'),
                            ('hbm_die_batch16', 'hbm_comparator', 'batch16')):
        x = pw[arm][pt]
        ctrl_w = x['die_components_mj_per_token']['hbm_controller_phy_io'] * 1e-3 * x['tokens_s'] / x['dies']
        phy_mm2 = 4 * MV['ot_hbm3e_phy'][0] * MV['ot_hbm3e_phy'][1] / 1e6
        power[design] = dict(tokens_s=x['tokens_s'], die_w=x['die_w'], hbm_controller_phy_w=round(ctrl_w, 1),
                             phy_area_mm2=round(phy_mm2, 2), phy_w_per_mm2=round(ctrl_w / phy_mm2, 2),
                             die_average_w_per_mm2=round(x['die_w'] / 815, 3),
                             liquid_die_limit_w=x['cooling']['liquid']['die_limit_w'],
                             liquid_capped_tokens_s=x['cooling']['liquid']['capped_tokens_s'])
    summary = dict(
        schema='opentallas.qwen-o4-floorplan.v1', tool='tools/qwen_o4_floorplan.py',
        status=('PARTIAL_tile_logic_area_is_an_estimate' if cs.get('status', '').startswith('ESTIMATE')
                else 'macro_packed_floorplan'),
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_sha256={f: sha(f) for f in INPUTS},
        clock=dict(adopted_ns=round(CLOCK_NS, 6), uncertainty_ns=UNC_NS,
                   note='qwen3_budget.json clock (1.09864 GHz); earlier 0.92 ns cuts are 1.07% slower'),
        die_um=[DIE_W, round(DIE_H, 3)], lattice_um=[SNAP_X, SNAP_Y], halo_um=[HALO_X, HALO_Y],
        logic_util=LOGIC_UTIL, corridor_um=CORRIDOR_UM, reach_um_per_cycle=round(reach, 1),
        power_density=power,
        fit={k: dict(fits=v['geometry']['fits'], tiles_needed=v['geometry']['tiles_needed'],
                     tiles_capacity=v['geometry']['tiles_capacity'],
                     tile_um=[v['tile']['w'], v['tile']['h']] if 'tile' in v else None,
                     spine_used_um=round(v['geometry']['spine_used'], 1),
                     core_height_um=round(v['geometry']['core_y1'] - v['geometry']['core_y0'], 1),
                     compute_area_mm2=v['geometry'].get('compute_area_mm2'),
                     legal=v['legality']['legal'], macros=v['legality']['macros'],
                     added_cycles_per_token=v['wire_budget']['added_cycles_per_token'] if 'wire_budget' in v else None)
             for k, v in records.items()},
        designs=records,
        claim_boundary='macro-packed placement and distance pricing only: no die route, no timing, no '
                       'power integrity; predictive ASAP7 views; reservations are named as such')
    (args.out_dir / 'floorplan.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps(summary['fit'], indent=1))


if __name__ == '__main__':
    main()
