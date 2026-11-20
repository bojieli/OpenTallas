"""DIE-LEVEL-CHECK-1119 (FABLE-PD-S81-2040 fix 1): a plain (budget) tap is priced at its partition type's declared
insertion, not the die common latency."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402

REG = dict(clkq_max_wire_ps=40.0, clkq_min_nowire_ps=20.0, setup_ps=10.0, hold_ps=5.0)
OV = {"reason": "serdes/col 450 budget"}
PLAN = {
    "clock": {"common_latency_ps": 250},
    "partition_types": {
        "col": {"clock": {"insertion_ps": 450, "insertion_target_override": OV}},
        "colff": {"clock": {"insertion_ps": 450, "insertion_ff_ps": 380, "insertion_target_override": OV}},
        "noreason": {"clock": {"insertion_ps": 450}},
        "plain": {"clock": {}},
    },
    "partitions": [{"name": "c0", "type": "col"}, {"name": "c1", "type": "colff"},
                   {"name": "n0", "type": "noreason"}, {"name": "p0", "type": "plain"}],
}
TAPS = {"t_c0__clk": {"part": "c0"}, "t_c1__clk": {"part": "c1"}, "t_n0__clk": {"part": "n0"},
        "t_p0__clk": {"part": "p0"}, "t_x__clk": {"part": "unknown"}}


def test_plain_tap_takes_type_insertion_tt():
    bl = R.tap_budget_latency(PLAN, TAPS, "TT", 250.0)
    assert bl == {"t_c0__clk": 450.0, "t_c1__clk": 450.0, "t_n0__clk": 250.0, "t_p0__clk": 250.0, "t_x__clk": 250.0}


def test_plain_tap_takes_type_insertion_ff():
    bl = R.tap_budget_latency(PLAN, TAPS, "FF", 202.5)
    assert bl["t_c0__clk"] == 364.5        # FF_TT_INSERTION_RATIO x 450
    assert bl["t_c1__clk"] == 380.0        # declared FF budget wins
    assert bl["t_p0__clk"] == 202.5 and bl["t_n0__clk"] == 202.5


def test_budget_views_price_type_latency_and_cancel_within_type():
    v = R.budget_views(PLAN, TAPS, "TT", REG, 250.0)
    assert v["t_c0__clk"][0]["lat_late"] == 450.0 and v["t_c0__clk"][0]["lat_early"] == 450.0
    assert v["t_p0__clk"][0]["lat_late"] == 250.0
    # same type, same declared latency -> it cancels in a pair (setup/hold equal the zero-latency pair)
    a, b = v["t_c0__clk"], v["t_c1__clk"]
    s = R.endpoint_slacks({}, {}, 0, 0, 0, 0, 0, 1000, 0, 0, a, b)
    z = R.endpoint_slacks({}, {}, 0, 0, 0, 0, 0, 1000, 0, 0, [R.budget_model(REG, 0)], [R.budget_model(REG, 0)])
    assert [x[:2] for x in s] == [x[:2] for x in z]

