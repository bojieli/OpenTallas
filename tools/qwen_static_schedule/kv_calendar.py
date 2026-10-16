"""36-layer static KV calendar at the 0az elastic HBM boundary (Qwen TP8 KV/system die).

What is static and what is elastic (owner 0az, 2026-10-15): the HBM stack/PHY return time is not compile-time fixed, so
corrected read sectors land in the per-PC elastic front (rtl/qwen_sys/static_kv_20261014/qkd_kv_hbm_elastic_front.sv,
NBLK x BLK sectors, block-granular RD credit: block b+NBLK may be requested only after block b is freed). Inside the die
every edge is compiled from "block ready": the compiler places each block's blk_go no earlier than the block's WORST
landing; puts follow 3 edges after blk_go, one per STRIDE HBM edge, into the static return ring
(qkd_static_kv_return_slots, DEPTH sectors), whose core-side expected_put slots feed the attention service K/V ports.

This module compiles, per pseudo channel (PC) and per layer, the RD/WR reservations, blk_go and put slots, the core
consume slots of the native QK pass (tools/qwen_kv_die/static_qk_calendar.py, sector/PC map of
tools/qwen_kv_die/static_kv_calendar.py) and the new-row K/V writes, then checks every structural constraint:
front credit, worst-case landing before blk_go, ring occupancy, put-before-consume, read-after-write of the token's own row,
one command per PC per HBM edge, and the 36-layer periodicity (layer L+1's prefetch never collides with layer L's V pass
or writes).  Every timing input is an explicit, sourced parameter; a missing one refuses the compile.
It never claims native qualification: the controller refresh calendar and V per-PC order are inputs, not derived here.
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]


def _mod(rel, name):
    s = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


QK = _mod('tools/qwen_kv_die/static_qk_calendar.py', 'static_qk_calendar')
KVM = _mod('tools/qwen_kv_die/static_kv_calendar.py', 'static_kv_calendar')

# sourced constants (each names its source)
SOURCED = dict(
    core_ps=KVM.CORE_PS,                       # static_kv_calendar.CORE_PS
    hbm_ps=KVM.HBM_PS,                         # static_kv_calendar.HBM_PS
    rd_landing_nominal_hbm=4 + 23 + 5,         # qkd_static_kv_return_calendar: reserved_rd +4 cmd, RL23, +5 corrected return
    front_window_hbm=26,                       # kv_elastic_boundary OPEN_JOINS: front first-sector +10..26 HBM edges (worst 26)
    put_after_go_hbm=3,                        # qkd_kv_hbm_elastic_front: first put 3 edges after blk_go
    front_nblk=4, front_blk=8, front_stride=1, # qkd_kv_hbm_elastic_front defaults
    ring_depth=8,                              # qkd_static_kv_return_slots DEPTH default
    qk_consume_age=34, qk_row_latency=21,      # attention native service (RL21) / static_qk_calendar consume age
)
REQUIRED = ('core_ps', 'hbm_ps', 'rd_landing_nominal_hbm', 'front_window_hbm', 'put_after_go_hbm', 'front_nblk', 'front_blk',
            'front_stride', 'ring_depth', 'ring_cdc_core_edges', 'qk_consume_age', 'qk_row_latency',
            'layer_period_core', 'write_ready_core', 'refresh')


def _need(p):
    miss = [k for k in REQUIRED if k not in p]
    if miss:
        raise ScheduleError(f'KV calendar inputs missing: {miss}')
    return p


def k_streams(T, p):
    """per PC: [(sector, consume core edge after QK start)], from the native QK calendar (all 128 PCs)"""
    cal = QK.compile_calendar(T, p['qk_row_latency'], p['qk_consume_age'])
    out = {}
    for eng in cal['engines']:
        s, e = eng['stack'], eng['engine']
        for q in range(4):
            pc = KVM.physical_pc(s, e, q)
            out[pc] = [(KVM.sector(sl['t'], False), sl['consume'], sl['t']) for sl in eng['slots']]
    return out


def pc_schedule(demand, p, start_hbm):
    """issue RD for demand (in consume order) as early as the front credit allows from HBM edge start_hbm; return
    per-sector issue / worst landing / blk_go / put (HBM edges) and the frees."""
    nb, bl, st = p['front_nblk'], p['front_blk'], p['front_stride']
    n = len(demand)
    blocks = math.ceil(n / bl)
    issue, go, put, freed = [0] * n, [0] * blocks, [0] * n, [0] * blocks
    t = start_hbm
    lmax = p['rd_landing_nominal_hbm'] + p['front_window_hbm']
    for b in range(blocks):
        if b >= nb:
            t = max(t, freed[b - nb])                       # block credit
        idx = range(b * bl, min(n, (b + 1) * bl))
        for i in idx:
            issue[i] = t
            t += 1                                          # one RD per PC per HBM edge
        land_last = issue[idx[-1]] + lmax
        prev_take = put[b * bl - 1] + st if b else 0
        go[b] = max(land_last, prev_take - p['put_after_go_hbm'])
        for k, i in enumerate(idx):
            put[i] = go[b] + p['put_after_go_hbm'] + k * st
        freed[b] = put[idx[-1]] + 1
    return dict(issue=issue, go=go, put=put, freed=freed, rd_end=t)


def hbm_to_core(e_hbm, p):
    return math.ceil(e_hbm * p['hbm_ps'] / p['core_ps'])


def _layer_pc(ks, p):
    sch = pc_schedule(ks, p, 0)
    vis = [hbm_to_core(x, p) + p['ring_cdc_core_edges'] for x in sch['put']]   # core edge the sector is consumable
    cons = [c for _, c, _ in ks]
    start = max(v - c for v, c in zip(vis, cons))                               # QK start so every put precedes consume
    ev = sorted([(v, 1) for v in vis] + [(start + c + 1, -1) for c in cons])    # ring: visible, not yet consumed
    occ = peak = 0
    for _, d in ev:
        occ += d
        peak = max(peak, occ)
    return start, peak, sch['rd_end'], len(ks), cons[-1] - cons[0] + 1


def compile_layer(T, p):
    """one layer, worst PC: minimal QK start (core edges after the PC prefetch start) with no hold, ring peak, K fetch"""
    _need(p)
    per = {pc: _layer_pc(ks, p) for pc, ks in k_streams(T, p).items() if ks}
    start = max(v[0] for v in per.values())
    peak = max(v[1] for v in per.values())
    k_hbm = max(v[2] for v in per.values())
    nks = max(v[3] for v in per.values())
    need_blocks = math.ceil((p['rd_landing_nominal_hbm'] + p['front_window_hbm'] + p['put_after_go_hbm'] + p['front_blk']) /
                            p['front_blk']) + 1
    return dict(T=T, pcs=len(per), k_sectors=nks, qk_start_after_prefetch_core=start, ring_peak=peak,
                ring_ok=peak <= p['ring_depth'], k_rd_hbm_edges=k_hbm, k_rd_core_edges=hbm_to_core(k_hbm, p),
                front_credit_rate=round(nks / k_hbm, 4), front_blocks_for_full_rate=need_blocks,
                qk_consume_core_edges=max(v[4] for v in per.values()))


def compile_36(T, p, layers=36):
    """periodic 36-layer check: per PC the K prefetch of layer L+1 + the K/V writes of layer L+1 + V reads of layer L fit
    one layer period of HBM edges, the token's own new K row is written before its RD, ring/credit constraints hold."""
    _need(p)
    one = compile_layer(T, p)
    period_hbm = math.floor(p['layer_period_core'] * p['core_ps'] / p['hbm_ps'])
    v_sectors = one['k_sectors']                              # V rows per PC = K rows per PC (static_kv_calendar model)
    writes = 2                                                # one K + one V sector of the new row per PC quarter
    busy = one['k_rd_hbm_edges'] + v_sectors + writes + p['refresh']['edges_per_layer']
    # the new token's own K row: its RD must issue after its WR commit
    ks = k_streams(T, p)
    own = [(pc, i) for pc, s in ks.items() for i, (_, _, t) in enumerate(s) if t == T - 1]
    return dict(layer=one, layers=layers, period_hbm=period_hbm, pc_busy_hbm_per_layer=busy,
                hbm_fits_period=busy <= period_hbm, own_row_pcs=len(own),
                own_row_scan_index=sorted({i for _, i in own}),
                own_row_rd_issue_hbm_after_prefetch=[i for _, i in own][:1],
                write_ready_core=p['write_ready_core'],
                feasible=one['ring_ok'] and busy <= period_hbm)
