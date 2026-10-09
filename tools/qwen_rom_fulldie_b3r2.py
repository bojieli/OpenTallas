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


def selected(enabled=False, band=False, area_pins=False, b3r3=False, widen_um=500.0, spread=False, b3r6=False,
             tree_cols=0, bw_align=False, east_mirror=False, bw_edge=False, io_faces=False,
             bw_edge_inner=False, bw_sp=100.0, bw_x=20.0, edge_gap=0.0, slab_obs_top=7, m6_strip=0.0,
             slab_group_h=0.0, cdc=None, slab_pg=None, slab_w_per_mm2=0.646, strip_span=False, r18=False, r19=False,
             tree_interleave=False, corr_m9_adj=None, corr_um=None, bw_wp=0, su_core_clock=False, slab_bw_m8=False, relay_pitch=0.0, io_chan=0.0,
             su_vm_abut=False, rtl_finish=False, vm_me=False, tt_h=0.0, bl_h=0.0, strict_ports=False, rtl_bound_masters=None, port_exemptions=None):
    if not enabled:
        raise ValueError('b3r2 selection is default off')
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
    v.REGION_PG = {r: (.48 / PG.bump_pitch(c, 90) if c else 0.) for r, c in F.REGION_PG.items()}
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
        v.TILE_BODY_W = v.KV_TILE_W - v.CORR
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
    if relay_pitch:
        _io_south(v)
        _relays(v, m, relay_pitch)
    m['b3r2']['r21_relay_pitch_um'] = relay_pitch
    if su_vm_abut:
        # outermost: after the relays (an abutted bus takes no relay); r21m: the banked memory's descriptor ports
        _su_vm_bus(v, m, *((SU_VM_A_BITS_BV, SU_VM_Q_BITS) if vm_me else (SU_VM_A_BITS, SU_VM_Q_BITS)))
    m['b3r2']['r21v_su_vm_abut'] = su_vm_abut
    return v, m


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
    gap = vm.y - (su.y + su.h)
    if abs(su.x - vm.x) > 1e-6 or abs(su.w - vm.w) > 1e-6 or not (0.0 <= gap <= SU_VM_ABUT_TOL_UM) \
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
        for M_, f, mine in ((s, 'N', ('va', 'vq')), (q, 'S', ('sa', 'sq'))):
            for pn in mine:                 # the base wrapper's default pin group for the new bus: replaced here
                if pn in M_.ports:
                    M_.ports.pop(pn)
                    M_.order.remove(pn)
            taken = [pn for pn, sp in M_.ports.items() if sp[0] == 'face' and sp[2] == f]
            if taken:
                raise ValueError(f'su_vm_abut: {M_.name} {f} face already holds {taken}')
        s.face('va', SU_VM_A_BITS, 'N', 'M5', a_c, 1)
        s.face('vq', SU_VM_Q_BITS, 'N', 'M5', q_c, 1)
        q.face('sa', SU_VM_A_BITS, 'S', 'M5', a_c, 1)
        q.face('sq', SU_VM_Q_BITS, 'S', 'M5', q_c, 1)
        return out
    v.masters = masters
    m['r21v_su_vm'] = dict(bits_su_to_vm=SU_VM_A_BITS, bits_vm_to_su=SU_VM_Q_BITS, gap_um=round(gap, 4),
                           face_um=round(w, 3), layer='M5', pitch_tracks=1,
                           a_span_um=[round(a_c - a_span / 2, 3), round(a_c + a_span / 2, 3)],
                           q_span_um=[round(q_c - q_span / 2, 3), round(q_c + q_span / 2, 3)],
                           stations=0, rtl_latency_added=0)


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
    for b in range(6):
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
        for b in range(6):
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
        for b in range(6):
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
    tgt = [(rows[4 * b] + rows[4 * b + 3] + v.TILE_SLOT[1]) / 2 for b in range(BANDS)]
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
        for mn, port, centre in (('qfd_io_xfifo', 'o_serdes_tx', 300.0), ('qfd_io_xfifo', 'i_serdes_rx', 360.0),
                                 ('qfd_io_serdes', 'c', 30.0), ('qfd_io_serdes', 'r', 90.0),
                                 ('qfd_io_embedding_rom', 'o', None), ('qfd_io_embedding_rom', 'a', -1.0)):
            M = o.get(mn)
            if M is None or port not in M.ports:
                continue
            bits = M.ports[port][1]
            c = centre if centre is not None else M.w - 20.0 - bits * 0.048
            if centre == -1.0:
                c = M.w - 60.0 - M.ports['o'][1] * 0.048 - 40.0     # beside the word, west of it
            mx = any(it.master == mn and it.orient in ('MX', 'R180') for it in model['insts'])
            M.ports[port] = ('face', bits, 'N' if mx else 'S', 'M5', c, 1)
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
                                  '+ ot_qfd_emb_pcport.sv',
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
RELAY_SKIP = ('clock_trunk', 'reset', 'tap', 'kv_land', 'cdc_core', 'hbm_cdc', 'phy_dfi')
RELAY_V_H = 30.24      # relay frame height with N/S faces only (vertical run): 512 flops + clock leaf, M1-M3
RELAY_MAX_UM = 350.0   # owner fast rule 2026-10-06: every die wire > ~350 um gets relay registers ...
RELAY_PITCH_UM = 300.0  # ... at a conservative ~300 um pitch


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
    import bisect
    RMAX = max(RELAY_MAX_UM, pitch)   # a wire is relayed only when longer than the relay pitch
    pos = _pin_pos(v, m)
    by = {i.name: i for i in m['insts']}
    g = m['geo']
    COLS = v.COLS
    cx_list = [m['col_x'](c) + v.TILE_BODY_W + v.CORR / 2 for c in range(COLS)]
    corr_x0 = [m['col_x'](c) + v.TILE_BODY_W for c in range(COLS)]
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
                if in_field(x0 + w / 2, y0 + h / 2) and corr_of(x0 + w / 2) is None:
                    continue           # never over a tile body
                if free((x0, y0, x0 + w, y0 + h)):
                    return x0, y0
        return None

    corr_used = {}

    def load(c, ya, yb):
        ya, yb = sorted((ya, yb))
        yb = max(yb, ya + 1.0)
        return sum(max(0.0, min(b_, yb) - max(a_, ya)) for a_, b_ in corr_used.get(c, ())) / (yb - ya)

    def poly_of(cl, P0, P1):
        f0, f1 = in_field(*P0), in_field(*P1)
        if cl == 'corridor' or (abs(P0[0] - P1[0]) < 1.0):
            return [P0, P1]
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
        return [P0, (P0[0], P1[1]), P1]

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
        for k, r in enumerate(regs):
            a, b_, c, d = r['rect']
            if a <= cx <= c and b_ <= cy <= d:
                return k
        return min(range(len(regs)), key=lambda k: abs((regs[k]['rect'][0] + regs[k]['rect'][2]) / 2 - cx)
                   + abs((regs[k]['rect'][1] + regs[k]['rect'][3]) / 2 - cy))
    ck_add = {}
    stats, B, fck_drop, fck_new, insts, worst, spill = {}, [], set(), [], [], [], []
    stage_of = {}
    order = {'corridor': 0, 'link_spine': 1, 'link_channel': 1, 'tree_spine': 2, 'tree_block': 3}
    buses = sorted(enumerate(m['buses']), key=lambda t: (order.get(t[1][1], 3), t[0]))
    keep = {}
    def relay_frame(bits, cl):
        """off-corridor relay frame: faces at one track; <= 512 b fits the 52.68 x 30.24 corridor relay, wider words
        take the face span (a link-spine relay is vertical flow only, N/S faces)."""
        span1 = bits * 0.048 + 4.0
        if bits <= 512:
            return v.CORR - v.SHAVE, RELAY_V_H - v.SHAVE
        w = max(v.up(span1, v.GX), v.CORR) - v.SHAVE
        if cl == 'link_spine' and span1 > BWP_H:
            return w, RELAY_V_H - v.SHAVE
        return w, max(v.up(span1, v.GY), BWP_H) - v.SHAVE

    plans = {}
    for idx, (bid, cl, bits, eps) in buses:
        if cl in RELAY_SKIP or len(eps) != 2:
            keep[idx] = [(bid, cl, bits, eps)]
            continue
        P0, P1 = pos(*eps[0]), pos(*eps[1])
        d = abs(P0[0] - P1[0]) + abs(P0[1] - P1[1])
        if d <= RMAX:
            keep[idx] = [(bid, cl, bits, eps)]
            continue
        path = poly_of(cl, P0, P1)
        cands, L = candidates(path)
        span1 = bits * 0.048 + 4.0
        span2 = bits * 0.096 + 4.0

        def frame(c, bits=bits, span1=span1, span2=span2):
            if c[3] is not None:       # corridor lane: full corridor width, faces at 1 track up to 512 b
                if bits <= 512:
                    return v.CORR - v.SHAVE, RELAY_V_H - v.SHAVE
                return v.CORR - v.SHAVE, max(v.up(min(span2, max(span1, BWP_H)), v.GY), BWP_H) - v.SHAVE
            return relay_frame(bits, cl)

        def _try(c, tol):
            w, h = frame(c)
            sp = place(c[1], c[2], w + v.SHAVE, h + v.SHAVE, c[3], tol)
            return None if sp is None else (sp[0], sp[1], w, h)
        frames, s_last, ycur = [], 0.0, None
        while L - s_last > pitch:
            reach = [c for c in cands if s_last + 1.0 < c[0] <= s_last + pitch]
            if not reach:
                nxt = [c for c in cands if c[0] > s_last + 1.0]
                if not nxt:
                    break
                reach = nxt[:1]
            if ycur is not None:      # a horizontal run keeps the height of its previous relay (no zig-zag)
                reach = [(c[0], c[1], ycur, c[3], c[4]) if c[4] == 'h' and abs(ycur - c[2]) < 400.0 else c
                         for c in reach]
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
            ycur = y0 + h / 2 if got[0][4] == 'h' else None
            s_last = got[0][0]
        plans[idx] = dict(bid=bid, cl=cl, bits=bits, eps=eps, P0=P0, P1=P1, frames=frames, d=d)

    def hops_of(pl):
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        return [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
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

    def sites(w, h):
        """lower-left corners where a w x h relay frame fits: every corridor slot (32.4 um steps) and a 21.6 um grid
        over the free area outside the tile arrays."""
        key = (round(w, 3), round(h, 3))
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
                if in_field(x0 + w / 2, y0 + h / 2) and y0 + h <= die_top + 1.0:
                    continue
                if free0((x0, y0, x0 + w, y0 + h)):
                    pts.append((x0, y0))
        arr = np.array(pts) if pts else np.zeros((0, 2))
        site_cache[key] = (arr, cKDTree(arr + np.array([w / 2, h / 2])) if len(arr) else None)
        return site_cache[key]

    repaired, unrepaired = [], []
    for idx, pl in sorted(plans.items()):
        hs = hops_of(pl)
        if max(hs) <= RMAX + 25.0:
            continue
        bits = pl['bits']
        w, h = relay_frame(bits, pl['cl'])
        W, H = w + v.SHAVE, h + v.SHAVE
        arr, tree = sites(W, H)
        if tree is None:
            unrepaired.append(pl['bid'])
            continue
        # free the bus's own pass-1 relays for its search
        own = [(f[0], f[1], f[0] + f[2] + v.SHAVE, f[1] + f[3] + v.SHAVE) for f in pl['frames']]
        for r_ in own:
            for gx in range(int(r_[0] // BK), int(r_[2] // BK) + 1):
                for gy in range(int(r_[1] // BK), int(r_[3] // BK) + 1):
                    lst = grid.get((gx, gy), [])
                    if r_ in lst:
                        lst.remove(r_)
        D = RMAX - max(W, H) / 2 + 26.0
        P0, P1 = pl['P0'], pl['P1']
        ctr = arr + np.array([W / 2, H / 2])
        ok_cache = {}

        def ok(i):
            if i not in ok_cache:
                x0, y0 = arr[i]
                ok_cache[i] = free((x0, y0, x0 + W, y0 + H))
            return ok_cache[i]
        def bfs(De):
            start = [i for i in tree.query_ball_point(P0, De, p=1) if ok(i)]
            par = {i: -1 for i in start}
            front, hit = start, None
            while front and hit is None and len(par) < 400000:
                for i in front:
                    if abs(ctr[i][0] - P1[0]) + abs(ctr[i][1] - P1[1]) <= De:
                        hit = i
                        break
                if hit is not None:
                    break
                nxt = []
                for i, nb in zip(front, tree.query_ball_point(ctr[front], D, p=1)):
                    for j in nb:
                        if j not in par and ok(j):
                            par[j] = i
                            nxt.append(j)
                nxt.sort(key=lambda j: abs(ctr[j][0] - P1[0]) + abs(ctr[j][1] - P1[1]))
                front = nxt[:4000]
            return hit, par, start
        hit, par, start = bfs(D)
        if hit is None:
            # end hops only: the measured closing span (430.56 um, corridor gate +11.9 ps at SS) when the pin's
            # neighbourhood is full
            hit, par, start = bfs(430.0 - max(W, H) / 2)
        if hit is None:
            unrepaired.append(f"{pl['bid']} (start {len(start)}, visited {len(par)}, sites {len(arr)}, D {D:.0f})")
            for r_ in own:
                add_rect(r_)
            continue
        chain = [hit]
        while par[chain[-1]] != -1:
            chain.append(par[chain[-1]])
        chain = chain[::-1]
        frames = []
        for i in chain:
            x0, y0 = arr[i]
            r_ = (x0, y0, x0 + W, y0 + H)
            if not free(r_):
                break
            add_rect(r_)
            frames.append((float(x0), float(y0), w, h))
        if len(frames) != len(chain):
            for f in frames:
                pass
            unrepaired.append(pl['bid'] + ' (self-overlap)')
        old = len(pl['frames'])
        pl['frames'] = frames
        repaired.append((pl['bid'], old, len(frames), round(max(hops_of(pl)), 1)))
    # ---- emit relays and hops
    for idx, pl in sorted(plans.items()):
        bid, cl, bits, eps = pl['bid'], pl['cl'], pl['bits'], pl['eps']
        link = cl in ('link_spine', 'link_channel')
        dom = next((by[x].domain for x, _ in eps if by[x].domain != 'cdc'), 'stream_1p2')
        pts = [pl['P0']] + [(f[0] + f[2] / 2, f[1] + f[3] / 2) for f in pl['frames']] + [pl['P1']]
        prev, hops = eps[0], []
        for k, (x0, y0, w, h) in enumerate(pl['frames']):
            here = pts[k + 1]

            def face(o):
                dx, dy = o[0] - here[0], o[1] - here[1]
                if abs(dx) >= abs(dy):
                    return 'E' if dx > 0 else 'W'
                return 'N' if dy > 0 else 'S'
            fi, fo = face(pts[k]), face(pts[k + 2])
            if fi == fo:
                # both neighbours on one side: the output takes the other axis toward its peer
                dx, dy = pts[k + 2][0] - here[0], pts[k + 2][1] - here[1]
                if fi in 'NS':
                    fo = 'E' if dx >= 0 else 'W'
                else:
                    fo = 'N' if dy >= 0 else 'S'
            mn = f'qfd_rly{"f" if link else ""}_{bits}_{fi}{fo}_{round(w)}x{round(h)}'
            masters_needed[mn] = (bits, fi, fo, w, h, link)
            nm = f'rly_{bid}_{k}'
            ccx, ccy = x0 + w / 2, y0 + h / 2
            reg = 'corridor' if corr_of(ccx) is not None and in_field(ccx, ccy) else next(
                (r_['kind'] for r_ in m['regions'] if r_['rect'][0] <= ccx <= r_['rect'][2]
                 and r_['rect'][1] <= ccy <= r_['rect'][3] and r_['kind'] != 'tile_field'), 'hub')
            insts.append(v.Inst(nm, mn, x0, y0, w, h, kind='relay', region=reg, domain=dom))
            by[nm] = insts[-1]
            hop = bid if k == 0 else f'{bid}__r{k}'
            hops.append((hop, cl, bits, [prev, (nm, 'a')]))
            if link:
                fck_new.append((f'fck_{hop}', 'clock_trunk', 1, [(prev[0], f'fck_{prev[1]}'), (nm, 'fck_a')]))
            elif dom == 'stream_1p2':
                ck_add.setdefault(f'clk_r{region_of(ccx, ccy)}', []).append((nm, 'ck'))
            else:
                ck_add.setdefault({'serial_0p9': 'clk_serial', 'link_serdes': 'clk_serdes',
                                   'link_ucie': 'clk_ucie'}.get(dom, f'clk_{dom}'), []).append((nm, 'ck'))
            prev = (nm, 'b')
        n = len(pl['frames'])
        last = bid if not n else f'{bid}__r{n}'
        hops.append((last, cl, bits, [prev, eps[1]]))
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
    missing = sorted(ck_add)
    m['buses'] = B + fck_new
    m['r21_stage_of'] = stage_of
    # achieved hop lengths (pin-centre Manhattan, relay pins at the frame faces)
    m['r21_relays'] = dict(pitch_um=pitch, max_um=RMAX, relays=len(insts), masters=len(masters_needed),
                          classes=stats, clock_nets_missing=missing, repaired=len(repaired),
                          repaired_examples=repaired[:20], unrepaired=unrepaired,
                          relay_flop_bits=sum(s['relay_bits'] for s in stats.values()),
                          relay_area_mm2=round(sum(i.w * i.h for i in insts) / 1e6, 3))
    base = v.masters

    def masters(model, k=1, port_bits=None):
        o = base(model, k, port_bits)
        for mn, (bits, fi, fo, w, h, link) in masters_needed.items():
            M = v.Master(mn, w, h, 3, f'die relay: one registered {bits}-b hop (ot_qwen_die_station TAP=0 family), '
                         f'standard cells M1-M3, in {fi} out {fo}')
            for port, f in (('a', fi), ('b', fo)):
                along = w if f in 'NS' else h
                pitch_tr = 2 if bits * 0.096 + 2.0 <= along else 1
                M.face(port, bits, f, 'M5' if f in 'NS' else 'M4', along / 2, pitch_tr)
            if link:
                M.area('fck_a', 1, w / 2 - 0.8, h / 2, 1)
                M.area('fck_b', 1, w / 2 + 0.8, h / 2, 1)
            else:
                M.area('ck', 1, w / 2, h / 2, 1)
            o[mn] = M
        return o
    v.masters = masters
    return m['r21_relays']


def _pin_pos(v, m):
    """(inst, port) -> die position of the port's pin centroid (instance orientation applied)."""
    M = v.masters(m, 1)
    pw = v.port_widths(m, 1)
    cen = {}
    for name, mst in M.items():
        acc = {}
        for nm, layer, r in v.pin_rects(mst, 1, {q: pw.get((name, q), 0) for q in mst.order}):
            a = acc.setdefault(nm.split('[')[0], [0.0, 0.0, 0])
            a[0] += (r[0] + r[2]) / 2
            a[1] += (r[1] + r[3]) / 2
            a[2] += 1
        cen[name] = {p: (a[0] / a[2], a[1] / a[2]) for p, a in acc.items()}
    by = {i.name: i for i in m['insts']}

    def pos(inst, port):
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
        cx, cy = it.x + it.w / 2, it.y + it.h / 2
        for k, r in enumerate(regs):
            a, b_, c, d = r['rect']
            if a <= cx <= c and b_ <= cy <= d:
                return k
        return min(range(len(regs)), key=lambda k: abs((regs[k]['rect'][0] + regs[k]['rect'][2]) / 2 - cx)
                   + abs((regs[k]['rect'][1] + regs[k]['rect'][3]) / 2 - cy))
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


R18_CK = ('ck', 'ckx', 'cks', 'cku', 'ckd', 'clk', 'hclk', 'crst', 'hrst', 'rst_n', 'h_arst_n', 'c_arst_n')


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
        out['qfd_io_xfifo'] = v.Master('qfd_io_xfifo', iox.w, iox.h, 3, 'IO-band CDC cluster: sequencer -> collective '
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
        for X in (iox,):
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
                    if mn in mirrored_x:
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
                    M.area(pn, 1, min(M.w - 1.0, max(1.0, M.w / 2 + ((j % 12) - 6) * 1.6)),
                           min(M.h - 1.0, max(1.0, M.h / 2 + (j // 12) * 1.6)), 1)
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
    tgt = [(rows[4 * b] + rows[4 * b + 3] + v.TILE_SLOT[1]) / 2 for b in range(BANDS)]
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
    tgt = [(rows[4 * b] + rows[4 * b + 3] + v.TILE_SLOT[1]) / 2 for b in range(BANDS)]
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
    B.append(('seq_coll', 'sequencer', 64 + 2, [(seq, 'cd'), ('io_collective', 'sd')]))
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
    for side, cols in (('W', range(31, -1, -1)), ('E', range(32, v.COLS))):
        acc = 0
        for c in cols:
            acc += S(f'head_{c}')
            head[c] = acc
    bd = 0
    for c in range(v.COLS):
        acc_s, acc_n = head[c], head[c]
        for r in range(11, -1, -1):
            acc_s += S(f'cor_{c}_{r}')
            bd = max(bd, acc_s + S(f'tap_{c}_{r}'))
        for r in range(12, v.ROWS):
            acc_n += S(f'cor_{c}_{r}')
            bd = max(bd, acc_n + S(f'tap_{c}_{r}'))
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
            prim[b[3][0][0]] = bid
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
        n += S(prim[slab])
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
    f2 = latency()
    ops = f2['me_ops_on_token_path']
    ls = v.link_stages(m)
    cur = dict(bd=bd, tree=tree, tws=tws, ord=ordv, link=link)
    base = dict(bd=rtl['bd'], tree=rtl['nws'] * 4, tws=rtl['tws'], ord=rtl['ord'], link=ls['r2_model_total_stages'])
    d_op = sum(cur[k] - base[k] for k in ('bd', 'tree', 'tws', 'ord'))
    d_link = cur['link'] - base['link']
    per_token = ops * d_op + 2 * 36 * d_link
    return dict(schema='opentallas.qwen-rom-relay-token-cost.v1', stages_r21=cur, stages_rtl=base,
                me_ops_per_ar_token=ops, delta_per_me_op=d_op, delta_link_per_traversal=d_link,
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
    return dict(schema=SCHEMA, tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                b2_generator_sha256=F.sha('tools/qwen_rom_fulldie.py'), b3_selection_sha256=F.sha('tools/qwen_rom_fulldie_b3.py'),
                die=die, vch_um=v.VCH, corridor_bits=v.CORRIDOR_BITS, tap_bits=v.TAP_BITS, band_repack=m['b3r2']['band'],
                instances=len(m['insts']), isa_bits=m['isa_bits'],
                group_map={k: v_ for k, v_ in m['b3r2']['groups'].items() if k in ('primary', 'overflow_groups', 'overflow_slab')},
                spine_parts=m['geo'].get('spine_parts_band') or m['geo']['spine_parts'],
                fifo=fifo_accounting(v, m), clock_regions_summary=by_kind, clock_regions=m['clock_regions'],
                spine_vertical_cut_bits=spine_cut(m, [3000, 8800, 12000, 18000, 25000]),
                link_stages=v.link_stages(m), bword_stages=bword_stages(v, m))


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
    meta = []
    insts = sorted(m['insts'], key=lambda it: -len(it.name))      # -instances is a pattern: longest name first
    for i, it in enumerate(insts):
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
    head = Path(path).read_text().split('\n')[:9]
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
            text, _ = PG.powered_lef(mst, 1, {q: pw.get((name, q), 0) for q in mst.order})
            parts.append(text)
    finally:
        PG.F = pg_f
    (work / 'elements.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(parts) +
                                       'END LIBRARY\n')
    meta = (write_pdn_r5 if rev == 'r5' else write_pdn_r4)(v, m, work / 'pdn.tcl', bump_um)['meta']
    (work / 'run_pdn.tcl').write_text("""# full-die PDN with macro grids on the placed floorplan
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\\s+(\\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
read_db /work/floorplan.odb
mem read
set t0 [clock seconds]
if {[catch {source /work/pdn.tcl; pdngen} err]} { puts "OT_PDN FAIL $err" } else {
  set nsw 0; foreach net [[ord::get_db_block] getNets] { foreach sw [$net getSWires] { incr nsw [llength [$sw getWires]] } }
  puts "OT_PDN PASS special_shapes=$nsw" }
puts "OT_TIME pdn_s=[expr {[clock seconds]-$t0}]"
mem pdn
foreach net {VDD VSS} { if {[catch {check_power_grid -net $net} err]} { puts "OT_PGCHECK $net FAIL $err" } else { puts "OT_PGCHECK $net PASS" } }
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
            m = dict(m, buses=[b for b in m['buses'] if b[1] not in ('clock_trunk', 'reset')])
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
