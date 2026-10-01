import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('ckv_feasibility',Path(__file__).resolve().parents[1]/'tools/w11_ckv_merge_feasibility.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_measured_failure_cannot_promote_exactness_or_zero_DRC():
    r=m.build();f=r['preserved_failure'];assert f['metrics']['route_drc']==0
    assert f['metrics']['setup_worst_slack_ps']==-817.655
    assert f['metrics']['hold_worst_slack_ps']==-9.34994
    assert not f['independent_FF_PASS'] and not f['M2_M5_hub_acceptance']
    assert not r['physical_admission'] and not r['engine_RTL_build_ready']
    assert r['full_token_rate'] is None and f['no_retry_or_tune']

def test_mixed_boundary_keeps_exact_rows_and_sixteen_groups():
    p=m.packets(127,512);seen={}
    for packet in p:
        for row in range(packet['first_row'],packet['first_row']+packet['rows']):
            seen.setdefault(row,[]).append(packet['group'])
        assert packet['serialization_cycles']*256>=packet['packet_bits']
    assert set(seen)==set(range(639))
    assert all(groups==list(range(16)) for groups in seen.values())
    mixed=[x for x in p if x['beat']==31]
    assert len(mixed)==16 and all(x['window_rows']==3 and x['ckv_rows']==1 for x in mixed)

def test_required_finite_service_is_explicit_not_baseline_free_rate():
    p=m.price(128,512);assert p['raw_input_serialization_cycles']==6720
    assert p['output_serialization_cycles']==8704
    assert p['conservative_no_overlap_service_cycles']==15424
    assert p['connected_cycles'] is None
    with pytest.raises(ValueError):m.price(129,512)
    with pytest.raises(ValueError):m.price(128,513)
    with pytest.raises(ValueError):m.price(128,512,0)
