#!/usr/bin/env python3
"""Replay measured PHW10 service; gate current-program/provider journal joins.

No execution, source overlay or simulated ACK. The retained native journal is
an older-core cone. Its calibration is useful but cannot enroll a whole core.
Provider packets below are an observer API, not an implemented transport.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import dsrom_I66_provider_clock_contract as P
import dsrom_I66_reserved_service as R
import dsrom_I66_standalone_calibration as S

OUT = R.ROOT / 'results/uarch/dsrom_I66_actual_service_join_20261002'
IDENTITY = dict(rank=2, generation=32, user=32, EID=9, stage=6, phase=10, key_word=32)
BITS = ['d_skip', 'waited', 'unit_ready', 'q_gate', 'kv_gate', 'm0_gate',
        'win_admit', 'coll_fault', 'rope_pf_fault', 'qe_go', 'rom_q_go',
        'rom_ready', 'coll_busy', 'adapter_fault', 'key_hit']


def uint(x, width=64):
    if type(x) is not int or not 0 <= x < 1 << width:
        raise ValueError('invalid unsigned field')
    return x


def identity(x):
    if set(x) != set(IDENTITY):
        raise ValueError('missing or extraneous operation identity')
    for k, w in IDENTITY.items():
        uint(x[k], w)
    eid = x['EID']
    if eid >= 384 or x['stage'] != (0 if eid < 288 else 1):
        raise ValueError('wrong expert owner')
    phase = 10 + 3 * eid if eid < 288 else 3 * (eid - 288)
    if x['phase'] != phase or x['key_word'] != 2149580800 + 4096 * eid:
        raise ValueError('wrong expert phase/key')
    return x


def file_pin(path, expected):
    if type(expected) is not str or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('invalid SHA256')
    p = Path(path)
    if S.sha(p) != expected:
        raise ValueError('artifact hash mismatch: ' + str(p))
    return p


def current_enrollment(p):
    """Static source admission plus actual runtime argv/journal enrollment.

    Qualified manifests are immutable inputs; self-declared port geometry is
    insufficient. This validates receipt consistency, not compiler honesty.
    Full source/parameter qualification remains the manifest owner's duty.
    """
    p = copy.deepcopy(p)
    for v in p['parameters'].values():
        uint(v)
    P.enrollment_gate(p)
    qualified = json.loads(file_pin(p['qualification_path'], p['qualification_sha256']).read_text())
    compiled = json.loads(file_pin(p['compile_manifest_path'], p['compile_manifest_sha256']).read_text())
    runtime = json.loads(file_pin(p['runtime_receipt_path'], p['runtime_receipt_sha256']).read_text())
    for record in [qualified, compiled]:
        for value in record['parameters'].values():
            uint(value)
    if qualified['scope'] != 'CURRENT_PHW10_FULLPROGRAM' or runtime['scope'] != qualified['scope']:
        raise ValueError('cone or historical runtime cannot enroll current whole program')
    if qualified['parameters'] != p['parameters'] or compiled['parameters'] != p['parameters']:
        raise ValueError('parameter qualification mismatch')
    if not qualified['source_files'] or compiled['source_files'] != qualified['source_files']:
        raise ValueError('incomplete compiled source closure')
    for path, h in qualified['source_files'].items():
        file_pin(path, h)
    for k, path in p['source_paths'].items():
        if qualified['source_files'].get(path) != compiled['source_sha256'][k]:
            raise ValueError('protected source outside qualified closure')
    if runtime['binary_sha256'] != p['binary_sha256'] or runtime['compile_manifest_sha256'] != p['compile_manifest_sha256']:
        raise ValueError('runtime executable/compile receipt mismatch')
    file_pin(p['binary_path'], p['binary_sha256'])
    for rank in map(str, range(4)):
        prog = Path(p['program_paths'][rank]).resolve()
        if prog.name != 'prog.hex':
            raise ValueError('actual loader requires DIR/prog.hex')
        if qualified['program_sha256'][rank] != p['program_sha256'][rank]:
            raise ValueError('canonical complete program mismatch')
        if qualified['field_image_sha256'][rank] != p['field_image_sha256'][rank]:
            raise ValueError('canonical complete field bundle mismatch')
        argv = runtime['rank_plusargs'][rank]
        for prefix, target in [('+DIR=', prog.parent), ('+OT_ROM_DIR=', Path(p['field_image_paths'][rank]).resolve())]:
            args = [s for s in argv if s.startswith(prefix)]
            if len(args) != 1 or Path(args[0][len(prefix):]).resolve() != target:
                raise ValueError('missing/conflicting actual loader argument')
    file_pin(p['journal_path'], runtime['journal_sha256'])
    return dict(status='PASS_CURRENT_STATIC_AND_RUNTIME_ENROLLMENT',
                binary_sha256=p['binary_sha256'], journal_sha256=runtime['journal_sha256'],
                accepted_origin=None, fulltoken=False)


def admission(samples, ident):
    """Source S_ISSUE -> NBA go -> registered EID -> key -> spine acceptance.

    Normal QE does not directly gate coll_busy/win_admit. They remain samples,
    not invented admission predicates. Fault/key-miss cannot grant service.
    """
    identity(ident)
    byedge = {}
    for s in samples:
        t = uint(s['edge'])
        identity(s['identity'])
        if t in byedge or s['identity'] != ident:
            raise ValueError('duplicate/stale core sample')
        for k in BITS:
            uint(s[k], 1)
        for k, w in [('pc', 14), ('st', 4), ('d_unit', 3), ('qe_mode', 2),
                     ('X_ROM', 1), ('FULL_SHAPE', 1), ('adapter_st', 3)]:
            uint(s[k], w)
        byedge[t] = s
    candidates = []
    for t, s in byedge.items():
        if (s['pc'], s['st'], s['d_unit']) != (66, 6, 3):
            continue
        if (s['X_ROM'], s['FULL_SHAPE'], s['qe_mode']) != (1, 1, 0):
            raise ValueError('wrong actual provider branch')
        if s['d_skip'] or s['coll_fault'] or s['rope_pf_fault'] or not all(s[k] for k in ['waited', 'unit_ready', 'q_gate', 'kv_gate', 'm0_gate']):
            continue
        try:
            nxt, rd, response, lookup, phase = [byedge[t+i] for i in [1, 2, 3, 4, 6]]
        except KeyError as e:
            raise ValueError('missing registered lifecycle sample') from e
        if not (nxt['st'] == 7 and nxt['pc'] == 66 and nxt['qe_go'] == nxt['rom_q_go'] == nxt['rom_ready'] == 1 and nxt['adapter_st'] == 0):
            raise ValueError('registered adapter admission mismatch')
        if rd['rom_vre'] != 1 or type(rd['rom_vre']) is not int or rd['rom_vaddr'] != 366688 or type(rd['rom_vaddr']) is not int:
            raise ValueError('wrong registered EID read')
        if uint(response['rom_vq'], 32) != ident['EID'] or response['adapter_st'] != 2:
            raise ValueError('wrong registered EID response')
        if lookup['adapter_st'] != 3 or lookup['key_hit'] != 1 or any(x['adapter_fault'] for x in [nxt, rd, response, lookup, phase]):
            raise ValueError('key miss/fault cannot grant phase')
        uint(phase['phase'], 10)
        uint(phase['key_word'], 32)
        if phase['phase_accept'] != 1 or type(phase['phase_accept']) is not int or phase['phase'] != ident['phase'] or phase['key_word'] != ident['key_word'] or phase['adapter_fault']:
            raise ValueError('wrong phase acceptance')
        candidates.append(dict(core_issue_edge=t, adapter_accept_edge=t+1, phase_accept_edge=t+6))
    if len(candidates) != 1:
        raise ValueError('require exactly one qualified operation admission')
    return candidates[0]


def provider_join(plan, packets):
    """Join actual callbacks to guaranteed slots; predictions never retire debt.

    Packet API: ordinal/edge/identity/kind/id, optional bits. Kinds capture,
    publish, ACK, source_idle, operation_retire. Every late observation is
    sticky rejection even if a later completion appears. No PC/busy packets.
    A finite bound is conditional on source-calendar/slot qualification.
    """
    plan = copy.deepcopy(plan)
    ident = identity(plan['calendar']['identity'])
    bound = R.compose(plan['calendar'], plan['events'], plan['domains'])
    ev = {e['id']: e for e in bound['reservation']['events']}
    got = set()
    idle = retired = False
    last = -1
    for ordinal, p in enumerate(packets):
        identity(p['identity'])
        if uint(p['ordinal']) != ordinal or p['identity'] != ident:
            raise ValueError('ordinal/stale operation mismatch')
        edge = uint(p['edge'])
        if edge < last or retired:
            raise ValueError('unordered or post-retirement callback')
        last = edge
        kind, event_id = p['kind'], p.get('id')
        if kind in ['source_idle', 'operation_retire'] and event_id is not None:
            raise ValueError('operation state callback cannot invent an event id')
        token = (kind, event_id)
        if token in got:
            raise ValueError('duplicate callback')
        if kind in ['capture', 'publish', 'ACK']:
            if event_id not in ev:
                raise ValueError('foreign provider event')
            e = ev[event_id]
            if kind == 'ACK':
                if e['ACK'] is None or ('capture', event_id) not in got:
                    raise ValueError('unowned or premature ACK')
                if e['kind'] == 'result' and ('publish', event_id) not in got:
                    raise ValueError('ACK before causal VM visibility')
                if edge > e['ACK'] or edge < e['visible']+1:
                    raise ValueError('late or premature ACK')
            else:
                if uint(p['bits']) != e['bits'] or edge != e['visible']:
                    raise ValueError('capture/publication misses reserved identity/deadline')
                if kind == 'publish' and (e['kind'] != 'result' or ('capture', event_id) not in got or uint(p['row']) != e['row'] or uint(p['address']) != e['address']):
                    raise ValueError('publication not owned by captured result')
        elif kind == 'source_idle':
            if edge != plan['calendar']['source_idle_edge']:
                raise ValueError('unqualified source idle')
            idle = True
        elif kind == 'operation_retire':
            required = {('capture', k) for k in ev} | {('publish', k) for k, e in ev.items() if e['kind'] == 'result'} | {('ACK', k) for k, e in ev.items() if e['ACK'] is not None}
            if not idle or not required <= got or edge > bound['successful_completion_edge'] or edge < bound['reservation']['last_retirement']:
                raise ValueError('early/late completion or outstanding causal debt')
            retired = True
        else:
            raise ValueError('not a causal provider callback')
        got.add(token)
    if not retired:
        raise ValueError('missing operation retirement')
    return dict(status='PASS_OBSERVER_RESERVED_SERVICE_JOIN', observed_packets=len(packets),
                observed_retire_edge=last, finite_conditional_bound=bound['successful_completion_edge'],
                hardware_admission=False, fulltoken=False)


def current_join(provenance, plan_path):
    """Only a reviewed phase plan can turn actual callbacks into a bound.

    The journal JSON contains core_samples and provider_packets, each captured
    by qualified observer sources. Its raw file hash is enrolled in the actual
    runtime receipt. API unit-test traces alone cannot use this entry point.
    """
    result = current_enrollment(provenance)
    plan = S.load(plan_path)
    ident = identity(plan['calendar']['identity'])
    q = S.load(Path(provenance['qualification_path']))
    try:
        binding = q['qualified_service_plans'][str(ident['EID'])]
    except KeyError as e:
        raise ValueError('no qualified phase-specific successful service guarantee') from e
    file_pin(plan_path, binding['plan_sha256'])
    for key in ['source_calendar', 'phase_source']:
        file_pin(binding[key+'_path'], binding[key+'_sha256'])
        if plan['calendar'][key+'_sha256'] != binding[key+'_sha256']:
            raise ValueError('reservation detached from phase source qualification')
    if not q['callback_source_files'] or not set(q['callback_source_files'].items()) <= set(q['source_files'].items()):
        raise ValueError('callback sources not compiled in qualified binary')
    trace = S.load(Path(provenance['journal_path']))
    origin = admission(trace['core_samples'], ident)
    uint(plan['calendar']['source_phase_accept_edge'])
    if plan['calendar']['accepted_edge'] != origin['adapter_accept_edge'] or plan['calendar']['source_phase_accept_edge'] != origin['phase_accept_edge']:
        raise ValueError('reservation origin differs from actual source acceptance')
    result['origin'] = origin
    result['service'] = provider_join(plan, trace['provider_packets'])
    result['status'] = 'PASS_CURRENT_ENROLLED_OPERATION_SERVICE'
    return result


def measured_cone(events=None):
    """Real PHW10 accepted-event replay and phase-specific local reservation.

    Calibration covers the actual compiled cone source only. It measures
    accepted/read/capture/publish/idle edges and checks source-NBA recurrence.
    No remote ACK or current-program accepted origin exists in this journal.
    """
    rec = S.load(S.A/'r2_PASS/record.json')
    pred = S.A/'prediction_r2'
    if S.sha_raw(S.A/'r2_PASS/actual.jsonl.gz') != rec['actual_journal_sha256'] or S.sha(pred/'prediction.json') != rec['prediction_sha256']:
        raise ValueError('retained journal/source calendar hash mismatch')
    model = S.load(pred/'prediction.json')
    sources = S.load(S.A/'source_snapshot/sources.json')
    for path, h in sources.items():
        file_pin(S.A/'source_snapshot/pinned'/path, h)
    S.source_contract()
    events = S.events('r2_PASS') if events is None else events
    last = -1
    for n, e in enumerate(events):
        if type(e['ordinal']) is not int or e['ordinal'] != n or uint(e['edge']) < last:
            raise ValueError('journal ordinal/edge mismatch')
        last = e['edge']
        for key, wanted in dict(rank=0, stage=0, phase=10, key_word=2149580800, reset_era=0).items():
            if type(e[key]) is not int or e[key] != wanted:
                raise ValueError('actual source owner/epoch mismatch')
    cal = S.compare(pred, events)
    if cal['result'] != 'PASS':
        raise ValueError('actual source calendar calibration failed')
    bykind = collections.defaultdict(list)
    for e in events:
        bykind[e['kind']].append(e)
    if dict(collections.Counter(e['kind'] for e in events)) != rec['actual_counts']:
        raise ValueError('actual raw category inventory differs from receipt')
    reservations = []
    for e in S.rows(pred/'upstream_prediction.jsonl'):
        if e['kind'] == 'cfg_ROM_read_accept':
            for shard in range(2):
                reservations.append(dict(id=f'cfg:{shard}:{e["word"]}', kind='cfg', domain=f'cfg{shard}', bits=2048*48, release=e['edge'], deadline=e['edge']+1))
        if e['kind'] == 'activation_field_accept':
            reservations.append(dict(id=f'activation:{e["edge"]}', kind='activation', domain='broadcast', bits=1632, release=e['edge']-17, deadline=e['edge']))
    for e in S.rows(pred/'root_prediction.jsonl'):
        reservations.append(dict(id=f'result:{e["row"]}', kind='result', domain='roots', bits=69, release=e['edge'], deadline=e['edge']+1))
    domain = lambda bits, latency, credits: dict(bits_per_edge=bits, latency_edges=latency, ACK_edges=0, retirement_kind='local_capture_visibility', credits=credits, storage_bits=bits*credits)
    domains = dict(cfg0=domain(98304, 1, 1), cfg1=domain(98304, 1, 1), broadcast=domain(1632, 17, 17), roots=domain(128*69, 1, 128))
    # Domain credits count individual root records, not whole 128-port buses.
    domains['roots']['storage_bits'] = 128*69
    reserved = R.reserve(reservations, domains)
    # These exact measured publication/capture edges were checked by compare.
    edges = {k: [min(e['edge'] for e in v), max(e['edge'] for e in v)] for k, v in bykind.items()}
    op, phase, retire = edges['op_accept'][0], edges['phase_accept'][0], edges['phase_retire'][0]
    if retire != model['absolute_edges']['adapter_retire_preedge'] or max(e['visible'] for e in reserved['events']) >= retire:
        raise ValueError('source completion before reserved publication')
    return dict(status='PASS_MEASURED_PHW10_CONE_SERVICE_CALIBRATION',
                binary_sha256=rec['binary_sha256'], source_commit=rec['source_commit'],
                compiler_sha256=rec['compiler_sha256'], source_manifest_sha256=rec['source_manifest_sha256'],
                retained_core_sha256=rec['source_sha256']['rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv'],
                current_core_sha256=S.sha(P.OUT/'inputs/core.sv.txt'),
                journal_sha256=rec['actual_journal_sha256'], prediction_sha256=rec['prediction_sha256'],
                compiled=model['compiled'], measured_counts=dict(collections.Counter(e['kind'] for e in events)),
                measured_edge_ranges=edges, calibrated_events=cal['observed_events'],
                source_specific_finite_service=dict(op_accept=op, phase_accept=phase, adapter_idle=retire,
                    measured_op_edges=retire-op, measured_phase_edges=retire-phase,
                    conditional_source_calendar_bound_edge=retire, reserved_local_last_publication=reserved['last_retirement']),
                reservation=reserved,
                unsupported=['current whole-program SHA/argv/origin', 'registered EID response value',
                    'interstage transport delivery/ACK', 'all384 expert service bounds', 'coll_busy release'],
                emission_edges_source_predicted=True, capture_edges_measured=True,
                scope='PHW10_OLDER_CORE_NATIVE_CONE_ONLY', current_program=False,
                payload_scope='Retained nonzero synthetic1 weights/input; not checkpoint payload qualification',
                reservation_scope='Source calendar wire/capture demand and fixed local slots; not new hardware buffer allocation',
                remote_service_bound=None, universal_service_bound=None, fulltoken=False,
                hardware_admission=False)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--measured-cone', action='store_true')
    a.add_argument('--enrollment', type=Path)
    a.add_argument('--plan', type=Path)
    a.add_argument('--trace', type=Path)
    a.add_argument('--out', type=Path, required=True)
    args = a.parse_args()
    if args.measured_cone:
        result = measured_cone()
    elif args.enrollment:
        p = S.load(args.enrollment)
        result = current_enrollment(p)
        if args.trace:
            if args.trace.resolve() != Path(p['journal_path']).resolve():
                raise ValueError('trace is not enrolled actual journal')
            if not args.plan:
                a.error('--trace requires reviewed --plan')
            result = current_join(p, args.plan)
    else:
        a.error('require --measured-cone or --enrollment')
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
