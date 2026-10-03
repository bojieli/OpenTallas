import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
import dsrom_I66_bank_VM_deadline_join as B


def fixture(pair=(66, 67), alias=False):
    # Synthetic normalized callbacks. Not a current program accepted journal.
    obs = B.D.source_model()['obligations']
    events, banks, contexts, admissions, tags = [], [], [], [], []
    for j, pc in enumerate(pair):
        ob = next(o for o in obs if o['producer_node'] == f'L0.I{pc}')
        choice = ob['phase_choices'][0]
        ident = dict(node=ob['producer_node'], expert=0, rank=0,
                     generation=1+j if alias else 1, user=0x1234ffff, xversion=1,
                     owner_stage=choice['stage'], phase=choice['phase'], key_word=choice['source_key_word'])
        origin = 10 + 15*j
        events.append(dict(kind='producer_accept', edge=origin, identity=ident))
        for row in range(576):
            events.append(dict(kind='home_postNBA', edge=origin+1+row//128,
                               identity=ident, row=row, address=ob['output_VM_elements'][0]+row, data=0x45a00000))
        events.append(dict(kind='source_idle', edge=origin+6, identity=ident,
                           busy_seen=1, adapter_fault=0, spine_fault=0))
        read_start = 100 + (100*j if alias else 0)
        target = ob['first_static_consumer'][0]
        for row in range(576):
            events.append(dict(kind='consumer_VM_read', edge=read_start+row//256,
                               identity=ident, valid=1, src=0, source_seq=9,
                               port='abcd'.index(target['operand']),
                               address=ob['output_VM_elements'][0]+row, data_pre=0x45a00000))
        c = dict(node=target['consumer_node'], rank=0, generation=ident['generation'],
                 user=ident['user'], xversion=1, seq=9,
                 accepted_front_pc=int(target['consumer_node'].split('I')[1]),
                 accept_edge=read_start-10, done_edge=read_start+50)
        if c not in contexts:
            contexts.append(c)
            admissions.append(dict(node=c['node'], vector_context=c,
                front_pc=c['accepted_front_pc'], state='S_ISSUE', d_unit=2,
                d_wait=target['wait_mask'], idles=2 if target['wait_mask'] else 0,
                gos=0, waited=1, unit_ready=1, q_gate=1, kv_gate=1, m0_gate=1,
                window_gate=1, healthy_reset_epoch=1,
                core_issue_edge=read_start-12, front_accept_edge=read_start-11))
            tags += [dict(edge=read_start+k+2, rank=0, generation=ident['generation'],
                          user=ident['user'], xversion=1, seq=9, valid=1, fault=0) for k in range(3)]
        banks.append(dict(identity=ident, bank_id='logical_two_shard_capture_pair',
                          bank_phase_accept_edge=origin, bank_rearm_postNBA_edge=origin+7,
                          last_packet_ACK_retire_edge=origin+7, packet_outstanding_after_last_ACK=0,
                          VM_lease_release_postNBA_edge=read_start+4,
                          row_credit_returns=[dict(row=r, postNBA_edge=origin+3+r//128) for r in range(576)]))
    events.sort(key=lambda e:e['edge'])
    trace=dict(timebase='native_core_clk', role='BASELINE_CURRENT_PROGRAM',
               vector_contexts=contexts, read_X_tags=tags,
               events=[dict(e, ordinal=i) for i,e in enumerate(events)])
    return trace, admissions, banks


def test_bank_rearms_before_shared_SU_read_but_VM_leases_overlap():
    trace, admissions, banks = fixture()
    before = copy.deepcopy((trace, admissions, banks))
    result = B.analyze_packets(trace, admissions, banks, 2)
    assert result['per_rank_supplied_trace_peak_frames'] == {0:2}
    assert all(o['source_bank_may_rearm_before_SU_read'] for o in result['operations'])
    assert not result['actual_current_enrollment']
    assert result['finite_actual_service_bound'] is None
    assert (trace, admissions, banks) == before


def test_wait0_consumer_requires_actual_admission_not_producer_idle():
    trace, admissions, banks = fixture((68, 69))
    assert admissions[0]['d_wait'] == 0
    assert admissions[0]['idles'] == 0
    assert B.analyze_packets(trace, admissions, banks, 2)['operations']
    admissions[0]['unit_ready'] = 0
    with pytest.raises(ValueError, match='admission gate false'):
        B.analyze_packets(trace, admissions, banks, 2)


@pytest.mark.parametrize('mutation', [
    'false_ready', 'all_gates_false', 'wrong_wait', 'stale_vector', 'wrong_pc',
    'float_gate', 'bool_gate', 'wrong_front_edge', 'missing_admission',
    'early_credit', 'same_edge_rearm', 'ACK_pending', 'source_still_busy',
    'packet_debt_pending', 'VM_release_at_last_read', 'VM_release_before_Xtag', 'missing_tag',
    'wrong_tag_user_high16', 'wrong_bank_user_high16', 'missing_row_credit',
    'duplicate_credit', 'partial_bank_coverage', 'float_rearm', 'wrong_clock'])
def test_reject_before_mutation(mutation):
    t, a, b = fixture()
    if mutation == 'false_ready':a[0]['unit_ready']=0
    elif mutation == 'all_gates_false':
        for k in ['unit_ready','q_gate','kv_gate','m0_gate','window_gate']:a[0][k]=0
    elif mutation == 'wrong_wait':a[0]['d_wait']=4
    elif mutation == 'stale_vector':a[0]=copy.deepcopy(a[0]);a[0]['vector_context']['generation']=2
    elif mutation == 'wrong_pc':a[0]['front_pc']=71
    elif mutation == 'float_gate':a[0]['unit_ready']=1.0
    elif mutation == 'bool_gate':a[0]['unit_ready']=True
    elif mutation == 'wrong_front_edge':a[0]['front_accept_edge']=a[0]['core_issue_edge']
    elif mutation == 'missing_admission':a.clear()
    elif mutation == 'early_credit':b[0]['row_credit_returns'][0]['postNBA_edge']=11
    elif mutation == 'same_edge_rearm':b[0]['bank_rearm_postNBA_edge']=25
    elif mutation == 'ACK_pending':b[0]['last_packet_ACK_retire_edge']=18
    elif mutation == 'source_still_busy':b[0]['bank_rearm_postNBA_edge']=15
    elif mutation == 'packet_debt_pending':b[0]['packet_outstanding_after_last_ACK']=1
    elif mutation == 'VM_release_at_last_read':b[0]['VM_lease_release_postNBA_edge']=102
    elif mutation == 'VM_release_before_Xtag':b[0]['VM_lease_release_postNBA_edge']=103
    elif mutation == 'missing_tag':t['read_X_tags'].pop()
    elif mutation == 'wrong_tag_user_high16':t['read_X_tags'][0]['user'] &= 0xffff
    elif mutation == 'wrong_bank_user_high16':b[0]=copy.deepcopy(b[0]);b[0]['identity']['user'] &= 0xffff
    elif mutation == 'missing_row_credit':b[0]['row_credit_returns'].pop()
    elif mutation == 'duplicate_credit':b[0]['row_credit_returns'][1]=dict(b[0]['row_credit_returns'][0])
    elif mutation == 'partial_bank_coverage':b.pop()
    elif mutation == 'float_rearm':b[0]['bank_rearm_postNBA_edge']=17.0
    elif mutation == 'wrong_clock':t['timebase']='nominal_3to4_CDC'
    before=copy.deepcopy((t,a,b))
    with pytest.raises(ValueError):B.analyze_packets(t,a,b,2)
    assert (t,a,b)==before


def test_equal_payload_does_not_permit_overlapping_VM_version_alias():
    t,a,b=fixture((66,66), alias=True)
    # Source-bank lifetimes are disjoint and both packet ledgers drain; a second
    # generation nevertheless overwrites the identical live VM address frame.
    assert b[0]['bank_rearm_postNBA_edge'] < b[1]['bank_phase_accept_edge']
    with pytest.raises(ValueError, match='live VM frame alias'):
        B.analyze_packets(t,a,b,2)


def test_static_minimum_four_is_not_actual_peak_or_payload_allocation():
    m=B.model()
    assert m['frames_at_I69']==['L0.I66','L0.I67','L0.I68','L0.I69']
    assert m['static_frame_lower_bound']==4
    assert m['owned_VM_words_at_four_frame_floor']==2304
    assert m['actual_peak_with_SU_Rplus2_tails'] is None
    assert [x['wait_mask'] for x in m['first_consumers']]==[2,2]+[0]*10
    assert not m['all_first_consumers_explicit_ME_wait']
    assert not m['all_first_consumers_explicit_QE_wait']


def test_actual_entry_has_no_normalized_fixture_fallback(monkeypatch, tmp_path):
    called=[]
    def deny(*args):
        called.append(args)
        raise ValueError('current PHW10 enrollment unavailable')
    monkeypatch.setattr(B.D, 'enrolled_join', deny)
    with pytest.raises(ValueError, match='enrollment unavailable'):
        B.enrolled_join({}, tmp_path/'slots', tmp_path/'service', tmp_path/'life')
    assert len(called)==1


def test_actual_publication_cannot_omit_phase_wide_writer_ledger():
    trace, admissions, banks = fixture()
    with pytest.raises(ValueError, match='complete phase writer/protocol/capacity'):
        B.publication_bundle_check(trace, banks, [], 2, {})


def publication_case():
    # Reuse the preserved phase/protocol fixture, not its times as a deadline.
    import importlib.util
    path=Path(__file__).with_name('test_dsrom_I66_phase_protocol_join.py')
    spec=importlib.util.spec_from_file_location('phase_fixture', path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    lease, samples, ctx, protocol=module.case()
    ident=dict(node='L0.I66', owner_stage=ctx['stage'],
               **{k:ctx[k] for k in ['rank','expert','phase','key_word','generation','user','xversion']})
    bank=dict(identity=ident, VM_lease_release_postNBA_edge=lease['release_edge'],
              row_credit_returns=[dict(row=e['row'],postNBA_edge=int(e['time'])) for e in protocol if e['kind']=='credit_return_capture'])
    trace=dict(events=[dict(kind='home_postNBA', identity=ident, row=e['row'],
                           edge=int(e['time']), address=398720+e['row'],data=e['row']+1)
                       for e in protocol if e['kind']=='home_visible'])
    bundle=dict(identity=ident, lease=lease, samples=samples, protocol_context=ctx, protocol_journal=protocol)
    return trace,[bank],[bundle],{B.key(ident):2}


def test_complete_publication_protocol_bank_join_schema_only():
    trace,banks,bundles,capacities=publication_case()
    assert B.publication_bundle_check(trace,banks,bundles,2,capacities)


@pytest.mark.parametrize('mutation',['value','credit','identity','competitor'])
def test_independently_valid_journals_need_exact_cross_association(mutation):
    trace,banks,bundles,capacities=publication_case()
    if mutation=='value':trace['events'][0]['data'] ^= 1
    elif mutation=='credit':banks[0]['row_credit_returns'][0]['postNBA_edge']+=1
    elif mutation=='identity':bundles[0]['lease']['context']=dict(bundles[0]['lease']['context'],user=1)
    elif mutation=='competitor':bundles[0]['samples'][5]['writes']=[dict(kind='xs_vm',port=0,address=398720,data=1)]
    before=copy.deepcopy((trace,banks,bundles,capacities))
    with pytest.raises(ValueError):B.publication_bundle_check(trace,banks,bundles,2,capacities)
    assert (trace,banks,bundles,capacities)==before
