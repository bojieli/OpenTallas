import pytest
from tools.w17_crom_vm_baseline import build,reserve

def test_capacity_never_substitutes_for_exclusion_proof():
    with pytest.raises(ValueError,match='manifest'):reserve(490640,33648,524288,None)
    with pytest.raises(ValueError,match='alias'):reserve(490640,33648,524288,[(490641,490642)])
    with pytest.raises(ValueError,match='capacity'):reserve(0,549760,524288,[])
    assert reserve(490640,33648,524288,[(0,490640)])

def test_actual_mapping_baseline_rejected_without_free_rows():
    r=build()
    assert len(r['logical_stage_maps'])==41 and r['commands_per_rank']==491
    assert r['stage_capacity']['max_stage_words']==33648
    assert r['stage_capacity']['sequential_constant_only_deficit_words']==25472
    assert r['arena_declared_allocation_aliases']
    assert r['authoritative_free_row_reservation'] is None
    assert r['warm']['C_rotate_su_op_extra_slow_cycles']==37
    assert not r['hardware_admission'] and r['cold']['actual_TTFT'] is None
