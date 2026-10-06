#!/usr/bin/env python3
"""Qwen3-8B ROM full-die physical composition (near-HBM r2 frame) and die-level feasibility cases.

Floorplan -> hardened element -> replicate (AGENTS.md design method 2).  The die is composed from black-box
abstracts of every hardened element, placed on the r2 floorplan (results/uarch/qwen_rom_floorplan_nearhbm_20261003/
model-r2.json, selected variant kv_kept_plus_ambiguous) and connected by the die-level nets only:

  tile field   64 x 24 W12 ROM tiles (re-framed, KV slice and fill port removed), 260.928 x 1,291.68 um bodies
               with a 52.704 um tile-column corridor on the east side of each tile
  corridors    one station per tile hop at the tile's pin row (637 tracks: clock 64, reset 64, instruction 379,
               go 1, x 128, ready 1), fed from a column head at the array mid-line; the heads are chained
               over the tile rows from the spine's x root (west chain, east chain)
  ME tree      W12 split tree: blocks of 4 x 4 tiles (TCUT = SMIN = 6), 15 in-block nodes hosted by tiles
               (t_out / n_a / n_b / n_y, 512 b), 96 block words (512 b) into the spine
  hub spine    1,214.784 um (r2) between the west and east half arrays: W5/TP4 reservation slabs, the hub
               element (near-HBM combine, link endpoints, X3 staging) at the mid-line beside a 174.096 um
               vertical link channel; horizontal link channels (96.768 um) at the two stack-centre heights
  shoreline    E/W: v2 east/west HBM3E PHY (833.496 x 12,000.12, M4 pins on its core face), controller band
               (247.536 um), near-HBM strip (328.32 um) with six row engines (328.32 x 1,998) and the
               strip-end link FIFO (mesochronous M1-M4) at the stack centre
  IO band      north edge, 1,563.84 um deep: collective, embedding ROM, UCIe, board SerDes

Modes
  plan                         floorplan record (every instance, region, corridor, PG region, clock domain,
                               crossing) + SVG + floorplan.def + domains.sdc + pdn.tcl
  real   --work W              case (a): real ASAP7 technology, every abstract with real pins on its facing
                               edges, placement through the orientation-aware snap library, on-track assert,
                               overlap/legality check, pin_access
  grt    --work W --k K        case (b): bundled-technology global route of every die-level net
                               (tools/chip_assembly/v41_die.py method: pitch x k, ceil(bits/k) nets per bus)
  ir     --work W --window N   case (c): OpenROAD PSM on a die window, M8/M9 straps at the region coverages,
                               region power densities, bump array
  clock                        case (d): top-level clock trunk / H-tree insertion and skew estimate
  record --case a|b|c --work W --out R
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

R2 = 'results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json'
R1 = 'results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r1.json'
PHY_EW = 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy.lef'
SNAP_LIB = 'physical/common/ot_macro_track_snap.tcl'
OUT = 'results/rtl/qwen_rom_fulldie_20261003'
PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'

GX, GY = 0.432, 2.16           # macro origin lattice (site 0.054 x 8, row 0.270 x 8; both multiples of 0.048)
EDGE = 20.0
SHAVE = 0.024                  # frame -> abstract: W, H = frame - 0.024 (= 0.024 mod 0.048: mirror-legal on M4/M5)
COLS, ROWS = 64, 24
TILE_SLOT = (313.632, 1291.68)
CORR = 52.704
TILE_BODY_W = TILE_SLOT[0] - CORR
HCH, VCH = 97.2, 174.096       # link channels: r2 96.768 rounded UP to the 2.16 um row lattice (45 x 2.16); spine 174.096
SPINE_W_R2 = 1214.784
PHY_DEPTH = 833.76             # 833.496 snapped up to GX
CTRL_W, STRIP_W = 247.536, 328.32
RE_H = 1998.0
FIFO = (96.768, 136.08)
IO_DEPTH = 1563.84
STATION = (CORR, 69.12)        # corridor station / column-head frame
LST_V = (VCH, 34.56)
LST_H = (34.56, HCH)
HUB_EL = 412.56
# r17 STREAM4 clock crossing: None (default) keeps the b3r16 shoreline.  Otherwise dict(w=, h=, per_stack=32,
# hbm_bits=, core_bits=): one routed per-PC CDC element (rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv) frame per HBM
# pseudo-channel in a column between the controller and the strip; the controller -> row-engine read bus is carried
# through them (controller -> CDC HCLK side, CDC core side -> the row engine serving that PC).
CDC = None
STRIP_SPAN = False             # r17d: strip/CDC/controller PG regions per stack span instead of the full column
# r18 (die-top lint Q1-Q15, main 694e21a6e): near-HBM attention DROPPED (no row engines, no hub combine); the strip
# column keeps one KV landing concentrator per stack (qfd_kvc, stack span tall, KVC_W wide: the strip-end link
# endpoint grown to take the 32 CDC core sides and the KV-new write; kept under the lfifo_<stack> name); an IO-band
# CDC slot (io_xfifo, IOX_W long) beside the collective; the PHY clk / rst_n leave the dfi bundle
R18 = False
# r19 (KV reconciliation, main e1701384d): tiles KEEP their KV slice (2 x ot_sram_1r1w_128x256_m1_r2c2 = 8 KiB a
# tile, 12 MiB a die) and take the landing words over a per-tile-row landing fabric (KVL_BITS a row, one registered
# hop a tile) from each stack's landing crossbar (the qfd_kvc frame, re-sorting the 32 PC landing words of its stack
# to the rows it serves); the tile slot widens so the full tile's mapped-cell ceiling still fits (KV_TILE_W)
R19 = False
KVL_BITS = 768                 # a row's landing bits a cycle: 24 rows x 768 >= 64 PCs x 283 a half array
KV_TILE_W = 319.68             # (125,000 / 0.5 + 10 ROM + 2 KV macros + 10,000 halo) / 1291.68 + corridor, on 0.432
KV_MACRO = 'ot_sram_1r1w_128x256_m1_r2c2'
# r20d: GRT M9 adjustment over the corridors (None: the base adjustment).  r20b i5: corridor M9 carries only tree-word
# vertical legs (the corridor chain is on M7, ~0.55 m a corridor) and all residual M9 overflow sits there
CORR_M9_ADJ = None
CDC_HO = 319                   # h_cred 3 + h_wv 1 + h_wsec 24 + h_cv 1 + h_csec 24 + h_cdata 256 + h_ctag 9 + h_fault 1
CDC_CO = 283                   # l_v 1 + l_sec 17 + l_row 8 + l_data 256 + l_pop 1 (l_* = the element's W face)
KVC_W = 96.768
IOX_W = 400.032
IOX_GAP = 40.176                # r18e: routing gap each side of io_xfifo (r18c i5: M4-M9 1.18-1.41 at 4.3 um gaps)
CORRIDOR_BITS = 637            # clock 64 + reset 64 + instruction 379 + go 1 + x 128 + ready 1
TAP_BITS = 511                 # instruction 379 + go 1 + x 128 + ready 1 + clock 1 + reset 1
TREE_BITS = 512                # W12 tile n_y / t_out word (16 x 32)
LINK_TRACKS = 1056             # 512 each way + 32 control (pricing boundaries.tracks_per_stack_link)
RE_READ_BITS = 1088            # per row engine HBM read port: 1,024 data + 64 command/valid (ASSUMED)
KVNEW_BITS = 128               # new-token K/V write, FIFO -> controller (ASSUMED)
IO_BITS = 512
CLK_TRUNK_TRACKS = 3           # shielded trunk (r2 cts.global_htree.tracks)
BLOCK = (4, 4)                 # tiles per tree block (cols, rows): 16 = 2^(TCUT-2)
LINK_STAGE_UM = 430.56         # corridor gate verdict (claude/qwen-corridor-gate @ 89e70dd78): 504 um link spans miss SS
                               # setup by 29-79 ps; 430.56 um tile-column segments close (+11.9 ps): stage pitch <= 430.56
LINK_WAYPOINT_UM = 4 * LINK_STAGE_UM   # one modelled waypoint per 4 registered stages
REGION_PG = dict(tile_field=0.0439, corridor=0.0439, channel=0.0439, hub=0.025, strip=0.1639, ctrl=0.1639,
                 io=0.025, phy=0.0)
REGION_W_PER_MM2 = dict(tile_field=1.05, corridor=1.05, channel=1.05, hub=0.385, strip=3.924, ctrl=3.924,
                        io=0.385, phy=0.36)
VIA_OBS = 0.05                 # r2 netted rule: 5 % via/OBS
ORFS_LOW_ADJ = 0.25            # ORFS asap7 ROUTING_LAYER_ADJUSTMENT


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def up(v, q):
    return round(math.ceil(v / q - 1e-9) * q, 6)


def dn(v, q):
    return round(math.floor(v / q + 1e-9) * q, 6)


def r2():
    return json.loads((ROOT / R2).read_text())


# ------------------------------------------------------------------------------------------------ geometry
class Inst:
    __slots__ = ('name', 'master', 'x', 'y', 'w', 'h', 'orient', 'kind', 'region', 'domain')

    def __init__(self, name, master, x, y, w, h, orient='R0', kind='', region='', domain='stream_1p2'):
        self.name, self.master, self.x, self.y, self.w, self.h = name, master, x, y, w, h
        self.orient, self.kind, self.region, self.domain = orient, kind, region, domain

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def d(self):
        return dict(name=self.name, master=self.master, x=round(self.x, 3), y=round(self.y, 3), w=round(self.w, 3),
                    h=round(self.h, 3), orient=self.orient, kind=self.kind, region=self.region, domain=self.domain)


SPINE_BLOCKS = [  # name, mm2, domain, source (r1 hub_spine_reservation)
    ('port_tiles', 11.08, 'stream_1p2', 'W5 spine_port_tiles (96 port groups)'),
    ('scale_rom', 14.359, 'stream_1p2', 'W5 spine_scale_rom'),
    ('vector_memory', 0.725, 'serial_0p9', 'W5 spine_vm (serial side of X1/X2)'),
    ('constants_sequencer', 2.157, 'stream_1p2', 'W5 constant ROM, program, sequencer'),
    ('su64_sfu', 1.6, 'serial_0p9', 'SU64 + SFU (estimated)'),
    ('tree_top', 2.397, 'stream_1p2', 'W5 split-tree top registers and result compaction'),
]
IO_BLOCKS = [  # name, mm2, domain
    ('collective', 3.6, 'serial_0p9'), ('embedding_rom', 11.046, 'stream_1p2'),
    ('ucie', 10.0, 'link_ucie'), ('serdes', 4.0, 'link_serdes')]


def build(spine_w=None, tree_mode='central'):
    """Every instance and region of the die.  Coordinates in um, die origin (0, 0).  Without spine_w: the
    narrowest spine (on the 0.432 um lattice) that packs every reservation slab."""
    if spine_w is not None:
        return _build(spine_w, tree_mode)
    first = _build(None, tree_mode)
    w = first['geo']['spine_w_needed']
    for i in range(40):
        m = _build(round(w + i * GX, 3), tree_mode)
        if m['geo']['spine_unplaced_mm2'] <= 1e-6:
            m['geo']['spine_w_needed'] = round(w + i * GX, 3)
            m['geo']['spine_w_area_bound'] = w
            return m
    raise SystemExit('spine does not pack')


def _build(spine_w, tree_mode):
    m = r2()
    fp = m['floorplan']
    assert (R19 or fp['tile_slot_um'] == list(TILE_SLOT)) and abs(fp['tile_corridor_um'] - CORR) < 1e-9
    notes = []
    # spine: the r2 width carries 32.437 mm2 of content in one 1,040.688 um column; packed here as two columns
    # beside a centred vertical link channel, with the two horizontal link channels crossing it
    content = sum(b[1] for b in SPINE_BLOCKS)
    spine_h = ROWS * TILE_SLOT[1] + 2 * HCH
    need_w = None
    if spine_w is None:
        # two columns, each loses 2 x HCH of height to the crossing channels; the hub element row loses
        # (cw - HUB_EL) x HUB_EL of the column it sits in
        for k in range(0, 400):
            sw = SPINE_W_R2 + k * GX
            cw = (sw - VCH) / 2
            cap = 2 * cw * (spine_h - 2 * HCH) / 1e6 - HUB_EL * HUB_EL / 1e6
            if cap >= content - 1e-6:
                need_w = round(sw, 3)
                break
        spine_w = need_w
    cw = dn((spine_w - VCH) / 2, GX)
    # x layout
    cdc_w = 0.0 if CDC is None else up(CDC['w'] + SHAVE, GX)
    band = PHY_DEPTH + CTRL_W + cdc_w + STRIP_W
    x_wband = up(EDGE, GX)
    x_arr_w = up(x_wband + band, GX)
    x_spine = x_arr_w + 32 * TILE_SLOT[0]
    x_arr_e = up(x_spine + 2 * cw + VCH, GX)
    x_eband = x_arr_e + 32 * TILE_SLOT[0]
    W = up(x_eband + band + EDGE, GX)
    # y layout: 7 rows, channel S, 10 rows, channel N, 7 rows, IO band
    y0 = up(EDGE, GY)
    row_y = []
    y = y0
    ch_y = []
    for r in range(ROWS):
        if r in (7, 17):
            ch_y.append(y)
            y += HCH
        row_y.append(y)
        y += TILE_SLOT[1]
    y_top = y
    mid = row_y[12]
    y_io = y_top
    H = up(y_io + IO_DEPTH + EDGE, GY)
    insts = []
    regions = []
    # ---- tiles, stations, heads
    def col_x(c):
        return x_arr_w + c * TILE_SLOT[0] if c < 32 else x_arr_e + (c - 32) * TILE_SLOT[0]
    for c in range(COLS):
        xc = col_x(c)
        for r in range(ROWS):
            insts.append(Inst(f't_{c}_{r}', 'qfd_tile_e' if (R19 and c >= 32) else 'qfd_tile', xc, row_y[r], TILE_BODY_W - SHAVE, TILE_SLOT[1] - SHAVE,
                              kind='tile', region='tile_field'))
            sy = row_y[r] + dn((TILE_SLOT[1] - STATION[1]) / 2, GY)
            insts.append(Inst(f's_{c}_{r}', 'qfd_cst', xc + TILE_BODY_W, sy, STATION[0] - SHAVE, STATION[1] - SHAVE,
                              kind='station', region='corridor'))
        hy = mid - dn(STATION[1] / 2, GY)
        insts.append(Inst(f'h_{c}', 'qfd_chead', xc + TILE_BODY_W, hy, STATION[0] - SHAVE, STATION[1] - SHAVE,
                          kind='head', region='corridor'))
    # head collides with the stations of rows 11/12?  stations sit at tile mid-height: 611 um away.
    regions.append(dict(name='tile_field_w', kind='tile_field', rect=[x_arr_w, y0, x_spine, y_top]))
    regions.append(dict(name='tile_field_e', kind='tile_field', rect=[x_arr_e, y0, x_eband, y_top]))
    for i, cy in enumerate(ch_y):
        regions.append(dict(name=f'hchan_{"sn"[i]}_w', kind='channel', rect=[x_arr_w, cy, x_spine, cy + HCH]))
        regions.append(dict(name=f'hchan_{"sn"[i]}_e', kind='channel', rect=[x_arr_e, cy, x_eband, cy + HCH]))
    for c in range(COLS):
        xc = col_x(c) + TILE_BODY_W
        regions.append(dict(name=f'corr_{c}', kind='corridor', rect=[xc, y0, xc + CORR, y_top]))
    # ---- spine
    x_vch = x_spine + cw
    regions.append(dict(name='spine', kind='hub', rect=[x_spine, y0, x_arr_e, y_top]))
    regions.append(dict(name='spine_vchan', kind='channel', rect=[x_vch, y0, x_vch + VCH, y_top]))
    hub = Inst('hub_el', 'qfd_hub', x_vch - up(HUB_EL, GX), mid - dn(HUB_EL / 2, GY), up(HUB_EL, GX) - SHAVE,
               dn(HUB_EL, GY) + GY - SHAVE, kind='hub_element', region='hub')
    hub.h = up(HUB_EL, GY) - SHAVE
    insts.append(hub)
    # column segments (between the channel crossings): south [y0, ch0), mid [ch0+HCH, ch1), north [ch1+HCH, top)
    segs = [(y0, ch_y[0]), (ch_y[0] + HCH, ch_y[1]), (ch_y[1] + HCH, y_top)]
    cols = {'W': x_spine, 'E': x_vch + VCH}
    # fill order: mid segment first (central blocks near the hub), then north/south with the reservations
    free = {(cn, si): [s0, s1] for cn in cols for si, (s0, s1) in enumerate(segs)}
    hub_lo, hub_hi = hub.y, hub.y + hub.h + SHAVE
    spine_parts = []

    def put(name, mm2, dom, src, col, seg, at_top=False):
        f = free[(col, seg)]
        h = up(mm2 * 1e6 / cw, GY)
        if f[1] - f[0] < h - 1e-6:
            return None
        if at_top:
            yy = f[1] - h
            f[1] = yy
        else:
            yy = f[0]
            f[0] = yy + h
        it = Inst(f'sp_{name}', f'qfd_sp_{name}', cols[col], yy, cw - SHAVE, h - SHAVE, kind='spine_block',
                  region='hub', domain=dom)
        insts.append(it)
        spine_parts.append(dict(name=name, mm2=mm2, placed_mm2=round(cw * h / 1e6, 4), col=col, seg=seg, src=src))
        return it
    # hub element row in the west column, mid segment: split that column segment around it
    fW = free[('W', 1)]
    below = [fW[0], hub_lo]
    above = [hub_hi, fW[1]]
    free[('W', 1)] = below
    free[('W', '1a')] = above
    segs_order = [('W', 1), ('W', '1a'), ('E', 1), ('W', 0), ('E', 0), ('W', 2), ('E', 2)]
    central = ['vector_memory', 'su64_sfu', 'tree_top', 'constants_sequencer']
    placed_central = {}
    leftovers = 0.0
    for name in central:
        b = next(x for x in SPINE_BLOCKS if x[0] == name)
        for key in segs_order:
            it = put(name, b[1], b[2], b[3], key[0], key[1], at_top=(key[1] == 1))
            if it:
                placed_central[name] = it
                break
        else:
            notes.append(f'spine: {name} does not fit')
    # port tiles and scale ROM: reservation slabs filling the free column segments; port slabs first, in the
    # segments nearest the block-row bands they serve (6 slabs), then scale ROM slabs in what remains
    need = {'port_tiles': next(x for x in SPINE_BLOCKS if x[0] == 'port_tiles'),
            'scale_rom': next(x for x in SPINE_BLOCKS if x[0] == 'scale_rom')}
    remaining = {k_: v[1] for k_, v in need.items()}
    idx = {'port_tiles': 0, 'scale_rom': 0}
    order = [('W', 0), ('E', 0), ('W', 2), ('E', 2), ('E', 1), ('W', 1), ('W', '1a')]
    for name in ('port_tiles', 'scale_rom'):
        per = need[name][1] / 6
        for key in order:
            while remaining[name] > 1e-6:
                f = free[key]
                avail = dn(f[1] - f[0], GY) * cw / 1e6
                if avail < 0.02:
                    break
                take = min(per, remaining[name], avail)
                h = up(take * 1e6 / cw, GY)
                if h > f[1] - f[0] + 1e-6:
                    h = dn(f[1] - f[0], GY)
                    take = h * cw / 1e6
                it = Inst(f'sp_{name}_{idx[name]}', f'qfd_sp_{name}_{idx[name]}', cols[key[0]], f[0], cw - SHAVE,
                          h - SHAVE, kind='spine_block', region='hub', domain=need[name][2])
                f[0] += h
                insts.append(it)
                spine_parts.append(dict(name=f'{name}_{idx[name]}', mm2=round(take, 4), placed_mm2=round(cw * h / 1e6, 4),
                                        col=key[0], seg=key[1], src=need[name][3]))
                idx[name] += 1
                remaining[name] -= take
        if remaining[name] > 1e-3:
            leftovers += remaining[name]
            notes.append(f'spine: {remaining[name]:.3f} mm2 of {name} does not fit')
    # ---- shoreline bands
    stack_cy = [ch_y[0] + HCH / 2, ch_y[1] + HCH / 2]
    bands = {'W': x_wband, 'E': x_eband}
    lfifos, ctrls, renges, phys, cdcs = {}, {}, {}, {}, {}
    for side, xb in bands.items():
        orient = 'MY' if side == 'W' else 'R0'
        if side == 'W':
            x_phy, x_ctrl, x_strip = xb, xb + PHY_DEPTH, xb + PHY_DEPTH + CTRL_W + cdc_w
            x_cdc = xb + PHY_DEPTH + CTRL_W
        else:
            x_strip, x_ctrl, x_phy = xb, xb + STRIP_W + cdc_w, xb + STRIP_W + cdc_w + CTRL_W
            x_cdc = xb + STRIP_W
        if not STRIP_SPAN:
            if CDC is not None:
                regions.append(dict(name=f'cdc_{side}', kind='strip', rect=[x_cdc, y0, x_cdc + cdc_w, y_top]))
            regions.append(dict(name=f'strip_{side}', kind='strip', rect=[x_strip, y0, x_strip + STRIP_W, y_top]))
            regions.append(dict(name=f'ctrl_{side}', kind='ctrl', rect=[x_ctrl, y0, x_ctrl + CTRL_W, y_top]))
        regions.append(dict(name=f'phy_{side}', kind='phy', rect=[x_phy, y0, x_phy + PHY_DEPTH, y_top]))
        for si, scy in enumerate(stack_cy):
            st = f'{side}{"SN"[si]}'
            span = 6 * RE_H + FIFO[1]
            sy0 = dn(scy - span / 2, GY)
            phy_y = sy0 + up((span - 12000.12) / 2, GY)
            if STRIP_SPAN:
                # r17d: the strip / CDC / controller PG and power regions cover the stack span they serve; the
                # empty column ends carry the tile-field lattice (r17b/c i5: M9 1.036 windows in the strip's
                # empty north end, where the 24 % strip coverage halved the M9 capacity next to the array edge)
                if CDC is not None:
                    regions.append(dict(name=f'cdc_{st}', kind='strip', rect=[x_cdc, sy0, x_cdc + cdc_w, sy0 + span]))
                regions.append(dict(name=f'strip_{st}', kind='strip', rect=[x_strip, sy0, x_strip + STRIP_W, sy0 + span]))
                regions.append(dict(name=f'ctrl_{st}', kind='ctrl', rect=[x_ctrl, sy0, x_ctrl + CTRL_W, sy0 + span]))
            phys[st] = Inst(f'phy_{st}', 'ot_hbm3e_phy', x_phy,
                            phy_y, 833.496, 12000.12, orient, kind='phy', region='phy', domain='hbm_976p6')
            insts.append(phys[st])
            ctrls[st] = Inst(f'ctrl_{st}', 'qfd_ctrl', x_ctrl, sy0, CTRL_W - SHAVE, span - SHAVE, orient, kind='ctrl',
                             region='ctrl', domain='hbm_976p6')
            insts.append(ctrls[st])
            if CDC is not None and R18:
                n = CDC['per_stack']
                pitch = dn(span / n, GY)
                cdcs[st] = []
                for p in range(n):
                    cy = sy0 + p * pitch + dn((pitch - CDC['h'] - SHAVE) / 2, GY)
                    it = Inst(f'cdc_{st}_{p}', 'qfd_cdc', x_cdc + (cdc_w - CDC['w'] - SHAVE) / 2, cy, CDC['w'],
                              CDC['h'], orient, kind='cdc', region='strip')
                    it.x = dn(it.x, GX)
                    cdcs[st].append(it)
                    insts.append(it)
            elif CDC is not None:
                n = CDC['per_stack']
                # each CDC frame sits level with the row-engine slot it feeds (PC p -> row engine p*6//n, slot j of
                # 6 on that engine's face), so the controller -> CDC -> row-engine hops are straight M4 runs (r17p:
                # frames at an even stack pitch made every core-side word jog vertically over the column, M7-M9
                # windows 1.08-1.19 at the shoreline)
                if RE_H / 6 < CDC['h'] + SHAVE - 1e-6:
                    raise SystemExit(f'CDC: frame height {CDC["h"]} um exceeds a row-engine slot ({RE_H / 6:.1f} um)')
                cdcs[st] = []
                for p in range(n):
                    k = p * 6 // n
                    j = p - min(q for q in range(n) if q * 6 // n == k)
                    y_re = sy0 + k * RE_H + (FIFO[1] if k >= 3 else 0)
                    cy = dn(y_re + (j + 0.5) * (RE_H - SHAVE) / 6 - CDC['h'] / 2, GY)
                    it = Inst(f'cdc_{st}_{p}', 'qfd_cdc', x_cdc + (cdc_w - CDC['w'] - SHAVE) / 2 if side == 'E' else
                              x_cdc + cdc_w - CDC['w'] - SHAVE - (cdc_w - CDC['w'] - SHAVE) / 2, cy, CDC['w'], CDC['h'],
                              orient, kind='cdc', region='strip')
                    it.x = dn(it.x, GX)
                    cdcs[st].append(it)
                    insts.append(it)
            yy = sy0
            renges[st] = []
            if R18:
                ky0, kh = sy0, span
                if R19:
                    # the landing crossbar spans the 12 tile rows its stack serves (S: rows 0-11, N: rows 12-23)
                    ky0 = row_y[0] if si == 0 else row_y[12]
                    kh = (row_y[11] + TILE_SLOT[1] - row_y[0]) if si == 0 else (y_top - row_y[12])
                lfifos[st] = Inst(f'lfifo_{st}', 'qfd_kvc_n' if (R19 and si == 1) else 'qfd_kvc', x_strip, ky0, STRIP_W - SHAVE, kh - SHAVE, orient,
                                  kind='link_fifo', region='strip')
                insts.append(lfifos[st])
                continue
            for k in range(7):
                if k == 3:
                    fx = x_strip + STRIP_W - FIFO[0] if side == 'W' else x_strip
                    lfifos[st] = Inst(f'lfifo_{st}', 'qfd_lfifo', fx, yy, FIFO[0] - SHAVE, FIFO[1] - SHAVE, orient,
                                      kind='link_fifo', region='strip')
                    insts.append(lfifos[st])
                    yy += FIFO[1]
                    continue
                re_ = Inst(f're_{st}_{len(renges[st])}', 'qfd_reng', x_strip, yy, STRIP_W - SHAVE, RE_H - SHAVE, orient,
                           kind='row_engine', region='strip')
                renges[st].append(re_)
                insts.append(re_)
                yy += RE_H
    # ---- IO band (north): collective centred on the spine, embedding west, UCIe and SerDes east
    io = {}
    xs = {}
    clen = up(3.6e6 / IO_DEPTH, GX)
    xs['collective'] = up(x_spine + (x_arr_e - x_spine) / 2 - clen / 2, GX)
    elen = up(11.046e6 / IO_DEPTH, GX)
    xs['embedding_rom'] = xs['collective'] - elen - 10 * GX
    ulen = up(10.0e6 / IO_DEPTH, GX)
    xs['ucie'] = xs['collective'] + clen + 10 * GX + ((up(IOX_W, GX) + 2 * IOX_GAP - 10 * GX) if R18 else 0)
    slen = up(4.0e6 / IO_DEPTH, GX)
    xs['serdes'] = xs['ucie'] + ulen + 10 * GX
    for (name, mm2, dom), ln in zip(IO_BLOCKS, (clen, elen, ulen, slen)):
        io[name] = Inst(f'io_{name}', f'qfd_io_{name}', xs[name], y_io, ln - SHAVE, IO_DEPTH - SHAVE, kind='io',
                        region='io', domain=dom)
        insts.append(io[name])
    if R18:
        io['xfifo'] = Inst('io_xfifo', 'qfd_io_xfifo', xs['collective'] + clen + IOX_GAP, y_io, up(IOX_W, GX) - SHAVE,
                           IO_DEPTH - SHAVE, kind='xfifo', region='io', domain='cdc')
        insts.append(io['xfifo'])
    regions.append(dict(name='io_band', kind='io', rect=[x_arr_w, y_io, x_eband, y_io + IO_DEPTH]))
    # ---- link waypoints: vertical legs in the spine channel, corner at the channel heights, horizontal
    lst = []
    legs = {}
    for si, scy in enumerate(stack_cy):
        leg = []
        ylo, yhi = (scy, hub.y) if si == 0 else (hub.y + hub.h, scy)
        n = max(0, int((yhi - ylo) // LINK_WAYPOINT_UM))
        for k in range(1, n + 1):
            yy = (yhi - k * LINK_WAYPOINT_UM) if si == 0 else (ylo + k * LINK_WAYPOINT_UM)
            if abs(yy - scy) < LINK_WAYPOINT_UM / 2:
                continue
            it = Inst(f'lv_{"SN"[si]}_{k}', 'qfd_lst_v', x_vch, dn(yy, GY), LST_V[0] - SHAVE, LST_V[1] - SHAVE,
                      kind='link_station', region='hub')
            lst.append(it)
            leg.append(it)
        corner = Inst(f'lc_{"SN"[si]}', 'qfd_lst_c', x_vch, ch_y[si], VCH - SHAVE, HCH - SHAVE,
                      'MX' if si == 0 else 'R0', kind='link_station', region='hub')
        lst.append(corner)
        legs[si] = (leg, corner)
    hwp = {}
    for si in range(2):
        for side in 'WE':
            pts = []
            xa, xb_ = (x_wband + band, x_spine) if side == 'W' else (x_arr_e, x_eband)
            n = int((xb_ - xa) // LINK_WAYPOINT_UM)
            for k in range(1, n + 1):
                xx = (xb_ - k * LINK_WAYPOINT_UM) if side == 'W' else (xa + k * LINK_WAYPOINT_UM - LST_H[0])
                # sit in a corridor (never on a tile body): nearest corridor x
                c = min(range(32) if side == 'W' else range(32, 64), key=lambda c: abs(col_x(c) + TILE_BODY_W - xx))
                # r18: over a tile body, clear of the corridor that crosses the channel there (r18j i5: M9 1.035 at
                # corridor 9 where lh_SW_* sat on the corridor's channel crossing)
                lx = dn(col_x(c) + TILE_BODY_W / 2 - LST_H[0] / 2, GX) if R18 else col_x(c) + TILE_BODY_W + GX * 20
                it = Inst(f'lh_{"SN"[si]}{side}_{k}', 'qfd_lst_h', lx, ch_y[si],
                          LST_H[0] - SHAVE, LST_H[1] - SHAVE, kind='link_station', region='channel')
                lst.append(it)
                pts.append(it)
            hwp[(si, side)] = pts
    insts += lst
    die = dict(w=W, h=H, mm2=round(W * H / 1e6, 3), budget_mm2=815.0, margin_mm2=round(815.0 - W * H / 1e6, 3))
    geo = dict(x_wband=x_wband, x_arr_w=x_arr_w, x_spine=x_spine, spine_w=round(x_arr_e - x_spine, 3), cw=cw,
               x_vch=x_vch, x_arr_e=x_arr_e, x_eband=x_eband, y0=y0, y_top=y_top, mid=mid, ch_y=ch_y, y_io=y_io,
               stack_cy=stack_cy, row_y=row_y, band=band, spine_content_mm2=content,
               spine_w_needed=need_w, spine_w_r2=SPINE_W_R2, spine_parts=spine_parts, spine_unplaced_mm2=leftovers)
    model = dict(die=die, geo=geo, insts=insts, regions=regions, notes=notes, hub=hub, phys=phys, ctrls=ctrls,
                 renges=renges, lfifos=lfifos, io=io, legs=legs, hwp=hwp, col_x=col_x, tree_mode=tree_mode, cdcs=cdcs)
    if CDC is not None:
        geo['cdc_col_w'] = cdc_w
    model['buses'] = buses(model)
    return model


# ------------------------------------------------------------------------------------------------ nets
def morton(c, r):
    z = 0
    for i in range(4):
        z |= ((c >> i) & 1) << (2 * i) | ((r >> i) & 1) << (2 * i + 1)
    return z


def buses(m):
    """[(id, class, bits, [(inst, port)])]: every die-level bus with its endpoints."""
    B = []
    g = m['geo']
    # corridors: head -> stations, away from the mid-line
    for c in range(COLS):
        prev = (f'h_{c}', 's')
        for r in range(11, -1, -1):
            B.append((f'cor_{c}_{r}', 'corridor', CORRIDOR_BITS, [prev, (f's_{c}_{r}', 'a')]))
            prev = (f's_{c}_{r}', 'b')
        prev = (f'h_{c}', 'n')
        for r in range(12, ROWS):
            B.append((f'cor_{c}_{r}', 'corridor', CORRIDOR_BITS, [prev, (f's_{c}_{r}', 'b')]))
            prev = (f's_{c}_{r}', 'a')
        for r in range(ROWS):
            B.append((f'tap_{c}_{r}', 'tap', TAP_BITS, [(f's_{c}_{r}', 'tap'), (f't_{c}_{r}', 'tap')]))
    # column-head chains from the x root (vector memory block: x network root, dataflow level 2 at the hub edge)
    xr = 'sp_vector_memory'
    prev = (xr, 'xw')
    for c in range(31, -1, -1):
        B.append((f'head_{c}', 'head_chain', CORRIDOR_BITS, [prev, (f'h_{c}', 'e')]))
        prev = (f'h_{c}', 'w')
    prev = (xr, 'xe')
    for c in range(32, COLS):
        B.append((f'head_{c}', 'head_chain', CORRIDOR_BITS, [prev, (f'h_{c}', 'w')]))
        prev = (f'h_{c}', 'e')
    # ME split tree: 4 x 4 blocks; 8 + 4 + 2 + 1 nodes hosted on distinct tiles; leaves = t_out
    bc, br = BLOCK
    nb = 0
    block_roots = []
    for c0 in range(0, COLS, bc):
        for r0 in range(0, ROWS, br):
            tiles = sorted(((c, r) for c in range(c0, c0 + bc) for r in range(r0, r0 + br)),
                           key=lambda t: morton(t[0] - c0, t[1] - r0))
            used = set()
            level = [(f't_{c}_{r}', 't_out') for c, r in tiles]
            lv = 0
            while len(level) > 1:
                nxt = []
                for i in range(0, len(level), 2):
                    # host: the first tile of this pair's subtree not yet hosting a node
                    span = 2 ** (lv + 1)
                    sub = tiles[i * (2 ** lv): i * (2 ** lv) + span]
                    host = next(f't_{c}_{r}' for c, r in sub if f't_{c}_{r}' not in used)
                    used.add(host)
                    B.append((f'tree_{nb}_{lv}_{i}a', 'tree_block', TREE_BITS, [level[i], (host, 'n_a')]))
                    B.append((f'tree_{nb}_{lv}_{i}b', 'tree_block', TREE_BITS, [level[i + 1], (host, 'n_b')]))
                    nxt.append((host, 'n_y'))
                level = nxt
                lv += 1
            block_roots.append((nb, level[0], c0, r0))
            nb += 1
    for b, root, c0, r0 in block_roots:
        if m['tree_mode'] == 'central':
            B.append((f'bword_{b}', 'tree_spine', TREE_BITS, [root, ('sp_tree_top', f'bw{b}')]))
        else:   # banded: to the port slice of this block-row band
            band = r0 // BLOCK[1]
            B.append((f'bword_{b}', 'tree_spine', TREE_BITS, [root, (f'sp_port_tiles_{band}', f'bw{b % 16}')]))
    if m['tree_mode'] != 'central':
        for band in range(6):
            B.append((f'pword_{band}', 'tree_spine', TREE_BITS, [(f'sp_port_tiles_{band}', 'rw'), ('sp_tree_top', f'bw{band}')]))
    # hub <-> stack links: hub -> vertical leg waypoints -> corner -> horizontal waypoints -> strip FIFO
    for si in range(2):
        leg, corner = m['legs'][si]
        prev = ('hub_el', 'ls' if si == 0 else 'ln')
        pin_in, pin_out = ('b', 'a') if si == 0 else ('a', 'b')
        for k, wp in enumerate(leg):
            B.append((f'lnkv_{si}_{k}', 'link_spine', 2 * LINK_TRACKS, [prev, (wp.name, pin_in)]))
            prev = (wp.name, pin_out)
        B.append((f'lnkv_{si}_c', 'link_spine', 2 * LINK_TRACKS, [prev, (corner.name, 'v')]))
        for side in 'WE':
            prev = (corner.name, side.lower())
            for k, wp in enumerate(m['hwp'][(si, side)]):
                B.append((f'lnkh_{si}{side}_{k}', 'link_channel', LINK_TRACKS,
                          [prev, (wp.name, 'e' if side == 'W' else 'w')]))
                prev = (wp.name, 'w' if side == 'W' else 'e')
            st = f'{side}{"SN"[si]}'
            B.append((f'lnkh_{si}{side}_f', 'link_channel', LINK_TRACKS, [prev, (m['lfifos'][st].name, 'lk')]))
    # in-strip fan, controller ports, PHY DFI
    if R19:
        # per-row landing fabric: stack crossbar -> the row's first tile -> ... -> the tile beside the spine
        for side in 'WE':
            cols = list(range(32)) if side == 'W' else list(range(63, 31, -1))
            for r in range(ROWS):
                st = f'{side}{"S" if r < 12 else "N"}'
                prev = (m['lfifos'][st].name, f'r{r % 12}')
                for c in cols:
                    B.append((f'kvl_{side}{r}_{c}', 'kv_land', KVL_BITS, [prev, (f't_{c}_{r}', 'li')]))
                    prev = (f't_{c}_{r}', 'lo')
    for st, res in m['renges'].items():
        if R18:
            for p, cd in enumerate(m['cdcs'][st]):
                # the closed element's four pin faces (route r11a, ot_qwen_stream4_cdc_pc RSEL=1): HCLK outputs E,
                # HCLK inputs N, landing outputs (+ l_pop) W, write-queue / write-done side S
                kvn = m['lfifos'][st].name
                B.append((f'cdho_{st}_{p}', 'hbm_cdc', CDC_HO, [(cd.name, 'ho'), (f'ctrl_{st}', f'c{p}i')]))
                B.append((f'cdhi_{st}_{p}', 'hbm_cdc', CDC['hbm_bits'] - CDC_HO, [(f'ctrl_{st}', f'c{p}o'), (cd.name, 'hi')]))
                B.append((f'cdco_{st}_{p}', 'cdc_core', CDC_CO, [(cd.name, 'co'), (kvn, f'c{p}i')]))
                B.append((f'cdci_{st}_{p}', 'cdc_core', CDC['core_bits'] - CDC_CO, [(kvn, f'c{p}o'), (cd.name, 'ci')]))
            B.append((f'dfi_{st}', 'phy_dfi', len(phy_pins()), [(f'ctrl_{st}', 'phy'), (f'phy_{st}', '*dfi')]))
            continue
        B.append((f'fan_{st}_s', 'strip_fan', LINK_TRACKS, [(f'lfifo_{st}', 'fs'), (res[2].name, 'fn')]))
        B.append((f'fan_{st}_n', 'strip_fan', LINK_TRACKS, [(f'lfifo_{st}', 'fn'), (res[3].name, 'fs')]))
        for a, b in ((2, 1), (1, 0), (3, 4), (4, 5)):
            pa, pb = ('fs', 'fn') if b < a else ('fn', 'fs')
            B.append((f'fan_{st}_{a}{b}', 'strip_fan', LINK_TRACKS, [(res[a].name, pa), (res[b].name, pb)]))
        if m.get('cdcs'):
            for p, cd in enumerate(m['cdcs'][st]):
                k = p * len(res) // len(m['cdcs'][st])
                j = p - min(q for q in range(len(m['cdcs'][st])) if q * len(res) // len(m['cdcs'][st]) == k)
                B.append((f'cdh_{st}_{p}', 'hbm_cdc', CDC['hbm_bits'], [(f'ctrl_{st}', f'c{p}'), (cd.name, 'h')]))
                B.append((f'cdc_{st}_{p}', 'cdc_core', CDC['core_bits'], [(cd.name, 'c'), (res[k].name, f'c{j}')]))
        else:
            for k, re_ in enumerate(res):
                B.append((f'rd_{st}_{k}', 'hbm_read', RE_READ_BITS, [(f'ctrl_{st}', f're{k}'), (re_.name, 'rd')]))
        B.append((f'kvn_{st}', 'hbm_read', KVNEW_BITS, [(f'lfifo_{st}', 'kv'), (f'ctrl_{st}', 'kv')]))
        B.append((f'dfi_{st}', 'phy_dfi', len(phy_pins()), [(f'ctrl_{st}', 'phy'), (f'phy_{st}', '*dfi')]))
    # hub-internal crossings and IO
    B.append(('x3', 'spine_local', IO_BITS, [('sp_su64_sfu', 'q'), ('hub_el', 'x3')]))
    B.append(('attn_ret', 'spine_local', IO_BITS, [('hub_el', 'ar'), ('sp_vector_memory', 'ar')]))
    B.append(('coll_tx', 'io', IO_BITS, [('sp_vector_memory', 'ct'), ('io_collective', 'vt')]))
    B.append(('coll_rx', 'io', IO_BITS, [('io_collective', 'vr'), ('sp_vector_memory', 'cr')]))
    B.append(('emb', 'io', IO_BITS, [('io_embedding_rom', 'o'), ('sp_vector_memory', 'em')]))
    B.append(('ucie_tx', 'io', 2 * IO_BITS, [('io_collective', 'u'), ('io_ucie', 'c')]))
    B.append(('serdes_tx', 'io', 2 * IO_BITS, [('io_collective', 's'), ('io_serdes', 'c')]))
    # clock trunks (shielded, 3 tracks): PLL (collective block) -> hub root -> each strip FIFO / controller band
    B.append(('ck_root', 'clock_trunk', CLK_TRUNK_TRACKS, [('io_collective', 'ck'), ('hub_el', 'ck')]))
    for st in m['lfifos']:
        B.append((f'ck_{st}', 'clock_trunk', CLK_TRUNK_TRACKS, [('hub_el', f'ck{st}'), (f'lfifo_{st}', 'ck')]))
    B.append(('ck_serial', 'clock_trunk', CLK_TRUNK_TRACKS, [('hub_el', 'cks'), ('sp_su64_sfu', 'ck')]))
    return B


_PHY_PINS = None


def phy_pins():
    """[(name, y_center_local)] of the v2 E/W PHY's signal pins (M4, west face)."""
    global _PHY_PINS
    if _PHY_PINS is None:
        txt = (ROOT / PHY_EW).read_text()
        out = []
        for pm in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n', txt, re.S):
            body = pm.group(2)
            if 'USE POWER' in body or 'USE GROUND' in body:
                continue
            rm = re.search(r'RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', body)
            out.append((pm.group(1), (float(rm.group(2)) + float(rm.group(4))) / 2))
        _PHY_PINS = out
    if R18:
        return [p for p in _PHY_PINS if p[0] not in ('clk', 'rst_n')]
    return _PHY_PINS


