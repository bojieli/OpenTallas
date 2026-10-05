import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stagebank',ROOT/'tools/v41_floorplan_stage_bankmap.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_actual_expert_shapes_have_equal_exact_bank_depth():
    a=m.reserve(576,5120);b=m.reserve(1280,2304)
    assert a['required_rows_per_bank']==b['required_rows_per_bank']==5760
    assert a['macros']==b['macros']==8
    assert a['useful_payload_bytes']==b['useful_payload_bytes']==1566720

def test_unsupported_geometry_refused():
    with pytest.raises(ValueError):m.reserve(575,5120)
    with pytest.raises(ValueError):m.reserve(576,5119)

def test_manifest_reservations_no_overlap_and_not_false_fit():
    x=json.loads((ROOT/'results/floorplan/v41_stage17_bankmap.json').read_text());cur=0
    for e in x['expert_matrices']:
        assert e['macro_first']==cur
        assert e['macro_last']-e['macro_first']+1==e['macros'];cur=e['macro_last']+1
        assert e['output_row_end']-e['output_row_begin']==e['rows']
    assert cur==13296
    assert len(x['expert_matrices'])==554*3
    assert not x['reservation']['capacity_acceptance']
    assert x['unbound_dense_tensors']
