#!/usr/bin/env python3
"""Floorplan of the Qwen3-8B O4 ROM die at the W12 design point: one hardened tile element replicated.

The die (G lane groups, TP-2 half of the model, AR only) is:
  * G/4 identical tile elements (rtl/hdc/ot_qwen_rom_tile.sv, hardened: its placed
    outline comes from the tile's place-and-route record), arranged in blocks of
    2^(TCUT-2) tiles = one split-tree subtree of 2^TCUT groups, so every tree level
    below TCUT stays inside a block;
  * a central spine: the engine top (ot_qwen_me_spine: issue, x network root, tree
    levels above TCUT, the G >> SMIN result-port groups' post-scale, argmax and
    result write), the port-local scale ROM (SCALE_LOCAL), the vector memory, the
    SW = 1,024 stream unit, the embedding and constant ROMs, the sequencer;
  * the frame of W5's floorplan (tools/qwen_o4_floorplan.py): 4 HBM3E PHYs on the
    long edges with KV-service bands behind them, the UCIe reservation and the
    collective on the west edge.

Every macro is placed (tile macros through the tile outline; spine macros as real
views) and checked for legality.  Every cross-region connection is priced with
the model's loaded wire constant (tools/uarch_model.py wire_cycles, 0.76 ps/um):
the register stages the distance needs become the RTL array's wire parameters
(BD, NWS, TWS, ORD) that the runtime composition simulates.  Writes a record,
a DEF of the macros and an SVG.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_o4_floorplan as F  # noqa: E402  (frame, legality, DEF/SVG writers)
import uarch_model as U  # noqa: E402
import arch_budget_qwen3 as Q  # noqa: E402

CLOCK_HZ = Q.clock_hz()
SNAP_X, SNAP_Y = F.SNAP_X, F.SNAP_Y
CORR = F.CORRIDOR_UM


REACH = [None]      # --reach-um: a measured per-stage reach overrides the model's rule


def wc(um):
    """register stages to cross um of loaded wire: ceil(L / reach) with a measured reach (W15 SS: 261 ps +
    1.135 ps/um, 504 um a stage at 0.833 ns), else the model's rule (tools/uarch_model.wire_cycles)"""
    if REACH[0]:
        return max(1, math.ceil(um / REACH[0])) if um > 0 else 0
    return U.wire_cycles(um, CLOCK_HZ, U.WIRE_PS_PER_UM_LOADED)


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


NOHALO = ('ot_hbm3e_phy', 'ot_qwen_rom_tile')


def legality(p):
    """tools/qwen_o4_floorplan.legality with the hardened tile abutting like the PHY abstracts"""
    die = [r for r in p.regions if r['kind'] == 'die'][0]
    errs = []
    ms = sorted(p.macros, key=lambda m: m['x'])
    for m in ms:
        if m['x'] < 0 or m['y'] < 0 or m['x'] + m['w'] > die['w'] + 1e-6 or m['y'] + m['h'] > die['h'] + 1e-6:
            errs.append(f"outside die: {m['inst']}")
        if abs(m['x'] / SNAP_X - round(m['x'] / SNAP_X)) > 1e-6 or abs(m['y'] / SNAP_Y - round(m['y'] / SNAP_Y)) > 1e-6:
            errs.append(f"off lattice: {m['inst']}")
    active, overlaps = [], 0
    for m in ms:
        hx = 0 if m['macro'] in NOHALO else F.HALO_X
        hy = 0 if m['macro'] in NOHALO else F.HALO_Y
        x0 = m['x'] - hx
        active = [q for q in active if q[1] > x0 + 1e-6]
        for q in active:
            b = q[2]
            if (m['y'] - hy < b['y'] + b['h'] - 1e-6 and b['y'] < m['y'] + m['h'] + hy - 1e-6
                    and x0 < b['x'] + b['w'] - 1e-6):
                overlaps += 1
                if overlaps <= 5:
                    errs.append(f"overlap/halo: {m['inst']} vs {b['inst']}")
        active.append((x0, m['x'] + m['w'] + hx, m))
    # tiles must stay out of the spine and frame regions
    blockers = [r for r in p.regions if r['kind'] in ('spine', 'service', 'reservation', 'logic')]
    for m in ms:
        if m['macro'] != 'ot_qwen_rom_tile':
            continue
        for r in blockers:
            if m['x'] < r['x'] + r['w'] and r['x'] < m['x'] + m['w'] and m['y'] < r['y'] + r['h'] and r['y'] < m['y'] + m['h']:
                errs.append(f"tile in region {r['name']}: {m['inst']}")
                break
    return dict(macros=len(p.macros), overlaps_including_halo=overlaps, errors=errs[:20], legal=not errs)


