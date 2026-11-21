"""ADOPT-CENSUS-1800: EVENT-CENSUS (vs the previous event) and the plan-geometry absolute census."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import event_census as EC  # noqa: E402
import plan_geom_census as PG  # noqa: E402


def mon_type(pin_xy, band=(17.28, 460.728, 45.36, 469.368), defines=(), extra=None):
    t = {"outline_um": [1442.88, 1226.88], "buses": [], "internal_stations": [], "ft_slots": [],
         "clock": {"landing_contract": {"bands": {"monitor_0": {"rect_um": list(band)}},
                                        "pins": [{"name": "cland_dn_fault_0", "xy_um": list(pin_xy)},
                                                 {"name": "cland_dn_ready_0", "xy_um": [pin_xy[0] - 2, pin_xy[1]]}]}},
         "verilog_defines": list(defines), "reset": {"sync_stages": 2}}
    t.update(extra or {})
    return t


def test_monitor_distance_matches_j5_t36():
    # slice_station t36: seat (31, 465), J5 pin (1329, 1224) = 2,057 um; 3fa87b84b18 pin (2, 467) = 31 um
    assert abs(EC.monitor_um(mon_type((1329.056, 1224.224)))[0] - 2057) < 2
    assert EC.monitor_um(mon_type((2, 467)))[0] < 35
    assert EC.monitor_um({"clock": {}})[0] is None


def test_census_flags_monitor_move_define_loss_and_hop_growth():
    hop = {"internal_stations": [{"conn": "core:a.x|core:b.y", "bits": 1, "from_um": [0, 0], "regs_um": [[500, 0]], "to_um": [600, 0]}]}
    prev = {"slice_station__t36": mon_type((2, 467), defines=["OT_A", "OT_B"]), "iqf__t1": mon_type((31, 466)),
            "keep__t1": mon_type((31, 466))}
    new = {"slice_station__t36": mon_type((1329.056, 1224.224), defines=["OT_A"]), "iqf__t1": mon_type((31, 466), extra=hop),
           "keep__t1": mon_type((31, 466)), "brand_new__t1": mon_type((1329, 1224))}
    rows, held = EC.census(prev, new, {}, {})
    assert set(held) == {"slice_station__t36", "iqf__t1"}
    w = " ".join(held["slice_station__t36"])
    assert "MON_UM" in w and "DEFINES lost OT_B" in w
    assert held["iqf__t1"] == ["HOPS_300 0 -> 1"]
    assert {r["verdict"] for r in rows if r["type"] == "brand_new__t1"} == {"NEW"}      # no previous type: reported, not held


def test_counterpart_by_base_type():
    prev = {"col__t1": mon_type((2, 467))}
    new = {"col__t1__cl1234567": mon_type((1329, 1224), extra={"param_base_type": "col__t1"})}
    _rows, held = EC.census(prev, new, {}, {})
    assert "col__t1__cl1234567" in held


def test_unreg_reads_from_kit_rtl(tmp_path):
    g = tmp_path / "items/lepe_mu_LP__t2/gen/lepe_mu_LP__t2"
    (g / "rtl").mkdir(parents=True)
    (g / "config.mk").write_text("export VERILOG_DEFINES = -DSYNTHESIS -DOT_S81SL_LEP_CRP2\n")
    (g / "rtl/ot_s81sl_slice_lep.sv").write_text("`ifdef OT_S81SL_LEP_RIP1\n`define X 1\n`endif\n`ifdef OT_MESO_DEBUG\n`endif\n")
    kd = EC.kit_dirs([tmp_path / "items"])
    assert kd == {"lepe_mu_LP__t2": str(g)}
    n, names = EC.unreg_reads(g, EC.kit_defines(g))
    assert (n, names) == (1, ["OT_S81SL_LEP_RIP1"])
    assert EC.unreg_reads(g, {"RIP1"})[0] == 0          # the bare-name selector sets it


def test_reset_rows_drop_regresses():
    p = mon_type((2, 467), extra={"relay_depth": [{"inst": "u_land", "port": "rst_n", "D": 3, "path_um": 1443}]})
    n = mon_type((2, 467))
    _rows, held = EC.census({"x__t1": p}, {"x__t1": n}, {}, {})
    assert held["x__t1"] == ["RESET_ROWS reset leg rows 1 -> 0"]


def test_hold_patch_adds_and_clears_census_keys():
    cfg = {"dies": {"s81": {"hold_items": {"old__t1": "EVENT-CENSUS J5: ...", "manual__*": "S81-DIE-R4 stop", "a/b": "x"}}}}
    ops = EC.hold_patch(cfg, "s81", {"t36": ["MON_UM 31 -> 2057 um"], "a/b": ["HOPS_300 0 -> 1"]}, "J6")
    paths = {o["op"] + " " + o["path"] for o in ops}
    assert "add /dies/s81/hold_items/t36" in paths
    assert "add /dies/s81/hold_items/a~1b" in paths                     # JSON pointer escape
    assert "remove /dies/s81/hold_items/old__t1" in paths               # no longer regressed
    assert not any("manual__" in p for p in paths)                      # never touches other holds
    assert all(o["value"].startswith("EVENT-CENSUS J6:") for o in ops if o["op"] == "add")


# ---------------------------------------------------------------- absolute plan-geometry census

def test_abs_hops_and_reset_legs():
    t = {"outline_um": [1000, 1000], "buses": [], "ft_slots": [],
         "internal_stations": [{"conn": "core:a.x|core:b.y", "bits": 1, "from_um": [0, 0], "regs_um": [[250, 0]], "to_um": [600, 0]}],
         "relay_depth": [{"inst": "u_land", "port": "rst_n", "D": 3, "path_um": 1443}, {"inst": "u_q", "port": "u_i", "D": 1, "path_um": 419.9},
                         {"inst": "u_q", "port": "u_v", "D": 1, "path_um": 900}],
         "reset": {"relay_um": 180.0}}
    h = PG.hop_findings(t)
    assert [round(v) for v, _ in h] == [350, 450]           # station hop 250 -> 600; u_v 900 / 2; u_i 210 is fine
    r = PG.reset_findings(t, "/nonexistent")
    assert [round(v) for v, _ in r] == [361]


def test_abs_core_wire_and_pins(tmp_path):
    (tmp_path / "pins_a.json").write_text(json.dumps({"pins": [{"name": "q[0]", "x": 10, "y": 5}, {"name": "q[1]", "x": 12, "y": 5},
                                                               {"name": "rst_n", "x": 1, "y": 1}]}))
    cores = [{"inst": "u_a", "origin_um": [0, 0], "outline_um": [20, 20], "orient": "R0", "pins_file": "pins_a.json"},
             {"inst": "u_b", "origin_um": [800, 0], "outline_um": [20, 20], "orient": "R0", "pins_file": "pins_a.json"},
             {"inst": "u_c", "origin_um": [100, 0], "outline_um": [20, 20], "orient": "MX", "pins_file": "pins_a.json"}]
    t = {"outline_um": [1000, 1000], "hard_cores": cores, "buses": [], "internal_stations": []}
    conns = {"u_a": {"q": ["core:u_b"]}, "u_c": {"q": ["core:u_a"]}}
    f = PG.core_wire_findings(t, tmp_path, conns)
    assert len(f) == 1 and round(f[0][0]) == 789 and "u_a.q" in f[0][1]
    t["internal_stations"] = [{"conn": "core:u_a.q|core:u_b.d", "regs_um": [[400, 0]]}]
    assert PG.core_wire_findings(t, tmp_path, conns) == []          # a station row registers the port
    assert PG.pin_abs(cores[2], 10, 5) == (110, 15)                  # MX flips y
    t["relay_sites"] = {"u_rst_relay.q": [900, 900], "u_lpad_dn.q[0]": [20, 20]}
    r = PG.reset_findings(t, tmp_path)
    assert len(r) == 3 and all("reset pin" in d for _v, d in r)


def test_abs_unreg_read(tmp_path):
    g = tmp_path / "gen/x__t1"
    (g / "rtl").mkdir(parents=True)
    (g / "rtl/m.sv").write_text("`ifdef OT_S81SL_VP_SRAMREG\n`endif\n")
    t = {"hard_cores": [{"inst": "u_m", "module": "ot_sram_1r1w_32x128", "lef": "x.lef"}]}
    f, n = PG.unreg_read_findings(t, g, set())
    assert n == 1 and f[0][0] == 1 and "OT_S81SL_VP_SRAMREG" in f[0][1]
    assert PG.unreg_read_findings(t, g, {"OT_S81SL_VP_SRAMREG"})[0] == []
    assert PG.unreg_read_findings(t, None, set())[0][0][0] is None    # no kit: UNMEASURED, still listed
    assert PG.unreg_read_findings({"hard_cores": []}, g, set()) == ([], 0)


def test_calib_helpers():
    rec = {"pairs": [["a", "b", 3, 579.3, [], "logic"], ["port:x", "c", 9, 900.0, [], "half_cycle"], ["d", "e", 1, 320.0, [], "channel"]]}
    assert PG.placed_worst(rec) == 579.3
    assert PG.kit_type("slw_fe_v1__clfe325744__cl08d14f0d-route-renewed-glider-20898-1795221149.placed.json") == "slw_fe_v1__clfe325744__cl08d14f0d"


def test_hook_steps_skip_cleanly():
    import argparse
    import precheck_hook as H
    a = argparse.Namespace(no_census=False, prev_plan="", plan="/p.json", no_adopt_diff=True, die="s81", event="J6")
    assert H.event_census(a, Path("/nonexistent")) == ""          # no previous event: nothing compared
    a.prev_plan = "/p.json"
    assert H.event_census(a, Path("/nonexistent")) == ""          # re-apply of the same plan
    assert H.adopt_diff(a, Path("/nonexistent")) == ""
    assert H.tree_of("/t1/tools/die_plan") == Path("/t1")


def test_hop_level_calibration_match():
    t = {"outline_um": [1000, 1000], "buses": [], "ft_slots": [],
         "internal_stations": [{"conn": "core:a.x|core:b.y", "from_um": [0, 0], "regs_um": [[250, 0]], "to_um": [600, 0]}]}
    segs = PG.segments(t)
    assert segs == [((0, 0), (250, 0)), ((250, 0), (600, 0))]
    legs = PG.measured_legs({"pairs": [["u_a/q", "u_b/q", 4, 420.0, ["i", "j", [255, 10], [590, 20]], "logic"],
                                       ["u_c/q", "u_d/q", 1, 500.0, ["i", "j", [900, 900], [400, 900]], "logic"]]})
    m = PG.match_hops(segs, legs)
    assert m == [(420.0, 350.0), (500.0, None)]


def test_kit_defines_do_not_count_as_a_plan_loss(tmp_path):
    g = tmp_path / "gen/x__t1"
    g.mkdir(parents=True)
    (g / "config.mk").write_text("export VERILOG_DEFINES = -DSYNTHESIS -DOT_A\n")
    _rows, held = EC.census({"x__t1": mon_type((2, 467), defines=["OT_A"])}, {"x__t1": mon_type((2, 467), defines=["OT_A"])},
                            {"x__t1": str(g)}, {})
    assert held == {}            # prev side read a kit, new side has none: SYNTHESIS / kit-only defines are not "lost"


def test_mutant_selectors_are_not_read_registers():
    import re
    rx = re.compile(EC.REGREAD_RE)
    assert rx.search("OT_S81SL_VP_SRAMREG") and rx.search("OT_S81SL_LEP_RIP1")
    assert not rx.search("OT_S81SL_VP_MUT_SRAMREG")