# ------------------------------------------------------------------------------------------------ abstracts
TRK = {'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M8': (0.116, 0.080)}


class Master:
    def __init__(self, name, w, h, obs_top, note):
        self.name, self.w, self.h, self.obs_top, self.note = name, w, h, obs_top, note
        self.ports = {}            # port -> (width, face, layer, centre_um along the face, pitch_tracks) | area
        self.order = []

    def face(self, port, width, face, layer, centre, pitch=1):
        self.ports[port] = ('face', width, face, layer, centre, pitch)
        self.order.append(port)

    def area(self, port, width, x, ycentre, pitch=2):
        self.ports[port] = ('area', width, x, ycentre, pitch)
        self.order.append(port)


def masters(m, k=1, port_bits=None):
    """Abstract masters.  k = bundle factor (1: real ASAP7 pins).  port_bits: (master, port) -> bits used."""
    g = m['geo']
    M = {}

    def mk(name, w, h, obs, note):
        M[name] = Master(name, w, h, obs, note)
        return M[name]
    tw, th = TILE_BODY_W - SHAVE, TILE_SLOT[1] - SHAVE
    sy = dn((TILE_SLOT[1] - STATION[1]) / 2, GY)
    t = mk('qfd_tile', tw, th, 7, 'W12 ROM tile re-frame (10 x ot_rom_4096x266_m8, cell ceiling 125,000 um2 at 0.5): '
           'internal routing M1-M7 (ORFS asap7 MAX_ROUTING_LAYER), M8/M9 over the top for die nets' +
           ('; r19 FULL tile: + KV slice 2 x ot_sram_1r1w_128x256_m1_r2c2 (8 KiB) and the landing-fabric hop (768 b '
            'registered in / out, the per-tile landing merge)' if R19 else ''))
    if R19:
        t.face('li', KVL_BITS, 'W', 'M4', th * 0.78, 1)
        t.face('lo', KVL_BITS, 'E', 'M4', th * 0.78, 1)
    t.face('tap', TAP_BITS, 'E', 'M4', sy + STATION[1] / 2, 2)
    for i, p in enumerate(('t_out', 'n_a', 'n_b', 'n_y')):
        t.area(p, TREE_BITS, 40.0 + 60.0 * i, th / 2, 2)
    if R19:
        te = mk('qfd_tile_e', tw, th, 7, t.note + ' (east-array variant: landing flows west)')
        te.ports, te.order = {k_: v_ for k_, v_ in t.ports.items()}, list(t.order)
        te.ports['li'] = ('face', KVL_BITS, 'E', 'M4', th * 0.78, 1)
        te.ports['lo'] = ('face', KVL_BITS, 'W', 'M4', th * 0.78, 1)
    s = mk('qfd_cst', STATION[0] - SHAVE, STATION[1] - SHAVE, 3, 'corridor pipeline station (637 flops + 3 tap '
           'repeater banks): standard cells M1-M3, die routing above')
    s.face('a', CORRIDOR_BITS, 'N', 'M5', s.w / 2, 1)
    s.face('b', CORRIDOR_BITS, 'S', 'M5', s.w / 2, 1)
    s.face('tap', TAP_BITS, 'W', 'M4', s.h / 2, 2)
    hd = mk('qfd_chead', STATION[0] - SHAVE, STATION[1] - SHAVE, 3, 'column head: head-chain station + corridor '
            'split north/south')
    for f, p in (('N', 'n'), ('S', 's')):
        hd.face(p, CORRIDOR_BITS, f, 'M5', hd.w / 2, 1)
    for f, p in (('W', 'w'), ('E', 'e')):
        hd.face(p, CORRIDOR_BITS, f, 'M4', hd.h / 2, 1)
    re_ = mk('qfd_reng', STRIP_W - SHAVE, RE_H - SHAVE, 7, 'near-HBM row engine (512 MAC lanes, 4 exp pipes, '
             'score SRAM): ot_qwen_nearhbm_attn_stack frame r1 328.32 x 1,998')
    re_.face('rd', RE_READ_BITS, 'E', 'M4', re_.h / 2, 2)
    re_.face('fn', LINK_TRACKS, 'N', 'M5', re_.w / 2, 2)
    re_.face('fs', LINK_TRACKS, 'S', 'M5', re_.w / 2, 2)
    lf = mk('qfd_lfifo', FIFO[0] - SHAVE, FIFO[1] - SHAVE, 3, 'strip-end link endpoint: mesochronous bisync FIFO '
            '(M1-M4), depth 8')
    lf.face('lk', LINK_TRACKS, 'W', 'M4', lf.h / 2, 1)
    lf.face('fn', LINK_TRACKS, 'N', 'M5', lf.w / 2, 1)
    lf.face('fs', LINK_TRACKS, 'S', 'M5', lf.w / 2, 1)
    lf.face('kv', KVNEW_BITS, 'E', 'M4', lf.h / 2 - 20, 1)
    lf.face('ck', CLK_TRUNK_TRACKS, 'E', 'M4', lf.h / 2 + 30, 1)
    span = 6 * RE_H + FIFO[1]
    c = mk('qfd_ctrl', CTRL_W - SHAVE, span - SHAVE, 7, 'streaming HBM controller (0.159 mm2/die, claude/qwen-hbm-'
           'sustained-bw @ 52ce3e9c1) + per-PC KV service (kept + ambiguous 11.878 mm2/die): 976.6 MHz')
    # PHY pins: same die y as the PHY's west-face pins
    st0 = next(iter(m['ctrls']))
    off = m['phys'][st0].y - m['ctrls'][st0].y
    c.ports['phy'] = ('phy', len(phy_pins()), 'E', 'M4', off, 1)
    c.order.append('phy')
    for kk in range(6):
        yy = kk * RE_H + (FIFO[1] if kk >= 3 else 0) + RE_H / 2
        c.face(f're{kk}', RE_READ_BITS, 'W', 'M4', yy, 2)
    c.face('kv', KVNEW_BITS, 'W', 'M4', 3 * RE_H + FIFO[1] / 2 - 20, 1)
    if m.get('cdcs'):
        # the controller's per-PC CDC ports face the CDC frame they feed; the row engine's per-PC landing ports
        # face the CDC frames it serves (centred on each frame)
        for o in list(c.order):
            if o.startswith('re'):
                c.order.remove(o)
                c.ports.pop(o)
        cds = m['cdcs'][st0]
        for p, cd in enumerate(cds):
            if R18:
                yc = cd.y - m['ctrls'][st0].y
                c.face(f'c{p}i', CDC_HO, 'W', 'M4', yc + cd.h * 0.35, 1)
                c.face(f'c{p}o', CDC['hbm_bits'] - CDC_HO, 'W', 'M4', yc + cd.h + 20.0, 1)
                continue
            c.face(f'c{p}', CDC['hbm_bits'], 'W', 'M4', cd.y - m['ctrls'][st0].y + cd.h / 2, 2)
        cdm = mk('qfd_cdc', CDC['w'], CDC['h'], 7, 'STREAM4 per-PC CDC element (ot_qwen_stream4_cdc_pc, routed frame)')
        if R18:
            cdm.face('ho', CDC_HO, 'E', 'M4', cdm.h * 0.35, 1)
            cdm.face('hi', CDC['hbm_bits'] - CDC_HO, 'N', 'M5', cdm.w / 2, 1)
            cdm.face('co', CDC_CO, 'W', 'M4', cdm.h * 0.6, 1)
            cdm.face('ci', CDC['core_bits'] - CDC_CO, 'S', 'M5', cdm.w / 2, 1)
        else:
            cdm.face('h', CDC['hbm_bits'], 'E', 'M4', cdm.h / 2, 2)
            cdm.face('c', CDC['core_bits'], 'W', 'M4', cdm.h / 2, 2)
        nmax = max(sum(1 for p in range(len(cds)) if p * 6 // len(cds) == k) for k in range(6))
        if R18:
            # the KV landing concentrator: link endpoint on the array face, every PC's CDC core side level with
            # its frame on the CDC face; the KV-new write rides the CDC write queues (no kvn bus to the controller)
            M.pop('qfd_reng', None)
            M.pop('qfd_lfifo', None)
            for o in [o for o in c.order if o == 'kv']:
                c.order.remove(o)
                c.ports.pop(o)
            reps = [st0] if not R19 else [next(k for k in m['lfifos'] if k.endswith('S')),
                                          next(k for k in m['lfifos'] if k.endswith('N'))]
            for rep_ in reps:
                lf_ = m['lfifos'][rep_]
                kv = mk(lf_.master, lf_.w, lf_.h, 7, 'STREAM4 KV landing concentrator (32 PC landing words -> the '
                        'stack link, KV-new write into the CDC write queues) + strip-end link endpoint')
                kv.face('lk', LINK_TRACKS, 'W', 'M4', (m['geo']['stack_cy'][0 if rep_.endswith('S') else 1] - lf_.y)
                        if R19 else (m['geo']['stack_cy'][0] - lf_.y), 1)
                if R19:
                    kv.note += '; r19: landing crossbar, 32 PC words -> 12 row buses x 768 b (one per tile row)'
                    ry = m['geo']['row_y']
                    r0 = 0 if rep_.endswith('S') else 12
                    for j in range(12):
                        kv.face(f'r{j}', KVL_BITS, 'W', 'M4', ry[r0 + j] + TILE_SLOT[1] * 0.78 - lf_.y, 1)
                for p, cd in enumerate(m['cdcs'][rep_]):
                    yc = cd.y - lf_.y
                    kv.face(f'c{p}i', CDC_CO, 'E', 'M4', yc + cd.h * 0.6, 1)
                    kv.face(f'c{p}o', CDC['core_bits'] - CDC_CO, 'E', 'M4', yc - 20.0, 1)
            nmax = 0
        if 'rd' in re_.ports:
            re_.order.remove('rd')
            re_.ports.pop('rd')
        for j in range(nmax):
            re_.face(f'c{j}', CDC['core_bits'], 'E', 'M4', (j + 0.5) * re_.h / nmax, 2)
    hb = mk('qfd_hub', m['hub'].w, m['hub'].h, 7, 'hub element: near-HBM combine (P.V 8-9, Z 5-10, 1/Z), 4 link '
            'endpoints (FIFO 8), X3 q/new-KV staging')
    hb.face('ln', 2 * LINK_TRACKS, 'N', 'M5', hb.w / 2, 1)
    hb.face('ls', 2 * LINK_TRACKS, 'S', 'M5', hb.w / 2, 1)
    hb.face('x3', IO_BITS, 'W', 'M4', hb.h / 2 - 60, 2)
    hb.face('ar', IO_BITS, 'W', 'M4', hb.h / 2 + 60, 2)
    for i, p in enumerate(['ck'] + [f'ck{st}' for st in m['lfifos']] + ['cks']):
        hb.face(p, CLK_TRUNK_TRACKS, 'E', 'M4', 20 + 12 * i, 1)
    lv = mk('qfd_lst_v', LST_V[0] - SHAVE, LST_V[1] - SHAVE, 3, 'link pipeline waypoint (vertical spine leg, 2 links)')
    lv.face('a', 2 * LINK_TRACKS, 'S' , 'M5', lv.w / 2, 1)
    lv.face('b', 2 * LINK_TRACKS, 'N', 'M5', lv.w / 2, 1)
    # vertical waypoints of the south leg are passed north->south: 'a' faces the hub on both legs by netlist
    lc = mk('qfd_lst_c', VCH - SHAVE, HCH - SHAVE, 3, 'link corner station: leg splits west/east')
    lc.face('v', 2 * LINK_TRACKS, 'S', 'M5', lc.w / 2, 1)
    lc.face('w', LINK_TRACKS, 'W', 'M4', lc.h / 2, 1)
    lc.face('e', LINK_TRACKS, 'E', 'M4', lc.h / 2, 1)
    lh = mk('qfd_lst_h', LST_H[0] - SHAVE, LST_H[1] - SHAVE, 3, 'link pipeline waypoint (horizontal channel)')
    lh.face('w', LINK_TRACKS, 'W', 'M4', lh.h / 2, 1)
    lh.face('e', LINK_TRACKS, 'E', 'M4', lh.h / 2, 1)
    # spine blocks
    for it in m['insts']:
        if it.kind != 'spine_block' or it.master in M:
            continue
        b = mk(it.master, it.w, it.h, 7, f'spine reservation slab {it.master}')
        if it.master == 'qfd_sp_vector_memory':
            b.face('xw', CORRIDOR_BITS, 'W', 'M4', b.h / 2, 1)
            b.face('xe', CORRIDOR_BITS, 'E', 'M4', b.h / 2, 1)
            b.face('ar', IO_BITS, 'E', 'M4', b.h / 2 - 60, 2)
            b.face('ct', IO_BITS, 'N', 'M5', b.w / 2 - 120, 2)
            b.face('cr', IO_BITS, 'N', 'M5', b.w / 2 + 120, 2)
            b.face('em', IO_BITS, 'S', 'M5', b.w / 2, 2)
        elif it.master == 'qfd_sp_su64_sfu':
            b.face('q', IO_BITS, 'E', 'M4', b.h / 2, 2)
            b.face('ck', CLK_TRUNK_TRACKS, 'E', 'M4', b.h / 2 + 50, 1)
        elif it.master == 'qfd_sp_tree_top':
            n = 96 if m['tree_mode'] == 'central' else 6
            cols = 8
            for i in range(n):
                b.area(f'bw{i}', TREE_BITS, 20.0 + (b.w - 40.0) * (i % cols) / cols,
                       b.h * ((i // cols) + 0.5) / math.ceil(n / cols), 1)
        elif it.master.startswith('qfd_sp_port_tiles'):
            if m['tree_mode'] != 'central':
                for i in range(16):
                    b.area(f'bw{i}', TREE_BITS, 20.0 + (b.w - 40.0) * (i % 8) / 8, b.h * ((i // 8) + 0.5) / 2, 1)
                b.face('rw', TREE_BITS, 'E', 'M4', b.h / 2, 1)
    for name, it in m['io'].items():
        b = mk(it.master, it.w, it.h, 7, f'IO band block {name}')
        if name == 'collective':
            b.face('vt', IO_BITS, 'S', 'M5', b.w / 2 - 300, 2)
            b.face('vr', IO_BITS, 'S', 'M5', b.w / 2 + 300, 2)
            b.face('u', 2 * IO_BITS, 'E', 'M4', b.h / 2, 2)
            b.face('s', 2 * IO_BITS, 'N', 'M5', b.w / 2, 2)
            b.face('ck', CLK_TRUNK_TRACKS, 'S', 'M5', b.w / 2, 1)
        elif name == 'embedding_rom':
            b.face('o', IO_BITS, 'E', 'M4', b.h / 2, 2)
        else:
            b.face('c', 2 * IO_BITS, 'W' if name == 'ucie' else 'S', 'M4' if name == 'ucie' else 'M5',
                   b.h / 2 if name == 'ucie' else b.w / 2, 2)
    if k > 1:
        ph = mk('ot_hbm3e_phy', 833.496, 12000.12, 4, 'v2 E/W HBM3E PHY abstract (bundled view)')
        pp = phy_pins()
        ph.face('dfi', len(pp), 'W', 'M4', (pp[0][1] + pp[-1][1]) / 2, 4)
        c.ports['phy'] = ('face', len(pp), 'E', 'M4', off + (pp[0][1] + pp[-1][1]) / 2, 4)
    return M


def pin_rects(mst, k, wmap):
    """[(pin name, layer, (x0, y0, x1, y1))] for one master.  wmap: port -> width actually emitted."""
    out = []
    for port in mst.order:
        spec = mst.ports[port]
        n = wmap.get(port, spec[1])
        if n <= 0:
            continue
        names = [f'{port}[{i}]' for i in range(n)] if n > 1 or True else [port]
        if spec[0] == 'phy':
            for (pn, yc), nm in zip(phy_pins(), names):
                y = spec[4] + yc
                out.append((nm, 'M4', (mst.w - 0.192, y - 0.012, mst.w, y + 0.012)))
            continue
        if spec[0] == 'area':
            _, _, x, yc, pitch = spec
            off, p = TRK['M8']
            step = p * k * pitch
            y = off * k + round((yc - n * step / 2 - off * k) / (p * k)) * p * k
            hw = 0.020 * k
            for i, nm in enumerate(names):
                yy = y + i * step
                out.append((nm, 'M8', (x, yy - hw, x + 0.4 * k, yy + hw)))
            continue
        _, _, face, layer, centre, pitch = spec
        off, p = TRK[layer]
        step = p * k * pitch
        along = mst.h if face in 'EW' else mst.w
        start = centre - n * step / 2
        start = max(start, 2 * p * k)
        if start + n * step > along - 2 * p * k:
            start = along - 2 * p * k - n * step
        if start < 0:
            raise ValueError(f'{mst.name}.{port}: {n} pins x {step:.3f} um do not fit {along:.3f} um ({face})')
        first = off * k + math.ceil((start - off * k) / (p * k) - 1e-9) * p * k
        hw = 0.012 * k
        depth = 0.192 * (k if k > 1 else 1)
        for i, nm in enumerate(names):
            pos = first + i * step
            if face == 'W':
                r = (0.0, pos - hw, depth, pos + hw)
            elif face == 'E':
                r = (mst.w - depth, pos - hw, mst.w, pos + hw)
            elif face == 'S':
                r = (pos - hw, 0.0, pos + hw, depth)
            else:
                r = (pos - hw, mst.h - depth, pos + hw, mst.h)
            out.append((nm, layer, r))
    return out


def lef_text(mst, k, wmap):
    L = [f'# tools/qwen_rom_fulldie.py abstract: {mst.note}', f'MACRO {mst.name}', '  CLASS BLOCK ;',
         f'  FOREIGN {mst.name} 0 0 ;', f'  SIZE {mst.w:.3f} BY {mst.h:.3f} ;', '  SYMMETRY X Y ;']
    pins = pin_rects(mst, k, wmap)
    for nm, layer, (a, b, c_, d) in pins:
        L += [f'  PIN {nm}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', f'      LAYER {layer} ;',
              f'        RECT {a:.3f} {b:.3f} {c_:.3f} {d:.3f} ;', '    END', f'  END {nm}']
    L.append('  OBS')
    for i in range(1, mst.obs_top + 1):
        L += [f'    LAYER M{i} ;', f'      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;']
    L += ['  END', f'END {mst.name}', '']
    return '\n'.join(L), len(pins)


# ------------------------------------------------------------------------------------------------ writers
def port_widths(m, k):
    """(master, port) -> emitted pin count (bundled: ceil(bits / k))."""
    w = {}
    by = {it.name: it for it in m['insts']}
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        for inst, port in eps:
            mstn = by[inst].master
            key = (mstn, port.lstrip('*'))
            w[key] = max(w.get(key, 0), n)
    return w


def write_netlist(m, k, path, top='qfd_die'):
    by = {it.name: it for it in m['insts']}
    conns = {it.name: [] for it in m['insts']}
    V = [f'// tools/qwen_rom_fulldie.py: die-level nets only (k = {k}: one net = {k} wires of a bus)',
         f'module {top} ();']
    phyn = [p[0] for p in phy_pins()]
    for bid, cls, bits, eps in m['buses']:
        n = bits if k == 1 else max(1, math.ceil(bits / k))
        net = f'n_{bid}'
        V.append(f'  wire [{n - 1}:0] {net};')
        for inst, port in eps:
            if port == '*dfi' and k == 1:
                # real PHY: its named (bus) pins, each bit to one bit of this net
                groups = {}
                for i, pn in enumerate(phyn):
                    mm = re.match(r'^(.*)\[(\d+)\]$', pn)
                    if mm:
                        groups.setdefault(mm.group(1), {})[int(mm.group(2))] = i
                    else:
                        conns[inst].append(f'.{esc(pn)}({net}[{i}])')
                for base, bits_ in groups.items():
                    hi = max(bits_)
                    cat = ', '.join(f'{net}[{bits_[j]}]' if j in bits_ else "1'b0" for j in range(hi, -1, -1))
                    conns[inst].append(f'.{esc(base)}({{{cat}}})')
            else:
                conns[inst].append(f'.{port.lstrip("*")}({net})')
    for it in m['insts']:
        V.append(f'  {it.master} {it.name} (' + ', '.join(conns[it.name]) + ');')
    V.append('endmodule\n')
    Path(path).write_text('\n'.join(V))


def esc(pn):
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', pn):
        return pn
    return '\\' + pn + ' '


def write_def_floorplan(m, path):
    """Die outline, every instance FIXED, region/group per clock domain, placement blockages over channels."""
    die = m['die']
    o = {'R0': 'N', 'MY': 'FN', 'MX': 'FS', 'R180': 'S'}
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN qfd_die ;',
         'UNITS DISTANCE MICRONS 1000 ;', f'DIEAREA ( 0 0 ) ( {round(die["w"] * 1000)} {round(die["h"] * 1000)} ) ;']
    dom_rects = {}
    for r in m['regions']:
        dom = {'strip': 'stream_1p2', 'ctrl': 'hbm_976p6', 'phy': 'hbm_976p6', 'io': 'io_mixed'}.get(r['kind'],
                                                                                                    'stream_1p2')
        if r['kind'] == 'hub':
            continue
        dom_rects.setdefault(dom, []).append(r['rect'])
    for it in m['insts']:
        if it.domain == 'serial_0p9':
            dom_rects.setdefault('serial_0p9', []).append([it.x, it.y, it.x + it.w, it.y + it.h])
    d.append(f'REGIONS {len(dom_rects)} ;')
    for dom, rects in dom_rects.items():
        rr = ' '.join(f'( {round(a * 1000)} {round(b * 1000)} ) ( {round(c * 1000)} {round(e * 1000)} )'
                      for a, b, c, e in rects[:2000])
        d.append(f'- {dom} {rr} + TYPE FENCE ;' if dom == 'serial_0p9' else f'- {dom} {rr} + TYPE GUIDE ;')
    d.append('END REGIONS')
    d.append(f'COMPONENTS {len(m["insts"])} ;')
    for it in m['insts']:
        d.append(f'- {it.name} {it.master} + FIXED ( {round(it.x * 1000)} {round(it.y * 1000)} ) {o[it.orient]} ;')
    d.append('END COMPONENTS')
    blk = [r for r in m['regions'] if r['kind'] == 'channel']
    d.append(f'BLOCKAGES {len(blk)} ;')
    for r in blk:
        a, b, c, e = r['rect']
        d.append(f'- PLACEMENT + PARTIAL 30.0 RECT ( {round(a * 1000)} {round(b * 1000)} ) ( {round(c * 1000)} {round(e * 1000)} ) ;')
    d.append('END BLOCKAGES')
    groups = {}
    for it in m['insts']:
        if it.domain in dom_rects and it.domain != 'stream_1p2':
            groups.setdefault(it.domain, []).append(it.name)
    d.append(f'GROUPS {len(groups)} ;')
    for gname, mem in groups.items():
        d.append(f'- grp_{gname} ' + ' '.join(mem) + f' + REGION {gname} ;')
    d.append('END GROUPS')
    d += ['END DESIGN', '']
    Path(path).write_text('\n'.join(d))


def write_sdc(path):
    Path(path).write_text("""# Die-level clock domains (AGENTS.md clock domains; HBM service at the streaming controller's CK/2)
create_clock -name clk_stream -period 0.833 [get_pins hub_el/ck]
create_clock -name clk_serial -period 1.111 [get_pins sp_su64_sfu/ck]
create_clock -name clk_hbm    -period 1.024 [get_pins {phy_*/clk}]
set_clock_uncertainty -setup 0.060 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
# crossings (each a FIFO; never a timed single-cycle path):
#   X1/X2/X3  hub spine centre, stream <-> serial, ratio CDC FIFO (rtl/common/ot_ratio_cdc_fifo.sv, 3:4)
#   H1-H24    controller band -> row engines (hbm 976.6 MHz -> stream 1.2 GHz), async two-clock FIFO per row engine
#   K1-K4     strip FIFO -> controller (new K/V write), async
#   M1-M4     strip-end link FIFOs: mesochronous (same 1.2 GHz, separate local trees)
#   L1-L2     IO band: UCIe / board SerDes, plesiochronous
set_clock_groups -asynchronous -group {clk_stream} -group {clk_serial} -group {clk_hbm}
""")


def write_pdn_tcl(path):
    """Per-region M8/M9 straps at the r2 coverages: 0.48 um stripes (below the 0.49975 um wide-metal class) at the
    pitch that gives the coverage per net, as macro grids over each region's instances; channels/corridors take the
    core grid at the tile-field coverage."""
    def pitch(cov):
        return round(dn(0.48 / cov, 0.080 * 2), 3)
    L = ['# tools/qwen_rom_fulldie.py die PDN: M8/M9 per-region straps at the r2 coverages (per net)',
         'add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power',
         'add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground',
         'global_connect', 'set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}',
         'define_pdn_grid -name {core} -voltage_domains {CORE} -pins {M9}']
    p = pitch(REGION_PG['tile_field'])
    L += [f'add_pdn_stripe -grid {{core}} -layer {{M8}} -width {{0.48}} -pitch {{{p}}} -offset {{2.0}}',
          f'add_pdn_stripe -grid {{core}} -layer {{M9}} -width {{0.48}} -pitch {{{p}}} -offset {{2.0}}',
          'add_pdn_connect -grid {core} -layers {M8 M9}']
    for grid, pat, cov in (('strip', 'qfd_reng qfd_lfifo qfd_ctrl', REGION_PG['strip']),
                           ('hub', 'qfd_hub qfd_sp_* qfd_lst_*', REGION_PG['hub']),
                           ('io', 'qfd_io_*', REGION_PG['io'])):
        p = pitch(cov)
        L += [f'set {grid}_cells {{}}',
              f'foreach mst [[ord::get_db] getLibs] {{ foreach c [$mst getMasters] {{ foreach pp {{{pat}}} {{ '
              f'if {{[string match $pp [$c getName]]}} {{ lappend {grid}_cells [$c getName] }} }} }} }}',
              f'define_pdn_grid -macro -cells ${grid}_cells -halo {{0 0 0 0}} -voltage_domains {{CORE}} -name {{{grid}}}',
              f'add_pdn_stripe -grid {{{grid}}} -layer {{M8}} -width {{0.48}} -pitch {{{p}}} -offset {{1.0}}',
              f'add_pdn_stripe -grid {{{grid}}} -layer {{M9}} -width {{0.48}} -pitch {{{p}}} -offset {{1.0}}',
              f'add_pdn_connect -grid {{{grid}}} -layers {{M8 M9}}']
    Path(path).write_text('\n'.join(L) + '\n')


def svg(m, path, scale=0.03):
    die = m['die']
    W, H = die['w'], die['h']
    s = scale
    col = dict(tile='#cfe0f3', station='#e6550d', head='#a63603', row_engine='#fdae6b', link_fifo='#d94801',
               ctrl='#9e9ac8', phy='#756bb1', hub_element='#31a354', spine_block='#c7e9c0', io='#fee391',
               link_station='#08519c')
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * s:.0f}" height="{H * s:.0f}" viewBox="0 0 {W * s:.1f} {H * s:.1f}">',
         f'<rect width="{W * s:.1f}" height="{H * s:.1f}" fill="#fff" stroke="#000"/>']
    for r in m['regions']:
        if r['kind'] in ('channel',):
            a, b, c, e = r['rect']
            o.append(f'<rect x="{a * s:.1f}" y="{(H - e) * s:.1f}" width="{(c - a) * s:.1f}" height="{(e - b) * s:.1f}" fill="#deebf7"/>')
    for it in m['insts']:
        if it.kind in ('station',):
            continue
        o.append(f'<rect x="{it.x * s:.2f}" y="{(H - it.y - it.h) * s:.2f}" width="{max(it.w * s, 0.3):.2f}" '
                 f'height="{max(it.h * s, 0.3):.2f}" fill="{col.get(it.kind, "#ccc")}" stroke="#555" stroke-width="0.1"/>')
    o.append('</svg>\n')
    Path(path).write_text('\n'.join(o))


def link_stages(m):
    """Registered stages on the hub <-> stack link and hub <-> IO paths at the 504 um r2 reach and at the corridor
    gate's closing pitch (430.56 um); per-token delta = 2 directions x 36 layers x delta stages (r1 pricing rule)."""
    g = m['geo']
    hub = m['hub']
    rows = []
    for st, lf in m['lfifos'].items():
        si = 0 if st[1] == 'S' else 1
        corner_y = g['ch_y'][si] + HCH / 2
        vert = abs((hub.y + hub.h / 2) - corner_y)
        horiz = abs((g['x_vch'] + VCH / 2) - (lf.x + lf.w / 2))
        fan = 2.5 * RE_H + FIFO[1] / 2                     # FIFO to the farthest row-engine centre
        trunk = vert + horiz
        r = dict(stack=st, trunk_um=round(trunk, 1), fan_um=round(fan, 1))
        for reach in (504.0, 450.0, LINK_STAGE_UM):
            r[f'stages_{int(reach)}'] = math.ceil(trunk / reach) + math.ceil(fan / reach)
        rows.append(r)
    worst = max(rows, key=lambda r: r['stages_504'])
    d = worst[f'stages_{int(LINK_STAGE_UM)}'] - worst['stages_504']
    io = abs(m['io']['collective'].y - (hub.y + hub.h / 2))
    return dict(paths=rows, worst=worst['stack'], r2_model_total_stages=46,
                delta_stages_at_430=d, per_token_cycles_delta=2 * 36 * d,
                per_token_us_delta=round(2 * 36 * d / 1.2e3, 3),
                hub_to_io=dict(um=round(io, 1), stages_504=math.ceil(io / 504), stages_430=math.ceil(io / LINK_STAGE_UM)),
                note='hub<->stack stations re-pitched to <= 430.56 um (corridor gate: 504 um spans miss SS setup by '
                     '29-79 ps); the tile-column corridor already runs 3 x 430.56 um per tile hop (closes). Report to '
                     'the model: the selected entry prices 45-46 stages.')


# ------------------------------------------------------------------------------------------------ plan record
def plan_record(m):
    die, g = m['die'], m['geo']
    kinds = {}
    for it in m['insts']:
        kinds[it.kind] = kinds.get(it.kind, 0) + 1
    cls = {}
    for bid, c, bits, eps in m['buses']:
        e = cls.setdefault(c, dict(buses=0, wires=0))
        e['buses'] += 1
        e['wires'] += bits
    area = {}
    for it in m['insts']:
        area[it.kind] = area.get(it.kind, 0.0) + (it.w + SHAVE) * (it.h + SHAVE) / 1e6
    r2m = r2()
    return dict(
        schema='opentallas.qwen-rom-fulldie.floorplan.v1', tool='tools/qwen_rom_fulldie.py', tool_sha256=sha('tools/qwen_rom_fulldie.py'),
        sources_sha256={p: sha(p) for p in (R2, R1, PHY_EW, SNAP_LIB)},
        die=die, r2_die_um=r2m['floorplan']['die_um'], r2_die_mm2=r2m['floorplan']['die_mm2'],
        delta_vs_r2=dict(die_w_um=round(die['w'] - r2m['floorplan']['die_um'][0], 3),
                         die_h_um=round(die['h'] - r2m['floorplan']['die_um'][1], 3),
                         die_mm2=round(die['mm2'] - r2m['floorplan']['die_mm2'], 3),
                         why=['spine content packed as two columns beside a centred vertical link channel with both '
                              'horizontal link channels crossing it, and the hub element row: needs '
                              f'{g["spine_w_needed"]} um against r2 {SPINE_W_R2} um',
                              'every origin on the die-origin 0.432 x 2.16 lattice (r2 used a core-relative lattice)']),
        geometry={k: v for k, v in g.items() if k not in ('row_y',)},
        instances=kinds, area_mm2_by_kind={k: round(v, 3) for k, v in area.items()},
        bus_classes=cls, notes=m['notes'], tree_mode=m['tree_mode'],
        regions=[dict(name=r['name'], kind=r['kind'], rect=[round(x, 3) for x in r['rect']],
                      pg_coverage_per_net=REGION_PG.get(r['kind']), peak_w_per_mm2=REGION_W_PER_MM2.get(r['kind']))
                 for r in m['regions'] if not r['name'].startswith('corr_')],
        link_stages=link_stages(m),
        corridor_gate_constraints=dict(
            source='claude/qwen-corridor-gate-20261003 @ 89e70dd78 verdict',
            centred_pin_row='tile tap pin row centred on its station (station at tile mid-height; tap rows on both '
                            'sides centred on the station centre): satisfied by construction',
            station_slab=f'station frame {STATION[0]} x {STATION[1]} um >= the 17.28 um slab variant',
            long_haul_layers='bundled GRT: M2-M5 adjustment 1.0 (no long haul); M6/M8 horizontal, M7/M9 vertical',
            stage_pitch_um=LINK_STAGE_UM),
        corridors=dict(count=COLS, width_um=CORR, bits=CORRIDOR_BITS, stations_per_column=ROWS, heads=COLS,
                       station_frame_um=list(STATION), tap_bits=TAP_BITS),
        clock_domains=dict(
            stream_1p2=dict(period_ns=0.833, regions=['tile field', 'corridors', 'channels', 'near-HBM strips',
                                                     'hub element', 'link stations', 'tree top / port / scale']),
            serial_0p9=dict(period_ns=1.111, regions=['SU64/SFU', 'vector memory (serial side)', 'collective reducers']),
            hbm_976p6=dict(period_ns=1.024, regions=['controller bands', 'PHY DFI'])),
        crossings=[
            dict(id='X1-X3', where='hub spine centre (SU/VM <-> hub element / x root)', kind='ratio CDC FIFO 3:4',
                 rtl='rtl/common/ot_ratio_cdc_fifo.sv (claude/two-clock-rtl-20261003 @ 27d86cfe)', count=3),
            dict(id='H1-H24', where='controller band west/east face -> each row engine', kind='async two-clock FIFO '
                 '(976.6 -> 1,200 MHz: 625:768, not a small ratio)', count=24, new=True,
                 note='r1/r2 list P1-P4 at the PHY boundary assuming a 1.2 GHz service; the streaming controller '
                      'closes at CK/2 = 976.6 MHz, so the crossing moves to the controller/row-engine face'),
            dict(id='K1-K4', where='strip FIFO -> controller (new-token K/V write)', kind='async FIFO', count=4, new=True),
            dict(id='M1-M4', where='strip-end link FIFO', kind='mesochronous bisync FIFO', count=4),
            dict(id='L1-L2', where='IO band', kind='plesiochronous link crossing', count=2)],
    )


# ------------------------------------------------------------------------------------------------ case (a): real
def case_real(m, work):
    work.mkdir(parents=True, exist_ok=True)
    k = 1
    M = masters(m, k)
    pw = port_widths(m, k)
    lefs, npins = [], 0
    for name, mst in M.items():
        wmap = {p: pw.get((name, p), 0) for p in mst.order}
        txt, n = lef_text(mst, k, wmap)
        lefs.append(txt)
        npins += n
    (work / 'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs) + 'END LIBRARY\n')
    (work / 'phy_ew.lef').write_text((ROOT / PHY_EW).read_text())
    (work / 'snap.tcl').write_text((ROOT / SNAP_LIB).read_text())
    write_netlist(m, k, work / 'die.v')
    write_pdn_tcl(work / 'pdn.tcl')
    die = m['die']
    pl = ['set _blk [ord::get_db_block]'] + [f'ot_mts::place [$_blk findInst {it.name}] {it.x:.3f} {it.y:.3f} {it.orient}'
                                           for it in m['insts']]
    (work / 'place.tcl').write_text('\n'.join(pl) + '\n')
    tcl = f"""# case (a): real-technology die floorplan, macro placement legality, on-track assert, pin access
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/phy_ew.lef
read_lef /work/elements.lef
read_verilog /work/die.v
link_design qfd_die
mem linked
initialize_floorplan -die_area {{0 0 {die['w']:.3f} {die['h']:.3f}}} -core_area {{0 0 {die['w']:.3f} {die['h']:.3f}}} -site asap7sc7p5t
source {PLAT}/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) {PLAT}/openRoad/make_tracks.tcl
source /work/snap.tcl
mem floorplan
set t0 [clock seconds]
source /work/place.tcl
puts "OT_TIME place_s=[expr {{[clock seconds]-$t0}}]"
mem placed
# legality: every instance inside the die, no two macros overlap (sweep on x), lattice moves reported
set blk [ord::get_db_block]
set boxes {{}}
foreach inst [$blk getInsts] {{
  set bb [$inst getBBox]
  lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$inst getName]]
}}
set boxes [lsort -integer -index 0 $boxes]
set n [llength $boxes]; set ov 0; set out 0
set dw [[$blk getDieArea] xMax]; set dh [[$blk getDieArea] yMax]
set active {{}}
foreach b $boxes {{
  lassign $b x0 y0 x1 y1 nm
  if {{$x0 < 0 || $y0 < 0 || $x1 > $dw || $y1 > $dh}} {{ incr out; if {{$out < 20}} {{ puts "OT_OUTSIDE $nm" }} }}
  set keep {{}}
  foreach a $active {{
    lassign $a ax0 ay0 ax1 ay1 an
    if {{$ax1 > $x0}} {{
      lappend keep $a
      if {{$ay0 < $y1 && $y0 < $ay1}} {{ incr ov; if {{$ov < 50}} {{ puts "OT_OVERLAP $an $nm" }} }}
    }}
  }}
  lappend keep $b
  set active $keep
}}
puts "OT_LEGAL instances=$n overlaps=$ov outside=$out"
write_def /work/floorplan_placed.def
mem def
if {{[catch {{ot_mts::assert_on_track -label fulldie}} err]}} {{ puts "OT_ASSERT FAIL $err" }} else {{ puts "OT_ASSERT PASS" }}
mem assert
set t0 [clock seconds]
set_routing_layers -signal M2-M9
if {{[catch {{pin_access -verbose 1}} err]}} {{ puts "OT_PA FAIL $err" }} else {{ puts "OT_PA DONE" }}
puts "OT_TIME pa_s=[expr {{[clock seconds]-$t0}}]"
mem pa
write_db /work/floorplan.odb
"""
    (work / 'run.tcl').write_text(tcl)
    (work / 'run_pa.tcl').write_text(f"""# case (a) follow-on: pin access and die PDN on the placed floorplan
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_db /work/floorplan.odb
mem read
set_routing_layers -signal M2-M9
set t0 [clock seconds]
if {{[catch {{pin_access -verbose 1}} err]}} {{ puts "OT_PA FAIL $err" }} else {{ puts "OT_PA DONE" }}
puts "OT_TIME pa_s=[expr {{[clock seconds]-$t0}}]"
mem pa
set t0 [clock seconds]
if {{[catch {{source /work/pdn.tcl; pdngen}} err]}} {{ puts "OT_PDN FAIL $err" }} else {{
  set nsw 0; foreach net [[ord::get_db_block] getNets] {{ foreach sw [$net getSWires] {{ incr nsw [llength [$sw getWires]] }} }}
  puts "OT_PDN PASS special_shapes=$nsw" }}
puts "OT_TIME pdn_s=[expr {{[clock seconds]-$t0}}]"
mem pdn
foreach net {{VDD VSS}} {{ if {{[catch {{check_power_grid -net $net}} err]}} {{ puts "OT_PGCHECK $net FAIL $err" }} else {{ puts "OT_PGCHECK $net PASS" }} }}
write_db /work/floorplan_pdn.odb
""")
    man = dict(case='a', instances=len(m['insts']), pins=npins, nets=sum(b[2] for b in m['buses']),
               masters=len(M) + 1)
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


# ------------------------------------------------------------------------------------------------ case (b): bundled GRT
def case_grt(m, work, k, tag, iters=50):
    from chip_assembly import v41_die as VD
    work.mkdir(parents=True, exist_ok=True)
    M = masters(m, k)
    pw = port_widths(m, k)
    lefs, npins = [], 0
    for name, mst in M.items():
        wmap = {p: pw.get((name, p), 0) for p in mst.order}
        txt, n = lef_text(mst, k, wmap)
        lefs.append(txt)
        npins += n
    (work / 'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs) + 'END LIBRARY\n')
    (work / 'tech.lef').write_text(VD.bundled_tech_lef(k))
    mm = dict(m)
    mm['buses'] = [b for b in m['buses'] if b[1] != 'tap']          # abutting taps: zero-length, pin access only
    write_netlist(mm, k, work / 'die.v')
    die = m['die']
    tracks = []
    for name, d, p, wd, sp, off in VD.ASAP7_LAYERS:
        tracks.append(f'make_tracks {name} -x_offset {off * k:.3f} -x_pitch {p * k:.3f} -y_offset {off * k:.3f} -y_pitch {p * k:.3f}')
    o = {'R0': 'R0', 'MY': 'MY', 'MX': 'MX'}
    place = [f'place_inst -name {it.name} -location {{{it.x:.3f} {it.y:.3f}}} -orientation {o[it.orient]} -status FIRM'
             for it in m['insts']]
    adj = []
    for ln in ('M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'):
        # corridor gate constraint (3): no long haul on M2-M5 (pins on M4/M5 are reached by vias at the pin gcell)
        adj.append(f'set_global_routing_layer_adjustment {ln} {1.0 if ln in ("M2", "M3", "M4", "M5") else VIA_OBS + 2 * REGION_PG["tile_field"]:.4f}')
    for r in m['regions']:
        if r['kind'] == 'corridor' and CORR_M9_ADJ is not None:
            x0, y0, x1, y1 = r['rect']
            adj.append(f'set_global_routing_region_adjustment {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer M9 '
                       f'-adjustment {CORR_M9_ADJ:.4f}')
        if r['kind'] in ('tile_field', 'corridor', 'channel', 'phy'):
            continue
        a = VIA_OBS + 2 * REGION_PG[r['kind']]
        x0, y0, x1, y1 = r['rect']
        for ln in ('M8', 'M9'):     # M6-M7 inside these regions are under macro OBS (GRT underflows there)
            adj.append(f'set_global_routing_region_adjustment {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {ln} -adjustment {a:.4f}')
    tcl = f"""# case (b): bundled (k = {k}) global route of every die-level net
proc mem {{tag}} {{ set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {{VmRSS:\\s+(\\d+)}} $s -> r; puts "OTMEM $tag [expr {{$r/1024}}] MB [clock seconds]" }}
read_lef /work/tech.lef
read_lef /work/elements.lef
read_verilog /work/die.v
link_design qfd_die
initialize_floorplan -die_area {{0 0 {die['w']:.3f} {die['h']:.3f}}} -core_area {{0 0 {die['w']:.3f} {die['h']:.3f}}} -site bsite
{chr(10).join(tracks)}
{chr(10).join(place)}
mem placed
{chr(10).join(adj)}
set_routing_layers -signal M2-M9
set t0 [clock seconds]
global_route -verbose -allow_congestion -congestion_iterations {iters} -congestion_report_file /work/grt_congestion.rpt
puts "OT_TIME grt_s=[expr {{[clock seconds]-$t0}}]"
mem grt
report_wire_length -net * -global_route -file /work/wirelength.csv
write_guides /work/route.guide
"""
    tcl += r"""
set blk [ord::get_db_block]
set out [open /work/gcell_usage.txt w]
set grid [$blk getGCellGrid]
set gx [$grid getGridX]; set gy [$grid getGridY]
puts $out "GRIDX [join $gx ,]"
puts $out "GRIDY [join $gy ,]"
set tech [ord::get_db_tech]
foreach ln {M2 M3 M4 M5 M6 M7 M8 M9} {
  set layer [$tech findLayer $ln]
  set nx [llength $gx]; set ny [llength $gy]
  for {set j 0} {$j < $ny} {incr j 4} {
    set row {}
    for {set i 0} {$i < $nx} {incr i 4} {
      set cap 0; set use 0
      for {set jj $j} {$jj < min($j+4,$ny)} {incr jj} {
        for {set ii $i} {$ii < min($i+4,$nx)} {incr ii} {
          set cap [expr {$cap + [$grid getCapacity $layer $ii $jj]}]
          set use [expr {$use + [$grid getUsage $layer $ii $jj]}]
        }
      }
      lappend row "$cap/$use"
    }
    puts $out "L $ln $j [join $row { }]"
  }
}
close $out
mem done
"""
    (work / 'run.tcl').write_text(tcl)
    man = dict(case='b', tag=tag, bundle_k=k, congestion_iterations=iters, instances=len(m['insts']), bundle_pins=npins,
               bundle_nets=sum(max(1, math.ceil(b[2] / k)) for b in mm['buses']),
               wires=sum(b[2] for b in mm['buses']), tree_mode=m['tree_mode'],
               adjustment=dict(base_M4_M9=VIA_OBS + 2 * REGION_PG['tile_field'], M2_M3=ORFS_LOW_ADJ,
                               regions={k_: VIA_OBS + 2 * v for k_, v in REGION_PG.items()}))
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


# ------------------------------------------------------------------------------------------------ case (c): IR window
WINDOWS = {
    # name: (x0, y0, x1, y1) chosen from the geometry at build time
    'tile_field': lambda g: (g['x_arr_w'] + 8 * TILE_SLOT[0], g['row_y'][2], g['x_arr_w'] + 16 * TILE_SLOT[0], g['row_y'][4]),
    'shoreline_w': lambda g: (g['x_wband'], g['stack_cy'][0] - 1300, g['x_arr_w'] + 4 * TILE_SLOT[0], g['stack_cy'][0] + 1300),
    'spine_hub': lambda g: (g['x_spine'] - 2 * TILE_SLOT[0], g['mid'] - 1300, g['x_arr_e'] + 2 * TILE_SLOT[0], g['mid'] + 1300),
    # r17: a full band-slab stack (bands 1 W/E: 8 routed port groups each) at its measured density
    'spine_slab': lambda g: (g['x_spine'] - 2 * TILE_SLOT[0], g['row_y'][6] - 1300, g['x_arr_e'] + 2 * TILE_SLOT[0],
                             g['row_y'][6] + 1300),
}
# r17: measured per-instance power density (W/mm2) by master prefix, overriding the region density under the
# instance (empty = the b3r16 region densities everywhere)
INST_W_PER_MM2 = {}
BUMP_PITCH, BUMP_SIZE = 45.0, 20.0          # v41_die_assembly CONST bump_pitch_um 45 (published 25-55), contact 2 x 10 um
POWER_BUMP_FRACTION = 0.25                  # v41_die_assembly CONST power_bump_fraction (assumed)
VDD_V = 0.7


def region_at(m, x, y):
    best = None
    for r in m['regions']:
        a, b, c, e = r['rect']
        if a <= x < c and b <= y < e:
            if r['kind'] in ('corridor', 'channel', 'strip', 'ctrl', 'phy', 'io'):
                return r['kind']
            best = r['kind']
    return best or 'tile_field'


def case_ir(m, work, window, peak=True, cov_scale=1.0, bump_pad=False, vdd_pitch=None, align=False, signal_bumps_phy=False):
    """cov_scale multiplies every region's M8/M9 coverage; bump_pad adds a 20 x 20 um M9 landing pad at every bump
    site (the UBM/AP landing any bump has: ASAP7 has no AP/RDL layer, so without it the bump contacts only the
    0.48 um stripes under it); sources are explicit per-net bump sites (VSS interleaved half a pitch off VDD)."""
    work.mkdir(parents=True, exist_ok=True)
    g = m['geo']
    x0, y0, x1, y1 = [round(v, 3) for v in WINDOWS[window](g)]
    x0, y0 = dn(x0, GX), dn(y0, GY)
    W, H = round(x1 - x0, 3), round(y1 - y0, 3)
    # straps: per region column/row segments; M9 vertical stripes at the pitch of the region under them, M8 horizontal
    vp = vdd_pitch or BUMP_PITCH / math.sqrt(POWER_BUMP_FRACTION)

    def pitch(cov):
        raw = dn(0.48 / (cov * cov_scale), 0.160)
        if not align:
            return raw
        # bump-aligned: the largest pitch <= raw that puts an odd number of stripe pitches in a bump pitch, so a
        # VDD stripe runs through every VDD bump column/row and a VSS stripe (half a pitch off) through every VSS one
        n = math.ceil(vp / raw - 1e-9)
        n += (n % 2 == 0)
        return round(vp / n, 4)
    sites = {'VDD': [], 'VSS': []}
    for net, off in (('VDD', vp / 2), ('VSS', 0.0)):
        yy = off if off > 0 else vp
        while yy < H - 1.0:
            xx = off if off > 0 else vp
            while xx < W - 1.0:
                if not (signal_bumps_phy and region_at(m, x0 + xx, y0 + yy) in ('phy', 'io')):
                    sites[net].append((round(xx, 3), round(yy, 3)))
                xx += vp
            yy += vp
    cell = 20.0
    nx, ny = int(W // cell), int(H // cell)
    # load tiles: 20 um cells, power = region density x area (peak in-phase)
    # straps: each region's own M8/M9 lattice (0.48 um stripes at the pitch of its coverage), cut at the region
    # boundaries; vias at every same-net crossing inside the region.  The PHY region has no die grid (own IP grid):
    # it takes the strip lattice so its load is fed (conservative for the strip: PHY current shares its mesh).
    R = 5.0
    rx, ry = int(math.ceil(W / R)), int(math.ceil(H / R))
    raster = [[0.0] * rx for _ in range(ry)]
    for j in range(ry):
        for i in range(rx):
            kd = region_at(m, x0 + (i + 0.5) * R, y0 + (j + 0.5) * R)
            raster[j][i] = pitch(REGION_PG[kd] or REGION_PG['strip'])
    pitches = sorted({v for row in raster for v in row})

    def pat(xx, yy):
        i, j = min(rx - 1, max(0, int(xx / R))), min(ry - 1, max(0, int(yy / R)))
        return raster[j][i]

    def lines(p, span):
        out = []
        v = ((vp / 2) % p) if align else 1.0
        while v < span - 0.5:
            out.append(('VDD', round(v, 3)))
            if v + p / 2 < span - 0.5:
                out.append(('VSS', round(v + p / 2, 3)))
            v += p
        return out

    def runs(fixed, axis, p):
        """intervals along the other axis where the raster pitch is p, on the line at 'fixed'"""
        segs, start = [], None
        n = ry if axis == 'y' else rx
        for t in range(n + 1):
            ok = t < n and (pat(fixed, (t + 0.5) * R) if axis == 'y' else pat((t + 0.5) * R, fixed)) == p
            if ok and start is None:
                start = t * R
            if not ok and start is not None:
                segs.append((start, min(t * R, H if axis == 'y' else W)))
                start = None
        return segs
    s9, s8, vias = [], [], []
    for p in pitches:
        xl, yl = lines(p, W), lines(p, H)
        for net, xx in xl:
            for (a_, b_) in runs(xx, 'y', p):
                s9.append((net, 'M9', xx - 0.24, a_, xx + 0.24, b_))
        for net, yy in yl:
            for (a_, b_) in runs(yy, 'x', p):
                s8.append((net, 'M8', a_, yy - 0.24, b_, yy + 0.24))
        ys_by_net = {'VDD': [y for n_, y in yl if n_ == 'VDD'], 'VSS': [y for n_, y in yl if n_ == 'VSS']}
        for net, xx in xl:
            for yy in ys_by_net[net]:
                if pat(xx, yy) == p:
                    vias.append((net, xx, yy))
    # loads: 20 um current cells at the region density; each cell's VDD / VSS pin is an M8 rect over one of the
    # region's own M8 stripes inside it (a PSM terminal: the pin overlaps the grid shape of its net)
    by_net = {'VDD': {}, 'VSS': {}}
    for (nn, ly, a_, b_, c_, e_) in s8:
        by_net[nn].setdefault(round((b_ + e_) / 2, 3), []).append((a_, c_))
    ys_sorted = {nn: sorted(v) for nn, v in by_net.items()}
    comps, power, lefs, kinds = [], {}, {}, {}
    ovr = [(it, d_) for it in m['insts'] for pre, d_ in INST_W_PER_MM2.items() if it.master.startswith(pre)
           and it.x < x1 and it.x + it.w > x0 and it.y < y1 and it.y + it.h > y0]
    import bisect
    missing = 0
    for j in range(ny):
        for i in range(nx):
            cx0, cy0 = i * cell, j * cell
            pins = {}
            for nn in ('VDD', 'VSS'):
                ys = ys_sorted[nn]
                lo = bisect.bisect_left(ys, cy0 + 0.3)
                best = None
                for t in range(lo, len(ys)):
                    yy = ys[t]
                    if yy > cy0 + cell - 0.3:
                        break
                    if any(r0 <= cx0 + 0.6 and r1 >= cx0 + cell - 0.6 for r0, r1 in by_net[nn][yy]):
                        if best is None or abs(yy - (cy0 + cell / 2)) < abs(best - (cy0 + cell / 2)):
                            best = yy
                pins[nn] = best
            if pins['VDD'] is None or pins['VSS'] is None:
                missing += 1
                continue
            key = (round(pins['VDD'] - cy0, 3), round(pins['VSS'] - cy0, 3))
            mn = f'qir_load_{int(key[0] * 1000)}_{int(key[1] * 1000)}'
            if mn not in lefs:
                pv, ps_ = key
                lefs[mn] = '\n'.join([f'MACRO {mn}', '  CLASS BLOCK ;', f'  FOREIGN {mn} 0 0 ;', '  SYMMETRY X Y ;',
                                       f'  SIZE {cell:.3f} BY {cell:.3f} ;',
                                       '  PIN VDD', '    DIRECTION INOUT ;', '    USE POWER ;', '    PORT', '      LAYER M8 ;',
                                       f'        RECT 0.600 {pv - 0.24:.3f} {cell - 0.6:.3f} {pv + 0.24:.3f} ;', '    END', '  END VDD',
                                       '  PIN VSS', '    DIRECTION INOUT ;', '    USE GROUND ;', '    PORT', '      LAYER M8 ;',
                                       f'        RECT 0.600 {ps_ - 0.24:.3f} {cell - 0.6:.3f} {ps_ + 0.24:.3f} ;', '    END', '  END VSS',
                                       '  OBS'] + [f'    LAYER M{q} ;\n      RECT 0 0 {cell:.3f} {cell:.3f} ;' for q in range(2, 8)] +
                                      ['  END', f'END {mn}', ''])
            kd = region_at(m, x0 + cx0 + cell / 2, y0 + cy0 + cell / 2)
            dens = REGION_W_PER_MM2[kd] if peak else REGION_W_PER_MM2[kd] * 0.25
            if INST_W_PER_MM2:
                px, py = x0 + cx0 + cell / 2, y0 + cy0 + cell / 2
                for it, dd in ovr:
                    if it.x <= px < it.x + it.w and it.y <= py < it.y + it.h:
                        dens = dd if peak else dd * 0.25
                        kd = f'inst:{it.master}'
                        break
            if signal_bumps_phy and kd in ("phy", "io"):
                dens = 0.0   # the PHY/IO macro is fed by its own supply bumps among its signal bumps
            n = f'L_{i}_{j}'
            comps.append((n, mn, cx0, cy0))
            power[n] = dens * cell * cell / 1e6
            kinds[n] = kd
    nm = 'loads'
    lefs = {nm: 'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs.values()) + 'END LIBRARY\n'}
    d = ['VERSION 5.8 ;', 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', 'DESIGN qir ;', 'UNITS DISTANCE MICRONS 1000 ;',
         f'DIEAREA ( 0 0 ) ( {round(W * 1000)} {round(H * 1000)} ) ;']
    # vias M8-M9 at every same-net crossing (0.48 x 0.48)
    d += ['VIAS 1 ;', '- via89 + RECT M8 ( -240 -240 ) ( 240 240 ) + RECT V8 ( -200 -200 ) ( 200 200 ) '
          '+ RECT M9 ( -240 -240 ) ( 240 240 ) ;', 'END VIAS']
    d.append(f'COMPONENTS {len(comps)} ;')
    d += [f'- {n} {mst} + FIXED ( {round(x * 1000)} {round(y * 1000)} ) N ;' for n, mst, x, y in comps]
    d.append('END COMPONENTS')
    d.append('SPECIALNETS 2 ;')
    nvia = len(vias)
    for net in ('VDD', 'VSS'):
        L = [f'- {net} ( * {net} ) + USE ' + ('POWER' if net == 'VDD' else 'GROUND')]
        first = True
        for (nn, ly, a_, b_, c_, e_) in s9 + s8:
            if nn != net:
                continue
            if ly == 'M9':
                xm = round((a_ + c_) / 2 * 1000)
                seg = f'{ly} 480 + SHAPE STRIPE ( {xm} {round(b_ * 1000)} ) ( * {round(e_ * 1000)} )'
            else:
                ym = round((b_ + e_) / 2 * 1000)
                seg = f'{ly} 480 + SHAPE STRIPE ( {round(a_ * 1000)} {ym} ) ( {round(c_ * 1000)} * )'
            L.append(('  + ROUTED ' if first else '    NEW ') + seg)
            first = False
        for (nn, xx, yy) in vias:
            if nn == net:
                L.append(f'    NEW M8 0 ( {round(xx * 1000)} {round(yy * 1000)} ) via89')
        if bump_pad:
            for (xx, yy) in sites[net]:
                L.append(f'    NEW M9 20000 ( {round(xx * 1000)} {round((yy - 10) * 1000)} ) ( * {round((yy + 10) * 1000)} )')
        L[-1] += ' ;'
        d += L
    d.append('END SPECIALNETS')
    d += ['END DESIGN', '']
    txt = '\n'.join(x for x in d if x != '')
    (work / 'top.def').write_text(txt)
    for n, t in lefs.items():
        (work / f'{n}.lef').write_text(t)
    vdd_pitch = vp
    for net in ('VDD', 'VSS'):
        (work / f'vsrc_{net}.loc').write_text(''.join(f'{x:.3f}, {y:.3f}, {BUMP_SIZE:.1f}, {VDD_V if net == "VDD" else 0.0}\n'
                                                     for x, y in sites[net]))
    tcl = f"""
set t0 [clock seconds]
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/{nm}.lef
read_def /work/top.def
set block [ord::get_db_block]
add_global_connection -net {{VDD}} -inst_pattern {{.*}} -pin_pattern {{^VDD$}} -power
add_global_connection -net {{VSS}} -inst_pattern {{.*}} -pin_pattern {{^VSS$}} -ground
global_connect
puts "OT_STAT insts=[llength [$block getInsts]]"
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source {PLAT}/setRC.tcl
set_pdnsim_source_settings -bump_dx {int(round(vdd_pitch))} -bump_dy {int(round(vdd_pitch))} -bump_size {int(BUMP_SIZE)} -bump_interval 1
{chr(10).join(f'set_pdnsim_inst_power -inst {n} -power {p:.9f}' for n, p in power.items())}
foreach net {{VDD VSS}} {{
  if {{[catch {{check_power_grid -net $net -error_file /work/pg_err_$net.rpt}} err]}} {{ puts "OT_PSM net=$net status=FAIL err=$err" }} else {{ puts "OT_PSM net=$net status=PASS" }}
}}
foreach net {{VDD VSS}} {{
  set_pdnsim_net_voltage -net $net -voltage [expr {{$net eq "VDD" ? {VDD_V} : 0.0}}]
  if {{[catch {{analyze_power_grid -net $net -vsrc /work/vsrc_$net.loc -voltage_file /work/ir_$net.rpt -error_file /work/ir_err_$net.rpt}} err]}} {{
    puts "OT_IR net=$net status=FAIL err=$err" }} else {{ puts "OT_IR net=$net status=PASS" }}
}}
puts "OT_TIME psm_s=[expr {{[clock seconds]-$t0}}]"
exit
"""
    (work / 'run.tcl').write_text(tcl)
    tot = {}
    for n, p in power.items():
        tot[kinds[n]] = tot.get(kinds[n], 0.0) + p
    meta = dict(case='c', window=window, window_um=[x0, y0, x1, y1], size_um=[W, H], cell_um=cell, loads=len(comps),
                power_w_by_region={k_: round(v, 4) for k_, v in tot.items()}, power_w=round(sum(power.values()), 4), cells_without_both_rails=missing,
                peak=peak, cov_scale=cov_scale, bump_pad=bump_pad, align=align, signal_bumps_phy=signal_bumps_phy, bump_sites=len(sites['VDD']), stripes=dict(M9=len(s9), M8=len(s8), vias=nvia, width_um=0.48,
                                        pitch_by_region={k_: pitch(v) for k_, v in REGION_PG.items() if v}),
                bumps=dict(array_pitch_um=BUMP_PITCH, power_fraction=POWER_BUMP_FRACTION, vdd_pitch_um=round(vdd_pitch, 2),
                           size_um=BUMP_SIZE, basis='tools/v41_die_assembly.py CONST (bump pitch published 25-55 um; '
                           'power fraction and contact assumed)'), vdd_v=VDD_V, budget_mv=35.0)
    (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
    (work / 'kinds.json').write_text(json.dumps(kinds))
    return meta


# ------------------------------------------------------------------------------------------------ case (d): clock
WIRE_MODELS = [  # name, ps per um, source
    ('asap7_ss_routed', 1.135, 'W15 SS routed 547-bit spans, BUFx4 repeaters: period = 261 ps + 1.135 ps/um '
                               '(tools/uarch_model.py SS_REACH_UM basis): upper bound for a clock trunk'),
    ('asap7_tt_routed_1mm', 0.605, 'configs/hardware/technology.json: ASAP7 post-route repeated wire at 1 mm spacing, '
                                   '605 ps/mm (TT)'),
    ('thick_metal_n5', 0.150, 'configs/hardware/technology.json latency.global_wire_delay_s_per_mm 150 ps/mm '
                              '(assumed thick top metal; no N5 wire routed)'),
]


def case_clock(m):
    """Top-level clock: H-tree to the 1,536 tiles + regions; insertion delay and OCV skew across the die."""
    g = m['geo']
    from v41_die_assembly import htree
    W, H = (g['x_eband'] - g['x_arr_w']) / 1000, (g['y_top'] - g['y0']) / 1000
    leaves = COLS * ROWS + 4 * 7 + 16
    lv = math.ceil(math.log2(leaves))
    total_mm, depth_mm = htree(W, H, lv)
    w, h = W, H
    segs = []
    for l in range(lv):
        seg = (w / 2 if l % 2 == 0 else h / 2)
        if l % 2 == 0:
            w /= 2
        else:
            h /= 2
        segs.append(seg / 2)            # htree() counts seg/2 a level on the root-to-leaf path
    below = [sum(segs[l:]) for l in range(lv)]
    models = []
    for name, ps_um, src in WIRE_MODELS:
        ins = depth_mm * 1000 * ps_um
        rows = []
        for derate in (0.02, 0.05, 0.08):
            sk = [round(2 * derate * b * 1000 * ps_um, 1) for b in below]
            fit25 = next((l for l in range(lv) if sk[l] <= 25.0), None)
            fit60 = next((l for l in range(lv) if sk[l] <= 60.0), None)
            rows.append(dict(ocv_derate=derate, skew_ps_by_divergence_level=sk, root_divergence_skew_ps=sk[0],
                             first_level_within_25ps=fit25, first_level_within_60ps=fit60,
                             subtree_extent_mm_within_25ps=round(2 * below[fit25], 3) if fit25 is not None else None,
                             subtree_extent_mm_within_60ps=round(2 * below[fit60], 3) if fit60 is not None else None))
        models.append(dict(model=name, ps_per_um=ps_um, source=src, insertion_ns=round(ins / 1000, 2),
                           insertion_periods_1p2GHz=round(ins / 833.3, 1), ocv=rows))
    tile_hop_ps = TILE_SLOT[1] * WIRE_MODELS[0][1]
    return dict(
        schema='opentallas.qwen-rom-fulldie.clock.v1', tool_sha256=sha('tools/qwen_rom_fulldie.py'),
        array_mm=[round(W, 3), round(H, 3)], leaves=leaves, levels=lv, htree_total_mm=round(total_mm, 1),
        root_to_leaf_mm=round(depth_mm, 3), segment_root_to_leaf_mm=[round(x, 3) for x in segs],
        nonshared_mm_by_divergence_level=[round(x, 3) for x in below], models=models,
        skew_rule='two leaves whose paths diverge at H-tree level l see OCV skew = 2 x derate x insertion of the '
                  'non-shared path (levels l..L-1); budget = the 60 ps setup / 25 ps hold uncertainty, no extra margin',
        corridor_forwarded=dict(tile_hop_um=TILE_SLOT[1], clock_arrival_step_ps_per_tile_ss=round(tile_hop_ps, 1),
                                note='the corridor carries 64 clock tracks: a clock forwarded with the bus arrives one '
                                     'tile-hop wire delay later at each tile row; forward-flowing corridor data is '
                                     'source-synchronous, but paths against the flow or across columns (ready, ME tree '
                                     'edges, block words) see the offset'),
        root_split=('physically adjacent leaves on either side of the H-tree root split (array mid-line and the spine) '
                    'diverge at the root: their skew is the level-0 figure; every bus crossing those lines (head chain, '
                    'block words, links) needs a FIFO, a mesochronous retimer, or a clock mesh'),
    )


# ------------------------------------------------------------------------------------------------ records
def _log(work):
    f = work / 'run.log'
    return f.read_text(errors='replace') if f.is_file() else ''


def _exit(work):
    f = work / 'run.log.exit'
    return int(f.read_text().strip()) if f.is_file() and f.read_text().strip() else None


def _rss_mb(log):
    m = re.search(r'Maximum resident set size \(kbytes\): (\d+)', log)
    return round(int(m.group(1)) / 1024) if m else None


def _wall(log):
    m = re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)', log)
    return m.group(1) if m else None


def record_a(work):
    log = _log(work)
    out = dict(case='a', exit=_exit(work), wall=_wall(log), peak_rss_mb=_rss_mb(log),
               manifest=json.loads((work / 'manifest.json').read_text()))
    m = re.search(r'OT_LEGAL instances=(\d+) overlaps=(\d+) outside=(\d+)', log)
    out['legality'] = dict(instances=int(m.group(1)), overlaps=int(m.group(2)), outside=int(m.group(3))) if m else None
    moved = []
    for mm in re.finditer(r'OT_MTS_PLACE (\S+) (\S+) (\S+) requested \(([-\d.]+), ([-\d.]+)\) placed \(([-\d.]+), ([-\d.]+)\)', log):
        dx, dy = float(mm.group(6)) - float(mm.group(4)), float(mm.group(7)) - float(mm.group(5))
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            moved.append((mm.group(1), mm.group(2), round(dx, 3), round(dy, 3)))
    out['snap_moves'] = dict(count=len(moved), by_master={}, max_um=max((abs(a_) + abs(b_) for _, _, a_, b_ in moved), default=0.0))
    for _, mst, a_, b_ in moved:
        out['snap_moves']['by_master'][mst] = out['snap_moves']['by_master'].get(mst, 0) + 1
    m = re.search(r'OT_MACRO_TRACK_ASSERT (\S+)(?: label=\S+)? macros=(\d+) pins_checked=(\d+) offtrack=(\d+) max_offset_nm=([\d.]+) no_track_grid=(\d+)', log)
    out['track_assert'] = dict(verdict=m.group(1), macros=int(m.group(2)), pins_checked=int(m.group(3)), offtrack=int(m.group(4)),
                               max_offset_nm=float(m.group(5)), no_track_grid=int(m.group(6))) if m else None
    out['track_assert_offenders'] = re.findall(r'OT_MACRO_TRACK_ASSERT offtrack (\S+)', log)[:40]
    pa = {}
    for key, pat in (('unique_instances', r'#unique instances\s*=\s*(\d+)'), ('scanned_instances', r'#scanned instances\s*=\s*(\d+)'),
                     ('inst_terms_valid_planar', r'#instTermValidViaApCnt\s*=\s*(\d+)'),
                     ('macro_valid_planar_ap', r'#macroValidPlanarAp\s*=\s*(\d+)'), ('macro_valid_via_ap', r'#macroValidViaAp\s*=\s*(\d+)'),
                     ('macro_no_ap', r'#macroNoAp\s*=\s*(\d+)')):
        mm = re.search(pat, log)
        if mm:
            pa[key] = int(mm.group(1))
    pa['status'] = 'DONE' if 'OT_PA DONE' in log else ('FAIL' if 'OT_PA FAIL' in log else 'not reached')
    pa['no_access_errors'] = len(re.findall(r'DRT-0073|No access point', log))
    pa['examples'] = re.findall(r'\[(?:WARNING|ERROR) DRT-00(?:73|74|83)\].*', log)[:20]
    out['pin_access'] = pa
    out['errors'] = re.findall(r'\[ERROR [^\]]+\].*|^Error: .*', log, re.M)[:10]
    return out


def record_b(work, m):
    from chip_assembly import v41_die as VD
    log = _log(work)
    rec = dict(case='b', exit=_exit(work), wall=_wall(log), peak_rss_mb=_rss_mb(log),
               manifest=json.loads((work / 'manifest.json').read_text()))
    p = VD.parse_log(log)
    rec['grt'] = {k_: v for k_, v in p.items() if k_ not in ('mem',)}
    mm = re.search(r'OT_TIME grt_s=(\d+)', log)
    rec['grt_s'] = int(mm.group(1)) if mm else None
    k = rec['manifest']['bundle_k']
    cls_of = {f'n_{bid}': (c, bits) for bid, c, bits, _ in m['buses']}
    lens = VD.parse_wirelength(work / 'wirelength.csv')
    per = {}
    for net, um in lens.items():
        base = net.split('[')[0]
        c, bits = cls_of.get(base, ('?', 0))
        e = per.setdefault(c, dict(bundle_nets=0, bundle_um=0.0, max_um=0.0))
        e['bundle_nets'] += 1
        e['bundle_um'] += um
        e['max_um'] = max(e['max_um'], um)
    for c, e in per.items():
        e['wire_m'] = round(e['bundle_um'] * k / 1e6, 1)
        e['bundle_um'] = round(e['bundle_um'], 1)
        e['max_um'] = round(e['max_um'], 1)
    rec['wire_by_class'] = per
    cm = VD.congestion_map(work / 'gcell_usage.txt', work / 'gcell_base.txt') if (work / 'gcell_base.txt').is_file() else {}
    rec['congestion_windows'] = cm.get('summary')
    # raw usage/capacity windows (no baseline run): windows above 0.7 and 1.0 of capacity, per layer
    u = {}
    f = work / 'gcell_usage.txt'
    if f.is_file():
        for line in f.read_text().splitlines():
            if not line.startswith('L '):
                continue
            fs = line.split()
            ln = fs[1]
            e = u.setdefault(ln, dict(windows=0, over_0p7=0, over_1=0, max=0.0))
            for cell in fs[3:]:
                cap, use = (float(x) for x in cell.split('/'))
                if cap <= 0:
                    continue
                r = use / cap
                e['windows'] += 1
                e['over_0p7'] += r > 0.7
                e['over_1'] += r > 1.0
                e['max'] = max(e['max'], round(r, 3))
    rec['gcell_window_usage'] = u
    rec['errors'] = re.findall(r'\[ERROR [^\]]+\].*|^Error: .*', log, re.M)[:10]
    return rec


def record_c(work):
    log = _log(work)
    meta = json.loads((work / 'manifest.json').read_text())
    out = dict(case='c', exit=_exit(work), wall=_wall(log), peak_rss_mb=_rss_mb(log), meta=meta)
    drops = re.findall(r'Worstcase IR drop: ([\d.e+-]+) V', log)
    avgs = re.findall(r'Average IR drop  : ([\d.e+-]+) V', log)
    if len(drops) >= 2:
        out['worst_mv'] = dict(VDD=round(float(drops[0]) * 1e3, 2), VSS=round(float(drops[1]) * 1e3, 2))
        out['avg_mv'] = dict(VDD=round(float(avgs[0]) * 1e3, 2), VSS=round(float(avgs[1]) * 1e3, 2))
        out['rail_to_rail_worst_mv'] = round(out['worst_mv']['VDD'] + out['worst_mv']['VSS'], 2)
        out['budget_mv'] = meta['budget_mv']
        out['pass'] = out['rail_to_rail_worst_mv'] <= meta['budget_mv']
    # worst per region kind (instance voltages; VDD drop = VDD - v, VSS bounce = v)
    kf = work / 'kinds.json'
    if kf.is_file():
        kinds = json.loads(kf.read_text())
        per = {}
        for net in ('VDD', 'VSS'):
            f = work / f'ir_{net}.rpt'
            if not f.is_file():
                continue
            for line in f.read_text().splitlines()[1:]:
                fs = line.split(',')
                if len(fs) < 6 or fs[0] not in kinds:
                    continue
                v = float(fs[5])
                d = (VDD_V - v) if net == 'VDD' else v
                x, y = float(fs[3]), float(fs[4])
                W_, H_ = meta['size_um']
                vp = meta['bumps']['vdd_pitch_um']
                interior = vp <= x <= W_ - vp and vp <= y <= H_ - vp
                e = per.setdefault(kinds[fs[0]], {})
                e[net] = round(max(e.get(net, 0.0), d * 1e3), 2)
                if interior:
                    e[net + '_interior'] = round(max(e.get(net + '_interior', 0.0), d * 1e3), 2)
                    wi = out.setdefault('worst_interior_mv', {})
                    wi[net] = round(max(wi.get(net, 0.0), d * 1e3), 2)
        out['worst_mv_by_region'] = per
        wi = out.get('worst_interior_mv')
        if wi and len(wi) == 2:
            out['rail_to_rail_interior_mv'] = round(wi['VDD'] + wi['VSS'], 2)
            out['pass_interior'] = out['rail_to_rail_interior_mv'] <= meta['budget_mv']
            out['interior_rule'] = 'cells at least one VDD bump pitch from every window edge (the die continues)'
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'real', 'grt', 'ir', 'clock', 'record'])
    ap.add_argument('--work', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--tag', default='base')
    ap.add_argument('--iters', type=int, default=50, help='GRT congestion iterations')
    ap.add_argument('--tree', default='central', choices=['central', 'banded'])
    ap.add_argument('--window', default='tile_field', choices=list(WINDOWS))
    ap.add_argument('--avg', action='store_true', help='IR at 25%% of peak density')
    ap.add_argument('--cov-scale', type=float, default=1.0)
    ap.add_argument('--bump-pad', action='store_true')
    ap.add_argument('--vdd-pitch', type=float)
    ap.add_argument('--align', action='store_true', help='bump-aligned strap lattices')
    ap.add_argument('--phy-signal-bumps', action='store_true', help='no power bumps over the PHY / IO regions')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--case', choices=['a', 'b', 'c'])
    a = ap.parse_args(argv)
    m = build(tree_mode=a.tree)
    if a.mode == 'plan':
        out = ROOT / OUT
        out.mkdir(parents=True, exist_ok=True)
        rec = plan_record(m)
        rec['instances_list_sha256'] = hashlib.sha256(json.dumps([it.d() for it in m['insts']]).encode()).hexdigest()
        (out / 'floorplan.json').write_text(json.dumps(rec, indent=1) + '\n')
        svg(m, out / 'floorplan.svg')
        write_def_floorplan(m, out / 'floorplan.def')
        write_sdc(out / 'domains.sdc')
        write_pdn_tcl(out / 'pdn.tcl')
        print(json.dumps(dict(die=rec['die'], delta=rec['delta_vs_r2'], instances=rec['instances'], classes=rec['bus_classes'],
                              notes=rec['notes']), indent=1))
        return 0
    if a.mode == 'clock':
        rec = case_clock(m)
        out = a.out or ROOT / OUT / 'clock_trunk.json'
        out.write_text(json.dumps(rec, indent=1) + '\n')
        for mo in rec['models']:
            print(mo['model'], mo['insertion_ns'], [(r['ocv_derate'], r['root_divergence_skew_ps'], r['subtree_extent_mm_within_60ps'], r['subtree_extent_mm_within_25ps']) for r in mo['ocv']])
        return 0
    if a.mode == 'record':
        cases = {}
        root = a.work
        for d in sorted(root.iterdir()):
            if not (d / 'manifest.json').is_file():
                continue
            man = json.loads((d / 'manifest.json').read_text())
            try:
                if man.get('case') == 'a':
                    cases[d.name] = record_a(d)
                elif man.get('case') == 'b':
                    mb = build(tree_mode=man.get('tree_mode', 'central'))
                    cases[d.name] = record_b(d, mb)
                elif man.get('case') == 'c':
                    cases[d.name] = record_c(d)
            except Exception as e:  # noqa: BLE001  (a partial case is recorded, never dropped)
                cases[d.name] = dict(error=repr(e))
        rec = dict(schema='opentallas.qwen-rom-fulldie.feasibility.v1', tool_sha256=sha('tools/qwen_rom_fulldie.py'),
                   cases=cases)
        out = a.out or ROOT / OUT / 'feasibility.json'
        out.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n')
        print(json.dumps({k_: {kk: v.get(kk) for kk in ('exit', 'rail_to_rail_worst_mv', 'legality', 'track_assert', 'grt_s')}
                          for k_, v in cases.items()}, indent=1))
        return 0
    if a.work is None:
        ap.error('--work required')
    work = a.work.resolve()
    if a.mode == 'real':
        print(json.dumps(case_real(m, work)))
    elif a.mode == 'grt':
        print(json.dumps(case_grt(m, work, a.k, a.tag, a.iters)))
    elif a.mode == 'ir':
        print(json.dumps(case_ir(m, work, a.window, peak=not a.avg, cov_scale=a.cov_scale, bump_pad=a.bump_pad,
                                 vdd_pitch=a.vdd_pitch, align=a.align, signal_bumps_phy=a.phy_signal_bumps)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
