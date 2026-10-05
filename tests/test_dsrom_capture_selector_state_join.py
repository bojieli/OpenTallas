import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_selector_state_join as J
import dsrom_capture_home_r49 as H

def test_distinct_state_and_no_recharge():
    m=J.build()
    assert m['disjoint_core_and_transport_bits']==1174534
    assert m['core']['original_bits']==571214
    assert m['transport']['full_bits']==476180
    assert m['costs_already_inside_whole_screen']
    assert m['nine_call_increment_cycles']==3312
    assert not m['contextual_PR_admitted']
    assert m['actual_accepted_consumer_deadline'] is None

def test_overlap_eliminated_but_no_legal_fit_credit():
    m=J.build()
    assert m['capture_home']['gap_um']==4.32
    assert m['capture_home']['common_owner_shard'] is None
    assert not m['complete_legal_allocation']

def test_positive_source_clock_reset_loads():
    m=J.build()
    for v in m['transport_pin_demand'].values():
        assert v['transport_CLK_fF']>200000
        assert v['transport_RESETN_fF']>0
        assert v['transport_SETN_fF']>0

@pytest.mark.parametrize('mutation',['core','FF','charge','cycle','overlap'])
def test_false_optimism_or_duplicate_charge_refused(mutation):
    d=copy.deepcopy(J.inputs());h=H.build()
    if mutation=='core':d['core']['shapes'][0]['state_bits']=127140
    if mutation=='FF':d['transport']['fixed']['data_FF']=0
    if mutation=='charge':d['transport']['cost']['old_station_replaced_not_added']=False
    if mutation=='cycle':d['transport']['fixed']['transport_cycles_per_call']=102
    if mutation=='overlap':h['geometry_raw_common_overlap_free']=False
    with pytest.raises(ValueError):J.reconcile(d['core'],d['transport'],d['review'],d['cells'],h)
