#!/usr/bin/env python3
"""Calibrated Qwen3-8B ROM KV-service calendar: baseline, streaming, near-HBM.

Model only. No RTL, no P&R, no adoption. Successor of the qwen_rom_kv_* calendar
records. It recomputes the current fill-path calendar (credit17 composition) with
the measured TP4 layer instead of the under-predicting unified-model chain, under
strict REFab refresh and the QROM-KV-SECDED-B1 mutable-storage protection baseline;
re-prices the streaming-only (cross-layer lease handoff) candidate like for like;
and composes the near-HBM attention candidate on the same measured compute.

Every record carries the 20 workload-identity fields and compare() refuses to
relate two rates whose identities differ, unless the differing field is a
delivery field that the caller declares as the cause.

Usage:
  python3 tools/uarch_model_qwen_rom_calibrated_calendar.py --result-dir DIR
  python3 tools/uarch_model_qwen_rom_calibrated_calendar.py --verify
"""
import argparse
import filecmp
from fractions import Fraction as F
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
import sys
import tempfile

import uarch_model as U
import uarch_model_qwen_kv_credit17 as C
import uarch_model_qwen_kv_decoupled_lease as D

A = C.A
S = A.S
ROOT = A.ROOT
OUT = ROOT / 'results/uarch/qwen_rom_calibrated_calendar_20261003'
INPUTS = OUT / 'inputs'
RECORDS = ('baseline-r1.json', 'streaming-rejected-r1.json', 'near-hbm-selected-r1.json', 'summary-r1.json')
PS_PER_CYCLE = F(2500, 3)  # 1.2 GHz stream clock
PREFIX_CYCLES = 451        # unified-model QKV prefix gating KW/VW writes (credit17); trace QKV span is 431
NL = 36

# Review inputs committed beside the records; sha256 frozen here so a changed
# input refuses to build rather than silently moving a figure.
INPUT_SHA256 = {
    'l0cal/l0_reconciliation.json':
        '7d978fa53cdfb6ba93c0774600d2f8ddd7ce8e96d7b6729e8fcf55abac33b3c7',
    'l0cal/l0_reconciliation.md':
        'becda125e6e47a75c3e2ccb53ce49b0075dc66eabe9f2b5e6a50c563f1534351',
    'policy/workload_identity.json':
        'c6e4210574c306df37713224f5c124976bedaaf8f8ea8e89173a94a661f6b887',
    'policy/workload_identity.md':
        '176f77c63dd71da29a3e33fabd068e5021e1408fde916329742c743daf52d244',
    'prefetch/decoupled_kv_service_pricing.json':
        '5e5e0d58d1e28599b533cbf9224e1a87435d1708dcb2d3dd623afdb6664beae5',
    'prefetch/decoupled_kv_service_pricing.md':
        '155c59c3a3b195f27c30f9274c3f00af843fd2021ae2fcebaa3c42481d77cb21',
    'prefetch/work/decoupled.py':
        '3c776a522b4f2bdae02a22c9ae55f9e238fd21c49d16daf19f55fe9f3970706a',
    'protref/protection_refresh_pricing.json':
        '85228235c0957b0c937f62e669f2654ebbc98f8b4dcd857bfd2d2e3fe1091adc',
    'protref/protection_refresh_pricing.md':
        'ea44e5d236045ddad8a0226a06d02dc177aaf8a0edc619b25c31d1419fed2db7',
    'protref/run_variants.py':
        '8e6b0d69513d26381b7c9c043b823db03cad7dcf2fd8bd3dc7658a4d78a7a421',
    'nearhbm/near_hbm_attention_pricing.json':
        'd6aa247886f1da97e2e5671bb8c165cfb06a81c44735814f4037c1bb86e3c504',
    'nearhbm/near_hbm_attention_pricing.md':
        '0a67b489ee0403e2ea800b2a54caf6268a2579d7f8f635d101e475a785d73114',
    'nearhbm/price_near_hbm_attention.py':
        '4df3d6b54eba49cf41654b64d6d0c4ca2ab5018d8c449d1da26ae7573ec3ba2d',
    'cooling/qwen_rom_cooling_recheck.json':
        'ed1208f8b136074ef2adab4ff3583fed5573fe23373b69b37a489e1a7092a319',
    'cooling/qwen_rom_cooling_recheck.md':
        'efda4557bfa3c1a8d1659e6ca986ea396190af303dd000eeae8ce3f22e582ca8',
}
REPO_PINS = (
    'tools/uarch_model.py',
    'tools/uarch_model_qwen_kv_credit17.py',
    'tools/uarch_model_qwen_kv_credit_allocator.py',
    'tools/uarch_model_qwen_kv_successor.py',
    'tools/uarch_model_qwen_kv_bank_groups.py',
    'tools/uarch_model_qwen_kv_decoupled_lease.py',
    'tools/uarch_model_qwen_rom_calibrated_calendar.py',
    'results/uarch/qwen_rom_kv_credit17_20261003/model-r2.json',
    'results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json',
    'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json',
    'results/rtl/qwen_rom_TP4_terminal_20261002/terminal_manifest.json',
)

# ---------------------------------------------------------------- identity
IDENTITY_FIELDS = (
    'model', 'design', 'decode_mode', 'speculation', 'batch_users',
    'context_window_positions', 'decode_position', 'position_basis',
    'kv_format', 'kv_bytes_per_element', 'kv_home', 'kv_on_die_reuse',
    'kv_delivery_policy', 'kv_offchip_read_B_per_die_token', 'kv_write_B_per_die_token',
    'fill_lanes', 'fill_bytes_per_edge', 'stream_clock_hz', 'rate_basis',
    'numerical_evidence_position')
