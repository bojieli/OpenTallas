"""Source resolution and causal event controls, never production execution."""
import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dewey_event_adapter_r9', ROOT / 'tools/h3_complete_native_calendar_event_adapter_r9.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.fixture
def control():
    node = dict(op='FMUL', dst='r', src=['a', 'b'], shape=[128], attrs={})
    ref = dict(model='Qwen', PC=0, leaf='mul', code_index=0, node_sha256=m.digest(node), opcode='FMUL',
               sources=['a','b'], destination='r', repetition=0, repetitions=2)
    q = dict(operations=[dict(calendar_export={'physical_primitives':{'kernel_invocations':{'mul':2}}})], microcode={'mul':[node]})
    caps = dict(SMs=32, fragment_credit=1, child_rows_per_SM=128, RF_mirrors=2, sector_bytes=32, frame_bytes=512)
    costs = {phase:dict(min_edges=2, max_edges=None, source='explicit prospective control edge cost', domain='streaming') for phase in m.PHASES}
    for phase,edges in [('accepted',8),('capture',8),('W2_retirement_commit',4),('reverse_CDC',3)]:costs[phase]['min_edges']=edges
    events = []
    def event(phase, **extra):
        key = 'event/' + str(len(events))
        events.append(dict(eventID=key, phase=phase, identity=[0,0,46,9,4], reset_epoch=7, domain='streaming',
                           port=m.PORTS[phase], accepted=True, native_ref=ref,
                           depends_on=[] if not events else [events[-1]['eventID']], **extra))
    for fragment in range(8):
        for child in [2*fragment,2*fragment+1]:
            event('accepted', child=child, fragment=fragment, child_owner46=child+64, backend16=0x4000+child)
            event('capture', child=child, fragment=fragment, payload_bytes=32, child_owner46=child+64, backend16=0x4000+child)
            event('W2_retirement_commit', child=child, coded_commit_complete=True, child_owner46=child+64, backend16=0x4000+child)
        event('continuation', children=[2*fragment,2*fragment+1], fragment=fragment)
    event('common_ACK', RF_mirrors=2); event('visible'); event('consumer')
    for child in range(16):
        event('reverse', child=child, child_owner46=child+64, backend16=0x4000+child)
        event('reverse_CDC', child=child, matched=True, child_owner46=child+64, backend16=0x4000+child)
    event('retire', allcopies_drained=True)
    return ref, node, events, caps, costs, q


def joined(control):
    ref, node, events, caps, costs, q = control
    literal = m.resolve_source_node(ref, q, {}, {})
    return m.join_endpoint_events(ref, literal, events, caps, costs)


def test_positive_exact_lifecycle_still_refuses_production(control):
    result = joined(control)
    assert result['complete_lifecycle'] and result['retained_child_debt'] == 0
    assert result['production_status'] == 'REFUSED'
    assert not result['finite_service_guarantee']
    assert len(result['unknown_service_eventIDs']) == len(control[2])
    assert result['phase_counts']['capture'] == 16
    for i,row in enumerate(result['events']):
        assert row['end_min_edges'] > row['start_min_edges']
        if i: assert row['start_min_edges'] >= result['events'][i-1]['end_min_edges']


@pytest.mark.parametrize('mutation', ['wrong_source','repetition','backend_gen','child_owner','domain','epoch','early_capture','continuation','RF_mirror','causal','missing_ack','reverse','early_retire','capacity','zero','bad_upper','duplicate','unowned','invented_port','fragment_capacity','stale_gate_lease','old_coded_commit'])
def test_wrong_owner_stale_and_resource_mutants(control, mutation):
    ref,node,events,caps,costs,q = control
    ack=next(e for e in events if e['phase']=='common_ACK')
    reverse=next(e for e in events if e['phase']=='reverse')
    continuation=next(e for e in events if e['phase']=='continuation')
    if mutation == 'wrong_source': q['microcode']['mul'][0]['src'] = ['invented','b']
    elif mutation == 'repetition': ref['repetition'] = 2
    elif mutation == 'backend_gen': events[1]['backend16'] &= 0xfff
    elif mutation == 'child_owner': events[1]['child_owner46'] = 999
    elif mutation == 'domain': events[1]['domain'] = 'NOT_A_BOUND_CLOCK_DOMAIN'
    elif mutation == 'epoch': events[1]['reset_epoch'] = 6
    elif mutation == 'early_capture': events[1]['child'] = 2
    elif mutation == 'continuation': continuation['children'] = [0,2]
    elif mutation == 'RF_mirror': ack['RF_mirrors'] = 1
    elif mutation == 'causal': events[1]['depends_on'] = []
    elif mutation == 'missing_ack': ack['phase'] = 'visible'
    elif mutation == 'reverse': reverse['backend16'] = 0
    elif mutation == 'early_retire': reverse['phase'] = 'retire'; reverse['allcopies_drained'] = True
    elif mutation == 'capacity': caps['child_rows_per_SM'] = 16
    elif mutation == 'zero': costs['capture']['min_edges'] = 0
    elif mutation == 'bad_upper': costs['capture']['max_edges'] = 1
    elif mutation == 'duplicate': events[1]['eventID'] = events[0]['eventID']
    elif mutation == 'unowned': events[0]['phase'] = 'capture'
    elif mutation == 'invented_port': events[0]['port'] = 'free_parallel_W2'
    elif mutation == 'old_coded_commit':costs['W2_retirement_commit']['min_edges']=1
    elif mutation == 'fragment_capacity':
        continuation['phase']='accepted'; continuation.update(child=2,fragment=0,child_owner46=100,backend16=0x4100)
    elif mutation == 'stale_gate_lease':
        # Positive source packet must reject stale real provider lease as well.
        actual=m.read(str((m.BASE/'inputs/Ampere_PC40.json').relative_to(ROOT)))['selected_C0_command']
        actual['source_gate_home']['lease']='stale'
        with pytest.raises(ValueError,match='lease/provider'):m.direct_RF_demand(m.read(m.QPATH),actual)
        return
    with pytest.raises(ValueError): joined(control)


