#!/usr/bin/env python3
"""Model-only bank-rearm / published-VM lease / accepted-deadline join.

Normalized test packets are not compiled callbacks. Actual calibration enters
through strict current-PHW10 enrollment and the existing source-read gate.
No launcher, payload-seat allocation, idle-based consumer guard or deadline cap.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import dsrom_I66_consumer_deadline as D
import dsrom_I66_source_interlock as I
import dsrom_I66_phase_protocol_join as H

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_I66_bank_VM_deadline_join_20261003'


def key(identity, source=None):
    D.operation_id(identity, D.source_model() if source is None else source)
    return json.dumps(identity, sort_keys=True)


def context_key(c):
    values = [c['node']]
    for name, bits in [('rank', 2), ('generation', 32), ('user', 32), ('xversion', 32), ('seq', 8), ('accept_edge', None)]:
        values.append(I.uint(c[name], bits))
    return tuple(values)


def admission_check(trace, admissions):
    """Bind actual core issue, SU front latch, and accepted vector identity.

    Gates are normalized source-equivalent conditions from compiled callbacks,
    including the applicable window guard; a false nonapplicable raw signal is
    not itself a failed gate. Actual compile provenance is checked separately.
    """
    source = D.source_model()
    waits = {p['consumer_node']: p['wait_mask'] for o in source['obligations'] for p in o['first_static_consumer']}
    target = [c for c in trace['vector_contexts'] if c['node'] in waits]
    if len(admissions) != len(target):
        raise ValueError('complete source admission-to-vector association required')
    indexed = {}
    for a in admissions:
        c = a['vector_context']
        ck = context_key(c)
        if ck in indexed or c not in target:
            raise ValueError('foreign/duplicate/stale accepted vector')
        if a['node'] != c['node'] or I.uint(a['front_pc'], 14) != I.uint(c['accepted_front_pc'], 14):
            raise ValueError('source accepted PC differs from latched vector command')
        if a['state'] != 'S_ISSUE' or I.uint(a['d_unit'], 3) != 2 or I.uint(a['d_wait'], 5) != waits[a['node']]:
            raise ValueError('source SU admission decode differs')
        expected_wait = I.waited(a['d_wait'], a['idles'], a['gos'])
        if I.uint(a['waited'], 1) != int(expected_wait) or not expected_wait:
            raise ValueError('source wait predicate not satisfied')
        for gate in ['unit_ready', 'q_gate', 'kv_gate', 'm0_gate', 'window_gate', 'healthy_reset_epoch']:
            if I.uint(a[gate], 1) != 1:
                raise ValueError('actual admission gate false: ' + gate)
        issue = I.uint(a['core_issue_edge'])
        front = I.uint(a['front_accept_edge'])
        if front != issue + 1 or front > I.uint(c['accept_edge']):
            raise ValueError('registered SU go/front/vector edge association')
        indexed[ck] = a
    if set(indexed) != {context_key(c) for c in target}:
        raise ValueError('missing source admission association')
    return indexed


def analyze_packets(trace, admissions, banks, minimum_credit_delay):
    """Pure normalized schema checker; never returns actual-enrollment credit.

    Source-bank release may precede SU reads. A separate address/version lease
    begins at producer admission and survives actual read/tag tails. This does
    not reserve a downstream payload seat or infer a timed consumer promise.
    """
    trace, admissions, banks = copy.deepcopy((trace, admissions, banks))
    delay = I.uint(minimum_credit_delay)
    if not delay:
        raise ValueError('positive captured credit return required')
    if trace['timebase'] != 'native_core_clk':
        raise ValueError('qualified shared native clock required; no implicit CDC mapping')
    admission_check(trace, admissions)
    source = D.source_model()
    phase_key = lambda identity: key(identity, source)
    grouped = {}
    for e in trace['events']:
        k = phase_key(e['identity'])
        grouped.setdefault(k, []).append(e)
    expected = {phase_key(e['identity']) for e in trace['events'] if e['kind'] == 'producer_accept'}
    if not expected or set(grouped) != expected or len(banks) != len(expected):
        raise ValueError('complete bank/producer coverage required')
    reads = [e for e in trace['events'] if e['kind'] == 'consumer_VM_read']
    bound = D.bind_actual_read_tags(reads, trace['read_X_tags'])
    if any(e.get('source_seq') != b['source_seq'] for e, b in zip(reads, bound)):
        raise ValueError('consumer source sequence differs from actual R+2 tag')
    # Existing source checker validates full576 values, addresses, identities,
    # source-healthy retirement and observed consumer ownership. Slots below are
    # OBSERVED publications for schema checking, not a reserved-service proof.
    observed_slots = [dict(identity=e['identity'], row=e['row'], postNBA_edge=e['edge'])
                      for e in trace['events'] if e['kind'] == 'home_postNBA']
    calibrated = D.calibrate(trace, observed_slots)
    bank_lifetimes = {}; VM_lifetimes = []; seen = set(); results = []
    for bank in banks:
        k = phase_key(bank['identity'])
        if k in seen or k not in expected:
            raise ValueError('spent or foreign phase identity')
        seen.add(k)
        events = grouped[k]
        accepts = [e for e in events if e['kind'] == 'producer_accept']
        if len(accepts) != 1:
            raise ValueError('actual producer acceptance must be unique')
        origin = I.uint(accepts[0]['edge'])
        visible = {I.uint(e['row'], 10): I.uint(e['edge']) for e in events if e['kind'] == 'home_postNBA'}
        idle = next(e['edge'] for e in events if e['kind'] == 'source_idle')
        last_read = max(e['edge'] for e in events if e['kind'] == 'consumer_VM_read')
        if type(bank['bank_id']) is not str or not bank['bank_id']:
            raise ValueError('named actual source bank owner required')
        bank_accept = I.uint(bank['bank_phase_accept_edge'])
        rearm = I.uint(bank['bank_rearm_postNBA_edge'])
        ack_retire = I.uint(bank['last_packet_ACK_retire_edge'])
        if I.uint(bank['packet_outstanding_after_last_ACK'], 32) != 0:
            raise ValueError('bank rearm retains outstanding packet debt')
        VM_release = I.uint(bank['VM_lease_release_postNBA_edge'])
        if bank_accept < origin or ack_retire < bank_accept:
            raise ValueError('bank/packet lifecycle precedes accepted origin')
        credits = {}
        for e in bank['row_credit_returns']:
            row = I.uint(e['row'], 10); edge = I.uint(e['postNBA_edge'])
            if row >= 576 or row in credits or edge < visible[row] + delay:
                raise ValueError('source credit before owned visibility/positive return or duplicate row')
            credits[row] = edge
        if set(credits) != set(range(576)):
            raise ValueError('complete576 source row credits required')
        if rearm < max(max(credits.values()), ack_retire, idle):
            raise ValueError('bank rearmed before visibility/credit/packet/source retirement')
        if VM_release < last_read + 2:
            raise ValueError('VM address/version lease released before actual R+2 tail')
        owner = (bank['identity']['rank'], bank['identity']['owner_stage'], bank['bank_id'])
        bank_lifetimes.setdefault(owner, []).append((bank_accept, rearm, k))
        ob = D.operation_id(bank['identity'], source)
        VM_lifetimes.append((origin, VM_release, bank['identity']['rank'], *ob['output_VM_elements'], k))
        results.append(dict(identity=bank['identity'], bank_rearm_postNBA_edge=rearm,
                            VM_lease_release_postNBA_edge=VM_release,
                            source_bank_may_rearm_before_SU_read=rearm < min(e['edge'] for e in events if e['kind'] == 'consumer_VM_read')))
    for lives in bank_lifetimes.values():
        ordered = sorted(lives)
        if any(nxt[0] <= prev[1] for prev, nxt in zip(ordered, ordered[1:])):
            raise ValueError('same-edge or overlapping source bank reuse')
    for i, a in enumerate(VM_lifetimes):
        for b in VM_lifetimes[i+1:]:
            if (a[2] == b[2] and max(a[0], b[0]) <= min(a[1], b[1])
                    and max(a[3], b[3]) < min(a[4], b[4])):
                raise ValueError('live VM frame alias across operation/version leases')
    peak = {}
    for rank in {a[2] for a in VM_lifetimes}:
        # Allocation is preedge; release is postNBA, so same-edge allocations
        # still coexist with the ending lease. Count intervals inclusively.
        relevant = [a for a in VM_lifetimes if a[2] == rank]
        peak[rank] = max(sum(a[0] <= edge <= a[1] for a in relevant)
                         for edge in {a[0] for a in relevant})
    return dict(scope='NORMALIZED_SCHEMA_CHECK_ONLY', operations=results,
                per_rank_supplied_trace_peak_frames=peak,
                read_edges=calibrated['operations'], actual_current_enrollment=False,
                finite_actual_service_bound=None, reserved_service_proved=False,
                hardware_admission=False, payload_seat_allocated=False)



def publication_bundle_check(trace, banks, bundles, minimum_credit_delay, reviewed_capacities):
    """Require phase-wide writer veto and protocol on the same owned edges."""
    source = D.source_model()
    phase_key = lambda identity: key(identity, source)
    expected = {phase_key(b['identity']): b for b in banks}
    if len(bundles) != len(expected) or set(reviewed_capacities) != set(expected):
        raise ValueError('complete phase writer/protocol/capacity bindings required')
    seen = set()
    for bundle in bundles:
        k = phase_key(bundle['identity'])
        if k not in expected or k in seen:
            raise ValueError('foreign/duplicate phase publication bundle')
        seen.add(k)
        b = expected[k]; ident = b['identity']; ctx = bundle['lease']['context']
        required = dict(stage=ident['owner_stage'], rank=ident['rank'], expert=ident['expert'],
                        phase=ident['phase'], key_word=ident['key_word'], generation=ident['generation'],
                        user=ident['user'], xversion=ident['xversion'], pc=int(ident['node'].split('I')[1]))
        if ctx != required:
            raise ValueError('cross-journal source phase identity differs')
        if bundle['lease']['release_edge'] != b['VM_lease_release_postNBA_edge']:
            raise ValueError('writer exclusion ends before VM lease release')
        H.join(bundle['lease'], bundle['samples'], bundle['protocol_context'],
               bundle['protocol_journal'], minimum_credit_delay, reviewed_capacities[k])
        pubs = {e['row']: (e['edge'], e['address'], e['data']) for e in trace['events']
                if e['kind'] == 'home_postNBA' and phase_key(e['identity']) == k}
        formatted = {r['row']: H.O.source_formatter(r, bundle['lease']['descriptor']) for r in bundle['lease']['records']}
        protocol_pubs = {e['row']: (int(H.Fraction(e['time'])), *formatted[e['row']]) for e in bundle['protocol_journal'] if e['kind'] == 'home_visible'}
        credits = {e['row']: e['postNBA_edge'] for e in b['row_credit_returns']}
        protocol_credits = {e['row']: int(H.Fraction(e['time'])) for e in bundle['protocol_journal'] if e['kind'] == 'credit_return_capture'}
        if pubs != protocol_pubs or credits != protocol_credits:
            raise ValueError('publication/credit edges differ across accepted journals')
    return True


def enrolled_join(provenance, slots_path, service_path, lifecycle_path):
    """Actual entry: no fake-packet/source-default enrollment fallback."""
    # Admission/source hashes/program words/native read contexts/calendars are
    # mandatory first; a model-only journal cannot bypass these gates.
    qualified = D.enrolled_join(provenance, slots_path, service_path)
    q = D.S.load(Path(provenance['qualification_path']))
    binding = q['bank_VM_deadline_binding']
    D.J.file_pin(lifecycle_path, binding['lifecycle_sha256'])
    if (not binding['callback_source_files'] or
            not set(binding['callback_source_files'].items()) <= set(q['source_files'].items())):
        raise ValueError('bank/admission/VM lease callbacks not compiled in enrolled closure')
    lifecycle = D.S.load(lifecycle_path)
    trace = D.S.load(Path(provenance['journal_path']))
    result = analyze_packets(trace, lifecycle['admissions'], lifecycle['banks'],
                             lifecycle['minimum_credit_delay'])
    publication_bundle_check(trace, lifecycle['banks'], lifecycle['phase_bundles'],
                             lifecycle['minimum_credit_delay'], binding['reviewed_bank_capacities'])
    if any(peak < model()['static_frame_lower_bound']
           for peak in result['per_rank_supplied_trace_peak_frames'].values()):
        raise ValueError('enrolled trace contradicts source four-frame floor')
    result.update(actual_current_enrollment=True, deadline_and_reserved_service=qualified,
                  scope='ENROLLED_L0_TWELVE_W1_W3_TP4_ONLY',
                  physical_c9_phase_reset_CDC_qualified=False,
                  composed_physical_deadline_proved=False)
    return result


def model():
    I.sources()
    pins = json.loads((OUT/'source_pins.json').read_text())
    for path, expected in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('source/dependency pin changed: ' + path)
    source = D.source_model()
    rows = []
    for o in source['obligations']:
        p = o['first_static_consumer'][0]
        rows.append(dict(producer=o['producer_node'], consumer=p['consumer_node'],
                         operand=p['operand'], wait_mask=p['wait_mask'], frame=o['output_VM_elements']))
    if [r['wait_mask'] for r in rows] != [2, 2] + [0] * 10:
        raise ValueError('source first-consumer wait masks changed')
    # Conditional static lower bound: accepted producer allocations precede
    # their first consumer instruction. Actual read/tag tails can only extend.
    live = {}
    for pc in range(66, 99):
        live[pc] = [r['producer'] for r in rows
                    if int(r['producer'].split('I')[1]) <= pc < int(r['consumer'].split('I')[1])]
    if live[69] != ['L0.I66', 'L0.I67', 'L0.I68', 'L0.I69']:
        raise ValueError('source simultaneous frame obligation changed')
    return dict(scope='SOURCE_AND_UNINSTALLED_CALLBACK_SCHEMA_ONLY', source_pins=pins, first_consumers=rows,
        all_first_consumers_explicit_ME_wait=False, all_first_consumers_explicit_QE_wait=False,
        source_wait2='SU only; other ten source operand obligations wait0',
        static_frame_lower_bound=max(map(len, live.values())), frames_at_I69=live[69],
        owned_VM_words_at_four_frame_floor=4*576,
        word_count_scope='Existing VM address ownership aperture, not new payload seats/storage.',
        static_floor_not_exact_peak=True, actual_peak_with_SU_Rplus2_tails=None,
        two_lifetimes='Bank: actual visibility + positive captured credits + packet ACK/source retire -> rearm. VM address/version: actual associated SU read R + observed R+2 tag -> release.',
        source_consumer_guard='No consumer is fenced by ME/QE wait bits. Require actual accepted source vector/read association or separately priced implemented source admission guard; rom_idle alone is insufficient.',
        static_program_guard='Bank for I66 must be rearmable for I67 before I70 reads both; holding bank until future SU read blocks in-order progress.',
        publication_gate='Actual entry also requires phase-wide all-writer exclusion/all-root interception bundles, complete source protocol, reviewed capacity and identical publication/credit edges; no independently passing journal shortcut.',
        callback_cost='Passive normalized fields only; no compiled callback or added hardware. A retained phase/version ledger and any admission guard still require state/ports/model/context timing price.',
        identity='Full169 context/user32 plus separate shard1; no epoch alias or payload-seat assumption.',
        clocks='c9d19ed59, actual root phase/reset, visibility and positive feedback/CDC required; no nominal edge conversion.',
        enrollment_entry='enrolled_join -> current_PHW10 source/binary/four-program/field + actual read-tag calibration + reviewed reserved service + compiled lifecycle callback closure',
        lower_bound_predecessor='69432b644657ec84073ebb8178f4f90520946886 recorded three previously published plus one active identity; this successor explicitly counts FOUR allocated/protected frames.',
        status='BOUND_MISSING', actual_current_journal=None, finite_actual_consumer_deadline=None,
        new_job=False, RTL_GO=False, fulltoken=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path)
    p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    text = json.dumps(model(), indent=2, sort_keys=True) + '\n'
    if a.verify:
        if text != (OUT/'model.json').read_text():
            raise SystemExit('model mismatch')
        print('source replay PASS; actual accepted deadline/peak BOUND_MISSING')
    elif a.out:
        a.out.write_text(text)
    else:
        print(text, end='')
