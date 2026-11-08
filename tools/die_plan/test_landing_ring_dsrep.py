import copy
import pytest
from clock_landings import Landings, LandingError
from test_clock_landings import B_BODY, ca_vehicle
from test_count_straps import strap_vehicle


def test_select_replication_preserves_cycles_and_writer_contract():
    p, t = strap_vehicle()
    base = Landings(copy.deepcopy(p), copy.deepcopy(t))
    baseline = base.type_rtl('B', B_BODY)
    p['partition_types']['B'].setdefault('clock', {})['landing_ring_dsrep'] = {'buses':['y'], 'dsrep':4}
    variant = Landings(p, t)
    rtl = variant.type_rtl('B', B_BODY)
    assert rtl.replace(', .DSREP(4)', '') == baseline
    assert '.WREG(1)' not in rtl
    assert variant.manifest()['lane_added_cycles'] == base.manifest()['lane_added_cycles']
    receipt = variant.manifest()['reset_placements']['B']['y']
    assert receipt['ring_dsrep'] == 4
    assert receipt['ring_dsrep_added_cycles'] == 0
    assert 'strap_k_delta' not in receipt


def test_absent_or_other_bus_leaves_rtl_byte_identical():
    p,t = strap_vehicle()
    expected = Landings(copy.deepcopy(p),copy.deepcopy(t)).type_rtl('B',B_BODY)
    p['partition_types']['B'].setdefault('clock', {})['landing_ring_dsrep'] = {'buses':['other'], 'dsrep':4}
    assert Landings(p,t).type_rtl('B',B_BODY) == expected


def test_non_strap_ring_rejects_unsupported_parameter():
    p,t=ca_vehicle()
    p['partition_types']['B'].setdefault('clock', {})['landing_ring_dsrep'] = {'buses':['y'], 'dsrep':4}
    with pytest.raises(LandingError,match='strap form'):
        Landings(p,t).type_rtl('B', B_BODY)


@pytest.mark.parametrize('bad',[True,0,3,128,'4'])
def test_invalid_copy_count_fails_before_rtl(bad):
    p,t=strap_vehicle()
    p['partition_types']['B'].setdefault('clock', {})['landing_ring_dsrep'] = {'buses':['y'],'dsrep':bad}
    with pytest.raises(LandingError,match='divide 64'):
        Landings(p,t).type_rtl('B',B_BODY)


def test_conflicting_writer_copy_count_is_rejected():
    p,t=strap_vehicle()
    p['partition_types']['B'].setdefault('clock', {}).update(
        landing_ring_dsrep={'buses':['y'],'dsrep':4},
        landing_ring_wreg={'buses':['y'],'dsrep':2})
    with pytest.raises(LandingError,match='conflicting'):
        Landings(p,t).type_rtl('B',B_BODY)
