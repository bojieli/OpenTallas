"""Plain-lane input budget event (DIE-S81-51 11-03, COORD 10:49 plain-seam input-face class part 2):
gen_phys.plain_seam_split on opt-in plan clock.plain_seam_split; absent = no change."""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import landing_contract as LC  # noqa: E402


def _plan(cfg, W, ring=()):
    slot = lambda n: {"name": n, "in_face": "W", "out_face": "E", "width": 2, "stations": 2}
    types = {"tx": {"ft_slots": [slot("a"), slot("b")]}, "rx": {"ft_slots": [slot("a"), slot("b")]},
             "lr": {"ft_slots": [slot("a")]}}
    parts = {"p0": {"type": "tx"}, "p1": {"type": "rx"}, "p2": {"type": "rx"}, "p3": {"type": "lr"}}
    ports = {"x0": {"src": {"part": "p0", "bus": "a_o"}, "dst": {"part": "p1", "bus": "a_i"}},
             "x1": {"src": {"part": "p0", "bus": "a_o"}, "dst": {"part": "p2", "bus": "a_i"}},
             "x2": {"src": {"part": "p0", "bus": "b_o"}, "dst": {"part": "p3", "bus": "a_i"}},   # landed receiver
             "x3": {"src": {"part": "p0", "bus": "b_o"}, "dst": {"part": "p1", "bus": "b_i"}}}
    clock = {"ft_hop_in_share": 0.16, "tap_window": {"window_ps": 100.0, "related_pair_ps": 100.0, "per_type_ps": W},
             "seam_hold": {"sender_ps": 0.0, "seam_ps": 40.0}}
    if cfg:
        clock["plain_seam_split"] = cfg
    return SimpleNamespace(die={"period_ps": 833.0}, clock=clock, types=types, parts=parts, ports=ports), ring


def _run(monkeypatch, cfg, W=None, ring=("lr",)):
    P, _ = _plan(cfg, W or {})
    monkeypatch.setattr(LC, "ring_input_ports", lambda P, tn: [("fclk_in_a_i", ["a_i[*]"])] if tn in ring else [])
    return gen_phys.plain_seam_split(P)


def test_absent_is_empty(monkeypatch):
    assert _run(monkeypatch, None) == {"in": {}, "out": {}}


def test_receiver_caps_and_sender_cut(monkeypatch):
    s = _run(monkeypatch, {"rx_in_max_ps": 480.0, "rx_in_raw_max_ps": 580.0})
    # rx window 100: raw min(699.72, 580, 480 + 100) = 580 -> written 480; landed lr untouched
    assert s["in"] == {"rx": {"a_i": 580.0, "b_i": 580.0}}
    # a_o: every port plain -> T - 580 = 253; b_o also feeds the landed lr ring -> keeps 0.16 T (absent)
    assert s["out"] == {"tx": {"a_o": 253.0}}


def test_small_window_binds_written_cap(monkeypatch):
    s = _run(monkeypatch, {"rx_in_max_ps": 480.0, "rx_in_raw_max_ps": 580.0}, W={"rx": 90.0})
    assert s["in"]["rx"]["a_i"] == 570.0 and s["out"]["tx"]["a_o"] == 263.0


def test_seam_sum_never_exceeds_period(monkeypatch):
    s = _run(monkeypatch, {"rx_in_max_ps": 480.0, "rx_in_raw_max_ps": 580.0}, W={"rx": 90.0})
    P, _ = _plan(None, {})
    for pr in P.ports.values():
        rt, st = P.parts[pr["dst"]["part"]]["type"], P.parts[pr["src"]["part"]]["type"]
        i = s["in"].get(rt, {}).get(pr["dst"]["bus"], 0.84 * 833.0)
        o = s["out"].get(st, {}).get(pr["src"]["bus"], 0.16 * 833.0)
        assert o + i <= 833.0 + 1e-6


def test_delay_lines_group_by_value():
    txt = gen_phys._ft_delay_lines("input", ["a_i", "b_i", "c_i"], 699.72, {"b_i": 580.0}, lambda v: f"{v - 100:.4f}")
    assert txt == ("set_input_delay -max 599.7200 -clock vclk [get_ports {a_i[*] c_i[*]}]\n"
                   "set_input_delay -max 480.0000 -clock vclk [get_ports {b_i[*]}]\n")