# Fields that describe how KV is delivered (the design under comparison). They
# may differ only when the comparison names them as the cause. All other fields
# describe the workload and must match exactly.
DELIVERY_FIELDS = frozenset((
    'kv_on_die_reuse', 'kv_delivery_policy', 'kv_offchip_read_B_per_die_token',
    'kv_write_B_per_die_token', 'fill_lanes', 'fill_bytes_per_edge', 'rate_basis'))
# Secondary bases that also gate a comparison (declared like delivery fields).
BASIS_KEYS = ('compute_calibration_id', 'service_assumptions_id')


class IdentityMismatch(ValueError):
    pass


def identity(**delivery):
    base = dict(model='qwen3-8b', design='rom_option_c_tp4_g6144', decode_mode='AR', speculation='none',
                batch_users=1, context_window_positions=8192, decode_position=8191,
                position_basis='worst_case_last_of_window', kv_format='fp8_e4m3_per_element_unscaled',
                kv_bytes_per_element=1, kv_home='attached_hbm_4_stacks_per_die',
                kv_on_die_reuse='k_tail_2_tiles_per_head_plus_current_v_forward',
                kv_delivery_policy='cold_per_layer_lease', kv_offchip_read_B_per_die_token=150690816,
                kv_write_B_per_die_token=156672, fill_lanes=7, fill_bytes_per_edge=448,
                stream_clock_hz=1200000000, rate_basis='finite_calendar_conditional',
                numerical_evidence_position=0)
    for k in delivery:
        if k not in DELIVERY_FIELDS:
            raise IdentityMismatch('workload field may not vary: ' + k)
    base.update(delivery)
    if tuple(base) != IDENTITY_FIELDS:
        raise IdentityMismatch('identity field order/set')
    return base


def compare(a, b, declared=()):
    """Relate rate a to rate b. Each is {'identity','compute_calibration_id',
    'service_assumptions_id','token_s'}. Refuses on any undeclared mismatch."""
    declared = set(declared)
    for f in declared:
        if f not in DELIVERY_FIELDS and f not in BASIS_KEYS:
            raise IdentityMismatch('only delivery or basis fields may be declared: ' + f)
    ia, ib = a['identity'], b['identity']
    if set(ia) != set(IDENTITY_FIELDS) or set(ib) != set(IDENTITY_FIELDS):
        raise IdentityMismatch('record lacks the 20 identity fields')
    diff = [f for f in IDENTITY_FIELDS if ia[f] != ib[f]]
    diff += [k for k in BASIS_KEYS if a[k] != b[k]]
    undeclared = [f for f in diff if f not in declared]
    if undeclared:
        raise IdentityMismatch('mismatched identity, undeclared: ' + ','.join(undeclared))
    unused = sorted(declared - set(diff))
    if unused:
        raise IdentityMismatch('declared cause does not differ: ' + ','.join(unused))
    return dict(a_token_s=a['token_s'], b_token_s=b['token_s'],
                rate_gain_a_over_b=b['token_s'] / a['token_s'] - 1, declared_causes=sorted(diff))


# ---------------------------------------------------------------- inputs
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs():
    got = {}
    for rel, want in INPUT_SHA256.items():
        p = INPUTS / rel
        h = sha(p)
        if h != want:
            raise ValueError('pinned review input changed: ' + rel)
        got[rel] = h
    j = lambda rel: json.loads((INPUTS / rel).read_text())
    return got, j('l0cal/l0_reconciliation.json'), j('policy/workload_identity.json'), \
        j('prefetch/decoupled_kv_service_pricing.json'), j('protref/protection_refresh_pricing.json'), \
        j('nearhbm/near_hbm_attention_pricing.json'), j('cooling/qwen_rom_cooling_recheck.json')


