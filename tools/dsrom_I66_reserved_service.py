"""Finite reservation theorem for source-owned, no-ready I66 boundaries.

No network is selected here. A provider must guarantee the reserved slots,
capture space, fixed delivery latency and causal ACK delay before accepting.
The supplied complete source calendar is phase-specific; never clone EID0.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_I66_reserved_service_20261002'


def integer(x, minimum=0):
    if type(x) is not int or x < minimum:
        raise ValueError('invalid integer')
    return x


def reserve(events, domains):
    """Reserve a shared domain, derive maximum capture/ACK-held capacity.

    Slots are charged once across ALL event classes. Arrival latency starts
    after the final serialized chunk. Same-edge ACK cannot release a credit
    for a new no-ready arrival: storage counts both at that boundary.
    Inputs are copied; rejection cannot mutate a caller's reservation.
    """
    events = copy.deepcopy(events)
    capacities = {}
    for name, d in domains.items():
        capacities[name] = integer(d['bits_per_edge'], 1)
        integer(d['latency_edges'], 1)
        kind = d.get('retirement_kind', 'causal_ACK')
        if kind not in ('causal_ACK', 'local_capture_visibility'):
            raise ValueError('unknown retirement provider')
        integer(d['ACK_edges'], 1 if kind == 'causal_ACK' else 0)
    used = collections.defaultdict(int)
    result = []
    seen = set()
    for e in sorted(events, key=lambda e: (e['release'], e['deadline'], e['id'])):
        if e['id'] in seen or e['domain'] not in domains:
            raise ValueError('duplicate identity or unknown domain')
        seen.add(e['id'])
        release = integer(e['release'])
        deadline = integer(e['deadline'])
        left = integer(e['bits'], 1)
        d = domains[e['domain']]
        chunks = []
        for edge in range(release, deadline - d['latency_edges'] + 1):
            slot = (e['domain'], edge)
            n = min(left, capacities[e['domain']] - used[slot])
            if n:
                used[slot] += n
                chunks.append([edge, n])
                left -= n
            if not left:
                break
        if left:
            raise ValueError('reserved delivery deadline infeasible: ' + e['id'])
        visible = chunks[-1][0] + d['latency_edges']
        result.append(dict(e, chunks=chunks, visible=visible,
                           retirement=visible+d['ACK_edges'],
                           ACK=visible+d['ACK_edges'] if d.get('retirement_kind', 'causal_ACK')=='causal_ACK' else None))
    requirements = {}
    for name, d in domains.items():
        ev = [e for e in result if e['domain'] == name]
        boundaries = sorted({t for e in ev for t in (e['release'], e['retirement'])})
        peak_n = peak_bits = 0
        for t in boundaries:
            active = [e for e in ev if e['release'] <= t and
                      (t <= e['retirement'] if e['ACK'] is not None else t < e['retirement'])]
            peak_n = max(peak_n, len(active))
            peak_bits = max(peak_bits, sum(e['bits'] for e in active))
        requirements[name] = dict(capture_and_ACK_held_credits=peak_n,
                                  capture_and_ACK_held_bits=peak_bits)
        if integer(d['credits']) < peak_n or integer(d['storage_bits']) < peak_bits:
            raise ValueError('insufficient reserved no-ready capture/ACK storage: ' + name)
    return dict(events=result, requirements=requirements,
                reserved_slot_bits=[dict(domain=k[0], edge=k[1], bits=v)
                                    for k, v in sorted(used.items())],
                last_retirement=max((e['retirement'] for e in result), default=0))


def compose(calendar, events, domains):
    """Conditional successful service bound, gated by complete source calendar.

    Source arithmetic/II validity is an independent prerequisite. The model
    checks identities, all 576 row obligations and transport deadlines, not
    numerical RTL equivalence or physical closure.
    """
    c = copy.deepcopy(calendar)
    for k in ('accepted_edge', 'source_idle_edge', 'first_VM_read_edge'):
        integer(c[k])
    if c['source_idle_edge'] < c['accepted_edge'] or c['first_VM_read_edge'] < c['accepted_edge']:
        raise ValueError('source edge precedes owner acceptance')
    if type(c['PHW']) is not int or type(c['X_ROM']) is not int or c['PHW'] != 10 or c['X_ROM'] != 1:
        raise ValueError('current phase/source binding required')
    for k in ('source_calendar_sha256', 'phase_source_sha256'):
        h = c[k]
        if not isinstance(h, str) or len(h)!=64 or any(ch not in '0123456789abcdef' for ch in h):
            raise ValueError('source SHA256 required')
    identity = c['identity']
    if set(identity) != {'rank', 'generation', 'user', 'EID', 'stage', 'phase', 'key_word'}:
        raise ValueError('complete causal identity required')
    for k in identity:
        integer(identity[k])
    if identity['rank'] >= 4 or identity['EID'] >= 384:
        raise ValueError('rank/EID bounds')
    eid = identity['EID']
    if identity['stage'] != (0 if eid < 288 else 1) or identity['phase'] != (10+3*eid if eid < 288 else 3*(eid-288)) or identity['key_word'] != 0x80000000+2097152+4096*eid:
        raise ValueError('source owner/key/phase mismatch')
    if any(e['identity'] != identity for e in events):
        raise ValueError('stale event owner')
    normalized = [{k:v for k,v in e.items() if k != 'identity'} for e in events]
    if normalized != c['source_boundary_events']:
        raise ValueError('source emission/capture schedule changed or incomplete')
    if c['source_idle_edge'] != c['source_retirement_edge']:
        raise ValueError('source retirement moved before source recurrence')
    r = reserve(events, domains)
    rows = [e for e in r['events'] if e['kind'] == 'result']
    if len(rows) != 576 or {e['row'] for e in rows} != set(range(576)):
        raise ValueError('all576 result identities required')
    if any(e['address'] != 398720+e['row'] or e['release'] < c['accepted_edge'] for e in rows):
        raise ValueError('result destination or causal origin mismatch')
    inputs = [e for e in r['events'] if e['kind'] == 'input']
    if len(inputs) != 1 or inputs[0]['bits'] != 5120*32 or inputs[0]['visible'] > c['first_VM_read_edge']:
        raise ValueError('input K5120 visibility before first read required')
    # Old source idle and old ACK state must be visible before reuse.
    completion = max(c['source_idle_edge'], r['last_retirement']) + 1
    return dict(status='PASS_CONDITIONAL_RESERVED_SERVICE', identity=identity,
                accepted_edge=c['accepted_edge'], successful_completion_edge=completion,
                successful_service_edges=completion-c['accepted_edge'], reservation=r,
                provider_obligations=['guaranteed exclusive/shared reserved slots for entire operation',
                    'all no-ready emissions captured with derived storage and credits',
                    'delivery/causal ACK by reserved edges without retry or loss',
                    'source phase calendar/II bound independently qualified',
                    'all576 postNBA destination visibility plus source-idle receipt'],
                current_provider_proved=False, runtime_observed=False,
                physical_admission=False, fulltoken=False)


def demand_example():
    """Current PHW10 EID0 source-demand example, not all-expert latency transfer.

    Default network values describe a reservation request, not an installed
    provider. Maxwell's 1681/108-bit proposal is preserved as a proposed ABI.
    Its older BST2 calendar is NOT used; BST17 PHW10 source calendars are used.
    """
    p = ROOT/'results/rtl/dsrom_I66_standalone_calibration_20261002/prediction_r2'
    rows = lambda name: [json.loads(s) for s in (p/name).read_text().splitlines()]
    ident = dict(rank=0, generation=1, user=0, EID=0, stage=0, phase=10, key_word=2149580800)
    # Reserve input before owner acceptance: 20x8192-bit edges, then registered delivery.
    shift = 22-10
    events = [dict(id='input', kind='input', domain='shared', bits=5120*32,
                   release=0, deadline=22, identity=ident)]
    for x in rows('upstream_prediction.jsonl'):
        if x['kind'] == 'activation_field_accept':
            events.append(dict(id='activation:'+str(x['edge']), kind='activation', domain='shared',
                bits=1681, release=x['edge']-17+shift, deadline=x['edge']+shift, identity=ident))
        if x['kind'] == 'cfg_ROM_read_accept':
            for shard in range(2):
                events.append(dict(id='cfg:'+str(shard)+':'+str(x['word']), kind='cfg', domain='local_cfg'+str(shard),
                    bits=2048*48, release=x['edge']+shift, deadline=x['edge']+1+shift, identity=ident))
    for x in rows('root_prediction.jsonl'):
        events.append(dict(id='result:'+str(x['row']), kind='result', domain='shared' if x['root'] >= 64 else 'local_root', bits=108,
            row=x['row'], address=398720+x['row'], release=x['edge']+shift,
            deadline=x['edge']+1+shift, identity=ident))
    domains=dict(shared=dict(bits_per_edge=8192, latency_edges=1, ACK_edges=1,
                             credits=1000, storage_bits=1000000),
                 local_root=dict(bits_per_edge=64*108, latency_edges=1, ACK_edges=0,
                                 retirement_kind='local_capture_visibility',
                                 credits=64, storage_bits=64*108))
    for shard in range(2):
        domains['local_cfg'+str(shard)] = dict(bits_per_edge=2048*48, latency_edges=1, ACK_edges=0,
                                              retirement_kind='local_capture_visibility',
                                              credits=1, storage_bits=2048*48)
    h = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    calendar=dict(identity=ident, accepted_edge=22, first_VM_read_edge=45+shift,
                  source_idle_edge=422+shift, PHW=10, X_ROM=1,
                  source_calendar_sha256=h(p/'prediction.json'),
                  phase_source_sha256=h(p/'img/spine_phase.hex'),
                  source_retirement_edge=422+shift,
                  source_boundary_events=[{k:v for k,v in e.items() if k != 'identity'} for e in events])
    result=compose(calendar, events, domains)
    return dict(schema='opentallas.I66.reserved-service.v1', example=result,
                input=dict(calendar=calendar, events=events, domains=domains),
                historical_PHW6_inherited=False, all384_service_transferred=False,
                default_stage_link_tx_selected=False, parameter_values_are_reservation_request=True,
                Maxwell_join='wire-deadline demands1681/108; selected r7 caller NP2048/R64/PHW10; no physical deadline transfer',
                Nash_join='exact622 owner phase/tensor/rank slices; one software command debt ledger',
                source_count=dict(K=5120, input_FP32_reads=80, cfg_reads_per_pair=25, result_rows=576),
                callbacks=['actual registered EID response and source owner acceptance',
                    'input delivery identity before VM read', 'each cfg read/capture before GO',
                    'preBST emission and both shard field captures', 'each root identity and accepted capture',
                    'each postNBA VM destination publication', 'all causal packet ACKs', 'source idle after busy'],
                observer_model=dict(simulation_only=True, hardware_ports=0, hardware_state_bits=0,
                    proposed_wrapper_copy=True, default_off=True,
                    observation_fields='preedge core/adapter/phase/read/write; postedge VM snapshot',
                    observer_state_bits=10400,
                    observer_state='8064bit root writer snapshot +2112bit CDMA snapshot +128bit counters +96bit loop indices; simulator-only',
                    compile='new wrapper copy requires fresh full current source frontend; no old PHW6 objects reused',
                    measured_full_geometry_frontend_peak_bytes=54214520832,
                    measured_full_geometry_frontend_seconds=625.017,
                    measured_generated_bytes=4181161051,
                    estimates_are_context_not_current_exact_measurement=True,
                    no_compile_or_runtime_admission=True))


if __name__ == '__main__':
    a=argparse.ArgumentParser();a.add_argument('--out', type=Path, required=True)
    a.add_argument('--plan', type=Path, help='phase-specific calendar/events/domains reservation request')
    args=a.parse_args()
    if args.plan:
        p=json.loads(args.plan.read_text())
        result=compose(p['calendar'],p['events'],p['domains'])
    else:
        result=demand_example()
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
