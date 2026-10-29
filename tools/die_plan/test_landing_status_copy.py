import copy
import pytest
from clock_landings import Landings,LandingError
from test_clock_landings import ca_vehicle,vehicle,B_BODY
from test_count_straps import strap_vehicle

@pytest.mark.parametrize('strapped',[False,True])
def test_status_bank_copy_is_explicit_and_prices_flops_without_cycles(strapped):
    p,t=strap_vehicle() if strapped else ca_vehicle()
    base=Landings(copy.deepcopy(p),copy.deepcopy(t));baseline=base.type_rtl('B',B_BODY)
    p['partition_types']['B']['landing_control_status_copy']=False
    off=Landings(copy.deepcopy(p),copy.deepcopy(t));assert off.type_rtl('B',B_BODY)==baseline
    p['partition_types']['B']['landing_control_status_copy']=True
    on=Landings(p,t);text=on.type_rtl('B',B_BODY)
    assert '.CONTROL_STATUS_COPY(1)' in text
    assert text.replace(', .CONTROL_STATUS_COPY(1)','')==baseline
    record=on.manifest()['reset_placements']['B']['y']
    assert record['status_copy_flops']==8 and record['status_copy_added_cycles']==0
    assert on.manifest()['lane_added_cycles']==base.manifest()['lane_added_cycles']

def test_status_copy_rejects_unimplemented_ring_or_non_boolean():
    p,t=vehicle();p['partition_types']['B']['landing_control_status_copy']=True
    with pytest.raises(LandingError,match='count-aligned'):Landings(p,t).type_rtl('B',B_BODY)
    p,t=ca_vehicle();p['partition_types']['B']['landing_control_status_copy']='true'
    with pytest.raises(LandingError,match='boolean'):Landings(p,t).type_rtl('B',B_BODY)
