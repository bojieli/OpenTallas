"""HANDOFF 0ga 2026-10-18: a recorded per-pair clock_rule excess <= 2 ps becomes a printed WARN; anything else FAILs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pre_route_gate as PRG  # noqa: E402

PAIRS = [{"corner": "ff", "a": "u_dly", "b": "u_syn", "ps": 80.5}, {"corner": "ff", "a": "u_chn", "b": "u_syn", "ps": 67.3}]
W = {"pair": "ddly-dsyn", "ff_ps": 80.5, "limit_ps": 80, "by": "coordinator 0ga 10-18"}


def run(waiver, ff=80.5, pairs=PAIRS):
    g = PRG.Gate()
    g.clock = {"evidence": {"tt_pin_spread_ps": 68.5, "ff_pin_spread_ps": ff, "tt_pin_spread_basis": "child_pair",
                            "ff_pin_spread_basis": "child_pair", "child_pairs": pairs}}
    g.add("FAIL", "clock_rule", "FF pin-flop spread > 80")
    PRG.apply_clock_rule_waiver(g, {"clock_rule_waiver": waiver} if waiver else {})
    return [i for i in g.items if i["check"] == "clock_rule"][0]


def test_waived():
    for pair in ("ddly-dsyn", "dly-syn", "u_syn-u_dly"):
        i = run(dict(W, pair=pair))
        assert i["severity"] == "WARN" and "WAIVED" in i["message"]


def test_wrong_pair():
    assert run(dict(W, pair="dchn-dsyn"))["severity"] == "FAIL"


def test_no_waiver():
    assert run(None)["severity"] == "FAIL"


def test_excess_too_big():
    assert run(dict(W, ff_ps=82.5), ff=82.5, pairs=[dict(PAIRS[0], ps=82.5)])["severity"] == "FAIL"


def test_value_above_recorded():
    assert run(W, ff=81.0, pairs=[dict(PAIRS[0], ps=81.0)])["severity"] == "FAIL"


def test_other_pair_over():
    assert run(W, pairs=PAIRS + [{"corner": "ff", "a": "u_chn", "b": "u_out", "ps": 80.2}])["severity"] == "FAIL"
