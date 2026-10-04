#!/usr/bin/env python3
"""Qwen3-8B ROM die floorplan model with near-HBM attention (model only; no RTL, no P&R).

Successor of the W12 frame (tools/qwen_rom_floorplan_w12.py, tools/qwen_o4_floorplan.py) for the
design selected for build in results/uarch/qwen_rom_calibrated_calendar_20261003/near-hbm-selected-r1.json:
TP4, G = 6,144 groups a die, 1,536 tiles, 4 HBM3E stacks a die, attention moved to a strip behind each
HBM PHY (two-phase, residue-512 striping, golden order), tree tops / 1/Z / multiply at the hub.

AGENTS.md method: floorplan -> one hardened element -> replicate.  This tool states the die outline, the
replicated tile field, the hub spine, the shoreline (PHY + controller band + near-HBM strip), the four
hub<->stack link corridors (tracks against capacity per layer), power-grid share, clock domains and CDC
locations, the area ledger (with the removed fill/assembly/credit service and the tile KV macros, whose
other users are verified in the source), SS wire stages, shoreline power density, and the ordered list
of hardened elements to qualify by P&R with their frames and target utilisation.

Three frames are evaluated; the tool selects the first that is legal (26 x 33 mm, sourced beachfront
ceiling, IO edge available, every corridor within capacity):
  A  current tile slot (357.696 x 1360.8 um, 96.768 um fill corridor), HBM on E/W edges
  B1 tile corridor narrowed to the non-fill demand, slot height kept
  B2 B1 plus slot height re-derived for the same 125,000 um2 cell ceiling at 0.5 (KV macros removed)
N/S HBM placement is evaluated as well and refused when it does not fit.

Usage:
  python3 tools/qwen_rom_floorplan_nearhbm.py --out-dir results/uarch/qwen_rom_floorplan_nearhbm_20261003
  python3 tools/qwen_rom_floorplan_nearhbm.py --verify
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import uarch_model as U  # noqa: E402  (SS reach, HBM shoreline constants)
import v41_die_assembly as VA  # noqa: E402  (closed-form die-grid IR model and its sourced constants)
import power_scenarios as PS  # noqa: E402  (cooling reference die share)

OUT = ROOT / 'results/uarch/qwen_rom_floorplan_nearhbm_20261003'
RECORD = 'model-r1.json'
SVG = 'floorplan-r1.svg'
SCHEMA = 'opentallas.qwen-rom-floorplan-nearhbm.v1'

CAL = 'results/uarch/qwen_rom_calibrated_calendar_20261003'
P = dict(
    pricing=f'{CAL}/inputs/nearhbm/near_hbm_attention_pricing.json',
    selected=f'{CAL}/near-hbm-selected-r1.json',
    cooling=f'{CAL}/inputs/cooling/qwen_rom_cooling_recheck.json',
    catalog='physical/asap7_memory_macros/index.json',
    phy='physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json',
    pin_audit='results/uarch/qwen_rom_floorplan_nearhbm_20261003/inputs/pinaccess/pin_access_audit.json',
    tile_rtl='rtl/hdc/ot_qwen_rom_tile_w12.sv',
    program='tools/hdc_program.py',
    fulltile='tools/uarch_model_qwen_rom_fulltile_slot.py',
    parent_ctx='results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json',
    credit17='results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json',
    dims='results/uarch/qwen_rom_physical_dimensions_20261002/blocked_dimensions_r2.json',
    w5='results/floorplan/qwen_o4/floorplan.json',
    power='configs/hardware/power_scenarios.json',
    tech='configs/hardware/technology.json',
    pdn='tools/chip_assembly/tcl/pdn_die.tcl',
    uarch='tools/uarch_model.py',
    die_assembly='tools/v41_die_assembly.py',
    budget='tools/arch_budget_qwen3.py',
    o4='tools/qwen_o4_floorplan.py',
    power_tool='tools/power_scenarios.py',
    matvec='rtl/hdc/ot_qwen_w12_matvec.sv',
)

# ---- lattice and policy constants (each with its source) ----
SNAP_X, SNAP_Y = 0.432, 2.16           # tools/qwen_o4_floorplan.py SNAP_X/SNAP_Y (PDN strap pitch / 8 rows)
EDGE_KEEP = 20.0                       # tools/qwen_o4_floorplan.py EDGE_KEEP
PITCH_NM = {'M6': 64, 'M7': 64, 'M8': 80, 'M9': 80}   # tools/qwen_o4_floorplan.py UPPER_PITCH_NM
SIGNAL_SHARE = 0.5                     # tools/qwen_o4_floorplan.py SIGNAL_SHARE (rest: PDN straps, vias, OBS)
RETICLE_UM = (26000.0, 33000.0)        # uarch_model.HBM_SHORE['reticle_mm'] (no stitching)
DIE_BUDGET_MM2 = 815.0                 # technology.json reticle.area_mm2 (Taalas HC1, the iso-area unit)
TILE_COLS, TILE_ROWS = 64, 24          # credit17 model-r3 routing_cost grid_columns/grid_rows (1,536 tiles)
TILE_SLOT_UM = (357.696, 1360.8)       # tools/qwen_rom_local_subtree_context.py selected_slot_um
CORRIDOR_UM = 96.768                   # fulltile slot / parent context selected corridor (M6 756 + M8 604 = 1,360)
CELL_CEILING_UM2 = 125000.0            # fulltile slot complete_cell_area_ceiling_um2 (at logic_utilization 0.5)
TILE_LOGIC_UTIL = 0.5                  # fulltile slot logic_utilization (kept: never raised here)
TILE_HALO_UM2 = 10000.0                # fulltile slot macro_halo_reservation_um2
ROM_MACRO, KV_MACRO, SCORE_MACRO = 'ot_rom_4096x266_m8', 'ot_sram_1r1w_128x256_m1_r2c2', 'ot_sram_1r1w_1024x256_m2_r2c2'
ROMS_PER_TILE, KV_PER_TILE = 10, 2     # blocked_dimensions_r2 macro_count_per_tile (CODE_BANKS 5 x 2 columns; 2 KV)
NONFILL_CUT_TRACKS = 64 + 64 + 379 + 1 + 128 + 1   # clock, reset, instruction, go, x, ready (uarch_model_qwen_kv_bank_groups cut)
FILL_TRACKS_PER_LANE = 1048            # fulltile slot fill_tracks
SPARE = (1360 - 1176) / 1176           # the fulltile reservation's own spare over its demand (15.6 %): applied to every channel
FF_UM2 = 0.37908 + 0.04374             # parent context model-r7 ASR + INV per bit (pricing FF)
LINK_FIFO_DEPTH = 8                    # ASSUMED mesochronous bisync FIFO depth per link direction
CELL_UTIL_TARGET = 0.70                # macro pin-access audit: route-feasible frame ~0.70 (timing binds first)

# ---- near-HBM shape (pricing r1/r2, unchanged in the selected entry) ----
STACKS = 4
ROW_ENGINE_PITCH_Y = 1998.0            # 925 x 2.16: six frames along a 12,000.096 um PHY


def snap_up(v, q):
    return math.ceil(v / q - 1e-9) * q


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def load(rel):
    return json.loads((ROOT / rel).read_text())


def capacity(width_um, layers):
    """signal tracks a corridor of this width offers on these layers (the fulltile slot's rule)"""
    return {l: math.floor(math.floor(width_um / (PITCH_NM[l] / 1000) + 1e-8) * SIGNAL_SHARE) for l in layers}


def width_for(tracks, layers, q=SNAP_X):
    w = q
    while sum(capacity(w, layers).values()) < tracks:
        w += q
    return round(w, 3)


def allot(tracks, cap):
    """fill layers in order; returns used per layer and the spare"""
    left, used = tracks, {}
    for l, c in cap.items():
        used[l] = min(c, left)
        left -= used[l]
    return dict(used=used, unrouted=left, spare={l: cap[l] - used[l] for l in cap}, fits=left == 0)


def stages(um, reach):
    return max(1, math.ceil(um / reach)) if um > 0 else 0


# ---------------------------------------------------------------- source verification (other users of tile KV)
def kv_macro_users():
    """The tile KV SRAMs' read port feeds only ME ops with me_wsrc = 1; their write port only the KV fill / new-token
    write (SU dst = DST_KV).  Both move to the near-HBM unit, so the macros have no other user."""
    prog = (ROOT / P['program']).read_text()
    rtl = (ROOT / P['tile_rtl']).read_text()
    wsrc1 = [i + 1 for i, l in enumerate(prog.splitlines()) if re.search(r'me_wsrc\s*=\s*1', l)]
    dstkv = [i + 1 for i, l in enumerate(prog.splitlines()) if 'dst=I.DST_KV' in l]
    inst = re.findall(r'ot_sram_1r1w_128x256_m1_r2c2\s+u_kv', rtl)
    gen = re.search(r'for \(p = 0; p < (\d+); p = p \+ 1\) begin : g_kv', rtl)
    read_sel = re.search(r'kv_re <= wsrc_r', (ROOT / 'rtl/hdc/ot_qwen_w12_matvec.sv').read_text())
    per_tile = int(gen.group(1)) if gen and inst else None
    return dict(
        macro=KV_MACRO, per_tile_in_rtl=per_tile, per_die=per_tile * TILE_COLS * TILE_ROWS if per_tile else None,
        read_users=[f'{P["program"]}:{n} (ME op me_wsrc=1: attention scores and P.V)' for n in wsrc1],
        write_users=[f'{P["program"]}:{n} (SU dst=DST_KV: new-token K/V write, DYN_KWRITE/DYN_VWRITE)' for n in dstkv],
        read_port_select='rtl/hdc/ot_qwen_w12_matvec.sv: kv_re <= wsrc_r (only KV-sourced ops read the slice)'
        if read_sel else None,
        write_port='rtl/hdc/ot_qwen_rom_tile_w12.sv kvw_* (registered masked port from the die KV fill network only)',
        other_users=[], both_users_move_to_near_hbm=len(wsrc1) == 2 and len(dstkv) == 2,
        credit_valid=per_tile == 2 and len(wsrc1) == 2 and len(dstkv) == 2,
        pricing_count_correction=('near_hbm_attention_pricing r1 credits one macro per GROUP (6,144 x 3,891.6 um2 = '
                                  '23.91 mm2, the unified-model QWEN_AREA ledger of the W5 tile); the W12 tile RTL and '
                                  'blocked_dimensions_r2 hold 2 per TILE (one per group pair): 3,072 macros'))


# ---------------------------------------------------------------- frames
def tile_slot(variant, mac):
    rom_w, rom_h = mac[ROM_MACRO]['width_um'], mac[ROM_MACRO]['height_um']
    kv_a = mac[KV_MACRO]['area_um2']
    rom_a = ROMS_PER_TILE * mac[ROM_MACRO]['area_um2']
    if variant == 'A':
        w_c, (sw, sh), kv = CORRIDOR_UM, TILE_SLOT_UM, KV_PER_TILE
        demand = FILL_TRACKS_PER_LANE + NONFILL_CUT_TRACKS
    else:
        demand = NONFILL_CUT_TRACKS
        w_c = width_for(math.ceil(demand * (1 + SPARE)), ('M7', 'M9'))
        sw = round(2 * rom_w + 4 * 4.32 + w_c, 3)
        kv = 0
        if variant == 'B1':
            sh = TILE_SLOT_UM[1]
        else:
            need = CELL_CEILING_UM2 / TILE_LOGIC_UTIL + rom_a + TILE_HALO_UM2
            sh = snap_up(need / (sw - w_c), SNAP_Y)
            sh = max(sh, snap_up(5 * (rom_h + 2 * 2.16), SNAP_Y))
    macro_a = rom_a + kv * kv_a
    cap = capacity(w_c, ('M7', 'M9'))
    logic_cap = ((sw - w_c) * sh - macro_a - TILE_HALO_UM2) * TILE_LOGIC_UTIL
    return dict(variant=variant, w_um=round(sw, 3), h_um=round(sh, 3), area_um2=sw * sh, corridor_um=w_c,
                corridor_capacity=cap, corridor_demand_tracks=demand,
                corridor=allot(demand, cap), kv_macros=kv, macro_area_um2=macro_a,
                cell_capacity_at_util_um2=round(logic_cap), cell_ceiling_um2=CELL_CEILING_UM2,
                cell_fit=logic_cap >= CELL_CEILING_UM2 - 1e-6, logic_util=TILE_LOGIC_UTIL,
                lattice_ok=abs(sw / SNAP_X - round(sw / SNAP_X)) < 1e-6 and abs(sh / SNAP_Y - round(sh / SNAP_Y)) < 1e-6)


def row_engine(pr, mac):
    """one of six per stack: 512 MAC lanes (4 q heads x 128 d), its score-tree / P.V accumulators, 4 exp pipes,
    one score SRAM (6 a stack instead of the pricing's 4: one per element, self-contained), q stationary"""
    c = pr['area_mm2']['components_um2']
    n = pr['rates_per_stack']['row_engines']
    sram = mac[SCORE_MACRO]
    lanes_hi, lanes_lo = c['lanes_MAC_UM2'] / n, c['lanes_LANE_COPY_plus_tree'] / n
    common = dict(exp_pipes=c['exp_pipes'] / n, s_minus_max_adders=c['s_minus_max_adders'] / n,
                  Z_chunk_adders=c['Z_chunk_adders'] / n, PV_tree_FF=c['PV_streaming_tree_stack_FF'] / n,
                  score_SRAM=sram['area_um2'], q_stationary_FF=c['q_stationary_FF'] / n)
    ctrl = pr['area_mm2']['control_share_assumed']
    hi = (lanes_hi + sum(common.values())) * (1 + ctrl)
    lo = (lanes_lo + sum(common.values())) * (1 + ctrl)
    depth = snap_up(hi / ROW_ENGINE_PITCH_Y, SNAP_X)
    return dict(per_stack=n, lanes=pr['rates_per_stack']['MAC_lanes'] // n, exp_pipes=pr['rates_per_stack']['exp_pipes'] // n,
                score_macros=1, score_macro=SCORE_MACRO, components_um2={k: round(v) for k, v in common.items()},
                lanes_um2=dict(hi=round(lanes_hi), lo=round(lanes_lo)),
                area_um2=dict(hi=round(hi), lo=round(lo)), frame_um=[round(depth, 3), ROW_ENGINE_PITCH_Y],
                frame_area_um2=round(depth * ROW_ENGINE_PITCH_Y), fill_hi=round(hi / (depth * ROW_ENGINE_PITCH_Y), 4),
                fill_lo=round(lo / (depth * ROW_ENGINE_PITCH_Y), 4),
                extra_score_macros_per_stack=n - 4,
                extra_score_macro_mm2_per_die=round(STACKS * (n - 4) * sram['area_um2'] / 1e6, 4))


def hub_element(pr):
    c = pr['area_mm2']['components_um2']
    link_bits = pr['boundaries']['tracks_per_stack_link']
    q_stage_bits = pr['boundaries']['in_bits_per_layer_per_stack']
    parts = dict(hub_combine=c['hub_combine'], max_compare_broadcast=c['max_compare'],
                 link_endpoint_FIFOs_hub_side=STACKS * link_bits * LINK_FIFO_DEPTH * FF_UM2,
                 q_newkv_staging_at_CDC=q_stage_bits * FF_UM2)
    ctrl = pr['area_mm2']['control_share_assumed']
    area = sum(parts.values()) * (1 + ctrl)
    side = snap_up(math.sqrt(area / CELL_UTIL_TARGET), SNAP_Y)
    side_x = snap_up(side, SNAP_X)
    return dict(parts_um2={k: round(v) for k, v in parts.items()}, area_um2=round(area),
                frame_um=[round(side_x, 3), round(side, 3)], util_at_routed_constants=round(area / (side_x * side), 3))


def hub_reservation(w5, pr):
    """hub spine contents: the W5 spine blocks (TP2, the only placed spine) carried to TP4 where the scaling is
    stated, plus the collective and the near-HBM hub element.  Every row is graded; none is a measured TP4 block."""
    reg = {r['name']: r['w'] * r['h'] / 1e6 for r in w5['designs']['rom_die.reachable_pruned']['regions']}
    rows = [
        ('port_tiles', reg['spine_port_tiles'], 'W5 spine_port_tiles (G>>SMIN = 96 port groups, same G at TP4)', 'placed-W5'),
        ('scale_rom', reg['spine_scale_rom'], 'W5 spine_scale_rom (whole-image replica; W12 SCALE_LOCAL size at TP4 unmeasured)', 'placed-W5'),
        ('vector_memory', reg['spine_vm'], 'W5 spine_vm', 'placed-W5'),
        ('embedding_rom', reg['spine_embedding_rom'] / 2, 'W5 half-vocabulary ROM / 2 (TP4 quarter vocabulary); may fit '
         'the 0.20 GB spare tile ROM instead (not verified)', 'scaled'),
        ('constants_sequencer', reg['spine_constants_sequencer'], 'W5 constant ROM, program, sequencer', 'placed-W5'),
        ('stream_unit_SU64_SFU', 64 * 25000 / 1e6, 'SU64 (TP4 terminal D4/G6144/SU64) x 25,000 um2 a lane '
         '(tools/arch_budget_qwen3.py SU_SPILL_MM2 basis, estimated)', 'estimated'),
        ('tree_top', reg['spine_tree_top'], 'W5 split-tree top registers and result compaction', 'placed-W5'),
        ('collective', reg['collective'], 'W5 collective reservation (all-reduce engine, link flow control)', 'reservation-W5'),
    ]
    return [dict(name=n, mm2=round(a, 3), source=s, grade=g) for n, a, s, g in rows]


IO_HOSTED = ('embedding_rom', 'collective')   # once-per-token lookup and the link-side collective sit beside the IO


def frame(variant, hbm_edges, mac, pr, phy, hub_rows, hub_el, re_el, svc_mm2):
    slot = tile_slot(variant, mac)
    phy_w, phy_h = phy['footprint']['width_um'], phy['footprint']['height_um']
    # controller / per-PC service band behind each PHY: the WHOLE current known KV service (credit17 model-r3
    # cells.total_known_service_mm2, 19.22 mm2 a die) kept, a quarter per stack -- no credit for the removed fill
    svc_band = svc_mm2 * 1e6 / STACKS / phy['footprint']['width_um']
    strip = re_el['frame_um'][0]
    band = snap_up(phy_h, SNAP_X) + snap_up(svc_band, SNAP_X) + strip
    ucie_mm2 = 10.0                                            # arch_budget_qwen3.UCIE_PHY_MM2 (assumed)
    ucie_len = 6400.0                                          # same note: ~6.4 mm of the shared edge
    ucie_depth = snap_up(ucie_mm2 * 1e6 / ucie_len, SNAP_Y)
    board_io_mm2 = 10 * 0.4                                    # ASSUMED 10 board SerDes lanes x 0.4 mm2 (uarch_model table_io lane)
    link_tracks = pr['boundaries']['tracks_per_stack_link']
    link_need = math.ceil(link_tracks * (1 + SPARE))
    h_chan = CORRIDOR_UM if sum(capacity(CORRIDOR_UM, ('M6', 'M8')).values()) >= link_need else width_for(link_need, ('M6', 'M8'))
    v_need = math.ceil(2 * link_tracks * (1 + SPARE))
    v_chan = width_for(v_need, ('M7', 'M9'))
    arr_w = TILE_COLS * slot['w_um']
    arr_h = TILE_ROWS * slot['h_um'] + 2 * h_chan
    hub_mm2 = sum(r['mm2'] for r in hub_rows if r['name'] not in IO_HOSTED) + hub_el['area_um2'] / 1e6
    io_hosted_mm2 = sum(r['mm2'] for r in hub_rows if r['name'] in IO_HOSTED)
    io_need_len = (ucie_mm2 + board_io_mm2 + io_hosted_mm2) * 1e6 / ucie_depth
    spine_h = arr_h
    spine_w = snap_up(hub_mm2 * 1e6 / spine_h + v_chan, SNAP_X)
    errs = []
    if hbm_edges == 'EW':
        W = 2 * EDGE_KEEP + 2 * band + arr_w + spine_w
        H = 2 * EDGE_KEEP + arr_h + ucie_depth
        shore_edge_len = H - 2 * EDGE_KEEP - ucie_depth
        need_edge = 2 * phy_w
        io_edge = 'north'
        core_x0 = EDGE_KEEP + band
        core_y0 = EDGE_KEEP
    else:
        W = 2 * EDGE_KEEP + arr_w + spine_w + ucie_depth
        H = 2 * EDGE_KEEP + 2 * band + arr_h
        shore_edge_len = W - 2 * EDGE_KEEP - ucie_depth
        need_edge = 2 * phy_w + 2 * U.HBM_SHORE['corner_mm'] * 1000
        io_edge = 'west'
        core_x0 = EDGE_KEEP + ucie_depth
        core_y0 = EDGE_KEEP + band
    W, H = snap_up(W, SNAP_X), snap_up(H, SNAP_Y)
    fits = W <= RETICLE_UM[0] + 1e-6 and H <= RETICLE_UM[1] + 1e-6
    if not fits:
        errs.append(f'outline {W:.0f} x {H:.0f} um exceeds the 26 x 33 mm field')
    if shore_edge_len < need_edge:
        errs.append(f'two PHYs need {need_edge:.0f} um of each HBM edge; {shore_edge_len:.0f} available')
    io_len = (W if hbm_edges == 'EW' else H) - 2 * EDGE_KEEP
    if io_need_len > io_len:
        errs.append(f'IO band needs {io_need_len:.0f} um of edge; {io_len:.0f} available')
    if not slot['corridor']['fits']:
        errs.append(f"tile corridor demand {slot['corridor_demand_tracks']} > capacity "
                    f"{sum(slot['corridor_capacity'].values())} (deficit {slot['corridor']['unrouted']})")
    if not slot['cell_fit']:
        errs.append('tile cell ceiling does not fit the slot at 0.5')
    perim = 2 * (W + H) / 1000
    beach = STACKS * U.HBM_SHORE['phy_edge_mm'] / perim, STACKS * phy_w / 1000 / perim
    beach_cap = load(P['tech'])['hbm']['hbm3e']['max_beachfront_utilization']['value']
    if beach[1] > beach_cap:
        errs.append('beachfront above the sourced ceiling')
    aspect = spine_h / spine_w
    return dict(variant=variant, hbm_edges=hbm_edges, legal=not errs, errors=errs, die_um=[round(W, 3), round(H, 3)],
                die_mm2=round(W * H / 1e6, 2), within_815_budget=W * H / 1e6 <= DIE_BUDGET_MM2,
                fits_26x33=fits, tile_slot=slot, array_um=[round(arr_w, 3), round(arr_h, 3)],
                core_origin_um=[round(core_x0, 3), round(core_y0, 3)],
                shoreline=dict(edges=('east', 'west') if hbm_edges == 'EW' else ('north', 'south'),
                               band_depth_um=round(band, 3), phy_um=[phy_h, phy_w], controller_band_um=round(snap_up(svc_band, SNAP_X), 3),
                               near_hbm_strip_um=strip, edge_len_um=round(shore_edge_len, 1), needed_edge_um=round(need_edge, 1),
                               beachfront_fraction_12mm=round(beach[1], 3), beachfront_fraction_8p5mm=round(beach[0], 3),
                               beachfront_ceiling=beach_cap),
                io=dict(edge=io_edge, ucie_mm2=ucie_mm2, ucie_len_um=ucie_len, band_depth_um=round(ucie_depth, 3),
                        board_serdes_reservation_mm2=board_io_mm2, hosted=list(IO_HOSTED),
                        hosted_mm2=round(io_hosted_mm2, 2), used_len_um=round(io_need_len, 1), edge_len_um=round(io_len, 1)),
                spine=dict(w_um=round(spine_w, 3), h_um=round(spine_h, 3), mm2=round(spine_w * spine_h / 1e6, 2),
                           hub_contents_mm2=round(hub_mm2, 2), vertical_link_channel_um=v_chan, aspect=round(aspect, 1)),
                link_channels=dict(horizontal_um=h_chan, vertical_um=v_chan, link_tracks=link_tracks,
                                   horizontal_need_tracks=link_need, vertical_need_tracks=v_need))


# ---------------------------------------------------------------- routes, stages, CDC, power
def routes(fr, pr, re_el):
    W, H = fr['die_um']
    x0, y0 = fr['core_origin_um']
    aw, ah = fr['array_um']
    slot_h = fr['tile_slot']['h_um']
    hc = fr['link_channels']['horizontal_um']
    hub_x = x0 + aw / 2 + fr['spine']['w_um'] / 2
    hub_y = y0 + ah / 2
    k = round(6000.0 / slot_h)                       # tile rows between the mid-line and each link channel
    ch_off = k * slot_h + hc / 2                     # channel centre offset from the mid-line (one channel each side)
    strip_face = EDGE_KEEP + fr['shoreline']['band_depth_um']
    dx = hub_x - strip_face
    reach = U.SS_REACH_UM[1.2e9]
    trunk_um = dx + ch_off
    # the link enters the strip at the stack centre (stacks aligned to the channels) and fans out to six frames
    pitch = ROW_ENGINE_PITCH_Y
    fan_um = 2.5 * pitch + fr['shoreline']['near_hbm_strip_um'] / 2
    phy_pin_span = 1768.128                            # ot_hbm3e_phy pins.pin_span_um (centred block)
    pin_to_far_engine = 2.5 * pitch + pitch / 2 - phy_pin_span / 2 + fr['shoreline']['controller_band_um']
    st_trunk, st_fan = stages(trunk_um, reach), stages(fan_um, reach)
    model_stages = pr['latency']['constants']['wire_stages_hub_to_stack']
    per_layer_delta = 2 * (st_trunk + st_fan - model_stages)
    L = pr['shape']['layers']
    ucie_um = (y0 + ah) - hub_y + fr['io']['band_depth_um'] / 2 if fr['io']['edge'] == 'north' else hub_x - x0
    st_ucie = stages(ucie_um, reach)
    tracks = pr['boundaries']['tracks_per_stack_link']
    hcap = capacity(hc, ('M6', 'M8'))
    vcap = capacity(fr['link_channels']['vertical_um'], ('M7', 'M9'))
    return dict(
        hub_xy_um=[round(hub_x, 1), round(hub_y, 1)],
        stack_centres_um=[[round(s, 1), round(hub_y + d * ch_off, 1)] for s in (strip_face, W - strip_face) for d in (-1, 1)],
        channel_rows_from_midline=k,
        hub_to_stack=dict(manhattan_um=round(trunk_um, 1), trunk_stages=st_trunk, in_strip_fan_um=round(fan_um, 1),
                          in_strip_fan_stages=st_fan, total_stages=st_trunk + st_fan, model_stages=model_stages,
                          model_basis='pricing: gh/2 + 6,000 um to the stack centre at 504 um/stage (hub at array centre, '
                                      'PHYs on N/S), in-strip fan not separated',
                          per_layer_cycle_delta_vs_model=per_layer_delta,
                          per_token_cycle_delta=per_layer_delta * L,
                          per_token_us_delta=round(per_layer_delta * L / 1.2e9 * 1e6, 3),
                          reach_um_per_stage=reach),
        phy_pins_to_farthest_row_engine=dict(um=round(pin_to_far_engine, 1), stages=stages(pin_to_far_engine, reach),
                                             note='on the HBM read-to-row-engine path; NOT in the selected entry\'s 1,700 '
                                                  'cycles unless the phase start is prefetched'),
        hub_to_io_edge=dict(edge=fr['io']['edge'], um=round(ucie_um, 1), stages_1p2GHz=st_ucie,
                            stages_0p9GHz=stages(ucie_um, U.SS_REACH_UM[0.9e9]),
                            note='UCIe/board link must sit on an edge without HBM; owned by the one-segment all-reduce '
                                 'stream: reconcile against its collective LAT, not priced here'),
        corridors=dict(
            per_link_tracks=tracks, link_bus_bits_each_way=pr['boundaries']['link_bus_bits_each_way'],
            horizontal=dict(count=2, width_um=hc, layers=hcap, demand_tracks=tracks,
                            allotment=allot(tracks, hcap),
                            note='one channel between tile rows at each stack-centre height; carries the west link on '
                                 'its west half and the east link on its east half: one link per cut'),
            vertical_in_spine=dict(width_um=fr['link_channels']['vertical_um'], layers=vcap, demand_tracks=2 * tracks,
                                   allotment=allot(2 * tracks, vcap),
                                   note='hub to the two channel heights: NW+NE links share the northern leg, SW+SE the southern'),
            tile_column_corridor=dict(width_um=fr['tile_slot']['corridor_um'], layers=fr['tile_slot']['corridor_capacity'],
                                      demand_tracks=fr['tile_slot']['corridor_demand_tracks'],
                                      allotment=fr['tile_slot']['corridor']),
            fill_control_tracks_removed=pr['boundaries']['fill_control_tracks_removed'],
            current_shared_tile_cut=dict(required=FILL_TRACKS_PER_LANE + NONFILL_CUT_TRACKS, capacity=1360,
                                         deficit=FILL_TRACKS_PER_LANE + NONFILL_CUT_TRACKS - 1360,
                                         source='parent context model-r7 wire.shared_tile_cut_tracks_required')),
        link_wire_um_per_die=round(STACKS * tracks * trunk_um))


def cdc_plan(fr, rt):
    return [
        dict(id='X1', where='hub spine centre: ME tree top / x-root (1.2 GHz) -> SU/SFU lanes (0.9 GHz)', kind='async FIFO (existing hub-edge crossing, dataflow level 2)', count=1, new=False),
        dict(id='X2', where='hub spine centre: SU/VM (0.9 GHz) -> x-broadcast root (1.2 GHz)', kind='async FIFO (existing)', count=1, new=False),
        dict(id='X3', where='hub spine centre: SU q (after RoPE) + new k/v (0.9 GHz) -> four stack links (1.2 GHz)', kind='async FIFO feeding the hub-side link endpoints; q staged once, broadcast to 4 links', count=1, new=True),
        dict(id='M1-M4', where='strip end of each hub<->stack link (stack centre)', kind='mesochronous bisync FIFO: same 1.2 GHz, separate local trees (one die tree would carry ~0.8 ns skew, v41_die_assembly clock section)', count=4, new=True,
             latency_cycles_each_way_assumed=2, per_token_cycles=2 * 2 * 36),
        dict(id='P1-P4', where='HBM controller <-> PHY DFI inside each shoreline band', kind='PHY IP boundary: the abstract assumes a 1,000 MHz controller clock (ot_hbm3e_phy.json interface.controller_clock_mhz, assumed); AGENTS.md puts the HBM service at 1.2 GHz, so the crossing sits at the PHY boundary if the licensed DFI clock differs', count=4, new=False),
        dict(id='L1-L2', where=f"{fr['io']['edge']} IO band: UCIe peer link and board SerDes", kind='plesiochronous link crossings (existing practice, results/rtl/v41_link_cdc_campaign.json K3)', count=2, new=False),
        dict(id='none', where='hub combine (P.V levels 8-9, Z levels 5-10, 1/Z, multiply)', kind='kept in the 1.2 GHz streaming domain as priced (139-cycle return_and_hub); recip/fp32_mul do not close at SS 1.2 GHz -> fallback is the SFU across X1 (priced below)', count=0, new=False),
    ]


def recip_fallback(pr):
    recip = pr['latency']['constants']['RECIP_LAT']
    at_0p9 = math.ceil(recip * 1.2 / 0.9)
    cross = 2 * 3
    per_layer = at_0p9 - recip + cross
    return dict(recip_lat_1p2=recip, recip_lat_in_1p2_cycles_at_0p9=at_0p9, crossing_cycles=cross,
                per_layer_cycles=per_layer, per_token_cycles=per_layer * pr['shape']['layers'],
                share_of_token=round(per_layer * pr['shape']['layers'] / pr['r2']['primary']['token_cycles'], 5))


def latency_deltas(rt, pr):
    """physical terms this floorplan adds to (or that are absent from) the selected 229,158-cycle token"""
    L = pr['shape']['layers']
    tok = pr['r2']['primary']['token_cycles']
    fb = recip_fallback(pr)
    rows = [
        ('hub<->farthest row-engine stages vs the model 45', rt['hub_to_stack']['per_token_cycle_delta'], 'included'),
        ('mesochronous FIFO at the strip end, 2 cycles each way (assumed)', 2 * 2 * L, 'included'),
        ('PHY pins -> farthest row-engine at each K/V phase start', 2 * rt['phy_pins_to_farthest_row_engine']['stages'] * L,
         'conditional: zero if the phase start is prefetched'),
        ('1/Z on the 0.9 GHz SFU if recip does not close at SS 1.2 GHz', fb['per_token_cycles'], 'conditional'),
        ('hub<->IO edge, 2 all-reduces x 2 directions per layer', 2 * 2 * rt['hub_to_io_edge']['stages_1p2GHz'] * L,
         'conditional: only if the measured collective LAT does not already carry it (all-reduce stream owns it)'),
    ]
    out = [dict(term=t, cycles_per_token=c, share_of_token=round(c / tok, 5), status=s) for t, c, s in rows]
    inc = sum(r['cycles_per_token'] for r in out if r['status'] == 'included')
    allc = sum(r['cycles_per_token'] for r in out)
    return dict(rows=out, included_cycles=inc, included_token_us=round((tok + inc) / 1.2e9 * 1e6, 3),
                worst_case_cycles=allc, worst_case_token_us=round((tok + allc) / 1.2e9 * 1e6, 3),
                selected_token_cycles=tok)


def power(fr, pr, cool, re_el, rt):
    """time-averaged (thermal) and in-phase peak (IR) power density of the shoreline regions at the selected rate"""
    sel_tok_s = pr['r2']['primary']['tokens_s']
    tok_cycles = pr['r2']['primary']['token_cycles']
    active = 2 * pr['latency']['cases']['primary']['per_layer_cycles']['K_phase'] * pr['shape']['layers'] / tok_cycles
    kv_B = 150976512                                           # selected identity kv_offchip_read_B_per_die_token
    c = cool['constants']
    pj_bit = dict(unqualified_die_share=10.19, io_only=0.8, gh200_die_share=8.23)  # cooling recheck sensitivities
    mac_pj = dict(A=3.974, B=0.59)                             # cooling recheck mac_A / mac_B
    leak, clk = 0.10, 8.5e-11 * 1.2e9                          # technology.json logic leakage, clock J/mm2/cycle
    strip_mm2 = re_el['frame_area_um2'] * re_el['per_stack'] / 1e6
    phy_mm2 = fr['shoreline']['phy_um'][0] * fr['shoreline']['phy_um'][1] / 1e6
    macs_tok = pr['shape']['attention_MACs_per_token_per_die'] / STACKS
    out = {}
    for sc, e in mac_pj.items():
        mac_avg = macs_tok * e * 1e-12 * sel_tok_s
        mac_peak = re_el['lanes'] * re_el['per_stack'] * 1.2e9 * e * 1e-12
        static = strip_mm2 * (leak + clk)                       # clock ungated upper bound in phase
        strip_avg = (mac_avg + strip_mm2 * leak + strip_mm2 * clk * active) / strip_mm2
        strip_peak = (mac_peak + static) / strip_mm2
        phy = {k: dict(avg=kv_B * 8 * v * 1e-12 * sel_tok_s / STACKS / phy_mm2,
                       peak=pr['rates_per_stack']['HBM_sustained_Bps'] * 8 * v * 1e-12 / phy_mm2)
               for k, v in pj_bit.items()}
        out[sc] = dict(strip_w_per_mm2=dict(avg=round(strip_avg, 3), peak_in_phase=round(strip_peak, 3)),
                       phy_w_per_mm2={k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in phy.items()},
                       band_avg_w_per_mm2=round((strip_avg * strip_mm2 + phy['unqualified_die_share']['avg'] * phy_mm2)
                                                / (strip_mm2 + phy_mm2), 3))
    cfg = load(P['power'])
    ref = cfg['cooling']
    die_w_ref, stacks_w_ref = PS.reference_die_w(cfg, ref['references']['h200_sxm'])
    dyn = {s: cool['baseline'][k]['dynamic_mJ_per_token'] - cool['baseline'][k]['dynamic_mJ_parts']['kv_ring_sram_and_delivery']
           for s, k in (('A', 'A_measured_implementation'), ('B', 'B_proposed_production'))}
    die_w = {s: round(cool['baseline']['A_measured_implementation']['static_w'] + d * 1e-3 * sel_tok_s, 1) for s, d in dyn.items()}
    # IR: v41_die_assembly closed form on this die's grid, at the in-phase peak of the strip and the PHY
    rc = VA.asap7_layer_rc()
    rho = sum(rc[k][0] * 1e3 * 0.040 for k in ('M8', 'M9')) / 2
    cov = 1.0 / 40.0
    r_eff = rho / cov
    V = VA.CONST['vdd_v']['value']
    p = VA.CONST['bump_pitch_um']['value'] / math.sqrt(VA.CONST['power_bump_fraction']['value'])
    Rc = p / math.sqrt(math.pi)
    a = VA.CONST['bump_contact_radius_um']['value']
    geom = Rc ** 2 * math.log(Rc / a) - (Rc ** 2 - a ** 2) / 2
    budget = VA.CONST['ir_budget_fraction']['value'] * V
    ir = {}
    for sc in out:
        for region, wpm in (('strip_peak', out[sc]['strip_w_per_mm2']['peak_in_phase']),
                            ('phy_peak_unqualified', out[sc]['phy_w_per_mm2']['unqualified_die_share']['peak'])):
            J = wpm / V * 1e-6
            dv = J * r_eff / 2 * geom * 2
            ir[f'{sc}_{region}'] = dict(w_per_mm2=wpm, drop_mv=round(dv * 1e3, 1), budget_mv=round(budget * 1e3, 1),
                                        within=dv <= budget, m8m9_coverage_needed=round(cov * dv / budget, 4))
    return dict(rate_tokens_s=sel_tok_s, stream_active_fraction=round(active, 4), strip_mm2_per_stack=round(strip_mm2, 3),
                phy_mm2=round(phy_mm2, 3), scenarios=out,
                sourced_hotspot_limit=None,
                hotspot_limit_flag=ref['hot_spot']['source'],
                reference_die_average_w_per_mm2=dict(
                    h200=round(die_w_ref / ref['references']['h200_sxm']['die_mm2'], 3),
                    basis='tools/power_scenarios.reference_die_w: H200 SXM 700 W less its 6 stacks at peak x stack_high, '
                          'over the 814 mm2 GH100 die: a die AVERAGE of a shipping part, not a hot-spot limit'),
                die_power_w_at_rate=dict(values=die_w, limit_liquid=474.56, limit_air=374.56,
                                         limit_source=c['cooling_liquid_die_w_474.56']['cite'], basis='cooling recheck P = static + E_dyn x r, with the KV ring '
                                         'SRAM/delivery term removed (fill gone); HBM path energy kept'),
                pdn=dict(upper_metal_signal_share=SIGNAL_SHARE, pdn_share_of_channels=1 - SIGNAL_SHARE,
                         die_grid=f"{P['pdn']} M8/M9 1.0 um stripes at 40 um: {cov:.3f} of each layer per net",
                         ir=ir, model='v41_die_assembly.ir_drop closed form (uniform sheet, VDD bump array), ASAP7 M8/M9 RC'))


def elements(re_el, hub_el, fr, pr, mac, pin):
    rules = {m['macro']: m for m in pin['catalog']}
    sram = rules[SCORE_MACRO]
    ff_bits = pr['boundaries']['tracks_per_stack_link']
    station_cells = ff_bits * FF_UM2
    station_h = snap_up(station_cells / CELL_UTIL_TARGET / fr['link_channels']['horizontal_um'], SNAP_Y)
    fifo_cells = 2 * ff_bits * LINK_FIFO_DEPTH * FF_UM2 * 1.1
    fifo_h = snap_up(fifo_cells / 0.6 / fr['link_channels']['horizontal_um'], SNAP_Y)
    uc = pr['unit_closure']
    tile = fr['tile_slot']
    return [
        dict(order=1, name='near-HBM row-engine', replicas_per_die=STACKS * re_el['per_stack'], domain='stream 1.2 GHz',
             frame_um=re_el['frame_um'], frame_area_mm2=round(re_el['frame_area_um2'] / 1e6, 4),
             orientation='R0 (element LEF R0-only, origin on 0.432 x 2.16)',
             macros=[dict(name=SCORE_MACRO, count=1, orientations_allowed=['R0', 'MY'],
                          origin_rule_mod_48nm=sram['origin_rule_mod_track_nm'],
                          note='H mod 0.048 = 6 nm: MX/R180 need origin = 18 nm; restrict to R0/MY at 0 mod 48 nm (audit fix c); W = 0.024 mod 0.048 already')],
             contents=f"{re_el['lanes']} BF16 MAC lanes, 128-wide score tree (LAT-7 adders), P.V accumulators interleaving >= 7 chunks, "
                      f"{re_el['exp_pipes']} exp pipes, s-max and Z-chunk adders, q stationary, 1 score SRAM",
             util_target=dict(cell_util_max=CELL_UTIL_TARGET, frame_fill_at_routed_constants_hi=re_el['fill_hi'],
                              frame_fill_lo=re_el['fill_lo'],
                              note='frame sized at the routed-unit constants (hi); synthesis sets the cell area and '
                                   'CORE_UTILIZATION must stay <= 0.70'),
             binding_risk=dict(kind='timing', units_not_closed_at_SS_1p2GHz=[
                 f"BF16 MAC pipe {uc['mac_bf16_um2']['fmax_mhz']} MHz (closed only there)",
                 f"exp {uc['exp_um2']['fmax_mhz']} MHz not closed", f"fp32_mul {uc['fp32_mul_um2']['fmax_mhz']} MHz not closed",
                 f"score SRAM SS clk->q {pr['area_mm2']['SRAM_macro']['ss_clk_to_q_ps']} ps of 833"],
                 rule='pipeline to close at SS/FF 60/25; every added stage reported to the model (score_latency, EXP_LAT)')),
        dict(order=2, name='hub element (near-HBM hub combine + hub-side link endpoints + X3 staging)', replicas_per_die=1,
             domain='stream 1.2 GHz (X3 async FIFO input from 0.9 GHz SU)', frame_um=hub_el['frame_um'],
             frame_area_mm2=round(hub_el['frame_um'][0] * hub_el['frame_um'][1] / 1e6, 4),
             placement='hub spine centre, between the vertical link channel and the SU/tree-top blocks',
             contents='P.V tree levels 8-9, Z tree levels 5-10, reciprocal (seed + 3 Newton), 8 FP32 multiplies, '
                      'per-head max compare/broadcast, 4 link endpoints (FIFO depth 8), q/new-kv staging',
             parts_um2=hub_el['parts_um2'],
             util_target=dict(cell_util=hub_el['util_at_routed_constants'], cell_util_max=CELL_UTIL_TARGET),
             binding_risk=dict(kind='timing', units_not_closed_at_SS_1p2GHz=[
                 f"recip {uc['recip_um2']['fmax_mhz']} MHz not closed", f"fp32_mul {uc['fp32_mul_um2']['fmax_mhz']} MHz not closed"],
                 fallback='1/Z on the 0.9 GHz SFU across X1 (priced in recip_fallback)')),
        dict(order=3, name='link endpoint (pipeline station + strip-side mesochronous FIFO)', domain='stream 1.2 GHz',
             replicas_per_die=dict(stations=STACKS * routes_cache['hub_to_stack']['total_stages'], strip_fifos=STACKS),
             station_frame_um=[fr['link_channels']['horizontal_um'], station_h],
             station_bits=ff_bits, station_cell_um2=round(station_cells), station_util=round(station_cells / (fr['link_channels']['horizontal_um'] * station_h), 3),
             fifo_frame_um=[fr['link_channels']['horizontal_um'], fifo_h], fifo_cell_um2=round(fifo_cells),
             span_um=U.SS_REACH_UM[1.2e9],
             binding_risk=dict(kind='timing', test='station-to-station 504 um span of a 1,056-bit bus at SS setup / FF hold 60/25 '
                               '(W15 measured the reach on 547-bit spans); FIFO pointer sync across the two local trees')),
        dict(order=4, name='tile re-frame (existing W12 tile, KV slice and fill port removed)', replicas_per_die=TILE_COLS * TILE_ROWS,
             domain='stream 1.2 GHz', frame_um=[tile['w_um'], tile['h_um']], corridor_um=tile['corridor_um'],
             util_target=dict(cell_util=TILE_LOGIC_UTIL, cell_ceiling_um2=CELL_CEILING_UM2,
                              cell_capacity_um2=tile['cell_capacity_at_util_um2']),
             macros=[dict(name=ROM_MACRO, count=ROMS_PER_TILE, mx_r180_origin_y_mod_2p16_um=0.81,
                          origin_rule_mod_48nm=rules[ROM_MACRO]['origin_rule_mod_track_nm'])],
             binding_risk=dict(kind='timing', note='the current tile is FAIL_NOMINAL_CLOCK_BALANCE (parent context r7); the '
                               're-frame is required by the selected frame and inherits the open tile campaigns')),
    ]


routes_cache = {}


def area_ledger(fr, re_el, hub_el, pr, users, mac, cur):
    tiles = TILE_COLS * TILE_ROWS
    W, H = fr['die_um']
    tile_mm2 = tiles * fr['tile_slot']['area_um2'] / 1e6
    phy_mm2 = STACKS * fr['shoreline']['phy_um'][0] * fr['shoreline']['phy_um'][1] / 1e6
    ctrl_mm2 = STACKS * fr['shoreline']['controller_band_um'] * fr['shoreline']['phy_um'][1] / 1e6
    strip_mm2 = STACKS * re_el['per_stack'] * re_el['frame_area_um2'] / 1e6
    chan_mm2 = 2 * fr['link_channels']['horizontal_um'] * fr['array_um'][0] / 1e6
    spine_mm2 = fr['spine']['mm2']
    io_band_mm2 = (W if fr['io']['edge'] == 'north' else H) * fr['io']['band_depth_um'] / 1e6
    band = fr['shoreline']['band_depth_um']
    shore_free_mm2 = 2 * band * (fr['shoreline']['edge_len_um'] - 2 * fr['shoreline']['phy_um'][1]) / 1e6
    io_used_mm2 = fr['io']['ucie_mm2'] + fr['io']['board_serdes_reservation_mm2'] + fr['io']['hosted_mm2']
    placed = tile_mm2 + phy_mm2 + ctrl_mm2 + strip_mm2 + chan_mm2 + spine_mm2 + io_band_mm2 + shore_free_mm2
    die = W * H / 1e6
    kv_macro = users['per_die'] * mac[KV_MACRO]['area_um2'] / 1e6 if users['credit_valid'] else 0.0
    cur_tile = tiles * cur['area_um2'] / 1e6
    f = pr['area_mm2']['freed']
    return dict(
        die_mm2=round(die, 2), budget_mm2=DIE_BUDGET_MM2, legal_field_mm2=RETICLE_UM[0] * RETICLE_UM[1] / 1e6,
        rows=dict(tile_field=round(tile_mm2, 2), hub_spine=round(spine_mm2, 2), hbm_phys=round(phy_mm2, 2),
                  hbm_controller_bands=round(ctrl_mm2, 2), near_hbm_strips=round(strip_mm2, 2),
                  link_channels=round(chan_mm2, 2), io_band=round(io_band_mm2, 2),
                  shoreline_free_segments=round(shore_free_mm2, 2), edge_keep_and_snap=round(die - placed, 2)),
        io_band_used_mm2=round(io_used_mm2, 2), io_band_spare_mm2=round(io_band_mm2 - io_used_mm2, 2),
        unallocated_mm2=round(shore_free_mm2 + io_band_mm2 - io_used_mm2, 2),
        over_815_budget_mm2=round(die - DIE_BUDGET_MM2, 2),
        hub_spine_contents_mm2=fr['spine']['hub_contents_mm2'],
        near_hbm_added=dict(strips_mm2=round(strip_mm2, 2), hub_element_mm2=round(hub_el['area_um2'] / 1e6, 3),
                            extra_score_macros_mm2=re_el['extra_score_macro_mm2_per_die'],
                            link_station_FF_mm2=round(STACKS * routes_cache['hub_to_stack']['total_stages'] *
                                                      pr['boundaries']['tracks_per_stack_link'] * FF_UM2 / 1e6, 4),
                            pricing_die_added_mm2=[pr['area_mm2']['die_added_lo'], pr['area_mm2']['die_added_hi']]),
        removed=dict(
            tile_KV_macros=dict(count=users['per_die'], macro_mm2=round(kv_macro, 3),
                                packed_mm2=round(kv_macro * U.QWEN_AREA['macro_pack'], 3),
                                pricing_figure_mm2=f['tile_KV_macros_conditional'],
                                verified_no_other_user=users['credit_valid'],
                                note='halved against the pricing: 2 per tile, not 1 per group'),
            tile_field_shrink_mm2=round(cur_tile - tile_mm2, 2),
            fill_corridor_tracks=pr['boundaries']['fill_control_tracks_removed'],
            fill_assembly_credit_service=dict(upper_bound_mm2=f['KV_service_known_upper_bound'],
                                              lower_bound_mm2=f['assembly_pools_lower_bound'],
                                              kept='per-PC request/return RAM, refresh, scheduling with one in-order local '
                                                   'consumer: charged here as the controller band: the whole 19.22 mm2 upper bound kept, no credit'),
            not_placed_in_this_frame=['global 7-lane fill network and its 1,536 destinations', '136/17 cohort credits',
                                      '56 x 85 assembly pools and owned DATA_GRANT', 'reverse grants, per-tile write ports '
                                      'and KV landing', 'tile KV slice (2 macros) and kvw_* port']),
        current_tile_field_mm2=round(cur_tile, 2))


def svg(fr, rt, re_el):
    W, H = fr['die_um']
    s = 0.03
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" font-size="9" font-family="sans-serif">',
           f'<rect x="0" y="0" width="{W * s:.1f}" height="{H * s:.1f}" fill="#fafafa" stroke="#000"/>']

    def rect(x, y, w, h, fill, label=''):
        out.append(f'<rect x="{x * s:.1f}" y="{(H - y - h) * s:.1f}" width="{w * s:.1f}" height="{h * s:.1f}" '
                   f'fill="{fill}" stroke="#333" stroke-width="0.4"/>')
        if label:
            out.append(f'<text x="{(x + 80) * s:.1f}" y="{(H - y - h / 2) * s:.1f}">{label}</text>')
    x0, y0 = fr['core_origin_um']
    aw, ah = fr['array_um']
    sw = fr['spine']['w_um']
    rect(x0, y0, aw / 2, ah, '#dde8f5', 'tiles W (32 x 24)')
    rect(x0 + aw / 2, y0, sw, ah, '#f5e3c8', 'hub')
    rect(x0 + aw / 2 + sw, y0, aw / 2, ah, '#dde8f5', 'tiles E')
    hub_x, hub_y = rt['hub_xy_um']
    hc = fr['link_channels']['horizontal_um']
    for (sx, sy) in rt['stack_centres_um']:
        rect(x0, sy - hc / 2, aw + sw, hc, '#c23b22')
        phy_h, phy_w = fr['shoreline']['phy_um']
        band = fr['shoreline']['band_depth_um']
        bx = EDGE_KEEP if sx < W / 2 else W - EDGE_KEEP - band
        rect(bx, sy - phy_w / 2, band, phy_w, '#9fd39f', 'PHY+ctl+strip')
    rect(x0 + aw / 2 + sw / 2 - fr['link_channels']['vertical_um'] / 2, rt['stack_centres_um'][0][1],
         fr['link_channels']['vertical_um'], rt['stack_centres_um'][1][1] - rt['stack_centres_um'][0][1], '#c23b22')
    if fr['io']['edge'] == 'north':
        rect(EDGE_KEEP, y0 + ah, W - 2 * EDGE_KEEP, fr['io']['band_depth_um'], '#e0d0f0', 'UCIe + board IO')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def build():
    pr, sel, cool = load(P['pricing']), load(P['selected']), load(P['cooling'])
    cat = load(P['catalog'])['macros']
    phy, pin, w5 = load(P['phy']), load(P['pin_audit']), load(P['w5'])
    users = kv_macro_users()
    re_el = row_engine(pr, cat)
    hub_el = hub_element(pr)
    hub_rows = hub_reservation(w5, pr)
    svc_mm2 = load(P['credit17'])['cells']['total_known_service_mm2']
    frames = [frame(v, e, cat, pr, phy, hub_rows, hub_el, re_el, svc_mm2) for v in ('A', 'B1', 'B2') for e in ('EW', 'NS')]
    chosen = next((f for f in frames if f['legal'] and f['hbm_edges'] == 'EW' and f['within_815_budget']),
                  next((f for f in frames if f['legal']), None))
    if chosen is None:
        raise SystemExit('no legal frame')
    rt = routes(chosen, pr, re_el)
    routes_cache.clear()
    routes_cache.update(rt)
    cur = tile_slot('A', cat)
    rec = dict(
        schema=SCHEMA, status='MODEL_ONLY_FLOORPLAN_PLAN', rtl=False, pnr=False, adoption=False,
        selected_entry=dict(record=P['selected'], status=sel['status'], token_us=sel['headline']['token_us'],
                            tokens_s=sel['headline']['tokens_per_s']),
        frames=[{k: v for k, v in f.items() if k not in ('tile_slot',)} | dict(tile_slot_um=[f['tile_slot']['w_um'], f['tile_slot']['h_um']],
                tile_corridor_um=f['tile_slot']['corridor_um'], tile_corridor_fits=f['tile_slot']['corridor']['fits'])
                for f in frames],
        selected_frame=chosen['variant'] + '-' + chosen['hbm_edges'],
        floorplan=chosen,
        hbm_phy_orientation=dict(
            issue='ot_hbm3e_phy has 9,209 M5 (vertical) pins on its top edge; the audit gives legal origins only for '
                  'R0/MX/MY/R180. On an east/west shoreline the core-facing edge is vertical, where M5 pins cannot be '
                  'reached in-plane; R90 is not a legal orientation of this abstract',
            required='a vertical-shoreline PHY abstract variant (tools/mem_compiler/hbm_phy_gen.py) with M4/M6 pins '
                     'on the core-facing edge, H/W chosen so pins stay on track (H = 0.024 mod 0.048 rule); a new '
                     'macro version, not an edit; zero area change',
            source=P['pin_audit']),
        routes=rt, cdc=cdc_plan(chosen, rt), recip_fallback=recip_fallback(pr),
        latency_deltas_vs_selected=latency_deltas(rt, pr),
        clock_domains=dict(
            stream_1p2GHz=['tile field (1,536 tiles)', 'near-HBM strips (24 row-engines)', 'hub element (hub combine, '
                           'link endpoints)', 'link stations and channels', 'HBM controller bands', 'ME top / x-root / tree top'],
            serial_0p9GHz=['SU64 + SFU', 'vector memory side of the hub CDC', 'collective reducers (owned by the '
                           'all-reduce stream)'],
            reach_um_per_stage={'1.2GHz': U.SS_REACH_UM[1.2e9], '0.9GHz': U.SS_REACH_UM[0.9e9]},
            policy='AGENTS.md clock domains (root 2026-09-30); SS 60 ps setup / FF 25 ps hold, never relaxed'),
        tile_kv_macro_users=users,
        row_engine=re_el, hub_element=hub_el, hub_spine_reservation=hub_rows,
        area=area_ledger(chosen, re_el, hub_el, pr, users, cat, cur),
        power=power(chosen, pr, cool, re_el, rt),
        hardened_elements=elements(re_el, hub_el, chosen, pr, cat, pin),
        open_items=[
            'HBM sustained 0.9 TB/s per stack and LEN>=5 controller accept (pricing section 7): unchanged binders',
            'hub spine contents are W5 (TP2) blocks carried to TP4: a TP4 hub synthesis replaces them',
            'board SerDes reservation (10 lanes x 0.4 mm2) and UCIe 10 mm2 are assumed',
            'no sourced hot-spot W/mm2 limit (configs/hardware/power_scenarios.json hot_spot: none found): flagged',
            'hub->IO edge distance enters the all-reduce: reconcile with the one-segment all-reduce stream',
            'PHY pins->farthest row-engine stages are not in the selected 1,700-cycle attention unless prefetched',
            'vertical-shoreline PHY abstract variant required before any die-level placement'],
        sources_sha256={v: sha(v) for v in P.values()},
        tool_sha256=sha('tools/qwen_rom_floorplan_nearhbm.py'),
        claim_boundary='Model and floorplan plan only. No routed die, no timing, no measured power; predictive ASAP7 '
                       'abstracts; every reservation is named as such.')
    return rec, svg(chosen, rt, re_el)


def write(out_dir: Path):
    rec, pic = build()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / RECORD).write_text(json.dumps(rec, indent=1, sort_keys=False) + '\n')
    (out_dir / SVG).write_text(pic)
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out-dir', type=Path)
    ap.add_argument('--verify', action='store_true', help='regenerate into a temp dir and require byte identity')
    a = ap.parse_args()
    if a.verify:
        with tempfile.TemporaryDirectory() as t:
            write(Path(t))
            bad = [n for n in (RECORD, SVG) if not filecmp.cmp(Path(t) / n, OUT / n, shallow=False)]
        if bad:
            raise SystemExit(f'verify FAILED: {bad} differ')
        print('verify OK: model-r1.json and floorplan-r1.svg byte-identical')
        return
    rec = write(a.out_dir or OUT)
    f = rec['floorplan']
    print(f"frame {rec['selected_frame']}: die {f['die_um'][0]:.0f} x {f['die_um'][1]:.0f} um = {f['die_mm2']} mm2; "
          f"hub->stack {rec['routes']['hub_to_stack']['total_stages']} stages")


if __name__ == '__main__':
    main()
