"""tests for signoff.py (no docker: parsing, discovery, record checks and the verdict)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff  # noqa: E402

GOOD_SDC = """create_clock -name clk -period 833.0000 [get_ports {ck}]
create_clock -name vclk -period 833.0000
set_clock_latency -source 250.0000 [get_clocks vclk]
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5000
set non_clk_in [all_inputs -no_clocks]
set_input_delay -max 166.6000 -clock vclk $non_clk_in
set_input_delay -min -40.0000 -clock vclk $non_clk_in
set_output_delay -max 166.6000 -clock vclk [all_outputs]
set_output_delay -min 0.0000 -clock vclk [all_outputs]
set_load 2 [all_outputs]
"""
# the pre-4b7b2b3e64 core-kit form: no min output delay (sender hold waived), min input 0
OLD_SDC = GOOD_SDC.replace("set_input_delay -min -40.0000", "set_input_delay -min 0.0000").replace(
    "set_output_delay -min 0.0000 -clock vclk [all_outputs]\n", "").replace(
    "set_output_delay -max 166.6000", "set_output_delay 166.6000")


def session_text(tt_setup=12.0, ss_setup=-150.0, ff_hold=3.0, spread_tt=40.0, slew=0, unconstrained=0, done=True):
    out = {}
    for c, (smax, smin, sp) in dict(ss=(ss_setup, 30.0, 50.0), ff=(150.0, ff_hold, 30.0),
                                    tt=(tt_setup, 10.0, spread_tt)).items():
        L = [f"SO CORNER {c.upper()}", "SO PARASITICS spef", "SO DESIGN blk", "SO CELLS 1000",
             "SO CLOCK_PORTS ck", "SO INPUTS a b", "SO OUTPUTS y", "SO CLOCKS clk vclk", "SO VCLKS vclk",
             "SO PERIOD clk 833", "SO PERIOD vclk 833",
             f"SO SDC_WNS_MAX {smax}", f"SO SDC_WNS_MIN {smin + 5}", "SO SDC_TNS_MAX 0", "SO SDC_TNS_MIN 0",
             "SO SDC_NVIOL_MAX 0", "SO SDC_NVIOL_MIN 0", "SO OVERLAY applied vclk in_min -40 out_min 0",
             f"SO STD_WNS_MAX {smax}", f"SO STD_WNS_MIN {smin}", "SO STD_TNS_MAX 0",
             f"SO STD_TNS_MIN {min(0, smin)}", "SO STD_NVIOL_MAX 0", f"SO STD_NVIOL_MIN {1 if smin < 0 else 0}",
             f"SO SLEW_VIOL {slew}", "SO CAP_VIOL 0", "SO FANOUT_MAX 12 n1", "SO FANOUT_VIOL 0",
             "SO_PATH_BEGIN CHECK_SETUP",
             f"Warning: There are {unconstrained} unconstrained endpoints." if unconstrained else "",
             "SO_PATH_END",
             "SO_CK 1 250.0 clk", f"SO_CK 1 {250.0 + sp} clk", "SO_CK 0 260.0 clk", "SO CK_ERRORS 0",
             "SO OCV5_WNS_MAX -3", "SO OCV5_WNS_MIN -1"]
        if done:
            L.append("SO DONE 1")
        out[c] = "\n".join(L)
    return out


def record(**kw):
    rec = dict(name="blk", corners={})
    for c, t in session_text(**{k: v for k, v in kw.items() if k in ("tt_setup", "ss_setup", "ff_hold", "spread_tt", "slew",
                                                                         "unconstrained", "done")}).items():
        r = signoff.corner_result(signoff.parse_session(t))
        r.update(corner=c, macro_missing=[])
        rec["corners"][c] = r
    rec["sdc_lint"] = dict(verdict=kw.get("sdc", "PASS"))
    rec["face_guard"] = dict(verdict=kw.get("fg", "PASS"))
    rec["route"] = dict(drc=kw.get("drc", 0), antenna_nets=kw.get("ant", 0), drc_source="t", antenna_source="t")
    return rec


def test_parse_session_values():
    r = signoff.corner_result(signoff.parse_session(session_text()["tt"]))
    assert r["done"] and r["sdc_wns_max"] == 12.0 and r["std_wns_min"] == 10.0
    assert r["insertion_pinflops"]["spread"] == 40.0 and r["insertion_pinflops"]["n"] == 2
    assert r["insertion_all"]["n"] == 3
    assert r["inputs"] == ["a", "b"] and r["clock_ports"] == ["ck"] and r["vclks"] == ["vclk"]
    assert r["periods"] == {"clk": 833.0, "vclk": 833.0}


def test_signed_when_everything_passes():
    rec = signoff.evaluate(record())
    assert rec["verdict"] == "SIGNED", rec["reasons"]
    # SS is information only (owner 2026-10-24): a deeply negative SS setup never blocks
    assert rec["checks"]["ss"]["verdict"] == "REPORT" and rec["checks"]["ss"]["setup_wns_ps"] == -150.0


def test_tt_setup_fail():
    rec = signoff.evaluate(record(tt_setup=-0.5))
    assert rec["verdict"] == "NOT SIGNED" and any(r.startswith("setup_tt: FAIL") for r in rec["reasons"])


def test_ss_drv_is_information_only():
    rec = record()
    rec["corners"]["ss"]["slew_viol"] = 40.0
    assert signoff.evaluate(rec)["verdict"] == "SIGNED"


def test_default_corners_are_tt_ff():
    assert signoff.CORNERS == ("tt", "ff") and "ss" not in signoff.BLOCKING


def test_ff_hold_uses_standard_overlay():
    rec = signoff.evaluate(record(ff_hold=-2.0))
    h = rec["checks"]["hold_ff"]
    assert h["verdict"] == "FAIL" and h["wns_ps"] == -2.0 and h["sdc_wns_ps"] == 3.0


def test_spread_over_80_fails_at_tt():
    rec = signoff.evaluate(record(spread_tt=85.4))
    assert rec["checks"]["clock"]["verdict"] == "FAIL"
    assert "TT pin-flop spread 85.4 ps > 80" in rec["checks"]["clock"]["problems"][0]


def test_insertion_target():
    rec = signoff.evaluate(record(), insertion_target=250.0)
    assert rec["checks"]["clock"]["verdict"] == "PASS"
    rec = signoff.evaluate(record(), insertion_target=150.0)
    assert rec["checks"]["clock"]["verdict"] == "FAIL"


def test_drv_unconstrained_drc_antenna():
    assert signoff.evaluate(record(slew=3))["checks"]["drv"]["verdict"] == "FAIL"
    assert signoff.evaluate(record(unconstrained=7))["checks"]["unconstrained"]["verdict"] == "FAIL"
    assert signoff.evaluate(record(drc=1))["checks"]["drc"]["verdict"] == "FAIL"
    assert signoff.evaluate(record(ant=2))["checks"]["antenna"]["verdict"] == "FAIL"
    assert signoff.evaluate(record(drc=None))["checks"]["drc"]["verdict"] == "NOT RUN"


def test_not_run_is_not_signed():
    rec = signoff.evaluate(record(done=False))
    assert rec["verdict"] == "NOT SIGNED" and "setup_tt: NOT RUN" in rec["reasons"]
    rec = signoff.evaluate(record(fg="NOT RUN"))
    assert rec["verdict"] == "NOT SIGNED"


def test_check_setup_counts():
    t = ("Warning: There are 12 unconstrained endpoints.\nWarning: There is 1 register/latch pin with no clock.\n"
         "Warning: There are 2 combinational loops in the design.")
    c = signoff.check_setup_counts(t)
    assert c["unconstrained"] == 12 and c["unclocked"] == 1 and c["loops"] == 2


def test_session_tcl_spef_vs_rcx_and_no_verdict_derate():
    t = signoff.session_tcl("ss", ["/ml0/m_ss.lib"], spef="/x/6_final.spef")
    assert "read_spef /base/6_final.spef" in t and "read_liberty /ml0/m_ss.lib" in t and "_RVT_SS_" in t
    # the derate comes after the verdict numbers and is removed before the clock measurement
    assert t.index("so_timing STD") < t.index("set_timing_derate -late 1.05") < t.index("unset_timing_derate")
    t = signoff.session_tcl("ff", [], spef=None)
    assert "extract_parasitics -ext_model_file" in t and "rcx_patterns.rules" in t


def _kit(tmp, sdc_text):
    kit = tmp / "kit"
    base = kit / "run" / "results" / "asap7" / "dp_x" / "base"
    base.mkdir(parents=True)
    for n in ("6_final.odb", "6_final.spef", "6_final.sdc", "1_synth.v"):
        (base / n).write_text("x")
    (kit / "constraint.sdc").write_text(sdc_text)
    (kit / "config.mk").write_text("export ADDITIONAL_LIBS = /work/views/m/m_tt.lib\n")
    (kit / "views" / "m").mkdir(parents=True)
    for c in ("tt", "ss"):
        (kit / "views" / "m" / f"m_{c}.lib").write_text("x")
    lg = kit / "run" / "logs" / "asap7" / "dp_x" / "base"
    lg.mkdir(parents=True)
    (lg / "5_2_route.json").write_text(json.dumps({"detailedroute__route__drc_errors": 0,
                                                   "detailedroute__antenna__violating__nets": 3}))
    return kit, base


def test_discover_and_route_counts(tmp_path):
    kit, base = _kit(tmp_path, GOOD_SDC)
    assert signoff.find_base(kit / "run") == base
    d = signoff.discover(base)
    assert d["kit"] == str(kit) and d["sdc_source"] == "kit" and d["spef"] and d["synth"].endswith("1_synth.v")
    rc = signoff.route_counts(d)
    assert rc["drc"] == 0 and rc["antenna_nets"] == 3


def test_macro_libs_per_corner(tmp_path):
    kit, _ = _kit(tmp_path, GOOD_SDC)
    libs, miss = signoff.macro_libs(str(kit), "ss")
    assert libs and libs[0].endswith("m_ss.lib") and not miss
    libs, miss = signoff.macro_libs(str(kit), "ff")
    assert not libs and miss == ["m_tt.lib (ff)"]


def test_sdc_lint_derived_mode(tmp_path):
    ports = dict(clock_ports=["ck"], inputs=["a"], outputs=["y"])
    kit, base = _kit(tmp_path, GOOD_SDC)
    r = signoff.run_sdc_lint(signoff.discover(base), ports)
    assert r["verdict"] == "PASS", r["errors"]
    kit2, base2 = _kit(tmp_path / "old", OLD_SDC)
    r = signoff.run_sdc_lint(signoff.discover(base2), ports)
    assert r["verdict"] == "FAIL"
    assert any("min output delay" in e for e in r["errors"]) and any("min input delay" in e for e in r["errors"])


def test_macro_lib_missing_blocks():
    rec = record()
    rec["corners"]["ff"]["macro_missing"] = ["m_tt.lib (ff)"]
    rec = signoff.evaluate(rec)
    assert rec["verdict"] == "NOT SIGNED" and rec["checks"]["macro_libs"]["verdict"] == "FAIL"


def test_paper_screen_tt_rule():
    import signoff_inventory
    import signoff_summary
    v = dict(ss_ps=17.77, setup_corner="tt", ss_sensitivity_ps=-295.16)
    assert signoff_inventory.tt_setup(v) == 17.77           # metrics.ss_ps holds the TT slack of an option-B verdict
    assert signoff_inventory.ss_info(v) == -295.16
    assert signoff_inventory.tt_setup(dict(ss_ps=5.0, setup_corner="ss")) is None
    rec = dict(cl_status="CLOSED", cl_tt_setup_ps=17.77, cl_ss_info_ps=-295.16, cl_setup_corner="tt", cl_ff_ps=6.59,
               cl_drc=0, spread_tt_ps=67.5, spread_ff_ps=59.6)
    assert signoff_summary.paper_screen(rec)["verdict"] == "PASS"     # SS never gates
    rec.update(spread_tt_ps=85.4)
    assert signoff_summary.paper_screen(rec)["verdict"] == "FAIL"
    rec.update(spread_tt_ps=50.0, cl_tt_setup_ps=-1.0)
    p = signoff_summary.paper_screen(rec)
    assert p["verdict"] == "FAIL" and p["problems"][0] == "recorded TT setup -1.00 ps"
    rec.update(cl_tt_setup_ps=None, cl_setup_corner="ss")
    assert signoff_summary.paper_screen(rec)["verdict"] == "INCOMPLETE"


def test_route_goal_kit_uses_5_route_with_rcx(tmp_path):
    base = tmp_path / "run" / "results" / "asap7" / "dp_y" / "base"
    base.mkdir(parents=True)
    (base / "5_route.odb").write_text("x")
    (base / "6_final.spef").write_text("stale")          # a SPEF without its 6_final.odb is not used
    assert signoff.find_base(tmp_path / "run") == base
    d = signoff.discover(base, sdc=str(base / "6_final.spef"))
    assert d["odb"].endswith("5_route.odb") and d["spef"] is None
    t = signoff.session_tcl("tt", [], d["spef"], odb="5_route.odb")
    assert "read_db /base/5_route.odb" in t and "extract_parasitics" in t


def test_gen_phys_kit_runs_signoff_last():
    import gen_phys
    k = gen_phys.RUN_KIT
    assert "signoff.py\" run --run-dir \"$K/run\"" in k
    assert k.index("generate_abstract") < k.index("signoff.py\" run") < k.rindex("exit $rc")


def test_corner_scoped_macro_libs(tmp_path):
    kit = tmp_path / "kit"; (kit / "macros").mkdir(parents=True)
    (kit / "macros/child_tt.lib").write_text("library(child) {}")
    (kit / "macros/child_ff.lib").write_text("library(child) {}")
    (kit / "config.mk").write_text("export ADDITIONAL_LIBS =\n"
        "export TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/child_tt.lib\n"
        "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/macros/child_ff.lib\n")
    for c in ("tt", "ff"):
        libs, missing = signoff.macro_libs(kit, c)
        assert libs == [str(kit / f"macros/child_{c}.lib")] and missing == []
    (kit / "macros/child_ff.lib").unlink()
    assert signoff.macro_libs(kit, "ff")[1]  # missing FF remains blocking


def test_corner_scoped_generic_lib_name(tmp_path):
    (tmp_path / "ff").mkdir(); (tmp_path / "ff/core.lib").write_text("library(c) {}")
    (tmp_path / "config.mk").write_text("export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /work/ff/core.lib\n")
    assert signoff.macro_libs(tmp_path, "ff") == ([str(tmp_path / "ff/core.lib")], [])
