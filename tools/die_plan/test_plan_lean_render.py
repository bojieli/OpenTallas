"""plan_lean_render: a tiny fixture plan renders die + type PNGs; a hop over reach is counted (mutant: reach 1e9 counts none).
V2: added_taps counted, ft chains in the > reach count, out-of-outline stations, slot/overlap geometry (mutants: abut and wide gaps not flagged)."""
import sys

import pytest
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


def test_v2_added_taps_ft_out_of_outline_and_slots(tmp_path):
    import copy
    P = copy.deepcopy(PLAN)
    ty = P["partition_types"]["ty__t1"]
    ty["clock"]["added_taps"] = [{"name": "clk_t9", "xy": [100, 100]}, {"name": "clk", "xy": [1, 1]}]   # 2nd duplicates a plan tap name
    ty["ft_slots"] = [{"name": "ft0", "in_face": "N", "in_window_um": [10, 20], "out_face": "S", "out_window_um": [10, 20],
                       "regs_um": [[15, 300], [15, 100], [15, 460]]}]      # N face y 300 -> reg 300,100 hop 200 ok; 100 -> 460 hop 360 ok; reg y 460 > h 300 out of outline
    ty["hard_cores"] += [{"origin_um": [70, 10], "outline_um": [50, 50]}, {"origin_um": [150, 10], "outline_um": [50, 50]},
                         {"origin_um": [190, 30], "outline_um": [50, 50]}]
    over, nlong = R.type_png(P, "ty__t1", tmp_path / "v2.png", {}, 405.0)
    assert R.LAST["added_taps"] == 1                  # a duplicate name is not counted twice
    assert R.LAST["out_of_outline"] == 1
    assert R.LAST["ft_long"] == 1                     # last ft hop (15,100) -> (15,460) is 360; (15,460) -> out face (15,0) is 460 > 405
    assert nlong == R.LAST["chain_long"] + R.LAST["ft_long"] == 2
    assert R.LAST["slots"] == 1 and R.LAST["overlaps"] == 1   # 60 -> 70 gap 10 um (flag); 120 -> 150 gap 30 (ok); 190 overlaps 150..200 (flag)


def test_core_slots_abut_wide_and_vertical():
    a = (0, 0, 50, 50)
    assert R.core_slots([a, (50, 0, 100, 50)]) == []                      # abut (gap 0) is fine
    assert R.core_slots([a, (78, 0, 100, 50)]) == []                      # exactly 28 um: not a slot
    assert [s[4] for s in R.core_slots([a, (60, 10, 100, 40)])] == [10]   # x-facing gap 10
    assert [s[4] for s in R.core_slots([a, (10, 56.17, 40, 90)])][0] == pytest.approx(6.17) and len(R.core_slots([a, (10, 56.17, 40, 90)])) == 1
    assert R.core_slots([a, (200, 200, 250, 250)]) == []                  # no facing extent
    assert R.core_slots([a, (40, 40, 100, 100)])[0][4] == -10             # overlap
    signed = {"origin_um": [49.46, 0], "outline_um": [50, 30],
              "orient": "R90", "track_offset_um": [0.54, 0]}
    assert R.core_rect(signed) == (50, 0, 80, 50)
    assert R.core_slots([a, R.core_rect(signed)]) == []
    assert R.core_slots([a, (50 - 1e-9, 0, 100, 50)]) == []


def test_header_numbers_come_from_the_checkers(tmp_path):
    """t57-style disagreement: a face-bus chain whose WORST pin (far end of the window) is > 405 um from its first station.  The drawn
    from_um is the window centre, so the drawn hop is short; precheck.reach_findings measures from the far end and flags it."""
    import copy
    P = copy.deepcopy(PLAN)
    ty = P["partition_types"]["ty__t1"]
    ty["outline_um"] = [1000, 300]
    ty["buses"] = [{"name": "b", "width": 300, "face": "N", "dir": "in", "window_um": [0, 500]}]
    ty["internal_stations"] = [{"conn": "bus:b", "bits": 300, "from_um": [250, 300], "regs_um": [[700, 250]], "to_um": [800, 250]}]
    ty["ft_slots"] = [{"name": "ft0", "in_face": "N", "in_window_um": [10, 20], "out_face": "S", "out_window_um": [10, 20],
                       "regs_um": [[15, 150]], "bit_sites_um": [[[15, 150]]], "bit_site_cell_um": [1.0, 1.0]}]
    cn = R.checker_numbers(ty, 405.0, [], [])
    assert cn["reach_gate"] + cn["reach_aim"] == len(R.PC.reach_findings(ty, 405.0)) >= 1
    assert cn["ft_out_sites"] == cn["ft_out_regs"] == 0
    ty["ft_slots"][0]["regs_um"] = [[15, 150], [15, 460]]
    ty["ft_slots"][0]["bit_sites_um"] = [[[15, 460]]]
    cn2 = R.checker_numbers(ty, 405.0, [], [])
    assert cn2["ft_out_sites"] == 1 and cn2["ft_out_regs"] == 1          # identical to adv_ft_outside.type_hits
    R.type_png(P, "ty__t1", tmp_path / "h.png", {}, 405.0)
    assert R.LAST["checker"]["reach_gate"] + R.LAST["checker"]["reach_aim"] >= 1
    # mutant: a reach of 1e9 makes the checker report no hop at all
    assert R.checker_numbers(ty, 1e9, [], [])["reach_gate"] == 0
