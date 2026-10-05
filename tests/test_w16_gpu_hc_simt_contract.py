import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_gpu_hc_simt_contract as C


def test_bank_conflicts_and_full_waves():
    p=C.assumptions()
    assert C.scatter_conflict()==8
    assert C.scatter_conflict(True)==4
    c=C.transpose(1024,p);a=C.transpose(1024,p,True)
    assert c['warp_scatter_stores']==256 and a['warp_scatter_stores']==128
    assert c['raw_read_bytes']==32768 and a['raw_read_bytes']==16384
    assert c['scatter_write_bytes']==32768 and a['scatter_write_bytes']==16384
    assert c['additional_cycles']>c['raw_read_bytes']//128


def test_shared_extents_external_buffers_not_free():
    l=C.shared_layout();end=0
    for r in l['regions']:
        assert r['base']==end and r['bytes']>0
        end=r['base']+r['bytes']
    assert end==53248 and l['unused_bytes']==12288
    assert l['external_coefficient_transpose_bytes']+l['external_activation_transpose_bytes']==3072
    assert l['external_buffers_charged_separately']


@pytest.mark.parametrize('key,value',[('measured',True),('integer_instruction_latency',0),
    ('shared_instruction_latency',0),('barrier_cycles',0),('bank_ports',2),
    ('shared_banks',64),('transpose_coefficient_buffer',0)])
def test_free_or_unpriced_profile_refused(key,value):
    p=copy.deepcopy(C.assumptions());p[key]=value
    with pytest.raises(ValueError):C.validate(p)


def test_latency_sensitivity_and_tail():
    p=C.assumptions();slow=copy.deepcopy(p);slow['integer_instruction_latency']*=2
    assert C.transpose(1024,slow)['additional_cycles']>C.transpose(1024,p)['additional_cycles']
    assert C.transpose(512,p)['tiles']==16
    with pytest.raises(ValueError):C.transpose(640,p)


def test_exact_candidate_binding_and_80_composition():
    r=C.build();c=r['composition']
    assert len(c['bindings'])==80 and c['source_program_operations']==2213
    assert c['original_local_cycles']==6854
    assert c['additional_transpose_cycles']>0
    assert c['HC80_conditional_compute_staging_us']==pytest.approx(80*c['conditional_compute_staging_cycles_operator']/900)
    assert all(len(b['service_nodes_unpriced'])==4 for b in c['bindings'])
    assert c['full_token_cycles'] is None and not c['complete_schedule_admitted']
    assert r['RF']['physical_bytes_die']==8388608
    assert r['RF']['analytical_macro_outline_area_mm2']==pytest.approx(7.96994961408)
    assert not r['ready_to_build'] and r['headline_rate'] is None
    assert r['numerical_scope']['reduction_boundaries']==91


def test_receipt_roundtrip_and_pin_refusal():
    r=json.loads(json.dumps(C.build()));C.check(r)
    r['pins']['tools/w19_gpu_simd_contract.py']='0'*64
    with pytest.raises(ValueError,match='pin drift'):C.check(r)
