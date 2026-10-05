import importlib.util,itertools
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('review',Path(__file__).resolve().parents[1]/'tools/ds_r67_physical_phase_review.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_exhaustive_two_phase_baseline_transitions():
    for kinds in itertools.product(('private','shared','absent'),repeat=2):
        for bits in itertools.product(range(4),repeat=4):
            phases=[{'reads':{i for i in range(2) if bits[t*2+i]&1},'writes':{i for i in range(2) if bits[t*2+i]&2}} for t in range(2)]
            got=m.page_evolution(dict(enumerate(kinds)),phases)
            state=list(kinds);expected=0
            for phase,result in zip(phases,got):
                for i in phase['reads']|phase['writes']:
                    if state[i]=='absent' or (state[i]=='shared' and i in phase['writes']):
                        expected+=4096;state[i]='private'
                assert result['cumulative_backing_bytes']==expected
            assert expected<=2*4096

def test_exit_does_not_reset_COW_state():
    got=m.page_evolution({0:'shared',1:'shared'},[{'reads':[],'writes':[0]},{'reads':[],'writes':[1]},{'reads':[0],'writes':[0]}])
    assert [r['cumulative_backing_bytes'] for r in got]==[4096,8192,8192]
    assert max(r['new_backing_bytes'] for r in got)==4096 # maxphase would underprice chain

def test_all_readonly_private_pages_have_no_new_backing():
    assert m.page_evolution({0:'shared',1:'private'},[{'reads':[0,1],'writes':[1]}])[0]['new_backing_bytes']==0

@pytest.mark.parametrize('kind',['unknown',None,7])
def test_unknown_baseline_rejected(kind):
    with pytest.raises(ValueError):m.page_evolution({0:kind},[{'reads':[0],'writes':[]}])

def test_missing_allocation_generation_rejected():
    with pytest.raises(ValueError):m.page_evolution({0:'private'},[{'reads':[1],'writes':[]}])

def test_thp_granule_not_assumed_basepage():
    assert m.page_evolution({0:'shared'},[{'reads':[],'writes':[0]}],granule=2**21)[0]['new_backing_bytes']==2**21

@pytest.mark.parametrize('bad',[None,True,-1,1.5])
def test_unknown_growth_cannot_admit(bad):
    with pytest.raises(ValueError):m.bounded_delta(cumulative_complete_touch_bytes=38,ram_exposure_bytes=74,kernel_growth=bad,peer_growth=0)

def test_touch_and_exposure_are_alternatives():
    assert m.bounded_delta(cumulative_complete_touch_bytes=38,ram_exposure_bytes=74,kernel_growth=2,peer_growth=3)==43
    assert m.bounded_delta(cumulative_complete_touch_bytes=200,ram_exposure_bytes=74,kernel_growth=2,peer_growth=3)==79

@pytest.mark.parametrize('args',[dict(roof=100,resident=101,shared_clean=0,shared_dirty=0),dict(roof=100,resident=50,shared_clean=30,shared_dirty=30)])
def test_RAM_only_mapping_validity(args):
    with pytest.raises(ValueError):m.exposure(**args)

def test_r67_source_and_scope_enrollment():
    v=m.model()
    assert v['source_child_processes_simultaneously_live']==1 and v['journals_created']==3 and v['checkpoints_retained']==2
    assert v['full_native_PCs']==2213 and v['full_homes']==290730
    assert not v['resource_admission'] and v['old_R64_guards_unchanged']
    assert v['baseline_physical']['RAM_only_new_backing_exposure_upper_bytes']==74466877440
    assert not v['baseline_physical']['guest_exit_proves_host_backing_release']
