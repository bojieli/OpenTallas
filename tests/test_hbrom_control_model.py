"""Analytical control-protection tests; no RTL qualification claims."""
import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/hbrom_control_model.py'
spec=importlib.util.spec_from_file_location('hbrom_control_model', P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_every_protected_entry_single_bit_fault_denies_commit():
    # Check every distinct width, both replicas and both state/command paths.
    widths={r['bits_per_entry'] for r in m.build()['inventory']}
    for w in widths:
        value=((1<<w)-1)//3
        assert m.commit_allowed(value,value,value,value,width=w)
        for bit in range(w):
            bad=value^(1<<bit)
            for args in [(bad,value,value,value),(value,bad,value,value),
                         (value,value,bad,value),(value,value,value,bad)]:
                assert not m.commit_allowed(*args,width=w)
        assert not m.commit_allowed(value,value,value,value,width=w,poisoned=True)


def test_out_of_range_identity_cannot_alias_after_truncation():
    assert not m.checked_equal(1<<64,0,64)
    assert not m.checked_equal(-1,(1<<64)-1,64)
    assert not m.checked_equal(1<<64,1<<64,64)


def test_full_selected_nc1_inventory_and_finite_credit_capacity():
    plan=m.build()
    rows={r['name']:r for r in plan['inventory']}
    assert rows['activation_write_valid_bits']['raw_bits']==256
    assert rows['ring_slot_identity']['raw_bits']==1024*64
    assert rows['output_valid_and_reserved_bits']['raw_bits']==8192
    assert rows['rom_feed_live_tag_bitmap']['raw_bits']==1024
    assert plan['cycles']['protected_credit_depth_min']==40
    assert plan['area']['raw_state_bits']==sum(r['raw_bits'] for r in plan['inventory'])
    assert plan['area']['protected_state_bits']>2*plan['area']['raw_state_bits']
    assert plan['area']['packed_total_allowance_mm2']>plan['area']['packed_increment_over_unprotected_mm2']>0


def test_latency_growth_is_priced_in_both_storage_and_credits():
    low=m.build(network_latency=14)
    high=m.build(network_latency=21)
    assert high['area']['raw_state_bits']>low['area']['raw_state_bits']
    assert high['cycles']['protected_credit_depth_min']-low['cycles']['protected_credit_depth_min']==14


@pytest.mark.parametrize('kw', [{'ring_depth':1000},{'max_out':1025},{'rows':0},{'network_latency':-1},{'descriptor_depth':3}])
def test_illegal_finite_shapes_rejected(kw):
    with pytest.raises(ValueError):
        m.build(**kw)
