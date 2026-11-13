"""R-CLOCK-5 (HOLD-TAP-1 11-13): kit preflight core_tap_reach -- an early core tap port must sit at its own hard core."""
import json
from pathlib import Path
import kit_preflight as KP

LEF = "MACRO core_m\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE 100.000 BY 50.000 ;\nEND core_m\n"


def kit(tmp_path, pins, macros, taps, orient=None, cfg=""):
    k = tmp_path / "kit"
    (k / "macros").mkdir(parents=True)
    (k / "macros" / "core_m.lef").write_text(LEF)
    (k / "io.tcl").write_text("".join(
        f"place_pin -pin_name {n} -layer M7 -location {{{x:.4f} {y:.4f}}} -pin_size {{0.0320 0.7680}}   ;# interior: die spine tap\n"
        for n, (x, y) in pins.items()))
    (k / "macro_place.tcl").write_text("".join(
        f"place_macro -macro_name {{{i}}} -location {{{x:.4f} {y:.4f}}} -orientation {(orient or {}).get(i, 'R0')} -exact\n"
        for i, (x, y) in macros.items()))
    (k / "core_taps.txt").write_text("# port inst pin|* early_ps insertion_ps\n" + "".join(
        f"{p} {i} clk 10 260\n" for p, i in taps))
    (k / "bound_macro_paths.json").write_text(json.dumps(
        {"rows": [{"inst": i, "physical_inst": i, "physical_master": "core_m"} for i in macros]}))
    (k / "config.mk").write_text(cfg)
    return k


def test_tap_at_its_core_passes(tmp_path):
    k = kit(tmp_path, {"clk_c0": (150.0, 60.0), "clk_c1": (1050.0, 20.0)},
            {"u_a": (100.0, 0.0), "u_b": (1000.0, 0.0)}, [("clk_c0", "u_a"), ("clk_c1", "u_b")])
    rows = dict((r[0], r) for r in KP.core_tap_reach_rows(k))
    assert rows["clk_c0"][2] == 10.0 and rows["clk_c1"][2] == 0.0      # 10 um above the outline; inside the outline
    assert KP.core_tap_reach(k) == []


def test_swapped_taps_fail_and_name_the_core_they_sit_at(tmp_path):
    # the S81 leaf form: each port sits on the OTHER core's site
    k = kit(tmp_path, {"clk_c0": (1050.0, 20.0), "clk_c1": (150.0, 20.0)},
            {"u_a": (100.0, 0.0), "u_b": (1000.0, 0.0)}, [("clk_c0", "u_a"), ("clk_c1", "u_b")])
    errs = KP.core_tap_reach(k)
    assert len(errs) == 2
    assert "core tap clk_c0 is 850 um from its core u_a (limit 300)" in errs[0] and "it sits at u_b" in errs[0]
    assert "R-CLOCK-5" in errs[0]


def test_only_a_far_tap_blocks_and_near_misses_are_named(tmp_path):
    k = kit(tmp_path, {"clk_c0": (350.0, 20.0), "clk_c1": (1500.0, 20.0)},
            {"u_a": (100.0, 0.0), "u_b": (1000.0, 0.0)}, [("clk_c0", "u_a"), ("clk_c1", "u_b")])
    assert KP.core_tap_reach_rows(k)[0][2] == 150.0
    errs = KP.core_tap_reach(k)
    assert len(errs) == 2 and "clk_c1 is 400 um" in errs[0] and "1 more core taps are 100-300 um" in errs[1] and "clk_c0=150" in errs[1]
    # without a tap over the limit the 150-um tap does not block
    k2 = kit(tmp_path / "b", {"clk_c0": (350.0, 20.0)}, {"u_a": (100.0, 0.0)}, [("clk_c0", "u_a")])
    assert KP.core_tap_reach(k2) == []


def test_orientation_swaps_the_outline(tmp_path):
    k = kit(tmp_path, {"clk_c0": (120.0, 95.0)}, {"u_a": (100.0, 0.0)}, [("clk_c0", "u_a")], orient={"u_a": "R90"})
    assert KP.core_tap_reach_rows(k)[0][2] == 0.0          # 50 x 100 after R90: the pin is inside


def test_multi_pin_tap_is_not_judged(tmp_path):
    k = kit(tmp_path, {"clk_c0": (5000.0, 20.0)}, {"u_a": (100.0, 0.0), "u_b": (1000.0, 0.0)},
            [("clk_c0", "u_a"), ("clk_c0", "u_b")])
    assert KP.core_tap_reach_rows(k) == [] and KP.core_tap_reach(k) == []


def test_config_limit_and_off(tmp_path):
    pins, mac, taps = {"clk_c0": (700.0, 20.0)}, {"u_a": (100.0, 0.0)}, [("clk_c0", "u_a")]
    assert len(KP.core_tap_reach(kit(tmp_path / "a", pins, mac, taps))) == 1
    assert KP.core_tap_reach(kit(tmp_path / "b", pins, mac, taps, cfg="export OT_CORE_TAP_REACH_UM = 600\n")) == []
    assert KP.core_tap_reach(kit(tmp_path / "c", pins, mac, taps, cfg="export OT_CORE_TAP_REACH_UM = 0\n")) == []


def test_kit_without_core_taps_is_untouched(tmp_path):
    (tmp_path / "config.mk").write_text("")
    assert KP.core_tap_reach_rows(tmp_path) == [] and KP.core_tap_reach(tmp_path) == []


def test_check_runs_it_as_a_blocking_preflight_check():
    src = (Path(KP.__file__)).read_text()
    assert "run('core_tap_reach', lambda: core_tap_reach(kit))" in src
