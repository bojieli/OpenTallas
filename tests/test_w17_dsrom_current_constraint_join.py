import sys
from pathlib import Path
from decimal import Decimal as D
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_dsrom_current_constraint_join as J

def test_integer_residency_and_power_join_does_not_transfer_fit():
    r=J.build();e=r['Engram']
    assert e['physical_macros']==1500067 and e['homes']==192
    assert D(e['maximum_home_clock_and_leak_W'])+D(e['margin_before_data_PHY_hub_W'])==D('474.56')
    assert D(e['all_arcs_allocation_excess_W'])>0
    assert e['allocation_is_not_physical_minimum']
    assert not r['physical_admission'] and r['full_token_latency'] is None
    assert r['CROM']['placement_verdict']=='REJECT_UNRESERVED_SU_DISPLACEMENT'
    assert 'VM.CONSTANT_HE' in r['candidate_decisions']['mandatory_retained']
