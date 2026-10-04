"""Source-bound old-state scheduling; no FP arithmetic, leaf simulation or new tree."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rd64',ROOT/'tools/dsrom_rd64_vm_calendar.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def outputs(machine, inputs, end=30):
    return [(e,v) for e in range(end) if (v:=machine.step(*inputs.get(e,(None,None)))) is not None]

@pytest.mark.parametrize('a,b,edge',[
    ((0,0,0,0,2),(0,0,1,0,2),7),
    ((0,0,0,0,1),None,3),
    ((0,0,0,0,2),None,5),
])
def test_node_preedge_and_rst_latency(a,b,edge):
    assert [e for e,_ in outputs(m.Node(),{0:(a,b)})]==[edge]


def test_continuous_sibling_pipeline_and_bypass_collision():
    n=m.Node();inputs={e:((0,e,0,0,2),(0,e,1,0,2)) for e in range(8)}
    # A complete row arriving during consecutive add results must be held.
    inputs[8]=((0,100,0,0,1),None)
    out=outputs(n,inputs)
    assert [e for e,_ in out[:8]]==list(range(7,15))
    assert [t[1] for _,t in out]==list(range(8))+[100]
    assert out[-1][0]>14


def test_full_fifo_pop_allows_push_but_ap_collision_rejects_overflow():
    n=m.Node();n.q[0].extend([(0,r,0,0,1) for r in range(64)])
    n.step((0,64,0,0,1));assert len(n.q[0])==64
    n.ap[3]=True
    with pytest.raises(ValueError,match='RD64 overflow'):n.step((0,65,0,0,1))

@pytest.mark.parametrize('inputs,edge',[
    ({0:(0,0,0,0,1)},2),
    ({0:(0,0,0,0,2),1:(0,0,1,0,2)},9),
])
def test_root_registered_launch_and_spine_sample(inputs,edge):
    r=m.ReturnRoot()
    out=[(e,v) for e in range(20) if (v:=r.step(inputs.get(e))) is not None]
    assert [e for e,_ in out]==[edge]
    # Spine w_we is post this edge, direct VM consumes it one edge later.
    assert edge+1 in (3,10)


def test_root_add_result_priority_defers_fifo_head():
    r=m.ReturnRoot();r.q.append((0,9,0,0,1));r.pipe[4]=(0,2,0,0,1)
    assert r.step() is None
    assert len(r.q)==1
    assert r.step()==(0,2,0,0,1)
    assert r.step()==(0,9,0,0,1)


def test_root_buffer_and_queue_actual_limits():
    r=m.ReturnRoot();r.buf={i:(0,i,0,0,2) for i in range(128)};r.q.append((0,200,0,0,2))
    with pytest.raises(ValueError,match='D128 overflow'):r.step()
    r=m.ReturnRoot();r.q.extend([(0,i,0,0,1) for i in range(128)]);r.pipe[4]=(0,1000,0,0,1)
    with pytest.raises(ValueError,match='QD128 overflow'):r.step((0,1001,0,0,1))


def test_sv_shift_widths_are_not_python_unlimited_shifts():
    assert not m.complete((0,0,0,6,31))  # 6'd1 << 6 truncates to zero
    assert not m.sibling((0,0,0,5,31),(0,0,1,5,31))

@pytest.mark.parametrize('addresses,banks,batches',[
    (list(range(128)),[2,2,2,2],2),
    (list(range(1,129)),[3,2,2,2],3),
    ([64*i for i in range(128)],[128,0,0,0],128),
    ([15]*128,[1,0,0,0],1),
])
def test_actual_native_word_bank_and_batch_service(addresses,banks,batches):
    d=m.batch_waves(addresses)
    assert d['distinct_words_per_bank']==banks and d['native_batches']==batches
    assert d['provider_elapsed_accept_to_earliest_retire_edges']==1+6*batches
    assert d['provider_inclusive_service_edge_bound']==2+6*batches

@pytest.mark.parametrize('address',[-1,1<<19,True,1.0,'1'])
def test_vm_address_rejects_alias_and_untyped_input(address):
    with pytest.raises(ValueError):m.batch_waves([address])


def two_edge_source_burst():
    # Legal complete tags, independent roots; generated from the actual root recurrence.
    rs=[m.ReturnRoot() for _ in range(128)];events=[]
    for e in range(5):
        for root,r in enumerate(rs):
            t=r.step((0,128*e+root,0,0,1) if e<2 else None)
            if t is not None:events.append(dict(edge=e,root=root,row=t[1],pos=t[0]))
    return events


def test_combined_legal_two_edge_burst_requires_more_than_peak_seats():
    events=two_edge_source_burst();d=m.bursts(events)
    assert d['peak_simultaneous_rows']==128 and d['events']==256
    assert {e['edge'] for e in events}=={2,3}
    # Even a one-batch native write cannot return checked credit in the next edge.
    assert m.batch_waves(list(range(128)))['provider_elapsed_accept_to_earliest_retire_edges']==13
    with pytest.raises(ValueError,match='overflow'):m.capture_calendar(events,[],128)
    d=m.capture_calendar(events,[],256)
    assert d['peak_seats_before_edge_release']==256
    assert d['remaining_row_debt']==256 and not d['all_supplied_rows_retired']
    assert not d['actual_source_context_clock_enrollment']


def test_positive_checked_visibility_credit_and_debt_completion():
    events=[dict(edge=2,root=0,row=4,pos=0)]
    release=[dict(root=0,row=4,pos=0,checked_visible_edge=10,captured_credit_edge=12)]
    d=m.capture_calendar(events,release,1)
    assert d['all_supplied_rows_retired'] and d['remaining_row_debt']==0
    assert d['calendar'][-1]['edge']==12

@pytest.mark.parametrize('change',[
    {'checked_visible_edge':2}, {'captured_credit_edge':10},
    {'root':1}, {'row':5}, {'pos':1}, {'captured_credit_edge':True},
])
def test_early_wrong_identity_or_nonpositive_credit_rejected(change):
    r=dict(root=0,row=4,pos=0,checked_visible_edge=10,captured_credit_edge=12);r.update(change)
    with pytest.raises(ValueError):m.capture_calendar([dict(edge=2,root=0,row=4,pos=0)],[r],1)


def test_credit_released_this_edge_cannot_be_reused_this_edge():
    events=[dict(edge=2,root=0,row=4,pos=0),dict(edge=12,root=0,row=5,pos=0)]
    r=dict(root=0,row=4,pos=0,checked_visible_edge=10,captured_credit_edge=12)
    with pytest.raises(ValueError,match='same-edge'):m.capture_calendar(events,[r],1)
    events[1]['edge']=13
    d=m.capture_calendar(events,[r],1);assert d['remaining_row_debt']==1


def test_raw_receipt_cannot_be_substituted_for_checked_visibility():
    r=dict(root=0,row=4,pos=0,raw_visible_edge=10,captured_credit_edge=12)
    with pytest.raises(ValueError,match='checked visibility'):m.capture_calendar([dict(edge=2,root=0,row=4,pos=0)],[r],1)


def test_duplicate_root_pulse_row_or_credit_rejected():
    e=dict(edge=2,root=0,row=4,pos=0)
    with pytest.raises(ValueError):m.bursts([e,e])
    with pytest.raises(ValueError):m.bursts([e,dict(e,edge=3)])
    r=dict(root=0,row=4,pos=0,checked_visible_edge=10,captured_credit_edge=12)
    with pytest.raises(ValueError):m.capture_calendar([e],[r,r],1)


def test_model_replays_exact_source_pins_and_keeps_current_admission_unknown():
    d=m.generate()
    assert json.loads((m.E/'model.json').read_text())==d
    assert d['path_examples']['six_levels_all_siblings_no_queue_input_to_legacy_VM_edges']==45
    assert d['accepted_current_journal'] is None
    assert d['combined_top_finite_capture_result'] is None
    assert not d['clock_or_rate_admission']


def test_legal_burst_record_replays_bytes_and_preserves_negative():
    import hashlib
    record=m.legal_burst_calibration()
    expected=json.dumps(record,indent=2,sort_keys=True)+'\n'
    assert (m.E/'legal_burst_calibration.json').read_text()==expected
    assert record['peak_only_capacity_negative']['verdict']=='REJECT'
    assert record['phase_capacity_control']['remaining_row_debt']==256
    assert not record['phase_capacity_control']['all_supplied_rows_retired']


def test_live_source_and_frozen_snapshot_identity():
    import hashlib
    pins=json.loads((m.E/'source_pins.json').read_text())
    for original,p in pins['sources'].items():
        assert hashlib.sha256((ROOT/original).read_bytes()).hexdigest()==p['sha256']
        assert (ROOT/original).read_bytes()==(ROOT/p['snapshot']).read_bytes()
