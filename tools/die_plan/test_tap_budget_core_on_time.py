"""S81-CLOCK-WINDOW-1119 (COORD 11-20): in an insertion-override type (450 TT), an early core tap delivered exactly on time
(tap early = declared core insertion - type budget) and a plain register of the same type must time as a zero-skew pair.
Before 7696cb76ce the plain register was priced at the die common latency (250) and the pair read 200 ps of false skew."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402

REG = dict(clkq_max_wire_ps=40.0, clkq_min_nowire_ps=20.0, setup_ps=10.0, hold_ps=5.0)
PLAN = {
    "clock": {"common_latency_ps": 250},
    "partition_types": {"col": {"clock": {"insertion_ps": 450, "insertion_target_override": {"reason": "col 450 budget"}}}},
    "partitions": [{"name": "c0", "type": "col"}],
}
TAPS = {"t_c0__clk": {"part": "c0"}, "t_c0__clk_c0": {"part": "c0"}}
CORE_INS, TAP_ARR, PERIOD = 750.0, 6000.0, 1000.0
EARLY = CORE_INS - 450.0            # the tree delivers the core tap this much early (on time)


def _pair(models_core, models_reg, launch_core=True):
    core_arr = TAP_ARR - EARLY
    if launch_core:
        return R.endpoint_slacks({}, {}, core_arr, core_arr, TAP_ARR, TAP_ARR, 0, PERIOD, 0, 0, models_core, models_reg)
    return R.endpoint_slacks({}, {}, TAP_ARR, TAP_ARR, core_arr, core_arr, 0, PERIOD, 0, 0, models_reg, models_core)


def _zero():
    z = [R.budget_model(REG, 0.0)]
    return [x[:2] for x in R.endpoint_slacks({}, {}, 0, 0, 0, 0, 0, PERIOD, 0, 0, z, z)]


def test_on_time_core_and_type_register_are_zero_skew_both_directions():
    views = R.budget_views(PLAN, TAPS, "TT", REG, 250.0)
    core = [R.declared_core_model(REG, "rom", CORE_INS)]
    assert views["t_c0__clk"][0]["lat_late"] == 450.0
    for launch_core in (True, False):
        assert [x[:2] for x in _pair(core, views["t_c0__clk"], launch_core)] == _zero()


def test_die_common_pricing_shows_the_old_200ps_artifact():
    core = [R.declared_core_model(REG, "rom", CORE_INS)]
    old = [R.budget_model(REG, 250.0)]
    s, h = _pair(core, old, launch_core=False)[0][:2]
    z_s, z_h = _zero()[0]
    assert round(h - z_h, 6) == -200.0 and round(s - z_s, 6) == 200.0   # 200 ps of false hold loss
