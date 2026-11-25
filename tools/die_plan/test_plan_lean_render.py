"""plan_lean_render: a tiny fixture plan renders die + type PNGs; a hop over reach is counted (mutant: reach 1e9 counts none)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_lean_render as R  # noqa: E402

PLAN = {"die": {"name": "t", "outline_um": [1000, 1000], "channels": [{"rect_um": [0, 0, 10, 1000]}]},
        "partitions": [{"name": "a", "type": "ty__t1", "origin_um": [100, 100], "orient": "R0"}],
        "partition_types": {"ty__t1": {"outline_um": [400, 300], "hard_cores": [{"origin_um": [10, 10], "outline_um": [50, 50]}],
            "clock": {"taps": [{"name": "clk", "xy": [10, 10]}, {"name": "clk_t1", "xy": [300, 200]}],
                      "sink_sites_um": [[12, 12, 1500], [290, 190, 5]]},
            "internal_stations": [{"from_um": [0, 0], "regs_um": [[500, 0]], "to_um": [510, 0]}]}}}


def test_render_counts_and_writes(tmp_path):
    R.die_png(PLAN, tmp_path / "die.png")
    over, nlong = R.type_png(PLAN, "ty__t1", tmp_path / "t.png", {}, 405.0)
    assert (tmp_path / "die.png").stat().st_size > 1000 and (tmp_path / "t.png").stat().st_size > 1000
    assert over == 1 and nlong == 1                   # tap clk holds 1,500 planned sinks; hop 0 -> 500 um > 405
    over2, nlong2 = R.type_png(PLAN, "ty__t1", tmp_path / "t2.png", {}, 1e9)
    assert nlong2 == 0
