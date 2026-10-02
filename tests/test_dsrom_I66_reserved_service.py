import copy
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_reserved_service as S
import dsrom_I66_observer_copy as O


@pytest.fixture
def model():
    return S.demand_example()


def test_finite_reserved_service_and_actual_credit_demand(model):
    e=model['example']
    assert e['successful_completion_edge']==435
    assert e['successful_service_edges']==413
    assert e['reservation']['requirements']['shared']==dict(capture_and_ACK_held_credits=192,capture_and_ACK_held_bits=163840)
    assert not e['runtime_observed'] and not e['current_provider_proved']
    assert not model['all384_service_transferred'] and not model['historical_PHW6_inherited']


@pytest.mark.parametrize('mutation', ['bandwidth','credits','storage','latency','stale','missing_root','duplicate_root','wrong_destination','PHW6','early_idle','activation_missing','input_late','owner_fallback'])
def test_adversarial_reserved_bound_rejected_before_mutation(model,mutation):
    p=copy.deepcopy(model['input']);baseline=copy.deepcopy(p)
    if mutation=='bandwidth':p['domains']['shared']['bits_per_edge']=256
    elif mutation=='credits':p['domains']['shared']['credits']=191
    elif mutation=='storage':p['domains']['shared']['storage_bits']=163839
    elif mutation=='latency':p['domains']['shared']['latency_edges']=2
    elif mutation=='stale':p['events'][-1]['identity']=dict(p['events'][-1]['identity'],generation=999)
    elif mutation=='missing_root':p['events'].pop()
    elif mutation=='duplicate_root':p['events'].append(copy.deepcopy(p['events'][-1]))
    elif mutation=='wrong_destination':p['events'][-1]['address']+=1
    elif mutation=='PHW6':p['calendar']['PHW']=6
    elif mutation=='early_idle':p['calendar']['source_idle_edge']-=1
    elif mutation=='activation_missing':p['events']=[e for e in p['events'] if e['kind']!='activation']
    elif mutation=='input_late':p['calendar']['first_VM_read_edge']=1
    elif mutation=='owner_fallback':p['calendar']['identity']['stage']=1
    before=copy.deepcopy(p)
    with pytest.raises(ValueError):S.compose(p['calendar'],p['events'],p['domains'])
    assert p==before and baseline==model['input']


@pytest.mark.parametrize('value',[True,1.5,-1,'1'])
def test_invalid_resource_envelope(value,model):
    p=copy.deepcopy(model['input']);p['domains']['shared']['bits_per_edge']=value
    with pytest.raises(ValueError):S.reserve(p['events'],p['domains'])


def test_shared_domain_charged_once_and_ack_credit_not_reused_same_edge():
    events=[dict(id='a',release=0,deadline=1,bits=8,domain='x'),dict(id='b',release=2,deadline=3,bits=8,domain='x')]
    d=dict(x=dict(bits_per_edge=8,latency_edges=1,ACK_edges=1,credits=1,storage_bits=8))
    with pytest.raises(ValueError,match='storage'):S.reserve(events,d)
    d['x'].update(credits=2,storage_bits=16)
    r=S.reserve(events,d);assert r['requirements']['x']['capture_and_ACK_held_credits']==2
    events[1]['release']=0;events[1]['deadline']=1
    with pytest.raises(ValueError,match='deadline'):S.reserve(events,d)


def test_local_capture_does_not_invent_ACK_or_delay(model):
    r=model['example']['reservation']
    cfg=[e for e in r['events'] if e['domain']=='local_cfg0']
    assert len(cfg)==25 and all(e['ACK'] is None and e['retirement']==e['visible'] for e in cfg)
    assert r['requirements']['local_cfg0']['capture_and_ACK_held_credits']==1
    assert r['requirements']['local_root']['capture_and_ACK_held_credits']==64


def test_source_receipt_required_not_arbitrary_false_binding(model):
    p=copy.deepcopy(model['input']);p['calendar']['source_calendar_sha256']='unbound'
    with pytest.raises(ValueError,match='SHA256'):S.compose(p['calendar'],p['events'],p['domains'])


def test_explicit_phase_plan_CLI(model,tmp_path):
    import subprocess
    p=tmp_path/'plan.json';p.write_text(json.dumps(model['input']))
    out=tmp_path/'result.json'
    subprocess.run([sys.executable,str(S.ROOT/'tools/dsrom_I66_reserved_service.py'),
                    '--plan',str(p),'--out',str(out)],check=True)
    assert json.loads(out.read_text())==model['example']


def test_observer_exact_inverse_and_default_off():
    text=O.generate()
    assert O.inverse(text)==O.ORIGINAL.read_text()
    assert O.COPY.read_text()==text
    assert O.PARAM in text and 'SIM_OBSERVE_I66 = 0' in text
    assert 'generate if (SIM_OBSERVE_I66 != 0)' in text


def test_observer_assignments_never_write_engine_and_no_delay_or_forcing():
    text=O.HOOKS
    import re
    assert not re.search(r'dut\.[\w.\[\]:+ *]+\s*(?:<=|=(?!=))',text)
    assert '#(' not in text and '#1' not in text and 'force ' not in text
    assert 'always @(negedge clk)' in text
    for name in ('ROM_accept','EID_read','EID_sample','key_lookup','phase_accept','root_sample','VM_write_accept','VM_postNBA','CDMA_pre','CDMA_VM_postNBA'):
        assert 'I66_OBS '+name in text


def test_hook_source_scopes_are_present_in_frozen_source():
    i=S.ROOT/'results/uarch/dsrom_I66_provider_clock_contract_20261002/inputs'
    core=(i/'core.sv.txt').read_text();tile=(i/'tile.sv.txt').read_text()
    for n in ['d_skip','qe_mode','rom_m_go','d_wait','rom_ready_w','rom_idle_w','g_rom','u_radapt','u_spine']:
        assert n in core
    for n in ['rom_vre','rom_vaddr','rom_vq','rom_we','rom_waddr','rom_wdata','xb_we4','xb_waddr4','xb_wdata4']:
        assert n in tile
    assert 'fault <= 1\'b1' in (S.ROOT/'rtl/v41die/ot_v41_rom_adapt.sv').read_text()
