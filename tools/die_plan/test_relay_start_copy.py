"""Private same-cycle START outputs of a count-aligned relay origin."""
import copy
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError
from test_clock_landings import ca_relay_vehicle, C_BODY


def fixture(enabled):
    p,t=ca_relay_vehicle()
    t['count_aligned']['strap_form']=True
    for tn,d in CAB.strap_ties(t['count_aligned'],p)['types'].items():
        p['partition_types'][tn]['count_straps']=[dict(name=n,width=w) for n,w in d['straps'].items()]
    p['partition_types']['C']['landing_relay_start_copy']=enabled
    c=Landings(p,t)
    # Minimal relay sender: one existing output broadcast, without a whole die.
    c.by_type['C']['outputs']=['w']
    return c


def test_relay_copy_uses_existing_rx_D_and_raw_reset_without_delay():
    c=fixture(True);s=c.type_rtl('C',C_BODY)
    assert 'assign cland_start_d = cland_rstart_in;' in s
    assert 'assign cland_start_raw = cland_reset_z;' in s
    assert 'ot_dp_landing_relay u_cland_fstart_w (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(cland_fstart_out_w));' in s
    assert c.land_slots('C')['buses']['cland_rstart_in']==dict(form='origin_start',origin='u_cland_rstart_rx')
    assert 'assign cland_fstart_out_w = cland_start;' not in s
    assert '.d(cland_rstart_in), .q(cland_start));' in s


def test_default_keeps_previous_relay_hardware_and_metadata():
    c=fixture(False);s=c.type_rtl('C',C_BODY)
    assert 'assign cland_fstart_out_w = cland_start;' in s
    assert 'u_cland_fstart_w' not in s
    assert 'cland_rstart_in' not in c.land_slots('C')['buses']


def test_relay_copy_rejects_non_boolean_or_wrong_origin_role():
    for v in (1,'true'):
        c=fixture(False);c.types['C']['landing_relay_start_copy']=v
        with pytest.raises(LandingError,match='must be a boolean'):c.type_rtl('C',C_BODY)
    c=fixture(False);c.types['B']['landing_relay_start_copy']=True
    from test_clock_landings import B_BODY
    with pytest.raises(LandingError,match='strap-form relay'):c.type_rtl('B',B_BODY)
