import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_D1_core_observation_model as m

def packet(**kw):
    p=dict(state=6,unit=1,**{'class':1},me_ready=True,kv_ok=True,kvd_v=False,win_idle=True,waited=True,q_gate=True,m0_gate=True,fault=False);p.update(kw);return p

def test_all_four_bit_combinations_and_registered_phase():
    for mask in range(16):
        bits=[bool(mask>>i&1) for i in range(4)];p=packet(**dict(zip(['me_ready','kv_ok','kvd_v','win_idle'],bits)))
        expected=mask==11
        r=m.validate_admission_edge(p,dict(me_go=expected));assert r['qualified_admission']==expected and not r['provider_completion']
        with pytest.raises(ValueError):m.validate_admission_edge(p,dict(me_go=not expected))

@pytest.mark.parametrize('key',['waited','q_gate','m0_gate','me_ready','kv_ok','win_idle'])
def test_nonadmission_pc_busy_ready_dont_hide_blocker(key):
    p=packet(**{key:False});assert not m.validate_admission_edge(p,dict(me_go=False))['qualified_admission']
    with pytest.raises(ValueError):m.validate_admission_edge(p,dict(me_go=True))

def test_fault_before_issue_and_stale_descriptor():
    with pytest.raises(ValueError):m.validate_admission_edge(packet(fault=True),dict(me_go=True))
    assert not m.validate_admission_edge(packet(kvd_v=True),dict(me_go=False))['qualified_admission']

@pytest.mark.parametrize('bad',[1,0,1.0,None,'1'])
def test_strict_observation_bits(bad):
    with pytest.raises(ValueError):m.validate_admission_edge(packet(kv_ok=bad),dict(me_go=False))

@pytest.mark.parametrize('key',sorted(m.ASSUMPTIONS))
def test_unavailable_real_service_assumption_refuses_bound(key):
    a={k:True for k in m.ASSUMPTIONS};a[key]=False
    with pytest.raises(m.BoundMissing):m.service_reference(a)

def test_calendar_offsets_not_absolute_original_deadline():
    r=m.service_reference({k:True for k in m.ASSUMPTIONS})
    assert (r['descriptor_to_stage'],r['descriptor_to_stream_done'],r['request_reply_min'],r['request_reply_max'])==(124369,124500,34,241)
    assert r['actual_core_issue_deadline'] is None and not r['universal_deadline'] and not r['actual_original_run']

@pytest.mark.parametrize('bad',[True,1.5,-1,1<<21,'128'])
def test_program_envelope(bad):
    with pytest.raises(ValueError):m.strict_encode(dict(me_nout=bad))

def test_source_bound_program_and_no_new_job():
    x=m.build();p=x['program'];first=m.isa.decode(int(p['words_hex'][0],16),full_shape=True)
    assert first['unit']==1 and first['wait']==2 and first['me_nout']==128 and first['me_k']==512
    assert x['real_binding']['X_ATT']==1 and x['real_binding']['SUN']==256
    assert x['service_status']=='BOUND_MISSING' and x['resources']['inherit_12GiB_GO'] is False
    assert x['compiler_invocations']==x['simulations']==0 and not p['original_program']
