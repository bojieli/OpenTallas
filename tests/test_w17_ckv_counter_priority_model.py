import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_ckv_counter_priority_model as C

def test_reset_priority_and_unchanged_normal_count():
    for count in (0,1,511,512,1023):
        for nwr in range(6):
            assert C.next_count(count,nwr,True)==0
            assert C.next_count(count,nwr,False)==count+nwr

def test_local_gate_does_not_transfer_broad_admission():
    r=C.build()
    assert r['counter_bits']==11 and r['added_pipeline_cycles']==0
    assert r['added_boundary_bits']==0 and r['added_FF_bits']==0
    assert r['local_companion_RTL_exact_gate_ready'] and not r['broad_admission']
    assert r['whole_candidate_power_not_a_dependency_of_local_exactness']
    assert r['contextual_SS_FF'] is None