def measured_compute(l0, nh):
    """Measured TP4 composition (retained terminal, position 0) and the
    unmeasured 8K attention delta from the unified model at me_lat_extra 167."""
    r2 = nh['r2']['inputs']
    m = dict(layer_L1_L35=r2['measured_layer_cycles_L1_L35'], L0=r2['L0'], head=r2['head'],
             unattributed_start_terminal=r2['unattributed_start_terminal'], token_total=r2['measured_total'],
             per_allreduce=r2['per_allreduce'], allreduces_per_layer=r2['allreduces_per_layer'],
             body_excl_collectives=r2['body_excl_collectives'],
             pos0_attention_trace=r2['position0_attention_share']['primary_trace_span'],
             pos0_attention_model_ctx1=r2['position0_attention_share']['alternative_model_ctx1'],
             me_lat_extra=r2['me_lat_extra_correct'])
    if (m['layer_L1_L35'], m['L0'], m['head'], m['token_total']) != (4668, 4669, 2998, 171090):
        raise ValueError('measured TP4 terminal figures changed')
    if l0['Q2_stage_contents']['itrace_die0']['segment_cycles'] != [490] * 4:
        raise ValueError('itrace segment cycles changed')
    if m['allreduces_per_layer'] != 2 * m['per_allreduce'] or m['body_excl_collectives'] + m['allreduces_per_layer'] != 4669:
        raise ValueError('L0 decomposition')
    nonlayer = m['token_total'] - NL * m['layer_L1_L35']
    if nonlayer != m['head'] + m['unattributed_start_terminal'] + (m['L0'] - m['layer_L1_L35']):
        raise ValueError('non-layer cycles')
    p1 = U.qwen_tp_point(4, 6144, 'board', clock_hz=1.2e9, me_lat_extra=m['me_lat_extra'], ctx=1, su_width=64)
    p8 = U.qwen_tp_point(4, 6144, 'board', clock_hz=1.2e9, me_lat_extra=m['me_lat_extra'], ctx=8192, su_width=64)
    delta = p8['layer_chain_cycles'] - p1['layer_chain_cycles']
    if (p1['layer_chain_cycles'], p8['layer_chain_cycles'], delta) != (2790, 4010, 1220):
        raise ValueError('unified-model 8K attention delta changed')
    return dict(measured=m, nonlayer_cycles=nonlayer,
                attention_8k_delta_cycles=delta,
                attention_8k_delta_source="tools/uarch_model.py:qwen_tp_point(4,6144,'board',1.2e9,me_lat_extra=167,su_width=64) "
                                          "layer_chain ctx 8192 (4010) minus ctx 1 (2790); UNMEASURED",
                me_lat_extra_basis='112 measured wire stages + 55 arithmetic delta; credit17/kv_bank_groups/kv_rate_risk passed 55 alone',
                prefix_cycles=PREFIX_CYCLES,
                rest_cycles_pos0=m['layer_L1_L35'] - PREFIX_CYCLES,
                rest_cycles_8k=m['layer_L1_L35'] - PREFIX_CYCLES + delta)


# ---------------------------------------------------------------- service variants
# QROM-KV-SECDED-B1, conservative latency edits (protref run_variants.py):
# return chain +3 service edges, request chain +2, assembly +2 stream periods.
SECDED_EDITS_CREDIT17 = {
    'col+25000+3000+2000+12000+link': 'col+25000+4000+3000+13000+link',
    'clock+3000+link+10000': 'clock+3000+link+12000',
    'fill[lane]=max(fill[lane],at+4*period)+period': 'fill[lane]=max(fill[lane],at+6*period)+period',
}
# credit17 capacity/validation edits as they read in the decoupled-lease source.
CREDIT17_EDITS_DECOUPLED = {
    'credit=[16]*8;globalcredit=128': 'credit=[17]*8;globalcredit=136',
    'pending[key]+n<=64': 'pending[key]+n<=68',
    '128-globalcredit': '136-globalcredit',
    "if peak_pool>80:raise ValueError('80 slots')": "if peak_pool>85:raise ValueError('85 slots')",
    'globalcredit!=128:raise': 'globalcredit!=136:raise',
    'col+25000+3000+12000+link': 'col+25000+3000+2000+12000+link',
    'owned(st,g,visible+link)': 'owned(st,g,visible+link+2000)',
}


def edited(src, edits, label):
    for old, new in edits.items():
        if src.count(old) != 1:
            raise ValueError(f'{label}: source anchor not unique/present: {old}')
        src = src.replace(old, new)
    return src


def credit17_secded_calendar():
    ns = dict(A.__dict__)
    exec(edited(C.cal, SECDED_EDITS_CREDIT17, 'credit17+SECDED'), ns)
    return ns['credit17_calendar']


def decoupled_credit17_secded_run():
    import inspect
    src = inspect.getsource(D.run)
    src = edited(src, CREDIT17_EDITS_DECOUPLED, 'decoupled+credit17')
    src = edited(src, SECDED_EDITS_CREDIT17, 'decoupled+SECDED')
    ns = dict(D.__dict__)
    exec(src, ns)
    return ns['run']


REFI, RFC = 3900, 350


class StrictREFab(S.PCService):
    """REFab issued at its due edge (bounded only by command-path legality), not
    at the next demand arrival. Copied from protref run_variants.py:Strict."""
    def column(self, layer, st, sector, write, arrival_ps):
        pc = S.pc_of(sector)
        s = self.state(st, pc)
        now = math.ceil(arrival_ps / 1000)
        while now >= s['nextref']:
            due = s['nextref']
            e = due
            if any(s['opened']):
                pre = self.command(st, pc, 'PREALL', max([due] + [s['pre'][b] for b in range(32) if s['opened'][b]]), sector)
                s['opened'] = [False] * 32
                s['actok'] = [max(v, pre + 17) for v in s['actok']]
                e = pre + 17
            ref = self.command(st, pc, 'REF', max(e, s['lastcol'] + 2, s['refblock']), sector)
            self.max_refresh_lateness = max(self.max_refresh_lateness, ref - due)
            s['nextref'] += REFI
            s['refblock'] = ref + RFC
            s['actok'] = [max(v, ref + RFC) for v in s['actok']]
        return super().column(layer, st, sector, write, arrival_ps)


def refresh_debt(service, total_ps):
    end_edge = math.ceil(total_ps / 1000)
    debt = 0
    for st in range(4):
        for pc in range(32):
            s = service.state(st, pc)
            if s['nextref'] <= end_edge:
                debt += 1 + (end_edge - s['nextref']) // REFI
    return end_edge, debt


