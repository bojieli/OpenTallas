"""s81_t51w_repoint: the pending native_w abstract -> signed view; pins and outline must not change; W-only taps take the
measured insertion, shared taps keep theirs."""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s81_t51w_repoint as RW  # noqa: E402

MOD = "s81p_x_native_w"
OLD = "old/" + MOD + ".lef"
NEWV = "views/" + MOD + "_signed"
M = {"tt": {"mean": 259.21}, "ff": {"mean": 198.74}}


def _plan():
    hc = [{"module": MOD, "lef": OLD, "pins_file": "pins/w.json", "outline_um": [613.44, 1209.6]},
          {"module": "s81p_x_native_e", "lef": "e.lef", "lib": "e.lib", "pins_file": "pins/e.json", "outline_um": [1, 1]}]
    taps = [{"name": "clk_t1", "insertion_ps": 250, "insertion_ff_ps": 202.5, "lands_on": [{"pin": MOD + ".clk_t1", "xy": [1, 1]}]},
            {"name": "clk_t2", "insertion_ps": 250, "insertion_ff_ps": 202.5,
             "lands_on": [{"pin": "s81p_x_native_e.clk_t2", "xy": [2, 2]}, {"pin": MOD + ".clk_t2", "xy": [3, 3]}]},
            {"name": "clk_t3", "insertion_ps": 240, "lands_on": [{"pin": "s81p_x_native_e.clk_t3", "xy": [4, 4]}]}]
    return {"partition_types": {"t51": {"hard_cores": hc, "clock": {"taps": taps}}}}


def test_repoint_plan():
    p = _plan()
    cnt = RW.repoint_plan(p, "t51", MOD, OLD, NEWV, "pins/w.json", M, [613.44, 1209.6], "note x")
    hc = p["partition_types"]["t51"]["hard_cores"][0]
    assert hc["lef"] == NEWV + "/" + MOD + ".lef" and hc["lib"] == NEWV + "/" + MOD + "_tt.lib" and hc["note"] == "note x"
    taps = p["partition_types"]["t51"]["clock"]["taps"]
    assert (taps[0]["insertion_ps"], taps[0]["insertion_ff_ps"]) == (259.21, 198.74)
    assert (taps[1]["insertion_ps"], taps[2]["insertion_ps"]) == (250, 240)
    assert cnt == {"taps_only": 1, "taps_shared": 1}


def test_repoint_refuses_reshape_and_wrong_form():
    with pytest.raises(ValueError, match="no reshape"):
        RW.repoint_plan(_plan(), "t51", MOD, OLD, NEWV, "pins/w.json", M, [600.0, 1209.6], "n")
    p = _plan()
    p["partition_types"]["t51"]["hard_cores"][0]["lib"] = "x.lib"
    with pytest.raises(ValueError, match="pending form"):
        RW.repoint_plan(p, "t51", MOD, OLD, NEWV, "pins/w.json", M, [613.44, 1209.6], "n")


def test_check_pins():
    view = [{"bus": "clk_t1", "bit": None, "layer": "M7", "x": 1.0, "y": 2.0},
            {"bus": "d", "bit": 3, "layer": "M5", "x": 4.0, "y": 5.0}]
    plan = {"source": "kit pins.json sha256 abc123", "pins": [{"name": "clk_t1", "layer": "M7", "x": 1.0, "y": 2.0},
                                                              {"name": "d[3]", "layer": "M5", "x": 4.0, "y": 5.0}]}
    assert RW.check_pins(plan, view, "abc123") == 2
    with pytest.raises(ValueError, match="cite"):
        RW.check_pins(plan, view, "zzz")
    bad = copy.deepcopy(plan)
    bad["pins"][1]["x"] = 4.02
    with pytest.raises(ValueError, match="differs on 1 pins"):
        RW.check_pins(bad, view, "abc123")


def test_lef_size():
    lef = f"MACRO {MOD}\n  CLASS BLOCK ;\n  SIZE 613.44 BY 1209.6 ;\nEND {MOD}\n"
    assert RW.lef_size(lef, MOD) == [613.44, 1209.6]
    with pytest.raises(ValueError):
        RW.lef_size(lef, "other")
