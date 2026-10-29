"""Physical contracts for the HEAD crop; no route or signoff claim."""
import copy
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('resize', Path(__file__).with_name('head_channel_resize_delta.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

@pytest.mark.parametrize('orient', ['R0','MX','MY','R180'])
def test_boundary_interfaces_stay_at_same_die_coordinates(orient):
    # The retained vertical face spans the original E face; arbitrary crops
    # must preserve positions after mirrored instance-origin movement.
    old = [100, 200]; w,h = 1442.88,1226.88
    crop = [0,354.24,w,483.84]
    new = r.new_origin(old,orient,w,h,crop)
    for x,y in [(0,380),(w,448),(w,466)]:
        before = r.to_die(old,orient,w,h,[x,y])
        after = r.to_die(new,orient,crop[2]-crop[0],crop[3]-crop[1],[x-crop[0],y-crop[1]])
        assert after == before


def test_ring_reader_extent_is_in_density_inventory():
    t={'clock':{'landing_contract':{'bands':{'wide':{'rect_um':[10,20,310,120],
                  'clock_roles':{'local_read_flops':576}}}}}}
    r.set_bank_taps(t)
    c=t['clock']
    assert c['tap_mode']=='density'
    assert {(x,y) for x,y,n in c['sink_sites_um']} == {(10,20),(10,120),(310,20),(310,120)}
    assert sum(n for x,y,n in c['sink_sites_um']) == 576
    assert c['tap_radius_um']<=250


def test_crop_rejects_functional_pin_outside_outline():
    t={'outline_um':[100,100],'clock':{'tap_um':[50,50], 'landing_contract':{
       'pins':[{'xy_um':[101,80]}]}}}
    assert r.check_inside(t)==[(101,80)]