def host_tile(lv, p, lt=2):
    k = lv - lt
    return (p << k) + (1 << (k - 1)) - 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--groups', type=int, default=6144)
    ap.add_argument('--smin', type=int, default=6)
    ap.add_argument('--smax', type=int, default=11)
    ap.add_argument('--tile-record', type=Path, help='tile P&R record (physical.json): die outline')
    ap.add_argument('--tile-um', type=float, nargs=2, help='tile outline w h (um) when no record')
    ap.add_argument('--rom-placement', type=Path, required=True, help='tools/qwen_o4_rom_placement.py output (AR only)')
    ap.add_argument('--spine-logic-mm2', type=float, default=4.0,
                    help='engine top + sequencer + TP seq cell area / 0.5 (placed), until synthesised')
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--reach-um', type=float, help='per-stage wire reach (um); W15 SS at 0.833 ns: 504')
    a = ap.parse_args()
    REACH[0] = a.reach_um
    G, TCUT = a.groups, a.smin
    NT, LT = G // 4, 2
    BLK = 1 << (TCUT - LT)                         # tiles a block (a level-TCUT subtree)
    NB = G >> TCUT                                 # blocks = tree words into the spine = result-port groups
    cat = json.loads((ROOT / 'physical/asap7_memory_macros/index.json').read_text())
    for n, m in cat['macros'].items():
        F.MV[n] = (m['width_um'], m['height_um'])
    F.MV['ot_hbm3e_phy'] = (12000.096, 833.49)
    rp = json.loads(a.rom_placement.read_text())
    if rp['die']['groups'] != G:
        raise SystemExit('ROM placement is for another group count')
    if a.tile_record:
        rec = json.loads(a.tile_record.read_text())
        pr = rec['place_and_route']
        die = pr.get('die_area_um') or pr.get('die_area')
        tw, th = float(die[2]) - float(die[0]), float(die[3]) - float(die[1])
        tile_src = str(a.tile_record)
    else:
        tw, th = a.tile_um
        tile_src = 'argument (estimate)'
    budget = json.loads((ROOT / 'results/arch/qwen3_budget.json').read_text())

    p = F.Plan(f'qwen_rom_w12_g{G}')
    p.region('die', 'die', 0, 0, F.DIE_W, F.DIE_H)
    ph = F.phy_strips(p)
    # KV service bands behind the PHY rows (W5 frame: 5 mm2 of fill/arbiter fabric a band)
    y_s0 = F.snap(F.EDGE_KEEP + ph + 4 * SNAP_Y, SNAP_Y)
    band = F.snap(5e6 / (F.DIE_W - 2 * F.EDGE_KEEP) / F.LOGIC_UTIL, SNAP_Y)
    p.region('svc_south', 'service', F.EDGE_KEEP, y_s0, F.DIE_W - 2 * F.EDGE_KEEP, band,
             holds='KV fill heads, per-PC arbiters, staging (the KV window lives in the tiles)')
    y_n1 = F.snap(F.DIE_H - F.EDGE_KEEP - ph - 4 * SNAP_Y, SNAP_Y)
    p.region('svc_north', 'service', F.EDGE_KEEP, y_n1 - band, F.DIE_W - 2 * F.EDGE_KEEP, band,
             holds='as svc_south')
    core_y0 = F.snap(y_s0 + band + CORR, SNAP_Y)
    core_y1 = y_n1 - band - CORR
    core_h = core_y1 - core_y0
    ucie_w = budget['ucie']['link']['phy_mm2_per_die'] * 1e6 / 12000.0
    p.region('ucie_phy', 'reservation', F.EDGE_KEEP, F.DIE_H / 2 - 6000, ucie_w, 12000,
             note='ledger 10 mm2; no LEF view')
    p.region('collective', 'logic', F.EDGE_KEEP + ucie_w, F.DIE_H / 2 - 6000, 300.0, 12000,
             holds='ot_rom_oneshot_allreduce, link flow control')
    west = F.snap(F.EDGE_KEEP + ucie_w + 300.0 + CORR, SNAP_X)
    east = F.DIE_W - F.EDGE_KEEP

    # ---------------------------------------------------------------- spine blocks
    scale_exact = rp['scale_rom']['exact_subset_needs_rtl_remap']
    ports_dense = rp['scale_rom']['result_port_groups']
    # SCALE_LOCAL: every port reserves every matrix's rounds (tools/qwen_rom_scale_local.py);
    # words a port = sum over the die's matrices of rounds * IL
    local_words = sum(s['rounds'] * 8 for s in rp['code_segments'])
    scale_banks_port = math.ceil(local_words / 4096)
    scale_macros = ports_dense * scale_banks_port
    emb = rp['embedding_rom']['macros'] + rp['embedding_rom']['scale_macros']
    crom = rp['constant_rom']['macros']
    vm_bank = U.vm_banking(512)                     # adopted: a 512-FP32 x read a cycle (root, 2026-09-29)
    vm_macros = vm_bank['macros']
    su_mm2 = budget['area']['stream_unit_spill_mm2']
    fmul_um2, qadd_um2, dff = 514.4, 180.5, U.DFF_UM2
    ports = NB
    top_cells = (ports * 16 * fmul_um2                            # post-scale multipliers
                 + ports * 16 * (1 + 32 + 18) * dff * 2           # argmax leaves + tree registers
                 + (ports - 1) * 16 * (qadd_um2 + 32 * dff * 4)   # tree levels above TCUT (add or hold)
                 + ports * 16 * 32 * dff * (2 + 2))               # result registers + write stages
    top_mm2 = top_cells / 1e6 / F.LOGIC_UTIL + a.spine_logic_mm2

    def blocks(sw):
        out = []
        emb_a = emb // 2
        for name, kind, macro, n, extra, holds in (
                ('spine_embedding_rom_a', 'rom', 'ot_rom_4096x266_m8', emb_a, 0.0, 'INT8 embedding (first half)'),
                ('spine_constants', 'seq', 'ot_rom_4096x72_m8', crom, 0.0, 'constant ROM'),
                ('spine_scale_rom', 'rom', 'ot_rom_4096x266_m8', scale_macros, 0.0,
                 f'port-local scale ROM (SCALE_LOCAL): {ports_dense} dense ports x {scale_banks_port} banks '
                 f'({local_words} words a port; the exact subset would be {scale_exact["macros"]} macros)'),
                ('spine_engine_top', 'ports', None, 0, top_mm2,
                 f'ot_qwen_me_spine: issue loop, x network root, split-tree levels {TCUT + 1}..13, '
                 f'{ports} result-port groups (post-scale, argmax, result write), sequencer, TP seq'),
                ('spine_vm', 'vm', 'ot_sram_1r1w_512x128_m4_r2c2', vm_macros, 0.4,
                 f'vector memory (177,808 FP32), {vm_macros} x 512x128 for a 512-element x read, registered conflict stage (XVM = 1)'),
                ('spine_stream_unit', 'su', None, 0, su_mm2, 'SW = 1,024 vector stream unit (ledger reservation)'),
                ('spine_embedding_rom_b', 'rom', 'ot_rom_4096x266_m8', emb - emb_a, 0.0, 'INT8 embedding (second half) + scales')):
            h = 0.0
            place = None
            if macro:
                pl, hf = F.block_of_macros(macro, n, name.replace('spine_', ''))
                h += hf(sw)
                place = pl
            h = F.snap(h + extra * 1e6 / sw, SNAP_Y)
            out.append(dict(name=name, kind=kind, height_um=h, place=place, macros=n, holds=holds))
        return out
    sw = None
    for k in range(1, 40):
        cand = F.snap(k * 200.0, SNAP_X)
        if sum(b['height_um'] for b in blocks(cand)) <= core_h:
            sw = cand
            break
    bl = blocks(sw)
    sx = F.snap(F.DIE_W / 2 - sw / 2, SNAP_X)
    p.region('spine', 'spine', sx, core_y0, sw, core_h)
    y = core_y0
    spine_y = {}
    for b in bl:
        p.region(b['name'], b['kind'], sx, y, sw, b['height_um'], holds=b['holds'], macros=b['macros'])
        if b['place']:
            b['place'](p, sx, y, sw, b['height_um'])
        spine_y[b['name']] = (y, y + b['height_um'])
        y += b['height_um']
    spine_used = y - core_y0

    # ---------------------------------------------------------------- tile arrays
    # A grid of abutted tiles each side of the spine, a 60 um corridor every 4 columns and every
    # 8 rows (W5).  Blocks of BLK tiles (one level-TCUT subtree) fill column bands of width 4, 2
    # or 1 tiles (4 x BLK/4, 2 x BLK/2, 1 x BLK): the tree below TCUT stays inside a block.
    tw, th = F.snap(tw, SNAP_X), F.snap(th, SNAP_Y)
    arrays, bands = [], []
    for side, x0, x1 in (('west', west, sx - CORR), ('east', sx + sw + CORR, east)):
        xs = []
        x = x0
        while x + tw <= x1 + 1e-6:
            xs.append(x)
            x += tw + (CORR if len(xs) % 4 == 0 else 0.0)
        ys = []
        yv = core_y0
        while yv + th <= core_y1 + 1e-6:
            ys.append(yv)
            yv += th + (CORR if len(ys) % 8 == 0 else 0.0)
        if side == 'west':
            xs = xs[::-1]                      # columns counted outward from the spine
        arrays.append(dict(side=side, x0=x0, x1=x1, cols=len(xs), rows=len(ys), tiles=len(xs) * len(ys)))
        c = 0
        while c < len(xs):
            wbw = min(4, len(xs) - c)
            if wbw == 3:
                wbw = 2
            bands.append((side, xs[c:c + wbw], ys))
            c += wbw
    cap_tiles = sum(ar['tiles'] for ar in arrays)
    block_slots = []
    for side, bxs, ys in bands:
        bw = len(bxs)
        bh = BLK // bw
        for r0 in range(0, len(ys) - bh + 1, bh):
            pos = [(bxs[cc], ys[r0 + rr]) for rr in range(bh) for cc in range(bw)]
            cx = sum(q[0] for q in pos) / len(pos) + tw / 2
            cy = sum(q[1] for q in pos) / len(pos) + th / 2
            block_slots.append((abs(cx - F.DIE_W / 2) + abs(cy - (core_y0 + core_h / 2)), side, bw, pos))
    block_slots.sort(key=lambda z: z[0])
    cap_blocks = len(block_slots)
    placed = block_slots[:NB]
    tile_xy = {}
    for b, (_, side, bw, pos) in enumerate(placed):
        # in-block order follows the tree: tile i of the block at the position whose (row, col)
        # interleaves i's bits (pairs side by side, then stacked), for any band width
        order = sorted(range(BLK), key=lambda i: i)
        if bw == 4:
            idx = [((i >> 1) & 1 | (i >> 3) << 1) * 4 + ((i & 1) | ((i >> 2) & 1) << 1) for i in order]
        elif bw == 2:
            idx = [(i >> 1) * 2 + (i & 1) for i in order]
        else:
            idx = list(order)
        for i in order:
            tile_xy[b * BLK + i] = pos[idx[i]]
    fits = len(placed) == NB and spine_used <= core_h + 1e-6
    tiles_region_area = sum((ar['x1'] - ar['x0']) * core_h for ar in arrays)
    F.MV['ot_qwen_rom_tile'] = (round(tw, 3), round(th, 3))
    for t, (x, yv) in sorted(tile_xy.items()):
        # the hardened tile is itself a macro (its own halos are inside its outline): abutted in a block
        p.macro(f'u_tile{t}', 'ot_qwen_rom_tile', F.snap(x, SNAP_X), F.snap(yv, SNAP_Y), 'R0', 'tiles')

    # ---------------------------------------------------------------- wires -> stages
    def centre(t):
        x, yv = tile_xy[t]
        return x + tw / 2, yv + th / 2

    def manhattan(a_, b_):
        return abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
    top_y = sum(spine_y['spine_engine_top']) / 2
    vm_y = sum(spine_y['spine_vm']) / 2
    top_pt, vm_pt = (F.DIE_W / 2, top_y), (F.DIE_W / 2, vm_y)
    # x network / instruction broadcast: VM (and the top beside it) -> every tile's input pins
    far_x = max(manhattan(vm_pt, centre(t)) + (tw + th) / 2 for t in tile_xy)
    far_i = max(manhattan(top_pt, centre(t)) + (tw + th) / 2 for t in tile_xy)
    XVM = 1
    BD = max(wc(far_x) + XVM, wc(far_i))
    # upper tree levels 3..TCUT: children's hosts (or tiles) -> the node's host tile
    lvl = {}
    for lv in range(LT + 1, TCUT + 1):
        worst = 0.0
        for pp in range(G >> lv):
            h = host_tile(lv, pp)
            for ch in (2 * pp, 2 * pp + 1):
                src = ch if lv - 1 == LT else host_tile(lv - 1, ch)
                if src not in tile_xy or h not in tile_xy:
                    continue
                worst = max(worst, manhattan(centre(src), centre(h)) + (tw + th) / 2)
        lvl[lv] = dict(worst_um=round(worst, 1), stages=wc(worst))
    NWS = max(v['stages'] for v in lvl.values())
    # level TCUT words -> the spine top
    far_t = max(manhattan(centre(host_tile(TCUT, b)), top_pt) + (tw + th) / 2 for b in range(NB)
                if host_tile(TCUT, b) in tile_xy)
    TWS = wc(far_t)
    # result write: port groups (spine top) -> VM
    ORD = wc(abs(top_y - vm_y) + sw / 2)
    ucie = sx - (F.EDGE_KEEP + ucie_w)
    xd = BD + (TCUT - LT) * NWS + TWS
    conns = [
        dict(name='instruction broadcast + x network: spine -> farthest tile', distance_um=round(max(far_x, far_i), 1),
             stages=BD, rtl_param='BD (includes the tile input register and XVM = 1)',
             bits=(3 * 18 + 13 * 24 + 13 + 1) + (1 << a.smax) * 32,
             note=f'{(1 << a.smax) // 4} quad lines of 128 bits leave the VM; line r feeds tiles t = r mod {(1 << a.smax) // 4}'),
        *(dict(name=f'split-tree level {lv}: child -> node host', distance_um=v['worst_um'], stages=v['stages'],
               rtl_param='NWS (uniform: the max over levels)', bits=G // (1 << (lv - 1)) * 16 * 32 // 2 * 2)
          for lv, v in lvl.items()),
        dict(name=f'split-tree level {TCUT} words -> spine top', distance_um=round(far_t, 1), stages=TWS,
             rtl_param='TWS', bits=NB * 16 * 32),
        dict(name='result write: port groups -> VM', distance_um=round(abs(top_y - vm_y) + sw / 2, 1), stages=ORD,
             rtl_param='ORD', bits=NB * 16 * 32),
        dict(name='TP exchange: spine -> UCIe PHY (one way)', distance_um=round(ucie, 1), stages=wc(ucie),
             rtl_param='not in the RTL (ot_rom_oneshot_allreduce LAT 11 is the link hop); priced per crossing',
             bits=512),
    ]
    # bisection over the vertical cut through the west array (M6 + M8 at 50% signal share)
    per_um = sum(1000.0 / F.UPPER_PITCH_NM[l] for l in ('M6', 'M8')) * F.SIGNAL_SHARE
    cap = per_um * core_h
    west_demand = ((1 << a.smax) * 32 + (3 * 18 + 13 * 24 + 14)       # x lines and broadcast (all reach west)
                   + (NB // 2) * 16 * 32                                # tree words from west blocks
                   + 3277 * 8 // 2)                                     # KV fill share
    leg = legality(p)
    macro_counts = {mn: sum(1 for m in p.macros if m['macro'] == mn) for mn in sorted({m['macro'] for m in p.macros})}
    tile_macros = rp['code_rom']['banks_per_column'] * 2
    macro_counts['ot_rom_4096x266_m8 (in tiles)'] = NT * tile_macros
    macro_counts['ot_sram_1r1w_128x256_m1_r2c2 (in tiles)'] = NT * 2
    array_need = NT * tw * th / 1e6
    rec = dict(
        schema='opentallas.qwen-rom-floorplan-w12.v1', tool='tools/qwen_rom_floorplan_w12.py',
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_sha256={q: sha(q) for q in ('tools/qwen_o4_floorplan.py', 'tools/uarch_model.py',
                                           'physical/asap7_memory_macros/index.json', 'results/arch/qwen3_budget.json')},
        rom_placement_sha256=hashlib.sha256(a.rom_placement.read_bytes()).hexdigest(),
        tile_outline_source=tile_src,
        design=dict(groups=G, tiles=NT, tile_groups=4, smin=a.smin, tree_cut=TCUT, blocks=NB, tiles_per_block=BLK,
                    code_banks_per_column=rp['code_rom']['banks_per_column'], tile_macros=tile_macros + 2,
                    ports=ports, scale_local=True),
        clock_hz=CLOCK_HZ, reach_um_override=a.reach_um, wire=dict(ps_per_um=U.WIRE_PS_PER_UM_LOADED, overhead_ps=U.WIRE_OVERHEAD_PS,
                                     reach_um=round((1e12 / CLOCK_HZ - U.UNCERTAINTY_PS - U.WIRE_OVERHEAD_PS) /
                                                    U.WIRE_PS_PER_UM_LOADED, 1)),
        die_um=[F.DIE_W, round(F.DIE_H, 3)],
        tile_um=[round(tw, 3), round(th, 3)], tile_mm2=round(tw * th / 1e6, 5),
        core=dict(y0=core_y0, y1=round(core_y1, 3), west=west, east=east),
        spine=dict(x=sx, width_um=sw, used_um=round(spine_used, 1), core_height_um=round(core_h, 1),
                   blocks=[{k: v for k, v in b.items() if k != 'place'} for b in bl]),
        arrays=arrays, block_capacity=cap_blocks, blocks_needed=NB,
        tiles_needed=NT, tiles_capacity_grid=cap_tiles, tiles_capacity_in_blocks=cap_blocks * BLK,
        array_area_mm2=round(tiles_region_area / 1e6, 1), tiles_area_mm2=round(array_need, 1),
        fits=fits, margin_blocks=cap_blocks - NB,
        margin_fraction=round((cap_blocks - NB) / cap_blocks, 4) if cap_blocks else None,
        margin_fraction_grid=round((cap_tiles - NT) / cap_tiles, 4) if cap_tiles else None,
        legality=leg, macro_counts=macro_counts,
        wire_stages=dict(BD=BD, XVM=XVM, NWS=NWS, TWS=TWS, ORD=ORD, XD=xd, engine_latency_added=xd + ORD,
                         per_level=lvl),
        connections=conns,
        bisection=dict(tracks_per_um=round(per_um, 2), cut_um=round(core_h, 1), capacity_wires=int(cap),
                       west_demand_wires=int(west_demand), utilisation=round(west_demand / cap, 4)),
        vm_x_read=dict(note=('the x chunk port reads up to 2^SMAX = %d elements in a cycle when a K step starts '
                             '(o/down at S = 2,048; the weighted sum reads 512 a cycle every cycle); the W5 VM '
                             '(96 x 512x128) serves 128 FP32 a cycle. A VM x-read bandwidth gap, not modelled.'
                             % (1 << a.smax))),
        claim_boundary=('macro-level floorplan: tile outline from its P&R record (or an estimate), spine blocks '
                        'from macro views and estimated logic; distances priced with the model wire constant; '
                        'no die route, no timing closure of the spine, no power integrity'))
    a.out_dir.mkdir(parents=True, exist_ok=True)
    stem = a.out_dir / f'qwen_rom_g{G}'
    rec['def_sha256'] = F.write_def(p, str(stem) + '_macros.def')
    F.write_svg(p, str(stem) + '.svg')
    (a.out_dir / f'qwen_rom_g{G}.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(json.dumps({k: rec[k] for k in ('tile_um', 'fits', 'blocks_needed', 'block_capacity', 'margin_fraction',
                                          'tiles_capacity_grid', 'margin_fraction_grid',
                                          'tiles_area_mm2', 'array_area_mm2', 'wire_stages', 'legality')},
                     indent=1, default=str)[:2500])


if __name__ == '__main__':
    main()
