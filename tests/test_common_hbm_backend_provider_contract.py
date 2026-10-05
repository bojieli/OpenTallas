import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('backend_provider',Path(__file__).resolve().parents[1]/'tools/common_hbm_backend_provider_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_acceptance_without_WR_issue_never_commits():
    x=m.BurstVisibilityModel();x.preload(1,b'a'*32);x.reserve(0,1,b'b'*32);x.tick(1000)
    assert x.read(1,True)==b'a'*32 and x.peek_visible(0) is None

def test_actual_burst_end_backing_action_and_retained_visible_timestamp():
    x=m.BurstVisibilityModel();x.preload(1,b'a'*32);x.reserve(0,1,b'b'*32);x.WR_issue(0,1,0);x.take_scheduled(0)
    x.tick(8);assert x.read(1,True)==b'a'*32 and x.peek_visible(0) is None
    x.tick();assert x.read(1,True)==b'b'*32
    e=x.peek_visible(0);assert e['visible_ps']==7500
    x.tick(100);assert x.peek_visible(0)==e

def test_schedule_callback_stall_does_not_lose_backing_commit():
    x=m.BurstVisibilityModel();x.reserve(0,1,b'b'*32);x.WR_issue(0,1,0);x.tick(9)
    assert x.peek_visible(0) is None and x.read(1,True)==b'b'*32
    x.take_scheduled(0);assert x.peek_visible(0)['visible_ps']==7500

def test_four_backend_events_reserved_through_visibility_delivery():
    x=m.BurstVisibilityModel()
    for t in range(4):x.reserve(t,t,b'a'*32);x.WR_issue(t,t,0);x.take_scheduled(t)
    x.tick(9);assert x.reserve(4,4,b'b'*32) is None
    x.take_visible(0);assert x.reserve(4,4,b'b'*32)==4

def test_fulladdress_high_sector_does_not_modulo_alias():
    x=m.BurstVisibilityModel();a=(1<<27)+1;b=a+(1<<24)
    x.preload(a,b'a'*32);x.preload(b,b'b'*32);assert x.read(a,True)!=x.read(b,True)

def test_unloaded_backing_and_unpublished_reader_fail_closed():
    x=m.BurstVisibilityModel();x.preload(1,b'a'*32)
    with pytest.raises(ValueError):x.read(1,False)
    with pytest.raises(ValueError):x.read(2,True)

def test_wrong_or_duplicate_actual_WR_event_rejected():
    x=m.BurstVisibilityModel();x.reserve(0,1,b'a'*32)
    with pytest.raises(ValueError):x.WR_issue(0,2,0)
    x.WR_issue(0,1,0)
    with pytest.raises(ValueError):x.WR_issue(0,1,0)

def test_finite_capacity_and_unproven_tag_recycle_rejected():
    x=m.BurstVisibilityModel()
    with pytest.raises(ValueError):x.reserve(0,x.capacity,b'a'*32)
    x.reserve(0,1,b'a'*32)
    with pytest.raises(ValueError):x.reserve(0,2,b'a'*32)

def test_exact_clock_fraction_and_extra_pending_storage_price():
    x=m.BurstVisibilityModel();x.tick(3);assert x.now==2500
    p=m.compose();assert p['storage']['bits_per_pending_backend_slot']==512
    assert p['additional_port_cost']['register_bits']==8192
