import pytest
from tools.dsrom_s81_rd64_capture import pair_spans,required_depths,pre_go_admission,model,R


def test_s81_active_pair_conservation():
    s=pair_spans();assert s[0][0]==0 and s[-1][1]==2417
    assert all(s[i][1]==s[i+1][0] for i in range(127))
    assert sum(b-a==19 for a,b in s)==113 and sum(b-a==18 for a,b in s)==15
    m=model();assert m['geometry']['nodes']==4706 and m['geometry']['padded_pair_seats']==0
    assert m['original_return']['state_lower_bits']==41610820
    assert m['original_return']['NO_READY'] and m['no_RD16']


def test_native_full_burst_captures_before_positive_VM_visibility():
    c=required_depths([[1]*128]*32+[[0]*128],[[1]*128]*33)
    assert c['required_depths']==[1]*128
    assert c['journal'][0]['VM_accepted']==[0]*128
    assert c['journal'][1]['VM_accepted']==[1]*128
    assert c['VM_accepted']==[32]*128 and c['pending']==[0]*128


def test_target_stall_never_stalls_or_drops_NOREADY_source():
    c=required_depths([[1]]*5+[[0]]*5,[[0]]*5+[[1]]*5)
    assert c['required_depths']==[5] and c['VM_accepted']==[5] and c['pending']==[0]
    assert sum(j['captured'][0] for j in c['journal'])==5


def test_simultaneous_retire_capture_uses_one_seat_not_zero():
    c=required_depths([[1],[1],[1]],[[1],[1],[1]])
    assert c['required_depths']==[1] and c['pending']==[1]


def test_no_service_guarantee_requires_exact_phase_not_arbitrary_fifo():
    rows=[[0,1,2]]+[[]]*127
    assert not pre_go_admission(rows,8,[16]+[0]*127)['admitted']
    x=pre_go_admission(rows,8,[24]+[0]*127)
    assert x['admitted'] and x['reserved_phase_returns']==24


def test_manifest_does_not_uniformly_divide_rows_by128():
    rows=[list(range(400))]+[[]]*127
    x=pre_go_admission(rows,1,[400]+[0]*127)
    assert x['required'][0]==400 and all(n==0 for n in x['required'][1:])
    assert x['admitted']


def test_pre_go_drain_calendar_bound_exact():
    rows=[[0,1]]+[[]]*127
    c=required_depths([[1]+[0]*127,[1]+[0]*127,[0]*128],[[1]*128]*3)
    assert pre_go_admission(rows,1,[1]+[0]*127,guaranteed_service=c)['admitted']


@pytest.mark.parametrize('rows',[[[0],[0]]+[[]]*126,[[65536]]+[[]]*127,[[True]]+[[]]*127])
def test_duplicate_or_width_invalid_rows_refuse(rows):
    with pytest.raises(ValueError):pre_go_admission(rows,1,[100]*128)


@pytest.mark.parametrize('a,s', [([[2]],[[1]]),([[1,0]],[[1]]),([[True]],[[1]]),([[1]],[[0.5]])])
def test_no_invented_ready_or_multireturn_port(a,s):
    with pytest.raises(ValueError):required_depths(a,s)


def test_current_record_does_not_admit_unbound_hardware():
    m=model();assert m['hardware_change_required'] is None
    assert m['combined_token_qualified'] is False and m['physical_build_admitted'] is False
    assert m['source_edges']['new_capture_FF_if_native_allports_accept']==0
    assert 'actual S81 Arendt tensor->pair->root row map' in m['missing']


def native_trace():
    return dict(root_rows=[[0],[1]]+[[]]*126,positions=1,obase=32,ops=8,fmt=1,
                rsplit=0,phase_fp32_low=False,phase_fp32_high=False,VM_AW=16,
                returns=[dict(edge=12,root=0,row=0,pos=0,fp32=0x3f800000,bf16=0x3f80,error=0),
                         dict(edge=12,root=1,row=1,pos=0,fp32=0x80000000,bf16=0x8000,error=0)],
                vm_writes=[dict(edge=13,root=0,address=32,data=0x3f800000,writer='ROM'),
                           dict(edge=13,root=1,address=33,data=0x80000000,writer='ROM')])


def test_observed_trace_preserves_rawbits_signedzero_and_positiveedge():
    from tools.dsrom_s81_rd64_capture import verify_native_vm_trace
    r=verify_native_vm_trace(**native_trace())
    assert r['VM_commits']==2 and r['last_actual_VM_commit_edge']==13


@pytest.mark.parametrize('field,value',[('edge',12),('address',34),('data',0)])
def test_early_foreign_or_payload_mismatched_actualwrite_refuses(field,value):
    from tools.dsrom_s81_rd64_capture import verify_native_vm_trace
    a=native_trace();a['vm_writes'][0][field]=value
    with pytest.raises(ValueError,match='actual VM commits'):verify_native_vm_trace(**a)


def test_missing_duplicate_and_faulted_return_debt_preserved():
    from tools.dsrom_s81_rd64_capture import verify_native_vm_trace
    for kind in ('missing','duplicate','fault'):
        a=native_trace()
        if kind=='missing':a['returns'].pop()
        elif kind=='duplicate':a['returns'].append(a['returns'][0])
        else:a['returns'][0]['error']=1
        with pytest.raises(ValueError):verify_native_vm_trace(**a)


def test_other_writer_cannot_invalidate_exclusiveVMlease():
    from tools.dsrom_s81_rd64_capture import verify_native_vm_trace
    a=native_trace();a['vm_writes'].append(dict(edge=14,address=32,data=0,writer='SU'))
    with pytest.raises(ValueError,match='other writer'):verify_native_vm_trace(**a)


def test_actual_VM_width_cannot_modulo_alias():
    from tools.dsrom_s81_rd64_capture import verify_native_vm_trace
    a=native_trace();a['obase']=65536
    with pytest.raises(ValueError,match='truncation'):verify_native_vm_trace(**a)


def test_committed_model_replays_byte_exact():
    import json
    from pathlib import Path
    p=Path(__file__).resolve().parents[1]/'results/uarch/dsrom_s81_rd64_capture_20261004/model.json'
    assert p.read_text()==json.dumps(model(),sort_keys=True,indent=2)+'\n'
