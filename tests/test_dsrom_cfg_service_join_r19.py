import copy,sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_cfg_service_join_r19 as B

@pytest.fixture(scope='module')
def m():return B.model()

def test_phase_and_hardware_counts_not_active_only(m):
    assert m['phase_identity_joins']==46509
    assert len(m['stage_inventory'])==58
    assert m['system_cfg_instances']==6651904
    assert m['system_cfg_pins']==585367552
    assert all(x['compiled_pairs']==4096 for x in m['stage_inventory'])
    assert sum(x['cfg_loader_words_over_used_phases_per_rank'] for x in m['stage_inventory'])==46509*4096*25

def test_service_is_inherited_once_and_failure_retained(m):
    assert m['containment_credit_mm2']==m['service_doublecharge_mm2']==0
    assert m['retained_whole_budget']['conservative_no_containment_credit_reticle_margin']==pytest.approx(-66.28861852384591)
    assert not m['runtime_or_rate_or_physical_admission']
    assert all(not s['generic27cycle_is_physical_latency'] for s in m['stage_inventory'])

def test_all_weight_descriptors_require_executable_patch(m):
    assert m['descriptor_key_audit']['QE']==1010
    assert m['descriptor_key_audit']['ME']==140
    assert len(m['weight_descriptor_audit'])==1150
    assert not any(x['exact_phase_provider_binding'] for x in m['weight_descriptor_audit'])
    assert m['descriptor_calendar']['rank_calendar_nodes']==19548
    assert m['descriptor_calendar']['received_service_calendar_bindings']==0

def test_wrong_stage_phase_key_rejected():
    data=B.inputs();data['key_tables.jsonl.gz'][0]['words'][0]^=1
    with patch.object(B,'inputs',return_value=data),pytest.raises(AssertionError):B.model()

def test_duplicate_phase_rejected():
    data=B.inputs();data['phase_directory.jsonl.gz'][1]=copy.deepcopy(data['phase_directory.jsonl.gz'][0])
    with patch.object(B,'inputs',return_value=data),pytest.raises(AssertionError):B.model()