def test_missing_receipts_remain_unknown(control):
    control[2][:] = control[2][:7]
    result = joined(control)
    assert not result['complete_lifecycle'] and result['retained_child_debt'] == 2
    assert 'consumer' in result['missing_phases']


def test_literal_ssa_count_and_I64_words():
    code = [dict(op='LOAD',dst='x',src=[],shape=[129],attrs={'dtype':'I64'}),
            dict(op='I2F',dst='y',src=['x'],shape=[129],attrs={})]
    steps = m.ds_steps(code)
    assert steps[0]['RF_result_words32'] == 2 and steps[0]['batches128'] == 2
    assert steps[1]['source_bytes'] == [1032] and steps[1]['result_bytes'] == 516
    code[1]['src'] = ['unknown']
    with pytest.raises(ValueError, match='before definition'): m.ds_steps(code)


def test_source_protected_cost_supersedes_unprotected_constant():
    costs = m.source_costs()
    w2 = costs['W2']
    assert w2['selected_bits_per_PC'] == 13608
    assert [w2[k] for k in ['request_min_edges','read_min_edges','write_min_edges','early_read_min_edges','early_write_min_edges','lookup_II_edges']] == [8,8,9,11,12,8]
    assert costs['W6']['raw_bits_per_SM'] == 71 and costs['W6']['protected_bits_per_SM'] == 144
    assert costs['upper_bound_edges'] is None and not costs['fixture_ns_as_upper_bound']


@pytest.fixture(scope='module')
def actual_PC40():
    return m.read(m.QPATH), m.read(str((m.BASE/'inputs/Ampere_PC40.json').relative_to(ROOT)))['selected_C0_command']


def test_actual_PC40_source_live_home_scan(actual_PC40):
    q,plan=actual_PC40; result=m.direct_RF_demand(q,plan)
    assert result['caller_kernel_repetitions'] == 48
    assert result['workspace_admission'] == 'REFUSED_MISSING_ENTERING_LIVE_LEASES'
    assert any(h['slot'] == 38 for h in result['existing_live_RF_homes'])
    assert result['phase_counts']['native_primitive'] == 6
    assert result['phase_counts']['both_RF_mirror_write'] == 7
    assert result['phase_counts']['common_RF_ACK'] == 7
    assert result['W2_HBM_commands'] == 0 and result['parent55'] is None
    assert result['actual_accepted_capture_ACK_consumer_reverse_events'] == 0
    assert result['finite_service_upper_edges'] is None
    # A supplied disjoint control snapshot is an allocation proof, no runtime credit.
    result=m.direct_RF_demand(q,plan,entering_workspace=[dict(slot=16,lease='x',rank=0,SM=0)])
    assert result['workspace_admission'] == 'PROSPECTIVE_DISJOINT_SOURCE_ALLOCATION'


@pytest.mark.parametrize('mutation',['workspace_live','provider_live','wrong_literal','wrong_leaf','HBM_owner','generation'])
def test_actual_PC40_admission_mutants(actual_PC40,mutation):
    q,original=actual_PC40; plan=copy.deepcopy(original)
    if mutation=='workspace_live':
        with pytest.raises(ValueError,match='entering active lease'):
            m.direct_RF_demand(q,plan,entering_workspace=[dict(slot=17,lease='existing',rank=0,SM=0)])
        return
    if mutation=='provider_live':
        q=copy.deepcopy(q)
        q['operands'].append(dict(birth_pc=0,retire_pc=50,version='actual.live',lease='live',homes=[dict(rank=0,SM=0,home={'class':'RF','slot_first':18,'vectors':1})]))
    elif mutation=='wrong_literal':plan['ordered_producer_actions'][5]['bits']=0
    elif mutation=='wrong_leaf':plan['source_step']['op']='FMIN'
    elif mutation=='HBM_owner':plan['parent55']=123
    elif mutation=='generation':plan['transient_enrollment'][0]['generation']=999
    with pytest.raises(ValueError):m.direct_RF_demand(q,plan)
