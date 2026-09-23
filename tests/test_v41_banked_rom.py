import math
import pytest
from tools.audit_v41_banked_rom import bank_requirements


def test_banks_deliver_requested_rate_under_stated_assumption():
    for rate in (4.5,18,72):
        r=bank_requirements(4595955000,rate)
        assert r['independent_logical_banks']*256*1e9*.65 >= rate*1e12
        assert r['rounded_capacity_bytes']>=4595955000
        assert r['rounded_capacity_bytes']-4595955000 < r['independent_logical_banks']*256


def test_read_power_and_compute_are_charged():
    r=bank_requirements(4595955000,72)
    assert r['read_path_power_W_by_pJ_per_delivered_bit']['1']==576
    assert r['scalar_lanes_at_assumed_clock_and_utilization']==208507
    assert r['read_energy_pJ_per_bit_if_100W_budget']==pytest.approx(.1736111111)


def test_address_stripe_selects_each_bank_once():
    banks=109
    words=list(range(banks))
    assert {w%banks for w in words}==set(range(banks))
    assert {w//banks for w in words}=={0}
    assert {w//banks for w in range(banks,2*banks)}=={1}
