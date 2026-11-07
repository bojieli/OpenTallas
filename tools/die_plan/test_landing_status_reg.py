import copy
import pytest
from clock_landings import Landings,LandingError
from test_clock_landings import ca_vehicle,vehicle,B_BODY
from test_count_straps import strap_vehicle

@pytest.mark.parametrize('strapped',[False,True])
def test_status_reg_is_explicit_and_adds_no_data_cycle(strapped):
    p,t=strap_vehicle() if strapped else ca_vehicle()
    base=Landings(copy.deepcopy(p),copy.deepcopy(t));baseline=base.type_rtl('B',B_BODY)
    p['partition_types']['B']['landing_status_reg']=False
    off=Landings(copy.deepcopy(p),copy.deepcopy(t));assert off.type_rtl('B',B_BODY)==baseline
    p['partition_types']['B']['landing_status_reg']=True
    on=Landings(p,t);text=on.type_rtl('B',B_BODY)
    assert '.STATUS_REG(1)' in text
    assert text.replace(', .STATUS_REG(1)','')==baseline
    record=on.manifest()['reset_placements']['B']['y']
    assert record['status_reg_added_data_cycles']==0 and record['status_reg_added_fault_cycles']==1
    assert on.manifest()['lane_added_cycles']==base.manifest()['lane_added_cycles']

def test_status_reg_rejects_plain_ring_or_non_boolean():
    p,t=vehicle();p['partition_types']['B']['landing_status_reg']=True
    with pytest.raises(LandingError,match='count-aligned'):Landings(p,t).type_rtl('B',B_BODY)
    p,t=ca_vehicle();p['partition_types']['B']['landing_status_reg']='true'
    with pytest.raises(LandingError,match='boolean'):Landings(p,t).type_rtl('B',B_BODY)
