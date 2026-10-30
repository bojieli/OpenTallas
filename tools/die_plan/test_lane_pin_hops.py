"""Mandatory slot pins cannot be shortcut by FF-centre Manhattan distance."""
from types import SimpleNamespace
import check


def plan(points):
    return SimpleNamespace(lane_crossings=lambda lid: [("p", "s", "a", "b")],
                           port_point=lambda name: points[name], slot=lambda part, slot: {"stations": 2})


def test_straight_route_preserves_every_hop():
    p = plan({"a": (100, 0), "b": (700, 0)})
    regs = [(0, 0), (200, 0), (500, 0), (800, 0)]
    assert check.lane_pin_hops(p, "l", regs) == [200, 300, 300]


def test_output_pin_detour_cannot_be_shortcut_by_close_flops():
    p = plan({"a": (100, 0), "b": (2000, 0)})
    regs = [(0, 0), (200, 0), (500, 0), (800, 0)]
    assert check.lane_pin_hops(p, "l", regs) == [200, 300, 2700]


def test_between_two_slots_visits_both_output_and_input_pins():
    points = {"a": (100, 0), "b": (2000, 0), "c": (2000, 100), "d": (700, 100)}
    p = SimpleNamespace(lane_crossings=lambda lid: [("p", "s", "a", "b"), ("q", "s", "c", "d")],
                        port_point=lambda name: points[name], slot=lambda part, slot: {"stations": 1})
    assert check.lane_pin_hops(p, "l", [(0, 0), (200, 0), (500, 100), (800, 100)]) == [200, 3400, 300]