# ---------------------------------------------------------------- calendar runs
def model_rest_extra():
    """credit17's unified-model compute, used only to prove the port reproduces
    the reviewed protref strict+SECDED figure (357.1349667 us)."""
    point = U.qwen_tp_point(4, 6144, 'ucie_measured', clock_hz=1200000000, me_lat_extra=55, ctx=8192, su_width=64)
    ar = F(str(point['exchange']['per_allreduce_cycles'])) * 2 * F(128, 100)
    rest = (F(point['layer_chain_cycles'] - PREFIX_CYCLES) + ar) * PS_PER_CYCLE
    extra = (F(point['cycles']) - NL * (F(point['layer_chain_cycles']) + 2 * F(str(point['exchange']['per_allreduce_cycles'])))) * PS_PER_CYCLE
    return rest, extra


def run_credit17(rest_ps, extra_ps):
    cal = credit17_secded_calendar()
    service = StrictREFab()
    t = F(0); compute = F(0); windows = [F(0)] * 2; rows = []; peaks = {}
    for layer in range(NL):
        begin = max(t, windows[layer % 2]); prefix = compute + PREFIX_CYCLES * PS_PER_CYCLE
        row = cal(layer, begin, prefix, service); t = row.pop('end_ps'); ready = row.pop('fill_end_ps')
        compute = max(ready, prefix) + rest_ps; windows[layer % 2] = max(t, compute)
        for k in ('peak_live_cohorts', 'peak_pending_entries_per_PC', 'peak_write_slots_per_PC', 'peak_words_per_group_lane_pool'):
            peaks[k] = max(peaks.get(k, 0), row[k])
        rows.append(dict(layer=layer, begin_ps=str(begin), prefix_ready_ps=str(prefix), fill_ready_ps=str(ready),
                         all_grants_ps=str(t), compute_done_ps=str(compute), cohorts=row['cohorts'],
                         service_bound=ready > prefix))
    total = max(t, compute) + extra_ps
    end_edge, debt = refresh_debt(service, total)
    return dict(total_exact_ps=str(total), total_s=float(total / 10**12), rows=rows, peaks=peaks,
                command_counts=dict(sorted(service.count.items())), command_event_sha256=service.digest.hexdigest(),
                max_refresh_lateness_edges=service.max_refresh_lateness, token_end_edge=end_edge,
                unissued_REFab_due_before_token_end=debt,
                service_bound_layers=sum(r['service_bound'] for r in rows))


def run_decoupled(handoff, rest_ps, extra_ps):
    run = decoupled_credit17_secded_run()
    service = StrictREFab()
    r = run(handoff, rest_ps, extra_ps, service)
    total = F(r['total_exact_ps'])
    end_edge, debt = refresh_debt(service, total)
    r['command_counts'] = dict(sorted(r['command_counts'].items()))
    r['command_event_sha256'] = service.digest.hexdigest()
    r['token_end_edge'] = end_edge
    r['unissued_REFab_due_before_token_end'] = debt
    r['rows'] = [{k: v for k, v in row.items()} for row in r['rows']]
    return r


def _job(spec):
    kind, args = spec[0], spec[1:]
    if kind == 'credit17':
        rest, extra = (F(x) for x in args)
        return run_credit17(rest, extra)
    handoff, rest, extra = args
    return run_decoupled(handoff, F(rest), F(extra))


def calendar_runs(comp, processes=7):
    mrest, mextra = model_rest_extra()
    extra = comp['nonlayer_cycles'] * PS_PER_CYCLE
    r0 = comp['rest_cycles_pos0'] * PS_PER_CYCLE
    r8 = comp['rest_cycles_8k'] * PS_PER_CYCLE
    specs = dict(
        repro_model_compute=('credit17', str(mrest), str(mextra)),
        baseline_pos0=('credit17', str(r0), str(extra)),
        baseline_8k=('credit17', str(r8), str(extra)),
        streaming_pos0=('decoupled', 'last_issue', str(r0), str(extra)),
        streaming_8k=('decoupled', 'last_issue', str(r8), str(extra)),
        control_pos0=('decoupled', 'all_grants', str(r0), str(extra)),
        control_8k=('decoupled', 'all_grants', str(r8), str(extra)))
    names = list(specs)
    with multiprocessing.get_context('fork').Pool(min(processes, len(names))) as pool:
        out = pool.map(_job, [specs[n] for n in names])
    return dict(zip(names, out))


# ---------------------------------------------------------------- records
def us(s):
    return round(s * 1e6, 4)


def rate(s):
    return round(1 / s, 1)


def pins(inputs_sha):
    repo = {p: sha(ROOT / p) for p in REPO_PINS}
    return dict(repo_sources_sha256=repo,
                review_inputs_sha256={'results/uarch/qwen_rom_calibrated_calendar_20261003/inputs/' + k: v
                                      for k, v in inputs_sha.items()},
                credit17_production_sources_verified=True)


def check_production_pins():
    old = json.loads((ROOT / 'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json').read_text())
    for p, h in old['source_sha256'].items():
        if sha(ROOT / p) != h:
            raise ValueError('pinned production source changed ' + p)
    return len(old['source_sha256'])


