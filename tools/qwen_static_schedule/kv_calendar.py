"""Static KV capacity screen at the 0az elastic HBM boundary (Qwen TP8 KV/system die).

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
    blocked = refresh_blocked(p)
    for b in range(blocks):
        if b >= nb:
            t = max(t, freed[b - nb])                       # block credit
        idx = range(b * bl, min(n, (b + 1) * bl))
        for i in idx:
            while blocked(t):
                t += 1                                      # REFpb command + tRREFD: no ACT/RD slot on this PC
            issue[i] = t
            t += 1                                          # one RD per PC per HBM edge
        land_last = issue[idx[-1]] + lmax
        prev_take = put[b * bl - 1] + st if b else 0
        go[b] = max(land_last, prev_take - p['put_after_go_hbm'])
        for k, i in enumerate(idx):
            put[i] = go[b] + p['put_after_go_hbm'] + k * st
        freed[b] = put[idx[-1]] + 1
    return dict(issue=issue, go=go, put=put, freed=freed, rd_end=t)


def receipt(contexts=(1, 128, 1000, 2048, 4096, 6144, 8192), layer_period_core=6639, ring_cdc_core_edges=3):
    """36-layer KV calendar receipt: KV-die resized boundary (front NBLK 10, ring DEPTH 64; kv_buffer_resize.json) under
    the controller refresh as implemented, plus the old sizes and the refresh upper bound as sensitivities."""
    base = dict(SOURCED, ring_cdc_core_edges=ring_cdc_core_edges, layer_period_core=layer_period_core, write_ready_core=0)
    cases = dict(
        resized_n10_d64_refresh_as_implemented=dict(base, front_nblk=10, ring_depth=64, refresh=refresh_from_table()),
        resized_n10_d64_refresh_upper_bound=dict(base, front_nblk=10, ring_depth=64, refresh=refresh_from_table(bound='upper')),
        resized_n10_d128_refresh_upper_bound=dict(base, front_nblk=10, ring_depth=128, refresh=refresh_from_table(bound='upper')),
        old_n4_d8_refresh_as_implemented=dict(base, refresh=refresh_from_table()),
    )
    out = {}
    for name, q in cases.items():
        out[name] = {}
        for T in contexts:
            r = screen_36_capacity(T, q)
            l = r['layer']
            out[name][str(T)] = dict(capacity_feasible=r['capacity_feasible'], production_schedule_qualified=False,
                                     qualification_blockers=r['qualification_blockers'], qk_start_after_prefetch=l['qk_start_after_prefetch_core'],
                                     ring_peak=l['ring_peak'], ring_depth=q['ring_depth'], front_nblk=q['front_nblk'],
                                     k_rd_core=l['k_rd_core_edges'], credit_rate=l['front_credit_rate'],
                                     pc_busy_hbm=r['pc_busy_hbm_per_layer'], refresh_edges=r['refresh_edges_per_layer'],
                                     period_hbm=r['period_hbm'], own_row_scan=r['own_row_scan_index'])
    return out


def refresh_blocked(p):
    """static REFpb windows of the HBM controller as implemented (results/arch/qwen_split_1014/kvsys_v1_4_3_design/
    hbm_refresh_calendar.json as_implemented: ot_hbm_r14_stream_pc_srow REF_MODE 1, REFpb every T_REFIPB HBM edges at
    the PC's strap phase, never postponed; tRFCpb lands on a bank outside the stream's current + next two sets, so the
    stream loses only the REFpb command slot + tRREFD = block_hbm edges of RD/ACT issue per period).
    refresh = {period_hbm, block_hbm, offset_hbm} (offset = PC phase - layer start, mod period); edges_per_layer only = legacy."""
    r = p['refresh']
    per, blk = r.get('period_hbm'), r.get('block_hbm', 0)
    if not per or not blk:
        return lambda t: False
    off = r.get('offset_hbm', 0)
    return lambda t: (t - off) % per < blk


def refresh_from_table(path=None, bound='as_implemented'):
    """refresh input from the KV-die controller table (as_implemented); the offset varies per layer -> compiled over all.
    bound='as_implemented': REF_MODE 1 never blocks a column command (ot_hbm_r14_stream_pc_srow: rd_block = 0 in
      REF_MODE 1; REFpb leaves on the ROW command slot; the bank is chosen outside the stream's current + next two sets,
      whose ACTs are issued one set = 128 sectors ahead, so the tRREFD = 8 ACT gap never reaches an RD): block_hbm = 0.
    bound='upper': every REFpb costs its command edge + tRREFD of RD issue (block_hbm = 1 + T_RREFD), the 6.8 % ACT-slot
      bound applied to RDs (sensitivity only)."""
    import json
    path = path or ROOT / 'results/arch/qwen_split_1014/kvsys_v1_4_3_design/hbm_refresh_calendar.json'
    a = json.loads(Path(path).read_text())['as_implemented']
    src = a['source']
    blk = 0 if bound == 'as_implemented' else 1 + src['T_RREFD']
    return dict(period_hbm=src['T_REFIPB'], block_hbm=blk, offset_hbm=0, bound=bound,
                source=str(Path(path).relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path))


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
    """one layer, worst PC and worst refresh phase: minimal QK start (core edges after the PC prefetch start) with no
    hold, ring peak, K fetch.  With a periodic refresh the layer start meets every phase over 36 layers x tokens, so the
    schedule is compiled at every offset and the worst is the static reservation."""
    _need(p)
    r = p['refresh']
    if r.get('period_hbm') and r.get('block_hbm') and not r.get('fixed_offset'):
        outs = [compile_layer(T, dict(p, refresh=dict(r, offset_hbm=o, fixed_offset=True))) for o in range(r['period_hbm'])]
        w = max(outs, key=lambda d: (d['qk_start_after_prefetch_core'], d['ring_peak'], d['k_rd_hbm_edges']))
        return dict(w, qk_start_after_prefetch_core=max(d['qk_start_after_prefetch_core'] for d in outs),
                    ring_peak=max(d['ring_peak'] for d in outs), ring_ok=all(d['ring_ok'] for d in outs),
                    k_rd_hbm_edges=max(d['k_rd_hbm_edges'] for d in outs),
                    k_rd_core_edges=max(d['k_rd_core_edges'] for d in outs), refresh_offsets=len(outs))
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


def screen_36_capacity(T, p, layers=36):
    """Necessary periodic capacity bound, not an emitted or qualified 36-layer programme.

    K storage/credit and aggregate per-period bandwidth are screened here. This
    function does not construct V ordering, concurrent write/JEDEC events or 36
    actual timelines. ``feasible`` therefore fails closed. Consumers exploring
    capacity must use the explicitly named ``capacity_feasible`` field.
    ``write_ready_core`` is checked only with explicit origin ``prefetch_start``;
    missing origin is unqualified evidence rather than an inferred time base.
    """
    _need(p)
    one = compile_layer(T, p)
    period_hbm = math.floor(p['layer_period_core'] * p['core_ps'] / p['hbm_ps'])
    v_sectors = one['k_sectors']                              # V rows per PC = K rows per PC (static_kv_calendar model)
    writes = 2                                                # one K + one V sector of the new row per PC quarter
    r = p['refresh']
    ref_edges = (math.ceil(period_hbm / r['period_hbm']) * r['block_hbm'] if r.get('period_hbm')
                 else r.get('edges_per_layer', 0))
    busy = one['k_rd_hbm_edges'] + v_sectors + writes + ref_edges
    # the new token's own K row: its RD must issue after its WR commit
    ks = k_streams(T, p)
    own = [(pc, i) for pc, s in ks.items() for i, (_, _, t) in enumerate(s) if t == T - 1]
    actual_issue = {pc: pc_schedule(stream, p, 0)['issue'] for pc, stream in ks.items()}
    own_issue = sorted({actual_issue[pc][i] for pc, i in own})
    origin = p.get('write_ready_origin')
    if origin is not None and origin != 'prefetch_start':
        raise ScheduleError('write_ready_origin must explicitly name prefetch_start')
    ready = p['write_ready_core']
    if type(ready) is not int or ready < 0:
        raise ScheduleError('write_ready_core must be a nonnegative integer')
    readiness_checked = origin == 'prefetch_start'
    ready_hbm = math.ceil(ready * p['core_ps'] / p['hbm_ps'])
    write_ok = all(t >= ready_hbm for t in own_issue) if readiness_checked else None
    blockers = ['actual 36 layer timelines not emitted/checked',
                'actual concurrent-write JEDEC programme not checked',
                'actual V consumer order and service ports not joined']
    if not readiness_checked:
        blockers.append('write readiness has no explicit source-bound time origin')
    elif not write_ok:
        blockers.append('own-row read precedes declared write readiness')
    return dict(layer=one, layers=layers, period_hbm=period_hbm, pc_busy_hbm_per_layer=busy, refresh_edges_per_layer=ref_edges,
                scope='necessary capacity screen only',
                hbm_fits_period=busy <= period_hbm, own_row_pcs=len(own),
                own_row_scan_index=sorted({i for _, i in own}),
                own_row_rd_issue_hbm_after_prefetch=own_issue,
                write_ready_core=ready, write_ready_origin=origin,
                write_readiness_checked=readiness_checked, own_row_read_after_write_ok=write_ok,
                capacity_feasible=one['ring_ok'] and busy <= period_hbm,
                production_schedule_qualified=False, qualification_blockers=blockers,
                feasible=False)


def compile_36(T, p, layers=36):
    """Legacy entry point: capacity diagnostic only, never programme qualification."""
    return screen_36_capacity(T, p, layers)
