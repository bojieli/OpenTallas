"""Contracts for the HEAD l48rf RE-FORM plan delta (grow + entries + raw repoint); no route or sign-off claim."""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('rf', Path(__file__).with_name('head_rf_plan_delta.py'))
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)


def to_die(o, orient, W, H, xy):
    x, y = xy
    x = W - x if orient in ('MY', 'R180') else x
    y = H - y if orient in ('MX', 'R180') else y
    return [round(o[0] + x, 3), round(o[1] + y, 3)]


@pytest.mark.parametrize('orient', ['R0', 'MX', 'MY', 'R180'])
def test_grow_keeps_every_object_at_its_die_position(orient):
    W, H, (l, b, r, tp) = 172.8, 86.4, (8.64, 17.28, 25.92, 34.56)
    t = {'outline_um': [W, H], 'clock': {'sink_sites_um': [[10, 20, 3]], 'tap_radius_um': 180.0,
         'landing_contract': {'bands': {'a': {'rect_um': [1, 2, 3, 4]}}}},
         'reset': {'local_taps_um': [[50, 60]]},
         'reset_start_raw_exports': [{'port': 'rst_start_raw_0', 'xy_um': [5, 6]}],
         'ft_slots': [{'in_face': 'W', 'out_face': 'N', 'in_window_um': [10, 20], 'out_window_um': [30, 40]}]}
    g = rf.grow_type(t, l, b, r, tp)
    assert g['outline_um'] == [round(W + l + r, 3), round(H + b + tp, 3)]
    assert g['clock']['sink_sites_um'] == [[10 + l, 20 + b, 3]]          # weight kept
    assert g['clock']['tap_radius_um'] == 180.0                          # size, not a coordinate
    assert g['clock']['landing_contract']['bands']['a']['rect_um'] == [1 + l, 2 + b, 3 + l, 4 + b]
    assert g['ft_slots'][0]['in_window_um'] == [10 + b, 20 + b]          # W face runs along y
    assert g['ft_slots'][0]['out_window_um'] == [30 + l, 40 + l]         # N face runs along x
    o = [1000.0, 2000.0]
    no = rf.new_origin(o, orient, W, H, [-l, -b, W + r, H + tp])
    NW, NH = g['outline_um']
    for old, new in ((t['reset']['local_taps_um'][0], g['reset']['local_taps_um'][0]),
                     (t['reset_start_raw_exports'][0]['xy_um'], g['reset_start_raw_exports'][0]['xy_um'])):
        assert to_die(no, orient, NW, NH, new) == to_die(o, orient, W, H, old)


def test_subtract_clips_channel_around_grown_slot():
    pieces = rf.subtract([0, 0, 100, 100], [20, 30, 60, 70])
    area = sum((q[2] - q[0]) * (q[3] - q[1]) for q in pieces)
    assert area == pytest.approx(100 * 100 - 40 * 40)
    assert all(not rf._ov(q, [20, 30, 60, 70]) for q in pieces)
    assert rf.subtract([0, 0, 10, 10], [20, 20, 30, 30]) == [[0, 0, 10, 10]]


def test_grow_rejects_off_grid():
    plan = {'partition_types': {'t': {'outline_um': [86.4, 86.4]}}, 'partitions': [], 'die': {'outline_um': [1000, 1000]}}
    with pytest.raises(SystemExit):
        rf.apply_grow(plan, {'t': [1.0, 0, 0, 0]}, {'grow': {}, 'channels_clipped': []})
