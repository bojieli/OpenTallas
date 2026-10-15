"""Qwen3-8B ROM full die, b3 r2: congestion closure source (default off; the b2 generator is not edited).

Builds on the b3 selection of tools/qwen_rom_fulldie_b3.py (codex/qwen-fulldie-pg-repair-20261003):
  F1  one pipelined reset wire per tile column instead of 64 (corridor 637 -> 388 bits),
  F2  the 379-bit column instruction as two 190-bit beats into a 2-deep column FIFO (tap 511 -> 325 bits),
  VCH the spine vertical link channel 174.096 -> 260.064 um,
  (c) the lower (south) hub<->stack link split over both edges of the channel,
and adds, in this file:
  pins   real signal interfaces for the ten abstracts b3_launch_r2 refused as signal-empty
         (constants_sequencer, port_tiles_6, scale_rom_0..7), taken from the RTL port lists:
           scale ROM  per result-port group: scale_gre 1 + scale_addr AW 24 (port -> ROM), scale_q W*16 = 256
                      (ROM -> port), shared scale_re 1     (rtl/hdc/ot_qwen_me_array_w12.sv ot_qwen_me_spine_w12)
           constant ROM  crom_re SW + crom_addr SW*AW (SU -> ROM), crom_q SW*64 (ROM -> SU), SW = 64
                      (rtl/hdc/ot_hdc_core_vector_weight.sv)
           sequencer  ME instruction ib 379 + go + valid/ready to the head-chain x root (vector memory),
                      the non-ME ISA fields (tools/hdc_isa.FIELDS) + valid/ready to SU64, collective descriptor
                      64 + start/done (rtl/rom/ot_rom_tp_seq.sv), ME/SU done back to the sequencer
         and the port-group -> slab map by area (slab 6 holds the overflow groups of bands 2 and 5, whose words
         the b2/b3 generator sent to slabs 2 and 5 regardless of capacity);
  meso   clock regions of decision C (origin/main d99237f66, rom_die_clocking_decision_20261003): one region per
         4 x 4-tile block, per spine band, per strip third, per IO block; FIFO slots that carry the decision's
         2.53 mm2 (tile-tap FIFOs inside a taller station frame, block-word FIFOs in the port slabs, strip-return
         FIFOs in a taller strip FIFO frame);
  band   (variant) port and scale slabs re-packed next to the block-row band they serve.  The b2/b3 packing puts
         all six band port slabs south of the hub, so bands 3-5's 24,576 block-word bits run 10-25 mm down the
         spine: 35,840 vertical bits cross y = 8.8 mm in the spine against 2,112 link bits (cut census below).
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as F          # noqa: E402
import qwen_rom_fulldie_pg_r3 as PG   # noqa: E402

SCHEMA = 'opentallas.qwen-rom-fulldie.b3r2.v1'
CLOCKING = 'results/uarch/rom_die_clocking_decision_20261003.json @ d99237f66'
# decision C FIFO inventory (derivation.area.qwen.C): 3,332,608 bits -> 2.53 mm2 (gross, depth 4)
FIFO_MM2_PER_BIT = 2.53 / 3332608
TAP_FIFO_BITS = 509 * 4            # one per tile tap (1,536)
BW_FIFO_BITS = 512 * 4             # one per block word (96)
# sys-takeover 2026-10-09 (registry qfd_native_collective_binding, opt-in --native-coll): the sequencer <-> collective
# path at the production engine widths through io_xfifo NCOLL (rtl/physical/ot_qwen_die_io_xfifo.sv): forward
# {tag32, mode, last, data512} 546 b + valid + credit = 548 b (seq_coll), return {err, rank2, last, data512} 516 b +
# valid + credit = 518 b (coll_seq).  Default off: the 64 + 2 descriptor word of r18-r21.
NATIVE_COLL = False
SEQ_COLL_BITS = (64 + 2, 546 + 2, 516 + 2)        # (r18-r21 descriptor, native forward, native return)
STRIP_FIFO_BITS = 544 * 4          # one per strip return (4)
# F2 station storage: 388 corridor flops + 379 assembly + one extra 190-bit beat entry, against 637 before
F2_STATION_EXTRA_BITS = 388 + 379 + 190 - 637
PORT_GROUPS, GROUPS_PER_BAND, BANDS = 96, 16, 6
# qwen-lane-band 2026-10-08: the W12 RTL's result-port groups (GT >> SMIN = 6,144 >> 7 = 48: 12 port elements x PQ 4),
# 8 per band (the band's 8 level-TCUT positions), 4 per band half.  PORT_GROUPS (96) counts the block words (16 block
# columns x 6 bands, level TCUT-1: two per result group) and keeps sizing their meso FIFOs; from r21m the slab's
# routed port-group elements are reserved per RESULT group (r17..r21f reserved one per block word: 96 against 48).
RTL_PORT_GROUPS = 48
SC_IN = 1 + 24                      # scale_gre + scale_addr, per group
SC_OUT = 16 * 16                    # scale_q W*16, per group
SW, AW = 64, 24
CROM_IN, CROM_OUT = SW + SW * AW, SW * 64
REGION_MAX_MM = 5.25


def _isa_bits():
    import hdc_isa as I
    me = sum(w for n, w in I.FIELDS if n.startswith('me_'))
    return sum(w for n, w in I.FIELDS), me


# ---- qwen-tp8 (results/arch/qwen_tp8_1012/SPEC.md sections 1, 2, 5): the TP8 track-A ROM die.  G = 3,072 lane groups
# = 768 qfd_tile_nk (the TP4 tile, unchanged) in 64 columns x 12 rows = 3 bands of 4 tile rows (TP4: 6); port groups
# 16 per band (48); the spine keeps its column; ROW_GAP um of routing channel between tile rows sizes the die to the
# spec outline (slot share <= 60 %, channels >= 35 %).  Opt-in (recipe tp8a); every other recipe is unchanged.
TP8 = None


def _band_tgt(v, rows, b):
    """y centre of band b's tile rows (tp8b F2: the centroid of the band's blocks, v.BAND_BLOCKS)."""
    bb = getattr(v, 'BAND_BLOCKS', None)
    if bb:
        ys = [rows[r0] + (rows[r0 + 3] + v.TILE_SLOT[1] - rows[r0]) / 2 for c0, r0 in bb[b]]
        return sum(ys) / len(ys)
    return (rows[4 * b] + rows[4 * b + 3] + v.TILE_SLOT[1]) / 2


def _tp8_globals(cfg):
    global PORT_GROUPS, BANDS, RTL_PORT_GROUPS, TP8
    TP8 = dict(cfg)
    BANDS = cfg['bands']
    PORT_GROUPS = GROUPS_PER_BAND * BANDS
    RTL_PORT_GROUPS = 8 * BANDS


def _tp8_base(v, cfg):
    v.ROWS = 4 * cfg['bands']
    v.NBANDS = cfg['bands']
    v.CH_ROWS = tuple(cfg['ch_rows'])
    v.ROW_GAP = cfg['row_gap']
    # TP8 per-die spine content: port groups halve (3 bands), scale rows 452,144 / 609,376 (SPEC section 1)
    sc = dict(port_tiles=0.5, scale_rom=452144 / 609376)
    v.SPINE_BLOCKS = [(n, a * sc.get(n, 1.0), d, s) for n, a, d, s in v.SPINE_BLOCKS]
    # IO band (SPEC section 3): the two-level collective (in-package pre-fold + owner-half select / all-gather around
    # the 4-rank fold) gets a 1.5x TP4 budget outline; the CDC cluster widens for the 3 SerDes word pairs
    v.IO_BLOCKS = [(n, a * (cfg.get('coll_scale', 1.5) if n == 'collective' else 1.0), d) for n, a, d in v.IO_BLOCKS]
    v.IOX_W = cfg.get('iox_w', 700.128)
    if cfg.get('f2'):
        _tp8b_base(v, cfg)
    if cfg.get('tile_body'):
        # contract v2 (SPEC 5, tile slot width): the GT 3,072 qfd_tile_nk cluster (ref_tile kit qfd_tile_nk_tp8, 311.04 x
        # 1,296 um) + the unchanged 52.704-um qfd_cst corridor; r19 takes the slot pitch from KV_TILE_W
        v.KV_TILE_W = round(cfg['tile_body'] + v.CORR, 6)
        v.TILE_SLOT = (v.KV_TILE_W, cfg.get('tile_h', v.TILE_SLOT[1]))
        v.TILE_BODY_W = cfg['tile_body']
        if cfg.get('f2'):
            # tp8b F2: column pitch = tile slot + the column channel (station corridor + spread tree legs)
            v.KV_TILE_W = cfg['f2']['col_pitch']
            v.TILE_SLOT = (v.KV_TILE_W, cfg.get('tile_h', v.TILE_SLOT[1]))
    if cfg.get('tree_pads'):
        _tp = json.loads((ROOT / cfg['tree_pads']).read_text())
        v.TREE_PADS = _tp['pads']
        v.TREE_PAD_TARGETS = _tp.get('targets', {})     # total relays per padded leg (unpadded relays + pads)


# ---- qwen-tp8 tp8b (results/arch/qwen_tp8_1012/SPEC.md section 0 / 5, floorplan F2, track B single die): 48 columns x
# 16 rows of qfd_tile_nk at the 311.04 x 1,296 slot (column pitch = slot + column channel), 3 compact bands of 16 4x4
# blocks (band 0 = block-row 0 + the 4 near-spine blocks of block-row 1; band 1 = the other 8 of block-row 1 + the 8
# near-spine blocks of block-row 2; band 2 = the other 4 of block-row 2 + block-row 3), the spine column widened to the
# F2 4,589 um with the KV-centre sub-column, the KV die halves on the W / E edges, ALL IO in one S band under a 400-um
# IO word channel.
def _tp8b_bands(cols, rows, bc=4, br=4):
    nbc, half = cols // bc, cols // bc // 2
    blocks = {}
    for c0 in range(0, cols, bc):
        for r0 in range(0, rows, br):
            k = c0 // bc
            side = 'W' if k < half else 'E'
            dist = (half - 1 - k) if side == 'W' else (k - half)      # 0 = next to the spine
            row = r0 // br
            if row == 0 or (row == 1 and dist <= 1):
                band = 0
            elif row == 1 or (row == 2 and dist <= 3):
                band = 1
            else:
                band = 2
            blocks[(c0, r0)] = (band, side, dist)
    out, members = {}, {}
    for b in range(3):
        mem = [cr for cr, t in blocks.items() if t[0] == b]
        w = sorted((cr for cr in mem if blocks[cr][1] == 'W'), key=lambda cr: (-blocks[cr][2], cr[1]))
        e = sorted((cr for cr in mem if blocks[cr][1] == 'E'), key=lambda cr: (blocks[cr][2], cr[1]))
        assert len(w) == len(e) == 8, ('tp8b band', b, len(w), len(e))
        for k, cr in enumerate(w + e):
            out[cr] = (b, k)
        members[b] = w + e
    return out, members


def _tp8b_base(v, cfg):
    f2 = cfg['f2']
    v.COLS, v.ROWS = f2['cols'], f2['rows']
    bmap, members = _tp8b_bands(v.COLS, v.ROWS, *v.BLOCK)
    v.BAND_OF = lambda b, c0, r0: bmap[(c0, r0)]
    v.BAND_BLOCKS = members


def _yshift(m, g, ys, dy, skip=()):
    """everything at or above y = ys moves up by dy (instances not in skip, regions, geo y values)."""
    for i in m['insts']:
        if i.name not in skip and i.y >= ys - 1e-3:
            i.y = round(i.y + dy, 4)
    for key in ('regions', 'clock_regions'):
        out = []
        for r in m.get(key, []):
            x0, y0, x1, y1 = r['rect']
            if y0 >= ys - 1e-3:
                y0, y1 = y0 + dy, y1 + dy
            elif y1 > ys + 1e-3:
                y1 = y1 + dy
            out.append(dict(r, rect=[x0, round(y0, 4), x1, round(y1, 4)]))
        m[key] = out
    for k in list(g):
        val = g[k]
        if k.startswith(('y', 'mid', 'row_y', 'ch_y', 'stack_cy')):
            if isinstance(val, (int, float)) and val >= ys - 1e-3:
                g[k] = round(val + dy, 4)
            elif isinstance(val, list) and val and all(isinstance(q, (int, float)) for q in val):
                g[k] = [round(q + dy, 4) if q >= ys - 1e-3 else q for q in val]


def _tp8b_f2(v, m):
    """tp8b F2 re-floorplan after the tp8a spine / IO surgery, before the relays (they are derived from this placement)."""
    from qwen_kv_die import rom_r22k as R
    f2 = TP8['f2']
    g = m['geo']
    by = {i.name: i for i in m['insts']}
    W = m['die']['w']
    S = v.SHAVE
    half = v.COLS // 2
    pitch = v.TILE_SLOT[0]
    xw_end = m['col_x'](half - 1) + pitch          # W field end (spine W face)
    xe0 = m['col_x'](half)                          # E field start
    spine_w = xe0 - xw_end
    # (1) the KV-centre sub-column (qkd_seq / host / ahub / embgw) on the spine's E side: spine -> f2 spine_w
    kvc = v.up(f2['spine_w'] - spine_w, v.GX)
    if kvc > 0:
        W = R._spine_relay_channel(v, m, g, xe0, kvc, W)
    g['tp8b_kvc_x'] = [round(xe0, 4), round(xe0 + kvc, 4)]
    # (1b) qwen-tp8/die it3 (fine cuts, coordinator 10-12: use the x margin of the 33-mm field): widen the W spine relay
    # channel by f2['w_ch'] and open a full-height A|B relay channel of f2['ab_ch'] between spine sub-columns W (port /
    # lane slabs) and M (SU / tree top / constants) -- the tree top's W face was abutted on all four sides and every
    # long spine word stacked in the one 225-um W channel.  SPINE_CHANNEL_X gets the A|B lane (load-balanced in _relays).
    wch, ab = v.up(f2.get('w_ch', 0.0), v.GX), v.up(f2.get('ab_ch', 0.0), v.GX)
    if wch or ab:
        xa, xb = by['sp_port_tiles_0'].x, by['sp_su64_sfu'].x
        chx0 = list(getattr(v, 'SPINE_CHANNEL_X', None) or [])
        if ab:
            W = R._spine_relay_channel(v, m, g, xb, ab, W)
        if wch:
            W = R._spine_relay_channel(v, m, g, xa, wch, W)
        if ab:
            # the VM stays centred on the SU / control-tile stack it abuts (su_vm / tt_mx words cross that seam
            # face to face); its W edge now leaves the widened W channel + ab free at its height
            by['sp_vector_memory'].x = round(by['sp_vector_memory'].x + ab, 4)
        lanes = [round(chx0[0] + wch / 2, 3)] if chx0 else []
        if ab:
            lanes.append(round(xb + wch + ab / 2, 3))
        lanes += [round(x + wch + ab, 3) for x in chx0[1:]]
        v.SPINE_CHANNEL_X = lanes
        v.SPINE_LANE_BALANCE = True
        v.TILE_CLUSTER = True        # coordinator 12:15: qfd_tile_nk is a cluster slot, die M8+ over it
        if f2.get('tile_m6'):
            v.CLUSTER_PLAN = 'M6'    # coordinator 2026-10-13: tiles M5-capped, die M6 over them for horizontal buses
        xe0 = round(xe0 + wch + ab, 4)
        ck = by.get('clk_rx')
        if ck is not None and ab:
            # the forwarded-clock receiver sat in sub-column W right where the KV-half words (aq / emf / emr) and the
            # VM result words cross the spine (fine x-cut 0.74 over it): it moves to sub-column M above the tree top
            t2 = by['tt_up4_2']
            ck.x, ck.y = round(t2.x, 4), round(v.dn(t2.y + t2.h + 1200.0, v.GY), 4)
        g['tp8b_kvc_x'] = [round(x + wch + ab, 4) for x in g['tp8b_kvc_x']]
        g['tp8b_spine_channels'] = dict(w_ch=wch, ab_ch=ab, lanes=lanes)
    # (2) the KV-die halves: W strip + channel left of the W field, E strip + channel right of the E field
    kvs = v.up(f2['kv_w'] + f2['kv_ch'], v.GX)
    W = R._spine_relay_channel(v, m, g, 0.0, kvs, W)
    g['tp8b_kv_w'] = [round(v.EDGE if hasattr(v, 'EDGE') else 0.0, 4), round(kvs, 4)]
    g['tp8b_kvc_x'] = [round(x + kvs, 4) for x in g['tp8b_kvc_x']]     # recorded before the W strip shifted the core
    W = round(W + kvs, 4)
    g['tp8b_kv_e'] = [round(W - kvs, 4), round(W, 4)]
    chx = getattr(v, 'SPINE_CHANNEL_X', None)
    if chx:
        v.SPINE_CHANNEL_X = [round(x + kvs + (kvc if x >= xe0 - 1e-3 else 0.0), 3) for x in chx]
        if getattr(v, 'SPINE_LANE_BALANCE', False):
            # it3: two more lanes in the KV-centre column (W and E of its blocks)
            # (>= 300 um from the E spine lane so the two never share a 260-um window); the KV centre's own words
            # run in this column too: _relays pre-loads these lanes (SPINE_LANE_PRELOAD bits over the die height)
            k0 = g['tp8b_kvc_x'][0]
            v.SPINE_CHANNEL_X = sorted(v.SPINE_CHANNEL_X + [round(k0 + 320.0, 3), round(k0 + 650.0, 3)])
            v.SPINE_LANE_PRELOAD = {round(k0 + 320.0, 3): 1000.0, round(k0 + 650.0, 3): 2500.0}
    # (3) IO band S: the core moves up by IO_DEPTH + the IO word channel; the IO blocks go to the S edge
    v.IO_SOUTH_BAND = True
    io = [i for i in m['insts'] if i.kind in ('io', 'xfifo')]
    ion = {i.name for i in io}
    y_io_old = min(i.y for i in io)
    ch = v.up(f2['io_chan'], v.GY)
    dy = v.up(v.IO_DEPTH + ch, v.GY)
    y_edge = g['y0']
    _yshift(m, g, 0.0, dy, skip=ion)
    for i in io:
        i.y = round(y_edge, 4)
    m['regions'] = [r for r in m['regions'] if r['name'] not in ('io_band', 'io_chan')]
    xa, xb = m['col_x'](0), m['col_x'](v.COLS - 1) + pitch
    m['regions'] += [dict(name='io_band', kind='io', rect=[xa, y_edge, xb, y_edge + v.IO_DEPTH]),
                     dict(name='io_chan', kind='channel', rect=[xa, y_edge + v.IO_DEPTH, xb, y_edge + dy])]
    # the IO row keeps its x order (SerDes 1 / 2, collective, xfifo, UCIe, SerDes 0), centred on the spine
    io.sort(key=lambda i: i.x)
    iog = f2.get('io_gap')
    if iog:
        # it3: >= io_gap between IO blocks (the abutted row left 2-41 um, so the xfifo <-> SerDes words' relays sat on
        # the die edge and hopped 3.5 mm diagonally over the UCIe PHY); host_serdes: a reserved slot for the KV host
        # SerDes PHY between the collective and the xfifo (filled by _tp8b_kv)
        x_ = x00 = io[0].x
        for i in io:
            if f2.get('host_serdes') and i.name == 'io_collective':
                # W of the collective: the slot must not split the collective | xfifo | UCIe words (11 kb face to face)
                g['tp8b_host_slot_dx'] = round(v.up(x_, v.GX) - x00, 4)
                x_ = v.up(x_, v.GX) + f2['host_serdes_w'] + iog
            i.x = round(v.up(x_, v.GX), 4)
            x_ = i.x + i.w + iog
    span = io[-1].x + io[-1].w - io[0].x
    xc = (m['col_x'](half - 1) + pitch + m['col_x'](half)) / 2 - kvc / 2      # the ROM spine (W of the KV centre)
    sx = v.dn(xc - (by['io_collective'].x + by['io_collective'].w / 2 - io[0].x) - io[0].x, v.GX)
    sx = max(sx, v.up(xa, v.GX) - io[0].x)
    sx = min(sx, v.dn(xb - io[-1].x - io[-1].w - S, v.GX))
    for i in io:
        i.x = round(i.x + sx, 4)
    if 'tp8b_host_slot_dx' in g:
        g['tp8b_host_slot'] = [round(x00 + sx + g.pop('tp8b_host_slot_dx'), 4), round(y_edge, 4)]
    g['y_io'] = g['y_top']          # the relays' corridor top (the IO band no longer sits above the field)
    H = v.up(g['y_top'] + v.EDGE if hasattr(v, 'EDGE') else g['y_top'] + 21.6, v.GY)
    m['die'] = dict(m['die'], w=W, h=H, mm2=round(W * H / 1e6, 3), margin_mm2=round(858 - W * H / 1e6, 3))
    # (4) the constant ROM row gets a >= f2['crom_ch'] um word channel to the buffer rows above it
    cr = [i for i in m['insts'] if i.name.startswith('crom_g_')]
    cb = [i for i in m['insts'] if i.name.startswith('cbuf_g_')]
    if cr and cb:
        gap = min(b_.y for b_ in cb) - max(c.y + c.h + S for c in cr)
        need = f2.get('crom_ch', 151.2) - gap
        if need > 0:
            for c in cr:
                c.y = round(v.dn(c.y - need, v.GY), 4)
        g['tp8b_crom_ch_um'] = round(min(b_.y for b_ in cb) - max(c.y + c.h + S for c in cr), 3)
    ov = []
    ins = [i for i in m['insts']]
    ins.sort(key=lambda i: i.x)
    for a_ in range(len(ins)):
        p = ins[a_]
        for b_ in range(a_ + 1, len(ins)):
            q = ins[b_]
            if q.x >= p.x + p.w - 1e-3:
                break
            if q.y < p.y + p.h - 1e-3 and p.y < q.y + q.h - 1e-3:
                ov.append((p.name, q.name))
    m['tp8b'] = dict(die_um=[W, H], spine_w=round(spine_w + kvc, 3), kvc_w=kvc, kv_strip_w=kvs, io_dy=dy,
                     io_x=[round(io[0].x, 3), round(io[-1].x + io[-1].w, 3)], overlaps=ov[:20], n_overlaps=len(ov))
    if ov and TP8.get('split') != 'compute':      # split compute die: spine re-placed after tp8b_v5, gated there
        raise SystemExit(f'tp8b: {len(ov)} overlaps, e.g. {ov[:6]}')


def _gate_track_lattice(lef, m):
    """Fail the case generation (seconds, locally) instead of the remote case (minutes): every BLOCK master must
    have a legal origin on the ASAP7 track lattice in R0/MX/MY/R180 (tools/check_macro_track_alignment.py, the
    same residue rule as physical/common/ot_macro_track_snap.tcl).  Origins themselves are snapped to that lattice
    by ot_mts in place.tcl; a master with no legal residue cannot be snapped anywhere."""
    import importlib.util
    f = Path(__file__).resolve().parent / 'check_macro_track_alignment.py'
    spec = importlib.util.spec_from_file_location('ot_mta', f)
    mta = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mta)
    res = mta.run([str(lef)], mta.ASAP7_TRACKS_NM, mta.ASAP7_LAYERS)
    bad = {r['macro']: {lay: s['no_legal_origin'] for lay, s in r.get('summary', {}).items() if s.get('no_legal_origin')}
           for r in res['macros']}
    bad = {k: v for k, v in bad.items() if v}
    m['track_lattice'] = dict(blocks=len(res['macros']), no_legal_origin=bad)
    if bad:
        raise SystemExit(f'track lattice: {len(bad)} masters have no legal origin: {dict(list(bad.items())[:6])}')


KV_DROP = ('d2d_kv', 'ucie_rom', 'ckb_kv', 'serdes_host')       # KV-die D2D / UCIe / clock bump / host SerDes: gone on one die
ROM_DROP = ('ucie_kv', 'd2d_rom', 'ckb_rom', 'rs_bump')
KV_CENTRE = ('pll', 'embgw', 'seq', 'ahub', 'host')              # N -> S in the KV-centre sub-column (the KV PLL is the die PLL)
# ROM-side D2D words re-terminated on the KV centre (the D2D pair is a wire on one die): bus -> (KV inst, port, bits or None)
KV_SHORT = dict(x3=('seq', 'r_x3', None), seq_d2d=('seq', 'r_sd', None), o4_kvd=('seq', 'r_kvd', None),
                attn_ret=('seq', 't_ar', None), d2d_seq=('seq', 't_ds', None), d2d_flt=('seq', 't_flt', None),
                o4_pw=('seq', 't_pw', None), emb=('embgw', 't_eq', 1024), emb_a=('embgw', 'r_ea', None),
                emb_cr=('embgw', 't_ecr', None))


def _tp8b_kv(v, m):
    """tp8b (track B, single die type): the KV die's two halves (HBM PHYs + CDC strips + landings + attention stacks,
    their own buses and relays) land unrotated in the W / E strips reserved by _tp8b_f2, the KV centre blocks (PLL,
    embedding gateway, KV sequencer, attention hub, host) in the KV-centre sub-column E of the ROM spine; the D2D pair
    (ROM d2d_rom/ucie_kv, KV d2d_kv/ucie_rom), the clock / reset bumps and the KV host SerDes are dropped and their words
    re-terminated directly (ROM peers <-> KV seq / embgw).  Embedding ingress is 1,024 b (embgw -> su64 eq).  Every
    word between the centre and a half is a new die wire, relayed by _relays (classes as on the KV die); the halves'
    own relayed words keep their KV-die relays (class '<cl>@kv', in RELAY_SKIP)."""
    global RELAY_SKIP
    from qwen_kv_die import kv_die as K
    g = m['geo']
    mk = K.build(kv_wq_mirror=True)
    KM = dict(K.masters(mk, 1))         # pins from the KV-die placement (same W | centre | E order on this die)
    KPW = dict(K.port_widths(mk, 1))
    Wk, Hk = mk['die']['w'], mk['die']['h']
    W, H = m['die']['w'], m['die']['h']
    kby = {i.name: i for i in mk['insts']}
    xs = [(i.x, i.x + i.w) for i in mk['insts'] if i.name not in KV_DROP + KV_CENTRE and not i.master.startswith('qkd_rly')]
    w_end = max(b for a, b in xs if a < Wk / 2)
    e_beg = min(a for a, b in xs if a >= Wk / 2)
    assert w_end <= g['tp8b_kv_w'][1] - 50 and Wk - e_beg <= g['tp8b_kv_e'][1] - g['tp8b_kv_e'][0] - 50, (w_end, Wk - e_beg)
    dy = v.dn((g['y0'] + g['y_top'] - Hk) / 2 if Hk <= g['y_top'] - g['y0'] else (H - Hk) / 2, v.GY)
    dxe = v.dn(W - Wk, v.GX)
    side = {}
    for i in mk['insts']:
        if i.name in KV_DROP or i.name in KV_CENTRE:
            continue
        cx = i.x + i.w / 2
        side[i.name] = 'W' if cx < Wk / 2 else 'E'
    # chains: base bus -> its segments; a chain touching a centre / dropped block loses its KV relays (re-relayed here)
    def base(b):
        return b.split('__r')[0]
    chains = {}
    for bus in mk['buses']:
        chains.setdefault(base(bus[0]), []).append(bus)
    keep_rly, nb = set(), []
    kept_chains = {}                                   # base bus -> (segments, relay names) of the chains kept as placed
    for b0, segs in chains.items():
        ends = [e for s_ in segs for e in s_[3] if not kby[e[0]].master.startswith('qkd_rly')]
        rl = {e[0] for s_ in segs for e in s_[3] if kby[e[0]].master.startswith('qkd_rly')}
        cl, bits = segs[0][1], segs[0][2]
        if any(e[0] in KV_DROP for e in ends):
            continue                                   # D2D / bump / SerDes words: re-terminated below or gone
        if len(segs) == 1 and len(segs[0][3]) != 2:
            nb.append((b0, cl, bits, [e for e in segs[0][3] if e[0] not in KV_DROP]))
            continue
        if any(e[0] in KV_CENTRE for e in ends) or len({side.get(e[0]) for e in ends}) > 1:
            nb.append((b0, cl, bits, [segs[0][3][0], segs[-1][3][-1]] if len(segs) > 1 else segs[0][3]))
            continue
        keep_rly |= rl
        if rl:
            kept_chains[b0] = (segs, rl)
        nb += [(bid, cl if cl in RELAY_SKIP else f'{cl}@kv', bt, eps) for bid, cl_, bt, eps in segs for cl in (cl_,)]
    # main 758ccc84c: KV relays now sit on their driver's clk_core trunk; a dropped (re-relayed) KV relay leaves the
    # multi-pin trunks with it, the kept ones keep their ck
    nb = [(b_, c_, t_, [e for e in eps_ if not (kby[e[0]].master.startswith('qkd_rly') and e[0] not in keep_rly)])
          if len(eps_) != 2 else (b_, c_, t_, eps_) for b_, c_, t_, eps_ in nb]
    RELAY_SKIP = tuple(RELAY_SKIP) + tuple(sorted({b[1] for b in nb if b[1].endswith('@kv')}))
    new = []
    for i in mk['insts']:
        if i.name in KV_DROP or i.name in KV_CENTRE:
            continue
        if i.master.startswith('qkd_rly') and i.name not in keep_rly:
            continue
        sd = side.get(i.name, 'W' if i.x < Wk / 2 else 'E')
        i.x = round(i.x + (dxe if sd == 'E' else 0.0), 4)
        i.y = round(i.y + dy, 4)
        new.append(i)
    # it17 (layer plan A, die M8+ over the tile_nk clusters): the KV strip head stacks (4 groups of 4 qkd_rhead + 1
    # qkd_ectl per stack column, abutted 7.8 mm) left KV-half words no crossing height but the stack ends (it16: all
    # W words in ONE row gap, 0.875).  Open a crossing channel of kv_xch um between consecutive head groups (groups
    # shift up by j * kv_xch, astk spans the stack unchanged); the channels (M4-M9 free, relay sites) are recorded in
    # v.KV_XCH per strip side for _relays (<= KV_XCH_CAP b per channel)
    xch = TP8['f2'].get('kv_xch')
    v.KV_XCH = {}
    xsh = {}                                           # instance -> its crossing-channel shift (um)
    if xch:
        import re as _re
        heads = [i for i in new if _re.match(r'(head|ectl)_[WE][SN]_\d+', i.name)]
        cols = {}
        for i in heads:
            sd, sn, c = _re.match(r'\w+?_([WE])([SN])_(\d+)', i.name).groups()
            cols.setdefault((sd, sn, round(i.x, 1)), {}).setdefault(int(c), []).append(i)
        for (sd, sn, cx), grp in sorted(cols.items()):
            order = sorted(grp, key=lambda c: min(i.y for i in grp[c]))
            spans = [(min(i.y for i in grp[c]), max(i.y + i.h for i in grp[c])) for c in order]
            x0_, x1_ = cx, max(i.x + i.w for c in order for i in grp[c])
            mv = []
            for j, c in enumerate(order):
                ya, yb = spans[j]
                yb = yb + 2000.0 if j == len(order) - 1 else yb     # the top group carries the relays above the stack
                sh = round(j * xch, 4)
                # the group and every short block / kept relay over its span in the column (astk is taller than a
                # group and stays); membership on the unshifted placement
                mv += [(i, sh) for i in new if sh and i.h < 1000.0 and i.x < x1_ - 1.0 and x0_ + 1.0 < i.x + i.w
                       and ya - 1.0 <= i.y + i.h / 2 <= yb + 1.0]
            for i, sh in mv:
                i.y = round(i.y + sh, 4)
                xsh[i.name] = round(xsh.get(i.name, 0.0) + sh, 4)
            chs = [round(spans[j][0] + (j - 0.5) * xch, 3) for j in range(1, len(order))]
            v.KV_XCH.setdefault(sd, set()).update(chs)
        v.KV_XCH = {k: sorted(x) for k, x in v.KV_XCH.items()}
        v.KV_XCH_STRIP = {sd: (min(i.x for i in heads if f'_{sd}' in i.name[4:7]), max(i.x + i.w for i in heads if f'_{sd}' in i.name[4:7]))
                          for sd in v.KV_XCH}
    # relay-data 2026-10-13 (pinreg audit: 52 kept hops of 700 um, krs / krq): a kept KV chain is as placed on the KV die
    # (every hop <= 450 um pin to pin) only if the crossing-channel shift moved ALL its members alike.  A chain whose
    # relays / endpoints moved by different amounts (head groups j * kv_xch, relays between the columns and the 12-mm
    # landing 0) is TORN: its KV relays are dropped and the word is re-relayed by _relays like every centre word.
    torn = []
    for b0, (segs, rl) in sorted(kept_chains.items()):
        mem = {e[0] for s_ in segs for e in s_[3]}
        if len({xsh.get(n_, 0.0) for n_ in mem}) > 1:
            torn.append(b0)
            keep_rly -= rl
            ids = {s_[0] for s_ in segs}
            nb = [b_ for b_ in nb if b_[0] not in ids]
            nb.append((b0, segs[0][1], segs[0][2], [segs[0][3][0], segs[-1][3][-1]]))
    if torn:
        new = [i for i in new if not (i.master.startswith('qkd_rly') and i.name not in keep_rly)]
        nb = [(b_, c_, t_, [e for e in eps_ if not (kby[e[0]].master.startswith('qkd_rly') and e[0] not in keep_rly)])
              if len(eps_) != 2 else (b_, c_, t_, eps_) for b_, c_, t_, eps_ in nb]
    v.RELAY_REACH_GATE = True
    # KV centre column (E of the ROM spine), centred on the die's mid-height
    x0, x1 = g['tp8b_kvc_x']
    gap = 2 * v.GY
    tot = sum(kby[n].h for n in KV_CENTRE) + gap * (len(KV_CENTRE) - 1)
    y = v.dn((g['y0'] + g['y_top']) / 2 + tot / 2, v.GY)
    for n in KV_CENTRE:
        i = kby[n]
        y = v.dn(y - i.h, v.GY)
        xc_ = x1 - 120.0 - 389.0 if TP8['f2'].get('kvc_east') else (x0 + x1) / 2   # it3: E-aligned centre stack
        i.x, i.y = round(v.dn(xc_ - i.w / 2, v.GX), 4), round(y, 4)
        y -= gap
        new.append(i)
    gone = [i for i in m['insts'] if i.name in ROM_DROP]
    m['insts'] = [i for i in m['insts'] if i.name not in ROM_DROP] + new
    # ROM-side buses: drop the D2D / bump words, re-terminate the D2D peers on the KV centre
    rb, short = [], {}
    for bid, cl, bits, eps in m['buses']:
        if bid in KV_SHORT:
            kn, kp, kb = KV_SHORT[bid]
            eps = [(kn, kp) if e[0] == 'd2d_rom' else e for e in eps]
            bits = kb or bits
            short[bid] = (kn, kp, bits, 'W')
            rb.append((bid, cl, bits, eps))
            continue
        if bid == 'pll_fwd':
            rb.append((bid, cl, bits, [('pll', 'pll_fwd')] + [e for e in eps if e[0] not in ROM_DROP]))
            continue
        if bid == 'rst_fwd_s':
            rb.append((bid, cl, bits, [('pll', 'rso_fwd')] + [e for e in eps if e[0] not in ROM_DROP]))
            continue
        eps = [e for e in eps if e[0] not in ROM_DROP]
        if len(eps) >= 2:
            rb.append((bid, cl, bits, eps))
    m['buses'] = rb + [(f'kv.{b}' if b in {x[0] for x in rb} else b, cl, bits, eps) for b, cl, bits, eps in nb]
    m['regions'] += [dict(name='kv_w', kind='kv_half', rect=[0.0, dy, w_end, dy + Hk]),
                     dict(name='kv_e', kind='kv_half', rect=[e_beg + dxe, dy, W, dy + Hk]),
                     dict(name='kv_centre', kind='kv_centre', rect=[x0, y, x1, y + tot + gap])]
    m['tp8b_kv'] = dict(kv_die_um=[Wk, Hk], dy=dy, dxe=dxe, w_end=round(w_end, 3), e_beg=round(e_beg + dxe, 3),
                        kept_relays=len(keep_rly), torn_chains=torn, insts=len(new), buses=len(nb), short=sorted(short), emb_ingress_b=1024)
    # qwen-tp8/die it3 (coordinator 10-12, single die type): EVERY die carries the KV host SerDes slot (serdes_host,
    # 112G x12 PHY) and the 2,085-b host FDI ingress host.fdi <-> serdes_host.fdi; only the dies wired to a host use it.
    # The PHY sits on a die edge (S IO row first, then N edge) in the free slot nearest the KV-centre column (the host
    # block's x), 20-um halo; its clock / reset join the KV centre's (clk_core_c / rst_core_c roots at the KV PLL).
    if TP8['f2'].get('host_serdes'):
        hs = kby['serdes_host']
        halo = 20.0
        xh = (x0 + x1) / 2
        occ = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]

        def hs_free(xa, ya):
            return all(not (a < xa + hs.w + halo and xa - halo < c and b < ya + hs.h + halo and ya - halo < d)
                       for a, b, c, d in occ)
        spot = None
        if 'tp8b_host_slot' in g:
            xs0, ys0 = g['tp8b_host_slot']
            spot = (v.up(xs0, v.GX), ys0)      # reserved by _tp8b_f2 (the overlap check below guards it)
        for ya in () if spot else (min(i.y for i in m['insts'] if i.kind in ('io', 'xfifo')), v.dn(H - hs.h - 21.6, v.GY)):
            xs_ = [v.dn(halo + k * 10.8, v.GX) for k in range(int((W - hs.w - 2 * halo) / 10.8))]
            ok = [x_ for x_ in xs_ if hs_free(x_, ya)]
            if ok:
                spot = (min(ok, key=lambda x_: abs(x_ + hs.w / 2 - xh)), ya)
                break
        if spot is None:
            raise SystemExit('tp8b kv: no edge slot for the host SerDes')
        hs.x, hs.y = round(spot[0], 4), round(spot[1], 4)
        m['insts'].append(hs)
        fdi = next(bt for b0, cl_, bt, eps in mk['buses'] if base(b0) == 'host_fdi')
        m['buses'].append(('host_fdi', 'd2d_fdi', fdi, [('host', 'fdi'), ('serdes_host', 'fdi')]))
        m['tp8b_kv'].update(host_serdes=dict(xy=[hs.x, hs.y], wh=[hs.w, hs.h], fdi_bits=fdi))
    # the KV centre's own clock / reset trees (clk_core_c / rst_core_c from the KV PLL to seq / embgw / ahub / host
    # [+ serdes_host]) were dropped with the D2D / UCIe ends: re-add them over the blocks present on this die
    have = {i.name for i in m['insts']}
    for b0, cl_, bt, eps in mk['buses']:
        if base(b0) in ('clk_core_c', 'rst_core_c') and b0 == base(b0):
            keep_e = [e for e in eps if e[0] in have]
            m['buses'].append((b0, cl_, bt, keep_e))
            m['tp8b_kv'].setdefault('centre_trees', []).append([b0, len(keep_e)])
    ins = sorted(m['insts'], key=lambda i: i.x)
    ov = []
    for a_ in range(len(ins)):
        p = ins[a_]
        for b_ in range(a_ + 1, len(ins)):
            q = ins[b_]
            if q.x >= p.x + p.w - 1e-3:
                break
            if q.y < p.y + p.h - 1e-3 and p.y < q.y + q.h - 1e-3:
                ov.append((p.name, q.name))
    out = [i.name for i in ins if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > W + 1e-3 or i.y + i.h > H + 1e-3]
    m['tp8b_kv'].update(n_overlaps=len(ov), overlaps=ov[:20], n_outside=len(out), outside=out[:20])
    if ov or out:
        raise SystemExit(f'tp8b kv: {len(ov)} overlaps {ov[:6]}, {len(out)} outside {out[:6]}')
    base_m, base_pw = v.masters, v.port_widths

    def masters(model, k=1, port_bits=None):
        # the TP4 master builders still read the dropped D2D frames by name: give them a view that has them
        o = base_m(dict(model, insts=list(model['insts']) + gone), k, port_bits)
        for name, q in KM.items():
            o.setdefault(name, q)
        sq, eg = o['qkd_seq'], o['qkd_embgw']
        ref = sq.ports.get('rf') or sq.ports.get('d2df')
        lay = ref[3] if ref and ref[0] == 'face' else 'M5'
        def occupied(mm, face):
            # intervals (along the face) already taken by face groups on that face, any layer
            occ = []
            for q in mm.ports.values():
                if q and q[0] == 'face' and q[2] == face:
                    h = q[1] * q[5] * 0.048 / 2
                    occ.append((q[4] - h, q[4] + h))
            return sorted(occ)

        for bid, (kn, kp, bits, face) in sorted(short.items()):
            mm = sq if kn == 'seq' else eg
            if kp in mm.ports:
                continue
            # a pin layer must run across its face: the N/S faces take the seq 'rf' layer (vertical, M5), the E/W
            # faces a horizontal layer (M4).  An M5 pin on a W/E face sits at x = depth/2 (0.096), off the M5 x
            # lattice the N/S pins fix -> 'ot_mts: qkd_embgw R0 x has no legal origin' (it2 case_r22k).  On M4 the
            # words share the face with the KV-half M4 groups, so each takes the first free gap (first fit, 4-um
            # gaps) instead of a private running offset from the face start.
            span = bits * 0.048 * 2
            L_ = mm.h if face in 'EW' else mm.w
            at = 8.0
            for a0, a1 in occupied(mm, face):
                if at + span + 4.0 <= a0:
                    break
                at = max(at, a1 + 4.0)
            if at + span > L_ - 2.0:
                raise ValueError(f'tp8b kv short {kp}: {bits} b do not fit the {mm.name} {face} face')
            mm.face(kp, bits, face, lay if face in 'NS' else 'M4', at + span / 2, 2)
        # r6 2026-10-13 (die timing by construction; the two pin plans no relay chain can serve):
        # (a) gq / gr (seq <-> embedding gateway, 530 b each): the KV-die pins face each other with the gateway S of
        #     the sequencer; on this die the centre stack has the gateway N of it, so both pins looked AWAY from their
        #     peer (911 um around two abutting blocks, no relay site in the 4-um gaps: 746.9 / 892.3 um hops).  They
        #     move to the facing faces (seq N, gateway S) at one x: an abutment wire, no relay, no cycle.
        ci = {i.name: i for i in model['insts'] if i.name in ('seq', 'embgw')}
        if len(ci) == 2 and ci['embgw'].y > ci['seq'].y:
            dx_ = ci['embgw'].x - ci['seq'].x
            for p_ in ('gq', 'gr'):
                q = sq.ports.get(p_)
                if not q or q[0] != 'face' or q[2] == 'N' or p_ not in eg.ports:
                    continue
                half = q[1] * q[5] * 0.048 / 2
                occ = occupied(sq, 'N') + [(a0 + dx_, a1 + dx_) for a0, a1 in occupied(eg, 'S')]
                at = None
                c_ = dx_ + 8.0 + half
                while c_ + half <= dx_ + eg.w - 8.0:
                    if all(c_ + half + 4.0 <= a0 or a1 + 4.0 <= c_ - half for a0, a1 in occ):
                        at = c_
                        break
                    c_ += 2.16
                if at is None:
                    raise ValueError(f'tp8b kv: no common free span for {p_} on the seq N / embgw S faces')
                sq.ports[p_] = (q[0], q[1], 'N', q[3], round(at, 4), q[5])
                e_ = eg.ports[p_]
                eg.ports[p_] = (e_[0], e_[1], 'S', e_[3], round(at - dx_, 4), e_[5])
        # (b) a port slab's block-word pin at an edge another block abuts (sp_port_tiles_1_f1.bw8 on the W edge against
        #     tt_ctlm, the vector memory below: the nearest relay site is 849 um away) moves to the slab's other
        #     edge, where its siblings' relay chains arrive.
        big_ = [i for i in model['insts'] if i.w * i.h > 4e4]
        cnt_ = {}
        for i in model['insts']:
            cnt_[i.master] = cnt_.get(i.master, 0) + 1
        for it in model['insts']:
            if not it.master.startswith(('qfd_port_tiles', 'qfd_sp_port_tiles')) or cnt_[it.master] != 1 or it.orient != 'R0':
                continue
            mm = o.get(it.master)
            if mm is None:
                continue
            bw = {p_: q for p_, q in mm.ports.items() if p_.startswith('bw') and q and q[0] == 'area'}

            def blocked(west, yy, it=it):
                xe = it.x if west else it.x + it.w
                return any(b_ is not it and b_.y - 1.0 <= yy <= b_.y + b_.h + 1.0 and
                           abs((b_.x + b_.w if west else b_.x) - xe) < 60.0 for b_ in big_)
            for p_, q in sorted(bw.items()):
                west = q[2] < 60.0
                if not west and q[2] <= mm.w - 60.0:
                    continue
                yy = it.y + q[3]
                if not blocked(west, yy) or blocked(not west, yy):
                    continue
                sib = [s_ for n_, s_ in bw.items() if n_ != p_ and ((s_[2] > mm.w - 60.0) if west else (s_[2] < 60.0))]
                if not sib or any(abs(s_[3] - q[3]) < 60.0 for s_ in sib):
                    continue
                mm.ports[p_] = (q[0], q[1], sib[0][2], q[3], q[4])
                m.setdefault('tp8b_kv', {}).setdefault('pin_moves', {})[f'{it.master}.{p_}'] = 'E' if west else 'W'
        su = o.get('qfd_sp_su64_sfu') or next((q for q in o.values() if 'eq' in q.ports and q.name.endswith('su64_sfu')), None)
        if su is not None and su.ports['eq'][0] == 'face':
            sp = su.ports['eq']
            su.ports['eq'] = (sp[0], 1024) + sp[2:]
        return o

    def port_widths(model, k=1):
        w = base_pw(model, k)
        for key, val in KPW.items():
            w.setdefault(key, val)
        for bid, (kn, kp, bits, face) in short.items():
            w[('qkd_seq' if kn == 'seq' else 'qkd_embgw', kp)] = bits
        return w
    v.masters, v.port_widths = masters, port_widths


def _tp8_io(v, m):
    """qwen-tp8 IO band: 3 SerDes ports (one per remote package, K4 board; TP4: 1 adapter for 2 destinations).  SerDes
    k = 1, 2 are placed W of the collective (MY: their S-face word pins at the end toward the collective); each gets
    its own collective s<k> / sr<k> words through the IO-band CDC cluster (i_/o_serdes_tx<k>, i_/o_serdes_rx<k>) and
    the SerDes link clock."""
    by = {i.name: i for i in m['insts']}
    col, s0, iox = by['io_collective'], by['io_serdes'], m['io']['xfifo']
    n = TP8.get('serdes', 3)
    x = col.x
    new = []
    for k in range(1, n):
        x = v.dn(x - 10 * v.GX - (s0.w + v.SHAVE), v.GX)
        it = v.Inst(f'io_serdes_{k}', s0.master, x, s0.y, s0.w, s0.h, 'MY', kind=s0.kind, region=s0.region,
                    domain=s0.domain)
        for o in m['insts']:
            assert not (o.x < it.x + it.w and it.x < o.x + o.w and o.y < it.y + it.h and it.y < o.y + o.h), \
                f'tp8 io: {it.name} overlaps {o.name}'
        new.append(it)
    m['insts'] += new
    bits = next(b for bid, cl, b, eps in m['buses'] if bid == 'serdes_tx')
    rbits = next(b for bid, cl, b, eps in m['buses'] if bid == 'serdes_rx')
    B = []
    for bid, cl, b, eps in m['buses']:
        if bid == 'clk_serdes':
            eps = list(eps) + [(it.name, 'ck') for it in new]
        B.append((bid, cl, b, eps))
    for k, it in enumerate(new, 1):
        B += [(f'serdes_tx{k}', 'io', bits, [('io_collective', f's{k}'), (iox.name, f'i_serdes_tx{k}')]),
              (f'serdes_tx{k}_x', 'io', bits, [(iox.name, f'o_serdes_tx{k}'), (it.name, 'c')]),
              (f'serdes_rx{k}', 'io', rbits, [(it.name, 'r'), (iox.name, f'i_serdes_rx{k}')]),
              (f'serdes_rx{k}_x', 'io', rbits, [(iox.name, f'o_serdes_rx{k}'), ('io_collective', f'sr{k}')])]
    m['buses'] = B
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        if 'qfd_io_collective' not in o:
            return o        # split compute static IO bind: credit IO masters retired
        C = o['qfd_io_collective']
        for q in range(1, n):
            for p0 in ('s', 'sr'):
                spec = C.ports[p0]
                assert spec[0] == 'face', (p0, spec)
                along = C.w if spec[2] in 'NS' else C.h
                span = spec[1] * 0.048 * spec[5] + 4.0
                c = spec[4] - q * span if spec[4] - q * span - span / 2 > 2.0 else spec[4] + q * span
                assert span / 2 + 2.0 <= c <= along - span / 2 - 2.0, ('tp8 collective pin', p0, q, c, along)
                C.face(f'{p0}{q}', spec[1], spec[2], spec[3], c, spec[5])
        X = o['qfd_io_xfifo']
        for q in range(1, n):
            for p0, j in (('o_serdes_tx', 0), ('i_serdes_rx', 1)):
                spec = X.ports.get(f'{p0}{q}')
                if spec is not None and spec[0] == 'face' and spec[2] in 'NS':
                    span = spec[1] * 0.048 * spec[5] + 4.0
                    X.ports[f'{p0}{q}'] = spec[:4] + (400.0 + (2 * (q - 1) + j) * span + span / 2,) + spec[5:]
        return o
    v.masters = masters
    m['tp8_io'] = dict(serdes=[s0.name] + [i.name for i in new], collective_um=[round(col.w, 3), round(col.h, 3)],
                       xfifo_um=[round(iox.w, 3), round(iox.h, 3)])


def _tp8_spine(v, m):
    """qwen-tp8 contract v2: the 26.0-mm reticle width.  At the 363.744-um slot pitch the 64 columns take 23.28 mm, so the
    spine gets <= 2.68 mm: three abutted 777.6-um sub-columns W | M | E between two full-height cfg['spine_gap'] edge
    relay channels (SPINE_CHANNEL_X; _seam_free moves pins off the W|M and M|E seams), and the near-square VM (3 x
    777.6, qwendie-1011 decision: its x path cannot cross a one-column cut) spans all three in a y window where the W
    and E sub-columns are free (vertical spine words pass it in the edge channels).  The SU / VM / control-tile / up4 / constant-store stack (abutted
    faces, ROM row at one height) moves up as one rigid body into the first such window inside its link-channel
    segment; the S-edge UCIe PHY + d2d_rom join the M sub-column.  Everything else keeps its y."""
    from qwen_kv_die import rom_r22k as R
    g = m['geo']
    by = {i.name: i for i in m['insts']}
    su, vm = by['sp_su64_sfu'], by['sp_vector_memory']
    cw, gap = 777.6, TP8['spine_gap']
    x0 = round(g['x_spine'], 4)
    xL = round(x0 + gap, 4)
    xM, xE = round(xL + cw, 4), round(xL + 2 * cw, 4)
    W = m['die']['w']
    xm0 = su.x
    left_sub = [i for i in m['insts'] if xm0 - cw - 1.0 <= i.x < xm0 - 1e-3 and i.name != vm.name and i.kind != 'tile'
                and i.y < g['y_top'] and i.x >= x0 + cw - 1e-3]
    # W edge channel, then M abutting W, E abutting M, then the E edge channel before the E tile field
    W = R._spine_relay_channel(v, m, g, x0, gap, W)
    xs = su.x
    W = R._spine_relay_channel(v, m, g, round(xs, 4), round(xM - xs, 4), W)
    xs = by['sp_port_tiles_0_f1'].x
    W = R._spine_relay_channel(v, m, g, round(xs, 4), round(xE - xs, 4), W)
    W = R._spine_relay_channel(v, m, g, round(xE + cw, 4), gap, W)
    for i in left_sub:
        i.x = round(xM + (i.x - gap - (xm0 - cw)), 4)      # moved by the W edge channel only
    # the small S-edge glue that sat in the old W | M channel (rs_bump, ckb_rom) steps W of the moved PHY / d2d column
    lsn = {i.name for i in left_sub}
    for i in m['insts']:
        if i.name in lsn or i.kind in ('tile', 'station', 'head') or i.y >= g['y_top']:
            continue
        if any(i.x < j.x + j.w + v.SHAVE and j.x < i.x + i.w + v.SHAVE and i.y < j.y + j.h + v.SHAVE and j.y < i.y + i.h + v.SHAVE
               for j in left_sub):
            i.x = round(v.dn(xM - i.w - v.SHAVE - 4.32, v.GX), 4)
    vm.x = xL
    # the rigid stack and the window search
    stack = [vm, su] + [by[n] for n in by if n.startswith(('tt_ctlm', 'tt_up4_', 'cbuf_g_', 'crom_g_'))]
    sn = {i.name for i in stack}
    S = v.SHAVE
    fixed = [i for i in m['insts'] if i.name not in sn and i.kind not in ('tile', 'station', 'head')
             and i.y < g['y_top'] and i.x + i.w > xL - 1e-3 and i.x < xE + cw + 1e-3]
    chans = [(r['rect'][1], r['rect'][3]) for r in m['regions'] if r['name'].startswith('hchan_')]
    seg = [(lo, hi) for lo, hi in zip([g['y0']] + [b for a, b in sorted(set(chans))],
                                      [a for a, b in sorted(set(chans))] + [g['y_top']])]
    y_lo, y_hi = min(i.y for i in stack), max(i.y + i.h + S for i in stack)
    seg0 = next((lo, hi) for lo, hi in seg if lo - 1e-3 <= vm.y < hi)

    def ov(a0, a1, b_):
        return a0 < b_.y + b_.h + S and b_.y < a1

    Lcol = [b_ for b_ in fixed if b_.x < xM - 1e-3]

    def chain(seed):
        # the W sub-column blocks abutting (in y) the seeds: the band slab stack moves as one rigid group
        grp = set(seed)
        while True:
            more = {c.name for c in Lcol if c.name not in grp and any(
                abs(c.y - (by[q].y + by[q].h + S)) < 3 * v.GY or abs(by[q].y - (c.y + c.h + S)) < 3 * v.GY for q in grp)}
            if not more:
                return grp
            grp |= more

    def fit(dy):
        """None when the stack cannot sit at dy; else the W-column group to move and its new y origin offset"""
        if y_lo + dy < seg0[0] - 1e-3 or y_hi + dy > seg0[1] + 1e-3:
            return None
        for a in stack:
            ay0, ay1 = a.y + dy, a.y + dy + a.h + S
            # the SU keeps an open E face (seq_su issue word si, 476 b: its S face is the constant buffers', N the VM's)
            ax1 = xE + cw if a is su else a.x + a.w + S
            for b_ in fixed:
                if b_ in Lcol and a is vm:
                    continue
                if a.x < b_.x + b_.w + S and b_.x < ax1 and ov(ay0, ay1, b_):
                    return None
        vy0, vy1 = vm.y + dy, vm.y + dy + vm.h + S
        hitL = [b_.name for b_ in Lcol if ov(vy0, vy1, b_)]
        if not hitL:
            return (set(), 0.0)
        grp = chain(hitL)
        gy0 = min(by[q].y for q in grp)
        gy1 = max(by[q].y + by[q].h + S for q in grp)
        rest = [b_ for b_ in Lcol if b_.name not in grp]
        for ny in sorted((v.up(vy1 + v.GY, v.GY), v.dn(vy0 - v.GY - (gy1 - gy0), v.GY)), key=lambda t: abs(t - gy0)):
            if ny < seg0[0] - 1e-3 or ny + (gy1 - gy0) > seg0[1] + 1e-3:
                continue
            if any(ov(ny, ny + gy1 - gy0, b_) for b_ in rest):
                continue
            return (grp, ny - gy0)
        return None
    dy, mv = None, None
    for k in range(0, int(max(seg0[1] - y_lo, y_hi - seg0[0]) / v.GY) + 1):
        for d_ in ((k * v.GY,) if k == 0 else (-k * v.GY, k * v.GY)):
            r_ = fit(d_)
            if r_ is not None:
                dy, mv = d_, r_
                break
        if dy is not None:
            break
    if dy is None and TP8.get('split') == 'compute':
        # qwen-split compute die: the spine is re-placed from the contract slot table (qwen_split/compute_spine.py) after
        # tp8b_v5; the window search of the merged die does not apply
        dy, mv = 0.0, (set(), 0.0)
    if dy is None:
        occ = sorted((round(b_.x), round(b_.y), round(b_.y + b_.h), b_.name) for b_ in fixed)
        raise SystemExit(f'tp8 spine: no window for the VM stack in segment {seg0} (W {W:.1f}); stack '
                         f'{sorted((round(a.x), round(a.y), round(a.y + a.h), a.name) for a in stack)}; fixed {occ}')
    for i in stack:
        i.y = round(i.y + dy, 4)
    for q in mv[0]:
        by[q].y = round(by[q].y + mv[1], 4)
    # seq_su (cbuf ctl / rdy x 8, SU issue / status / count, VM vrd / vrq / vwr, d2d words) leaves the far N end of the
    # E sub-column for the slot between the constant ROM row and the SU's E face: its 20+ words no longer cross the VM
    # window (the edge channels carry only the control-tile snapshots and the collective words past it)
    sq = by.get('seq_su')
    crt = max(by[f'crom_g_{k}'].y + by[f'crom_g_{k}'].h + S for k in range(8))
    if sq is not None and su.y - crt >= sq.h + S + 4 * v.GY:
        sq.x = round(v.up(xE + 43.2, v.GX), 4)
        sq.y = round(v.dn(crt + (su.y - crt - sq.h - S) / 2, v.GY), 4)
    v.SPINE_CHANNEL_X = [round(x0 + gap / 2, 3), round(xE + cw + gap / 2, 3)]
    m['die'] = dict(m['die'], w=W, mm2=round(W * m['die']['h'] / 1e6, 3), margin_mm2=round(858 - W * m['die']['h'] / 1e6, 3))
    m['tp8_spine'] = dict(sub_x=[xL, xM, xE], cw=cw, gap=gap, spine_w=round(xE + cw + gap - x0, 3), vm_xy=[vm.x, vm.y],
                          stack_dy=round(dy, 3), seq_su_xy=[sq.x, sq.y] if sq is not None else None, w_group_moved=sorted(mv[0]), w_group_dy=round(mv[1], 3), segment=list(seg0), moved_left_sub=[i.name for i in left_sub], die_w=W)


def selected(enabled=False, band=False, area_pins=False, b3r3=False, widen_um=500.0, spread=False, b3r6=False,
             tree_cols=0, bw_align=False, east_mirror=False, bw_edge=False, io_faces=False,
             bw_edge_inner=False, bw_sp=100.0, bw_x=20.0, edge_gap=0.0, slab_obs_top=7, m6_strip=0.0,
             slab_group_h=0.0, cdc=None, slab_pg=None, slab_w_per_mm2=0.646, strip_span=False, r18=False, r19=False,
             tree_interleave=False, corr_m9_adj=None, corr_um=None, bw_wp=0, su_core_clock=False, slab_bw_m8=False, relay_pitch=0.0, io_chan=0.0,
             su_vm_abut=False, rtl_finish=False, vm_me=False, tt_h=0.0, bl_h=0.0, strict_ports=False, rtl_bound_masters=None, port_exemptions=None, emb_hbm=False, before_relays=None, seam_free=False, station_word=0, tp8=None):
    if not enabled:
        raise ValueError('b3r2 selection is default off')
    if tp8:
        _tp8_globals(tp8)
    spec = importlib.util.spec_from_file_location('qfd_b3r2_private', F.__file__)
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    if io_chan:
        v.IO_CHAN = v.up(io_chan, v.GY)   # r22: IO-band routing channel above the top tile row
    # ---- Codex b3 selection (tools/qwen_rom_fulldie_b3.py selected()), unchanged
    old_vch = v.VCH
    v.VCH = v.up(260, v.GX)
    v.SPINE_W_R2 += v.VCH - old_vch
    v.LST_V = (v.VCH, v.LST_V[1])
    v.CORRIDOR_BITS = 388
    v.TAP_BITS = 325
    if station_word:
        # qwendie-1012 contract v5 D5: the closed station (ot_qwen_die_station a_d/b_d/t_d + a_r/b_r/t_r) and tile_nk
        # (ib 379 + ib_go 1 + xl 128) carry 508 data + ready = 509 bits per hop; the b3r2 compressed transport (323)
        # is implemented by no RTL.  The closed qfd_cst view has NO clock/reset bundle on its corridor or tap faces
        # (clk / rst_n are single W-face pins; the die clock comes from the die CTS plan to the 'ck' pin), so the
        # corridor and tap words are the 509-bit station word itself (388 = 323 + 65 carried a 64-clock + reset bundle
        # the station never had; 574 at pitch 2 = 55.1 um does not fit the 52.68 um station face, 509 = 48.9 um does).
        v.CORRIDOR_BITS = station_word
        v.TAP_BITS = station_word
    v.REGION_PG = {r: (.48 / PG.bump_pitch(c, 90) if c else 0.) for r, c in F.REGION_PG.items()}
    if tp8:
        _tp8_base(v, tp8)
    # ---- meso FIFO slots and F2 storage
    st_extra_um2 = (TAP_FIFO_BITS + F2_STATION_EXTRA_BITS) * FIFO_MM2_PER_BIT * 1e6
    st_extra_h = v.up(st_extra_um2 / v.CORR, v.GY)
    v.STATION = (v.CORR, v.STATION[1] + st_extra_h)
    sf_extra_h = v.up(STRIP_FIFO_BITS * FIFO_MM2_PER_BIT * 1e6 / v.FIFO[0], v.GY)
    v.FIFO = (v.FIFO[0], v.FIFO[1] + sf_extra_h)
    bw_mm2 = PORT_GROUPS * BW_FIFO_BITS * FIFO_MM2_PER_BIT
    v.SPINE_BLOCKS = [(n, (a + bw_mm2) if n == 'port_tiles' else a, d, s) for n, a, d, s in v.SPINE_BLOCKS]
    if su_core_clock:
        # r20g (coordinator 2026-10-06): the measured token cycles run the SU64/SFU and the vector memory on the 1.2 GHz
        # core clock (one clock in the RTL: ot_qwen_rom_core's u_su / VM ports), so the die puts them in the stream domain
        v.SPINE_BLOCKS = [(n, a, 'stream_1p2' if n in ('su64_sfu', 'vector_memory') else d, s)
                          for n, a, d, s in v.SPINE_BLOCKS]
    # r17: the band slab is 8 routed port-group elements (ot_qwen_slab_port_group, 777.576 x slab_group_h um each,
    # BW_FIFO=0) stacked in its column plus the 8 block-word meso FIFOs (meso_d4_v7, own element); default 0 keeps
    # the b3r16 area-derived slab (8 x 342.9 um)
    v.SLAB_GROUP_H = slab_group_h
    v.CDC = cdc
    v.STRIP_SPAN = strip_span or r18
    v.R18 = r18 or r19
    v.R19 = r19
    v.CORR_M9_ADJ = corr_m9_adj
    if r19:
        v.TILE_SLOT = (v.KV_TILE_W, v.TILE_SLOT[1])
        # qwen-tp8 coordinator DECISION 2026-10-12 12:15: the qfd_tile_nk cluster slot is 311.04 x 1296; tp8b's F2
        # column pitch (394.848) is slot + station corridor + a 31-um die channel, so the body keeps tile_body (it had
        # taken pitch - corridor = 342.12 and the die lost that channel over the M8+-only cluster)
        v.TILE_BODY_W = tp8['tile_body'] if tp8 and tp8.get('tile_body') and tp8.get('f2') else v.KV_TILE_W - v.CORR
    if corr_um:
        # r20e: a wider corridor (tree-word M9 legs crowd the corridors); the tile body keeps its width, the slot grows
        body = v.TILE_BODY_W
        v.CORR = corr_um
        v.STATION = (corr_um, v.STATION[1])
        v.TILE_SLOT = (round(body + corr_um, 6), v.TILE_SLOT[1])
    r18 = r18 or r19
    if r18:
        if not (cdc and slab_group_h):
            raise ValueError('r18 builds on the r17 die (--slab-group-h and --cdc)')
        v.STRIP_W = v.KVC_W
    if vm_me:
        if not (b3r3 and rtl_finish and su_vm_abut and slab_group_h):
            raise ValueError('r21m (vm_me) builds on r21f: b3r3, slab_group_h, su_vm_abut and rtl_finish')
        v.XCOL = VM_ME_XCOL          # a third spine column M (the base generator's x layout)
        v.R21M_TT_H, v.R21M_BL_H = tt_h, bl_h   # r21b: routed slot heights of the band tree top / band lanes (0: r21m)
        v.RELAY_RINGS = 400          # an off-corridor relay may sit up to ~3.5 mm from its path point (was 1.4)
    m = v.build(tree_mode='banded')
    _split_south(v, m)
    if b3r3:
        # b3r3: spine widened ~0.5 mm; one port+scale slab per band half (scale ROM inside its port slab, so the
        # scale bus is slab-internal); central blocks around the hub; constant ROM beside SU64
        w0 = m['geo']['spine_w_needed']
        w = v.up(w0 + widen_um, 2 * v.GX)
        if tp8:
            # qwen-tp8: the spine columns keep the TP4 777.6 um width (closed d2d_rom / su64_sfu / ctlm / slab views)
            w = round(2 * tp8.get('spine_cw', 777.6) + v.VCH, 3)
        m = v.build(spine_w=w, tree_mode='banded')
        m['geo']['spine_w_needed'] = w0
        m['geo']['b3r3_spine_w'] = w
        m['geo']['b3r3_widen_um'] = round(w - w0, 3)
        _split_south(v, m)
        if vm_me:
            _repack_r21m(v, m)
        else:
            _repack_b3r3(v, m)
    elif band:
        # the band repack loses the sub-group slivers of each interval: widen the spine on the 0.432 um lattice
        # until every slab packs (the step count is recorded with the die)
        w0 = m['geo']['spine_w_needed']
        for step in range(0, 400):
            m = v.build(spine_w=round(w0 + 4 * step * v.GX, 3), tree_mode='banded')
            m['geo']['spine_w_needed'] = w0
            _split_south(v, m)
            try:
                _repack_band(v, m)
            except SystemExit:
                continue
            m['geo']['band_repack_spine_w'] = round(w0 + 4 * step * v.GX, 3)
            m['geo']['band_repack_widen_um'] = round(4 * step * v.GX, 3)
            break
        else:
            raise SystemExit('band repack does not pack')
    if slab_group_h:
        # r17: the band slabs are their own PG/power region: measured routed element power (r6d 0.229 W in
        # 777.576 x 455.76 um = 0.646 W/mm2, 1.7x the spine's 0.385 W/mm2 reservation) and the die lattice's
        # coverage (tile field; r17b spine_slab IR at the hub's 2.5 % was 37.4 mV > 35)
        v.REGION_PG['slab'] = v.REGION_PG['tile_field'] if slab_pg is None else slab_pg
        v.REGION_W_PER_MM2 = dict(v.REGION_W_PER_MM2, slab=slab_w_per_mm2)
        for it in m['insts']:
            if it.kind == 'spine_block' and it.master.startswith('qfd_port_tiles'):
                m['regions'].append(dict(name=f'slab_{it.name[3:]}', kind='slab',
                                         rect=[it.x, it.y, it.x + it.w + v.SHAVE, it.y + it.h + v.SHAVE]))
    if edge_gap:
        _edge_gap(v, m, edge_gap)
    if east_mirror:
        _east_mirror(v, m)
    if TP8 and TP8.get('root_spread'):
        _root_spread(v, m)
    groups = _group_map(v, m)
    _spine_buses(v, m, groups)
    if bw_align:
        by = {i.name: i for i in m['insts']}
        ry, rx = {}, {}
        for bid, cl, bits, eps in m['buses']:
            if bid.startswith('bword_'):
                (root, _), (slab, pin) = eps
                ry.setdefault(slab, {})[int(pin[2:])] = by[root].y + by[root].h / 2
                rx.setdefault(slab, {})[int(pin[2:])] = by[root].x + by[root].w / 2
        m['b3r8_root_y'] = ry
        m['b3r8_root_x'] = rx
    m['strict_ports'] = bool(strict_ports)
    m['rtl_bound_masters'] = rtl_bound_masters
    m['port_exemptions'] = port_exemptions or {}
    m['clock_regions'] = clock_regions(v, m)
    m['die']['budget_mm2'] = 858
    m['die']['margin_mm2'] = round(858 - m['die']['mm2'], 3)
    m['b3r2'] = dict(station_frame_um=list(v.STATION), station_extra_h_um=st_extra_h, strip_fifo_frame_um=list(v.FIFO),
                     strip_fifo_extra_h_um=sf_extra_h, bw_fifo_mm2=round(bw_mm2, 4), band=band or b3r3, b3r3=b3r3,
                     groups=groups)
    _wrap_masters(v, m, area_pins, ns_faces=b3r3, spread=spread or b3r6, channel=b3r6, bw_align=bw_align,
                  bw_edge=bw_edge, bw_edge_inner=bw_edge_inner, bw_sp=bw_sp, bw_x=bw_x)
    m['b3r2']['b3r14_edge_gap_um'] = m['geo'].get('edge_gap_um', 0.0)
    m['b3r2']['b3r13_bw_sp_um'] = bw_sp
    m['b3r2']['b3r13_bw_x_um'] = bw_x
    m['b3r2']['spread_pins'] = spread or b3r6
    m['b3r2']['b3r6_channel_pins'] = b3r6
    if tree_cols:
        _tree_cols(v, tree_cols, interleave=tree_interleave)
    m['b3r2']['b3r7_tree_pin_columns'] = tree_cols
    m['b3r2']['r20_tree_pin_interleave'] = tree_interleave
    m['b3r2']['r20_corridor_m9_adjustment'] = corr_m9_adj
    m['b3r2']['r20e_corridor_um'] = corr_um
    m['b3r2']['b3r8_bw_align'] = bw_align
    m['b3r2']['b3r9_east_mirror'] = east_mirror
    m['b3r2']['b3r10_bw_edge'] = bw_edge
    if slab_obs_top != 7 or m6_strip:
        _slab_entry(v, slab_obs_top, m6_strip)
    m['b3r2']['r21_slab_bw_m8'] = slab_bw_m8
    m['b3r2']['b3r15_slab_obs_top'] = slab_obs_top
    m['b3r2']['b3r15_m6_strip_um'] = m6_strip
    if io_faces:
        _io_faces(v)
    m['b3r2']['b3r11_io_faces'] = io_faces
    m['b3r2']['b3r12_bw_edge_inner'] = bw_edge_inner
    m['b3r2']['area_pins'] = area_pins
    m['b3r2']['r20f_bw_waypoint_every_cols'] = bw_wp
    m['b3r2']['r20g_su_vm_core_clock'] = su_core_clock
    if bw_wp:
        _bw_waypoints(v, m, bw_wp)
    if r18:
        _r18_post(v, m)
    if slab_bw_m8:
        _slab_bw_m8(v)            # outermost: after every other slab-pin rule (io_faces, r18)
    if rtl_finish:
        _rtl_finish(v, m)     # before the relays: the new / moved words get their relay chains
    m['b3r2']['r21f_rtl_finish'] = rtl_finish
    if vm_me:
        _vm_me(v, m)          # before the relays (the result / lane words get their relay chains)
    m['b3r2']['r21m_vm_me'] = vm_me
    if emb_hbm:
        _emb_hbm(v, m)        # before the relays: the SU <-> hub embedding words get their relay chains
    m['b3r2']['r21c_emb_hbm'] = emb_hbm
    if tp8 and before_relays is not None:
        _br0 = before_relays

        def before_relays(v_, m_):
            _br0(v_, m_)
            if TP8.get('spine_gap'):
                _tp8_spine(v_, m_)
            _tp8_io(v_, m_)
            if TP8.get('f2'):
                _tp8b_f2(v_, m_)
                if TP8['f2'].get('kv'):
                    _tp8b_kv(v_, m_)
                if TP8['f2'].get('v5'):
                    from qwen_kv_die import tp8b_v5 as _V5
                    _V5.apply(v_, m_, sys.modules[__name__])
    if before_relays is not None:
        # Opt-in system composition: actual slots/ports precede relay discovery.
        # Default recipes retain their existing geometry and master contracts.
        before_relays(v, m)
    if seam_free:
        _seam_free(v, m)      # after every pin-plan rule, before the relays (they are derived from the moved pins)
    m['b3r2']['r22ks_seam_free'] = seam_free
    if before_relays is not None:
        _regions_from_placement(m)   # the surgery moved blocks: region clocks follow the FINAL placement
    if relay_pitch:
        _io_south(v)
        if getattr(v, 'V5_FINAL_MASTERS', None):
            # r9: the v5 pin rules that must have the last word (closed views pin for pin, abutted bundles pin to pin,
            # credit pins beside their words) run after every other pin-plan wrapper and before the relay plan
            _bm = v.masters

            def _mfinal(model, k=1, port_bits=None, _bm=_bm):
                o = _bm(model, k, port_bits)
                v.V5_FINAL_MASTERS(model, o, k)
                return o
            v.masters = _mfinal
        _corr0 = v.CORR
        if m.get('corridor_lanes'):
            v.CORR = min(w_ for _, w_ in m['corridor_lanes'])
        try:
            _relays(v, m, relay_pitch)
        finally:
            v.CORR = _corr0
        if getattr(v, 'RELAY_REACH_GATE', False):   # tp8b (die timing by construction)
            _reset_tree(v, m)     # after the relays: legalised against the FINAL placement
        if before_relays is not None:
            _regions_from_placement(m)   # the relays joined region clocks: re-file + split to the measured cap again
    m['b3r2']['r21_relay_pitch_um'] = relay_pitch
    if su_vm_abut:
        # outermost: after the relays (an abutted bus takes no relay); r21m: the banked memory's descriptor ports
        _su_vm_bus(v, m, *((SU_VM_A_BITS_BV, SU_VM_Q_BITS) if vm_me else (SU_VM_A_BITS, SU_VM_Q_BITS)))
    m['b3r2']['r21v_su_vm_abut'] = su_vm_abut
    if before_relays is not None and getattr(v, 'FACE_PACK_FINAL', False):
        _face_pack_final(v, m)   # outermost: after every pin-moving wrapper
    return v, m


def _face_pack_final(v, m):
    """qwendie-1011 (r22ko4 audit): no two face pin groups of one master may overlap on one face + layer.  _despan
    (inside the surgery) only slides forward and gives up at the face end; later wrappers (seam-free) move pins after
    it.  This outermost pass packs every face + layer forward, then backward from the face end when the forward pack
    overflows; pinned (abutted pair) groups never move; any overlap left raises."""
    inner = v.masters
    pinned = getattr(v, 'PINNED_FACE_PORTS', set())
    rec = m['b3r2'].setdefault('face_pack_final', [])
    gap = 0.1   # only real overlaps move (already-legal groups keep their place: abutted pairs stay aligned)

    def masters(model, k=1, port_bits=None):
        M = inner(model, k, port_bits)
        for name, mst in M.items():
            groups = {}
            for p in dict.fromkeys(mst.order):     # a port can appear twice in order (re-added by a later wrapper)
                s = mst.ports.get(p)
                if s and s[0] == 'face':
                    groups.setdefault((s[2], s[3]), []).append(p)
            for (face, layer), ps in groups.items():
                L_ = mst.h if face in 'EW' else mst.w
                G = sorted(([p, mst.ports[p][4], mst.ports[p][1] * mst.ports[p][5] * 0.048 / 2] for p in ps),
                           key=lambda g: g[1])
                fix = lambda g: (name, g[0]) in pinned   # noqa: E731
                for _ in range(3):
                    for a, b in zip(G, G[1:]):       # forward
                        need = a[1] + a[2] + gap + b[2]
                        if b[1] < need:
                            if fix(b) and not fix(a):
                                a[1] = b[1] - b[2] - gap - a[2]
                            elif not fix(b):
                                b[1] = need
                    end = L_                          # backward from the face end
                    for g in reversed(G):
                        if g[1] + g[2] > end - 0.5 and not fix(g):
                            g[1] = end - 0.5 - g[2]
                        end = g[1] - g[2] - gap
                    G.sort(key=lambda g: g[1])
                bad = [(a[0], b[0]) for a, b in zip(G, G[1:]) if b[1] - b[2] < a[1] + a[2] - 1e-6] + \
                      [(g[0], 'face end') for g in G if g[1] - g[2] < -1e-6 or g[1] + g[2] > L_ + 1e-6]
                if bad:
                    raise ValueError(f'{name} {face}/{layer}: face groups do not fit: {bad[:4]}')
                for g in G:
                    kind, bits, f, ly, c, pitch = mst.ports[g[0]]
                    if abs(c - g[1]) > 1e-6:
                        mst.ports[g[0]] = (kind, bits, f, ly, round(g[1], 3), pitch)
                        if len(rec) < 400:
                            rec.append((name, g[0], face, layer, round(c, 3), round(g[1], 3)))
        return M
    v.masters = masters


# r21v (qwen-split-exact 2026-10-07): the stream unit <-> vector memory bus.  ot_qwen_rom_core's u_su reads three
# operands (va / vb / vc: per lane re + AW-bit address out, FP32 back) and writes one (vm_we / vm_waddr / vm_wdata)
# per lane, SW = 64, AW = 24: 3 x (64 + 1,536) + (64 + 1,536 + 2,048) = 8,448 bits SU -> VM and 3 x 2,048 = 6,144
# bits VM -> SU (14,592).  The reads are FIXED-LATENCY (the lane captures va/vb/vc_q one edge after re: the vector
# memory's registered output), so the bus takes NO pin station: the two masters abut face to face (SU64 N face on
# the VM S face, b3r3 _repack_b3r3 stacks them in the W spine column) and every bit is an abutted M5 pin pair at
# the same x (one M5 track each, both masters 777.576 um wide, R0).  The VM's read data leaves its output register
# (owner rule: capture flop at the macro); the SU's write / address bits leave the lane's registers.
SU_VM_A_BITS = 3 * (64 + 64 * 24) + (64 + 64 * 24 + 64 * 32)      # 8,448 SU -> VM
SU_VM_Q_BITS = 3 * 64 * 32                                        # 6,144 VM -> SU
SU_VM_ABUT_TOL_UM = 0.05                                          # the generator's SHAVE gap (0.024 um) + rounding


def _su_vm_bus(v, m, a_bits=None, q_bits=None):
    SU_VM_A_BITS = a_bits if a_bits is not None else globals()['SU_VM_A_BITS']   # noqa: N806
    SU_VM_Q_BITS = q_bits if q_bits is not None else globals()['SU_VM_Q_BITS']   # noqa: N806
    by = {i.name: i for i in m['insts']}
    su, vm = by['sp_su64_sfu'], by['sp_vector_memory']
    # contract v5 (r8): the bit-plane VM region sits N of the tree top; the SU abuts its N face (R0: an MX master's M8
    # clock pins are not mirror-legal): the SU takes va / vq on its S face, the VM sa / sq on N
    north = bool(getattr(v, 'SU_VM_NORTH', False))
    gap = (su.y - (vm.y + vm.h)) if north else vm.y - (su.y + su.h)
    # qwendie-1011: a VM wider than the SU (r22ko4 near-square slot) abuts with the SU inside its S face; the pin
    # groups shift by the SU's offset (0 for every equal-width recipe: unchanged)
    off = round(su.x - vm.x, 4) if vm.w > su.w + 1e-6 else 0.0
    if abs(su.x - vm.x - off) > 1e-6 or not (-1e-6 <= off and su.x + su.w <= vm.x + vm.w + 1e-6) \
            or (off == 0.0 and abs(su.w - vm.w) > 1e-6) or not (0.0 <= gap <= SU_VM_ABUT_TOL_UM) \
            or su.orient != 'R0' or vm.orient != 'R0':
        raise ValueError(f'su_vm_abut: SU64 {su.x:.3f},{su.y:.3f} {su.w:.3f}x{su.h:.3f} {su.orient} and VM '
                         f'{vm.x:.3f},{vm.y:.3f} {vm.w:.3f}x{vm.h:.3f} {vm.orient} do not abut (gap {gap:.3f} um): '
                         'route the bus with relay stations and matching RTL latency instead')
    if su.domain != vm.domain:
        raise ValueError(f'su_vm_abut: SU64 ({su.domain}) and VM ({vm.domain}) in different clock domains')
    m['buses'] += [('su_vm_a', 'spine_local', SU_VM_A_BITS, [('sp_su64_sfu', 'va'), ('sp_vector_memory', 'sa')]),
                   ('su_vm_q', 'spine_local', SU_VM_Q_BITS, [('sp_vector_memory', 'sq'), ('sp_su64_sfu', 'vq')])]
    w = su.w
    p = 0.048                                       # M5 track (qwen_rom_fulldie TRK)
    a_span, q_span = SU_VM_A_BITS * p, SU_VM_Q_BITS * p
    lo = 2.0                                        # um clear of the face corners and between the two groups
    a_c = lo + a_span / 2
    q_c = lo + a_span + lo + q_span / 2
    if lo + a_span + lo + q_span > w - lo:
        raise ValueError(f'su_vm_abut: {SU_VM_A_BITS + SU_VM_Q_BITS} M5 pins do not fit the {w:.3f} um face')
    base = v.masters

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        s, q = out['qfd_sp_su64_sfu'], out['qfd_sp_vector_memory']
        if model.get('native_control_contract'):
            # Native controller retired the legacy VM request/ready service.
            # These are unbound abstract pins, not a reusable physical view.
            for retired in ('xd', 'xr'):
                q.ports.pop(retired, None)
                q.order[:] = [x_ for x_ in q.order if x_ != retired]   # not 'p': py3.12+ inlined comprehension
        for M_, f, mine in ((s, 'S' if north else 'N', ('va', 'vq')), (q, 'N' if north else 'S', ('sa', 'sq'))):
            for pn in mine:                 # the base wrapper's default pin group for the new bus: replaced here
                if pn in M_.ports:
                    M_.ports.pop(pn)
                    M_.order.remove(pn)
            # qwen-tp8 v2: a VM wider than the SU may carry other pin groups on its S face outside the SU's span
            # (seq_su's all-reduce words rise beside the SU into the VM's S face E of it); anything inside the
            # abutted span is still refused
            lo_f, hi_f = (off, off + su.w) if M_ is q else (0.0, su.w)
            taken = [pn for pn, sp in M_.ports.items() if sp[0] == 'face' and sp[2] == f
                     and sp[4] + sp[1] * p * sp[5] / 2 + lo > lo_f and sp[4] - sp[1] * p * sp[5] / 2 - lo < hi_f]
            if taken:
                raise ValueError(f'su_vm_abut: {M_.name} {f} face already holds {taken}')
        s.face('va', SU_VM_A_BITS, 'S' if north else 'N', 'M5', a_c, 1)
        s.face('vq', SU_VM_Q_BITS, 'S' if north else 'N', 'M5', q_c, 1)
        q.face('sa', SU_VM_A_BITS, 'N' if north else 'S', 'M5', a_c + off, 1)
        q.face('sq', SU_VM_Q_BITS, 'N' if north else 'S', 'M5', q_c + off, 1)
        return out
    v.masters = masters
    m['r21v_su_vm'] = dict(bits_su_to_vm=SU_VM_A_BITS, bits_vm_to_su=SU_VM_Q_BITS, gap_um=round(gap, 4),
                           face_um=round(w, 3), layer='M5', pitch_tracks=1,
                           a_span_um=[round(a_c - a_span / 2, 3), round(a_c + a_span / 2, 3)],
                           q_span_um=[round(q_c - q_span / 2, 3), round(q_c + q_span / 2, 3)],
                           stations=0, rtl_latency_added=0, **({'vm_face_offset_um': off} if off else {}))


# r21f (qwen-rtl-finish 2026-10-07): the abstracts of the three masters whose RTL was finished
# (rtl/qwen_sys/rtl_finish_20261007) and of the re-cut sequencer / SU (split-exact), from the RTL port lists:
#   qfd_sp_tree_top  ot_qfd_sp_tree_top: the spine CONTROL element.  Issue in from the sequencer (si: go + the 379 ME
#                    fields + x_rdy's peer is the VM), status out (so: ready, idle, progress, ov, argmax, wrom / kv
#                    strobes, fault), the x descriptor (xd: 53 b) and the per-slot maxima write (mx: 553 b) to the VM,
#                    x_rdy (xr) from the VM, and per band slab the lane / port-element control (c<b>: the per-level tree
#                    selects / valids and the port-element tags, broadcast, + the band's share of the scale requests)
#                    and its returns (f<b>: the band's port-element argmax nodes and faults + lane faults).
#                    The tree words (pword_*) and the result word (tt_res) keep their r21 path as the RESULT path:
#                    the band result serializer and the 6:1 result-row merge onto the VM row write port are NOT yet RTL
#                    (m['r21f']['open']).
#   qfd_sp_vector_memory  ot_qfd_sp_vector_memory: + xd / xr / mx; the embedding word moves to the SU (em dropped).
#   qfd_io_embedding_rom  ot_qfd_io_embedding_rom root: request {v, kind, 24-b address} + credit return; response
#                    {v, 512 b}; its requester is the SU (row buffer), not the sequencer.
#   qfd_sp_constants_sequencer / qfd_sp_su64_sfu  the embedding request leaves from the SU (ea / ecr / eq), the
#                    sequencer's ea / md ports go; seq <-> tree top issue / status (ti / ts).
TT_ISSUE_BITS = 1 + 3 * 18 + 13 * 24 + 13          # go + ot_qwen_me_spine fields (NW = 18): 380
TT_STATUS_BITS = 1 + 1 + 16 + 1 + 18 + 32 + 1 + 1 + 1 + 24 + 1     # ready idle progress ov am_idx am_val am_any wrom_re kv_re wrom_addr fault
TT_XD_BITS = 1 + 24 + 24 + 4
TT_MX_BITS = 1 + 24 + 16 + 512
TT_BAND_C_BITS = 2 * 14 + 1 + 113 + (1 + 8 + 8 * 24)   # selects + valids, tag valid + fields, the band's 8 scale requests
TT_BAND_F_BITS = 2 * 51 + 2 + 3                         # 2 port elements' argmax nodes + faults, lane faults
EMB_REQ_BITS, EMB_RSP_BITS = 1 + 1 + 24, 1 + 512


def _rtl_finish(v, m):
    B = []
    for bid, cl, bits, eps in m['buses']:
        if bid == 'seq_done':
            continue                                   # replaced by the tree top's status word
        if bid == 'emb_a':
            eps = [('sp_su64_sfu', 'ea') if e == ('sp_constants_sequencer', 'ea') else e for e in eps]
            bits = EMB_REQ_BITS
        if bid == 'emb':
            eps = [('sp_su64_sfu', 'eq') if e == ('sp_vector_memory', 'em') else e for e in eps]
            bits = EMB_RSP_BITS
        B.append((bid, cl, bits, eps))
    B += [('tt_si', 'sequencer', TT_ISSUE_BITS, [('sp_constants_sequencer', 'ti'), ('sp_tree_top', 'si')]),
          ('tt_so', 'sequencer', TT_STATUS_BITS, [('sp_tree_top', 'so'), ('sp_constants_sequencer', 'ts')]),
          ('tt_xd', 'tree_spine', TT_XD_BITS, [('sp_tree_top', 'xd'), ('sp_vector_memory', 'xd')]),
          ('tt_xr', 'tree_spine', 1, [('sp_vector_memory', 'xr'), ('sp_tree_top', 'xr')]),
          ('tt_mx', 'tree_spine', TT_MX_BITS, [('sp_tree_top', 'mx'), ('sp_vector_memory', 'mx')]),
          ('emb_cr', 'io', 1, [('io_embedding_rom', 'acr'), ('sp_su64_sfu', 'ecr')])]
    for b in range(BANDS):
        B += [(f'tt_c{b}', 'tree_spine', TT_BAND_C_BITS, [('sp_tree_top', f'c{b}'), (f'sp_port_tiles_{b}', 'tc')]),
              (f'tt_f{b}', 'tree_spine', TT_BAND_F_BITS, [(f'sp_port_tiles_{b}', 'tf'), ('sp_tree_top', f'f{b}')])]
    m['buses'] = B
    m['r21f'] = dict(
        rtl={'qfd_sp_tree_top': 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv ot_qfd_sp_tree_top',
             'qfd_sp_vector_memory': 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv ot_qfd_sp_vector_memory',
             'qfd_io_embedding_rom': 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_io_embedding_rom.sv ot_qfd_emb_root (+ taps)',
             'qfd_sp_su64_sfu': 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv ot_qfd_sp_su64_sfu_ab',
             'qfd_sp_constants_sequencer': 'rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer.sv'},
        open=['ME result path: band result serializer + tree-top 6:1 result-row merge onto the VM row write port (the '
              'pword_* / tt_res words keep their r21 path)',
              'tree lanes (qfd_sp_tree_lane x16) and port elements: placed in the band slabs (c<b> / f<b> carry their '
              'control); their t_lvl / y words inside the slab region are not die buses here',
              'VM area: the banked master needs ~2.4 mm2 (777.6 x 3110.4 or 1555.2 square route variants) against the '
              'r21 0.725 mm2 slab; the spine column is not re-packed in this recipe',
              'SU <-> VM 3 x 64 scalar fixed-latency lane ports (r21v abutted bus): not served by the banked VM'])
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        tt, vm, sq, su, em = (o['qfd_sp_tree_top'], o['qfd_sp_vector_memory'], o['qfd_sp_constants_sequencer'],
                              o['qfd_sp_su64_sfu'], o.get('qfd_io_embedding_rom'))   # r21c: no embedding ROM
        for M_, gone in ((tt, ('md',)), (vm, ('em',)), (sq, ('ea', 'md'))):
            for pn in gone:
                if pn in M_.ports:
                    M_.ports.pop(pn)
                    M_.order.remove(pn)
        # tree top: issue / status on the E face (the sequencer column), band control on the W face (the slabs),
        # VM words on the S face (the VM is below in the W spine column)
        tt.face('si', TT_ISSUE_BITS, 'E', 'M4', tt.h - 150.0, 2)
        tt.face('so', TT_STATUS_BITS, 'E', 'M4', tt.h - 60.0, 2)
        tt.face('xd', TT_XD_BITS, 'S', 'M5', 100.0, 2)
        tt.face('xr', 1, 'S', 'M5', 140.0, 2)
        tt.face('mx', TT_MX_BITS, 'S', 'M5', 400.0, 1)
        for b in range(BANDS):
            tt.face(f'c{b}', TT_BAND_C_BITS, 'W', 'M4', 150.0 + b * 480.0, 1)
            tt.face(f'f{b}', TT_BAND_F_BITS, 'W', 'M4', 150.0 + b * 480.0 + 220.0, 1)
        vm.face('xd', TT_XD_BITS, 'N', 'M5', 640.0, 1)
        vm.face('xr', 1, 'N', 'M5', 670.0, 1)
        vm.face('mx', TT_MX_BITS, 'E', 'M4', vm.h * 0.75, 1)
        sq.face('ti', TT_ISSUE_BITS, 'W', 'M4', 2600.0, 2)
        sq.face('ts', TT_STATUS_BITS, 'W', 'M4', 2700.0, 2)
        su.face('ea', EMB_REQ_BITS, 'W', 'M4', 1500.0, 2)
        su.face('ecr', 1, 'W', 'M4', 1520.0, 2)
        su.face('eq', EMB_RSP_BITS, 'W', 'M4', 1300.0, 1)
        if em is not None:
            if 'a' in em.ports:
                em.ports['a'] = em.ports['a'][:1] + (EMB_REQ_BITS,) + em.ports['a'][2:]
            if 'o' in em.ports:
                em.ports['o'] = em.ports['o'][:1] + (EMB_RSP_BITS,) + em.ports['o'][2:]
            em.face('acr', 1, 'S', 'M5', em.w - 200.0, 1)
        for b in range(BANDS):
            mn = f'qfd_port_tiles_{b}'
            if mn in o:
                P = o[mn]
                P.face('tc', TT_BAND_C_BITS, 'E', 'M4', 400.0, 1)
                P.face('tf', TT_BAND_F_BITS, 'E', 'M4', 400.0 + TT_BAND_C_BITS * 0.048 / 2 + TT_BAND_F_BITS * 0.048 / 2 + 10.0, 1)
        return o
    v.masters = masters


# r21m (qwen-vm-me 2026-10-08): the spine re-packed for the RTL of rtl/qwen_sys/vm_me_20261008.
#   column M        a third spine column (VM_ME_XCOL wide): the die grows by VM_ME_XCOL (on the reticle budget: r21f
#                   821.3 mm2 + 0.78 x 32.8 = ~846.8 <= 858) instead of squeezing the two columns.  The columns are
#                   W | VCH | M | E: the outer two keep the band-half slabs beside their tile arrays (no block word
#                   crosses the spine), the middle one holds the vector memory, the stream unit and the sequencer.
#   vector memory   qfd_sp_vector_memory_bv (copy 0 = 64 banks x 2 ot_sram_1r1w_256x256 for the x beats, 3 SU replica
#                   copies of 16 banks x 2 ot_sram_1r1w_1024x256, the bank-write arbiter, skid queues, the 6:1 result
#                   merge): 2.09 mm2 of macros, slot 777.6 x VM_BV_H in column M with the stream unit
#                   qfd_sp_su64_sfu_bv abutted below it (descriptor SU <-> VM bus, no stations), centred on the hub.
#   tree lanes      per band, qfd_sp_band_lanes (the 16 lanes' tree levels TCUT+1..TCUT+3 over the band's 8 level-
#                   TCUT positions, 7 FP32 adders a lane), stacked on the band's W primary slab (the band's level-TCUT
#                   words in, tw, and its result-position words out, ty, 4,096 b each, abutted); the band word (one
#                   position, 512 b: pword) goes to the tree top, which holds levels TCUT+4.. across the 6 bands and
#                   returns the 3 positions of splits SMAX-1 / SMAX to band 0 (tt_ty, 1,536 b).  The 16 monolithic
#                   lanes of the qwen-rtl-finish partition (ot_qwen_spine_lane over all 48 positions, no wire stage to
#                   the port elements) do not fit the die: 16 x 6 x 2 x 256 b of unstaged words across 31 mm.  OPEN:
#                   the per-band lane RTL (ot_qwen_spine_lane cut by position range; the tree top's levels above).
#   port elements   the band slabs: each half (qfd_port_tiles_<b> / _f1, 8 slab port-group elements) hosts one W12 port
#                   element pair's result groups with their scale banks (r17); the slab primary is the band's port
#                   element host for the lane and result words.
#   band serializer qfd_sp_res_ser x 6 (ot_qfd_res_ser: 8 x ot_sram_1r1w_64x512 + flops), one per band abutted
#                   below its W primary slab: the band's result slots in (rq, 4,425 b, abutted), credit / valid beats
#                   to the memory's merge (rs, 551 b), credit back (rc), rok (rk) to the memory's me_ok AND.
#   words           pword_* (slab -> tree top result word) and tt_res (tree top -> VM) are gone: results go slab ->
#                   serializer -> VM; tt_land (VM -> tree top landed-burst count, 16 b) and vm_meok (VM -> sequencer
#                   me_mem_ok term) are new.
VM_ME_XCOL = 777.6
VM_BV_H = 6220.8          # 777.6 x 6,220.8 = 4.84 mm2: 2.09 mm2 macros (43 %) + the x path / SU replica / write logic
SU_BV_H = 2058.48         # ot_qfd_sp_su64_sfu_bv: ot_qfd_sp_su64_sfu_ab's slot (the lanes / embedding buffer unchanged)
LANE_WH = 600.048         # qfd_sp_tree_lane (physical/qwen_die_masters/cfg/qfd_sp_tree_lane.env): 46 adders in 0.36 mm2
BL_H = 1131.84            # qfd_sp_band_lanes: 16 lanes x 7 adders = 112 / 46 x 0.36 mm2 = 0.88 mm2 in a 777.6 column
SER_H = 518.4             # qfd_sp_res_ser: 8 x 171.288 x 77.784 macros + ~30 k flops in 777.6 x 518.4 (0.40 mm2)
NLANES = 16
LANE_C_BITS = 2 * 14      # t_sel_e / t_tv_e ([$clog2(GT):0] each, GT = 6,144)
LANE_W_BITS = 8 * 16 * 32  # a band's 8 level-TCUT positions x 16 lanes (tw in / ty out of the band lanes)
TT_TY_BITS = 3 * 16 * 32 + 2   # the tree top's top-level positions (splits SMAX-1 / SMAX) back to band 0 + use / valid
SER_I_BITS = 8 * (24 + 16 + 512) + 8 + 1   # 8 slots {addr, mask, data} + we + ov
SER_O_BITS = 1 + 1 + 1 + 20 + 16 + 512     # v, end, nul, row, mask, data
SU_VM_A_BITS_BV = 3 * (1 + 1 + 24 + 24) + (64 + 24 + 24 + 64 * 32) + (1 + 24 + 32)   # descriptors + lane writes + reducer
LAND_BITS = 16


def _repack_r21m(v, m):
    """r21m spine: tree top above the hub (W) as b3r3; in the middle column M the banked VM centred on the hub, the
    stream unit abutted below it and the sequencer below that; the band slabs (r17: W / E halves in the outer columns,
    M as overflow); each band's W primary is a stack: result serializer, slab, band-lane block (all abutted)."""
    g = m['geo']
    cw = g['cw']
    hub = m['hub']
    m['insts'] = [i for i in m['insts'] if i.kind != 'spine_block']
    cols, free = _spine_free(v, m, [])
    spans = {c: [list(iv) for iv in ivs] for c, ivs in free.items()}
    area = {n: a for n, a, *_ in v.SPINE_BLOCKS}
    dom = {n: d for n, a, d, *_ in v.SPINE_BLOCKS}
    hh = lambda mm2: v.up(mm2 * 1e6 / cw, v.GY)   # noqa: E731
    parts = []

    def put(name, master, col, y, h, domain='stream_1p2', w=None):
        it = v.Inst(name, master, cols[col], y, (cw if w is None else w) - v.SHAVE, h - v.SHAVE, kind='spine_block',
                    region='hub', domain=domain)
        m['insts'].append(it)
        return it
    hub_lo, hub_hi = hub.y, hub.y + hub.h + v.SHAVE
    hub_c = (hub_lo + hub_hi) / 2
    tt_h = getattr(v, 'R21M_TT_H', 0.0)
    h_tt = v.up(tt_h, v.GY) if tt_h else hh(area['tree_top'])
    h_cs = hh(area['constants_sequencer'])
    h_vm, h_su = v.up(VM_BV_H, v.GY), v.up(SU_BV_H, v.GY)
    if tt_h:
        # r21b: the band tree top (777.6 x 3,732.48 / 4,354.56) no longer fits W above the hub without pushing band 3's
        # serializer / slab / band-lane stack out of its column; it moves to M on top of the VM (its x_ / mx_ /
        # land_cnt face is the bottom one, toward the VM).  SU + VM + tree top are one stack in M, VM centred on the
        # hub where the interval allows (else the least shift down), the sequencer below as before.
        y_st = _place_near(v, free, 'M', h_su + h_vm + h_tt, hub_c - h_su / 2 + h_tt / 2)
        y_su, y_vm = y_st, y_st + h_su
        y_tt, tt_col = y_vm + h_vm, 'M'
        m['geo']['r21b_vm_shift_um'] = round((y_vm + h_vm / 2) - hub_c, 3)
    else:
        y_tt, tt_col = _place_near(v, free, 'W', h_tt, hub_hi + h_tt / 2), 'W'
        y_st = _place_near(v, free, 'M', h_vm + h_su, hub_c - h_su / 2)       # SU + VM stack: VM centred on the hub
        y_su, y_vm = y_st, y_st + h_su
    y_cs = _place_near(v, free, 'M', h_cs, y_su - h_cs / 2)              # the sequencer below the SU (constant ROM)
    put('sp_vector_memory', 'qfd_sp_vector_memory', 'M', y_vm, h_vm, dom['vector_memory'])
    put('sp_su64_sfu', 'qfd_sp_su64_sfu', 'M', y_su, h_su, dom['su64_sfu'])
    put('sp_tree_top', 'qfd_sp_tree_top', tt_col, y_tt, h_tt, dom['tree_top'])
    put('sp_constants_sequencer', 'qfd_sp_constants_sequencer', 'M', y_cs, h_cs, dom['constants_sequencer'])
    for n, y, h, c in (('vector_memory', y_vm, h_vm, 'M'), ('su64_sfu', y_su, h_su, 'M'), ('tree_top', y_tt, h_tt, tt_col),
                       ('constants_sequencer', y_cs, h_cs, 'M')):
        parts.append(dict(name=n, col=c, y=round(y, 3), h=h))
    # band slabs (r17 over W / E / M, held to their band's column segment); the W primary carries the serializer
    # below it and the band-lane block above it
    rows = g['row_y']
    tgt = [_band_tgt(v, rows, b) for b in range(BANDS)]
    order = sorted(range(BANDS), key=lambda b: abs(tgt[b] - g['mid']))
    m['band_slabs'] = {}
    per = PORT_GROUPS // (2 * BANDS)
    m['geo']['slab_group_h_um'] = v.SLAB_GROUP_H
    rpg = RTL_PORT_GROUPS // (2 * BANDS)                       # result-port groups per half (4) for per (8) block words
    m['geo']['slab_h_um'] = v.up(rpg * v.SLAB_GROUP_H + per * BW_FIFO_BITS * FIFO_MM2_PER_BIT * 1e6 / cw, v.GY)
    m['geo']['slab_port_groups'] = dict(result_groups=RTL_PORT_GROUPS, per_half=rpg, block_words=PORT_GROUPS, bw_per_half=per)
    bl_h = getattr(v, 'R21M_BL_H', 0.0) or BL_H
    m['geo']['r21m_slots_um'] = dict(tree_top=h_tt, band_lanes=v.up(bl_h, v.GY), res_ser=v.up(SER_H, v.GY))
    _repack_r17(v, m, free, put, parts, tgt, order, cw, spans, lanes_h=v.up(bl_h, v.GY), ser_h=v.up(SER_H, v.GY),
                rtl_groups=True)
    m['geo']['spine_parts_r21m'] = parts
    m['geo']['spine_free_after_um'] = {c: [[round(a, 1), round(b_, 1)] for a, b_ in iv] for c, iv in free.items()}
    m['geo']['x_col_m'] = cols['M']


def _vm_me(v, m):
    """r21m buses and abstracts (see the r21m comment above)."""
    gm = m['b3r2']['groups']
    prim = gm['primary']
    B = []
    for bid, cl, bits, eps in m['buses']:
        if bid == 'tt_res':
            continue
        if bid.startswith('pword_'):           # the band word now leaves the band-lane block (+ its valid)
            b = int(bid.split('_')[1])
            eps = [(f'sp_band_lanes_{b}', 'pw')] + list(eps[1:])
            bits = bits + 1
        B.append((bid, cl, bits, eps))
    for b in range(BANDS):
        bl = f'sp_band_lanes_{b}'
        B += [(f'tw_{b}', 'tree_spine', LANE_W_BITS, [(prim[b], 'tw'), (bl, 'tw')]),
              (f'ty_{b}', 'tree_spine', LANE_W_BITS, [(bl, 'ty'), (prim[b], 'ty')]),
              (f'tt_lc{b}', 'tree_spine', LANE_C_BITS, [('sp_tree_top', f'lc{b}'), (bl, 'c')]),
              (f'tt_lf{b}', 'tree_spine', 1, [(bl, 'f'), ('sp_tree_top', f'lf{b}')])]
    B.append(('tt_ty', 'tree_spine', TT_TY_BITS, [('sp_tree_top', 'ty'), ('sp_band_lanes_0', 'tt')]))
    for b in range(BANDS):
        sr = f'sp_res_ser_{b}'
        B += [(f'rq_{b}', 'tree_spine', SER_I_BITS, [(prim[b], 'rq'), (sr, 'i')]),
              (f'rs_{b}', 'tree_spine', SER_O_BITS, [(sr, 'o'), ('sp_vector_memory', f'rb{b}')]),
              (f'rc_{b}', 'tree_spine', 1, [('sp_vector_memory', f'rc{b}'), (sr, 'cr')]),
              (f'rk_{b}', 'tree_spine', 1, [(sr, 'ok'), ('sp_vector_memory', f'rk{b}')])]
    B += [('tt_land', 'spine_local', LAND_BITS, [('sp_vector_memory', 'ld'), ('sp_tree_top', 'ld')]),
          ('vm_meok', 'spine_local', 1, [('sp_vector_memory', 'mo'), ('sp_constants_sequencer', 'mo')])]
    m['buses'] = B
    m['r21m'] = dict(
        rtl={'qfd_sp_vector_memory': 'rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv ot_qfd_sp_vector_memory_bv',
             'qfd_sp_su64_sfu': 'rtl/qwen_sys/vm_me_20261008/ot_qfd_su_master_bv.sv ot_qfd_sp_su64_sfu_bv',
             'qfd_sp_res_ser': 'rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv ot_qfd_res_ser',
             'qfd_sp_tree_top': 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv ot_qfd_sp_tree_top (LANDED = 1, '
                                'BAND = 1: ot_qfd_band_upper inside, cfg qfd_sp_tree_top_b)',
             'qfd_sp_band_lanes': 'rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv ot_qfd_band_lanes (NL 16; '
                                  'tree top part: ot_qfd_band_upper)'},
        column_m_um=VM_ME_XCOL, vm_slot_um=[round(m['geo']['cw'], 3), VM_BV_H], su_slot_um=[round(m['geo']['cw'], 3), SU_BV_H],
        band_lanes_slot_um=[round(m['geo']['cw'], 3), BL_H], ser_slot_um=[round(m['geo']['cw'], 3), SER_H],
        port_elements={b: [prim[b]] for b in range(BANDS)},
        band_lanes=dict(rtl='rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv',
                        bench='rtl/test/qwen_lane_band/tb_qfd_band_lanes.sv',
                        frame='band-local result slots: split s <= 10 band b slot k = group b * 2^(10-s) + k; s 11 / 12 '
                              'band 0 slot k = group k (tree top words)', cycles='+5 + 2 LNK edges per ME op result'),
        band_integrate=dict(slab_port_group='ot_qwen_slab_port_group BANDF 1 (GID = slot 8b + k; group g(split, slot))',
                            spine='rtl/qwen_sys/band_integrate_20261008/ot_qfd_spine_band.sv',
                            bench='rtl/test/qwen_band_integrate/tb_qfd_spine_band.sv'),
        tree_top_slot_um=[round(m['geo']['cw'], 3), m['geo'].get('r21m_slots_um', {}).get('tree_top')],
        tree_top_col='M (r21b: on the VM, SU + VM + tree top one stack)' if getattr(v, 'R21M_TT_H', 0.0) else 'W',
        open=([] if getattr(v, 'R21M_TT_H', 0.0) else
              ['tree top slot: qfd_sp_tree_top_b is 777.6 x 3732.48 (the upper levels; r21m slot is the r21f tree top\'s); '
               'recipe r21b / r21bt']) + [
              'band lane <-> slab words connect each band at its W primary slab (a band\'s fragments reach it by pfrag)'],
        slab_port_groups='RTL_PORT_GROUPS 48 (8 a band, 4 a half; 12 port elements x PQ 4), block-word FIFOs stay 96')
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        # the SU <-> VM abutted bus owns the VM S face and the SU N face (_su_vm_bus): every other default pin group
        # the wrappers put there moves to the side faces (VM: E, toward the band column; SU: W)
        moves = [('qfd_sp_vector_memory', 'S', ('sa', 'sq'), 'W', None), ('qfd_sp_su64_sfu', 'N', ('va', 'vq'), 'W', None),
                 ('qfd_sp_vector_memory', 'E', (), 'W', None)]
        if getattr(v, 'R21M_TT_H', 0.0):
            # r21b: the tree top sits in M; its band-lane words (bw*: band word + valid, lc* / lf*: lane control /
            # fault, ty: the split-11/12 return to band 0) face the band-lane blocks in W
            moves.append(('qfd_sp_tree_top', 'E', (), 'W', re.compile(r'^(bw|lc|lf)\d+$|^ty$')))
        for mn, f, keep, to, only in moves:
            M_ = o[mn]
            mv = [pn for pn, sp in M_.ports.items() if sp[0] == 'face' and sp[2] == f and pn not in keep
                  and (only is None or only.match(pn))]
            for pn in mv:
                _, w_, _, _, _, pitch = M_.ports[pn]
                M_.ports.pop(pn)
                span = w_ * F.TRK['M4'][1] * k * max(1, pitch)
                used = sorted(_face_used(M_, to, k))
                y, ok = 6.0, False
                for lo, hi in used + [(M_.h - 4.0, M_.h)]:
                    if y + span + 2.0 <= lo:
                        ok = True
                        break
                    y = max(y, hi + 2.0)
                if not ok:
                    raise ValueError(f'r21m: {mn}.{pn} ({w_} b) does not fit the {to} face')
                M_.ports[pn] = ('face', w_, to, 'M4', y + span / 2, pitch)
        # the band-lane block and the serializer: their abutted words (tw / ty, rq) on the stack faces, every other
        # word as M8 area pins (their peers -- tree top, vector memory -- are reached through relays in any direction)
        for mn, ports in (('qfd_sp_band_lanes', ('c', 'f', 'pw', 'tt')), ('qfd_sp_res_ser', ('o', 'ok', 'cr'))):
            if mn not in o:
                continue
            M_ = o[mn]
            xq = 40.0
            for pn in ports:
                if pn in M_.ports:
                    w_ = M_.ports[pn][1]
                    M_.ports[pn] = ('area', w_, xq, M_.h / 2, 1)
                    xq += 120.0
        return o
    v.masters = masters


BWP_H = 60.48       # r20f block-word waypoint frame height: 512 M4 face pins at 2 tracks (49.2 um) + margins, on GY


def _bw_waypoints(v, m, every):
    """r20f: block-word waypoints.  A block word (root tile -> its band slab in the spine) is a chain of registered
    hops through waypoint stations in the corridors of its root row, one every `every` tile columns (5 x 319.68 =
    1,598 um <= 4 x 430.56, the link waypoint rule), so a congested global route cannot detour it (r18j i50: the
    worst word 81 routed stages against 64 at i5 / floorplan).  The stations stack downward from the corridor station
    of that row; the hops keep the bus class (tree_spine) and the word's name on the first hop (bword_<b>), the rest
    bwseg_<b>_<k>."""
    col_x, row_y = m['col_x'], m['geo']['row_y']
    st_y = v.dn((v.TILE_SLOT[1] - v.STATION[1]) / 2, v.GY)
    slot_n, insts, out = {}, [], []
    for bid, cl, bits, eps in m['buses']:
        if not bid.startswith('bword_'):
            out.append((bid, cl, bits, eps))
            continue
        b = bid[len('bword_'):]
        (root, rp), (slab, sp) = eps
        c, r = map(int, root.split('_')[1:])
        west = c < v.COLS // 2
        cols = [c + every * k for k in range(1, v.COLS) if c + every * k < v.COLS // 2] if west else \
            [c - every * k for k in range(1, v.COLS) if c - every * k >= v.COLS // 2]
        prev = (root, rp)
        for k, cc in enumerate(cols):
            n = slot_n.get((cc, r), 0)
            slot_n[(cc, r)] = n + 1
            # stacked downward from the corridor station of the row (the word's pins sit at the tile's mid height)
            y = v.dn(row_y[r] + st_y - 2.16 - (n + 1) * (BWP_H + 2.16), v.GY)
            if y < row_y[r] + 2.16:
                raise ValueError(f'bw waypoints: corridor {cc} row {r} below its station is full ({n + 1})')
            name = f'bwp_{b}_{k}'
            insts.append(v.Inst(name, 'qfd_bwp_e' if west else 'qfd_bwp_w', col_x(cc) + v.TILE_BODY_W, y, v.CORR - v.SHAVE, BWP_H - v.SHAVE,
                                kind='waypoint', region='corridor'))
            out.append((bid if k == 0 else f'bwseg_{b}_{k}', cl, bits, [prev, (name, 'w' if west else 'e')]))
            prev = (name, 'e' if west else 'w')
        out.append((bid if not cols else f'bwseg_{b}_{len(cols)}', cl, bits, [prev, (slab, sp)]))
    m['insts'] += insts
    m['buses'] = out
    m['b3r2']['r20f_bw_waypoints'] = dict(stations=len(insts), every_cols=every,
                                          max_per_corridor_slot=max(slot_n.values()) if slot_n else 0)
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        for mn, flow in (('qfd_bwp_e', 'eastbound: in w, out e'), ('qfd_bwp_w', 'westbound: in e, out w')):
            w = v.Master(mn, v.CORR - v.SHAVE, BWP_H - v.SHAVE, 3, 'block-word waypoint: one registered 512-b '
                         f'tree-word hop (512 flops) in a corridor, standard cells M1-M3, die routing above ({flow})')
            w.face('w', v.TREE_BITS, 'W', 'M4', w.h / 2, 2)
            w.face('e', v.TREE_BITS, 'E', 'M4', w.h / 2, 2)
            o[mn] = w
        return o
    v.masters = masters


def _io_south(v):
    """r21: the IO-band words that cross another IO element (SerDes words over the UCIe macro, the embedding word
    beside the collective) leave on the S face of their element, at the end toward the peer, so their relays sit in
    the corridors of the top tile row instead of over an IO macro (the band has no free area between its elements)."""
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        at_s = getattr(v, 'IO_SOUTH_BAND', False)
        lst = [('qfd_io_xfifo', 'o_serdes_tx', 300.0), ('qfd_io_xfifo', 'i_serdes_rx', 360.0),
               ('qfd_io_serdes', 'c', 30.0), ('qfd_io_serdes', 'r', 90.0),
               ('qfd_io_embedding_rom', 'o', None), ('qfd_io_embedding_rom', 'a', -1.0)]
        if at_s:
            # qwen-tp8/die it4 (tp8b: IO band at the S edge, core to the N): every SerDes word leaves its CDC cluster /
            # SerDes on the core-facing N face into the IO word channel (the S face is the die edge; the xfifo's
            # tx1/tx2/rx1/rx2 sat on its W face in the 4-um gap abutting the collective) -- serdes 1/2 words at the
            # xfifo's W end (toward serdes 1/2), serdes 0 words toward its E end (clear of the seq/coll pins at 630+)
            lst = [('qfd_io_xfifo', 'o_serdes_tx2', 40.0), ('qfd_io_xfifo', 'i_serdes_rx2', 100.0),
                   ('qfd_io_xfifo', 'o_serdes_tx1', 160.0), ('qfd_io_xfifo', 'i_serdes_rx1', 220.0),
                   ('qfd_io_xfifo', 'o_serdes_tx', 450.0), ('qfd_io_xfifo', 'i_serdes_rx', 510.0),
                   ('qfd_io_serdes', 'c', 30.0), ('qfd_io_serdes', 'r', 90.0)]
        for mn, port, centre in lst:
            M = o.get(mn)
            if M is None or port not in M.ports:
                continue
            bits = M.ports[port][1]
            c = centre if centre is not None else M.w - 20.0 - bits * 0.048
            if centre == -1.0:
                c = M.w - 60.0 - M.ports['o'][1] * 0.048 - 40.0     # beside the word, west of it
            mx = any(it.master == mn and it.orient in ('MX', 'R180') for it in model['insts'])
            M.ports[port] = ('face', bits, ('S' if mx else 'N') if at_s else ('N' if mx else 'S'), 'M5', c, 1)
        # spine blocks whose words sat as area pins inside the body (a relay can only be beside a macro): the tree
        # top's port-slab words, its result word and done to its E face (the vertical channel), the sequencer's
        # collective / embedding-address / done words to its W face (the channel), the VM's tree-result word to E
        # (r21b: the tree top sits in column M, its band words come from the band-lane blocks in W: W face)
        moves = (('qfd_sp_tree_top', ['bw0', 'bw1', 'bw2', 'bw3', 'bw4', 'bw5', 'r', 'md'],
                  'W' if getattr(v, 'R21M_TT_H', 0.0) else 'E'),
                 ('qfd_sp_constants_sequencer', ['cd', 'ea', 'md'], 'W'),
                 ('qfd_sp_vector_memory', ['tr'], 'E'))
        for mn, ports, face in moves:
            M = o.get(mn)
            if M is None:
                continue
            ps = [q for q in ports if q in M.ports]
            used = [(s[4] - s[1] * 0.048 * s[5] / 2 - 2, s[4] + s[1] * 0.048 * s[5] / 2 + 2)
                    for q, s in M.ports.items() if s[0] == 'face' and s[2] == face and q not in ps]
            y = 20.0
            for q in ps:
                bits = M.ports[q][1]
                span = bits * 0.048 + 4.0
                while any(a_ < y + span and y < b_ for a_, b_ in used):
                    y += 10.0
                M.ports[q] = ('face', bits, face, 'M4', y + span / 2, 1)
                used.append((y, y + span))
                y += span + max(10.0, (M.h - 40.0) / max(1, len(ps)) - span)
        return o
    v.masters = masters


# r21c (emb-hbm 2026-10-08, OWNER DECISION 2026-10-08 ~21:00 PT): the Qwen3-8B input embedding moves out of the on-die
# ROM into each die's attached HBM (rtl/qwen_sys/emb_hbm_20261008, design review REVIEW_QUEUE.md "EMB-HBM").
#   * the IO-band embedding ROM element (io_embedding_rom, qfd_io_embedding_rom: the r21b 11.046 mm2 placeholder for a
#     root + taps + 2,374 code / 3 scale bank parents) is removed with its die words (emb_a 26 b, emb 513 b, emb_cr) and
#     their relay chains (r21b: 54 relays on emb_a alone) and its clock leaf;
#   * the SU's embedding face (ea / ecr / eq, unchanged: ot_qfd_su_embed_pf) now talks to the HUB (qfd_hub_emb:
#     ot_qwen_die_hub_emb_top = the full-rate hub + the embedding gateway ot_qfd_emb_gw); the rows come over the
#     existing hub <-> stack links (EMB link class), no new wide die bus;
#   * the strip / controller additions sit inside existing frames: the per-stack embedding engine (ot_qfd_emb_strip,
#     core clock) beside the strip-end link endpoint in the qfd_kvc frame, the static-row port in every PC controller
#     (qfd_ctrl_emb_<pc>: ot_qwen_ctrl_pc_emb) and the per-PC ECC / class port (ot_qfd_emb_pcport) in the controller
#     band; their area is recorded in m['r21c'] against those frames.
# The IO band keeps its depth (the die outline does not change); the freed band length is recorded as slack.
# area estimates of the in-frame additions (flops x 0.32 um2 ASAP7 DFF / 0.55 util x 1.6 logic) -- the review sizes them
EMB_STRIP_FLOPS = 32 * 4 * 258 + 4 * 523 + 4 * 523 + 516 + 400 + 32 * 4 + 200     # rx FIFOs, in/tx queues, packer, credits
EMB_PCPORT_FLOPS = 32 + 4 * 288 + 288 + 32 + 288 + 258 + 64                         # class FIFO, write FIFO, decode pipe
# sys-takeover 2026-10-09 (coordinator: adopt the HBM ECC side-band on KV writes, registry qfd_hbm_ecc_provider): the
# per-PC port runs KVW = 2 -- the KV write data is the per-PC STREAM4 CDC's completion entry (h_cv / h_cdata, already on
# the cdho_<st>_<p> hbm_cdc bus into the controller element, CDC_HO), encoded into the side-band; every WR's PHY write
# data leaves two HCLK edges after its column.  No new die bus (kw_v / kw_d = h_cv / h_cdata inside qfd_ctrl);
# +2 x 288 + 2 flops a PC.  (KVW = 1, the closed view views/qfd_emb_pcport_kvw, expects the data before the column and
# faults at this timing: physical/sys_takeover/kvw2_path_bench.sh neg 'kvw1'.)
EMB_PCPORT_KVW = 2
EMB_PCPORT_FLOPS += 2 * 288 + 2 if EMB_PCPORT_KVW == 2 else 0
EMB_GW_FLOPS = 32 * 25 + 4 * 523 + 512 + 26 + 512 + 160 + 4 * 8 * 11                 # request FIFO, slots, eq, pins, tags


def _emb_hbm(v, m):
    """r21c: drop the embedding ROM, terminate the SU's embedding words at the hub (see the r21c comment above)."""
    gone = 'io_embedding_rom'
    ins = [i for i in m['insts'] if i.name == gone]
    if len(ins) != 1:
        raise ValueError('r21c builds on r21f+ (io_embedding_rom present once)')
    rom = ins[0]
    m['insts'] = [i for i in m['insts'] if i.name != gone]
    m['io'] = {k: it for k, it in m['io'].items() if it.name != gone}
    B, dropped = [], []
    for bid, cl, bits, eps in m['buses']:
        if bid == 'emb_a':
            eps = [('sp_su64_sfu', 'ea'), ('hub_el', 'ea')]
        elif bid == 'emb':
            eps = [('hub_el', 'eq'), ('sp_su64_sfu', 'eq')]
        elif bid == 'emb_cr':
            eps = [('hub_el', 'ecr'), ('sp_su64_sfu', 'ecr')]
        elif any(e[0] == gone for e in eps):
            eps = [e for e in eps if e[0] != gone]
            if len(eps) < 2:
                dropped.append(bid)
                continue
        B.append((bid, cl, bits, eps))
    m['buses'] = B
    for r in m.get('regions', []):
        pass
    gw_mm2 = EMB_GW_FLOPS * 0.32 * 1.6 / 0.55 / 1e6
    m['r21c'] = dict(
        removed=dict(instance=gone, master=rom.master, rect_um=[round(rom.x, 3), round(rom.y, 3), round(rom.w, 3), round(rom.h, 3)],
                     mm2=round(rom.w * rom.h / 1e6, 3), buses_dropped=dropped,
                     note='the r21b placeholder; the RTL-sized full replica (2,374 code + 3 scale bank parents + 2,376 taps + '
                          'root) would need ~88.1 mm2 (EMB_HBM_FEASIBILITY.md)'),
        rerouted=['emb_a (26 b) sp_su64_sfu.ea -> hub_el.ea', 'emb (513 b) hub_el.eq -> sp_su64_sfu.eq',
                  'emb_cr (1 b) hub_el.ecr -> sp_su64_sfu.ecr'],
        rtl={'qfd_hub': 'rtl/qwen_sys/emb_hbm_20261008/ot_qwen_die_hub_emb.sv ot_qwen_die_hub_emb_top (+ ot_qfd_emb_gw)',
             'qfd_ctrl (per PC)': 'rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv (ot_hbm_r14_stream_pc_srow SROW 1) '
                                  '+ ot_qfd_emb_pcport.sv (KVW 2: KV write side-band from the CDC completion h_cv / h_cdata)',
             'qfd_kvc (strip end)': 'rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_strip.sv + ot_qfd_link_far.sv (class split)'},
        in_frame_mm2=dict(gateway_in_hub=round(gw_mm2, 4),
                          strip_engine_per_stack=round(EMB_STRIP_FLOPS * 0.32 * 1.6 / 0.55 / 1e6, 4),
                          pcport_per_pc=round(EMB_PCPORT_FLOPS * 0.32 * 1.6 / 0.55 / 1e6, 5)),
        io_band_slack_um=round(rom.w + v.SHAVE, 3))
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        o.pop('qfd_io_embedding_rom', None)
        hb = o['qfd_hub']
        # W face: x3 / ar sit at h/2 -+ 60 (2-pitch, ~49 um each); the embedding words below and above them
        hb.face('ea', EMB_REQ_BITS, 'W', 'M4', 40.0, 2)
        hb.face('ecr', 1, 'W', 'M4', 50.0, 2)
        hb.face('eq', EMB_RSP_BITS, 'W', 'M4', hb.h - 40.0, 1)
        return o
    v.masters = masters


# ------------------------------------------------------------------------------------------------ r21 die relays
# coll_fdi (Qwen split compute static IO, 2026-10-15): the collective <-> PHY FDI words; their relay registers are
# inside the static collective RTL (RU / RS relay_ck roots), a die relay would be an unscheduled stage
RELAY_SKIP = ('clock_trunk', 'reset', 'tap', 'kv_land', 'cdc_core', 'hbm_cdc', 'phy_dfi', 'coll_fdi')
# the standard corridor relay frame (52.68 x 30.24, faces at one track: 520 x 0.048 + 4 = 29 um of a 52.68-um face)
# holds up to 520 b (split compute C7: 514-b tree words {fault, valid, 512}, 516-b DVM corridor word)
RELAY_STD_BITS = 520
RELAY_V_H = 30.24      # relay frame height with N/S faces only (vertical run): 512 flops + clock leaf, M1-M3
RELAY_MAX_UM = 350.0   # owner fast rule 2026-10-06: every die wire > ~350 um gets relay registers ...
RELAY_PITCH_UM = 300.0  # ... at a conservative ~300 um pitch
# owner 2026-10-13 (die timing by construction): register at the pin -> wire <= 500 um -> register at the pin, measured
# PIN TO PIN (bounding box of the net's pin centroids, as tools/hier_contract/pinreg_audit.py).  Under v.RELAY_REACH_GATE
# (tp8b) _relays accepts a chain only when every hop is <= RELAY_REACH_OK pin to pin and raises on any data net over
# RELAY_REACH_UM; clock / reset trees are built by CTS / the reset tree and are not data hops.
RELAY_REACH_UM = 500.0
RELAY_REACH_OK = 490.0
# split-compute C4 (2026-10-14, compute-die lead r2): under the reach gate a relay chain is judged PIN TO PIN only (the
# owner rule, TT sign-off).  The centre-to-centre RMAX + 25 proxy came from the SS-measured 430.56-um corridor pitch (SS is
# a sensitivity, owner option B) and made every corridor -> corridor hop of a 472.6 / 522.3-um column pitch illegal (pin
# to pin 420 / 470 um): horizontal tree / block words detoured to the IO channel (C3: 222 unrepaired, bword 149 stages).
# The relay masters must meet the reach: o + s <= 683.3 - 0.76 x 490 = 310.9 ps TT (relay element, compute queue).
import os as _os_r
P2P_REACH = _os_r.environ.get('OT_RELAY_P2P', '1') != '0'
RELAY_NEVER = ('clock_trunk', 'reset')


def _relay_terminal_possible(centers, endpoint, reach_um, is_free, hop_ok=None):
    """Necessary terminal condition for BFS, using the same centers and hop predicate.

    An empty legal terminal set cannot be repaired by visiting more intermediate
    sites. Use centers, not site origins: their offset can change reach eligibility.
    """
    import numpy as np
    ids = np.flatnonzero(np.abs(centers[:, 0] - endpoint[0]) +
                         np.abs(centers[:, 1] - endpoint[1]) <= reach_um)
    return any(is_free(int(i)) and (hop_ok is None or hop_ok(
        (float(centers[i][0]), float(centers[i][1])), endpoint)) for i in ids)


def _relays(v, m, pitch=RELAY_PITCH_UM):
    """r21 (owner fast rule 2026-10-06): relay registers on every die wire longer than ~350 um, at <= `pitch` um along
    a rectilinear path.  A relay is one registered hop of the bus (the closed station family, ot_qwen_die_station
    TAP=0 at the bus width: qfd_cst SS +73.7 / FF +26.3, qfd_chead SS +51.3), standard cells M1-M3 only (OBS M1-M3),
    so the corridor's M4-M9 stay open over it; its upstream port `a` faces the previous point, `b` the next one.
    Paths: inside a tile array, along the bus's own corridor (corridor class) or an L through the corridor nearest the
    two pins (tree words), relays at every corridor crossed and at <= pitch along the corridor; a word leaving the
    array turns in the array's edge corridor nearest its far end; elsewhere (spine / IO band / channels) an L,
    vertical first, with each relay in the nearest free spot.  Link hops (forwarded-clock link stations) get a
    forwarded clock per relay hop; every other relay takes its source's region clock (stream) or domain clock.
    Not relayed: clock / reset trees, the tile tap and KV landing hops (<= 350 um by construction), CDC / HBM strip
    words (<= 350 um) and the DFI (417 um, HBM PHY interface timing, priced by the controller)."""
    if _os_r.environ.get('OT_RELAY_SKIP') == '1':     # smoke runs only (masters / pins / die.v without the relay plan)
        m['r21_relays'] = dict(skipped=True)
        return
    import bisect
    RMAX = max(RELAY_MAX_UM, pitch)   # a wire is relayed only when longer than the relay pitch
    pos = _pin_pos(v, m)
    by = {i.name: i for i in m['insts']}
    g = m['geo']
    COLS = v.COLS
    cx_list = [m['col_x'](c) + v.TILE_BODY_W + v.CORR / 2 for c in range(COLS)]
    corr_x0 = [m['col_x'](c) + v.TILE_BODY_W for c in range(COLS)]
    if m.get('corridor_lanes'):
        # split compute PM-H-S: per-column station lanes (even W of its MY tile, odd E of its R0 tile); v.CORR is the
        # lane width for the whole relay plan (set by the caller)
        corr_x0 = [x0 for x0, _ in m['corridor_lanes']]
        cx_list = [x0 + v.CORR / 2 for x0 in corr_x0]
    fields = [r['rect'] for r in m['regions'] if r['kind'] == 'tile_field']
    fw, fe = fields[0], fields[1]

    def in_field(x, y):
        return any(a - 1 <= x <= c + v.CORR + 1 and b - 1 <= y <= d + 1 for a, b, c, d in fields)

    def side_cols(x):
        return range(0, COLS // 2) if x < (fw[2] + fe[0]) / 2 else range(COLS // 2, COLS)

    # occupancy: per corridor (sorted y intervals) and a coarse grid of every instance rect
    BK = 250.0
    grid = {}

    def add_rect(r):
        for gx in range(int(r[0] // BK), int(r[2] // BK) + 1):
            for gy in range(int(r[1] // BK), int(r[3] // BK) + 1):
                grid.setdefault((gx, gy), []).append(r)

    def free(r, gap=0.0):
        if r[0] < 0 or r[1] < 0 or r[2] > m['die']['w'] or r[3] > m['die']['h']:
            return False
        for gx in range(int((r[0] - gap) // BK), int((r[2] + gap) // BK) + 1):
            for gy in range(int((r[1] - gap) // BK), int((r[3] + gap) // BK) + 1):
                for q in grid.get((gx, gy), ()):
                    if q[0] < r[2] + gap - 1e-6 and r[0] < q[2] + gap - 1e-6 and q[1] < r[3] + gap - 1e-6 and r[1] < q[3] + gap - 1e-6:
                        return False
        return True
    for it in m['insts']:
        add_rect((it.x, it.y, it.x + it.w, it.y + it.h))
    die_top = g['y_io']

    def corr_of(x):
        j = min(range(COLS), key=lambda c: abs(cx_list[c] - x))
        return j if abs(cx_list[j] - x) < 1.0 else None

    def place(x, y, w, h, corr, tol=None):
        """lower-left corner of a free w x h frame nearest (x, y): inside corridor `corr` (x fixed) when given."""
        if corr is not None:
            ccs = [corr] if tol is not None else sorted(side_cols(cx_list[corr]), key=lambda c: abs(c - corr))[:5]
            for cc in ccs:
                x0 = corr_x0[cc]
                for k in range(0, 400 if tol is None else int(tol / v.GY) + 1):
                    for sgn in ((1,) if k == 0 else (1, -1)):
                        y0 = v.dn(y - h / 2 + sgn * k * v.GY, v.GY)
                        r = (x0, y0, x0 + w, y0 + h)
                        if y0 >= g['y0'] and y0 + h <= die_top and free(r):
                            return x0, y0
            return None
        for ring in range(0, getattr(v, 'RELAY_RINGS', 160) if tol is None else int(tol / (4 * v.GY)) + 1):
            st = ring * 4 * v.GY
            cands = [(0, 0)] if ring == 0 else \
                [(dx, dy) for dx in (-st, st) for dy in [i * 4 * v.GY for i in range(-ring, ring + 1)]] + \
                [(dx, dy) for dy in (-st, st) for dx in [i * 4 * v.GY for i in range(-ring + 1, ring)]]
            for dx, dy in sorted(cands, key=lambda t: abs(t[0]) + abs(t[1])):
                x0 = v.dn(x - w / 2 + dx, v.GX)
                y0 = v.dn(y - h / 2 + dy, v.GY)
                if in_field(x0 + w / 2, y0 + h / 2) and corr_of(x0 + w / 2) is None and not (cur_tight[0] or cur_gapok[0]):
                    continue           # never over a tile body (it4: a KV row-run relay may sit in a row gap; free()
                    #                    still refuses any tile overlap)
                if free((x0, y0, x0 + w, y0 + h)):
                    return x0, y0
        return None

    corr_used = {}

    def load(c, ya, yb):
        ya, yb = sorted((ya, yb))
        yb = max(yb, ya + 1.0)
        return sum(max(0.0, min(b_, yb) - max(a_, ya)) for a_, b_ in corr_used.get(c, ())) / (yb - ya)

    # qwen-tp8/die it3: spine lane balancing (SPINE_LANE_BALANCE): a long vertical spine word takes the lane (spine relay
    # channel) that minimises detour + the worst 260-um window load it would see; a lane whose straight run would
    # cross a hard block (> 0.04 mm2) is not eligible.  lane_bits[x] = per-260-um-bin bits already assigned.
    LBIN = 260.0
    lane_bits = {x: [0.0] * (int(m['die']['h'] // LBIN) + 2) for x in (getattr(v, 'SPINE_CHANNEL_X', None) or [])}
    big = [(it.x, it.y, it.x + it.w, it.y + it.h) for it in m['insts'] if it.w * it.h > 4e4]
    for x_, b_ in (getattr(v, 'SPINE_LANE_PRELOAD', None) or {}).items():
        if x_ in lane_bits:
            lane_bits[x_] = [b_] * len(lane_bits[x_])
    cur_bits = [0]
    io_sub = [[], [], [], []]
    IO_SUB_F = (0.1, 0.37, 0.63, 0.9)
    # it4 (fine cuts): KV-half words (KV centre <-> W / E KV strip) run in a row gap across the field, not via the IO
    # channel (pass-2 search sent kvn_* down to the IO channel and back up: 80 relays, 1 kb stacked on the serdes words)
    KVC_NAMES = ('pll', 'embgw', 'seq', 'ahub', 'host')
    gap_bits = {}
    gap_tot, gap_id, xch_bits = {}, {}, {}     # it17: aggregate per row gap; bits per head-stack crossing channel
    KV_GAP_CAP, KV_XCH_CAP = 4000.0, 1600.0
    kv_gaps = []
    gap_set = set()
    cur_tight = [False]
    cur_gapok = [False]      # r8 (coordinator 2026-10-13): row-gap sites are legal for head chains
    e_rot = [0]
    tight_stride = set()     # it4: buses on the KV row-run rule place relays at pitch - 70 (frame snapping at the field /
    #                          strip edges overshot RMAX by 10-70 um, and the pass-2 search then rerouted them via the IO channel)
    if getattr(v, 'SPINE_LANE_BALANCE', False) and g.get('row_y'):
        ry = sorted(g['row_y'])
        th = v.TILE_SLOT[1]
        if getattr(v, 'TILE_CLUSTER', False):
            # coordinator DECISION 2026-10-12 12:15: qfd_tile_nk is a CLUSTER slot (M2-M7 inside), the die has only
            # M8+ over it (0.75 x 260 um x M8 = 2,438 b per fine window): a KV-half word (530-1,048 b) runs in a row gap
            # (M4-M8 free), on one of three sub-lanes per gap, never over a tile row
            kv_gaps = sorted(round(a + th + (b - a - th) * f, 3) for a, b in zip(ry, ry[1:]) if b - (a + th) > 120.0
                             for f in (0.25, 0.5, 0.75))
            gap_set = set(kv_gaps)
            gap_id = {round(a + th + (b - a - th) * f, 3): k for k, (a, b) in enumerate(zip(ry, ry[1:])) for f in (0.25, 0.5, 0.75)}
            if getattr(v, 'CLUSTER_PLAN', 'A') == 'M6':
                # r8 (coordinator 2026-10-13, tile growth): die M6 over the M5-capped tiles carries horizontal buses, so
                # a KV-half word may also run OVER a tile row (relays in the column corridors, one per column pitch);
                # the row-gap sub-lanes stay first choice (the run cost charges 600 for a lane outside gap_set) and
                # every lane is admitted by its fine windows (hr) at the cut model's caps
                kv_gaps = sorted(kv_gaps + [round(a + th * f, 3) for a in ry for f in (0.2, 0.4, 0.6, 0.8)])
        else:
            kv_gaps = [round((a + th + b) / 2, 3) for a, b in zip(ry, ry[1:]) if b - (a + th) > 120.0]
            # over-tile runs too (M6+ over the M5-capped tiles, relays in the corridors): the KV strips' head stacks
            # leave crossing heights only below / between / above their stacks, which are mostly over tile rows
            gap_set = set(kv_gaps)
            kv_gaps = sorted(kv_gaps + [round(a + th * f, 3) for a in ry for f in (0.25, 0.5, 0.75)])
    io_ch = next(((r['rect'][1], r['rect'][3]) for r in m['regions'] if r['name'] == 'io_chan'), None) \
        if getattr(v, 'SPINE_LANE_BALANCE', False) else None

    def lane_pick(chx, P0, P1, lb):
        ya, yb = sorted((P0[1], P1[1]))
        ka, kb = int(ya // LBIN), int(yb // LBIN) + 1
        best = None
        for x in chx:
            if any(a < x < c and b < yb - 1.0 and ya + 1.0 < d for a, b, c, d in big):
                continue
            det = abs(x - P0[0]) + abs(x - P1[0])
            pk = max(lb[x][ka:kb]) + cur_bits[0]
            cost = det + 6000.0 * pk / 4900.0     # it4: 4000 -> 6000 (tt_ty + 4 bwords stacked on the E spine lane)
            if FIELD_ALLOC:
                # it24: every placed chain is booked: the lane's fine windows at their cut-model caps
                cost += 20000.0 * max(0.0, vr(x, ya, yb, cur_bits[0]) - 1.0) + 600.0 * vr(x, ya, yb)
            if best is None or cost < best[0]:
                best = (cost, x)
        if best is None:
            best = (0, min(chx, key=lambda x: abs(x - P0[0]) + abs(x - P1[0])))
        x = best[1]
        for k in range(ka, min(kb, len(lb[x]))):
            lb[x][k] += cur_bits[0]
        return x

    def io_lane(lo, hi, subs, allow=None):
        """it4: the IO sub-lane whose 260-um bin, then lane, carries the fewest bits over this word's x span.
        it17: the KV host link (host_fdi, 2,085 b) owns the top sub-lane; the SerDes / IO words share the two bottom
        ones (> 260 um from it), so no fine window holds the 4 kb of SerDes words and the host link together"""
        def ov(j):
            return sum(b_ for a_, c_, b_ in io_sub[j] if a_ < hi and lo < c_)
        binl = lambda j: sum(ov(q) for q in range(len(subs)) if int(subs[q] // 260.0) == int(subs[j] // 260.0))  # noqa: E731
        if FIELD_ALLOC:
            # r8: by the fine windows the lane's run would see with this word added (cut-model caps): the two bottom
            # sub-lanes share one 260-um window, and 10 SerDes words on them stood at 5,120 b / 7,928 = 0.646
            k = min(allow if allow is not None else range(len(subs)),
                    key=lambda j: (round(max(hr(subs[j], lo, hi, cur_bits[0]), 1.0), 3), binl(j), ov(j), j))
        else:
            k = min(allow if allow is not None else range(len(subs)), key=lambda j: (binl(j), ov(j), j))
        io_sub[k].append((lo, hi, cur_bits[0]))
        return k

    # it17 (layer plan A: die M8 H / M9 V only over the tile_nk clusters): a field allocator.  Every routed path's
    # horizontal / vertical legs are booked per 260-um window (the fine-cut grid: windows at multiples of 260 um);
    # an over-tile horizontal leg is admitted only while its windows stay <= HCAP (2 x 512 b + slack of M8's 2,438
    # tracks), else it jogs into the nearest row-gap sub-lane (M4-M8 free, <= GCAP); a vertical corridor leg takes the
    # corridor (column) whose windows stay lowest, capped at VCAP.  Classes it places: tree words and every other
    # field-to-field / field-to-spine word (corridor-class words keep their own corridor and are only booked).
    FBIN = 260.0
    hb, vb = {}, {}
    HCAP, GCAP, VCAP = 1400.0, 4000.0, 1800.0
    FIELD_ALLOC = bool(getattr(v, 'TILE_CLUSTER', False)) and bool(kv_gaps)
    if FIELD_ALLOC:
        # it19: 480-um IO channel (tp8b): SerDes words on the two bottom sub-lanes (frames inside the 1,560-1,820
        # fine window), the 2,085-b host_fdi relay frame (106 um) on a top sub-lane low enough to fit under the
        # channel top (at 0.9 it was pushed down into the SerDes window: 0.754)
        IO_SUB_F = (0.08, 0.30, 0.55, 0.85)
    ry_ = sorted(g.get('row_y') or [])
    th_ = v.TILE_SLOT[1]

    def over_tile(y):
        k = bisect.bisect_right(ry_, y) - 1
        return k >= 0 and ry_[k] - 1.0 <= y <= ry_[k] + th_ + 1.0

    ABIN = 50.0     # it19: along-the-leg resolution = the fine-cut line spacing (a 260-um bin at a pin end charged
    #                 every leg the full load of the pin stubs that only cross part of it: phantom 1.9 kb)

    def _bins(a, b, st=ABIN):
        a, b = sorted((a, b))
        return range(int(a // st), int(b // st) + 1)

    def hload(y, xa, xb):
        yb_ = int(y // FBIN)
        xa, xb = sorted((xa, xb))
        return max((hb.get((yb_, k), 0.0) for k in _bins(xa + 1.0, xb - 1.0)), default=0.0) if xb - xa > 2.0 else 0.0

    def vload(x, ya, yb):
        xb_ = int(x // FBIN)
        ya, yb = sorted((ya, yb))
        return max((vb.get((xb_, k), 0.0) for k in _bins(ya + 1.0, yb - 1.0)), default=0.0) if yb - ya > 2.0 else 0.0

    # it24: per-window caps from the cut model itself (results/arch/qwen_tp8_1012/cuts.py usable(), CAP_MODE v3) x
    # CAP_FRAC, instead of the flat HCAP / GCAP / VCAP (a corridor window over a tile row has 3.4-4.3 kb usable, so a
    # flat 1.8 kb refused corridors with room; a row-gap window ~8 kb).  Each 50-um bin's cap is the min of the usable
    # tracks at the two cut lines bounding it (the fine scan cuts every 50 um).
    CAP_FRAC = 0.58
    _ucache = {}
    if FIELD_ALLOC:
        import sys as _sys
        _cdir = str(Path(__file__).resolve().parents[1] / 'results' / 'arch' / 'qwen_tp8_1012')
        if _cdir not in _sys.path:
            _sys.path.insert(0, _cdir)
        import cuts as _cuts
        _cm0, _cp0 = _cuts.CAP_MODE, _cuts.CLUSTER_PLAN
        _cuts.CAP_MODE = 'v3'
        # r8 (coordinator 2026-10-13): tiles are M5-capped -> die M6 over the tile field for horizontal buses
        _cuts.CLUSTER_PLAN = getattr(v, 'CLUSTER_PLAN', 'A')
        _bm = _cuts.block_model([dict(x=i.x, y=i.y, w=i.w, h=i.h, m=getattr(i, 'master', '')) for i in m['insts']])
        _cuts.CAP_MODE, _cuts.CLUSTER_PLAN = _cm0, _cp0
        import numpy as _np
        _ed = {'x': _np.arange(0.0, m['die']['h'] + FBIN, FBIN), 'y': _np.arange(0.0, m['die']['w'] + FBIN, FBIN)}

    def _ucap(ax, k):
        """usable x CAP_FRAC per 260-um window along the cut line ax = k * ABIN"""
        if (ax, k) not in _ucache:
            _ucache[(ax, k)] = _cuts.usable(ax, k * ABIN, _ed[ax], *_bm)[0] * CAP_FRAC
        return _ucache[(ax, k)]

    def hcap(yw, k):
        """cap of the horizontal-leg bin (window yw, along-x bin k): vertical cut lines at k*ABIN, (k+1)*ABIN"""
        a, b = _ucap('x', k), _ucap('x', k + 1)
        j = min(yw, len(a) - 1)
        return float(min(a[j], b[j]))

    def vcap(xw, k):
        a, b = _ucap('y', k), _ucap('y', k + 1)
        j = min(xw, len(a) - 1)
        return float(min(a[j], b[j]))

    def hr(y, xa, xb, bits=0.0):
        """max over the leg's bins of (booked + bits) / cap"""
        yb_ = int(y // FBIN)
        xa, xb = sorted((xa, xb))
        if xb - xa <= 2.0:
            return 0.0
        return max((hb.get((yb_, k), 0.0) + bits) / hcap(yb_, k) for k in _bins(xa + 1.0, xb - 1.0))

    def vr(x, ya, yb, bits=0.0):
        xb_ = int(x // FBIN)
        ya, yb = sorted((ya, yb))
        if yb - ya <= 2.0:
            return 0.0
        return max((vb.get((xb_, k), 0.0) + bits) / vcap(xb_, k) for k in _bins(ya + 1.0, yb - 1.0))

    def book(path, bits):
        for (xa, ya), (xb, yb) in zip(path, path[1:]):
            if abs(ya - yb) < 1e-6 and abs(xa - xb) > 1e-6:
                for k in _bins(xa, xb):
                    hb[(int(ya // FBIN), k)] = hb.get((int(ya // FBIN), k), 0.0) + bits
            elif abs(xa - xb) < 1e-6 and abs(ya - yb) > 1e-6:
                for k in _bins(ya, yb):
                    vb[(int(xa // FBIN), k)] = vb.get((int(xa // FBIN), k), 0.0) + bits

    def near_corr(x, toward):
        """the corridor next to a tile face pin at x, on the side toward `toward`"""
        sc = side_cols(x)
        cand = [cx_list[c] for c in sc if (cx_list[c] >= x - 1.0 if toward >= x else cx_list[c] <= x + 1.0)]
        return min(cand, key=lambda q: abs(q - x)) if cand else min((cx_list[c] for c in sc), key=lambda q: abs(q - x))

    def hleg(P, xt, bits):
        """legs taking pin P horizontally to corridor x = xt: at the pin's height when its windows have room (or the
        run stays within one column pitch), else via the nearest row-gap sub-lane with room. -> (points, cost)"""
        xa, ya = P
        if abs(xt - xa) < 1.0:
            return [], 0.0
        if not over_tile(ya) or abs(xt - xa) < 480.0 or hr(ya, xa, xt, bits) <= 1.0:
            return [(xt, ya)], 0.0
        xn = near_corr(xa, xt)
        best = None
        for yg in kv_gaps:
            if hr(yg, xn, xt, bits) > 1.0 or vr(xn, ya, yg, bits) > 1.0:
                continue
            c_ = 2.0 * abs(yg - ya) + 3000.0 * hr(yg, xn, xt)
            if best is None or c_ < best[0]:
                best = (c_, yg)
        if best is None:
            # it19: graded (a flat 5000 kept tree words out of a free neighbour corridor: 0.72)
            return [(xt, ya)], 1500.0 + 3000.0 * max(0.0, hr(ya, xa, xt, bits) - 1.0)
        yg = best[1]
        return [(xn, ya), (xn, yg), (xt, yg)], best[0]

    def field_route(P0, P1, bits):
        lo, hi = sorted((P0[0], P1[0]))
        sc = side_cols(P0[0])
        cs = [c for c in sc if lo - 1200.0 <= cx_list[c] <= hi + 1200.0] or \
            [min(sc, key=lambda c: abs(cx_list[c] - (lo + hi) / 2))]
        best = None
        for c in cs:
            xc = cx_list[c]
            la, ca = hleg(P0, xc, bits)
            lb, cb = hleg(P1, xc, bits)
            ya_ = la[-1][1] if la else P0[1]
            yb_ = lb[-1][1] if lb else P1[1]
            vl = vload(xc, ya_, yb_)
            cost = ca + cb + 2.0 * max(0.0, lo - xc, xc - hi) + 20000.0 * max(0.0, vr(xc, ya_, yb_, bits) - 1.0) + 600.0 * vr(xc, ya_, yb_)
            if _os.environ.get('OT_FA_DBG') and _dbg_cur[0].startswith(_os.environ['OT_FA_DBG']):
                print('FA_C', _dbg_cur[0], xc, round(ca), round(cb), round(vl), round(cost), la, lb, flush=True)
                _pf = [(k * ABIN, round(vb.get((int(xc // FBIN), k), 0))) for k in _bins(ya_ + 1, yb_ - 1)]
                print('FA_V', xc, [q for q in _pf if q[1] >= vl - 1][:3], [q for q in _pf if q[1] > 0][::6], flush=True)
            if best is None or cost < best[0]:
                best = (cost, la, lb)
        _, la, lb = best
        return [P0] + la + lb[::-1] + [P1]

    def exit_jog(Pf, Po, xc, ya_, bits):
        """it19: a field-exit tail that would run over a tile body at Po's height into a full window (4 words over
        the first E-field tile next to the KV-centre face: 0.92) drops to a true row gap instead, runs it to the strip
        just outside the field on Po's side and climbs there to Po. -> (tail, cost, vload) or None"""
        if not gap_set or not over_tile(Po[1]) or abs(xc - Po[0]) < 200.0 or hr(Po[1], xc, Po[0], bits) <= 1.0:
            return None
        F = fw if Pf[0] < (fw[2] + fe[0]) / 2 else fe
        if F[0] - 1.0 <= Po[0] <= F[2] + v.CORR + 1.0:
            return None
        xg = F[0] - 60.0 if Po[0] < F[0] else F[2] + v.CORR + 60.0
        if (xg - Po[0]) * (xg - xc) > 0:
            return None
        best = None
        for yg in gap_set:
            if any(a < xg < c and min(yg, Po[1]) < d and b < max(yg, Po[1]) for a, b, c, d in big):
                continue
            if hr(yg, xc, xg, bits) > 1.0:
                continue
            vl = max(vr(xc, ya_, yg), vr(xg, yg, Po[1]))
            c_ = 2.0 * (abs(yg - ya_) + abs(yg - Po[1])) + 3000.0 * hr(yg, xc, xg)
            if best is None or c_ < best[0]:
                best = (c_, yg, vl)
        if best is None:
            return None
        _, yg, vl = best
        return [(xc, yg), (xg, yg), (xg, Po[1])], best[0], vl

    def field_exit(Pf, Po, bits):
        """a field pin to a block outside the field (spine / KV centre): vertical in the column corridor whose windows
        stay lowest, the over-tile leg toward Po at Po's height while it has room, else in a row gap to the field edge
        corridor and up / down that corridor."""
        sc = side_cols(Pf[0])
        edge = min(sc, key=lambda c: abs(cx_list[c] - Po[0]))
        cs = sorted(sc, key=lambda c: abs(cx_list[c] - Po[0]))[:10]
        best = None
        for c in cs:
            xc = cx_list[c]
            la, ca = hleg(Pf, xc, bits)
            ya_ = la[-1][1] if la else Pf[1]
            xe = cx_list[edge]
            run = abs(xc - xe) > 420.0 and over_tile(Po[1]) and hr(Po[1], xc, xe, bits) > 1.0
            if run:
                lb, cb = hleg((xe, Po[1]), xc, bits)     # same rule mirrored: the edge corridor carries the jog
                tail = lb[::-1] + [(xe, Po[1])]
                vl = max(vr(xc, ya_, lb[-1][1]), vr(xe, lb[-1][1], Po[1]))
            else:
                tail, cb = [(xc, Po[1])], 0.0
                vl = vr(xc, ya_, Po[1])
                tj = exit_jog(Pf, Po, xc, ya_, bits)
                if tj is not None:
                    tail, cb, vl = tj
            # it24: vl is the window fill ratio (booked / cap); + bits / cap as the excess test
            vx = vl + bits / max(1.0, min(vcap(int(xc // FBIN), k) for k in _bins(min(ya_, Po[1]), max(ya_, Po[1]))))
            cost = ca + cb + abs(xc - Po[0]) / 4.0 + 20000.0 * max(0.0, vx - 1.0) + 600.0 * vl
            if best is None or cost < best[0]:
                best = (cost, la, tail)
        _, la, tail = best
        if _os.environ.get('OT_FA_DBG') and _dbg_cur[0].startswith(_os.environ['OT_FA_DBG']):
            print('FA_X', _dbg_cur[0], Pf, Po, best[0], la, tail, flush=True)
        return [Pf] + la + tail + [Po]

    _dbg_cur = ['']

    def _poly0(cl, P0, P1, bid=None, eps=None):
        _dbg_cur[0] = bid or ''
        f0, f1 = in_field(*P0), in_field(*P1)
        if _os.environ.get('OT_FA_DBG') and bid and bid.startswith(_os.environ['OT_FA_DBG']):
            print('FA_DBG', bid, cl, P0, P1, f0, f1, FIELD_ALLOC, list(side_cols(P0[0]))[:2], flush=True)
        if cl == 'head_chain' and abs(P0[0] - P1[0]) > 300.0 and abs(P0[1] - P1[1]) > 600.0:
            # r10: a head root whose head stands off the VM pin's x (the E root: the VM region is W-aligned on the spine):
            # one lane just outside the field on the head pin's side, entered from a short run below / above the VM pin
            # (the lane is the open strip between the KV-centre column and the field, not a field corridor)
            Ph, Pv = (P1, P0) if abs(P1[0] - (fw[2] + fe[0]) / 2) > abs(P0[0] - (fw[2] + fe[0]) / 2) else (P0, P1)
            xl = Ph[0] + (150.0 if Pv[0] > Ph[0] else -150.0)
            yv = Pv[1] + (130.0 if Ph[1] > Pv[1] else -130.0)
            path = [Pv, (Pv[0], yv), (xl, yv), (xl, Ph[1]), Ph]
            return path if Pv is P0 else path[::-1]
        if cl == 'corridor' or (abs(P0[0] - P1[0]) < 1.0 and not (FIELD_ALLOC and f0 and f1 and not cl.startswith('kvn'))):
            # it19: under FIELD_ALLOC a same-x field word goes through field_route too (the straight vertical
            # shortcut stacked 3 x 512-b tree words + a corridor word in one column channel: 0.72 / 0.68 / 0.65)
            return [P0, P1]
        if FIELD_ALLOC and cl != 'corridor' and not cl.startswith('kvn') and f0 and f1 and side_cols(P0[0]) == side_cols(P1[0]):
            return field_route(P0, P1, cur_bits[0])
        if FIELD_ALLOC and f0 != f1 and not cl.startswith('kvn'):
            Pf, Po = (P0, P1) if f0 else (P1, P0)
            path = field_exit(Pf, Po, cur_bits[0])
            return path if f0 else path[::-1]
        if f0 and f1 and side_cols(P0[0]) == side_cols(P1[0]):
            xm = (P0[0] + P1[0]) / 2
            lo, hi = sorted((P0[0], P1[0]))
            cs = [c for c in side_cols(P0[0]) if lo - 170.0 <= cx_list[c] <= hi + 170.0] or \
                [min(side_cols(P0[0]), key=lambda c: abs(cx_list[c] - xm))]
            xc = cx_list[min(cs, key=lambda c: load(c, P0[1], P1[1]) + abs(cx_list[c] - xm) / 2000.0)]
            return [P0, (xc, P0[1]), (xc, P1[1]), P1]
        if f0 != f1:
            Pf, Po = (P0, P1) if f0 else (P1, P0)
            cs = sorted(side_cols(Pf[0]), key=lambda c: abs(cx_list[c] - Po[0]))[:4]
            xc = cx_list[min(cs, key=lambda c: load(c, Pf[1], Po[1]) + abs(cx_list[c] - Po[0]) / 2000.0)]
            path = [Pf, (xc, Pf[1]), (xc, Po[1]), Po]
            return path if f0 else path[::-1]
        if io_ch is not None and max(P0[1], P1[1]) < io_ch[0] and abs(P0[0] - P1[0]) > 500.0:
            # it3: an IO-row word between two IO blocks that are not neighbours runs in the IO word channel above the
            # row (its straight run would cross the UCIe / collective PHY bodies: relays fell on the die edge and hopped
            # 1.3-3.5 mm over the PHY)
            lo_, hi_ = sorted((P0[0], P1[0]))
            if any(a < hi_ - 1.0 and lo_ + 1.0 < c and b < min(P0[1], P1[1]) + 1.0 < d for a, b, c, d in big):
                # two sub-lanes over the channel height, least-loaded first (one centre line stacked every word
                # in one 260-um window)
                # it4: four sub-lanes (one word per lane where possible: shared lanes stacked relays at the faces)
                hch = io_ch[1] - io_ch[0]
                subs = [io_ch[0] + hch * f for f in IO_SUB_F]
                k_ = io_lane(lo_, hi_, subs, allow=(0, 1, 2) if FIELD_ALLOC else None)
                return [P0, (P0[0], subs[k_]), (P1[0], subs[k_]), P1]
        if io_ch is not None and bid is not None and bid.split('__r')[0] == 'host_fdi' and abs(P0[0] - P1[0]) > 500.0 \
                and (P0[1] < io_ch[0]) != (P1[1] < io_ch[0]):
            # it4: the KV host link drops down a spine lane into its own IO-channel sub-lane, then along it to the host
            # SerDes face (it staircased across the field's bottom row into the serdes words' window)
            Pa, Pi = (P0, P1) if P1[1] < io_ch[0] else (P1, P0)
            hch = io_ch[1] - io_ch[0]
            subs = [io_ch[0] + hch * f for f in IO_SUB_F]
            k_ = io_lane(*sorted((P0[0], P1[0])), subs, allow=(3,) if FIELD_ALLOC else None)
            chx = getattr(v, 'SPINE_CHANNEL_X', None)
            xl = lane_pick(chx, Pa, (Pa[0], subs[k_]), lane_bits) if chx else Pa[0]
            xd = getattr(v, 'HOST_FDI_DROP_X', None)
            if xd is not None:
                # r9 (contract v5 T21): the PHY's FDI pins are on its W face: the link drops down the middle of the
                # access strip W of the macro and turns to the pins at their height
                path = [Pa, (xl, Pa[1]), (xl, subs[k_]), (xd, subs[k_]), (xd, Pi[1]), Pi]
            else:
                path = [Pa, (xl, Pa[1]), (xl, subs[k_]), (Pi[0], subs[k_]), Pi]
            return path if Pa is P0 else path[::-1]
        if kv_gaps and eps is not None and len(eps) == 2:
            n0, n1 = eps[0][0], eps[1][0]
            strip = lambda P: P[0] < fw[0] - 1.0 or P[0] > fe[2] + v.CORR + 1.0      # noqa: E731
            kc0, kc1 = n0 in KVC_NAMES, n1 in KVC_NAMES
            if (kc0 and strip(P1)) or (kc1 and strip(P0)):
                Pc, Ps = (P0, P1) if kc0 else (P1, P0)
                F = fw if Ps[0] < Pc[0] else fe
                chx = getattr(v, 'SPINE_CHANNEL_X', None) or [Pc[0]]
                kvl = [x for x in chx if abs(x - Pc[0]) < 1500.0] or [Pc[0]]
                best = None
                sd_ = 'W' if Ps[0] < Pc[0] else 'E'
                xs_ = (getattr(v, 'KV_XCH_STRIP', None) or {}).get(sd_)
                # it17: the jog column between the field and the strip's head stacks (W: E of the stacks; E: W of them)
                fe_ = F[0] if sd_ == 'W' else F[2] + v.CORR
                xj = round((xs_[1] + fe_) / 2 if sd_ == 'W' else (xs_[0] + fe_) / 2, 3) if xs_ else None

                def clear(y_, xa_, xb_):
                    lo_, hi_ = sorted((xa_, xb_))
                    return not any(a < hi_ - 1.0 and lo_ + 1.0 < c and b < y_ + 35.0 and y_ - 35.0 < d and c - a > 350.0
                                   and not (a <= Ps[0] <= c)
                                   and not (a <= Pc[0] <= c and b <= Pc[1] <= d) and not (F[0] - 1 <= a and c <= F[2] + v.CORR + 1)
                                   for a, b, c, d in big)
                # r8: the row-gap sub-lanes first; an over-tile (die M6) lane is offered only when no row-gap lane keeps
                # its fine windows within the cap (run a1: a 530-b word on an over-tile lane had its corridor relays
                # pushed off the lane by the stations and crossed a two-tree-word corridor window, vertical cut 0.659)
                m6_only = [y_ for y_ in kv_gaps if y_ not in gap_set] if getattr(v, 'CLUSTER_PLAN', 'A') == 'M6' else []
                for yg in [y_ for y_ in kv_gaps if not m6_only or y_ in gap_set] + [None] + m6_only:
                    if yg is None:
                        if best is not None and best[3] <= 1.0:
                            break
                        continue
                    gid = gap_id.get(yg)
                    if gid is not None and gap_tot.get(gid, 0.0) + cur_bits[0] > KV_GAP_CAP:
                        continue                 # it17: <= ~4 kb aggregate per row gap (all its sub-lanes)
                    if clear(yg, Pc[0], Ps[0]):
                        opts = [(yg, None)]
                    elif xj is not None and clear(yg, Pc[0], xj):
                        opts = [(yg, yc) for yc in v.KV_XCH.get(sd_, ())
                                if xch_bits.get((sd_, yc), 0.0) + cur_bits[0] <= KV_XCH_CAP]
                    else:
                        continue
                    for yg_, yc in opts:
                        yr = yg_ if yc is None else yc
                        det = abs(yg_ - Pc[1]) + abs(yg_ - yr) + abs(yr - Ps[1])
                        cost = det + 6000.0 * (gap_bits.get(yg_, 0.0) + cur_bits[0]) / 1000.0 + (0.0 if yg_ in gap_set else 600.0) \
                            + (6000.0 * (xch_bits.get((sd_, yc), 0.0) + cur_bits[0]) / 1000.0 if yc is not None else 0.0)
                        fill_ = 0.0
                        if FIELD_ALLOC:
                            # it24: the run's fine windows (cut-model caps): three sub-lanes of one gap share a window
                            fill_ = hr(yg_, Pc[0], Ps[0], cur_bits[0])
                            cost += 20000.0 * max(0.0, fill_ - 1.0) + 600.0 * hr(yg_, Pc[0], Ps[0])
                        if best is None or cost < best[0]:
                            best = (cost, yg_, yc, fill_)
                if best is not None:
                    yg, yc = best[1], best[2]
                    gap_bits[yg] = gap_bits.get(yg, 0.0) + cur_bits[0]
                    if gap_id.get(yg) is not None:
                        gap_tot[gap_id[yg]] = gap_tot.get(gap_id[yg], 0.0) + cur_bits[0]
                    if yc is not None:
                        xch_bits[(sd_, yc)] = xch_bits.get((sd_, yc), 0.0) + cur_bits[0]
                    yr = yg if yc is None else yc
                    tight_stride.add(bid)
                    if Ps[0] > Pc[0]:
                        # E-bound: the KV centre's E face is next to the E field: run up / down its first corridor
                        # it4b: E-bound words run up / down the 120-um gap between the KV centre stack and the E
                        # field (their pins are on that face): the corridor legs + horizontal stubs from the pins
                        # stacked 3.2 kb in one window (0.69)
                        xl = round((Pc[0] + F[0]) / 2, 3) if 0.0 < F[0] - Pc[0] < 200.0 else \
                            min((x for x in cx_list if x > Pc[0]), default=Pc[0])
                        if FIELD_ALLOC:
                            # it19: E-bound kvn words pick, by booked vertical load, among the KVc|E-field gap and
                            # the first two E-field corridors (all on the fixed gap crowded the KV-centre E face:
                            # 0.69 / 0.67)
                            xo = [xl] + sorted(x for x in cx_list if x > Pc[0] + 1.0 and abs(x - xl) > 1.0)[:2]
                            # it24: + the stub from the KVc E-face pin to the lane at pin height (a corridor lane's stub
                            # crosses the KVc|E gap with every other E-face word: 0.74 at x 18550)
                            xl = min(xo, key=lambda q: (vr(q, Pc[1], yg, cur_bits[0]) > 1.0 or hr(Pc[1], Pc[0], q, cur_bits[0]) > 1.0,
                                                        2000.0 * max(vr(q, Pc[1], yg), hr(Pc[1], Pc[0], q)) + 0.3 * abs(q - Pc[0])))
                    else:
                        xl = lane_pick(kvl, Pc, (Pc[0], yg), lane_bits) if all(x in lane_bits for x in kvl) else kvl[0]
                    fa, fb = (F[2] + v.CORR, F[0]) if Ps[0] < Pc[0] else (xl, F[2] + v.CORR)
                    jog = [] if yc is None else [(xj, yg), (xj, yc)]
                    path = [Pc, (xl, Pc[1]), (xl, yg), (fa, yg), (fb, yg)] + jog + [(Ps[0], yr), Ps]
                    bs = by.get(eps[1][0] if kc0 else eps[0][0])
                    if bs is not None and abs(Ps[1] - yr) > 1.0:
                        # it4: approach a strip pin from its own face: a pin on the N / S face of a block between the
                        # run height and the pin (wctl: the kvn leg ran up through its 518-um body, hop 575 um) is
                        # reached from a side channel beside the block, then along the face
                        top, bot = bs.y + bs.h, bs.y
                        face_n = abs(Ps[1] - top) < 2.0
                        face_s = abs(Ps[1] - bot) < 2.0
                        if (face_n and yr < bot) or (face_s and yr > top):
                            xs = bs.x + bs.w + 65.0 if Ps[0] < Pc[0] else bs.x - 65.0
                            ya = Ps[1] + (60.0 if face_n else -60.0)
                            path = [Pc, (xl, Pc[1]), (xl, yg), (fa, yg), (fb, yg)] + jog + [(xs, yr), (xs, ya), (Ps[0], ya), Ps]
                    return path if Pc is P0 else path[::-1]
        chx = getattr(v, 'SPINE_CHANNEL_X', None)
        if chx and abs(P0[1] - P1[1]) > 1000.0 and min(chx) - 1500.0 < P0[0] < max(chx) + 1500.0 \
                and min(chx) - 1500.0 < P1[0] < max(chx) + 1500.0 and lane_bits is not None:
            # r22k (kv-die KV2): a long vertical spine word runs in the spine relay channel nearest its two pins (the
            # spine columns abut blocks end to end: a leg over them has no relay site)
            if getattr(v, 'SPINE_LANE_BALANCE', False):
                xc = lane_pick(chx, P0, P1, lane_bits)
            else:
                xc = min(chx, key=lambda x: abs(x - P0[0]) + abs(x - P1[0]))
            return [P0, (xc, P0[1]), (xc, P1[1]), P1]
        return [P0, (P0[0], P1[1]), P1]

    # ---- r9 (die lead 2026-10-13, contract v5): WALLS.  A block longer than one hop along a wire has no relay site
    # inside it (the bit-plane VM region spans the spine: 4,709 x 2,348 um; the KV-centre column; the SU group), so a
    # planned leg through it put its relays in a heap at the block edge and left the chain to the pass-2 search (run
    # b2: every N-S spine word crossed the VM; x3 / emb found no free site near the SU for the heaps of the others).
    # A word whose planned path runs > WALL_HIT um inside a wall is re-planned on a rectilinear grid (block edges +-
    # WALL_CL, the spine lanes, the column corridors, the row gaps, the two pins) by a shortest-path search: an edge
    # inside a wall is not allowed, the cost is length + turns + the fill of the fine windows it would see (cut model
    # caps, as every other field allocation) with this word added.
    WALL_UM, WALL_CL, WALL_HIT = 320.0, 45.0, 30.0
    _is_tile = lambda it: getattr(it, 'master', '').startswith('qfd_tile')     # noqa: E731
    big_nt = [(it.x, it.y, it.x + it.w, it.y + it.h) for it in m['insts'] if it.w * it.h > 4e4 and not _is_tile(it)]
    _wl = {}
    wall_log = []

    def _walls(ax, c):
        """merged wall intervals on the line y = c (ax 'h': intervals in x) or x = c (ax 'v': intervals in y): big
        blocks whose interior holds the line, merged across gaps a relay frame does not fit (< 60 um), kept when
        longer than WALL_UM (a tile row is no wall for a horizontal wire: relays in every column corridor)"""
        key = (ax, round(c, 2))
        if key not in _wl:
            if ax == 'h':
                iv = sorted((a_, c_) for a_, b_, c_, d_ in big if b_ < c < d_)
            else:
                iv = sorted((b_, d_) for a_, b_, c_, d_ in big if a_ < c < c_)
            out = []
            for lo, hi in iv:
                if out and lo - out[-1][1] < 60.0:
                    out[-1][1] = max(out[-1][1], hi)
                else:
                    out.append([lo, hi])
            _wl[key] = [(lo, hi) for lo, hi in out if hi - lo > WALL_UM]
        return _wl[key]

    _wi = {}

    def _wall_iv(ax, c):
        """walls SEALING the line: stretches where both sides of the line (c - 3, c + 3) lie inside a wall.  A line along
        a block face with a free channel beside it is open (the relays stand in the channel); a line inside a block, or
        along the seam of two abutted blocks, is not."""
        key = (ax, round(c, 2))
        if key not in _wi:
            A_, B_, out = _walls(ax, c - 3.0), _walls(ax, c + 3.0), []
            for a0, a1 in A_:
                for b0, b1 in B_:
                    lo, hi = max(a0, b0), min(a1, b1)
                    if hi - lo > 1.0:
                        out.append((lo, hi))
            _wi[key] = out
        return _wi[key]

    def _wall_hit(pa, pb):
        (xa, ya), (xb, yb) = pa, pb
        if abs(ya - yb) < 1e-6:
            lo, hi, W_ = min(xa, xb), max(xa, xb), _wall_iv('h', ya)
        elif abs(xa - xb) < 1e-6:
            lo, hi, W_ = min(ya, yb), max(ya, yb), _wall_iv('v', xa)
        else:
            return 0.0
        return sum(max(0.0, min(hi, b_ - 2.0) - max(lo, a_ + 2.0)) for a_, b_ in W_)

    def _inside_big(P):
        return any(a_ + 2.0 < P[0] < c_ - 2.0 and b_ + 2.0 < P[1] < d_ - 2.0 for a_, b_, c_, d_ in big)

    def wall_route(P0, P1, bits):
        import heapq
        Wd, Hd = m['die']['w'], m['die']['h']
        x0, x1 = max(0.0, min(P0[0], P1[0]) - 2600.0), min(Wd, max(P0[0], P1[0]) + 2600.0)
        y0, y1 = max(0.0, min(P0[1], P1[1]) - 1600.0), min(Hd, max(P0[1], P1[1]) + 1600.0)
        keepx, keepy = {P0[0], P1[0]}, {P0[1], P1[1]}
        xs, ys = set(), set()
        for a_, b_, c_, d_ in big_nt:
            if a_ < x1 and c_ > x0 and b_ < y1 and d_ > y0:
                xs |= {a_ - WALL_CL, c_ + WALL_CL}
                ys |= {b_ - WALL_CL, d_ + WALL_CL}
        keepx |= {x for x in cx_list if x0 <= x <= x1}
        xs |= set(getattr(v, 'SPINE_CHANNEL_X', None) or [])
        ys |= {y for y in (gap_set or ()) if y0 <= y <= y1}
        for F_ in fields:
            ys |= {F_[1] - WALL_CL, F_[3] + WALL_CL}
            xs |= {F_[0] - WALL_CL, F_[2] + v.CORR + WALL_CL}

        def lines(keep_, more, lo, hi):
            out = sorted(q for q in keep_ if lo - 1e-6 <= q <= hi + 1e-6)
            for q in sorted(more):
                if lo <= q <= hi and all(abs(q - k_) > 8.0 for k_ in out):
                    out.append(q)
            return sorted(out)
        X, Y = lines(keepx, xs, x0, x1), lines(keepy, ys, y0, y1)
        ix = {q: i for i, q in enumerate(X)}
        iy = {q: i for i, q in enumerate(Y)}
        if len(X) * len(Y) > 400000:
            return None
        ecost = {}

        def edge(i, j, d):
            """cost of the edge from node (i, j) one step in direction d (0 E, 1 N, 2 W, 3 S); None = not allowed"""
            i2, j2 = i + (1, 0, -1, 0)[d], j + (0, 1, 0, -1)[d]
            if not (0 <= i2 < len(X) and 0 <= j2 < len(Y)):
                return None
            key = (min(i, i2), min(j, j2), d & 1)
            if key not in ecost:
                pa, pb = (X[i], Y[j]), (X[i2], Y[j2])
                L_ = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                if _wall_hit(pa, pb) > 1.0:
                    ecost[key] = None
                else:
                    c_ = L_
                    if FIELD_ALLOC and L_ > 2.0:
                        f_ = hr(pa[1], pa[0], pb[0], bits) if d & 1 == 0 else vr(pa[0], pa[1], pb[1], bits)
                        c_ += L_ * 0.5 * min(f_, 1.0) + 20000.0 * max(0.0, f_ - 1.0) * max(L_, 50.0) / 260.0
                    ecost[key] = c_
            return ecost[key], i2, j2
        src, dst = (ix[P0[0]], iy[P0[1]]), (ix[P1[0]], iy[P1[1]])
        dist, par = {}, {}
        heap = [(0.0, src[0], src[1], -1)]
        dist[(src[0], src[1], -1)] = 0.0
        end = None
        while heap:
            c0, i, j, d0 = heapq.heappop(heap)
            if c0 > dist.get((i, j, d0), 1e18) + 1e-9:
                continue
            if (i, j) == dst:
                end = (i, j, d0)
                break
            for d in range(4):
                if d0 >= 0 and (d - d0) % 4 == 2:
                    continue
                e_ = edge(i, j, d)
                if e_ is None or e_[0] is None:
                    continue
                c1 = c0 + e_[0] + (90.0 if d0 >= 0 and d != d0 else 0.0)
                k_ = (e_[1], e_[2], d)
                if c1 < dist.get(k_, 1e18):
                    dist[k_] = c1
                    par[k_] = (i, j, d0)
                    heapq.heappush(heap, (c1, e_[1], e_[2], d))
        if end is None:
            return None
        pts, k_ = [], end
        while k_ is not None:
            pts.append((X[k_[0]], Y[k_[1]]))
            k_ = par.get(k_)
        pts = pts[::-1]
        out = [pts[0]]
        for q in pts[1:]:
            if len(out) >= 2 and ((abs(out[-2][0] - out[-1][0]) < 1e-6 and abs(out[-1][0] - q[0]) < 1e-6) or
                                  (abs(out[-2][1] - out[-1][1]) < 1e-6 and abs(out[-1][1] - q[1]) < 1e-6)):
                out[-1] = q
            elif abs(q[0] - out[-1][0]) + abs(q[1] - out[-1][1]) > 1e-6:
                out.append(q)
        return out

    def die_lane_path(path, bid):
        lane_window = (getattr(v, 'DIE_LANE_WINDOWS', {}) or {}).get(bid)
        if lane_window:
            lo, hi, xl = lane_window['y0'], lane_window['y1'], lane_window['x']
            routed = [path[0]]
            for a, b in zip(path, path[1:]):
                if abs(a[0] - b[0]) < 1e-6 and max(a[1], b[1]) > lo and min(a[1], b[1]) < hi:
                    ya, yb = max(lo, min(hi, a[1])), max(lo, min(hi, b[1]))
                    routed.extend([(a[0], ya), (xl, ya), (xl, yb), (b[0], yb), b])
                else:
                    routed.append(b)
            path = [q for j, q in enumerate(routed) if not j or q != routed[j - 1]]
        return path

    def poly_of(cl, P0, P1, bid=None, eps=None):
        path = die_lane_path(_poly0(cl, P0, P1, bid=bid, eps=eps), bid)
        if not getattr(v, 'WALL_AVOID', False) or cl == 'corridor':
            return path
        if cl.startswith('kvn') or cl == 'd2d_fdi' or (bid or '') in tight_stride:
            # a planned run (KV row run, host link): only the leg that crosses a wall is taken round it
            out_, ch_ = [path[0]], False
            for a_, b_ in zip(path, path[1:]):
                sub = wall_route(a_, b_, cur_bits[0]) if _wall_hit(a_, b_) > WALL_HIT and not _inside_big(a_) and not _inside_big(b_) else None
                if sub:
                    out_ += sub[1:]
                    ch_ = True
                else:
                    out_.append(b_)
            if ch_:
                wall_log.append((bid, cl, cur_bits[0], 'leg', len(path), len(out_)))
            return die_lane_path(out_, bid)
        hit = sum(_wall_hit(a_, b_) for a_, b_ in zip(path, path[1:]))
        if hit <= WALL_HIT or _inside_big(P0) or _inside_big(P1):
            return path
        alt = wall_route(P0, P1, cur_bits[0])
        L0 = sum(abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) for a_, b_ in zip(path, path[1:]))
        L1 = sum(abs(a_[0] - b_[0]) + abs(a_[1] - b_[1]) for a_, b_ in zip(alt, alt[1:])) if alt else None
        wall_log.append((bid, cl, cur_bits[0], round(hit), round(L0), None if L1 is None else round(L1)))
        return die_lane_path(alt or path, bid)

    def candidates(path):
        """(arc, x, y, corr) points a relay may take along the path."""
        out, s = [], 0.0
        for (xa, ya), (xb, yb) in zip(path, path[1:]):
            L = abs(xb - xa) + abs(yb - ya)
            if L < 1e-6:
                continue
            horiz = abs(yb - ya) < 1e-6
            if horiz and in_field(xa, ya) and in_field(xb, yb):
                lo, hi = sorted((xa, xb))
                for c in range(COLS):
                    if lo - 1.0 <= cx_list[c] <= hi + 1.0 and in_field(cx_list[c], ya):
                        out.append((s + abs(cx_list[c] - xa), cx_list[c], ya, c, 'h'))
            else:
                n = max(1, int(L // 20.0))
                cr = corr_of(xa) if not horiz else None
                for i in range(1, n + 1):
                    f = i / n
                    x, y = xa + (xb - xa) * f, ya + (yb - ya) * f
                    out.append((s + L * f, x, y, cr if in_field(x, y) else None, 'v' if not horiz else 'o'))
            s += L
        return sorted(set(out), key=lambda q: (q[0], q[1], q[2], -1 if q[3] is None else q[3], q[4])), s

    masters_needed = {}
    regs = m['clock_regions']

    def region_of(cx, cy):
        return region_at(regs, cx, cy)
    ck_add = {}
    stats, B, fck_drop, fck_new, insts, worst, spill = {}, [], set(), [], [], [], []
    stage_of = {}
    # it24: the KV host link (d2d_fdi) places first: its spine lane + IO sub-lane relay sites never depend on the
    # order of the other classes (it22: kvn before trees took its sites and it staircased into the SerDes window)
    # r10 (token path, el1013-rom-layer-tput-qwen.log): the two head roots (VM xw / xe -> h_23 / h_24) are on every ME
    # op of a token: they place before every other class and take the shortest lane (run g0: head_24 was planned last
    # into the E field, 6 columns off its head and back: 25 stages against 8 on the W root)
    order = {'head_chain': -2, 'd2d_fdi': -1, 'corridor': 0, 'link_spine': 1, 'link_channel': 1, 'tree_spine': 2, 'tree_block': 3}
    buses = sorted(enumerate(m['buses']), key=lambda t: (order.get(t[1][1], 3), t[0]))
    keep = {}
    def relay_frame(bits, cl):
        """off-corridor relay frame: faces at one track; <= 512 b fits the 52.68 x 30.24 corridor relay, wider words
        take the face span (a link-spine relay is vertical flow only, N/S faces)."""
        span1 = bits * 0.048 + 4.0
        if bits <= RELAY_STD_BITS:
            return v.CORR - v.SHAVE, RELAY_V_H - v.SHAVE
        w = max(v.up(span1, v.GX), v.CORR) - v.SHAVE
        if cl == 'link_spine' and span1 > BWP_H:
            return w, RELAY_V_H - v.SHAVE
        return w, max(v.up(span1, v.GY), BWP_H) - v.SHAVE

    # ---- qwen-tp8 v2: tree-leg pad columns are RESERVED before the bulk relays (it1/v2g: placed after them, the
    # corridors next to the node were full and pads scattered up to 850 um from their sink).  Each padded leg gets
    # one contiguous column of `pad` frames in one corridor flanking its sink tile, starting at the sink's height and
    # growing toward the source; the bulk relays then route source -> far end of the column (P1 override), so
    # consecutive pads are one frame apart and the last pad is within reach of the M8 tree pins at the tile middle.
    tpads = getattr(v, 'TREE_PADS', None) or {}
    pre_pads, pre_far = {}, {}
    if tpads:
        bidx0 = {bid: idx for idx, (bid, cl, bits, eps) in buses}
        for bid, npad in sorted(tpads.items(), key=lambda t: -t[1]):
            if bid not in bidx0:
                raise ValueError(f'tree pads: no bus {bid}')
            idx = bidx0[bid]
            _, cl, bits, eps = m['buses'][idx]
            P0, P1 = pos(*eps[0]), pos(*eps[1])
            w, h = relay_frame(bits, cl)
            sgn = 1 if P0[1] >= P1[1] else -1
            best = None
            for c_ in sorted(range(COLS), key=lambda c: abs(corr_x0[c] + v.CORR / 2 - P1[0]))[:2]:
                x0 = corr_x0[c_]
                got, y = [], P1[1] - h / 2
                for k in range(npad):
                    hit = None
                    for t in range(0, int(600.0 / v.GY)):
                        y0 = v.dn(y + sgn * t * v.GY, v.GY)
                        r = (x0, y0, x0 + w + v.SHAVE, y0 + h + v.SHAVE)
                        if y0 >= g['y0'] and r[3] <= die_top and free(r) and \
                                not any(q[1] < r[3] - 1e-6 and r[1] < q[3] - 1e-6 for q in got):
                            hit = r
                            break
                    if hit is None:
                        break
                    got.append(hit)
                    y = hit[1] + sgn * (h + v.SHAVE)
                if len(got) < npad:
                    continue
                cen = [((q[0] + q[2]) / 2, (q[1] + q[3]) / 2) for q in got]
                hops = [abs(cen[0][0] - P1[0]) + abs(cen[0][1] - P1[1])] + \
                       [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(cen, cen[1:])]
                if best is None or max(hops) < best[0]:
                    best = (max(hops), got, cen)
            if best is None or best[0] > RMAX:
                continue                      # fall back to the post-bulk walk below
            for q in best[1]:
                add_rect(q)
            # chain order: far end first, the frame nearest the sink last
            pre_pads[idx] = [(q[0], q[1], w, h) for q in reversed(best[1])]
            pre_far[idx] = best[2][-1]
    def hops_of(pl):
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
    def backtracks(pl):
        """qwendie-1011 (textbook audit class 4 / fp_margin_lint far_side): a relay farther (Manhattan) from the next
        chain point than its predecessor is (+ 20 um) -- the chain doubles back."""
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        mh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])   # noqa: E731
        return any(mh(pts[i], pts[i + 1]) > mh(pts[i - 1], pts[i + 1]) + 20.0 for i in range(1, len(pts) - 1))

    GATE = bool(getattr(v, 'RELAY_REACH_GATE', False))
    PT_EXT = {}          # r10: block pin point -> half extents of its pin group (pos.ext)

    def _pt_key(o):
        return (round(o[0], 2), round(o[1], 2))

    def _ext_room(f, o, bits):
        """um the outer bits of a block pin group stand beyond a relay face (one track per bit) centred on it"""
        he = PT_EXT.get(_pt_key(o))
        if he is None:
            return 0.0
        return max(0.0, (he[1] if f in 'EW' else he[0]) - bits * 0.048 / 2)

    def frame_faces(pts, k, fr, bits):
        """(in face, out face) of relay frame k of a chain (pts = P0, frame centres, P1): toward the previous / next
        point on the dominant axis; both on one side: the output takes the other axis.  r9 (pin alignment): toward a
        BLOCK PIN (first / last hop) the face is turned to the other axis when the pin would stand nearer than the bus
        needs to jog and off the face centre by more than 20 um (the hop becomes an L, which needs no jog)."""
        x0, y0, w, h = fr
        here = pts[k + 1]

        def face(o):
            dx, dy = o[0] - here[0], o[1] - here[1]
            if abs(dx) >= abs(dy):
                return 'E' if dx > 0 else 'W'
            return 'N' if dy > 0 else 'S'
        fi, fo = face(pts[k]), face(pts[k + 2])
        if fi == fo:
            dx, dy = pts[k + 2][0] - here[0], pts[k + 2][1] - here[1]
            fo = ('E' if dx >= 0 else 'W') if fi in 'NS' else ('N' if dy >= 0 else 'S')
        fp = {'E': (x0 + w, y0 + h / 2), 'W': (x0, y0 + h / 2), 'N': (x0 + w / 2, y0 + h), 'S': (x0 + w / 2, y0)}
        need = bits / (0.60 * 31.51)

        def bad(f, o):
            # r9 / r10: a block pin group is as wide as its own pin plan (two tracks, area pins, a closed view's free
            # order): a relay nearer than the jog room is judged without trusting the centroid offset
            q = fp[f]
            gap, jog = (abs(q[0] - o[0]), abs(q[1] - o[1])) if f in 'EW' else (abs(q[1] - o[1]), abs(q[0] - o[0]))
            return gap < need and jog + _ext_room(f, o, bits) > 20.0

        def alt(f, o):
            dx, dy = o[0] - here[0], o[1] - here[1]
            return ('E' if dx >= 0 else 'W') if f in 'NS' else ('N' if dy >= 0 else 'S')
        if k + 2 == len(pts) - 1 and bad(fo, pts[k + 2]):
            a_ = alt(fo, pts[k + 2])
            if a_ != fi and not bad(a_, pts[k + 2]):
                fo = a_
        if k == 0 and bad(fi, pts[0]):
            a_ = alt(fi, pts[0])
            if a_ != fo and not bad(a_, pts[0]):
                fi = a_
        return fi, fo, fp

    def pin_pts(pl, faces=None):
        """relay-data 2026-10-13: the chain's pins as the emit step below draws them (port a at the centre of the face
        toward the previous point, b toward the next; both neighbours on one side: b takes the other axis)"""
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        out = [pl['P0']]
        for k, (x0, y0, w, h) in enumerate(pl['frames']):
            fi, fo, fp = frame_faces(pts, k, (x0, y0, w, h), pl['bits'])
            out += [fp[fi], fp[fo]]
            if faces is not None:
                faces += [fi, fo]
        out.append(pl['P1'])
        return out

    # r9 (coordinator 2026-10-13, tools/hier_contract/pin_align.py): a relay standing closer to its peer's pin face than
    # the bus needs to jog (gap < bits / JOG_TRK_UM) must stand IN FRONT of the pin (jog <= 20 um): the jog alone would
    # take more than 0.60 of the tracks between the two faces.  JOG_TRK_UM = 0.60 x 31.51 tracks per um of channel.
    JOG_TRK_UM, JOG_OK_UM = 0.60 * 31.51, 20.0
    OPPF = {'E': 'W', 'W': 'E', 'N': 'S', 'S': 'N'}

    def jog_bad(pl):
        """indices k of the frames with a too-near, offset pin pair (to the previous point: -k-1, to the next: k)"""
        fc = []
        q = pin_pts(pl, fc)
        n = len(pl['frames'])
        bad = []
        need = pl['bits'] / JOG_TRK_UM
        for k in range(n + 1):                       # hop k: point k (out pin) -> point k + 1 (in pin)
            a_, b_ = q[2 * k], q[2 * k + 1]
            fa = fc[2 * k - 1] if k >= 1 else None           # out face of frame k - 1
            fb = fc[2 * k] if k < n else None                # in face of frame k
            if fa is not None and fb is not None and fb != OPPF[fa]:
                continue                                      # an L between two relays: not judged
            f_ = fa or fb
            if f_ is None:
                continue
            gap, jog = (abs(a_[0] - b_[0]), abs(a_[1] - b_[1])) if f_ in 'EW' else (abs(a_[1] - b_[1]), abs(a_[0] - b_[0]))
            if n and k in (0, n):                 # r10: a block pin end is as wide as its own pin plan
                jog += _ext_room(f_, a_ if k == 0 else b_, pl['bits'])
            if (jog > JOG_OK_UM and gap < need) or (gap < 1.0 and jog > 0.1):      # + pin_align's abutted rule
                bad.append(k)
        return bad

    def p2p_hops(pl):
        """pin-to-pin hop lengths of a chain (the audit's measure); the allocator's own measure (hops_of) is centre to
        centre, up to w / 2 + h / 2 a side shorter"""
        q = pin_pts(pl)
        return [abs(q[i][0] - q[i + 1][0]) + abs(q[i][1] - q[i + 1][1]) for i in range(0, len(q), 2)]

    def reach_bad(pl):
        return GATE and max(p2p_hops(pl)) > RELAY_REACH_OK

    def chain_path(P0, frames, P1, poly):
        """it24: the rectilinear route of a PLACED relay chain (each hop an L whose corner lies nearer the allocator's
        poly) -- what the allocator books, so its load model is the placement, not the plan"""
        pts = [P0] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in frames] + [P1]

        def dpoly(q):
            best_ = 1e18
            for (xa_, ya_), (xb_, yb_) in zip(poly, poly[1:]):
                qx = min(max(q[0], min(xa_, xb_)), max(xa_, xb_))
                qy = min(max(q[1], min(ya_, yb_)), max(ya_, yb_))
                best_ = min(best_, abs(q[0] - qx) + abs(q[1] - qy))
            return best_
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
                out.append(min(((a[0], b[1]), (b[0], a[1])), key=dpoly))
            out.append(b)
        return out

    def rm_rect(r_):
        """r8: drop a frame rect from the live grid, tolerant of the two ways a frame's far corner is summed
        (x + (w + SHAVE) in pass 2, (x + w) + SHAVE elsewhere): an exact tuple test left pass-2 frames in place"""
        for gx in range(int((r_[0] - 1e-3) // BK), int((r_[2] + 1e-3) // BK) + 1):
            for gy in range(int((r_[1] - 1e-3) // BK), int((r_[3] + 1e-3) // BK) + 1):
                lst = grid.get((gx, gy))
                if lst:
                    lst[:] = [q for q in lst if not (abs(q[0] - r_[0]) < 1e-6 and abs(q[1] - r_[1]) < 1e-6
                                                     and abs(q[2] - r_[2]) < 1e-6 and abs(q[3] - r_[3]) < 1e-6)]

    def unplace(frames):
        for f in frames:
            r_ = (f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE)
            rm_rect(r_)
            cc_ = corr_of(f[0] + f[2] / 2)
            if cc_ is not None and (f[1], f[1] + f[3]) in corr_used.get(cc_, []):
                corr_used[cc_].remove((f[1], f[1] + f[3]))

    def replace_frames(frames):
        for f in frames:
            add_rect((f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE))
            cc_ = corr_of(f[0] + f[2] / 2)
            if cc_ is not None:
                corr_used.setdefault(cc_, []).append((f[1], f[1] + f[3]))
    booked = {}          # it24: idx -> (booked rectilinear chain route, bits)
    # contract v4 T7 / v5 (r8): a PAIRED bus = x_d (with the flow) + its 1-b x_r (ready, against the flow).  The reverse
    # net is never planned by itself: it rides the forward chain's relay frames (one registered hop each way per frame,
    # the closed station family ot_qwen_die_station TAP=0), relay ports a_d / a_r (upstream face) and b_d / b_r
    pair = dict(m.get('bus_pair') or {})          # forward bid -> reverse bid
    rev_idx = {b_[0]: j_ for j_, b_ in enumerate(m['buses']) if b_[0] in set(pair.values())}
    feedback = []        # it24: (bid, max hop before, after, accepted)
    plans = {}
    import os as _os
    _only = tuple(q for q in _os.environ.get('OT_RELAY_ONLY', '').split(',') if q)   # debug: relay only these buses
    _dbg = set(q for q in _os.environ.get('OT_RELAY_DBG', '').split(',') if q)
    for idx, (bid, cl, bits, eps) in buses:
        # relay-data 2026-10-13: 'not relayed' classes (<= 350 um by construction) are relayed all the same when their
        # pins are farther apart than the die reach (wcf_*: cdc -> landing, 623 um pin to pin, 128 words); a kept KV
        # chain ('@kv') is never touched here (a torn one was already handed over whole by _tp8b_kv)
        skip_cl = cl in RELAY_SKIP
        if bid in rev_idx:
            keep[idx] = [(bid, cl, bits, eps)]      # replaced by per-hop reverse nets when its forward bus is relayed
            continue
        if len(eps) != 2 or (_only and not bid.startswith(_only)) or (skip_cl and (
                not GATE or cl in RELAY_NEVER or cl.endswith('@kv'))):
            keep[idx] = [(bid, cl, bits, eps)]
            continue
        P0, P1 = pos(*eps[0]), pre_far.get(idx) or pos(*eps[1])
        PT_EXT[_pt_key(P0)] = pos.ext(*eps[0])
        if idx not in pre_far:
            PT_EXT[_pt_key(P1)] = pos.ext(*eps[1])
        d = abs(P0[0] - P1[0]) + abs(P0[1] - P1[1])
        terminal = getattr(v, 'TERMINAL_TIGHT', {})
        direct_limit = min(terminal.get(tuple(eps[0]), float('inf')), terminal.get(tuple(eps[-1]), float('inf')))
        if _dbg and bid in _dbg:
            print('DBG0', bid, cl, bits, eps, P0, P1, round(d, 1), GATE, P2P_REACH, skip_cl, direct_limit, flush=True)
        if d <= min(RELAY_REACH_OK if (skip_cl or (GATE and P2P_REACH)) else RMAX, direct_limit):   # C7: pin to pin
            keep[idx] = [(bid, cl, bits, eps)]
            continue
        cur_bits[0] = bits
        path = poly_of(cl, P0, P1, bid=bid, eps=eps)
        span1 = bits * 0.048 + 4.0
        span2 = bits * 0.096 + 4.0

        wide = span1 > v.CORR - v.SHAVE     # split compute C7: a word whose one-track face exceeds the corridor
        #                                     (DVM head word 1,567 b) takes the off-corridor frame, placed off-corridor

        def frame(c, bits=bits, span1=span1, span2=span2):
            if c[3] is not None and not wide:       # corridor lane: full corridor width, faces at 1 track up to 520 b
                if bits <= RELAY_STD_BITS:
                    return v.CORR - v.SHAVE, RELAY_V_H - v.SHAVE
                return v.CORR - v.SHAVE, max(v.up(min(span2, max(span1, BWP_H)), v.GY), BWP_H) - v.SHAVE
            return relay_frame(bits, cl)

        def _try(c, tol):
            w, h = frame(c)
            sp = place(c[1], c[2], w + v.SHAVE, h + v.SHAVE, None if wide else c[3], tol)
            return None if sp is None else (sp[0], sp[1], w, h)
        def _chain(path):
            cands, L = candidates(path)
            frames, s_last, ycur = [], 0.0, None
            # qwendie-1011: a TERMINAL_TIGHT endpoint (an unregistered element input: ctlm c* carries p_am into the
            # fixed-latency argmax loop) gets its relay within `tight` um of the pin; same relay count (checked by the caller)
            tt_ = getattr(v, 'TERMINAL_TIGHT', {})
            tight0 = tt_.get(tuple(eps[0]))
            tight1 = tt_.get(tuple(eps[-1]))
            pitch_b = pitch - 70.0 if bid in tight_stride else pitch
            cur_tight[0] = bid in tight_stride
            cur_gapok[0] = cl == 'head_chain'
            while L - s_last > (tight1 if tight1 and len(frames) else pitch_b) or (tight0 and not frames and L > tight0):
                hi_ = tight0 if (tight0 and not frames) else pitch_b
                reach = [c for c in cands if s_last + 1.0 < c[0] <= s_last + hi_]
                if not reach:
                    nxt = [c for c in cands if c[0] > s_last + 1.0]
                    if not nxt:
                        break
                    reach = nxt[:1]
                if ycur is not None:      # a horizontal run keeps the height of its previous relay (no zig-zag)
                    reach = [(c[0], c[1], ycur, c[3], c[4]) if (c[4] == 'h' or (c[4] == 'o' and bid in tight_stride))
                             and abs(ycur - c[2]) < 400.0 else c for c in reach]
                got = None
                for tol in (20.0, 80.0, 200.0):
                    for c in reach[::-1]:
                        sp = _try(c, tol)
                        if sp is not None:
                            got = (c, sp)
                            break
                    if got is not None:
                        break
                if got is None:
                    c = reach[-1]
                    sp = _try(c, None)
                    if sp is None:
                        raise ValueError(f'relays: no free spot for {bid} near ({c[1]:.0f}, {c[2]:.0f})')
                    got = (c, sp)
                x0, y0, w, h = got[1]
                add_rect((x0, y0, x0 + w + v.SHAVE, y0 + h + v.SHAVE))
                cc_ = corr_of(x0 + w / 2)
                if cc_ is not None:
                    corr_used.setdefault(cc_, []).append((y0, y0 + h))
                frames.append((x0, y0, w, h))
                ycur = y0 + h / 2 if (got[0][4] == 'h' or (got[0][4] == 'o' and bid in tight_stride and ycur is not None)) else None
                s_last = got[0][0]
                if _dbg and bid in _dbg:
                    print('DBG', bid, 'L', round(L), 'path', [(round(a), round(b)) for a, b in path] if len(frames) == 1 else '',
                          'c', [round(q) if isinstance(q, float) else q for q in got[0]], 'at', (round(x0), round(y0)))
            return frames

        frames = _chain(path)
        if FIELD_ALLOC and cl != 'corridor' and not cl.startswith('kvn') and (in_field(*P0) or in_field(*P1)):
            # it24: feedback from placement to the allocator.  A chain whose relays could not keep <= RMAX hops (or that
            # doubles back) would go to the pass-2 search, which wanders off the booked route (tree_26_1_4b: booked
            # corridor 19220, placed down the KVc|E gap and back over t_24_8: 0.92).  Instead the stretch where the
            # chain failed gets a phantom full load and the allocator picks again (<= 2 tries; the best chain wins).
            def _bad(fr):
                pl_ = dict(P0=P0, P1=P1, frames=fr, bits=bits)
                if GATE and P2P_REACH:
                    return max(p2p_hops(pl_)) > RELAY_REACH_OK or backtracks(pl_)
                return max(hops_of(pl_)) > RMAX + 25.0 or backtracks(pl_)
            for _try_n in range(2):
                if not _bad(frames):
                    break
                pts_ = [P0] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in frames] + [P1]
                hs_ = hops_of(dict(P0=P0, P1=P1, frames=frames))
                j_ = max(range(len(hs_)), key=lambda q: hs_[q])
                (ax_, ay_), (bx_, by_) = pts_[j_], pts_[j_ + 1]
                box = (min(ax_, bx_) - 60.0, min(ay_, by_) - 60.0, max(ax_, bx_) + 60.0, max(ay_, by_) + 60.0)
                ph = []
                for (xa_, ya_), (xb_, yb_) in zip(path, path[1:]):
                    xa2, xb2 = max(min(xa_, xb_), box[0]), min(max(xa_, xb_), box[2])
                    ya2, yb2 = max(min(ya_, yb_), box[1]), min(max(ya_, yb_), box[3])
                    if abs(xa_ - xb_) < 1e-6 and box[0] <= xa_ <= box[2] and yb2 > ya2:
                        ph.append([(xa_, ya2), (xa_, yb2)])
                    elif abs(ya_ - yb_) < 1e-6 and box[1] <= ya_ <= box[3] and xb2 > xa2:
                        ph.append([(xa2, ya_), (xb2, ya_)])
                if not ph:
                    break
                for q in ph:
                    book(q, 1e6)
                path2 = poly_of(cl, P0, P1, bid=bid, eps=eps)
                for q in ph:
                    book(q, -1e6)
                if path2 == path:
                    break
                unplace(frames)
                frames2 = _chain(path2)
                ok2 = not _bad(frames2)
                feedback.append((bid, round(max(hs_)), round(max(hops_of(dict(P0=P0, P1=P1, frames=frames2)))), ok2))
                if ok2:
                    path, frames = path2, frames2
                else:
                    unplace(frames2)
                    replace_frames(frames)
                    break
        if FIELD_ALLOC:
            # it24: book the PLACED chain (the allocator's load model = the placement)
            cp_ = chain_path(P0, frames, P1, path)
            book(cp_, bits)
            booked[idx] = (cp_, bits)
        plans[idx] = dict(bid=bid, cl=cl, bits=bits, eps=eps, P0=P0, P1=P1, frames=frames, d=d, path=path)

    # ---- pass 2: a bus whose relays could not keep <= RMAX hops (crowded lane, a spine macro in the way)
    # is re-placed by a breadth-first search over every free relay spot of the die: wires may cross any macro on
    # M8/M9, only the relays need free area, so the fewest-relay chain with every hop <= pitch is found exactly
    import numpy as np
    from scipy.spatial import cKDTree
    site_cache = {}
    grid0 = {}
    for it in m['insts']:              # sites ignore relays (ok() re-checks every site against the live grid)
        r_ = (it.x, it.y, it.x + it.w, it.y + it.h)
        for gx in range(int(r_[0] // BK), int(r_[2] // BK) + 1):
            for gy in range(int(r_[1] // BK), int(r_[3] // BK) + 1):
                grid0.setdefault((gx, gy), []).append(r_)

    def free0(r):
        if r[0] < 0 or r[1] < 0 or r[2] > m['die']['w'] or r[3] > m['die']['h']:
            return False
        for gx in range(int(r[0] // BK), int(r[2] // BK) + 1):
            for gy in range(int(r[1] // BK), int(r[3] // BK) + 1):
                for q in grid0.get((gx, gy), ()):
                    if q[0] < r[2] - 1e-6 and r[0] < q[2] - 1e-6 and q[1] < r[3] - 1e-6 and r[1] < q[3] - 1e-6:
                        return False
        return True

    def sites(w, h, gaps=False):
        """lower-left corners where a w x h relay frame fits: every corridor slot (32.4 um steps) and a 21.6 um grid
        over the free area outside the tile arrays (gaps: also the free in-field area, i.e. the row gaps)."""
        key = (round(w, 3), round(h, 3), gaps)
        if key in site_cache:
            return site_cache[key]
        pts = []
        if w <= v.CORR + 1e-6:
            for c in range(COLS):
                x0 = corr_x0[c]
                y = v.up(g['y0'], v.GY)
                while y + h <= die_top:
                    if free0((x0, y, x0 + w, y + h)):
                        pts.append((x0, y))
                    y = round(y + 15 * v.GY, 6)
        step = 21.6
        for x in np.arange(0.0, m['die']['w'] - w, step):
            for y in np.arange(0.0, m['die']['h'] - h, step):
                x0, y0 = v.up(float(x), v.GX), v.up(float(y), v.GY)
                if in_field(x0 + w / 2, y0 + h / 2) and y0 + h <= die_top + 1.0 and not gaps:
                    continue
                if free0((x0, y0, x0 + w, y0 + h)):
                    pts.append((x0, y0))
        arr = np.array(pts) if pts else np.zeros((0, 2))
        site_cache[key] = (arr, cKDTree(arr + np.array([w / 2, h / 2])) if len(arr) else None)
        return site_cache[key]


    repaired, unrepaired, off_plan, cut_over = [], [], [], []
    lifted0 = set()      # r9: chains lifted off the grid at the start of pass 2 (their pass-1 frames are not restored)
    unrep = {}           # r8: bid -> reason (a chain repaired by a later rip-up pass leaves the list)
    rep_at = {}          # r8: idx of every chain pass 2 re-placed
    hop_chk = [None]     # r6: the load test of the span search (None outside it)

    def needs_repair(pl):
        if GATE and P2P_REACH:
            return backtracks(pl) or reach_bad(pl)
        hs = hops_of(pl)
        return not (max(hs) <= RMAX + 25.0 and not backtracks(pl) and not reach_bad(pl))

    def repair(idx, pl, gaps=False):
        hs = hops_of(pl)
        bits = pl['bits']
        w, h = relay_frame(bits, pl['cl'])
        W, H = w + v.SHAVE, h + v.SHAVE
        # r8 (coordinator 2026-10-13): row-gap sites are legal for head chains (h_<c> sits at a row gap in the column
        # channel: head_24's W pin had no free site within reach once its neighbours were repaired)
        arr, tree = sites(W, H, gaps or pl['bid'] in tight_stride or (GATE and pl['cl'] == 'head_chain'))
        if tree is None:
            unrep[pl['bid']] = 'no sites'
            return False
        # free the bus's own pass-1 relays for its search
        own = [(f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE) for f in pl['frames']]
        for r_ in own:
            rm_rect(r_)
        D = RMAX - max(W, H) / 2 + 26.0
        if GATE and P2P_REACH:
            # split-compute C4: the reach is PIN TO PIN (owner rule; RELAY_REACH_OK): two frames face to face on the
            # dominant axis are up to one frame extent nearer than their centres
            D = RELAY_REACH_OK + max(W, H)
        P0, P1 = pl['P0'], pl['P1']
        ctr = arr + np.array([W / 2, H / 2])
        # qwendie-1011: every hop of the searched chain makes progress toward the load (no doubling back)
        dP1 = np.abs(ctr[:, 0] - P1[0]) + np.abs(ctr[:, 1] - P1[1])
        ok_cache = {}

        near = None
        # it24: under FIELD_ALLOC every repaired chain stays near its (allocator-booked) route: within 450 um (KV row
        # runs, as before), 300 um (field words), 120 um (the host link in its IO sub-lane: it22 wandered into the
        # SerDes window); only if that search fails does the unconstrained one run, and the bus is listed off_plan
        near_r = 450.0 if pl['bid'] in tight_stride else (
            (120.0 if pl['cl'] == 'd2d_fdi' else 300.0) if FIELD_ALLOC and pl.get('path') else None)
        if near_r is not None:
            # it4: a KV row-run word is repaired within 450 um of its planned path (the unconstrained search wandered
            # down to the IO channel and back: 80-140 relays on words planned at 50-90)
            near = np.full(len(ctr), np.inf)
            arcp = np.zeros(len(ctr))
            s0_ = 0.0
            for (xa_, ya_), (xb_, yb_) in zip(pl['path'], pl['path'][1:]):
                qx = np.clip(ctr[:, 0], min(xa_, xb_), max(xa_, xb_))
                qy = np.clip(ctr[:, 1], min(ya_, yb_), max(ya_, yb_))
                dd = np.abs(ctr[:, 0] - qx) + np.abs(ctr[:, 1] - qy)
                better = dd < near
                arcp = np.where(better, s0_ + np.abs(qx - xa_) + np.abs(qy - ya_), arcp)
                near = np.minimum(near, dd)
                s0_ += abs(xb_ - xa_) + abs(yb_ - ya_)
            neard = near
            near = near <= near_r
            # progress along the planned path (not toward the load: the run detours by design)
            dP1 = s0_ - arcp
            dP1_arc = dP1
        dP1_free = np.abs(ctr[:, 0] - P1[0]) + np.abs(ctr[:, 1] - P1[1])

        def ok(i):
            if i not in ok_cache:
                x0, y0 = arr[i]
                ok_cache[i] = (near is None or bool(near[i])) and free((x0, y0, x0 + W, y0 + H))
            return ok_cache[i]
        near_cons = near
        def _e_pin(pt, i):            # block pin point -> frame i face (pin to pin estimate)
            dx_, dy_ = abs(ctr[i][0] - pt[0]), abs(ctr[i][1] - pt[1])
            return dx_ + dy_ - (W / 2 if dx_ >= dy_ else H / 2)

        def _e_ff(i, j):              # frame i -> frame j, facing faces on the dominant axis
            dx_, dy_ = abs(ctr[i][0] - ctr[j][0]), abs(ctr[i][1] - ctr[j][1])
            return dx_ + dy_ - (W if dx_ >= dy_ else H)
        p2p_on = GATE and P2P_REACH
        RCH = RELAY_REACH_OK - 5.0

        def bfs(De, mono):
            if not _relay_terminal_possible(ctr, P1, De, ok, hop_chk[0]):
                return None, {}, []
            start = [i for i in tree.query_ball_point(P0, De, p=1) if ok(i) and (not p2p_on or _e_pin(P0, i) <= RCH) and (
                hop_chk[0] is None or hop_chk[0](P0, (float(ctr[i][0]), float(ctr[i][1]))))]
            par = {i: -1 for i in start}
            front, hit = start, None
            while front and hit is None and len(par) < 400000:
                for i in front:
                    if abs(ctr[i][0] - P1[0]) + abs(ctr[i][1] - P1[1]) <= De and (not p2p_on or _e_pin(P1, i) <= RCH) and (
                            hop_chk[0] is None or hop_chk[0]((float(ctr[i][0]), float(ctr[i][1])), P1)):
                        hit = i
                        break
                if hit is not None:
                    break
                nxt = []
                for i, nb in zip(front, tree.query_ball_point(ctr[front], D, p=1)):
                    for j in nb:
                        if j not in par and (not mono or dP1[j] < dP1[i]) and ok(j) and (not p2p_on or _e_ff(i, j) <= RCH) and (
                                not GATE or abs(arr[j][0] - arr[i][0]) >= W or abs(arr[j][1] - arr[i][1]) >= H) and (
                                hop_chk[0] is None or hop_chk[0]((float(ctr[i][0]), float(ctr[i][1])),
                                                                 (float(ctr[j][0]), float(ctr[j][1])))):
                            par[j] = i
                            nxt.append(j)
                nxt.sort(key=lambda j: dP1[j])
                front = nxt[:4000]
            return hit, par, start

        def chain_of(hit, par):
            c_ = [hit]
            while par[c_[-1]] != -1:
                c_.append(par[c_[-1]])
            return [(float(arr[i][0]), float(arr[i][1]), w, h) for i in c_[::-1]]
        # qwendie-1011: a monotone chain (each relay closer to the load: no doubling back) first; the unconstrained
        # search only when the pass-1 hops are too long; a pass-1 chain whose hops pass is never replaced by a worse one
        need = reach_bad(pl) if (GATE and P2P_REACH) else (max(hs) > RMAX + 25.0 or reach_bad(pl))
        found, why = None, ''
        tries = [(D, True), (D, False), (430.0 - max(W, H) / 2, True), (430.0 - max(W, H) / 2, False)]
        unbooked = False
        if GATE:
            # relay-data 2026-10-13 (pinreg audit: 28 chains left 'unrepaired' and silently kept, hops to 2.4 mm).  A
            # planned leg over a block (a KV-half word's end leg ran 4 mm inside the attention stack to its S-face pin)
            # has no relay site within the route corridor.  r6: only the BAD SPAN of the chain is searched again (the
            # frames around every hop over the reach, +- 1, then +- 3, then the whole chain): the rest of the chain
            # stays on its booked route.  The span search is LOAD-AWARE (a hop is taken only when one of its two L
            # routes fits the allocator's window caps with this word added: cut <= 0.58 usable, then <= 0.60), inside
            # the route corridor first, then 2x / 4x / 8x wider, then the whole die; a chain is accepted only when
            # every hop is <= RELAY_REACH_OK PIN TO PIN and no two frames overlap.  The first run of this rule (v1)
            # re-searched whole chains without the load test: kvn_WS left its row gap for a mid-tile lane two block
            # words already used (cut 0.864).
            radii = [near_r, 2 * near_r, 4 * near_r, 8 * near_r, None] if near_r is not None else [None]
            off, fallback = False, None
            if idx in booked:
                book(booked[idx][0], -bits)
                unbooked = True
            nfr = len(pl['frames'])
            hp_, hc_ = p2p_hops(pl), hops_of(pl)
            badk = [k_ for k_ in range(nfr + 1) if hp_[k_] > RELAY_REACH_OK or (hc_[k_] > RMAX + 25.0 and not P2P_REACH)]
            spans_ = []
            if badk and not backtracks(pl):
                for mg_ in (1, 3):
                    sp_ = (max(0, min(badk) - mg_), min(nfr, max(badk) + mg_))
                    if sp_ not in spans_ and sp_ != (0, nfr):
                        spans_.append(sp_)
            spans_.append((0, nfr))
            lims = [1.0, 0.60 / CAP_FRAC, None] if FIELD_ALLOC else [None]
            lim_cur = [None]

            def hop_fits(pa, pb):
                """one of the two L routes pa -> pb stays within the window caps with this word added"""
                lim = lim_cur[0]
                if lim is None:
                    return True
                (xa_, ya_), (xb_, yb_) = pa, pb
                if max(hr(ya_, xa_, xb_, bits), vr(xb_, ya_, yb_, bits)) <= lim:
                    return True
                return max(vr(xa_, ya_, yb_, bits), hr(yb_, xa_, xb_, bits)) <= lim

            def _overlap(fr):
                return any(abs(p_[0] - q_[0]) < W and abs(p_[1] - q_[1]) < H for i_, p_ in enumerate(fr) for q_ in fr[i_ + 1:])

            def _rm_rect(r_):
                for gx in range(int(r_[0] // BK), int(r_[2] // BK) + 1):
                    for gy in range(int(r_[1] // BK), int(r_[3] // BK) + 1):
                        lst = grid.get((gx, gy), [])
                        if r_ in lst:
                            lst.remove(r_)
            P0_, P1_ = P0, P1
            for a_, b_ in spans_:
                pre_, suf_ = pl['frames'][:a_], pl['frames'][b_:]
                kept_ = [(f[0], f[1], f[0] + W, f[1] + H) for f in pre_ + suf_]
                if idx in lifted0 and any(not free(r_) for r_ in kept_):
                    # r9: a lifted chain keeps the rest of its pass-1 chain only while those sites are still free (run
                    # f1: 13 chains 'self-overlap': the kept frames had gone to chains repaired before)
                    continue
                for r_ in kept_:
                    add_rect(r_)
                P0 = (pre_[-1][0] + w / 2, pre_[-1][1] + h / 2) if pre_ else P0_
                P1 = (suf_[0][0] + w / 2, suf_[0][1] + h / 2) if suf_ else P1_
                dP1_free = np.abs(ctr[:, 0] - P1[0]) + np.abs(ctr[:, 1] - P1[1])
                hop_chk[0] = hop_fits
                for lim in lims:
                    lim_cur[0] = lim
                    for r_ in radii:
                        if r_ is None:
                            near, dP1 = None, dP1_free
                        else:
                            near, dP1 = neard <= r_, dP1_arc
                        ok_cache.clear()
                        for De, mono in tries:
                            if not mono and not need:
                                continue
                            hit, par, start = bfs(De, mono)
                            if hit is None:
                                _e = tree.query_ball_point(P1, De, p=1)     # sites at the load end: all / free / reached
                                why = (f"span {a_}-{b_} of {nfr}, start {len(start)}, visited {len(par)}, sites {len(arr)}, "
                                       f"D {D:.0f}, De {De:.0f}, corridor {r_}, load {lim}, end sites {len(_e)} / free "
                                       f"{sum(1 for i_ in _e if ok(i_))} / reached {sum(1 for i_ in _e if i_ in par)}, "
                                       f"P0 ({P0[0]:.0f}, {P0[1]:.0f}) P1 ({P1[0]:.0f}, {P1[1]:.0f})")
                                continue
                            cand = pre_ + chain_of(hit, par) + suf_
                            plc = dict(pl, frames=cand)
                            if _overlap(cand):
                                why = 'self-overlap'
                                continue
                            if max(p2p_hops(plc)) > RELAY_REACH_OK:
                                why = f'span {a_}-{b_}: pin-to-pin {max(p2p_hops(plc)):.0f}'
                                continue
                            if backtracks(plc) and not mono:
                                fallback = fallback or (cand, r_, lim)
                                continue
                            found = cand
                            break
                        if found is not None:
                            break
                    if found is not None:
                        break
                hop_chk[0] = None
                for r__ in kept_:
                    _rm_rect(r__)
                if found is not None:
                    off = r_ != radii[0]
                    if lim is None and FIELD_ALLOC:
                        cut_over.append(pl['bid'])
                    break
            P0, P1 = P0_, P1_
            if found is None and fallback is not None and need:
                found, off = fallback[0], fallback[1] != radii[0]
                if fallback[2] is None and FIELD_ALLOC:
                    cut_over.append(pl['bid'])
        else:
            tries = [(D, True), (D, False), (430.0 - max(W, H) / 2, True), (430.0 - max(W, H) / 2, False)]
            if near_cons is not None and FIELD_ALLOC and pl['bid'] not in tight_stride:
                tries = [(De_, mo_, True) for De_, mo_ in tries] + [(De_, mo_, False) for De_, mo_ in tries]
            else:
                tries = [(De_, mo_, True) for De_, mo_ in tries]
            off = False
            for De, mono, cons in tries:
                if not mono and not need:
                    continue
                if found is not None and not cons and not off:
                    break                    # a constrained chain exists: never trade it for an off-plan one
                if not cons and not off:
                    off = True
                    near = None
                    dP1 = dP1_free
                    ok_cache.clear()
                hit, par, start = bfs(De, mono)
                if hit is None:
                    why = f"start {len(start)}, visited {len(par)}, sites {len(arr)}, D {D:.0f}"
                    continue
                cand = chain_of(hit, par)
                if mono or not backtracks(dict(pl, frames=cand)) or found is None:
                    found = cand
                if mono or not need:
                    break
                if not backtracks(dict(pl, frames=cand)):
                    break
        frames = []
        if found is not None:
            for f in found:
                r_ = (f[0], f[1], f[0] + W, f[1] + H)
                if not free(r_):
                    break
                add_rect(r_)
                frames.append(f)
            if len(frames) != len(found):
                # the found chain overlaps itself: roll it back (a partial chain leaves a gap hop)
                for f in frames:
                    r_ = (f[0], f[1], f[0] + W, f[1] + H)
                    for gx in range(int(r_[0] // BK), int(r_[2] // BK) + 1):
                        for gy in range(int(r_[1] // BK), int(r_[3] // BK) + 1):
                            lst = grid.get((gx, gy), [])
                            if r_ in lst:
                                lst.remove(r_)
                frames, why = [], 'self-overlap'
        if not frames:
            unrep[pl['bid']] = why
            if idx not in lifted0:
                for r_ in own:
                    add_rect(r_)
            else:
                # Pass-1 frames were lifted before the work list, so another
                # repaired chain may own their sites now. Do not emit those
                # stale rectangles on a failed search. The open chain remains
                # explicitly unrepaired; a later retry can search fresh sites.
                pl['frames'] = []
            if unbooked:
                book(booked[idx][0], bits)
            return False
        old = len(pl['frames'])
        pl['frames'] = frames
        unrep.pop(pl['bid'], None)
        rep_at[idx] = True
        repaired[:] = [q for q in repaired if q[0] != pl['bid']]
        repaired.append((pl['bid'], old, len(frames), round(max(hops_of(pl)), 1)))
        if off and pl['bid'] not in off_plan:
            off_plan.append(pl['bid'])
        if idx in booked:
            # it24: re-book the repaired chain in place of the pass-1 one
            if not unbooked:
                book(booked[idx][0], -bits)
            cp_ = chain_path(P0, frames, P1, pl['path'])
            book(cp_, bits)
            booked[idx] = (cp_, bits)
        return True

    # r8 (coordinator 2026-10-13: "rip up and re-repair neighbouring chains on failure"): pass 2 is a work list.  A chain
    # that cannot be repaired names its victims = the chains pass 2 already re-placed that hold a frame within RIP_UM of
    # one of its bad hops; their frames are lifted, the failing chain is repaired first, then every victim takes its
    # old frames back where they are still free and is re-repaired where they are not (span search around the lost
    # frames).  One rip-up round per failing chain; a second failure restores the victims untouched.
    RIP_UM = 450.0
    rip_log, gap_tier, retry_log = [], [], []

    def _bad_pts(pl):
        pts_ = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        hp_, hc_ = p2p_hops(pl) if GATE else hops_of(pl), hops_of(pl)
        out = []
        for k_ in range(len(hc_)):
            if (hc_[k_] > RMAX + 25.0 and not (GATE and P2P_REACH)) or (GATE and hp_[k_] > RELAY_REACH_OK):
                out += [pts_[k_], pts_[k_ + 1]]
        return out or [pl['P0'], pl['P1']]

    def _lift(j):
        plj = plans[j]
        fr = list(plj['frames'])
        unplace(fr)
        return fr

    def _settle(j, fr):
        """a lifted victim takes back every old frame that is still free; -> True when the chain is whole again"""
        plj = plans[j]
        wj, hj = fr[0][2], fr[0][3]
        keep_ = [f for f in fr if free((f[0], f[1], f[0] + wj + v.SHAVE, f[1] + hj + v.SHAVE))]
        for f in keep_:
            add_rect((f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE))
        plj['frames'] = keep_
        return len(keep_) == len(fr)

    work = [idx for idx, pl in sorted(plans.items()) if needs_repair(pl)]
    if _os.environ.get('OT_RELAY_TRACE'):
        import time as _time
        _t0 = _time.time()
        for idx in work:
            pl_ = plans[idx]
            print('P2', pl_['bid'], pl_['cl'], pl_['bits'], 'n', len(pl_['frames']), 'cc', round(max(hops_of(pl_))),
                  'p2p', round(max(p2p_hops(pl_))), 'back', backtracks(pl_),
                  'path', [(round(a_), round(b_)) for a_, b_ in (pl_.get('path') or [])], flush=True)
    if GATE:
        # r9: every chain that needs repair leaves the grid BEFORE the first search.  Their pass-1 frames are the heaps
        # at the edges of the blocks their plans crossed; left in place they took the sites the earlier repairs needed
        # (run b2: x3 'start 0', emb 'end free 0' beside the SU) and were gone by the end of the pass.
        for idx in work:
            unplace(plans[idx]['frames'])
            lifted0.add(idx)
    ripped = set()
    rounds = 0
    while work:
        idx = work.pop(0)
        pl = plans[idx]
        if not needs_repair(pl):
            continue
        _ok1 = repair(idx, pl)
        if _os.environ.get('OT_RELAY_TRACE'):
            print('P2R', pl['bid'], _ok1, 'n', len(pl['frames']), round(_time.time() - _t0), 's', unrep.get(pl['bid'], ''), flush=True)
        if _ok1 or not GATE:
            continue
        if repair(idx, pl, True):
            # r8: last tier before a rip-up: the row-gap sites (relay sites stay in the gaps / corridors; run a1:
            # tree_27_1_6b had no free corridor slot within reach of its source pin)
            gap_tier.append(pl['bid'])
            continue
        if idx in ripped or rounds >= 40:
            continue
        ripped.add(idx)
        rounds += 1
        bp = _bad_pts(pl)
        vict = [j for j in sorted(rep_at) if j != idx and plans[j]['frames'] and any(
            abs(f[0] + f[2] / 2 - q[0]) + abs(f[1] + f[3] / 2 - q[1]) <= RIP_UM for f in plans[j]['frames'] for q in bp)]
        if not vict:
            continue
        lifted = {j: _lift(j) for j in vict}
        ok_ = repair(idx, pl) or repair(idx, pl, True)
        redo = [j for j in vict if not _settle(j, lifted[j])]
        rip_log.append((pl['bid'], [plans[j]['bid'] for j in vict], bool(ok_), [plans[j]['bid'] for j in redo]))
        for j in redo:
            ripped.discard(j)
        work = redo + work
    if GATE:
        # r9: the chains still open are searched again once everything else stands (their sites may have been held by a
        # chain that has since moved); a chain that stays open keeps its pass-1 frames and is reported
        for _rnd in range(3):
            pend = [idx for idx, pl in sorted(plans.items()) if idx in lifted0 and pl['bid'] in unrep]
            got_ = [idx for idx in pend if repair(idx, plans[idx]) or repair(idx, plans[idx], True)]
            retry_log.append((len(pend), len(got_)))
            if not got_ or len(got_) == len(pend):
                break
    unrepaired[:] = [f'{b_} ({w_})' for b_, w_ in unrep.items()]
    # ---- r9 pin alignment of the relay hops: a frame of a too-near, offset pair slides to the nearest free spot where
    # every hop it touches is either in front of its peer or far enough to jog, within the reach
    jog_log = []
    if GATE:
        for idx, pl in sorted(plans.items()):
            if not pl['frames'] or pl['bid'] in unrep:
                continue
            for _it in range(6):
                bad = jog_bad(pl)
                if not bad:
                    break
                n_ = len(pl['frames'])
                fixed = False
                for hk in bad:
                    for fk in ([hk] if hk < n_ else []) + ([hk - 1] if hk >= 1 else []):
                        x0, y0, w_, h_ = pl['frames'][fk]
                        r0 = (x0, y0, x0 + w_ + v.SHAVE, y0 + h_ + v.SHAVE)
                        rm_rect(r0)
                        inc = corr_of(x0 + w_ / 2) is not None and in_field(x0 + w_ / 2, y0 + h_ / 2)
                        cands = []
                        for ix in ([0] if inc else range(-24, 25)):
                            for iy in range(-24, 25):
                                cands.append((abs(ix) + abs(iy), ix * 20 * v.GX, iy * 4 * v.GY))
                        if not inc:                  # r10: centre on an abutted block pin group (fine x / y steps first)
                            for ix in range(-30, 31):
                                for iy in range(-6, 7):
                                    cands.append((0.02 * (abs(ix) + abs(iy)), ix * 2 * v.GX, iy * v.GY))
                        got = None
                        for _, dx_, dy_ in sorted(cands):
                            if dx_ == 0 and dy_ == 0:
                                continue
                            x1, y1 = v.dn(x0 + dx_, v.GX), v.dn(y0 + dy_, v.GY)
                            if not inc and in_field(x1 + w_ / 2, y1 + h_ / 2) and corr_of(x1 + w_ / 2) is None and pl['cl'] != 'head_chain':
                                continue
                            if not free((x1, y1, x1 + w_ + v.SHAVE, y1 + h_ + v.SHAVE)):
                                continue
                            tr = dict(pl, frames=pl['frames'][:fk] + [(x1, y1, w_, h_)] + pl['frames'][fk + 1:])
                            if max(p2p_hops(tr)) > RELAY_REACH_OK or (max(hops_of(tr)) > RMAX + 25.0 and not P2P_REACH):
                                continue
                            nb = jog_bad(tr)
                            if len(nb) < len(bad) and not any(q_ in nb for q_ in (fk, fk + 1) if q_ not in bad):
                                got = (x1, y1)
                                break
                        if got is None:
                            add_rect(r0)
                            continue
                        pl['frames'][fk] = (got[0], got[1], w_, h_)
                        add_rect((got[0], got[1], got[0] + w_ + v.SHAVE, got[1] + h_ + v.SHAVE))
                        jog_log.append((pl['bid'], fk, round(got[0] - x0, 1), round(got[1] - y0, 1)))
                        fixed = True
                        break
                    if fixed:
                        break
                if not fixed:
                    jog_log.append((pl['bid'], 'open', bad))
                    break
    # ---- qwen-tp8 tree-leg pads (tools/qwen_die_seam/tree_pads.py: the array bench's arrival model on the unpadded
    # netlist): a tree word whose leg arrives early at its node gets `pad` extra relays at its sink end, in the
    # corridor the node tile's W-face tree pins face, so both legs of every node arrive on the same cycle
    targets = getattr(v, 'TREE_PAD_TARGETS', {}) or {}
    pad_trim = dict(trimmed=0, extended=0, over=[])
    extra = {}
    for idx, fr_ in pre_pads.items():
        _, cl, bits, eps = m['buses'][idx]
        bid_ = m['buses'][idx][0]
        nb_ = len(plans[idx]['frames']) if idx in plans else 0
        if bid_ in targets:
            # the bulk relays now end at the column's far end: keep exactly target - bulk pads (nearest the sink),
            # so the leg's register depth is the balanced one whatever the bulk planner did
            need = targets[bid_] - nb_
            if need < 0:
                pad_trim['over'].append(bid_)
                need = 0
            if need < len(fr_):
                pad_trim['trimmed'] += len(fr_) - need
                fr_ = fr_[len(fr_) - need:] if need else []
            elif need > len(fr_):
                pad_trim['extended'] += need - len(fr_)
                extra[bid_] = need - len(fr_)
        if idx not in plans:
            P0 = pos(*eps[0])
            plans[idx] = dict(bid=m['buses'][idx][0], cl=cl, bits=bits, eps=eps, P0=P0, P1=None, frames=[], d=0.0)
            keep.pop(idx, None)
        pl = plans[idx]
        pl['P1'] = pos(*eps[1])
        pl['frames'] = list(pl['frames']) + fr_
        pl['d'] = abs(pl['P0'][0] - pl['P1'][0]) + abs(pl['P0'][1] - pl['P1'][1])
    pre_ids = {m['buses'][i][0] for i in pre_pads}
    tpads = {b: n for b, n in tpads.items() if b not in pre_ids}
    tpads.update(extra)
    m['tp8_pad_trim'] = pad_trim

    def pad_spot(x, y, w, h, rings=200):
        # nearest free frame anywhere (corridor, row-gap channel, spine): free() rejects every instance rect
        for ring in range(rings):
            st = ring * 4 * v.GY
            cands = [(0, 0)] if ring == 0 else \
                [(dx, dy) for dx in (-st, st) for dy in [i * 4 * v.GY for i in range(-ring, ring + 1)]] + \
                [(dx, dy) for dy in (-st, st) for dx in [i * 4 * v.GY for i in range(-ring + 1, ring)]]
            for dx, dy in sorted(cands, key=lambda t_: abs(t_[0]) + abs(t_[1])):
                x0, y0 = v.dn(x - w / 2 + dx, v.GX), v.dn(y - h / 2 + dy, v.GY)
                if y0 >= g['y0'] and y0 + h <= die_top and free((x0, y0, x0 + w, y0 + h)):
                    return x0, y0
        return None
    # qwen split compute C5 (compute-die lead r2, die-bus audit 2026-10-14): the reference array is lockstep (one BD, one
    # NWS per tree level, one TWS); on the die every tile sees go after its own head + corridor stages and every leg has
    # its own relay count (C3: 503 / 720 nodes misaligned, max leg skew 106, block-word spread up to 220 at a slab vs its
    # 4-deep FIFO).  The node takes valid from leg a only, so skew = a wrong sum: pad the early leg of every node and every
    # block word to its slab's latest arrival, from THIS build's chains (tools/qwen_split/tree_skew.arrival_pads)
    if TP8 and TP8.get('split') == 'compute' and _os.environ.get('OT_TREE_PADS_INLINE', '1') != '0':
        sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
        import tree_skew as _TS
        S_, E_ = {}, {}
        for idx, (bid, cl, bits, eps) in buses:
            if bid.endswith('_rdy') or len(eps) != 2:
                continue
            S_[bid] = (len(plans[idx]['frames']) + 1) if idx in plans else 1
            E_[bid] = (eps[0][0], eps[-1][0])
        ipads, irep = _TS.arrival_pads(S_, E_)
        tpads.update(ipads)
        from qwen_split.direct_up4 import equal_age_pads
        tpads=equal_age_pads(S_,m.get('relay_equal_groups',{}),tpads)
        m['tp8_inline_pads'] = dict(irep, pads=len(tpads), pad_relays=sum(tpads.values()),
                                  equal_age_groups=len(m.get('relay_equal_groups',{})))
    # Reconcile the allocator's mutable occupancy with the exact frames that
    # will be emitted after repair/rip-up/jog/pre-pad trimming. Every inline
    # arrival pad must see ALL surviving frames, not a stale search grid.
    # An existing collision is a structural plan failure, never a legal site.
    grid.clear()
    for it in m['insts']:
        add_rect((it.x, it.y, it.x + it.w, it.y + it.h))
    for idx, pl in sorted(plans.items()):
        for fk, f in enumerate(pl['frames']):
            rr = (f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE)
            if not free(rr):
                raise ValueError(f"relay occupancy: {pl['bid']} frame {fk} overlaps a surviving frame before inline pads")
            add_rect(rr)
    pad_done = {}
    if tpads:
        bidx = {bid: idx for idx, (bid, cl, bits, eps) in buses}
        for bid, npad in sorted(tpads.items()):
            if bid not in bidx:
                raise ValueError(f'tree pads: no bus {bid}')
            idx = bidx[bid]
            if idx not in plans:
                _, cl, bits, eps = m['buses'][idx]
                P0, P1 = pos(*eps[0]), pos(*eps[1])
                plans[idx] = dict(bid=bid, cl=cl, bits=bits, eps=eps, P0=P0, P1=P1, frames=[],
                                  d=abs(P0[0] - P1[0]) + abs(P0[1] - P1[1]))
                keep.pop(idx, None)
            pl = plans[idx]
            w, h = relay_frame(pl['bits'], pl['cl'])
            x1, y1 = pl['P1']
            cc = corr_of(x1 - v.CORR / 2)
            got = []
            # the pads sit on the segment from the sink back to the bus's last relay (or its source): pad j at
            # (j + 1) / (npad + 1) of the way, each at the nearest free spot (every hop ~ segment / (npad + 1))
            fq = pl['frames'][-1] if pl['frames'] else None
            Q = (fq[0] + fq[2] / 2, fq[1] + fq[3] / 2) if fq else pl['P0']
            px, py = x1 - v.CORR / 2, y1
            leg_c = None
            for j in range(npad):
                # a walk from the sink toward Q: each pad nearest the point 1 / (pads left + 1) of the way from the
                # previous pad to Q (consecutive pads stay together; the walk ends next to Q)
                fr = 1.0 / (npad - j + 1)
                qx, qy = px + (Q[0] - px) * fr, py + (Q[1] - py) * fr
                sp = place(qx, qy, w + v.SHAVE, h + v.SHAVE, cc, 150.0) if cc is not None else None
                if sp is None and cc is None:
                    # contract v2: qfd_tile_nk's tree pins are area pins inside the body (x 10-223 um), so the sink
                    # is in no corridor: take the nearer of the two corridors flanking the walk point (y search
                    # +-400 um), never the row gap ~650 um away (it1: 1,226 hops over reach)
                    # one corridor per leg (v2g audit: alternating between the two flanking corridors zigzagged the
                    # chain, 68 hops of 700-830 um): the first pad picks it, the rest walk along it
                    best = None
                    for c_ in ([leg_c] if leg_c is not None else
                               sorted(range(COLS), key=lambda c: abs(cx_list[c] - qx))[:2]):
                        s_ = place(cx_list[c_], qy, w + v.SHAVE, h + v.SHAVE, c_, 400.0)
                        if s_ is not None:
                            d_ = abs(s_[0] + w / 2 - qx) + abs(s_[1] + h / 2 - qy)
                            if best is None or d_ < best[0]:
                                best = (d_, s_, c_)
                    sp = best[1] if best else None
                    if best:
                        leg_c = best[2]
                if sp is None:
                    sp = pad_spot(qx, qy, w + v.SHAVE, h + v.SHAVE)
                if sp is None:
                    raise ValueError(f'tree pads: no free spot for {bid} pad {j}')
                add_rect((sp[0], sp[1], sp[0] + w + v.SHAVE, sp[1] + h + v.SHAVE))
                got.append((sp[0], sp[1], w, h))
                px, py = sp[0] + w / 2, sp[1] + h / 2
            got.reverse()          # chain order: the last pad placed (farthest along the walk) first, the sink's last
            pl['frames'] = list(pl['frames']) + got
            pad_done[bid] = npad
    m['tp8_tree_pads'] = dict(buses=len(pad_done) + len(pre_pads), relays=sum(pad_done.values()) + sum(
        len(f) for f in pre_pads.values()), reserved_columns=len(pre_pads), walked=len(pad_done))
    # ---- emit relays and hops
    for idx, pl in sorted(plans.items()):
        bid, cl, bits, eps = pl['bid'], pl['cl'], pl['bits'], pl['eps']
        link = cl in ('link_spine', 'link_channel')
        dom = next((by[x].domain for x, _ in eps if by[x].domain != 'cdc'), 'stream_1p2')
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        prev, hops, rhops = eps[0], [], []
        for k, (x0, y0, w, h) in enumerate(pl['frames']):
            here = pts[k + 1]

            fi, fo, _fp = frame_faces(pts, k, (x0, y0, w, h), bits)       # the one face rule (pin_pts draws the same)
            pr_ = bid in pair
            mn = f'qfd_rly{"f" if link else ("p" if pr_ else "")}_{bits}_{fi}{fo}_{round(w)}x{round(h)}'
            masters_needed[mn] = (bits, fi, fo, w, h, link, pr_)
            nm = f'rly_{bid}_{k}'
            ccx, ccy = x0 + w / 2, y0 + h / 2
            reg = 'corridor' if corr_of(ccx) is not None and in_field(ccx, ccy) else next(
                (r_['kind'] for r_ in m['regions'] if r_['rect'][0] <= ccx <= r_['rect'][2]
                 and r_['rect'][1] <= ccy <= r_['rect'][3] and r_['kind'] != 'tile_field'), 'hub')
            insts.append(v.Inst(nm, mn, x0, y0, w, h, kind='relay', region=reg, domain=dom))
            by[nm] = insts[-1]
            hop = bid if k == 0 else f'{bid}__r{k}'
            hops.append((hop, cl, bits, [prev, (nm, 'a_d' if pr_ else 'a')]))
            if pr_:
                rhop = pair[bid] if k == 0 else f'{pair[bid]}__r{k}'
                rprev = (prev[0], prev[1][:-2] + '_r') if prev[1].endswith('_d') else (prev[0], prev[1] + '_r')
                rhops.append((rhop, cl, 1, [(nm, 'a_r'), rprev]))
            if link:
                fck_new.append((f'fck_{hop}', 'clock_trunk', 1, [(prev[0], f'fck_{prev[1]}'), (nm, 'fck_a')]))
            elif dom == 'stream_1p2':
                ck_add.setdefault(f'clk_r{region_of(ccx, ccy)}', []).append((nm, 'ck'))
            else:
                ck_add.setdefault({'serial_0p9': 'clk_serial', 'link_serdes': 'clk_serdes',
                                   'link_ucie': 'clk_ucie'}.get(dom, f'clk_{dom}'), []).append((nm, 'ck'))
            prev = (nm, 'b_d' if pr_ else 'b')
        n = len(pl['frames'])
        last = bid if not n else f'{bid}__r{n}'
        hops.append((last, cl, bits, [prev, eps[1]]))
        if bid in pair and n:
            e1 = eps[1]
            rhops.append((f'{pair[bid]}__r{n}', cl, 1, [(e1[0], e1[1][:-2] + '_r' if e1[1].endswith('_d') else e1[1] + '_r'),
                                                         (prev[0], 'b_r')]))
            keep[rev_idx[pair[bid]]] = rhops
        if link and n:
            fck_drop.add(f'fck_{bid}')
            fck_new.append((f'fck_{last}', 'clock_trunk', 1, [(prev[0], 'fck_b'), (eps[1][0], f'fck_{eps[1][1]}')]))
        keep[idx] = hops
        stage_of[bid] = n + 1
        s = stats.setdefault(cl, dict(buses=0, relays=0, relay_bits=0, max_hop_um=0.0, max_stages=0))
        s['buses'] += 1
        s['relays'] += n
        s['relay_bits'] += n * bits
        s['max_stages'] = max(s['max_stages'], n)
        s['max_hop_um'] = round(max(s['max_hop_um'], max(hops_of(pl))), 1)
        worst.append((bid, cl, round(pl['d'], 1), n))
    m['insts'] += insts
    B = [h for idx in range(len(m['buses'])) for h in keep[idx]]
    B = [b for b in B if b[0] not in fck_drop]
    for j, (bid, cl, bits, eps) in enumerate(B):
        if bid in ck_add:
            B[j] = (bid, cl, bits, eps + ck_add.pop(bid))
    # qwen-tp8/die it4 (relay ck audit, coordinator 10-12): a stream relay in a clock region that had no sink yet (the
    # KV-strip tail relays of the E KV-half words: 100 relays) named a clk_r<k> net that did not exist and was left with
    # its ck unconnected; such a region now gets its own net from the region-clock root (pll_r<k>, as _regions_from_placement)
    root_ = next((e[0] for b_ in B if re.fullmatch(r'clk_r\d+', b_[0]) for e in b_[3] if e[1].startswith('pll_r')), None)
    for key in [k_ for k_ in ck_add if re.fullmatch(r'clk_r\d+', k_)]:
        if root_ is not None:
            B.append((key, 'clock_trunk', 1, [(root_, 'pll_' + key[4:])] + ck_add.pop(key)))
    missing = sorted(ck_add)
    m['buses'] = B + fck_new
    m['r21_stage_of'] = stage_of
    # achieved hop lengths (pin-centre Manhattan, relay pins at the frame faces)
    m['r21_relays'] = dict(pitch_um=pitch, max_um=RMAX, relays=len(insts), masters=len(masters_needed),
                          classes=stats, clock_nets_missing=missing, repaired=len(repaired),
                          repaired_examples=repaired[:20], unrepaired=unrepaired, cut_over=cut_over,
                          repaired_all=[r[0] for r in repaired], off_plan=off_plan, feedback=feedback, rip_up=rip_log, gap_tier=gap_tier,
                          wall_avoid=wall_log, retry=retry_log, jog_fix=jog_log,
                          relay_flop_bits=sum(s['relay_bits'] for s in stats.values()),
                          relay_area_mm2=round(sum(i.w * i.h for i in insts) / 1e6, 3))
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        for mn, (bits, fi, fo, w, h, link, pr_) in masters_needed.items():
            M = v.Master(mn, w, h, 3, f'die relay: one registered {bits}-b hop (ot_qwen_die_station TAP=0 family), '
                         f'standard cells M1-M3, in {fi} out {fo}' + (' + the 1-b ready hop against the flow' if pr_ else ''))
            for port, f in (('a', fi), ('b', fo)):
                along = w if f in 'NS' else h
                pitch_tr = 2 if (bits + (2 if pr_ else 0)) * 0.096 + 2.0 <= along else 1
                if pr_:
                    st_ = 0.048 * pitch_tr
                    M.face(port + '_d', bits, f, 'M5' if f in 'NS' else 'M4', along / 2 - st_, pitch_tr)
                    M.face(port + '_r', 1, f, 'M5' if f in 'NS' else 'M4', along / 2 + (bits / 2 + 1) * st_, pitch_tr)
                    continue
                M.face(port, bits, f, 'M5' if f in 'NS' else 'M4', along / 2, pitch_tr)
            if link:
                M.area('fck_a', 1, w / 2 - 0.8, h / 2, 1)
                M.area('fck_b', 1, w / 2 + 0.8, h / 2, 1)
            else:
                M.area('ck', 1, w / 2, h / 2, 1)
            o[mn] = M
        return o
    v.masters = masters
    if GATE:
        # relay-data 2026-10-13: the release rule checked on the emitted die (the audit's measure: bounding box of the
        # net's pin centroids): no data net over RELAY_REACH_UM; a miss is an error, never a kept 'unrepaired' chain
        pos2 = _pin_pos(v, m)
        over, hmax = [], 0.0
        # pinreg-pairs 2026-10-13 (el1013-pinreg-audit.log): every hop is ALSO judged on its own pair of real views
        # (tools/hier_contract/pair_check.py Gate, table results/arch/pinreg_audit_1013/pairs/view_timing.json or
        # $OT_PAIR_TIMING): limit = min(RELAY_REACH_UM, (T - 60 - SKEW - o_src - s_dst) / 0.76); the flat RELAY_REACH_UM
        # stays the rule of every hop without a view on either end (the interim relay masters).  A pair bound only by
        # direction (die port names that are not the view's) is listed, not failed.  OT_QWEN_PAIR_GATE=0 = flat rule.
        pg_, pair_over = None, []
        import os as _os2
        if _os2.environ.get('OT_QWEN_PAIR_GATE', '1') != '0':
            sys.path.insert(0, str(ROOT / 'tools' / 'hier_contract'))
            try:
                import pair_check as _PC
            except ImportError:                      # a tree without main's tools/hier_contract/pair_check.py: flat rule
                _PC = None
            if _PC is not None:
                cn_ = {(e[0], e[1].lstrip('*')): re.sub(r'_r\d+$', '', b_) for b_, c_, n_, eps_ in m['buses'] if c_ == 'clock_trunk'
                       for e in eps_}
                pg_ = _PC.Gate(default_um=RELAY_REACH_UM, clock_net=cn_)
                by_ = {i.name: i for i in m['insts']}
        for bid, cl, bits, eps in m['buses']:
            if cl in RELAY_NEVER or len(eps) < 2:
                continue
            pts_ = [pos2(*e) for e in eps]
            L_ = max(q[0] for q in pts_) - min(q[0] for q in pts_) + max(q[1] for q in pts_) - min(q[1] for q in pts_)
            hmax = max(hmax, L_)
            if L_ > RELAY_REACH_UM:
                over.append((bid, cl, bits, round(L_, 1)))
            elif pg_ is not None and cl != 'constant':
                for e_, q_ in zip(eps[1:], pts_[1:]):
                    lim_ = pg_.limit(eps[0][0], getattr(by_[eps[0][0]], 'master', ''), eps[0][1].lstrip('*'),
                                     e_[0], getattr(by_[e_[0]], 'master', ''), e_[1].lstrip('*'))
                    Lp_ = abs(pts_[0][0] - q_[0]) + abs(pts_[0][1] - q_[1])
                    if Lp_ > lim_:
                        pair_over.append((bid, cl, bits, round(Lp_, 1), lim_))
        if pair_over:
            over += [t_[:4] for t_ in pair_over if t_[:4] not in over]
        m['r21_relays'].update(reach_um=RELAY_REACH_UM, max_pin_to_pin_um=round(hmax, 1), over_reach=sorted(over, key=lambda t: -t[3]))
        if pg_ is not None:
            m['r21_relays']['pair_check'] = dict(
                table_masters=len(pg_.t), hops=dict(pg_.used), over_pair_limit=sorted(pair_over, key=lambda t: t[4] - t[3])[:200],
                hold_fail=[list(k_) + [h_] for k_, h_ in sorted(pg_.hold.items(), key=lambda kv: kv[1])],
                tightest=sorted((l_, k_[0] + '.' + k_[1], k_[2] + '.' + k_[3]) for k_, l_ in pg_.pairs.items() if l_ < RELAY_REACH_UM)[:60],
                candidates_bound_by_direction=sorted((l_, k_[0] + '.' + k_[1], k_[2] + '.' + k_[3]) for k_, l_ in pg_.candidates.items())[:60])
        if _os.environ.get('OT_RELAY_DUMP'):
            import json as _json
            _rep = {r[0]: r for r in repaired}
            _json.dump(dict(rmax=RMAX, pitch=pitch, reach_um=RELAY_REACH_UM, unrepaired=unrepaired, off_plan=off_plan, cut_over=cut_over,
                            feedback=feedback, tight_stride=sorted(tight_stride), over_reach=m['r21_relays']['over_reach'],
                            max_pin_to_pin_um=round(hmax, 1), clock_nets_missing=missing, classes=stats,
                            tp8b_kv=dict(torn_chains=m.get('tp8b_kv', {}).get('torn_chains'),
                                         kept_relays=m.get('tp8b_kv', {}).get('kept_relays')),
                            plans=[dict(bid=p_['bid'], cl=p_['cl'], bits=p_['bits'], eps=p_['eps'], P0=p_['P0'], P1=p_['P1'],
                                        n=len(p_['frames']), repaired=_rep.get(p_['bid']),
                                        cc=round(max(hops_of(p_)), 1), p2p=round(max(p2p_hops(p_)), 1))
                                   for _, p_ in sorted(plans.items())]),
                       open(_os.environ['OT_RELAY_DUMP'], 'w'))
        if over and _os.environ.get('OT_RELAY_GATE') != 'warn':
            raise ValueError(f'relays: {len(over)} data nets over {RELAY_REACH_UM:.0f} um pin to pin, worst {over[:8]}; '
                             f'unrepaired {unrepaired[:8]}')
    return m['r21_relays']


# ------------------------------------------------------------------------------------------------ registered reset tree
# owner 2026-10-13 (die timing by construction): a reset is an inter-tile signal like any other: register at the pin ->
# wire <= 500 um -> register at the pin.  A reset net whose pin bounding box (half perimeter, the pinreg audit's measure)
# exceeds RELAY_REACH_UM is replaced by a registered tree of 1-bit repeaters, clocked by the domain of its sinks.
RST_REP = 'qfd_rst_rep'          # ot_qwen_rst_rep PAD=0: 1 input flop + 2 registered outputs (q0, q1) = 2 cycles
RST_PAD = 'qfd_rst_rep_p8'       # ot_qwen_rst_rep PAD=8: 8 pad flops between the input and the output rank = 10 cycles
RST_PAD_LV = 5                   # one pad cell = 5 repeater levels (10 cycles)
RST_W, RST_H = 5.184, 2.16       # 12 GX x 1 GY (<= 5.4 x 2.16: 96 sites x 8 rows), M1-M3
RST_PITCH_UM = 220.0             # trunk lattice
RST_LEAF_UM = 200.0              # sinks of one lattice cell share a leaf repeater
RST_NET_UM = 450.0               # build limit per net (cell centres); the emitted pins are re-checked at RST_OK_UM
RST_OK_UM = 480.0
RST_GAP_UM = 2.16                # clearance to every other instance


def _hp(pts):
    return max(p[0] for p in pts) - min(p[0] for p in pts) + max(p[1] for p in pts) - min(p[1] for p in pts)


class _RstOcc:
    """occupancy of the placement (the `free` / `add_rect` grid of _relays) + nearest legal site search."""
    BK = 250.0

    def __init__(self, rects, W, H, gx, gy):
        self.g, self.W, self.H, self.gx, self.gy = {}, W, H, gx, gy
        for r in rects:
            self.add(r)

    def _cells(self, r, gap=0.0):
        BK = self.BK
        return [(i, j) for i in range(int((r[0] - gap) // BK), int((r[2] + gap) // BK) + 1)
                for j in range(int((r[1] - gap) // BK), int((r[3] + gap) // BK) + 1)]

    def add(self, r):
        for c in self._cells(r):
            self.g.setdefault(c, []).append(r)

    def remove(self, r):
        for c in self._cells(r):
            self.g[c].remove(r)

    def hit(self, r, gap):
        for c in self._cells(r, gap):
            for q in self.g.get(c, ()):
                if q[0] < r[2] + gap - 1e-6 and r[0] < q[2] + gap - 1e-6 and q[1] < r[3] + gap - 1e-6 and r[1] < q[3] + gap - 1e-6:
                    return q
        return None

    def free(self, r, gap):
        return r[0] >= gap and r[1] >= gap and r[2] <= self.W - gap and r[3] <= self.H - gap and self.hit(r, gap) is None

    def site(self, tx, ty, box=None, lim=600.0, w=RST_W, h=RST_H, gap=RST_GAP_UM):
        """lower-left corner (on the GX / GY lattice) of a free w x h frame near the centre (tx, ty); `box` =
        (x0, y0, x1, y1) limits the frame centre.  Best-first over edge projections: a blocked candidate is pushed
        past each edge of the block that stops it (so a target inside a block, or between abutting blocks, walks out
        to the nearest channel); the nearest free candidate within `lim` um (Manhattan, from the target) wins."""
        import heapq
        gx, gy = self.gx, self.gy
        heap, seen, best, pops = [(0.0, tx, ty)], set(), None, 0
        while heap and pops < 4000:
            d, cx, cy = heapq.heappop(heap)
            pops += 1
            if d > lim or (best is not None and d >= best[0]):
                break
            cx = min(max(cx, gap + w / 2 + gx), self.W - gap - w / 2 - gx)      # a point off the die: its nearest die point
            cy = min(max(cy, gap + h / 2 + gy), self.H - gap - h / 2 - gy)
            x0 = round(math.floor((cx - w / 2) / gx + 1e-9) * gx, 6)
            y0 = round(math.floor((cy - h / 2) / gy + 1e-9) * gy, 6)
            r = (x0, y0, x0 + w, y0 + h)
            if r[0] < gap or r[1] < gap or r[2] > self.W - gap or r[3] > self.H - gap:
                continue
            if box and not (box[0] <= x0 + w / 2 <= box[2] and box[1] <= y0 + h / 2 <= box[3]):
                continue
            q = self.hit(r, gap)
            if q is None:
                dd = abs(x0 + w / 2 - tx) + abs(y0 + h / 2 - ty)
                if best is None or dd < best[0]:
                    best = (dd, x0, y0)
                continue
            for nx, ny in ((q[0] - gap - w / 2 - gx, cy), (q[2] + gap + w / 2 + gx, cy),
                           (cx, q[1] - gap - h / 2 - gy), (cx, q[3] + gap + h / 2 + gy)):
                key = (round(nx, 1), round(ny, 1))
                if key not in seen:
                    seen.add(key)
                    heapq.heappush(heap, (abs(nx - tx) + abs(ny - ty), nx, ny))
        return None if best is None else (best[1], best[2])


def _rst_tree_build(nets, rects, W, H, gx, gy, pitch=RST_PITCH_UM):
    """nets: [dict(bid, dom, drv=(inst, port, (x, y)), sinks=[(inst, port, (x, y))])].  Returns (cells, wires, stats,
    errors): cells [(name, master, x, y, bid)], wires [(net, bid, [(inst, port)])] (driver first).  Pure geometry: the
    caller supplies pin positions and the placement rectangles, and re-checks the emitted pins."""
    import collections
    occ = _RstOcc(rects, W, H, gx, gy)
    P = pitch
    cells, wires, errors, per = [], [], [], {}
    trees = []
    for net in nets:
        bid = net['bid']
        N = {}                                  # node id -> dict(x, y (frame corner), kids, sinks)
        seq = [0]

        def new(tx, ty, box=None, _N=N, _seq=seq, _bid=bid):
            s = occ.site(tx, ty, box)
            if s is None:
                return None
            occ.add((s[0], s[1], s[0] + RST_W, s[1] + RST_H))
            k = _seq[0]
            _seq[0] += 1
            _N[k] = dict(x=s[0], y=s[1], kids=[], sinks=[], pad=0, master=RST_REP,
                         mv=abs(s[0] + RST_W / 2 - tx) + abs(s[1] + RST_H / 2 - ty))
            return k

        def c_(k, _N=N):
            return (_N[k]['x'] + RST_W / 2, _N[k]['y'] + RST_H / 2)
        # 1. leaf repeaters: the sinks of one RST_LEAF_UM cell, the repeater at the free site nearest their centroid;
        #    a group that does not fit one net is split per sink (repeater nearest each pin)
        grp = collections.defaultdict(list)
        for s in net['sinks']:
            grp[(int(s[2][0] // RST_LEAF_UM), int(s[2][1] // RST_LEAF_UM))].append(s)
        leaves = []
        work = [grp[k] for k in sorted(grp)]
        while work:
            ss = work.pop(0)
            tx = sum(s[2][0] for s in ss) / len(ss)
            ty = sum(s[2][1] for s in ss) / len(ss)
            k = new(tx, ty)
            if k is not None and _hp([c_(k)] + [s[2] for s in ss]) <= RST_NET_UM:
                N[k]['sinks'] = ss
                leaves.append(k)
                continue
            if k is not None:
                occ.remove((N[k]['x'], N[k]['y'], N[k]['x'] + RST_W, N[k]['y'] + RST_H))
                del N[k]
            if len(ss) == 1:
                errors.append(dict(net=bid, kind='sink_unreachable', pin=f'{ss[0][0]}.{ss[0][1]}', at=[round(q, 1) for q in ss[0][2]]))
            else:
                work = [[s] for s in ss] + work
        # 2. root repeater at the driver pin
        d = net['drv']
        root = new(d[2][0], d[2][1])
        if root is None or _hp([c_(root), d[2]]) > RST_NET_UM:
            errors.append(dict(net=bid, kind='driver_unreachable', pin=f'{d[0]}.{d[1]}', at=[round(q, 1) for q in d[2]]))
            continue
        # 3. trunk: lattice cells with a free site within pitch / 4 of the centre (else anywhere in the cell); BFS tree
        #    from the root's cell over neighbour cells whose sites are within one net of each other
        tent = {}

        def usable(c):
            if c not in tent:
                cx, cy = (c[0] + 0.5) * P, (c[1] + 0.5) * P
                if not (0 <= cx - P / 2 < W and 0 <= cy - P / 2 < H):     # the cell overlaps the die
                    tent[c] = None
                else:
                    tent[c] = occ.site(cx, cy, box=(cx - P / 4, cy - P / 4, cx + P / 4, cy + P / 4), lim=P) or \
                        occ.site(cx, cy, box=(cx - P / 2, cy - P / 2, cx + P / 2, cy + P / 2), lim=2 * P)
            return tent[c]

        def attach(k):
            """the usable trunk cell nearest node k."""
            x, y = c_(k)
            c0 = (int(x // P), int(y // P))
            best = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = (c0[0] + dx, c0[1] + dy)
                    s = usable(c)
                    if s is not None:
                        dd = abs(s[0] + RST_W / 2 - x) + abs(s[1] + RST_H / 2 - y)
                        if dd <= RST_NET_UM - 60 and (best is None or dd < best[0]):
                            best = (dd, c)
            if best is not None:
                return best[1]
            # no usable cell beside k (a pin at the die edge, a strip between abutting blocks): the nearest usable cell
            # within 5 cells, bridged by repeaters on the straight line to it, each hop within one net
            far = None
            for dx in range(-5, 6):
                for dy in range(-5, 6):
                    c = (c0[0] + dx, c0[1] + dy)
                    s = usable(c)
                    if s is not None:
                        dd = abs(s[0] + RST_W / 2 - x) + abs(s[1] + RST_H / 2 - y)
                        if far is None or dd < far[0]:
                            far = (dd, c, s)
            if far is None:
                return None
            ex, ey = far[2][0] + RST_W / 2, far[2][1] + RST_H / 2
            n = int(far[0] // 330.0) + 1                  # hops from the cell to k
            head, pt = k, (x, y)
            for j in range(1, n):                         # bridge points from k towards the cell
                bx_, by_ = x + (ex - x) * j / n, y + (ey - y) * j / n
                b_ = new(bx_, by_, None)
                if b_ is None or _hp([c_(b_), pt]) > RST_NET_UM - 30:
                    return None
                N[b_]['kids'] = [head]
                bridged[head] = b_
                head, pt = b_, c_(b_)
            if _hp([pt, (ex, ey)]) > RST_NET_UM - 30:
                return None
            return far[1]
        bridged = {}
        rc = attach(root)
        want = {}
        for k in leaves:
            c = attach(k)
            if c is None:
                errors.append(dict(net=bid, kind='leaf_no_trunk_cell', at=[round(q, 1) for q in c_(k)]))
            else:
                h_ = k
                while h_ in bridged:
                    h_ = bridged[h_]
                want.setdefault(c, []).append(h_)
        if rc is None:
            errors.append(dict(net=bid, kind='root_no_trunk_cell', at=[round(q, 1) for q in c_(root)]))
            continue
        par, todo, left = {rc: None}, collections.deque([rc]), set(want) - {rc}
        bx = [min(c[0] for c in list(want) + [rc]) - 3, min(c[1] for c in list(want) + [rc]) - 3,
              max(c[0] for c in list(want) + [rc]) + 3, max(c[1] for c in list(want) + [rc]) + 3]
        while todo and left:
            c = todo.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (c[0] + dx, c[1] + dy)
                if n not in par and bx[0] <= n[0] <= bx[2] and bx[1] <= n[1] <= bx[3] and usable(n) is not None and \
                        abs(tent[n][0] - tent[c][0]) + abs(tent[n][1] - tent[c][1]) <= RST_NET_UM - 30:
                    par[n] = c
                    left.discard(n)
                    todo.append(n)
        for c in sorted(left):
            errors.append(dict(net=bid, kind='trunk_unreachable', cell=list(c), leaves=len(want[c])))
        on = set()
        for c in want:
            while c is not None and c in par and c not in on:
                on.add(c)
                c = par[c]
        on.add(rc)
        node = {}
        for c in sorted(on, key=lambda c: (abs(c[0] - rc[0]) + abs(c[1] - rc[1]), c)):
            cx, cy = (c[0] + 0.5) * P, (c[1] + 0.5) * P
            node[c] = new(tent[c][0] + RST_W / 2, tent[c][1] + RST_H / 2, box=(cx - P / 2, cy - P / 2, cx + P / 2, cy + P / 2))
            assert node[c] is not None, (bid, c)
        if root in bridged:
            raise ValueError(f'reset tree: {bid} root repeater has no trunk cell beside it')
        N[root]['kids'] = [node[rc]]
        for c in on:
            if par[c] is not None:
                N[node[par[c]]]['kids'].append(node[c])
            N[node[c]]['kids'] += want.get(c, [])
        # 4. collinear pass-through nodes dropped while the hop still fits one net
        todo = [root]
        while todo:
            p = todo.pop()
            while len(N[p]['kids']) == 1:
                k = N[p]['kids'][0]
                if N[k]['sinks'] or len(N[k]['kids']) != 1 or _hp([c_(p), c_(N[k]['kids'][0])]) > RST_NET_UM - 20:
                    break
                N[p]['kids'] = N[k]['kids']
                occ.remove((N[k]['x'], N[k]['y'], N[k]['x'] + RST_W, N[k]['y'] + RST_H))
                del N[k]
            todo += N[p]['kids']
        # 5. outputs: the kids of a node in <= 2 nets (first fit); more nets -> an auxiliary repeater beside the node
        #    takes the shallower groups.  Heights (repeater levels below a node) bottom-up.
        order, todo = [], [root]
        while todo:
            p = todo.pop()
            order.append(p)
            todo += N[p]['kids']
        ht = {}
        for p in reversed(order):
            if N[p]['sinks']:
                N[p]['outs'] = [[('sink', s) for s in N[p]['sinks']]]
                ht[p] = 0
                continue
            if not N[p]['kids']:
                # split compute C7: a trunk node left with neither sinks nor kids (its leaves were bridged to a
                # neighbour cell) drives nothing: record it, no repeater level
                N[p]['outs'] = []
                ht[p] = 0
                errors.append(dict(net=bid, kind='empty_node', at=[round(q, 1) for q in c_(p)]))
                continue
            groups = []
            for k in sorted(N[p]['kids'], key=lambda k: -ht[k]):
                for g_ in groups:
                    if _hp([c_(p)] + [c_(o) for o in g_] + [c_(k)]) <= RST_NET_UM:
                        g_.append(k)
                        break
                else:
                    if _hp([c_(p), c_(k)]) > RST_NET_UM:
                        errors.append(dict(net=bid, kind='hop_over', um=round(_hp([c_(p), c_(k)]), 1), at=[round(q, 1) for q in c_(k)]))
                    groups.append([k])
            groups.sort(key=lambda g_: -max(ht[k] for k in g_))
            cur = p
            while len(groups) > 2:
                a = new(*c_(cur))
                assert a is not None, (bid, 'aux')
                N[cur]['outs'] = [[('node', k) for k in groups[0]], [('node', a)]]
                N[cur]['kids'] = groups[0] + [a]
                groups = groups[1:]
                cur = a
            N[cur]['outs'] = [[('node', k) for k in g_] for g_ in groups]
            N[cur]['kids'] = [k for g_ in groups for k in g_]
            q = cur                                # heights of the auxiliary chain, then the node
            while True:
                ht[q] = 1 + max(ht[k] for k in N[q]['kids'])
                if q == p:
                    break
                q = next(o for o in N if q in N[o]['kids'])
        trees.append(dict(net=net, N=N, root=root, ht=ht, new=new, c_=c_))
    # 6. equal depth: every leaf of a domain at the domain's maximum.  The slack of an edge (parent height - 1 - child
    #    height) is padded ON THAT EDGE, as near the root as the tree allows (shared by the whole subtree), by a pad
    #    chain beside the child: RST_PAD cells (5 levels each) + plain repeaters.
    hdom = {}
    for t in trees:
        hdom[t['net']['dom']] = max(hdom.get(t['net']['dom'], 0), t['ht'][t['root']])
    for t in trees:
        net, N, root, ht, new, c_ = t['net'], t['N'], t['root'], t['ht'], t['new'], t['c_']
        bid = net['bid']
        pads = [0, 0]

        def chain(k, lv):
            """pad chain of lv levels in front of node k; returns the node that takes k's place in its parent's net."""
            head, prev = None, None
            for mst in [RST_PAD] * (lv // RST_PAD_LV) + [RST_REP] * (lv % RST_PAD_LV):
                a = new(*c_(k))
                assert a is not None, (bid, 'pad')
                N[a]['master'] = mst
                pads[mst == RST_PAD] += 1
                if prev is None:
                    head = a
                else:
                    N[prev]['outs'] = [[('node', a)]]
                prev = a
            if prev is not None:
                N[prev]['outs'] = [[('node', k)]]
            return head if head is not None else k
        first = chain(root, hdom[net['dom']] - ht[root])
        for p in [k for k in N if k in ht and not N[k]['sinks']]:
            N[p]['outs'] = [[(kind, chain(o, ht[p] - 1 - ht[o])) if kind == 'node' else (kind, o) for kind, o in g_]
                            for g_ in N[p]['outs']]
        # 7. emit; depth of every sink in cycles (2 per repeater, 10 per pad cell)
        name = {k: f'rstt_{bid}_{k}' for k in N}
        wires.append((bid, bid, [(net['drv'][0], net['drv'][1]), (name[first], 'd')]))
        dep, todo, nn, mx = set(), [(first, 0)], 0, _hp([net['drv'][2], c_(first)])
        while todo:
            k, cyc = todo.pop()
            cyc += 10 if N[k]['master'] == RST_PAD else 2
            for j, g_ in enumerate(N[k]['outs']):
                nn += 1
                eps, pts = [(name[k], f'q{j}')], [c_(k)]
                for kind, o in g_:
                    if kind == 'sink':
                        eps.append((o[0], o[1]))
                        pts.append(o[2])
                        dep.add(cyc)
                    else:
                        eps.append((name[o], 'd'))
                        pts.append(c_(o))
                        todo.append((o, cyc))
                mx = max(mx, _hp(pts))
                wires.append((f'{bid}__t{nn}', bid, eps))
        for k in sorted(N):
            cells.append((name[k], N[k]['master'], N[k]['x'], N[k]['y'], bid, round(N[k]['mv'], 2)))
        per[bid] = dict(dom=net['dom'], sinks=len(net['sinks']), repeaters=len(N) - pads[0] - pads[1], pad_rep=pads[0],
                        pad_p8=pads[1], nets=nn + 1, max_net_um=round(mx, 1), levels=ht[root] + 1,
                        depth_cycles=sorted(dep))
    return cells, wires, per, errors


def _reset_tree(v, m):
    """tp8 reset tree (owner 2026-10-13 release gate; plan results/arch/qwen_tp8_1013/reset_tree_plan.json): every bus of
    class 'reset' longer than RELAY_REACH_UM pin to pin (bounding box of the pin centroids, as pinreg_audit.py) becomes a
    registered tree of 1-bit repeaters (RST_REP: clk + d on W, q0 on E, q1 on N; 1 input flop + 2 registered outputs,
    2 cycles), every site LEGALISED on the GX / GY lattice against the final placement (after the relays) with RST_GAP_UM
    clearance, every net (one driver + its sinks) <= RST_OK_UM.  Each tree is clocked by the clock net of its sinks
    (clk_core_<q>, clk_hbm_<q>, the KV core clock): assertion and release are synchronous to the leaf domain.  EQUAL
    DEPTH per domain (bus name less the quadrant suffix): the slack of every tree edge is padded by a pad chain beside
    the child (RST_PAD cells of 10 cycles + plain repeaters), so every sink of a domain leaves reset in the same cycle.
    Power-on only: 0 cycles per token.  Raises on any reset net left over the reach."""
    if _os_r.environ.get('OT_RELAY_SKIP') == '1':
        return
    import os as _os
    by = {i.name: i for i in m['insts']}
    pos = _pin_pos(v, m)
    ckof = {}
    for bid, cl, bits, eps in m['buses']:
        if cl == 'clock_trunk':
            for i, p in eps:
                ckof.setdefault(i, []).append((bid, p))
    nets, ck_of_bus, idx_of = [], {}, {}
    for idx, (bid, cl, bits, eps) in enumerate(m['buses']):
        if cl != 'reset' or len(eps) < 2:
            continue
        pts = [pos(*e) for e in eps]
        if _hp(pts) <= RELAY_REACH_UM:
            continue
        if bits != 1:
            raise ValueError(f'reset tree: {bid} is {bits} b')
        d = next((j for j, e in enumerate(eps) if re.match(r'rso|hrst$|crst$', e[1].lstrip('*'))), 0)
        sinks = [(e[0], e[1], pts[j]) for j, e in enumerate(eps) if j != d]
        # the clock of the sinks: the clock net on the sink instance (a CDC leaf has two: h_* pins ride hclk)
        vote = {}
        for i, p, _ in sinks:
            c = ckof.get(i, [])
            if len(c) > 1:
                hb = p.lstrip('*').startswith('h')
                c = [q for q in c if q[1].lstrip('*').startswith('h') == hb] or c
            if c:
                vote[c[0][0]] = vote.get(c[0][0], 0) + 1
        if not vote:
            raise ValueError(f'reset tree: {bid} sinks carry no clock net')
        ck_of_bus[bid] = max(sorted(vote), key=lambda k: vote[k])
        idx_of[bid] = idx
        nets.append(dict(bid=bid, dom=re.sub(r'_(?:[WE][SN]|c)$', '', bid), drv=(eps[d][0], eps[d][1], pts[d]), sinks=sinks,
                         domain=by[sinks[0][0]].domain))
    rec = dict(reach_um=RELAY_REACH_UM, long_reset_nets=len(nets), repeaters=0, pad_cells=0, nets=0, max_net_um=0.0)
    m['tp8_reset_tree'] = rec
    if not nets:
        return rec
    rects = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]
    if _os.environ.get('OT_RESET_DUMP'):
        import json as _json
        _json.dump(dict(nets=nets, rects=rects, W=m['die']['w'], H=m['die']['h'], gx=v.GX, gy=v.GY), open(_os.environ['OT_RESET_DUMP'], 'w'))
    cells, wires, per, errors = _rst_tree_build(nets, rects, m['die']['w'], m['die']['h'], v.GX, v.GY)
    if errors:
        rec.update(errors=errors, per_net=per)
        if _os.environ.get('OT_RESET_GATE') == 'warn':     # diagnosis only: the long nets are left in place and reported
            return rec
        raise ValueError(f'reset tree: {len(errors)} unbuildable: {errors[:8]}')
    dom_inst = {n['bid']: n['domain'] for n in nets}
    ck_add = {}
    for nm, mst, x, y, bid, _ in cells:
        m['insts'].append(v.Inst(nm, mst, x, y, RST_W, RST_H, kind='reset_rep', region='reset_tree', domain=dom_inst[bid]))
        ck_add.setdefault(ck_of_bus[bid], []).append((nm, 'clk'))
    drop = set(idx_of.values())
    B = [b for j, b in enumerate(m['buses']) if j not in drop]
    B = [(bid, cl, bits, eps + ck_add.pop(bid)) if bid in ck_add else (bid, cl, bits, eps) for bid, cl, bits, eps in B]
    assert not ck_add, sorted(ck_add)
    m['buses'] = B + [(nm, 'reset', 1, eps) for nm, _, eps in wires]
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        for mn, pad in ((RST_REP, 0), (RST_PAD, 8)):
            M = v.Master(mn, RST_W, RST_H, 3, f'reset tree repeater (ot_qwen_rst_rep PAD={pad}): 1 input flop + {pad} pad '
                         f'flops + 2 registered outputs, standard cells M1-M3, clk + d on W, q0 on E, q1 on N')
            M.face('clk', 1, 'W', 'M4', RST_H * 0.3)
            M.face('d', 1, 'W', 'M4', RST_H * 0.7)
            M.face('q0', 1, 'E', 'M4', RST_H / 2)
            M.face('q1', 1, 'N', 'M5', RST_W / 2)
            o[mn] = M
        return o
    v.masters = masters
    # the release rule on the emitted pins (the audit's measure), every reset-class net of the die
    pos = _pin_pos(v, m)
    over, mx = [], 0.0
    for bid, cl, bits, eps in m['buses']:
        if cl != 'reset' or len(eps) < 2:
            continue
        L_ = _hp([pos(*e) for e in eps])
        if bid in per or '__t' in bid:
            mx = max(mx, L_)
        if L_ > (RST_OK_UM if '__t' in bid else RELAY_REACH_UM):
            over.append((bid, round(L_, 1)))
    deps = {}
    for bid, r in per.items():
        deps.setdefault(r['dom'], set()).update(r['depth_cycles'])
    # legalisation: distance (Manhattan, um) from each requested point (lattice cell centre for a trunk node, sink
    # centroid for a leaf, the node it pads / fans out for a pad or auxiliary cell) to the legal site taken
    moved = sorted(c[5] for c in cells)
    rec.update(repeaters=sum(r['repeaters'] for r in per.values()), pad_rep=sum(r['pad_rep'] for r in per.values()),
               pad_p8=sum(r['pad_p8'] for r in per.values()), cells=len(cells), nets=len(wires), max_net_um=round(mx, 1),
               depth_cycles={d_: sorted(s) for d_, s in deps.items()}, max_depth_cycles=max(max(s) for s in deps.values()),
               pads='pad chains beside the child of each slack edge: qfd_rst_rep_p8 (10 cycles) + qfd_rst_rep (2 cycles)',
               masters=[RST_REP, RST_PAD], frame_um=[RST_W, RST_H], gap_um=RST_GAP_UM, lattice_um=RST_PITCH_UM,
               clock_of={b_: ck_of_bus[b_] for b_ in sorted(ck_of_bus)}, per_net=per, over=over,
               legalised=dict(sites=len(moved), moved_over_1um=sum(1 for q in moved if q > 1.0), median_um=moved[len(moved) // 2],
                              p90_um=moved[len(moved) * 9 // 10], max_um=moved[-1]),
               cycles_per_token=0)
    if any(len(s) != 1 for s in deps.values()):
        raise ValueError(f'reset tree: unequal leaf depth {rec["depth_cycles"]}')
    if over and _os.environ.get('OT_RESET_GATE') != 'warn':
        raise ValueError(f'reset tree: {len(over)} reset nets over the reach: {over[:8]}')
    return rec


def _pin_pos(v, m):
    """(inst, port) -> die position of the port's pin centroid (instance orientation applied)."""
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    cen, ext = {}, {}
    for name, mst in M.items():
        acc = {}
        for nm, layer, r in v.pin_rects(mst, 1, {q: pw.get((name, q), 0) for q in mst.order}):
            a = acc.setdefault(nm.split('[')[0], [0.0, 0.0, 0, 1e18, -1e18, 1e18, -1e18])
            cx_, cy_ = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
            a[0] += cx_
            a[1] += cy_
            a[2] += 1
            a[3], a[4], a[5], a[6] = min(a[3], cx_), max(a[4], cx_), min(a[5], cy_), max(a[6], cy_)
        cen[name] = {p: (a[0] / a[2], a[1] / a[2]) for p, a in acc.items()}
        ext[name] = {p: ((a[4] - a[3]) / 2, (a[6] - a[5]) / 2) for p, a in acc.items()}
    by = {i.name: i for i in m['insts']}

    extra = getattr(v, 'PIN_POS_EXTRA', None) or {}

    def pos(inst, port):
        if (inst, port) in extra:
            return extra[(inst, port)]
        i = by[inst]
        c = cen.get(i.master, {}).get(port.lstrip('*'))
        if c is None:
            return (i.cx, i.cy)
        x, y = c
        if i.orient in ('MY', 'R180'):
            x = i.w - x
        if i.orient in ('MX', 'R180'):
            y = i.h - y
        return (i.x + x, i.y + y)

    def pin_ext(inst, port):
        """r10: half extents (x, y) of the port's pin group (a relay in front of it must leave the difference room)"""
        return ext.get(by[inst].master, {}).get(port.lstrip('*'), (0.0, 0.0))
    pos.ext = pin_ext
    return pos


# ------------------------------------------------------------------------------------------------ r18 (die-top lint)
XF_GAP = 30.0       # um between the channel CDC cluster and the spine columns (their channel-face pins stay open)


def _r18_post(v, m):
    """Die-top lint Q1-Q14 (results/rtl/die_top_lint_20261006/qwen_rom_findings.json, main 694e21a6e):
      Q7  no row engines / near-HBM combine (built in _build with R18); the hub keeps the link endpoints and the root
      Q5  every serial <-> stream <-> link crossing goes through a CDC cluster: sp_xfifo (decision C X1/X2/X3 ratio
          FIFOs, in the spine channel between SU64 / VM and the sequencer) or io_xfifo (beside the collective);
          the KV-new write rides the STREAM4 CDC write queues (no kvn bus)
      Q9  token id -> embedding ROM address (emb_a, from the core in the sequencer slab)
      Q10 tree-top result word -> vector memory (tt_res, through sp_xfifo)
      Q11 UCIe / SerDes receive words (ucie_rx / serdes_rx)
      Q1-Q4 clock nets: one stream net per decision-C region from the hub root, the serial net, the two link-PHY
          clocks, one HBM clock per stack from its controller's PLL entry (PHY clk and every CDC hclk), resets of
          the CDC / PHY, forwarded clocks along the link stations (Q6); the field clock leaves the corridor words
      Q8  role variants of the station / head / channel-waypoint masters
      Q14 no abstract port without a die net (dropped in the masters wrapper)"""
    g = m['geo']
    by = {i.name: i for i in m['insts']}
    for it in m['insts']:
        if it.kind == 'cdc':
            it.domain = 'cdc'
    # ---- Q4: the field clock / reset bits leave the corridor / tap / head-chain words
    B = []
    for bid, cl, bits, eps in m['buses']:
        if cl in ('corridor', 'head_chain'):
            bits -= 65                 # 64 forwarded clock tracks + 1 reset
        elif cl == 'tap':
            bits -= 2                  # clock + reset
        if cl == 'clock_trunk':
            continue                   # replaced below
        B.append((bid, cl, bits, eps))
    m['buses'] = B
    # ---- the serial blocks host the decision-C X1/X2/X3 ratio FIFOs at their stream-side ports (r18f: a separate
    # channel cluster sp_xfifo concentrated 18.5k crossing pins in the channel beside the hub, i5 overflow 16,408
    # with M8/M9 1.22-1.27 there); SU64 and VM get the stream clock beside their serial one
    hosts = {'sp_su64_sfu', 'sp_vector_memory'}
    hub = m['hub']
    lv = sorted(i.y + i.h for i in m['insts'] if i.kind == 'link_station' and abs(i.x - g['x_vch']) < 140
                and i.y + i.h <= hub.y)
    y0 = v.up(max(lv) + 15.0, v.GY)
    y1 = v.dn(hub.y - 30.0, v.GY)
    xf = None
    iox = m['io']['xfifo']
    # ---- new buses (Q9, Q10, Q11)
    m['buses'] += [('emb_a', 'io', 24, [('sp_constants_sequencer', 'ea'), ('io_embedding_rom', 'a')]),
                   ('tt_res', 'tree_spine', v.TREE_BITS, [('sp_tree_top', 'r'), ('sp_vector_memory', 'tr')]),
                   ('ucie_rx', 'io', 2 * v.IO_BITS, [('io_ucie', 'r'), ('io_collective', 'ur')]),
                   ('serdes_rx', 'io', 2 * v.IO_BITS, [('io_serdes', 'r'), ('io_collective', 'sr')])]
    # ---- Q5: every remaining cross-domain bus through a CDC cluster
    io_side = {'io_collective', 'io_ucie', 'io_serdes'}
    B = []
    xing = []
    for bid, cl, bits, eps in m['buses']:
        ds = {by[i].domain for i, _ in eps}
        if len(ds) < 2 or 'cdc' in ds:
            B.append((bid, cl, bits, eps))
            continue
        (a, pa), (b, pb) = eps
        if {a, b} & hosts and not {a, b} & io_side:
            B.append((bid, cl, bits, eps))
            xing.append(dict(bus=bid, cls=cl, bits=bits, src=a, dst=b, fifo=(set((a, b)) & hosts).pop() + ' (host)',
                             domains=[by[a].domain, by[b].domain]))
            continue
        X = iox
        B.append((bid, cl, bits, [(a, pa), (X.name, f'i_{bid}')]))
        B.append((bid + '_x', cl, bits, [(X.name, f'o_{bid}'), (b, pb)]))
        xing.append(dict(bus=bid, cls=cl, bits=bits, src=a, dst=b, fifo=X.name,
                         domains=[by[a].domain, by[b].domain]))
    m['buses'] = B
    # ---- clocks / resets (Q1-Q4, Q6)
    regs = m['clock_regions']

    def region_of(it):
        return region_at(regs, it.x + it.w / 2, it.y + it.h / 2)
    per = {}
    for it in m['insts']:
        if it.domain == 'stream_1p2' and it.name != 'hub_el':
            per.setdefault(region_of(it), []).append((it.name, 'ck'))
        elif it.kind == 'cdc':
            per.setdefault(region_of(it), []).append((it.name, 'clk'))
    for h in sorted(hosts):
        per.setdefault(region_of(by[h]), []).append((h, 'ckx'))
    per.setdefault(region_of(iox), []).append((iox.name, 'ck'))
    CK = [('clk_root', 'clock_trunk', 1, [('io_collective', 'pll_stream'), ('hub_el', 'ck')])]
    for k in sorted(per):
        CK.append((f'clk_r{k}', 'clock_trunk', 1, [('hub_el', f'pll_r{k}')] + per[k]))
    ser = [(i.name, 'ck') for i in m['insts'] if i.domain == 'serial_0p9' and i.name != 'io_collective']
    CK.append(('clk_serial', 'clock_trunk', 1, [('io_collective', 'pll_serial')] + ser + [(iox.name, 'cks')]))
    CK.append(('clk_ucie', 'clock_trunk', 1, [('io_collective', 'pll_ucie'), ('io_ucie', 'ck'), (iox.name, 'cku')]))
    CK.append(('clk_serdes', 'clock_trunk', 1, [('io_collective', 'pll_serdes'), ('io_serdes', 'ck'), (iox.name, 'ckd')]))
    RS = []
    for st, ct in m['ctrls'].items():
        cds = m['cdcs'][st]
        CK.append((f'clk_hbm_{st}', 'clock_trunk', 1, [(ct.name, 'pll_hbm'), (f'phy_{st}', 'clk')] +
                   [(cd.name, 'hclk') for cd in cds]))
        RS.append((f'rst_hbm_{st}', 'reset', 1, [(ct.name, 'hrst'), (f'phy_{st}', 'rst_n')] +
                   [(cd.name, 'h_arst_n') for cd in cds]))
        RS.append((f'rst_kv_{st}', 'reset', 1, [(m['lfifos'][st].name, 'crst')] + [(cd.name, 'c_arst_n') for cd in cds]))
    # Q6: a forwarded clock with every link hop (the waypoint stations are forwarded-clock link stages)
    for bid, cl, bits, eps in list(m['buses']):
        if cl in ('link_spine', 'link_channel'):
            CK.append((f'fck_{bid}', 'clock_trunk', 1, [(eps[0][0], f'fck_{eps[0][1]}'), (eps[1][0], f'fck_{eps[1][1]}')]))
    m['buses'] += CK + RS
    m['r18'] = dict(crossings=xing, clock_nets=len(CK), region_nets=len(per), reset_nets=len(RS),
                    cdc_hosts=sorted(hosts),
                    io_xfifo=[round(iox.x, 3), round(iox.y, 3), round(iox.w, 3), round(iox.h, 3)],
                    fifo_bits=dict(hosts=sum(x['bits'] for x in xing if x['fifo'].endswith('(host)')),
                                   io=sum(x['bits'] for x in xing if x['fifo'] == 'io_xfifo')))
    # ---- Q8: role variants (flow direction differs by instance)
    mid = g['mid']
    for it in m['insts']:
        if it.kind == 'station':
            it.master = 'qfd_cst_n' if it.y >= mid else 'qfd_cst_s'
        elif it.kind == 'head':
            it.master = 'qfd_chead_e' if it.x >= g['x_vch'] else 'qfd_chead_w'
        elif it.master == 'qfd_lst_h':
            it.master = 'qfd_lst_h_e' if it.x >= g['x_vch'] else 'qfd_lst_h_w'
    _r18_masters(v, m)


R18_CK = tuple(f'ck_{f_}{k}' for f_, n_ in (('bw', 8), ('pair', 4), ('col', 16), ('mul', 16), ('group', 4)) for k in range(n_)) + ('ck', 'ckx', 'cks', 'cku', 'ckd', 'clk', 'hclk', 'crst', 'hrst', 'rst_n', 'h_arst_n', 'c_arst_n') + tuple(f'ck{i}' for i in range(9)) + tuple(f'ck_l{i}' for i in range(16)) + ('ck_pin', 'mux_ck', 'ck_node') + tuple(f'ck_rp{k}' for k in range(5)) + tuple(f'ck_lsl{k}' for k in range(8)) + tuple(f'llr_ck{k}' for k in range(5)) + tuple(f'ck_r{r}_{k}' for r in range(8) for k in range(64)) + tuple(f'clk_{family}{k}' for family, count in [('colr', 4), ('ecol', 5), ('pfold', 4), ('efold', 4)] for k in range(count))


def _r18_masters(v, m):
    base = v.masters

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        for var, src in (('qfd_cst_n', 'qfd_cst'), ('qfd_cst_s', 'qfd_cst'), ('qfd_chead_e', 'qfd_chead'),
                         ('qfd_chead_w', 'qfd_chead'), ('qfd_lst_h_e', 'qfd_lst_h'), ('qfd_lst_h_w', 'qfd_lst_h')):
            o = out[src]
            n = v.Master(var, o.w, o.h, o.obs_top, o.note + f' ({var[-1].upper()} flow variant)')
            n.ports, n.order = dict(o.ports), list(o.order)
            out[var] = n
        for src in ('qfd_cst', 'qfd_chead', 'qfd_lst_h'):
            out.pop(src, None)
        hb = out['qfd_hub']
        hb.note = 'hub element: 4 stack-link endpoints (FIFO 8) and the stream clock root (near-HBM combine DROPPED)'
        for pn in ('ls', 'ck') + tuple(p for p in hb.order if p.startswith('ck') and p != 'ck'):
            if pn in hb.ports:
                hb.ports.pop(pn)
                hb.order.remove(pn)
        # Q13: the hub's SU / VM words face the channel CDC cluster below-east of it; VM em faces the channel too
        for pn, fr in (('x3', 0.22), ('ar', 0.36)):
            if pn in hb.ports:
                hb.ports[pn] = ('face', v.IO_BITS, 'E', 'M4', hb.h * fr, 2)
        if 'ln' in hb.ports:           # r18_real: DRT-0073 on ln[26] at 0.78 h (one pin, no neighbour); one band up
            hb.ports['ln'] = hb.ports['ln'][:4] + (hb.h * 0.81,) + hb.ports['ln'][5:]
        if 'lsw' in hb.ports:          # the split south leg runs in the channel east of the hub
            hb.ports['lsw'] = ('face', v.LINK_TRACKS, 'E', 'M4', hb.h * 0.08, 1)
        vm = out['qfd_sp_vector_memory']
        if 'em' in vm.ports:           # the embedding ROM is in the IO band to the north (left of the hub)
            vm.ports['em'] = ('face', v.IO_BITS, 'N', 'M5', vm.w * 0.2, 2)
        xf = None
        iox = model['io']['xfifo']
        # split compute static IO bind: io_xfifo retired (its CDC is inside the static collective)
        xf_live = any(i_ is iox for i_ in model['insts'])
        out['qfd_io_xfifo'] = None if not xf_live else v.Master('qfd_io_xfifo', iox.w, iox.h, 3, 'IO-band CDC cluster: sequencer -> collective '
                                       'ratio FIFO, collective <-> UCIe / SerDes link-clock async FIFOs')
        # CDC cluster data ports: one pin group per crossing on the face toward its other endpoint; sp_xfifo groups
        # level with the peer's group across the 30 um gap where they fit (r18c i5: M6 1.15 between the SU64 / VM
        # faces and staggered cluster groups), the rest in the free intervals from the top
        byn = {i.name: i for i in model['insts']}
        # r18i: the IO link words spread over the IO band height (r18g i50: every collective / UCIe / SerDes / CDC
        # group stacked in the top 180 um of the band, M6-M8 1.05-1.07 at the die's north edge)
        for mst_, port_, yc_ in (('qfd_io_collective', 'ur', 1000.0), ('qfd_io_collective', 'sr', 1350.0),
                                 ('qfd_io_collective', 'sd', 300.0), ('qfd_io_ucie', 'r', 1000.0),
                                 ('qfd_io_serdes', 'r', 1350.0)):
            if mst_ in out and port_ in out[mst_].ports and out[mst_].ports[port_][0] == 'face':
                out[mst_].ports[port_] = out[mst_].ports[port_][:4] + (yc_,) + out[mst_].ports[port_][5:]
        if not xf_live:
            out.pop('qfd_io_xfifo')
        for X in ((iox,) if xf_live else ()):
            M = out[X.master]
            want = []
            for bid, cl, nb, eps in model['buses']:
                for j, (inst, port) in enumerate(eps):
                    if inst != X.name:
                        continue
                    ot = byn[eps[1 - j][0]]
                    if X is iox and abs(ot.cy - X.cy) > abs(ot.cx - X.cx):
                        face, along, layer = ('N' if ot.cy > X.cy else 'S'), M.w, 'M5'
                    else:
                        face, along, layer = ('E' if ot.cx > X.cx else 'W'), M.h, 'M4'
                    span = (max(1, math.ceil(nb / k)) * 0.048 * k if k > 1 else nb * 0.048) + 1.0
                    yc = None
                    pm = out.get(ot.master)
                    pspec = pm.ports.get(eps[1 - j][1].lstrip('*')) if pm is not None else None
                    if pspec is not None and pspec[0] == 'face' and \
                            pspec[2] == ('W' if face == 'E' else 'E'):
                        yc = ot.y + pspec[4] - X.y
                        if not (span / 2 + 1.0 <= yc <= along - span / 2 - 1.0):
                            yc = None
                    want.append((port, nb, face, layer, along, span, yc))
            occ = {}
            for port, nb, face, layer, along, span, yc in sorted(want, key=lambda w_: w_[6] is None):
                iv = occ.setdefault(face, [])
                if yc is not None and all(yc + span / 2 <= a_ or yc - span / 2 >= b_ for a_, b_ in iv):
                    iv.append((yc - span / 2, yc + span / 2))
                    M.face(port, nb, face, layer, yc, 1)
                    continue
                top = along - 2.0
                for a_, b_ in sorted(iv, key=lambda z: -z[1]):
                    if b_ <= top - span:
                        continue          # this group lies below a candidate slot [top - span, top]
                    top = min(top, a_)
                # scan downward for the highest free slot
                cands = sorted(iv, key=lambda z: -z[0])
                y_hi = along - 2.0
                for a_, b_ in cands + [(-1e9, 1.0)]:
                    if y_hi - b_ >= span:
                        break
                    y_hi = min(y_hi, a_)
                if y_hi - span < 1.0:
                    raise ValueError(f'{X.master}.{port}: face {face} full')
                iv.append((y_hi - span, y_hi))
                M.face(port, nb, face, layer, y_hi - span / 2, 1)
        used = {}
        for bid, cl, bits, eps in model['buses']:
            for inst, port in eps:
                used.setdefault(inst, set()).add(port.lstrip('*'))
        mst_used = {}
        byname = {i.name: i for i in model['insts']}
        for inst, ps in used.items():
            mst_used.setdefault(byname[inst].master, set()).update(ps)
        from qwen_system.port_guard import audit_dropped_ports, PortBindingError
        try:
            model['q14_dropped'] = audit_dropped_ports(
                out, mst_used, strict=model.get('strict_ports', False),
                bound_masters=model.get('rtl_bound_masters'), exemptions=model.get('port_exemptions'))
        except PortBindingError as exc:
            model['q14_dropped'] = exc.ledger
            raise
        mirrored_x = {i.master for i in model['insts'] if i.orient in ('MX', 'R180')}
        for mn, M in out.items():
            # Q14: drop abstract ports no die net reaches
            for pn in [p for p in M.order if p not in mst_used.get(mn, set())]:
                M.order.remove(pn)
                M.ports.pop(pn, None)
            # clock / reset ports: M8 area pins in a row at the block centre (reachable over any OBS)
            j = 0
            for pn in sorted(mst_used.get(mn, set())):
                if pn in M.ports and not (pn in R18_CK or pn.startswith(('pll_', 'fck_'))):
                    continue
                if pn in M.ports and M.ports[pn][0] == 'area':
                    continue
                if pn in R18_CK or pn.startswith(('pll_', 'fck_')):
                    # (the earlier wrappers' face stacking put these on faces already holding data pins: r18_real
                    # pll_r60 on top of hub ln[24]; they all become centre area pins here)
                    if pn in M.ports:
                        M.order.remove(pn)
                        M.ports.pop(pn)
                    if mn in mirrored_x and mn not in getattr(v, 'MIRROR_CK_FINAL', ()):
                        # MX / R180 masters: an M8 area pin's mirror lands off the M8 track (r18c: ot_mts found no
                        # legal origin for qfd_lst_c_split MX); an M5 pin on the N face stays on track mirrored
                        nf = [q for q, sp in M.ports.items() if sp[0] == 'face' and sp[2] == 'N'
                              and not (q in R18_CK or q.startswith(('pll_', 'fck_')))]
                        if nf:
                            raise ValueError(f'{mn}: N face taken, no mirror-legal clock pin slot')
                        M.ports[pn] = ('face', 1, 'N', 'M5', 4.0 + j * 1.0, 1)
                        M.order.append(pn)
                        j += 1
                        continue
                    M.order.append(pn)
                    pp_ = getattr(v, 'CK_AREA_PITCH', 1.6)   # qwendie-1011 r22ko4: 3.2 (1.6 < the M8 pin: rows overlapped)
                    M.area(pn, 1, min(M.w - 1.0, max(1.0, M.w / 2 + ((j % 12) - 6) * pp_)),
                           min(M.h - 1.0, max(1.0, M.h / 2 + (j // 12) * pp_)), 1)
                    j += 1
        return out
    v.masters = masters


def _edge_gap(v, m, gap):
    """b3r14: an empty routing gap of `gap` um (rounded up to 2 GX) between each tile array and the spine slab
    column that faces it; the die grows by 2 gaps.  Everything from the W slab column eastward moves +gap, the E
    array and everything east of it +2 gap (b3r12_i50: M8 1.04-1.11 windows in the one gcell column at the W slab
    face, and M9 gcell overflow over the station column s_31_* next to it; the slab OBS M1-M7 leaves M8 the only
    entry layer, so the face column had no room to fan the block words out)."""
    g = m['geo']
    gap = v.up(gap, 2 * v.GX)
    xs, xe, eps = g['x_spine'], g['x_arr_e'], 1e-6
    sh0 = lambda x: (2 * gap if x >= xe - eps else gap if x >= xs - eps else 0.0)       # a left edge / point
    sh1 = lambda x: (2 * gap if x > xe + eps else gap if x > xs + eps else 0.0)        # a right edge
    for it in m['insts']:
        it.x = round(it.x + sh0(it.x), 3)
    for r in m['regions']:
        a, b, c, d = r['rect']
        r['rect'] = [round(a + sh0(a), 3), b, round(c + sh1(c), 3), d]
    for k in ('x_spine', 'x_vch', 'x_arr_e', 'x_eband'):
        g[k] = round(g[k] + sh0(g[k]), 3)
    old_col_x = m['col_x']
    m['col_x'] = lambda c: old_col_x(c) + (2 * gap if c >= 32 else 0.0)
    m['die']['w'] = round(m['die']['w'] + 2 * gap, 3)
    m['die']['mm2'] = round(m['die']['w'] * m['die']['h'] / 1e6, 3)
    g['edge_gap_um'] = gap


def _split_south(v, m):
    """tools/qwen_rom_fulldie_b3.py selected(): south leg split over both channel edges (verbatim logic)."""
    half = v.VCH / 2
    oldleg, oldcorner = m['legs'][0]
    removed = {i.name for i in oldleg} | {oldcorner.name}
    m['insts'] = [i for i in m['insts'] if i.name not in removed]
    splits = {}
    for side, dx in [('W', 0), ('E', half)]:
        leg = []
        for i in oldleg:
            q = v.Inst(i.name + '_' + side, 'qfd_lst_v_split', i.x + dx, i.y, half - v.SHAVE, i.h, kind='link_station',
                       region='hub')
            leg.append(q)
            m['insts'].append(q)
        corner = v.Inst('lc_S' + side, 'qfd_lst_c_split', oldcorner.x + dx, oldcorner.y, half - v.SHAVE, oldcorner.h,
                        oldcorner.orient, kind='link_station', region='hub')
        m['insts'].append(corner)
        splits[side] = (leg, corner)
    buses = []
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('lnkv_0_'):
            continue
        if bid.startswith('lnkh_0W_'):
            eps = [(splits['W'][1].name, p) if i == oldcorner.name else (i, p) for i, p in eps]
        if bid.startswith('lnkh_0E_'):
            eps = [(splits['E'][1].name, p) if i == oldcorner.name else (i, p) for i, p in eps]
        buses.append((bid, cl, bits, eps))
    for side in ['W', 'E']:
        leg, corner = splits[side]
        prev = ('hub_el', 'lsw' if side == 'W' else 'lse')
        for k, i in enumerate(leg):
            buses.append((f'lnkv_0_{side}_{k}', 'link_spine', v.LINK_TRACKS, [prev, (i.name, 'b')]))
            prev = (i.name, 'a')
        buses.append((f'lnkv_0_{side}_c', 'link_spine', v.LINK_TRACKS, [prev, (corner.name, 'v')]))
    m['buses'] = buses
    m['south_split'] = {s: dict(stations=[i.name for i in l], corner=c.name) for s, (l, c) in splits.items()}


# ------------------------------------------------------------------------------------------------ spine slabs
def _spine_free(v, m, keep):
    """free [lo, hi) intervals per spine column after the kept instances, channel crossings and the hub."""
    g = m['geo']
    cols = {'W': g['x_spine'], 'E': g['x_vch'] + v.VCH}
    if getattr(v, 'XCOL', 0.0):
        # r21m: three columns; the outer two (W, E) keep the band-half slabs beside their tile arrays (a block word
        # never crosses the spine), the middle one M (east of the vertical channel) holds the VM / SU / sequencer
        cols = {'W': g['x_spine'], 'M': g['x_vch'] + v.VCH, 'E': g['x_vch'] + v.VCH + g['cw']}
    ch = g['ch_y']
    segs = [(g['y0'], ch[0]), (ch[0] + v.HCH, ch[1]), (ch[1] + v.HCH, g['y_top'])]
    hub = m['hub']
    free = {}
    for c, x in cols.items():
        iv = [list(s) for s in segs]
        blocks = [(i.y, i.y + i.h + v.SHAVE) for i in keep if abs(i.x - x) < 1]
        if c == 'W':
            blocks.append((hub.y, hub.y + hub.h + v.SHAVE))
        for lo, hi in blocks:
            nxt = []
            for a, b in iv:
                if hi <= a or lo >= b:
                    nxt.append([a, b])
                    continue
                if lo > a:
                    nxt.append([a, lo])
                if hi < b:
                    nxt.append([hi, b])
            iv = nxt
        free[c] = [x_ for x_ in iv if x_[1] - x_[0] > v.GY]
    return cols, free


def _repack_band(v, m):
    """Port and scale slabs in band order, filled bottom-up through both spine columns (central blocks and the hub
    stay).  Each band is four units: its west-half and east-half port groups (block columns 0-7 / 8-15, so a block
    word enters the column on its own side) and the matching scale halves.  A unit goes to the column whose fill
    cursor is lower (its own side on a tie within one group height) and is split at interval ends on whole port
    groups; the first port fragment of a band is that band's primary (result word to the tree top)."""
    g = m['geo']
    cw = g['cw']
    central = [i for i in m['insts'] if i.kind == 'spine_block' and not i.name.startswith(('sp_port_tiles', 'sp_scale_rom'))]
    m['insts'] = [i for i in m['insts'] if not i.name.startswith(('sp_port_tiles', 'sp_scale_rom'))]
    cols, free = _spine_free(v, m, central)
    rows = g['row_y']
    tgt = [_band_tgt(v, rows, b) for b in range(BANDS)]
    port_g = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'port_tiles') / PORT_GROUPS
    scale_g = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'scale_rom') / PORT_GROUPS
    for c in free:
        free[c].sort()
    cur = {c: 0 for c in free}            # index of the interval being filled
    parts = []
    m['band_slabs'] = {}
    nfrag = {}

    def start(c, per):
        """lowest y where one group of `per` mm2 fits in column c (skipping slivers), or None."""
        h = v.up(per * 1e6 / cw, v.GY)
        while cur[c] < len(free[c]) and free[c][cur[c]][1] - free[c][cur[c]][0] < h - 1e-6:
            cur[c] += 1
        return free[c][cur[c]][0] if cur[c] < len(free[c]) else None

    for b in range(BANDS):
        for kind, per in (('port', port_g), ('scale', scale_g)):
            for side in ('W', 'E'):
                left = GROUPS_PER_BAND // 2
                gidx = [GROUPS_PER_BAND * b + (0 if side == 'W' else 8) + j for j in range(8)]
                while left:
                    hg = v.up(per * 1e6 / cw, v.GY)
                    st = {c: start(c, per) for c in free}
                    opts = [c for c in st if st[c] is not None]
                    if not opts:
                        raise SystemExit(f'spine: band {b} {kind} does not pack')
                    c = min(opts, key=lambda c_: (st[c_] - (hg if c_ == side else 0)))
                    iv = free[c][cur[c]]
                    n = min(left, int((iv[1] - iv[0]) * cw / 1e6 / per + 1e-9))
                    h = v.up(n * per * 1e6 / cw, v.GY)
                    if h > iv[1] - iv[0] + 1e-6:
                        n -= 1
                        h = v.up(n * per * 1e6 / cw, v.GY)
                    y = iv[0]
                    iv[0] = y + h
                    key = (kind, b)
                    k = nfrag.get(key, 0)
                    nfrag[key] = k + 1
                    base = f'sp_{"port_tiles" if kind == "port" else "scale_rom"}_{b}'
                    name = base if k == 0 else f'{base}_f{k}'
                    it = v.Inst(name, 'qfd' + name[2:], cols[c], y, cw - v.SHAVE, h - v.SHAVE, kind='spine_block',
                                region='hub')
                    m['insts'].append(it)
                    gs, gidx = gidx[:n], gidx[n:]
                    m['band_slabs'].setdefault(key, []).append((it, gs))
                    parts.append(dict(name=name[3:], kind=kind, band=b, side=side, col=c, groups=gs, y=round(y, 3),
                                      h=round(h, 3), target_y=round(tgt[b], 1), offset_um=round(y + h / 2 - tgt[b], 1)))
                    left -= n
    m['geo']['spine_parts_band'] = parts


def _place_near(v, free, col, h, t):
    """lowest-cost y in column col's free intervals for a block of height h centred nearest t; cuts the interval."""
    best = None
    for iv in free[col]:
        if iv[1] - iv[0] < h - 1e-6:
            continue
        y = min(max(t - h / 2, iv[0]), iv[1] - h)
        y = v.up(y, v.GY) if v.up(y, v.GY) + h <= iv[1] + 1e-6 else v.dn(y, v.GY)
        if best is None or abs(y + h / 2 - t) < best[0] - 1e-6:
            best = (abs(y + h / 2 - t), iv, y)
    if best is None:
        raise SystemExit(f'spine: {h:.1f} um does not fit column {col}')
    _, iv, y = best
    _take(free[col], iv, y, y + h)
    return y


def _repack_b3r3(v, m):
    """Central blocks first, fixed around the hub (W column): vector memory directly below the hub (x root on the
    head row), SU64 below it, tree top directly above; the constant ROM + sequencer in the E column level with SU64
    (crom bus across the channel only).  Then one port+scale slab per band half, in the column of its half
    (block columns 0-7 west, 8-15 east), nearest its band centre; bands nearest the hub first."""
    g = m['geo']
    cw = g['cw']
    hub = m['hub']
    m['insts'] = [i for i in m['insts'] if i.kind != 'spine_block']
    cols, free = _spine_free(v, m, [])
    spans = {c: [list(iv) for iv in ivs] for c, ivs in free.items()}   # r17: link-channel-bounded column spans
    area = {n: a for n, a, *_ in v.SPINE_BLOCKS}
    dom = {n: d for n, a, d, *_ in v.SPINE_BLOCKS}
    hh = lambda mm2: v.up(mm2 * 1e6 / cw, v.GY)
    parts = []

    def put(name, master, col, y, h, domain='stream_1p2'):
        it = v.Inst(name, master, cols[col], y, cw - v.SHAVE, h - v.SHAVE, kind='spine_block', region='hub',
                    domain=domain)
        m['insts'].append(it)
        return it
    hub_lo, hub_hi = hub.y, hub.y + hub.h + v.SHAVE
    h_vm, h_su, h_tt, h_cs = hh(area['vector_memory']), hh(area['su64_sfu']), hh(area['tree_top']), \
        hh(area['constants_sequencer'])
    y_vm = _place_near(v, free, 'W', h_vm, hub_lo - h_vm / 2)
    y_su = _place_near(v, free, 'W', h_su, y_vm - h_su / 2)
    y_tt = _place_near(v, free, 'W', h_tt, hub_hi + h_tt / 2)
    y_cs = _place_near(v, free, 'E', h_cs, y_su + h_su / 2)
    put('sp_vector_memory', 'qfd_sp_vector_memory', 'W', y_vm, h_vm, dom['vector_memory'])
    put('sp_su64_sfu', 'qfd_sp_su64_sfu', 'W', y_su, h_su, dom['su64_sfu'])
    put('sp_tree_top', 'qfd_sp_tree_top', 'W', y_tt, h_tt, dom['tree_top'])
    put('sp_constants_sequencer', 'qfd_sp_constants_sequencer', 'E', y_cs, h_cs, dom['constants_sequencer'])
    for n, y, h, c in (('vector_memory', y_vm, h_vm, 'W'), ('su64_sfu', y_su, h_su, 'W'), ('tree_top', y_tt, h_tt, 'W'),
                       ('constants_sequencer', y_cs, h_cs, 'E')):
        parts.append(dict(name=n, col=c, y=round(y, 3), h=h))
    rows = g['row_y']
    tgt = [_band_tgt(v, rows, b) for b in range(BANDS)]
    half = (area['port_tiles'] + area['scale_rom']) / (2 * BANDS)
    h_sl = hh(half)
    if getattr(v, 'SLAB_GROUP_H', 0.0):
        per = PORT_GROUPS // (2 * BANDS)
        h_sl = v.up(per * v.SLAB_GROUP_H + per * BW_FIFO_BITS * FIFO_MM2_PER_BIT * 1e6 / cw, v.GY)
        m['geo']['slab_group_h_um'] = v.SLAB_GROUP_H
        m['geo']['slab_h_um'] = h_sl
    m['band_slabs'] = {}
    order = sorted(range(BANDS), key=lambda b: abs(tgt[b] - g['mid']))
    if getattr(v, 'SLAB_GROUP_H', 0.0):
        _repack_r17(v, m, free, put, parts, tgt, order, cw, spans)
        return
    for b in order:
        for side in ('W', 'E'):
            y = _place_near(v, free, side, h_sl, tgt[b])
            name = f'sp_port_tiles_{b}' if side == 'W' else f'sp_port_tiles_{b}_f1'
            it = put(name, 'qfd' + name[2:], side, y, h_sl)
            gs = [GROUPS_PER_BAND * b + (0 if side == 'W' else 8) + j for j in range(8)]
            m['band_slabs'].setdefault(('port', b), []).append((it, gs))
            parts.append(dict(name=name[3:], kind='port+scale', band=b, side=side, col=side, groups=gs, y=round(y, 3),
                              h=h_sl, target_y=round(tgt[b], 1), offset_um=round(y + h_sl / 2 - tgt[b], 1)))
    for b in range(BANDS):
        m['band_slabs'][('port', b)].sort(key=lambda z: z[0].name)
        m['band_slabs'][('scale', b)] = m['band_slabs'][('port', b)]
    m['scale_in_port'] = True
    m['geo']['spine_parts_band'] = parts
    m['geo']['spine_free_after_um'] = {c: [[round(a, 1), round(b_, 1)] for a, b_ in iv] for c, iv in free.items()}


def _repack_r17(v, m, free, put, parts, tgt, order, cw, spans, lanes_h=0.0, ser_h=0.0, rtl_groups=False):
    """r17 band slabs of routed port-group elements: each band half is 8 groups of SLAB_GROUP_H (+ its 8 block-word
    FIFOs) in the column of its half, nearest the band centre.  Where the column's free interval is shorter (the
    hub column between the horizontal link channels holds SU64, the vector memory, the hub and the tree top), the
    half keeps as many whole groups as fit and its remaining groups form one overflow fragment in the other column
    of the same span (`_f2`/`_f3`, result word to the band primary through the existing pfrag bus).  Bands nearest
    the hub are packed first."""
    per = PORT_GROUPS // (2 * BANDS)
    fifo_um = BW_FIFO_BITS * FIFO_MM2_PER_BIT * 1e6 / cw
    # rtl_groups (r21m, qwen-lane-band): a fragment of n block words holds ceil(n / 2) result-port group elements
    gpw = RTL_PORT_GROUPS / PORT_GROUPS if rtl_groups else 1.0
    hgt = lambda n: v.up(math.ceil(n * gpw - 1e-9) * v.SLAB_GROUP_H + n * fifo_um, v.GY)   # noqa: E731

    def span(c, t):
        return next((sp for sp in spans[c] if sp[0] - 1e-6 <= t <= sp[1] + 1e-6),
                    min(spans[c], key=lambda sp: min(abs(sp[0] - t), abs(sp[1] - t))))

    def cands(c, t, h):
        lo, hi = span(c, t)
        return [iv for iv in free[c] if iv[0] >= lo - 1e-6 and iv[1] <= hi + 1e-6 and iv[1] - iv[0] >= h - 1e-6]

    def place(c, t, h):
        best = None
        for iv in cands(c, t, h):
            y = min(max(t - h / 2, iv[0]), iv[1] - h)
            y = v.up(y, v.GY) if v.up(y, v.GY) + h <= iv[1] + 1e-6 else v.dn(y, v.GY)
            if best is None or abs(y + h / 2 - t) < best[0] - 1e-6:
                best = (abs(y + h / 2 - t), iv, y)
        if best is None:
            raise SystemExit(f'spine r17: {h:.1f} um does not fit column {c} in the span of y {t:.0f}')
        _take(free[c], best[1], best[2], best[2] + h)
        return best[2]
    def cap(iv, x=0.0):
        n = 0
        while hgt(n + 1) + x <= iv[1] - iv[0] + 1e-6:
            n += 1
        return n

    def dist(iv, t):
        return 0.0 if iv[0] <= t <= iv[1] else min(abs(iv[0] - t), abs(iv[1] - t))
    over, nfr = [], {}
    for b in order:
        for side in ('W', 'E'):
            left = [GROUPS_PER_BAND * b + (0 if side == 'W' else 8) + j for j in range(per)]
            first = True
            while left:
                # nearest interval of the span with room for at least one group: own column, then the other one
                # (r21m: the band's primary also carries the band-lane block stacked on it, lanes_h)
                xh = (lanes_h + ser_h) if (first and side == 'W') else 0.0
                col, iv = None, None
                for c in ((side, 'E' if side == 'W' else 'W') + (('M',) if 'M' in free else ())):
                    ivs = [iv_ for iv_ in cands(c, tgt[b], hgt(1) + xh)]
                    if ivs:
                        col, iv = c, min(ivs, key=lambda iv_: dist(iv_, tgt[b]))
                        break
                if col is None:
                    raise SystemExit(f'spine r17: band {b} {side} groups {left} do not fit the span of y {tgt[b]:.0f}')
                n = min(len(left), cap(iv, xh))
                h = hgt(n)
                y = min(max(tgt[b] - (h + xh) / 2, iv[0]), iv[1] - h - xh)
                y = v.up(y, v.GY) if v.up(y, v.GY) + h + xh <= iv[1] + 1e-6 else v.dn(y, v.GY)
                _take(free[col], iv, y, y + h + xh)
                if xh:
                    # r21m stack, bottom up: the band's result serializer, the primary slab, the band-lane block
                    if ser_h:
                        put(f'sp_res_ser_{b}', 'qfd_sp_res_ser', col, y, ser_h)
                        parts.append(dict(name=f'res_ser_{b}', kind='res_ser', band=b, col=col, y=round(y, 3), h=ser_h))
                        y += ser_h
                    put(f'sp_band_lanes_{b}', 'qfd_sp_band_lanes', col, y + h, lanes_h)
                    parts.append(dict(name=f'band_lanes_{b}', kind='band_lanes', band=b, col=col, y=round(y + h, 3), h=lanes_h))
                if first and col == side:
                    name = f'sp_port_tiles_{b}' if side == 'W' else f'sp_port_tiles_{b}_f1'
                else:
                    k = nfr.get(b, 2)
                    nfr[b] = k + 1
                    name = f'sp_port_tiles_{b}_f{k}'
                    over.append((b, side, col, left[:n]))
                first = False
                it = put(name, 'qfd' + name[2:], col, y, h)
                m['band_slabs'].setdefault(('port', b), []).append((it, left[:n]))
                parts.append(dict(name=name[3:], kind='port+scale', band=b, side=side, col=col, groups=left[:n],
                                  y=round(y, 3), h=h, target_y=round(tgt[b], 1),
                                  offset_um=round(y + h / 2 - tgt[b], 1)))
                left = left[n:]
    for b in range(BANDS):
        m['band_slabs'][('port', b)].sort(key=lambda z: z[0].name)
        m['band_slabs'][('scale', b)] = m['band_slabs'][('port', b)]
    m['scale_in_port'] = True
    m['geo']['spine_parts_band'] = parts
    m['geo']['slab_overflow'] = [dict(band=b, side=s_, col=c_, groups=g_) for b, s_, c_, g_ in over]
    m['geo']['spine_free_after_um'] = {c: [[round(a, 1), round(b_, 1)] for a, b_ in iv] for c, iv in free.items()}


def _take(lst, iv, lo, hi):
    i = lst.index(iv)
    new = []
    if lo - iv[0] > v_GY:
        new.append([iv[0], lo])
    if iv[1] - hi > v_GY:
        new.append([hi, iv[1]])
    lst[i:i + 1] = new


v_GY = F.GY


def _group_map(v, m):
    """port group -> (port slab inst, scale slab inst); block b of band b//16 slot j = b % 16 is group 16*band + j."""
    if 'band_slabs' in m:
        port, scale = {}, {}
        for (kind, b), frags in m['band_slabs'].items():
            for it, gs in frags:
                for g in gs:
                    (port if kind == 'port' else scale)[g] = it.name
        return dict(port=port, scale=scale, primary={b: m['band_slabs'][('port', b)][0][0].name for b in range(BANDS)})
    by = {i.name: i for i in m['insts']}
    per = next(a for n, a, *_ in v.SPINE_BLOCKS if n == 'port_tiles') / PORT_GROUPS
    port, over = {}, []
    for b in range(BANDS):
        it = by[f'sp_port_tiles_{b}']
        cap = min(GROUPS_PER_BAND, int((it.w + v.SHAVE) * (it.h + v.SHAVE) / 1e6 / per + 1e-6))
        for j in range(GROUPS_PER_BAND):
            g = GROUPS_PER_BAND * b + j
            if j < cap:
                port[g] = it.name
            else:
                over.append(g)
    extra = sorted(n for n in by if n.startswith('sp_port_tiles_') and int(n.rsplit('_', 1)[1]) >= BANDS)
    for g in over:   # overflow groups -> the remaining port slab(s), in order
        port[g] = extra[0]
    scales = sorted((n for n in by if n.startswith('sp_scale_rom_')), key=lambda n: int(n.rsplit('_', 1)[1]))
    tot = sum((by[n].w + v.SHAVE) * (by[n].h + v.SHAVE) for n in scales)
    scale, acc, gi = {}, 0.0, 0
    for n in scales:
        acc += (by[n].w + v.SHAVE) * (by[n].h + v.SHAVE)
        while gi < PORT_GROUPS and (gi + 0.5) / PORT_GROUPS <= acc / tot + 1e-9:
            scale[gi] = n
            gi += 1
    return dict(port=port, scale=scale, primary={b: f'sp_port_tiles_{b}' for b in range(BANDS)},
                overflow_groups=over, overflow_slab=extra[0] if extra else None)


def _spine_buses(v, m, gm):
    """block words to the slab holding their port group; fragment -> band primary; scale per group pair;
    sequencer / constant ROM interfaces."""
    total, me_bits = _isa_bits()
    B = []
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('bword_') or bid.startswith('pword_'):
            continue
        B.append((bid, cl, bits, eps))
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('bword_'):
            blk = int(bid.split('_')[1])
            # block_roots enumerate c0 (16 block columns) outer, r0 (6 bands) inner: blk = 6 * cidx + band.
            # Port group = 16 * band + cidx.  (The b2/b3 generator used port bw{blk % 16}, which puts two block
            # words of one band on the same slab pin, e.g. blocks 0 and 48 on port_tiles_0.bw0.)
            g = GROUPS_PER_BAND * (blk % BANDS) + blk // BANDS
            bof = getattr(v, 'BAND_OF', None)
            if bof is not None:
                # qwen-tp8 tp8b (F2 compact bands): the block's band / port index come from the band map (v.BAND_OF,
                # _tp8b_bands), not the legacy 'blk = BANDS * cidx + band' order -- with 4 block rows and 3 bands that
                # order put every third block on a far band's slab (block words up to 18 mm long, stacked in the W
                # spine channel: fine cuts 1.0-1.9).  The block is the one holding the word's root tile.
                mm_ = re.match(r't_(\d+)_(\d+)$', eps[0][0])
                c_, r_ = int(mm_.group(1)), int(mm_.group(2))
                band_, k_ = bof(blk, c_ - c_ % v.BLOCK[0], r_ - r_ % v.BLOCK[1])
                g = GROUPS_PER_BAND * band_ + k_
            slab = gm['port'][g]
            # the overflow slab holds groups of two bands: its pins are named by port group
            pin = f'g{g}' if slab == gm.get('overflow_slab') else f'bw{g % GROUPS_PER_BAND}'
            B.append((bid, cl, bits, [eps[0], (slab, pin)]))
    for b in range(BANDS):
        prim = gm['primary'][b]
        B.append((f'pword_{b}', 'tree_spine', v.TREE_BITS, [(prim, 'rw'), ('sp_tree_top', f'bw{b}')]))
        frags = sorted({gm['port'][GROUPS_PER_BAND * b + j] for j in range(GROUPS_PER_BAND)} - {prim})
        for f in frags:
            B.append((f'pfrag_{b}_{f[3:]}', 'tree_spine', v.TREE_BITS, [(f, f'cw{b}'), (prim, f'cf{f[-1]}')]))
    pairs = {}
    for g in range(PORT_GROUPS):
        pairs.setdefault((gm['port'][g], gm['scale'][g]), []).append(g)
    for (p, s), gs in sorted(pairs.items()):
        if p == s:
            continue          # scale ROM inside its port slab (b3r3): slab-internal
        tag = f'{p[3:]}__{s[3:]}'
        B.append((f'sca_{tag}', 'scale', len(gs) * SC_IN + 1, [(p, f'sa_{s[3:]}'), (s, f'a_{p[3:]}')]))
        B.append((f'scq_{tag}', 'scale', len(gs) * SC_OUT, [(s, f'q_{p[3:]}'), (p, f'sq_{s[3:]}')]))
    seq = 'sp_constants_sequencer'
    B.append(('seq_ib', 'sequencer', 379 + 3, [(seq, 'ib'), ('sp_vector_memory', 'ib')]))
    B.append(('seq_su', 'sequencer', total - me_bits + 2, [(seq, 'su'), ('sp_su64_sfu', 'si')]))
    B.append(('seq_done', 'sequencer', 2, [('sp_tree_top', 'md'), (seq, 'md')]))
    B.append(('seq_sud', 'sequencer', 2, [('sp_su64_sfu', 'sd'), (seq, 'sd')]))
    if NATIVE_COLL:
        B.append(('seq_coll', 'sequencer', SEQ_COLL_BITS[1], [(seq, 'cd'), ('io_collective', 'sd')]))
        B.append(('coll_seq', 'sequencer', SEQ_COLL_BITS[2], [('io_collective', 'cs'), (seq, 'cc')]))
    else:
        B.append(('seq_coll', 'sequencer', SEQ_COLL_BITS[0], [(seq, 'cd'), ('io_collective', 'sd')]))
    B.append(('crom_a', 'crom', CROM_IN, [('sp_su64_sfu', 'ca'), (seq, 'ca')]))
    B.append(('crom_q', 'crom', CROM_OUT, [(seq, 'cq'), ('sp_su64_sfu', 'cq')]))
    m['buses'] = B
    m['isa_bits'] = dict(total=total, me=me_bits, su_and_control=total - me_bits)


def _wrap_masters(v, m, area_pins=False, ns_faces=False, spread=False, channel=False, bw_align=False,
                  bw_edge=False, bw_edge_inner=False, bw_sp=100.0, bw_x=20.0):
    """Every endpoint port that the b3 masters do not define becomes a pin group on the face toward the far
    endpoint (M4 on W/E), stacked from the top of the face so no two groups overlap."""
    base = v.masters
    by = {i.name: i for i in m['insts']}

    def masters(model, k=1, port_bits=None):
        by = {i.name: i for i in model['insts']}
        out = base(model, k, port_bits)
        if 'qfd_tile_e' in out:
            # r19: the east-array tile = the (wrapped) west tile with the landing in / out faces swapped
            t, te = out['qfd_tile'], out['qfd_tile_e']
            te.ports = {k_: v_ for k_, v_ in t.ports.items()}
            te.order = list(t.order)
            te.ports['li'] = ('face',) + t.ports['li'][1:2] + ('E',) + t.ports['li'][3:]
            te.ports['lo'] = ('face',) + t.ports['lo'][1:2] + ('W',) + t.ports['lo'][3:]
        hub = out['qfd_hub']
        if 'lsw' not in hub.ports:
            hub.face('lsw', v.LINK_TRACKS, 'W', 'M4', hub.h / 8, 1)
            hub.face('lse', v.LINK_TRACKS, 'E', 'M4', hub.h / 2, 1)
        half = v.VCH / 2
        sv = v.Master('qfd_lst_v_split', half - v.SHAVE, v.LST_V[1] - v.SHAVE, 3, 'b3 one lower stack link, half channel')
        sv.face('a', v.LINK_TRACKS, 'S', 'M5', sv.w / 2, 1)
        sv.face('b', v.LINK_TRACKS, 'N', 'M5', sv.w / 2, 1)
        sc = v.Master('qfd_lst_c_split', half - v.SHAVE, v.HCH - v.SHAVE, 3, 'b3 lower corner, one stack link')
        sc.face('v', v.LINK_TRACKS, 'S', 'M5', sc.w / 2, 1)
        sc.face('w', v.LINK_TRACKS, 'W', 'M4', sc.h / 2, 1)
        sc.face('e', v.LINK_TRACKS, 'E', 'M4', sc.h / 2, 1)
        out[sv.name] = sv
        out[sc.name] = sc
        if spread:
            # b3r4: the north link leaves the hub on its E face (the channel side); on the N face it ran into the
            # tree top that abuts the hub (b3r3: M7/M9 windows over capacity at the hub top)
            hub.ports['ln'] = ('face', 2 * v.LINK_TRACKS, 'E', 'M4', hub.h * 0.78, 1)
            # block-word area pins: one word per eighth of the slab height, at the edge facing its tile array
            # (b3r3: all eight words of a slab entered one 41 um M8 band, M8 windows 1.125 at the slab faces)
            xs = model['geo']['x_vch']
            slab_prefix = ('qfd_sp_port_tiles', 'qfd_port_tiles') if channel else ('qfd_sp_port_tiles',)
            for it in model['insts']:
                if it.kind != 'spine_block' or not it.master.startswith(slab_prefix):
                    continue
                b = out[it.master]
                east = it.x > xs
                # b3r6: the b3r3 band slabs' masters are qfd_port_tiles_<b>[_f1] (not qfd_sp_*), so b3r4/b3r5 never
                # spread them: all eight words sat as M4 face pins in the top 212 um of the slab face (the M8 1.09
                # windows at every east slab's top-east corner).  Only the slab's own eight words get pins.
                words = range(8, 16) if (channel and east) else range(8) if channel else range(16)
                yj = {i: b.h * (i % 8 + 0.5) / 8 for i in words}
                if bw_align:
                    # b3r8: the slab's words enter at the height of their block roots (all eight roots of a band
                    # side sit on one tile row), 100 um apart, instead of eighths of the slab: b3r7's remaining M9
                    # windows at the W column edge (x 11.42 mm, y 8.4 / 18.85 mm) are block words running down
                    # the spine edge from the root row to a slab pin up to 2.6 mm away
                    ry = model['b3r8_root_y'].get(it.name, {})
                    ws = sorted((i for i in words if i in ry), key=lambda i: ry[i])
                    yr = sum(ry[i] for i in ws) / len(ws) - it.y if ws else 0.0
                    if ws and bw_edge and not (50.0 <= yr <= b.h - 50.0):
                        # b3r10: the root row lies outside the slab (band 3 W sits above the tree top, band 2 E
                        # below its row): the words enter at the near edge, spread over the slab width, so the
                        # vertical climb runs over the neighbouring block's M9, not down one column at the spine
                        # edge (b3r8: M9 windows 1.30 at x 10.8-11.5 mm, y 18.85 mm, all eight band-3 W words)
                        ye = 70.0 if yr < 50.0 else b.h - 70.0
                        ordx = sorted(ws, key=lambda i: model['b3r8_root_x'][it.name][i], reverse=not east)
                        x0, x1 = 20.0, b.w - 40.0
                        if bw_edge_inner:
                            # b3r12: the word from the block next to the spine climbs farthest into the slab
                            # (b3r11: M9 1.04 at x 11.42 mm, y 18.85 mm, the spine-edge corridor under slab 3 W)
                            # (ordx runs nearest-root first for an east slab already; reverse the west one)
                            ordx = ordx if east else ordx[::-1]
                            x0, x1 = (0.25 * b.w, b.w - 40.0) if not east else (20.0, 0.75 * b.w)
                        for q, i in enumerate(ordx):
                            xq = x0 + (x1 - x0 - 20.0) * (q + 0.5) / len(ordx)
                            if f'bw{i}' not in b.order:
                                b.order.append(f'bw{i}')
                            b.ports[f'bw{i}'] = ('area', v.TREE_BITS, xq, ye, 2)
                        continue
                    if ws:
                        # b3r13: bw_sp > 100 spreads the root-row words over more of the slab face (b3r12_i50: M8
                        # 1.11 windows in the gcell column at the W slab face, x 11.4576 mm, inside the 800 um
                        # band each slab's eight words entered)
                        sp = bw_sp
                        cen = sum(ry[i] for i in ws) / len(ws) - it.y
                        cen = min(max(cen, sp * len(ws) / 2 + 20.0), b.h - sp * len(ws) / 2 - 20.0)
                        for q, i in enumerate(ws):
                            yj[i] = cen + (q - (len(ws) - 1) / 2) * sp
                for i in words:
                    j = i % 8
                    # 2-track pin pitch: a word's 32 bundled M8 pins span 82 um, two M8 tracks per wire
                    if f'bw{i}' not in b.order:
                        b.order.append(f'bw{i}')        # pins are emitted in Master.order (b3r6 fix)
                    b.ports[f'bw{i}'] = ('area', v.TREE_BITS, (b.w - 20.0 - bw_x) if east else bw_x, yj[i], 2)
            # corridor buses: pins at a 2-track pitch over the station / column-head N and S faces (37 um of the
            # 52.7 um frame instead of 19 um), so the vertical corridor run spreads over the corridor's M7/M9
            # tracks (b3r4 per-gcell dump: 62.7k M9 overflow, all in the corridor x range, 7-8 tracks a gcell)
            for nm in ('qfd_cst', 'qfd_chead'):
                mst = out[nm]
                for pn in ('a', 'b', 'n', 's'):
                    if pn in mst.ports and mst.ports[pn][0] == 'face' and mst.ports[pn][2] in 'NS':
                        kind, w_, face, layer, centre, _ = mst.ports[pn]
                        mst.ports[pn] = (kind, w_, face, layer, centre, 2)
        if channel:
            # b3r6: tree-top block-word area pins at a 2-track pitch (6 words in one row at mid height)
            tt = out.get('qfd_sp_tree_top')
            if tt is not None:
                for pn, spec in list(tt.ports.items()):
                    if spec[0] == 'area':
                        tt.ports[pn] = spec[:4] + (2,)
        # spine slabs created by the band repack (fragments) need masters
        for it in model['insts']:
            if it.kind == 'spine_block' and it.master not in out:
                b = v.Master(it.master, it.w, it.h, 7, f'spine reservation slab {it.master}')
                out[it.master] = b
                if it.master.startswith('qfd_sp_port_tiles'):
                    for i in range(16):
                        b.area(f'bw{i}', v.TREE_BITS, 20.0 + (b.w - 40.0) * (i % 8) / 8, b.h * ((i // 8) + 0.5) / 2, 1)
        cursor = {}
        bits = {}
        far = {}
        for bid, cl, nb, eps in model['buses']:
            for idx, (inst, port) in enumerate(eps):
                mst = by[inst].master if inst in by else None
                if mst is None or mst not in out or port.lstrip('*') in out[mst].ports:
                    continue
                other = eps[1 - idx][0] if len(eps) == 2 else eps[0][0]
                bits[(mst, port)] = max(bits.get((mst, port), 0), nb)
                far[(mst, port)] = (by[inst], by[other])
        spine = {i.master for i in model['insts'] if i.kind == 'spine_block'}
        colcur = {}
        if channel:
            _channel_pins(v, model, out, bits, far, k)
        for (mst, port), nb in sorted(bits.items(), key=lambda kv: -kv[1]):
            M = out[mst]
            if channel and port in M.ports:
                continue
            me, ot = far[(mst, port)]
            if area_pins and mst in spine:
                # M8 area pins over the slab interior (as the b2 block-word pins), in columns between the
                # existing bw columns, stacked from the top; a slab is a reservation, so its ports reach the die
                # nets from above instead of crowding one M4 face (b3r2b: M4-M7 overflow at the slab faces)
                step = 0.080 * k
                span = max(1, math.ceil(nb / k)) * step + 2.0
                cols = colcur.setdefault(mst, {j: M.h - 4.0 for j in range(max(1, int((M.w - 60) // 60)))})
                j = max(cols, key=lambda c_: cols[c_])
                if cols[j] - span < 2.0:
                    raise ValueError(f'{mst}.{port}: no area pin room ({nb} bits)')
                centre = cols[j] - span / 2
                cols[j] -= span
                M.area(port, nb, 50.0 + 60.0 * j, centre, 1)
                continue
            vert = ns_faces and abs(ot.cy - me.cy) > abs(ot.cx - me.cx)
            if getattr(v, 'SLAB_GROUP_H', 0.0) and port.startswith(('cf', 'cw')):
                # r17: fragment result words leave on the channel faces; a fragment's N/S face abuts its stacked
                # neighbour (band 3 f3 under f2, band 2 f3 on the sequencer), which buries N/S pins
                vert = False
            face = ('N' if ot.cy >= me.cy else 'S') if vert else ('E' if ot.cx >= me.cx else 'W')
            layer = 'M5' if vert else 'M4'
            step = 0.048 * k
            span = max(1, math.ceil(nb / k)) * step if k > 1 else nb * 0.048
            along = M.w if vert else M.h
            if getattr(v, 'SLAB_GROUP_H', 0.0) and port.startswith(('cf', 'cw')) and not vert and ot.cy < me.cy:
                # r17: a fragment result word whose other end lies below enters at the bottom of the face (from the
                # top it ran the whole slab height down the channel edge: r17p M6 1.04 at the band-3 primary)
                c = cursor.get((mst, face, 'lo'), 4.0)
                centre = c + span / 2 + 1.0
                cursor[(mst, face, 'lo')] = centre + span / 2 + 1.0
                M.face(port, nb, face, layer, centre, 1)
                continue
            c = cursor.get((mst, face), along - 4.0)
            centre = c - span / 2 - 1.0
            cursor[(mst, face)] = centre - span / 2 - 1.0
            if centre - span / 2 < 1.0:
                raise ValueError(f'{mst}.{port}: face {face} full')
            M.face(port, nb, face, layer, centre, 1)
        return out
    v.masters = masters


def _abutter(model, me, face, gap=2.0, frac=0.5):
    """name of the block (not a relay) whose edge lies within `gap` um of `me`'s `face` over at least `frac` of that
    face, or None."""
    for o in model['insts']:
        if o is me or o.name.startswith('rly_'):
            continue
        if face in 'NS':
            d = (o.y - (me.y + me.h)) if face == 'N' else (me.y - (o.y + o.h))
            ov = min(me.x + me.w, o.x + o.w) - max(me.x, o.x)
            L = me.w
        else:
            d = (o.x - (me.x + me.w)) if face == 'E' else (me.x - (o.x + o.w))
            ov = min(me.y + me.h, o.y + o.h) - max(me.y, o.y)
            L = me.h
        if -0.5 <= d <= gap and ov >= frac * L:
            return o.name
    return None


OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}


def _seam_free(v, m):
    """r22ks (qwen-1010/d 2026-10-10, opt-in): no word leaves a block through a face that another block abuts, unless
    it is an abutted pair (the peer is that block, on its facing face).  r22k4's full-die GRT put all of its 159,448
    overflow in one 90 x 60 um window: the tree top's ty (1,538 b) on its S face and the VM's rb3-rb5 (3 x 551 b) on
    its N face sat on the zero-width tree-top / VM seam, under both blocks' M1-M7 obstructions, so every wire escaped
    by an M8 / M9 via stack at the seam.  A violating word moves to the face on the other axis toward its peer (or
    the peer's side when the peer is the abutting block), at the end of that face nearer the peer, clear of the pins
    already there.  Single-instance blocks only (a shared master's faces serve every instance); clock / reset nets
    are built by the die clock tree.  The decision is taken once, on the pre-relay buses, and then held (after the
    relays a word's peer is its first relay, which was placed for the moved pin)."""
    base = v.masters
    cache = {}
    moves = m.setdefault('r22ks_seam_moves', {})

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        insts = [i for i in model['insts'] if not i.name.startswith('rly_')]
        n_of = {}
        for i in insts:
            n_of[i.master] = n_of.get(i.master, 0) + 1
        by = {i.name: i for i in model['insts']}
        if True:
            peers = {}
            for bid, cl, nb, eps in model['buses']:
                if cl in ('clock_trunk', 'reset'):
                    continue
                for j, (inst, port) in enumerate(eps):
                    peers.setdefault((inst, port.lstrip('*')), []).extend(
                        (e[0], e[1].lstrip('*'), nb) for q, e in enumerate(eps) if q != j)
            for it in insts:
                M_ = out.get(it.master)
                if M_ is None or n_of.get(it.master) != 1:
                    continue
                for pn, sp in list(M_.ports.items()):
                    if sp[0] != 'face' or (it.name, pn) not in peers or (it.master, pn) in cache:
                        continue
                    if any(q[0].startswith('rly_') for q in peers[(it.name, pn)]):
                        continue           # after the relays: only the pre-relay decisions hold
                    f = sp[2]
                    ab = _abutter(model, it, f)
                    if ab is None:
                        continue
                    pp = peers[(it.name, pn)]
                    paired = all(q[0] == ab for q in pp) and all(
                        (out[by[ab].master].ports.get(q[1]) or ('',))[0] == 'face'
                        and out[by[ab].master].ports[q[1]][2] == OPP[f] for q in pp)
                    if paired:
                        continue
                    o = by[pp[0][0]]
                    osp = out[o.master].ports.get(pp[0][1]) if o.master in out else None
                    if f in 'NS':
                        nf = 'E' if o.cx > it.cx + 1.0 else 'W' if o.cx < it.cx - 1.0 else None
                    else:
                        nf = 'N' if o.cy > it.cy + 1.0 else 'S' if o.cy < it.cy - 1.0 else None
                    if nf is None and osp is not None and osp[0] == 'face' and osp[2] != OPP[f]:
                        nf = osp[2]        # the peer straight across the seam: leave on the side of its pin
                    cands = [x for x in ((nf,) if nf else ()) + tuple('NSEW') if x != f]
                    nf = next((x for x in cands if _abutter(model, it, x) is None), None)
                    if nf is None:
                        raise ValueError(f'r22ks: {it.name}.{pn}: every other face is abutted')
                    low = (o.cx < it.cx) if nf in 'NS' else (o.cy < it.cy)
                    cache[(it.master, pn)] = (nf, low, sum(q[2] for q in pp), ab)
        for (mn, pn), (nf, low, nb, ab) in cache.items():
            M_ = out[mn]
            sp = M_.ports[pn]
            if sp[0] == 'face' and sp[2] == nf:
                continue
            w_ = sp[1]
            layer = 'M5' if nf in 'NS' else 'M4'
            along = M_.w if nf in 'NS' else M_.h
            n = max(1, math.ceil(w_ / k)) if k > 1 else w_
            span = n * F.TRK[layer][1] * k
            M_.ports.pop(pn)
            used = sorted(_face_used(M_, nf, k))
            a_ = 4.0 if low else along - 4.0 - span - 2.0
            for _ in range(len(used) + 1):
                hit = [u for u in used if u[0] < a_ + span + 2.0 and u[1] > a_]
                if not hit:
                    break
                a_ = max(u[1] for u in hit) if low else min(u[0] for u in hit) - span - 2.0
            if a_ < 1.0 or a_ + span + 2.0 > along - 1.0 or hit:
                raise ValueError(f'r22ks: {mn}.{pn} ({w_} b) does not fit the {nf} face')
            M_.ports[pn] = ('face', w_, nf, layer, a_ + 1.0 + span / 2, 1)
            if k == 1:
                moves[f'{mn}.{pn}'] = dict(face=f'{sp[2]}->{nf}', bits=w_, seam_with=ab)
        # pin plan frozen at its pre-relay state: the default face rule re-derives a block's pins from its CURRENT
        # buses, so after the relay pass a word's pin turned toward its last relay (r22k: VM rb3 W face at pitch 4,
        # where its relays were planned, became an N-face seam pin) -- pins first, relays from the pins, never back
        if k in snap:
            for (mn, pn), sp in snap[k].items():
                if mn in out and pn in out[mn].ports:
                    out[mn].ports[pn] = sp
        else:
            snap[k] = {(i.master, pn): sp for i in insts if n_of.get(i.master) == 1 and i.master in out
                       for pn, sp in out[i.master].ports.items()}
        return out
    snap = {}
    v.masters = masters
    masters(m, 1)             # decide on the pre-relay buses (the relay pass rewrites them as it goes)


def _face_used(M, face, k):
    """[lo, hi] intervals (master-local, along the face) already taken by face pins on `face`."""
    used = []
    for spec in M.ports.values():
        if spec[0] != 'face' or spec[2] != face:
            continue
        _, w, _, layer, centre, pitch = spec
        n = max(1, math.ceil(w / k)) if k > 1 else w
        span = n * F.TRK[layer][1] * k * pitch
        used.append((centre - span / 2 - 2.0, centre + span / 2 + 2.0))
    return used


def _channel_pins(v, model, out, bits, far, k):
    """b3r6: a bus between two spine blocks on opposite sides of the channel leaves both blocks on the faces that
    look at each other (E of the west block, W of the east block, M4), with its pins at the same die y on both
    faces, inside the two blocks' vertical overlap, skipping pins already on either face, at the widest pitch
    (4..1 tracks) that fits.  b3r4/b3r5 stacked these from the top of whichever face the centre-to-centre
    direction chose: the constant-ROM buses (crom_q 4,096 + crom_a 1,600 bits) entered the channel in the top
    200 um of SU64, the vector-memory instruction word left through the S face into the same corner (M7 1.09,
    M9 1.06 windows at x 12.2-12.5 mm, y 14.45-14.53 mm)."""
    xs = model['geo']['x_vch']
    by = {i.name: i for i in model['insts']}
    groups = {}
    for (mst, port), nb in bits.items():
        me, ot = far[(mst, port)]
        if me.kind != 'spine_block' or ot.kind != 'spine_block' or (me.cx < xs) == (ot.cx < xs):
            continue
        w_, e_ = (me, ot) if me.cx < xs else (ot, me)
        groups.setdefault((w_.name, e_.name), {})[(me.name, port)] = nb
    placed = {}
    for (wn, en), ports in sorted(groups.items()):
        W, E = by[wn], by[en]
        lo, hi = max(W.y, E.y) + 4.0, min(W.y + W.h, E.y + E.h) - 4.0
        # pair the two ends of each bus: one slot per bus, both ends at the same y
        buses = {}
        for (inst, port), nb in ports.items():
            mate = None
            for bid, cl, nb_, eps in model['buses']:
                if len(eps) == 2 and (inst, port) in [(a, p.lstrip('*')) for a, p in eps]:
                    mate = bid
                    break
            buses.setdefault(mate, []).append((inst, port, nb))
        need = sum(max(1, math.ceil(max(nb for *_, nb in ends) / k)) for ends in buses.values())
        if hi - lo < 20.0:
            continue
        used = [(W.y + a, W.y + b) for a, b in _face_used(out[W.master], 'E', k)] + \
               [(E.y + a, E.y + b) for a, b in _face_used(out[E.master], 'W', k)]
        if getattr(v, 'SLAB_GROUP_H', 0.0):
            # r17: a link waypoint in the channel abuts both faces and buries any pin in its y span (r17p
            # DRT-0073 on sp_port_tiles_2_f2/cw2: lv_S_2_E covers the fragment's W face at y 11,969-12,003)
            used += [(i.y - 2.0, i.y + i.h + 2.0) for i in model['insts']
                     if i.kind == 'link_station' and xs - 1.0 <= i.x <= xs + v.VCH + 1.0]
        free = [(lo, hi)]
        for a, b in sorted(used):
            nf = []
            for x0, x1 in free:
                if b <= x0 or a >= x1:
                    nf.append((x0, x1))
                    continue
                if a > x0:
                    nf.append((x0, a))
                if b < x1:
                    nf.append((b, x1))
            free = nf
        step1 = F.TRK['M4'][1] * k
        for pitch in (4, 3, 2, 1):
            spans = sorted(((max(1, math.ceil(max(nb for *_, nb in ends) / k)) * step1 * pitch + 4.0, bid)
                            for bid, ends in buses.items()), reverse=True)
            fr = [list(iv) for iv in sorted(free, key=lambda iv: iv[0] - iv[1])]
            slot = {}
            for sp, bid in spans:
                iv = next((iv for iv in fr if iv[1] - iv[0] >= sp), None)
                if iv is None:
                    break
                slot[bid] = iv[1] - sp / 2           # from the top of the free interval
                iv[1] -= sp
            else:
                break
        else:
            continue
        for bid, ends in buses.items():
            y = slot[bid]
            for inst, port, nb in ends:
                it = by[inst]
                face = 'E' if it.name == wn else 'W'
                out[it.master].face(port, nb, face, 'M4', y - it.y, pitch)
                placed[(it.master, port)] = (face, round(y, 1), pitch)
    model.setdefault('b3r6_channel', {}).update({f'{a}.{b}': v_ for (a, b), v_ in placed.items()})


def _root_spread(v, m):
    """qwen-tp8 contract v2 (TP4 e9 finding, el1011-qwendie 03:50): the morton host rule puts every block root (and so
    the 16 block words of a band and their waypoints) in ONE tile row (local row 1), which overflowed the M8 / M6 H
    rows over that row.  Re-host each block's tree with its local row index XORed with (block column mod 4): XOR on
    the row bits is an automorphism of the morton pair tree (every level's partner keeps its distance), so every leg
    keeps its length and the reduction order is unchanged (ROM slice placement is a compile-time map, as in
    _east_mirror); the roots land on local rows 1, 0, 3, 2 -> four distinct rows per band."""
    bc, br = v.BLOCK
    rx = re.compile(r't_(\d+)_(\d+)$')

    def mp(inst):
        mm = rx.match(inst)
        if not mm:
            return inst
        c, r = int(mm.group(1)), int(mm.group(2))
        r0 = r - r % br
        return f't_{c}_{r0 + ((r - r0) ^ ((c // bc) % br))}'
    out, n = [], 0
    for bid, cl, bits, eps in m['buses']:
        if cl == 'tree_block' or bid.startswith('bword_'):
            neps = [(mp(i), p) if p in ('t_out', 'n_a', 'n_b', 'n_y') else (i, p) for i, p in eps]
            n += neps != eps
            eps = neps
        out.append((bid, cl, bits, eps))
    m['buses'] = out
    roots = sorted({int(rx.match(e[0]).group(2)) for bid, cl, bits, eps in out if bid.startswith('bword_')
                    for e in eps[:1] if rx.match(e[0])})
    m['geo']['tp8_root_spread'] = dict(remapped_buses=n, root_rows=roots)


def _east_mirror(v, m):
    """b3r9: mirror the ME split tree of every east-array block (block columns 8-15) in x, so its root sits in the
    block column nearest the spine like the west blocks' (the morton host rule puts every root at local (3, 1): the
    spine side for the west array, the far side for the east array).  Only the tile hosting each tree node changes:
    the tree's pairing and order are the same logical tree over the same 16 K-slices, with the compiler placing
    slice s on the mirrored tile (ROM contents are a compile-time map), so the reduction order is unchanged.
    b3r7: the far-east roots run block 95's tree and word along the last corridor next to the PHY strip
    (M9 windows 1.10 at x 23.32 mm, y 29.3-30.0 mm), and every east block word starts 3 tile pitches further out."""
    bc = v.BLOCK[0]
    half = v.COLS // 2
    rx = re.compile(r't_(\d+)_(\d+)$')

    def mir(inst):
        mm = rx.match(inst)
        if not mm:
            return inst
        c, r = int(mm.group(1)), int(mm.group(2))
        if c < half:
            return inst
        c0 = c - c % bc
        return f't_{c0 + bc - 1 - (c - c0)}_{r}'
    out = []
    n = 0
    for bid, cl, bits, eps in m['buses']:
        if cl == 'tree_block' or bid.startswith('bword_'):
            neps = [(mir(i), p) if p in ('t_out', 'n_a', 'n_b', 'n_y') else (i, p) for i, p in eps]
            n += neps != eps
            eps = neps
        out.append((bid, cl, bits, eps))
    m['buses'] = out
    m['geo']['b3r9_mirrored_buses'] = n


def _io_faces(v):
    """b3r11: the collective -> SerDes word leaves io_collective on its E face (below the UCIe word) and enters
    io_serdes on its W face, instead of N (the die edge: 21 um of sliver above the IO row) and S.  b3r8: the only
    M9 window over 1.0 outside the spine was n_serdes_tx (53 of 53 nets) at x 12.34-12.42 mm on the die top edge."""
    base = v.masters

    def masters(model, k=1, port_bits=None):
        out = base(model, k, port_bits)
        if 'qfd_io_collective' not in out or 'qfd_io_serdes' not in out:
            return out      # split compute static IO bind: the credit IO masters are retired (native_static_io_bind)
        col, ser = out['qfd_io_collective'], out['qfd_io_serdes']
        kind, w, face, layer, centre, pitch = col.ports['u']
        col.ports['s'] = ('face', col.ports['s'][1], 'E', 'M4', centre + 400.0, 2)
        ser.ports['c'] = ('face', ser.ports['c'][1], 'W', 'M4', centre + 400.0, 2)
        return out
    v.masters = masters


TREE_COL_UM = 9.24          # one GRT gcell (the k16 GRT grid pitch, gcell_over.txt x step)


def _tree_cols(v, ncols, interleave=False):
    """b3r7: the tile's four tree-word area pins (t_out, n_a, n_b, n_y; 32 bundled M8 pins each) laid out as ncols
    sub-columns one gcell apart instead of one 82 um stack at one x.  b3r5's per-gcell dump: 13.1k of the 19.4k
    M9 overflow sits over the tile bodies at the tree-pin x (column offsets 246-292 um), 7-8 M9 tracks a gcell
    carrying a 32-wire word that leaves one x.
    interleave (r20): the four ports' sub-columns interleave across the body (port i, sub-column j at
    x = 10 + (4 j + i) gcells) instead of four 6-gcell groups: r18j i50 / r19 i5 M9 overflow is 1-gcell-wide vertical
    lines of tree words (tree nets 57k of 60k blamed gcell-hits) at the pin-group x and in the corridor."""
    stride = 4 if interleave else 1
    base_masters, base_rects = v.masters, v.pin_rects

    def masters(model, k=1, port_bits=None):
        out = base_masters(model, k, port_bits)
        # r20: the r19 east-array variant qfd_tile_e copies the tile's ports BEFORE this wrapper ran, so it kept the
        # one-stack b3r5 tree pins (x 100: r19 i5 M9 33.8k, the 'li/lo' swap is its only intended difference)
        for t, i, pn in [(out[tn], i, pn) for tn in ('qfd_tile', 'qfd_tile_e') if tn in out
                         for i, pn in enumerate(('t_out', 'n_a', 'n_b', 'n_y'))]:
            spec = t.ports[pn]
            if spec[0] == 'area' and len(spec) == 5:
                # x 10 + 60 i (was 40 + 60 i): the ncols sub-columns stay inside the 260.9 um body
                x = 10.0 + (TREE_COL_UM * i if interleave else 60.0 * i)
                if x + (ncols - 1) * stride * TREE_COL_UM + 0.4 * k > (t.w - 2.0 if interleave else min(x + 60.0, t.w - 2.0)) - 1e-6:
                    raise ValueError(f'tree pin columns: {ncols} do not fit')
                t.ports[pn] = ('area', spec[1], x, spec[3], spec[4], ncols)
        return out

    def pin_rects(mst, k, wmap):
        cols = {p: s_ for p, s_ in mst.ports.items() if s_[0] == 'area' and len(s_) == 6}
        if not cols:
            return base_rects(mst, k, wmap)
        saved = dict(mst.ports)
        for p in cols:
            mst.ports[p] = cols[p][:5]
        try:
            rects = base_rects(mst, k, wmap)
        finally:
            mst.ports.clear()
            mst.ports.update(saved)
        out = []
        for nm, layer, r in rects:
            port = nm.split('[')[0]
            if port not in cols:
                out.append((nm, layer, r))
                continue
            _, _, x, yc, pitch, nc = cols[port]
            n = wmap.get(port, cols[port][1])
            i = int(nm.split('[')[1].rstrip(']'))
            per = math.ceil(n / nc)
            ci, ri = i // per, i % per
            off, pp = F.TRK['M8']
            step = pp * k * pitch
            y = off * k + round((yc - per * step / 2 - off * k) / (pp * k)) * pp * k + ri * step
            hw = 0.020 * k
            xx = x + ci * stride * TREE_COL_UM
            out.append((nm, layer, (xx, y - hw, xx + 0.4 * k, y + hw)))
        return out
    v.masters, v.pin_rects = masters, pin_rects


def _slab_bw_m8(v):
    """r21 seam fix (owner 2026-10-06): the band slabs' block-word pins move from the M6 strip (b3r15 option B) to
    M8 at the array-facing face, one word per port-group slot (the slab is a stack of port-group elements, each
    with its bw_/tw_ pins on M8 spread over its whole array face: pins_bw_m8.tcl), the words in their root order.
    r20c 0-iteration full-die GRT: the east slabs' M6 strip funnelled every east block word through one gcell
    column at the seam with the first east tile column (tile OBS M1-M7), 2D capacity 1-2."""
    base_masters = v.masters

    def masters(model, k=1, port_bits=None):
        out = base_masters(model, k, port_bits)
        xv = model['geo']['x_vch']
        for name, b in out.items():
            if not name.startswith('qfd_port_tiles'):
                continue
            west = next(it.x < xv for it in model['insts'] if it.master == name)
            b.m6_strip = None
            bws = sorted((p_ for p_, s in b.ports.items() if p_.startswith('bw') and s[0] == 'area'),
                         key=lambda p_: (b.ports[p_][3], int(p_[2:])))
            if not bws:
                continue
            slot = b.h / len(bws)
            step_tr = max(2, int((slot - 16.0) / (0.08 * k * v.TREE_BITS)))
            inst = next(it for it in model['insts'] if it.master == name)
            rx = model.get('b3r8_root_x', {}).get(inst.name, {})
            for q, p_ in enumerate(bws):
                # the face towards the word's root (a fragment in the far spine column takes words of both arrays)
                i = int(p_[2:])
                from_west = rx[i] < inst.cx if i in rx else west
                x = 0.2 if from_west else b.w - 0.6
                b.ports[p_] = ('area', b.ports[p_][1], x, slot * (q + 0.5), step_tr)
        return out
    v.masters = masters


def _slab_entry(v, obs_top=7, strip=0.0):
    """b3r15: a second horizontal entry layer into the band port/scale slabs (qfd_port_tiles_*); b3r12/b3r13 i50
    finals put every over-capacity M8 window in the gcell column at the W slab face because OBS M1-M7 left M8 the
    only entry layer.
    Option A (obs_top=5): the slab is implemented with M1-M5 only (proved on a port-group P&R), so M6/M7 are free
        over the whole slab; the block-word pins stay M8 area pins.
    Option B (strip > 0): a `strip` um wide channel inside the array-facing slab face keeps OBS M1-M5 only (the
        slab logic under it routes M1-M5); the block-word pins move to M6 inside that channel, 3 M6 tracks apart."""
    base_masters, base_rects, base_lef = v.masters, v.pin_rects, v.lef_text

    def masters(model, k=1, port_bits=None):
        out = base_masters(model, k, port_bits)
        for name, b in out.items():
            if not name.startswith('qfd_port_tiles'):
                continue
            b.obs_top = obs_top
            if strip:
                # the column decides the array-facing face (an edge-entry slab's bw pins sit across its width)
                xv = model['geo']['x_vch']
                west = next(it.x < xv for it in model['insts'] if it.master == name)
                b.m6_strip = (0.0, strip) if west else (b.w - strip, b.w)
                # edge-entry words (b3r10) share one y at the slab edge: stack them into the slab, 100 um apart
                yy = {}
                for p_, spec in b.ports.items():
                    if p_.startswith('bw') and spec[0] == 'area':
                        yy.setdefault(round(spec[3], 1), []).append(p_)
                b.m6_y = {}
                for y0, ps in yy.items():
                    if len(ps) == 1:
                        b.m6_y[ps[0]] = y0
                        continue
                    up = y0 < b.h / 2
                    for q, p_ in enumerate(sorted(ps, key=lambda z: int(z[2:]))):
                        d = 60.0 + 100.0 * q
                        b.m6_y[p_] = (y0 - 70.0 + d) if up else (y0 + 70.0 - d)
        return out

    def pin_rects(mst, k, wmap):
        rects = base_rects(mst, k, wmap)
        sx = getattr(mst, 'm6_strip', None)
        if not sx:
            return rects
        off, p = F.TRK['M6']
        step = p * k * 3
        hw = 0.016 * k
        out = []
        for nm, layer, r in rects:
            port = nm.split('[')[0]
            spec = mst.ports.get(port)
            if not (port.startswith('bw') and spec and spec[0] == 'area'):
                out.append((nm, layer, r))
                continue
            n = wmap.get(port, spec[1])
            i = int(nm.split('[')[1].rstrip(']'))
            yc = getattr(mst, 'm6_y', {}).get(port, spec[3])
            y = off * k + round((yc - n * step / 2 - off * k) / (p * k)) * p * k + i * step
            x0 = sx[0] + 0.25 * (sx[1] - sx[0])
            out.append((nm, 'M6', (x0, y - hw, x0 + 0.4 * k, y + hw)))
        return out

    def lef_text(mst, k, wmap):
        txt, n = base_lef(mst, k, wmap)
        sx = getattr(mst, 'm6_strip', None)
        if not sx:
            return txt, n
        head, tail = txt.split('  OBS\n', 1)
        L = ['  OBS']
        for i in range(1, mst.obs_top + 1):
            if i >= 6:
                for a, c in ((0.0, sx[0]), (sx[1], mst.w)):
                    if c - a > 1e-6:
                        L += [f'    LAYER M{i} ;', f'      RECT {a:.3f} 0 {c:.3f} {mst.h:.3f} ;']
            else:
                L += [f'    LAYER M{i} ;', f'      RECT 0 0 {mst.w:.3f} {mst.h:.3f} ;']
        L += ['  END', f'END {mst.name}', '']
        return head + '\n'.join(L), n
    v.masters, v.pin_rects, v.lef_text = masters, pin_rects, lef_text


# ------------------------------------------------------------------------------------------------ clock regions
def region_at(regs, cx, cy):
    """clock region of a point: the region whose rectangle contains it, else the one whose rectangle is NEAREST (edge
    distance).  qwendie-1011 textbook audit (class 1): the old nearest-CENTRE fallback put a channel relay / ROM group
    outside every rectangle into a region whose centre was nearer but whose rectangle was far (spine bands r97 / r98
    of r22ko4 grew to 6.6 / 6.3 mm sink spans against REGION_MAX_MM 5.25)."""
    def dist(r):
        a, b_, c, d = r['rect']
        return max(a - cx, 0.0, cx - c) + max(b_ - cy, 0.0, cy - d)
    return min(range(len(regs)), key=lambda k: (dist(regs[k]), k))


def _regions_from_placement(m):
    """qwendie-1011 textbook audit (class 1): re-derive every region clock net (clk_r<k>) from the final placement.
    The r18 pass assigns region clocks from the placement it sees; a later surgery (r22ko4 surgery_o4: seq_su,
    cbuf_g / crom_g groups, spine parts) moves blocks without moving their clock pin, so a block kept the clock of a
    region it no longer sits in (r22ko4: creg_spine_1 / _2 sink spans 6.6 / 6.3 mm vs REGION_MAX_MM 5.25).  Every
    sink pin is re-filed under region_at(its centre); the root keeps one pll_r<k> output per non-empty region."""
    regs = m['clock_regions']
    by = {i.name: i for i in m['insts']}
    keep, root, sinks = [], None, []
    for bus in m['buses']:
        bid, cl, bits, eps = bus
        if re.fullmatch(r'clk_r\d+', bid):
            for i, p in eps:
                if p.startswith('pll_r'):
                    root = root or i
                else:
                    sinks.append((i, p))
        else:
            keep.append(bus)
    if root is None:
        return
    per = {}
    for i, p in sinks:
        it = by[i]
        per.setdefault(region_at(regs, it.x + it.w / 2, it.y + it.h / 2), []).append((i, p))
    # a region whose MEASURED sink span exceeds REGION_MAX_MM (r22ko4 + near-square VM: band rectangles 5,264 um tall)
    # splits at the median of its long axis into two regions (a new root output each) until every span fits
    cap, split = REGION_MAX_MM * 1000, 0
    work = sorted(per)
    while work:
        k = work.pop()
        l = per[k]
        cx = [by[i].x + by[i].w / 2 for i, _ in l]
        cy = [by[i].y + by[i].h / 2 for i, _ in l]
        dx, dy = max(cx) - min(cx), max(cy) - min(cy)
        if max(dx, dy) <= cap or len(l) < 2:
            continue
        key = cx if dx >= dy else cy
        o = sorted(range(len(l)), key=lambda j: key[j])
        lo, hi = [l[j] for j in o[:len(o) // 2]], [l[j] for j in o[len(o) // 2:]]
        r0 = regs[k]
        a, b_, c, d = r0['rect']
        nk = len(regs)
        regs.append(dict(name=f"{r0['name']}_s{split}", kind=r0['kind'], rect=[a, b_, c, d], split_of=r0['name']))
        per[k], per[nk] = lo, hi
        split += 1
        for kk in (k, nk):        # the rectangle is shared: record the halves' measured extent
            xs_ = [by[i].x + by[i].w / 2 for i, _ in per[kk]]
            ys_ = [by[i].y + by[i].h / 2 for i, _ in per[kk]]
            ext = round(max(max(xs_) - min(xs_), max(ys_) - min(ys_)) / 1000, 4)
            regs[kk]['extent_mm'], regs[kk]['within_5p25'] = ext, ext <= REGION_MAX_MM + 1e-9
        work += [k, nk]
    moved = sum(1 for bus in m['buses'] if re.fullmatch(r'clk_r\d+', bus[0])
                for i, p in bus[3] if not p.startswith('pll_r')
                and f'clk_r{region_at(regs, by[i].x + by[i].w / 2, by[i].y + by[i].h / 2)}' != bus[0])
    m['buses'] = keep + [(f'clk_r{k}', 'clock_trunk', 1, [(root, f'pll_r{k}')] + per[k]) for k in sorted(per)]
    m['b3r2']['regions_from_placement'] = dict(sinks=len(sinks), refiled=moved, region_nets=len(per), split=split)


def region_spans(m):
    """measured sink span per region clock net (clk_r<k>: every pin but the hub's pll_r<k>), from the placement."""
    by = {i.name: i for i in m['insts']}
    out = {}
    for bid, cl, bits, eps in m['buses']:
        if not re.fullmatch(r'clk_r\d+', bid):
            continue
        pts = [by[i] for i, p in eps if i in by and not p.startswith('pll_')]
        if pts:
            xs = [i.x + i.w / 2 for i in pts]
            ys = [i.y + i.h / 2 for i in pts]
            out[bid] = dict(sinks=len(pts), span_um=[round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)])
    return out


def clock_regions(v, m):
    """Decision C regions: 4 x 4-tile blocks (with their corridors), spine bands, strip thirds, IO blocks."""
    g = m['geo']
    rows, colx = g['row_y'], m['col_x']
    R = []
    for c0 in range(0, v.COLS, 4):
        for r0 in range(0, v.ROWS, 4):
            x0 = colx(c0)
            x1 = colx(c0 + 3) + v.TILE_SLOT[0]
            y0, y1 = rows[r0], rows[r0 + 3] + v.TILE_SLOT[1]
            R.append(dict(name=f'creg_t{c0 // 4}_{r0 // 4}', kind='tile_block', rect=[x0, y0, x1, y1]))
    for b in range(BANDS):
        y0 = rows[4 * b] if b else g['y0']
        y1 = rows[4 * b + 3] + v.TILE_SLOT[1] if b < BANDS - 1 else g['y_top']
        R.append(dict(name=f'creg_spine_{b}', kind='spine_band', rect=[g['x_spine'], y0, g['x_arr_e'], y1]))
    for st, res in m['renges'].items():
        if not res:
            # r18: no row engines; the strip third = the CDC frames of that third of the stack (+ the concentrator)
            cds = m['cdcs'][st]
            n = len(cds)
            kv = m['lfifos'][st]
            for k in range(3):
                # the third's CDC frames and the same y-slice of the stack-tall KV concentrator (a 12 mm element:
                # it is three regions inside, meso FIFOs between its slices, AREA in its frame)
                parts = cds[k * n // 3:(k + 1) * n // 3]
                y0_, y1_ = min(i.y for i in parts), max(i.y + i.h for i in parts)
                R.append(dict(name=f'creg_strip_{st}_{k}', kind='strip', rect=[min([i.x for i in parts] + [kv.x]), y0_,
                         max([i.x + i.w for i in parts] + [kv.x + kv.w]), y1_]))
            continue
        for k in range(3):
            parts = res[2 * k:2 * k + 2] + ([m['lfifos'][st]] if k == 1 else [])
            if m.get('cdcs'):
                # r17: the CDC frames of the PCs this third's row engines serve (their core-side clock)
                n = len(m['cdcs'][st])
                parts = parts + [cd for p, cd in enumerate(m['cdcs'][st]) if p * len(res) // n in (2 * k, 2 * k + 1)]
            R.append(dict(name=f'creg_strip_{st}_{k}', kind='strip', rect=[min(i.x for i in parts), min(i.y for i in parts),
                     max(i.x + i.w for i in parts), max(i.y + i.h for i in parts)]))
    for name, it in m['io'].items():
        n = max(1, math.ceil(it.w / (REGION_MAX_MM * 1000)))
        for k in range(n):
            R.append(dict(name=f'creg_io_{name}_{k}', kind='io', rect=[it.x + it.w * k / n, it.y, it.x + it.w * (k + 1) / n,
                                                                       it.y + it.h]))
    for r in R:
        x0, y0, x1, y1 = r['rect']
        r['rect'] = [round(z, 3) for z in r['rect']]
        r['extent_mm'] = round(max(x1 - x0, y1 - y0) / 1000, 4)
        r['within_5p25'] = r['extent_mm'] <= REGION_MAX_MM + 1e-9
    return R


def fifo_accounting(v, m):
    st = sum(1 for i in m['insts'] if i.kind == 'station')
    sf = len(m['lfifos'])
    ext = m['b3r2']
    return dict(
        source=CLOCKING, mm2_per_bit=FIFO_MM2_PER_BIT,
        tile_tap=dict(count=st, bits_each=TAP_FIFO_BITS, mm2=round(st * TAP_FIFO_BITS * FIFO_MM2_PER_BIT, 4),
                      slot='inside the station frame (station height + extra, with the F2 storage)'),
        block_word=dict(count=PORT_GROUPS, bits_each=BW_FIFO_BITS, mm2=ext['bw_fifo_mm2'], slot='port_tiles slab area'),
        strip_return=dict(count=sf, bits_each=STRIP_FIFO_BITS, mm2=round(sf * STRIP_FIFO_BITS * FIFO_MM2_PER_BIT, 4),
                          slot='strip FIFO frame height'),
        total_mm2=round((st * TAP_FIFO_BITS + PORT_GROUPS * BW_FIFO_BITS + sf * STRIP_FIFO_BITS) * FIFO_MM2_PER_BIT, 4),
        f2_station_extra=dict(bits_each=F2_STATION_EXTRA_BITS, mm2=round(st * F2_STATION_EXTRA_BITS * FIFO_MM2_PER_BIT, 4)),
        station_frame_um=ext['station_frame_um'], station_frame_extra_h_um=ext['station_extra_h_um'],
        station_slot_mm2_added=round(st * v.CORR * ext['station_extra_h_um'] / 1e6, 4),
        head_frame_note='column heads share the station frame (64 x the same extra height: the head-side 2-deep F2 '
                        'column FIFO)')


def spine_cut(m, ys):
    """vertical bits crossing horizontal cuts inside the spine x range (2-pin legs, vertical run at the spine end)."""
    g = m['geo']
    by = {i.name: i for i in m['insts']}
    out = {}
    for y in ys:
        d = {}
        for bid, cl, bits, eps in m['buses']:
            if cl == 'tap':
                continue
            pts = [(by[i].cx, by[i].cy) for i, _ in eps]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if min(y0, y1) < y < max(y0, y1):
                    xv = x1 if g['x_spine'] <= x1 <= g['x_arr_e'] else x0
                    if g['x_spine'] <= xv <= g['x_arr_e']:
                        d[cl] = d.get(cl, 0) + bits
        out[str(round(y))] = dict(sorted(d.items()), total=sum(d.values()))
    return out


def latency(points=(0, 1)):
    """F2 exposed cost in the unified model: +1 cycle on every ME op's instruction path (beat 2 trails beat 1 by
    one cycle, cut-through per hop) when the instruction is not prefetched; 0 when the static schedule fills the
    2-deep column FIFO during the previous op.  qwen_tp_point(4, 6144, board, 1.2 GHz, me_lat_extra 167, SU64) is
    the probe the clocking decision used."""
    import uarch_model as u
    r = {}
    for e in points:
        p = u.qwen_tp_point(4, 6144, 'board', clock_hz=u.PRODUCT_CLOCK_HZ, me_lat_extra=167 + e, su_width=64)
        r[e] = dict(cycles=p['cycles'], tok_s_b1=p['tokens_s_b1'])
    d = r[1]['cycles'] - r[0]['cycles']
    return dict(probe='uarch_model.qwen_tp_point(4, 6144, "board", PRODUCT_CLOCK_HZ, me_lat_extra=167(+1), su_width=64)',
                unified_model_sha256=hashlib.sha256((ROOT / 'tools/uarch_model.py').read_bytes()).hexdigest(),
                base=r[0], plus_one=r[1], me_ops_on_token_path=d,
                exposed_no_prefetch=dict(cycles_per_token=d, us=round(d / 1.2e3, 4),
                                         rate_delta_pct=round(100 * (r[1]['tok_s_b1'] / r[0]['tok_s_b1'] - 1), 4)),
                exposed_static_prefetch=dict(cycles_per_token=0,
                                             why='instruction words are static program fields (go is a separate wire); '
                                                 'the sequencer streams op i+1 into the 2-deep column FIFO while op i '
                                                 'runs (every ME op occupies >= 2 cycles), so only beats issued after a '
                                                 'pipeline drain are exposed'),
                f1_reset=dict(cycles_per_token=0, why='reset is not on the token path; release takes <= 44 pipelined '
                                                      'hops once at power-on'),
                adopted_figure='bound +%d cycles/token (%.3f%%) until the RTL prefetch is measured' %
                               (d, -100 * (r[1]['tok_s_b1'] / r[0]['tok_s_b1'] - 1)))


def bword_stages(v, m, pitch=None):
    """Registered stages on each block word's path to the tree top: block root -> its slab (-> band primary when
    it lands on a fragment) -> tree top, rectilinear centre distance at the link stage pitch (430.56 um)."""
    pitch = pitch or v.LINK_STAGE_UM
    by = {i.name: i for i in m['insts']}
    d = lambda a, b: abs(by[a].cx - by[b].cx) + abs(by[a].cy - by[b].cy)
    prim, frag = {}, {}
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('pword_'):
            prim[eps[0][0]] = eps[1][0]
        if bid.startswith('pfrag_'):
            frag[eps[0][0]] = eps[1][0]
    per = []
    seg = {bid: eps for bid, cl, bits, eps in m['buses'] if bid.startswith(('bword_', 'bwseg_'))}
    for bid, cl, bits, eps in m['buses']:
        if not bid.startswith('bword_'):
            continue
        root, slab = eps[0][0], eps[1][0]
        legs = [(root, slab)]
        b, k = bid[len('bword_'):], 1
        while f'bwseg_{b}_{k}' in seg:          # r20f waypoint chain
            a_, z_ = seg[f'bwseg_{b}_{k}'][0][0], seg[f'bwseg_{b}_{k}'][1][0]
            legs.append((a_, z_))
            slab = z_
            k += 1
        if slab in frag:
            legs.append((slab, frag[slab]))
            slab = frag[slab]
        legs.append((slab, prim[slab]))
        per.append(sum(math.ceil(d(a, b) / pitch) for a, b in legs))
    return dict(pitch_um=pitch, words=len(per), max=max(per), mean=round(sum(per) / len(per), 2), min=min(per))


def latency_tws(stages):
    """Token cycles when the model's level-6 word -> spine-top term QWEN_WIRE_W12.tws (30) is replaced by the
    floorplan's worst block-word stage count: me_lat_extra = 167 + (stages - 30) in the clocking-decision probe."""
    import uarch_model as u
    tws = u.QWEN_WIRE_W12['tws']
    r = {}
    for e in (0, stages - tws):
        p = u.qwen_tp_point(4, 6144, 'board', clock_hz=u.PRODUCT_CLOCK_HZ, me_lat_extra=167 + e, su_width=64)
        r[e] = (p['cycles'], p['tokens_s_b1'])
    e = stages - tws
    return dict(model_term='tools/uarch_model.py QWEN_WIRE_W12["tws"]', model_tws=tws, floorplan_stages=stages,
                delta_stages_per_me_op=e, base_cycles=r[0][0], new_cycles=r[e][0], delta_cycles_per_token=r[e][0] - r[0][0],
                delta_us=round((r[e][0] - r[0][0]) / 1.2e3, 3), base_tok_s=r[0][1], new_tok_s=r[e][1],
                rate_delta_pct=round(100 * (r[e][1] / r[0][1] - 1), 3),
                probe='uarch_model.qwen_tp_point(4, 6144, "board", PRODUCT_CLOCK_HZ, me_lat_extra=167+delta, su_width=64)',
                unified_model_sha256=hashlib.sha256((ROOT / 'tools/uarch_model.py').read_bytes()).hexdigest(),
                instruction_for_model_owner='set QWEN_WIRE_W12["tws"] = floorplan_stages (me_lat_extra follows) and '
                                            're-run the Qwen ROM headline; bound until a routed path STA confirms the pitch')


def wire_bound_8k(v, m, comp='results/rtl/qwen_dspark_system_20261004/ctx8k/step_composed_ctx8k.json',
                  ar_job='results/rtl/qwen_dspark_system_20261004/ctx8k/k_AR0.json', routed=None):
    """The measured 8K token / DSpark step (REAL_MEM RTL, which already carries the RTL wire stages bd/nws/tws/ord of
    its build) with the die floorplan's measured wire-stage bounds added: worst block word (tws) minus the RTL's tws
    on every ME op, the hub<->stack link delta (2 traversals a layer pass), and the F2 two-beat +1 a ME op.  ME ops a
    layer pass and a head come from the unified model's +1 probe (217 = 36 x 6 + 1)."""
    C = json.loads((ROOT / comp).read_text())
    rtl = json.loads((ROOT / ar_job).read_text())['wire_stages']
    bw = bword_stages(v, m)
    ls = v.link_stages(m)
    f2 = latency()
    ops_tok = f2['me_ops_on_token_path']
    if (ops_tok - 1) % 36:
        raise SystemExit(f'ME ops a token {ops_tok} is not 36 x n + 1')
    ops_layer, ops_head = (ops_tok - 1) // 36, 1
    if routed is not None:
        # r17: stage counts from the die's global-route wire lengths (tools/qwen_rom_die_path_sta.py) instead of
        # the floorplan's rectilinear centre distances
        bw = dict(bw, max=routed['block_words']['stages_routed_max'], basis='GRT routed length (path_sta)',
                  floorplan_max=bw['max'])
        ls = dict(ls, delta_stages_at_430=routed['links']['stages_routed'] - ls['r2_model_total_stages'])
    d_tws = bw['max'] - rtl['tws']
    d_link = ls['delta_stages_at_430']
    per_layer = ops_layer * (d_tws + 1) + 2 * d_link
    per_head = ops_head * (d_tws + 1)
    cc = C['components_cycles']
    clk = C['clock_hz']
    # AR token: 36 layer passes + 1 head; DSpark step: verify 2 x 36 layer passes + 2 heads, drafter layer passes
    # (drafter_layers_rtl / one drafter layer) + S draft heads, commit (no ME op)
    nd = round(C['composed']['draft_terms']['drafter_layers_rtl'] / cc['drafter_layer_D0_S3'])
    s_heads = 3
    ar0 = C['composed']['ar_token_cycles']
    st0 = C['composed']['step_cycles']
    ar_pen = 36 * per_layer + per_head
    st_pen = 2 * 36 * per_layer + 2 * per_head + nd * per_layer + s_heads * per_head
    ar1, st1 = ar0 + ar_pen, st0 + st_pen
    tau = C['tau']
    return dict(schema='opentallas.qwen-rom-wire-bound-8k.v1', source=dict(composition=comp, ar_job=ar_job),
                rtl_wire_stages=rtl, floorplan_block_word_stages=bw, hub_stack=dict(
                    rtl_r2_entry_stages=ls['r2_model_total_stages'], floorplan_stages=ls['r2_model_total_stages'] + d_link,
                    delta=d_link, traversals_per_layer_pass=2),
                me_ops=dict(per_layer_pass=ops_layer, per_head=ops_head, per_ar_token=ops_tok),
                deltas=dict(tws_per_me_op=d_tws, two_beat_per_me_op=1, link_per_traversal=d_link,
                            per_layer_pass=per_layer, per_head=per_head),
                ar=dict(measured_cycles=ar0, penalty_cycles=ar_pen, bound_cycles=ar1,
                        measured_tok_s=round(clk / ar0, 1), bound_tok_s=round(clk / ar1, 1),
                        delta_pct=round(100 * (ar0 / ar1 - 1), 3)),
                dspark=dict(measured_step_cycles=st0, drafter_layer_passes=nd, draft_heads=s_heads,
                            penalty_cycles=st_pen, bound_step_cycles=st1, tau=tau,
                            measured_tok_s=round(tau * clk / st0, 1), bound_tok_s=round(tau * clk / st1, 1),
                            delta_pct=round(100 * (st0 / st1 - 1), 3)),
                basis='routed (GRT wire length per die net)' if routed is not None else 'floorplan geometry',
                status='bound: floorplan stage counts at the 430.56 um corridor-gate pitch (no routed-path STA); the '
                       'hub<->stack delta assumes the REAL_MEM measurement carries the r2 46-stage link; F2 bound '
                       'is 0 once the column-FIFO prefetch is measured')


def relay_token_cost(v, m, ar_job='results/rtl/qwen_dspark_system_20261004/ctx8k/k_AR0.json'):
    """Registered-stage counts of the die paths every ME op / layer pass waits on, from the die's buses (one register
    boundary per die hop: each element port is registered, r21 relays add hops), against the stages the measured
    token RTL carries (k_AR0 wire_stages): bd = x / instruction broadcast VM -> head chain -> corridor -> tap,
    tree = the in-block split tree (leaf t_out -> block root, all levels), tws = block word -> slab (-> primary) ->
    tree top, ord = tree-top result -> VM; link = hub <-> stack (two traversals a layer pass)."""
    st = m.get('r21_stage_of', {})
    S = lambda bid: st.get(bid, 1)
    B = {b[0]: b for b in m['buses']}
    # ---- bd
    head = {}
    # r9: the head row splits the columns and the rows in HALVES (64 x 24: 31 | 32 and 11 | 12, as before; tp8 48 x 16:
    # 23 | 24 and 7 | 8 -- the fixed 31 / 11 walked the E head chain into the W side's sum)
    hc, hr_ = v.COLS // 2, v.ROWS // 2
    bd_at = None
    for side, cols in (('W', range(hc - 1, -1, -1)), ('E', range(hc, v.COLS))):
        acc = 0
        for c in cols:
            acc += S(f'head_{c}')
            head[c] = acc
    bd = 0
    for c in range(v.COLS):
        acc_s, acc_n = head[c], head[c]
        for r in range(hr_ - 1, -1, -1):
            acc_s += S(f'cor_{c}_{r}')
            if acc_s + S(f'tap_{c}_{r}') > bd:
                bd, bd_at = acc_s + S(f'tap_{c}_{r}'), (c, r, head[c])
        for r in range(hr_, v.ROWS):
            acc_n += S(f'cor_{c}_{r}')
            if acc_n + S(f'tap_{c}_{r}') > bd:
                bd, bd_at = acc_n + S(f'tap_{c}_{r}'), (c, r, head[c])
    # ---- in-block tree: longest leaf -> root
    import re as _re
    tree = 0
    blocks = {}
    for bid in B:
        mm = _re.match(r'tree_(\d+)_(\d+)_(\d+)([ab])$', bid)
        if mm:
            blocks.setdefault(int(mm[1]), []).append(bid)
    for nb, legs in blocks.items():
        out_t = {}
        for bid in sorted(legs, key=lambda b: int(b.split('_')[2])):
            # the original 2-endpoint bus: source output -> host input (relayed buses keep their first hop name)
            src = B[bid][3][0]
            last = f'{bid}__r{S(bid) - 1}' if S(bid) > 1 else bid
            dst = B[last][3][1]
            t0 = out_t.get(src[0], 0) if src[1] == 'n_y' else 0
            out_t[dst[0]] = max(out_t.get(dst[0], 0), t0 + S(bid))
        tree = max(tree, max(out_t.values()))
    # ---- block words to the tree top
    prim, frag = {}, {}
    for bid, b in B.items():
        if bid.startswith('pword_'):
            source=b[3][0][0]
            if source not in prim or S(bid)>S(prim[source]):
                prim[source]=bid
        if bid.startswith('pfrag_'):
            frag[b[3][0][0]] = bid
    tws = 0
    for bid, b in B.items():
        if not _re.match(r'bword_\d+$', bid):
            continue
        last = f'{bid}__r{S(bid) - 1}' if S(bid) > 1 else bid
        slab = B[last][3][1][0]
        n = S(bid)
        if slab in frag:
            fb = frag[slab]
            n += S(fb)
            fl = f'{fb}__r{S(fb) - 1}' if S(fb) > 1 else fb
            slab = B[fl][3][1][0]
        n += S(prim[slab]) if slab in prim else 0     # tp8: no primary-slab word (the tree top is tt_ctlm: tt_c / tt_f)
        tws = max(tws, n)
    ordv = S('tt_res')
    # ---- hub <-> stack: the longest chain of link hops a traversal takes (hub -> leg -> corner -> channel -> FIFO)
    lk = {}
    for bid in B:
        mm = _re.match(r'lnk([vh])_(\d)(\w?)_?(\w+)$', bid)
    link_chains = {}
    for bid in B:
        if bid.startswith(('lnkv_', 'lnkh_')) and '__r' not in bid:
            si = bid[5]
            link_chains.setdefault(si, []).append(bid)
    link = 0
    for si, bids in link_chains.items():
        vs = sum(S(b) for b in bids if b.startswith('lnkv_'))
        hs = {}
        for b in bids:
            if b.startswith('lnkh_'):
                hs.setdefault(b[5:7], 0)
                hs[b[5:7]] += S(b)
        link = max(link, vs + max(hs.values() or [0]))
    rtl = json.loads((ROOT / ar_job).read_text())['wire_stages']
    try:
        ops, ops_src = latency()['me_ops_on_token_path'], 'latency()'
    except Exception as e:   # noqa: BLE001  (a build tree without the result files latency() reads)
        ops, ops_src = 217, f'217 = results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json (latency() unavailable: {type(e).__name__})'
    ls = v.link_stages(m)
    cur = dict(bd=bd, tree=tree, tws=tws, ord=ordv, link=link)
    base = dict(bd=rtl['bd'], tree=rtl['nws'] * 4, tws=rtl['tws'], ord=rtl['ord'], link=ls['r2_model_total_stages'])
    d_op = sum(cur[k] - base[k] for k in ('bd', 'tree', 'tws', 'ord'))
    d_link = cur['link'] - base['link']
    per_token = ops * d_op + 2 * 36 * d_link
    return dict(schema='opentallas.qwen-rom-relay-token-cost.v1', stages_r21=cur, stages_rtl=base,
                bd_worst_tile=dict(col=bd_at[0], row=bd_at[1], head_stages=bd_at[2], head_roots={f'head_{c}': S(f'head_{c}') for c in (hc - 1, hc)}) if bd_at else None,
                me_ops_per_ar_token=ops, me_ops_source=ops_src, delta_per_me_op=d_op, delta_link_per_traversal=d_link,
                cycles_per_ar_token=per_token,
                basis='one register boundary per die hop (element ports registered); r21 relays add hops; the measured '
                      'token RTL carries the base stages (k_AR0 wire_stages bd / nws x 4 levels / tws / ord, r2 link)')


def write_def_regions(v, m, path):
    v.write_def_floorplan(m, path)
    txt = Path(path).read_text()
    head, rest = txt.split('REGIONS ', 1)
    n, rest2 = rest.split(' ;', 1)
    regs = [f'- {r["name"]} ( {round(r["rect"][0] * 1000)} {round(r["rect"][1] * 1000)} ) ( {round(r["rect"][2] * 1000)} '
            f'{round(r["rect"][3] * 1000)} ) + TYPE GUIDE ;' for r in m['clock_regions']]
    txt = head + f'REGIONS {int(n) + len(regs)} ;' + rest2.replace('END REGIONS', '\n'.join(regs) + '\nEND REGIONS', 1)
    Path(path).write_text(txt)


def record(v, m):
    die = m['die']
    by_kind = {}
    for r in m['clock_regions']:
        e = by_kind.setdefault(r['kind'], dict(count=0, max_extent_mm=0, over_5p25=[]))
        e['count'] += 1
        e['max_extent_mm'] = max(e['max_extent_mm'], r['extent_mm'])
        if not r['within_5p25']:
            e['over_5p25'].append(r['name'])
    # qwendie-1011 (textbook class 1): the MEASURED sink span of every region clock net, not only the rectangle's
    spans = region_spans(m)
    span_max = max((max(s['span_um']) for s in spans.values()), default=0.0)
    return dict(schema=SCHEMA, tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                b2_generator_sha256=F.sha('tools/qwen_rom_fulldie.py'), b3_selection_sha256=F.sha('tools/qwen_rom_fulldie_b3.py'),
                die=die, vch_um=v.VCH, corridor_bits=v.CORRIDOR_BITS, tap_bits=v.TAP_BITS, band_repack=m['b3r2']['band'],
                instances=len(m['insts']), isa_bits=m['isa_bits'],
                group_map={k: v_ for k, v_ in m['b3r2']['groups'].items() if k in ('primary', 'overflow_groups', 'overflow_slab')},
                spine_parts=m['geo'].get('spine_parts_band') or m['geo']['spine_parts'],
                fifo=fifo_accounting(v, m), clock_regions_summary=by_kind, clock_regions=m['clock_regions'],
                region_sink_spans=spans, region_sink_span_max_mm=round(span_max / 1000, 4),
                regions_over_5p25_measured=sorted(k for k, s in spans.items() if max(s['span_um']) > REGION_MAX_MM * 1000),
                spine_vertical_cut_bits=spine_cut(m, [3000, 8800, 12000, 18000, 25000]),
                link_stages=v.link_stages(m), bword_stages=bword_stages(v, m),
                **({'tp8_reset_tree': m['tp8_reset_tree']} if m.get('tp8_reset_tree') else {}))


GCELL_OVER_TCL = r"""
# every gcell whose usage exceeds its capacity (per-gcell, not windowed)
set out [open /work/gcell_over.txt w]
foreach ln {M4 M5 M6 M7 M8 M9} {
  set layer [$tech findLayer $ln]
  for {set j 0} {$j < $ny} {incr j} {
    for {set i 0} {$i < $nx} {incr i} {
      set c [$grid getCapacity $layer $i $j]; set u [$grid getUsage $layer $i $j]
      if {$u > $c} { puts $out "$ln [lindex $gx $i] [lindex $gy $j] $c $u" }
    }
  }
}
close $out
"""


def summarize(work):
    """Per-layer GRT overflow (final congestion report) and 4x4-gcell window use/capacity (gcell_usage.txt:
    `L <layer> <row> cap/use ...`, capacity first)."""
    import gzip
    work = Path(work)
    log = (work / 'run.log').read_text(errors='replace')
    i = log.rfind('Final congestion report')
    layers = {}
    if i >= 0:
        for ln in log[i:].splitlines()[3:14]:
            f = ln.split()
            if len(f) >= 9 and (f[0].startswith('M') or f[0] == 'Total'):
                layers[f[0]] = dict(resource=int(f[1]), demand=int(f[2]), usage_pct=float(f[3].rstrip('%')),
                                    max_h=int(f[4]), max_v=int(f[6]), overflow=int(f[8]))
    gp = work / 'gcell_usage.txt'
    op = gzip.open if not gp.exists() else open
    gp = gp if gp.exists() else work / 'gcell_usage.txt.gz'
    gx = gy = None
    win = {}
    with op(gp, 'rt') as fh:
        for ln in fh:
            if ln.startswith('GRIDX'):
                gx = [int(x) for x in ln.split()[1].split(',')]
                continue
            if ln.startswith('GRIDY'):
                gy = [int(x) for x in ln.split()[1].split(',')]
                continue
            f = ln.split()
            layer, row = f[1], int(f[2])
            e = win.setdefault(layer, dict(windows=0, over=0, zero_cap_used=0, max_ratio=0.0, at=None, over_xy=[]))
            for ci, cu in enumerate(f[3:]):
                cap, use = (float(z) for z in cu.split('/'))
                e['windows'] += 1
                if cap == 0:
                    e['zero_cap_used'] += use > 0
                    continue
                r = use / cap
                if r > 1:
                    e['over'] += 1
                    e['over_xy'].append((gx[4 * ci] / 1000, gy[row] / 1000))
                if r > e['max_ratio']:
                    e['max_ratio'], e['at'] = r, [gx[4 * ci] / 1000, gy[row] / 1000]
    for e in win.values():
        xy = e.pop('over_xy')
        e['max_ratio'] = round(e['max_ratio'], 4)
        if xy:
            e['over_bbox_um'] = [min(x for x, _ in xy), min(y for _, y in xy), max(x for x, _ in xy), max(y for _, y in xy)]
    ex = (work / 'run.log.exit').read_text().strip() if (work / 'run.log.exit').exists() else None
    t = re.search(r'OT_TIME grt_s=(\d+)', log)
    rss = re.search(r'Maximum resident set size \(kbytes\): (\d+)', log)
    return dict(case=work.name, exit=ex, grt_s=int(t.group(1)) if t else None,
                peak_rss_gb=round(int(rss.group(1)) / 2**20, 1) if rss else None, layers=layers, windows=win)


def native_stdcell_pg_lines(grid='core'):
    """Literal row rails and a connected sparse ladder for die-top cells.

    Hardened macro obstructions clip this stdcell grid; macro PG remains on
    its own qualified interfaces. Literal M1 contact and all upper connects
    are checked after pdngen, not inferred from global_connect.
    """
    lines=[f'add_pdn_stripe -grid {grid} -layer M1 -width .018 -followpins',
           f'add_pdn_stripe -grid {grid} -layer M2 -width .018 -followpins']
    for layer,width,pitch,spacing,offset in (
            ('M3',.09,4.32,2.07,1.08),('M4',.12,4.32,2.04,1.08),
            ('M5',.12,8.64,4.20,2.16),('M6',.160,8.64,4.160,2.16),
            ('M7',.160,8.64,4.160,2.16)):
        lines.append(f'add_pdn_stripe -grid {grid} -layer {layer} -width {width} -pitch {pitch} -spacing {spacing} -offset {offset} -extend_to_boundary')
    lines += [f'add_pdn_connect -grid {grid} -layers {{M{i} M{i+1}}}' for i in range(1,8)]
    return lines


def write_pdn_r4(v, m, path, bump_um):
    """Connected full-die PDN (r4).  r2 (one M8+M9 macro grid per instance) passed pdngen but failed
    check_power_grid: each macro grid stops inside its instance, the frames abut with a 24 nm gap, so every
    element is an M9 island (b3r2b_pdn run_pdn_r2.log PSM-0038/0039/0069; reproduced on four abutting elements).
    r4: one die-level core grid of M8 + M9 stripes over everything at the tile-field bump-aligned pitch (the
    abstracts obstruct only M1-M7), plus per-instance M8 macro grids over the boundary on the same die-aligned
    lattice, connecting the elements' M7 rails to M8
    and M8 to the core M9; the HBM PHY's M4 rails reach M8 through an M5 macro grid (PHY OBS is M1-M4).
    Verified PASS on the four-element and PHY fixtures (check_power_grid VDD/VSS)."""
    def aligned(coverage, vp=bump_um):
        raw = v.dn(0.48 / coverage, 0.160)
        n = math.ceil(vp / raw - 1e-9)
        n += (n % 2 == 0)
        return round(vp / n, 3)
    cp = aligned(F.REGION_PG['tile_field'])
    L = ['# r4 full-die PDN: die core grid M8/M9 + per-instance M8 macro grids over the boundary',
         'add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power',
         'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground',
         'global_connect', 'set_voltage_domain -name CORE -power VDD -ground VSS',
         'define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND',
         f'add_pdn_stripe -grid core -layer M8 -width .48 -pitch {cp:.3f} -offset 0',
         f'add_pdn_stripe -grid core -layer M9 -width .48 -pitch {cp:.3f} -offset 0',
         'add_pdn_connect -grid core -layers {M8 M9}']
    L += native_stdcell_pg_lines('core')
    meta = []
    insts = sorted(m['insts'], key=lambda it: -len(it.name))      # -instances is a pattern: longest name first
    for i, it in enumerate(insts):
        if min(it.w, it.h) < 3.0:
            continue              # r9: no macro grid for a cell without rails of its own (reset-tree repeaters)
        g = f'pg_{i}'
        L.append(f'define_pdn_grid -macro -instances {{{it.name}}} -voltage_domains CORE -name {g} -starts_with GROUND '
                 '-grid_over_boundary')
        if it.master == 'ot_hbm3e_phy':
            L += [f'add_pdn_stripe -grid {g} -layer M5 -width .504 -pitch {cp:.3f} -offset {(-it.x) % cp:.3f}',
                  f'add_pdn_connect -grid {g} -layers {{M4 M5}}', f'add_pdn_connect -grid {g} -layers {{M5 M8}}']
            meta.append(dict(instance=it.name, layer='M5', pitch=cp))
            continue
        region = v.region_at(m, it.cx, it.cy)
        cov = F.REGION_PG.get(region) or F.REGION_PG['tile_field']
        # one M8 lattice everywhere: a macro stripe at another pitch would overlap core stripes of the other net
        # (shorts) and a core-less M9-only variant failed the fixture; region coverages are qualified by the PSM
        # window cases, this run qualifies connectivity
        p = cp
        L += [f'add_pdn_stripe -grid {g} -layer M8 -width .48 -pitch {p:.3f} -offset {(-it.y) % p:.3f}',
              f'add_pdn_connect -grid {g} -layers {{M7 M8}}', f'add_pdn_connect -grid {g} -layers {{M8 M9}}']
        meta.append(dict(instance=it.name, region=region, layer='M8', pitch=p, coverage_request=cov))
    Path(path).write_text('\n'.join(L) + '\n')
    return dict(core_pitch_um=cp, grids=len(meta), meta=meta)


def write_pdn_r5(v, m, path, bump_um):
    """r5 = r4 stripes/connects with unambiguous grid ownership.  pdngen `-instances` is a Tcl regexp over every
    instance name (pdn::get_insts), so r4's bare names claimed several instances each (sp_port_tiles_0 matched
    sp_port_tiles_0_f1, s_1_1 matched s_1_10; >1000 PDN-0182 on b3r2b).  r5 anchors every name (^name$) and puts all
    instances whose stripe offset to the die lattice is equal into one grid (pdngen builds one instance grid per
    matched instance, offsets stay instance-relative), so ~3,200 grids become a few dozen and no instance is matched
    by two grids."""
    r4 = write_pdn_r4(v, m, path, bump_um)
    cp = r4['core_pitch_um']
    raw_lines = Path(path).read_text().splitlines()
    # Keep all core commands, including literal stdcell rails/upconnects.
    # A fixed nine-line prefix silently dropped any new core-PG commands.
    first_macro = next((j for j,line in enumerate(raw_lines) if line.startswith('define_pdn_grid -macro')), len(raw_lines))
    head = raw_lines[:first_macro]
    head[0] = '# r5 full-die PDN: r4 grids, anchored instance patterns, one macro grid per stripe phase'
    byname = {it.name: it for it in m['insts']}
    groups = {}
    for e in r4['meta']:
        it = byname[e['instance']]
        if not re.fullmatch(r'[A-Za-z0-9_]+', it.name):
            raise ValueError(f'instance name needs escaping: {it.name}')
        key = ('M5', round((-it.x) % cp, 3)) if e['layer'] == 'M5' else ('M8', round((-it.y) % cp, 3))
        groups.setdefault(key, []).append(it.name)
    L = list(head)
    for j, ((layer, off), names) in enumerate(sorted(groups.items())):
        g = f'pg_{layer.lower()}_{j}'
        pats = ' '.join(f'^{n}$' for n in sorted(names))
        L.append(f'define_pdn_grid -macro -instances {{{pats}}} -voltage_domains CORE -name {g} -starts_with GROUND '
                 '-grid_over_boundary')
        if layer == 'M5':
            L += [f'add_pdn_stripe -grid {g} -layer M5 -width .504 -pitch {cp:.3f} -offset {off:.3f}',
                  f'add_pdn_connect -grid {g} -layers {{M4 M5}}', f'add_pdn_connect -grid {g} -layers {{M5 M8}}']
        else:
            L += [f'add_pdn_stripe -grid {g} -layer M8 -width .48 -pitch {cp:.3f} -offset {off:.3f}',
                  f'add_pdn_connect -grid {g} -layers {{M7 M8}}', f'add_pdn_connect -grid {g} -layers {{M8 M9}}']
    Path(path).write_text('\n'.join(L) + '\n')
    return dict(core_pitch_um=cp, grids=len(groups), instances=len(r4['meta']), meta=r4['meta'])


def case_pdn(v, m, work, bump_um, rev='r4'):
    """Real-technology die (legality, track assert, pin access) with power abstracts (VDD/VSS M7 + M8 rails on every
    element, tools/qwen_rom_fulldie_pg_r3.powered_lef) and the connected r4 full-die pdn.tcl (write_pdn_r4);
    run_pdn.tcl runs pdngen + check_power_grid."""
    man = v.case_real(m, work)
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    parts = []
    # r5: the power abstracts take the selected module's pin geometry (tree-column / edge-entry pin_rects live on v,
    # PG.powered_lef reads F, which raised on the b3r7+ 6-field pin specs); r4 keeps its F geometry byte-identical
    pg_f = PG.F
    if rev == 'r5':
        PG.F = v
    try:
        for name, mst in M.items():
            wm_ = {q: pw.get((name, q), 0) for q in mst.order}
            if min(mst.w, mst.h) < 3.0:
                # r9: a cell too small for its own rails (the reset-tree repeater, 5.184 x 2.16) is die-top standard-cell
                # logic: no power abstract, no macro grid (it is powered by the die's std-cell rails when it is placed)
                text, _ = v.lef_text(mst, 1, wm_)
            else:
                text, _ = PG.powered_lef(mst, 1, wm_)
            parts.append(text)
    finally:
        PG.F = pg_f
    (work / 'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(parts) +
                                       'END LIBRARY\n')
    _gate_track_lattice(work / 'elements.lef', m)
    meta = (write_pdn_r5 if rev == 'r5' else write_pdn_r4)(v, m, work / 'pdn.tcl', bump_um)['meta']
    (work / 'run_pdn.tcl').write_text("""# full-die PDN with macro grids on the placed floorplan
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\\s+(\\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
read_db /work/floorplan.odb
mem read
set t0 [clock seconds]
if {[catch {source /work/pdn.tcl; pdngen; source /work/die_constant_pg_check.tcl} err]} { puts "OT_PDN FAIL $err"; error $err } else {
  set nsw 0; foreach net [[ord::get_db_block] getNets] { foreach sw [$net getSWires] { incr nsw [llength [$sw getWires]] } }
  puts "OT_PDN PASS special_shapes=$nsw" }
puts "OT_TIME pdn_s=[expr {[clock seconds]-$t0}]"
mem pdn
foreach net {VDD VSS} { if {[catch {check_power_grid -net $net} err]} { puts "OT_PGCHECK $net FAIL $err"; error $err } else { puts "OT_PGCHECK $net PASS" } }
mem check
write_db /work/floorplan_pdn.odb
""")
    man.update(case='a_pdn', bump_um=bump_um, macro_grids=len(meta), producer=__file__, die=m['die'],
               **({'pdn_rev': rev} if rev != 'r4' else {}),
               execution_order=['run.tcl', 'run_pdn.tcl'])
    (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    return man


def _cdc_arg(t):
    """--cdc W,H[,N[,HB,CB]]: the per-PC CDC frame.  Port bits from the RTL port list of ot_qwen_stream4_cdc_pc
    (TAGW 9): HCLK side h_lv 1 + h_lsec 17 + h_lrow 8 + h_ldata 256 + h_cred 3 + h_wv 1 + h_wsec 24 + h_hand 1 + h_wcon 1
    + h_cv 1 + h_csec 24 + h_cdata 256 + h_ctag 9 + h_av 1 + h_atag 9 + h_fault 1 = 613; core side l_v 1 + l_sec 17 +
    l_row 8 + l_data 256 + l_pop 1 + w_v 1 + w_sec 24 + w_data 256 + w_tag 9 + w_room 1 + wd_v 1 + wd_tag 9 + c_fault 1 = 585."""
    if not t:
        return None
    f = [float(x) for x in t.split(',')]
    return dict(w=f[0], h=f[1], per_stack=int(f[2]) if len(f) > 2 else 32,
                hbm_bits=int(f[3]) if len(f) > 3 else 613, core_bits=int(f[4]) if len(f) > 4 else 585)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['plan', 'grt', 'real', 'pdn', 'ir', 'latency', 'summary', 'wire8k', 'relaycost'])
    ap.add_argument('--window', default='tile_field')
    ap.add_argument('--vdd-pitch', type=float, default=63.64,
                    help='per-net bump pitch: 63.64 = 45 um array, every core bump power (the IR PASS cases ir_*_align_b45)')
    ap.add_argument('--enable-b3r2', action='store_true')
    ap.add_argument('--band', action='store_true', help='band-local port/scale slabs')
    ap.add_argument('--area-pins', action='store_true', help='spine slab ports as M8 area pins')
    ap.add_argument('--b3r3', action='store_true', help='b3r3 spine: +0.5 mm, scale in port slab, crom beside SU64')
    ap.add_argument('--widen-um', type=float, default=500.0)
    ap.add_argument('--spread', action='store_true', help='b3r4: hub north link on the E face, block-word pins spread')
    ap.add_argument('--b3r6', action='store_true', help='b3r6 = b3r5 + band-slab block words actually spread (master '
                    'name fix), channel buses face-to-face inside the blocks\' overlap, tree-top pins at 2 tracks')
    ap.add_argument('--tree-cols', type=int, default=0, help='b3r7: tile tree-word pins in this many gcell columns')
    ap.add_argument('--bw-align', action='store_true', help='b3r8: slab block-word pins at their block-root height')
    ap.add_argument('--bw-edge', action='store_true', help='b3r10: words of a slab whose roots lie outside it enter '
                    'at the near edge, spread over the slab width')
    ap.add_argument('--bw-edge-inner', action='store_true', help='b3r12: edge-entry words climb inside the slab')
    ap.add_argument('--io-faces', action='store_true', help='b3r11: collective->SerDes word on the E/W faces')
    ap.add_argument('--native-coll', action='store_true', help='sys-takeover: full-width sequencer <-> collective '
                    '(548-b forward, 518-b return through io_xfifo NCOLL); default the 66-b descriptor word')
    ap.add_argument('--bw-sp', type=float, default=100.0, help='b3r13: root-row block-word pin spacing in a slab (um)')
    ap.add_argument('--bw-x', type=float, default=20.0, help='b3r13: block-word pin column distance from the slab face (um)')
    ap.add_argument('--edge-gap', type=float, default=0.0, help='b3r14: routing gap (um) between each tile array and '
                    'its facing spine slab column; the die grows by two gaps')
    ap.add_argument('--slab-obs-top', type=int, default=7, help='b3r15 option A: band port/scale slab OBS top layer '
                    '(5 = slab routed M1-M5, M6/M7 free over it)')
    ap.add_argument('--m6-strip', type=float, default=0.0, help='b3r15 option B: width (um) of an OBS-M1-M5 entry '
                    'channel inside the array-facing slab face; block-word pins on M6 in it')
    ap.add_argument('--slab-group-h', type=float, default=0.0, help='r17: band slab = 8 routed port-group elements of '
                    'this height (um; 455.76 / 570.24 closed routes) + 8 block-word FIFOs; 0 = b3r16 area-derived slab')
    ap.add_argument('--slab-pg', type=float, default=None, help='r17: M8/M9 PG coverage per net over the band slabs '
                    '(default: the tile-field coverage)')
    ap.add_argument('--slab-w-per-mm2', type=float, default=0.646, help='r17: band-slab power density (measured r6d)')
    ap.add_argument('--r19', action='store_true', help='r19: r18 + full tiles with KV slices and the per-row landing '
                    'fabric from per-stack landing crossbars (KV reconciliation)')
    ap.add_argument('--su-core-clock', action='store_true', help='r20g: SU64/SFU and the vector memory on the 1.2 GHz core '
                    'clock (as the measured token RTL)')
    ap.add_argument('--bw-wp', type=int, default=0, help='r20f: block-word waypoint every N tile columns (0: off)')
    ap.add_argument('--ir-guard', type=float, default=0.0, help='r21: IR window guard band (um) of continuing grid / bumps')
    ap.add_argument('--relay-pitch', type=float, default=0.0, help='r21: relay registers on every die wire > 350 um '
                    'at this pitch (um; 0: off)')
    ap.add_argument('--slab-bw-m8', action='store_true', help='r21: band-slab block-word pins on M8 at the array face, '
                    'one word per port-group slot (seam fix)')
    ap.add_argument('--io-chan', type=float, default=0.0, help='r22: routing channel (um, on 2.16) between the top tile '
                    'row and the IO band; the die grows by it')
    ap.add_argument('--rtl-finish', action='store_true', help='r21f: tree-top / VM / embedding-root / re-cut '
                    'sequencer + SU abstracts from the finished RTL (qwen-rtl-finish)')
    ap.add_argument('--su-vm-abut', action='store_true', help='r21v: SU64 <-> VM bus (14,592 b) as abutted M5 pins '
                    '(SU64 N face on the VM S face), no stations')
    ap.add_argument('--corr-um', type=float, default=None, help='r20e: corridor width (um, on 0.432)')
    ap.add_argument('--corr-m9-adj', type=float, default=None, help='r20d: GRT M9 adjustment over the corridors')
    ap.add_argument('--tree-interleave', action='store_true', help='r20: tree-word pin sub-columns interleaved across '
                    'the tile body')
    ap.add_argument('--r18', action='store_true', help='r18: die-top lint Q1-Q14 (no row engines, CDC clusters, clock '
                    'nets, role variants)')
    ap.add_argument('--strip-span', action='store_true', help='r17d: strip/CDC/controller PG regions per stack span')
    ap.add_argument('--routed', type=Path, help='wire8k: path_sta record (routed stage counts) instead of geometry')
    ap.add_argument('--inst-density', action='append', default=[],
                    help='r17 ir: MASTER_PREFIX=W_PER_MM2 measured element power density over the instance (repeatable)')
    ap.add_argument('--cdc', default='', help='r17 STREAM4 CDC column: W,H[,per_stack[,hbm_bits,core_bits]] of the '
                    'routed ot_qwen_stream4_cdc_pc frame (um); empty = b3r16 shoreline')
    ap.add_argument('--east-mirror', action='store_true', help='b3r9: east-array block trees mirrored (root spine-side)')
    ap.add_argument('--pdn-rev', default='r4', choices=['r4', 'r5'], help='pdn mode: r5 = anchored, phase-grouped '
                    'macro grids (no PDN-0182 grid-ownership conflicts)')
    ap.add_argument('--work', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--iters', type=int, default=5)
    ap.add_argument('--tag', default='b3r2')
    ap.add_argument('--recipe', default=None, help='die_top_lint Qwen recipe (e.g. r21b): selects the die from the '
                    'recipe dict (incl. vm_me / tt_h / bl_h, which have no flag) instead of the per-feature flags')
    a = ap.parse_args(argv)
    global NATIVE_COLL
    NATIVE_COLL = bool(a.native_coll)
    if a.mode == 'summary':
        print(json.dumps(summarize(a.work), indent=1))
        return 0
    if a.mode == 'latency':
        print(json.dumps(latency(), indent=1))
        return 0
    if a.recipe:
        import die_top_lint as DTL
        r = dict(DTL.QWEN_RECIPES[a.recipe])
        cdc = r.pop('cdc')
        v, m = selected(True, cdc=_cdc_arg(cdc), **r)
    else:
        v, m = selected(a.enable_b3r2, band=a.band, area_pins=a.area_pins, b3r3=a.b3r3, widen_um=a.widen_um, spread=a.spread,
                        b3r6=a.b3r6, tree_cols=a.tree_cols,
                        bw_align=a.bw_align, east_mirror=a.east_mirror, bw_edge=a.bw_edge,
                        io_faces=a.io_faces, bw_edge_inner=a.bw_edge_inner, bw_sp=a.bw_sp, bw_x=a.bw_x,
                        edge_gap=a.edge_gap, slab_obs_top=a.slab_obs_top, m6_strip=a.m6_strip,
                        slab_group_h=a.slab_group_h, cdc=_cdc_arg(a.cdc),
                        slab_pg=a.slab_pg, slab_w_per_mm2=a.slab_w_per_mm2, strip_span=a.strip_span, r18=a.r18,
                        r19=a.r19, tree_interleave=a.tree_interleave, corr_m9_adj=a.corr_m9_adj, corr_um=a.corr_um, bw_wp=a.bw_wp, su_core_clock=a.su_core_clock, slab_bw_m8=a.slab_bw_m8, relay_pitch=a.relay_pitch, io_chan=a.io_chan, su_vm_abut=a.su_vm_abut, rtl_finish=a.rtl_finish)
    if a.mode == 'relaycost':
        rec = dict(relay_token_cost(v, m), relays=m.get('r21_relays'))
        if a.out:
            a.out.write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps({k: rec[k] for k in ('stages_r21', 'stages_rtl', 'delta_per_me_op', 'delta_link_per_traversal',
                                              'cycles_per_ar_token')}, indent=1))
        return 0
    if a.mode == 'wire8k':
        rec = wire_bound_8k(v, m, routed=json.loads(a.routed.read_text()) if a.routed else None)
        if a.out:
            a.out.write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps(dict(ar=rec['ar'], dspark=rec['dspark'], deltas=rec['deltas']), indent=1))
        return 0
    if a.mode == 'plan':
        out = a.out
        out.mkdir(parents=True, exist_ok=True)
        rec = record(v, m)
        (out / 'plan.json').write_text(json.dumps(rec, indent=1) + '\n')
        write_def_regions(v, m, out / 'floorplan.def')
        v.svg(m, out / 'floorplan.svg')
        print(json.dumps(dict(die=rec['die'], fifo=rec['fifo']['total_mm2'], regions=rec['clock_regions_summary'],
                              cut=rec['spine_vertical_cut_bits']), indent=1))
        return 0
    work = a.work.resolve()
    if work.exists() and any(work.iterdir()):
        raise SystemExit('refuse existing output')
    if a.mode == 'grt':
        if a.r18:
            # clock / reset / forwarded-clock nets are built by CTS / the reset tree on reserved shielded tracks, not
            # by the signal router: a 1-bit net is one k-bundled wire (16 tracks), so 150 region / link clock nets
            # converging on the hub root read as ~2,400 tracks there (r18e i5: M9 1.35 around the hub)
            # reset-tree 2026-10-13: with the registered reset tree (m['tp8_reset_tree']) every reset net is an
            # ordinary registered <= 500 um signal hop between repeaters: it is ROUTED like data, only clocks are CTS's
            rt = (m.get('tp8_reset_tree') or {}).get('cells')
            m = dict(m, buses=[b for b in m['buses'] if b[1] not in (('clock_trunk',) if rt else ('clock_trunk', 'reset'))])
        man = v.case_grt(m, work, a.k, a.tag, a.iters)
        (work / 'run.tcl').write_text((work / 'run.tcl').read_text().replace('mem done', GCELL_OVER_TCL + 'mem done'))
        man.update(b3r2=record(v, m), producer=__file__)
        (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
        print(json.dumps({k: man[k] for k in ('tag', 'instances', 'bundle_pins', 'bundle_nets', 'wires')}))
    elif a.mode == 'ir':
        v.INST_W_PER_MM2 = {kv.split('=')[0]: float(kv.split('=')[1]) for kv in a.inst_density}
        # the IR PASS recipe of the b2 floorplan (cases ir_*_align_b45): bump-aligned straps, every core bump power
        man = v.case_ir(m, work, a.window, align=True, vdd_pitch=a.vdd_pitch, guard=a.ir_guard)
        man['b3r2'] = dict(producer=__file__, band=a.band, die=m['die'])
        (work / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
        print(json.dumps({k: man[k] for k in ('window', 'power_w', 'bump_sites')}))
    elif a.mode == 'pdn':
        print(json.dumps(case_pdn(v, m, work, a.vdd_pitch, a.pdn_rev)))
    else:
        man = v.case_real(m, work)
        print(json.dumps(man))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