def build(processes=7):
    inputs_sha, l0, wid, dec, prot, nh, cool = load_inputs()
    nprod = check_production_pins()
    rec_fields = wid['q4_recommended_identity']['fields']
    if tuple(rec_fields) != IDENTITY_FIELDS:
        raise ValueError('identity field list differs from the policy review')
    comp = measured_compute(l0, nh)
    runs = calendar_runs(comp, processes)
    pin = pins(inputs_sha)
    pin['credit17_production_source_count'] = nprod

    # reproduction of the reviewed strict+SECDED figure under model compute
    want = prot['variants']['ecc_strict_refab']['total_conditional_s']
    repro = runs['repro_model_compute']
    repro_ok = abs(repro['total_s'] - want) < 1e-15
    if not repro_ok:
        raise ValueError('strict+SECDED port does not reproduce the reviewed 357.1349667 us')
    # the cross-layer loop, in all_grants control mode, must reproduce the per-layer calendar
    for c in ('pos0', '8k'):
        if runs['control_' + c]['total_exact_ps'] != runs['baseline_' + c]['total_exact_ps']:
            raise ValueError('decoupled all_grants control does not reproduce baseline_' + c)

    m = comp['measured']
    svc_id = 'credit17_one17_136_68_85_strict_refab_secded_b1_conservative'
    cal_pos0 = 'rtl_tp4_pos0_layer4668_ar991x2_nonlayer3042'
    cal_8k = 'rtl_tp4_pos0_layer4668_ar991x2_nonlayer3042_plus_model_attn8k_1220_unmeasured'
    base_id = identity()
    b0, b8 = runs['baseline_pos0'], runs['baseline_8k']
    fill_floor_us = 281.4
    baseline = dict(
        schema='qrom-calibrated-calendar-baseline.v1',
        status='CALIBRATED_BASELINE_MODEL_ONLY_NOT_ADOPTED',
        identity=base_id, compute_calibration_id=cal_pos0, service_assumptions_id=svc_id,
        design=dict(
            fill_path='credit17 composition (results/uarch/qwen_rom_kv_credit17_20261003/model-r2.json calendar): '
                      '17/group, 136 global cohorts, 68 pending/PC (64 RAM + 4 FF spill), 85 words/pool, 8 return groups, '
                      '4 column paths/stack, 7 global fill lanes x 64 B at 1.2 GHz, cold-per-layer lease',
            why_credit17='latest finite fill-path calendar and the storage QROM-KV-SECDED-B1 was sized on; it and its 16-credit '
                         'predecessor both carry recorded G0/1%-screen failures, so this is the reference baseline, not an adopted rate',
            refresh='strict REFab at its due edge (RTL refreshes from IDLE, ot_hbm_r14_pc.sv:120); JEDEC tREFI 3.9 us, tRFC 350 ns',
            mutable_protection=dict(name='QROM-KV-SECDED-B1', latency='conservative: +3 return service edges, +2 request edges, '
                                    '+2 assembly stream periods', calendar_source_edits=SECDED_EDITS_CREDIT17,
                                    area_mm2_per_die=0.404, area_basis='cell area only (FF 0.116, enc/check/correct 0.215, parity 0.073); '
                                    'hold buffers, PG, routing, clock not priced', rom_ecc=False,
                                    policy='AGENTS ROM policy removes ROM ECC only; SRAM/FF mutable KV-service state keeps protection')),
        compute=dict(comp, rest_ps_pos0=str(comp['rest_cycles_pos0'] * PS_PER_CYCLE),
                     rest_ps_8k=str(comp['rest_cycles_8k'] * PS_PER_CYCLE),
                     nonlayer_ps=str(comp['nonlayer_cycles'] * PS_PER_CYCLE),
                     composition='compute(l)=max(fill_ready(l),prefix(l))+rest; prefix(l)=compute(l-1)+451 cycles; '
                                 'rest=4668-451 at position 0 (measured layer incl. 2x991 exposed all-reduces); '
                                 'non-layer=171090-36*4668=3042 (head 2998 + 43 unattributed + L0 extra 1)',
                     uncalibrated_predecessor_compute='qwen_tp_point ucie_measured me_lat_extra=55: chain 3338, AR 71 (drops the 112 wire stages)'),
        headline=dict(case='measured compute at position 0 (the attention share is the 87-cycle trace span)',
                      token_s=b0['total_s'], token_us=us(b0['total_s']), tokens_per_s=rate(b0['total_s']),
                      total_exact_ps=b0['total_exact_ps']),
        sensitivity_8k_attention_unmeasured=dict(added_cycles_per_layer=comp['attention_8k_delta_cycles'],
                                                 token_s=b8['total_s'], token_us=us(b8['total_s']), tokens_per_s=rate(b8['total_s']),
                                                 compute_calibration_id=cal_8k, total_exact_ps=b8['total_exact_ps']),
        calendar=dict(position0=b0, attention8k=b8),
        reproduction=dict(case='same edits under the unified-model compute (credit17 r2 rest/extra)',
                          token_s=repro['total_s'], expected_from_protref_ecc_strict_refab_s=want,
                          reproduced=repro_ok, max_refresh_lateness_edges=repro['max_refresh_lateness_edges']),
        bounds=dict(fill_lane_floor_us=fill_floor_us, command_bus_floor_us=dec['floors']['command_bus_floor_us'],
                    compute_chain_us_pos0=us(float((NL * m['layer_L1_L35'] + comp['nonlayer_cycles']) * PS_PER_CYCLE / 10**12)),
                    compute_chain_us_8k=us(float((NL * (m['layer_L1_L35'] + comp['attention_8k_delta_cycles']) + comp['nonlayer_cycles']) * PS_PER_CYCLE / 10**12)),
                    binder='KV fill service (finite credits over 7 fill lanes); compute chain does not bind',
                    target_3k_s=1 / 3000, meets_3k=b0['total_s'] <= 1 / 3000),
        comparison_to_uncalibrated=dict(credit17_r2_lazy_noprot_model_compute_us=358.6013,
                                        note='not comparable: compute_calibration_id and service_assumptions_id differ; '
                                             'shown for provenance only'),
        cooling=dict(binds=False, basis='qwen_rom_cooling_recheck: A-liquid cap 17,650 tok/s, worst valid sensitivity 11,184',
                     caps_tokens_s=cool['verdict']['baseline_caps_tokens_s']),
        unqualified=['sustained HBM PHY rate (actual_sustained_PHY_Bps null)', 'loaded routes / Ampere channels, 1.0/1.2 GHz CDC',
                     'SECDED hold buffers, PG, routing, clock; slow correction path calendar',
                     'token-end refresh debt carried to the next token (unissued REFab counted, not charged)',
                     '8K attention compute (+1220 cycles/layer) is a model figure; only position 0 is measured',
                     'one-segment all-reduce (991 measured two-segment is used)', 'SS/FF physical timing of the measured RTL',
                     'embedding hand-off (host-preloaded in the measurement)'],
        admission=dict(model_only=True, new_RTL=False, new_PnR=False, adoption=False),
        pins=pin)

    # ---- streaming-only candidate (rejected)
    s0, s8 = runs['streaming_pos0'], runs['streaming_8k']
    g0 = b0['total_s'] / s0['total_s'] - 1
    g8 = b8['total_s'] / s8['total_s'] - 1
    stream_id = identity(kv_delivery_policy='cross_layer_lease_handoff_at_last_issue')
    reviewed = dec['task3_candidate']['runs']
    streaming = dict(
        schema='qrom-calibrated-calendar-streaming-candidate.v1',
        status='REJECTED_MODEL_GAIN_BELOW_1PERCENT_AT_8K_CALIBRATED' if g8 < 0.01 else 'REJECTED_INSUFFICIENT',
        identity=stream_id, compute_calibration_id=cal_pos0, service_assumptions_id=svc_id,
        candidate='Hand the per-layer KV lease to layer l+1 when every layer-l descriptor head has issued its last request, '
                  'instead of when every layer-l grant has retired. Zero added storage; two layer epochs live in credits, '
                  'pending entries and owner slots.',
        implementation='tools/uarch_model_qwen_kv_decoupled_lease.py:run (reviewed decoupled.py), rewritten to credit17 + SECDED-B1 '
                       'by asserted anchors, strict REFab service; all_grants control mode reproduces the baseline calendar exactly',
        source_edits=dict(credit17=CREDIT17_EDITS_DECOUPLED, secded=SECDED_EDITS_CREDIT17),
        like_for_like=dict(
            position0=dict(baseline_s=b0['total_s'], candidate_s=s0['total_s'], candidate_us=us(s0['total_s']),
                           tokens_per_s=rate(s0['total_s']), rate_gain=g0, clears_1percent=g0 >= 0.01),
            attention8k_unmeasured=dict(baseline_s=b8['total_s'], candidate_s=s8['total_s'], candidate_us=us(s8['total_s']),
                                        tokens_per_s=rate(s8['total_s']), rate_gain=g8, clears_1percent=g8 >= 0.01,
                                        compute_calibration_id=cal_8k),
            control_reproduces_baseline=True,
            calendars=dict(position0=s0, attention8k=s8)),
        reviewed_numbers_preserved=dict(
            source='inputs/prefetch/decoupled_kv_service_pricing.json',
            basis='16-credit predecessor (model-r4), lazy refresh, no mutable-storage protection',
            service_assumptions_id='credit16_128_64_80_lazy_refab_noprot',
            runs={k: dict(label=v['label'], control_s=v['control_all_grants_s'], candidate_s=v['candidate_last_issue_s'],
                          rate_gain=v['rate_gain']) for k, v in reviewed.items()},
            floors=dec['floors'],
            third_tile_window=dict(gain=dec['task4_storage']['third_tile_window_one_extra_layer']['gain'],
                                   area_mm2_per_die=dec['task4_storage']['third_tile_window_one_extra_layer']['area_mm2_per_die'],
                                   fits=dec['task4_storage']['third_tile_window_one_extra_layer']['fits'])),
        rejection=dict(
            reasons=[f'like-for-like gain at the 8K-attention calibrated compute is {g8*100:.3f}% '
                     f'({"below" if g8 < 0.01 else "at/above"} the 1% adoption screen)',
                     f'position-0 gain {g0*100:.3f}% is the upper case and still leaves the token at {us(s0["total_s"]):.1f} us, '
                     f'above the 333.3 us 3k budget',
                     'command-bus floor 308.16 us binds before the 280.6 us fill floor; with unlimited in-flight storage the '
                     'ceiling is about +15%, far below the near-HBM candidate (near-hbm-selected-r1.json)',
                     'needs unqualified cross-layer epoch RTL (two live layer epochs in credits, pending, owner slots)'],
            failed_verdict_is_final=True),
        unqualified=dec['task5_assumptions']['unqualified'],
        admission=dict(model_only=True, new_RTL=False, new_PnR=False, adoption=False),
        pins=pin)

    # ---- near-HBM attention candidate (selected for build as a model entry)
    r1 = nh['latency']['cases']
    body = m['layer_L1_L35'] - m['pos0_attention_trace'] - m['allreduces_per_layer']
    if body != nh['r2']['per_layer_primary']['noncollective_nonattention_body']:
        raise ValueError('near-HBM body composition')
    ar_cases = {'991_measured_two_segment': 991, '620_one_segment_l0cal_estimate': 620, '490_one_segment_transfer_plus_resume': 490}
    att_cases = {k: r1[k]['per_layer_cycles']['total'] for k in ('primary', 'hbm_0p7TBs', 'narrow_bus_128', 'kv_prefetch_2x_lanes')}
    grid = {}
    for an, ar in ar_cases.items():
        for cn, att in att_cases.items():
            per_layer = body + 2 * ar + att
            cyc = NL * per_layer + comp['nonlayer_cycles']
            t = float(cyc * PS_PER_CYCLE / 10**12)
            grid[f'{cn}@AR{an}'] = dict(per_layer_cycles=per_layer, token_cycles=cyc, token_s=t, token_us=us(t), tokens_per_s=rate(t))
    prim = grid['primary@AR991_measured_two_segment']
    if prim['token_cycles'] != nh['r2']['primary']['token_cycles']:
        raise ValueError('near-HBM r2 primary not reproduced')
    alt_body = m['layer_L1_L35'] - m['pos0_attention_model_ctx1'] - m['allreduces_per_layer']
    alt_cyc = NL * (alt_body + 2 * 991 + att_cases['primary']) + comp['nonlayer_cycles']
    near_id = identity(kv_delivery_policy='near_hbm_two_phase_stack_local_attention',
                       kv_on_die_reuse='none_new_k_v_forwarded_to_owner_stack',
                       kv_offchip_read_B_per_die_token=wid['q2_bytes_and_gap']['logical_kv_read_per_die_token_ctx8192_pos8191'],
                       fill_lanes=0, fill_bytes_per_edge=0, rate_basis='analytical_overlap')
    near_cal = 'rtl_tp4_pos0_body2599_ar991x2_nonlayer3042_plus_near_hbm_attention_model'
    near = dict(
        schema='qrom-calibrated-calendar-near-hbm-attention.v1',
        status='SELECTED_FOR_BUILD_MODEL_ENTRY_NOT_ADOPTED',
        identity=near_id, compute_calibration_id=near_cal, service_assumptions_id='near_hbm_stack_local_fifo_strict_refab_secded_unpriced',
        identity_notes=dict(kv_offchip_read='all 8191 prior K/V positions read from HBM (no K-tail SRAM); logical 150,976,512 B',
                            kv_write='assumed equal to the calendar sector write (156,672 B); the owner-stack write is not modelled',
                            the_150847488_figure='the r1 pricing labelled 150,847,488 B as KV; it is RD+WR command bytes (policy review)'),
        candidate='Attention moves to a shoreline unit behind each HBM PHY: stream K (both KV heads), store FP32 scores, '
                  'exchange the per-head max, stream V; KV striped stack=(t mod 512) div 128 so every P.V and Z chunk is stack-local; '
                  'tree tops, reciprocal and multiply at the hub. Bit-exact to the golden two-pass order; online softmax is not.',
        composition=dict(per_layer='body (4668 - 87 pos-0 attention - 1982 all-reduces = 2599) + 2 x AR + near-HBM attention',
                         body_cycles=body, attention_cycles=att_cases, nonlayer_cycles=comp['nonlayer_cycles'],
                         attention_terms_primary=r1['primary']['per_layer_cycles'],
                         body_position_independent_assumed=True),
        headline=dict(case='primary, AR 991 measured', **prim),
        sensitivities=dict(grid=grid,
                           pos0_attention_share_model_522=dict(token_cycles=alt_cyc, token_us=us(float(alt_cyc * PS_PER_CYCLE / 10**12)))),
        selected_for_build_because=[
            'removes the 7-lane global fill, its 136/17 credits, 56x85 assembly pools, reverse grants and per-tile KV landing',
            'the only priced lever that clears the service bound: compute chain binds afterwards',
            'two-pass exact order mirrors the golden; area 13.85-15.81 mm2/die added fits the 19.67 mm2 slot headroom before credits'],
        unqualified_inputs=[
            'HBM sustained 0.9 TB/s per stack (modelled; now sets the attention term; 0.7 TB/s sensitivity listed)',
            'controller accept rate: LEN1 at II 5 caps 204.8 GB/s/stack; needs LEN>=5 reads per accept or a controller redesign',
            'closure at SS 1.2 GHz of exp (1,196 MHz), recip (1,223 MHz) and fp32_mul (1,275 MHz): not closed; BF16 MAC pipe closed only at 1,040 MHz; '
            'score SRAM SS clk-to-q 692 ps of 833 ps',
            'KV layout change: residue-512 stack striping and chunk-major order replace the source-hash PC allocator',
            'shoreline floorplan: 3.4-3.9 mm2 per stack (0.29-0.33 mm strip behind each PHY) needs floorplan-owner approval; '
            'hub at array centre (22.3 mm, 45 wire stages) assumed',
            'all-reduce: 991 measured two-segment; one-segment 620/490 unmeasured',
            'P.V split is tied to G=6144 (golden attn_splits)',
            'stack base-die thermal limit: heat moves to the base dies; no limit exists in the repo',
            'control share (5% assumed), repeaters, CTS, PG; per-stack SECDED on the new score SRAM/FIFOs not priced',
            'body taken position-independent (measured at position 0); embedding hand-off not included'],
        area=nh['area_mm2'],
        unit_closure=nh['unit_closure'],
        adoption_gates=['exact RTL gate against the golden two-pass order', 'measured RTL gain', 'SS/FF closure in context',
                        'sustained-rate HBM measurement', 'floorplan approval'],
        admission=dict(model_only=True, new_RTL=False, new_PnR=False, adoption=False, selected_for_build=True),
        pins=pin)

    # ---- summary with identity-checked comparisons
    def view(rec, token_s, cal=None):
        return dict(identity=rec['identity'], compute_calibration_id=cal or rec['compute_calibration_id'],
                    service_assumptions_id=rec['service_assumptions_id'], token_s=token_s)
    vb0 = view(baseline, b0['total_s']); vb8 = view(baseline, b8['total_s'], cal_8k)
    vs0 = view(streaming, s0['total_s']); vs8 = view(streaming, s8['total_s'], cal_8k)
    vn = view(near, prim['token_s'])
    comparisons = dict(
        streaming_vs_baseline_pos0=compare(vs0, vb0, ['kv_delivery_policy']),
        streaming_vs_baseline_8k=compare(vs8, vb8, ['kv_delivery_policy']),
        near_hbm_vs_baseline_pos0=compare(vn, vb0, ['kv_delivery_policy', 'kv_on_die_reuse', 'kv_offchip_read_B_per_die_token',
                                                    'fill_lanes', 'fill_bytes_per_edge', 'rate_basis',
                                                    'compute_calibration_id', 'service_assumptions_id']),
        near_hbm_vs_baseline_8k=compare(vn, vb8, ['kv_delivery_policy', 'kv_on_die_reuse', 'kv_offchip_read_B_per_die_token',
                                                  'fill_lanes', 'fill_bytes_per_edge', 'rate_basis',
                                                  'compute_calibration_id', 'service_assumptions_id']))
    refused = {}
    published = dict(
        atlas_headline_TP2_DFlash=dict(identity=dict(base_id, design='rom_tp2_two_reticle_g4608', speculation='dflash',
                                                     rate_basis='analytical_overlap'),
                                       compute_calibration_id='arch_budget_qwen3', service_assumptions_id='max_compute_kv_7p2TBs',
                                       token_s=1 / 18720),
        microarch_6222_mixed_position=dict(identity=dict(base_id, kv_delivery_policy='kv_on_core_not_in_cycles', fill_lanes=0,
                                                         fill_bytes_per_edge=0, rate_basis='analytical_overlap',
                                                         position_basis='position0_calibration_applied_at_8191'),
                                           compute_calibration_id='uarch_model_qwen_l0_rtl_ratio', service_assumptions_id='none',
                                           token_s=1 / 6222),
        uncalibrated_credit17_r2=dict(identity=base_id, compute_calibration_id='qwen_tp_point_ucie_extra55',
                                      service_assumptions_id='credit17_lazy_refab_noprot', token_s=358.6013e-6))
    for name, other in published.items():
        try:
            compare(vb0, other, ['kv_delivery_policy', 'fill_lanes', 'fill_bytes_per_edge', 'rate_basis'])
            refused[name] = 'NOT REFUSED'
        except IdentityMismatch as e:
            refused[name] = 'REFUSED: ' + str(e)
    summary = dict(
        schema='qrom-calibrated-calendar-summary.v1',
        status='MODEL_ONLY_SUMMARY',
        headline_numbers=dict(
            calibrated_current=dict(token_us=us(b0['total_s']), tokens_per_s=rate(b0['total_s']),
                                    at_8k_attention_unmeasured=dict(token_us=us(b8['total_s']), tokens_per_s=rate(b8['total_s']))),
            streaming_rejected=dict(token_us=us(s0['total_s']), tokens_per_s=rate(s0['total_s']), rate_gain=g0,
                                    at_8k_attention_unmeasured=dict(token_us=us(s8['total_s']), tokens_per_s=rate(s8['total_s']), rate_gain=g8)),
            near_hbm_selected_for_build=dict(token_us=prim['token_us'], tokens_per_s=prim['tokens_per_s'],
                                             one_segment_AR_620=grid['primary@AR620_one_segment_l0cal_estimate']['token_us'],
                                             one_segment_AR_490=grid['primary@AR490_one_segment_transfer_plus_resume']['token_us'])),
        identity_fields=list(IDENTITY_FIELDS), delivery_fields_declarable=sorted(DELIVERY_FIELDS), basis_keys=list(BASIS_KEYS),
        comparison_rule='Two rates are related only when every workload field matches; delivery fields and the compute/service '
                        'basis may differ only when declared as the cause.',
        comparisons=comparisons, refused_comparisons=refused,
        records=[r for r in RECORDS if r != 'summary-r1.json'],
        pins=pin)
    return {'baseline-r1.json': baseline, 'streaming-rejected-r1.json': streaming,
            'near-hbm-selected-r1.json': near, 'summary-r1.json': summary}


def write(records, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for name, rec in records.items():
        with (outdir / name).open('x') as f:
            json.dump(rec, f, indent=1, sort_keys=False)
            f.write('\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--result-dir', type=Path)
    g.add_argument('--verify', action='store_true', help='regenerate into a temp dir and require byte-identical records')
    ap.add_argument('--processes', type=int, default=7)
    a = ap.parse_args()
    recs = build(a.processes)
    if a.result_dir:
        write(recs, a.result_dir)
        return 0
    with tempfile.TemporaryDirectory(prefix='qrom-calibrated-verify-') as d:
        write(recs, Path(d))
        bad = [n for n in RECORDS if not filecmp.cmp(Path(d) / n, OUT / n, shallow=False)]
    for n in RECORDS:
        print(('MISMATCH ' if n in bad else 'IDENTICAL ') + n)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
