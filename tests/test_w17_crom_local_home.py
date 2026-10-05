import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_crom_local_home as L

def test_local_candidate_displaces_existing_SU_and_prices_both_routes():
    r=L.build()
    assert r['registered_route_fast_cycles_each_direction']==11
    assert r['placement_verdict']=='REJECT_UNRESERVED_SU_DISPLACEMENT'
    assert not r['physical_admission'] and r['full_operator_latency'] is None
    assert r['logical_coefficient_reads_per_rank']==549760
    assert r['selected_model_candidate']['total_banks']==7380
    for row in r['scenarios']:
        assert row['added_forward_control_pipeline_bits']==704
        assert row['added_reverse_control_pipeline_bits']==768
        assert row['old75route_power_not_subtracted']
