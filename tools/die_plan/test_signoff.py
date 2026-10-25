"""tests for signoff.py (no docker: parsing, discovery, record checks and the verdict)."""
import json
import sys
import pytest
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


def session_text(tt_setup=12.0, ss_setup=-150.0, ff_hold=3.0, spread_tt=40.0, slew=0, unconstrained=0, done=True,
                 pair_setup=30.0, pair_hold=25.0):
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
             "SO OCV5_WNS_MAX -3", "SO OCV5_WNS_MIN -1",
             "SO PAIR_COUNTS regs 3 no_clock_arrival 0 data_pins 3 pairs 2 inter_clock 0", "SO PAIR_METHOD tag",
             f"SO PAIR_max n 2 worst {pair_setup} bounded 0 signed {-pair_setup} launch a capture b crpr 4.0 p99_raw 31 "
             "searched 1 nopath 0 verify 0.010",
             f"SO PAIR_min n 2 worst {pair_hold} bounded 0 signed {pair_hold} launch a capture b crpr 4.0 p99_raw 26 "
             "searched 1 nopath 0 verify 0.020", "SO PAIR_SECONDS 1", "SO PAIR_DONE 1"]
        if done:
            L.append("SO DONE 1")
        out[c] = "\n".join(L)
    return out


def record(**kw):
    rec = dict(name="blk", corners={})
    for c, t in session_text(**{k: v for k, v in kw.items() if k in ("tt_setup", "ss_setup", "ff_hold", "spread_tt", "slew",
                                                                         "unconstrained", "done", "pair_setup", "pair_hold")}).items():
        r = signoff.corner_result(signoff.parse_session(t))
        r.update(corner=c, macro_missing=[])
        rec["corners"][c] = r
    rec["sdc_lint"] = dict(verdict=kw.get("sdc", "PASS"))
    rec["face_guard"] = dict(verdict=kw.get("fg", "PASS"))
    rec["route"] = dict(drc=kw.get("drc", 0), antenna_nets=kw.get("ant", 0), drc_source="t", antenna_source="t")
    # COORD 10-25: a per-corner FF insertion reference is required (ff_ref_missing otherwise)
    # (default: a bound at the session's own pin-flop means, so the clock insertion check is neutral here)
    m = {c: (rec["corners"].get(c, {}).get("insertion_pinflops") or {}).get("mean") for c in ("tt", "ff")}
    rec["policy"] = kw.get("policy", dict(ff_vclk="sdc", insertion_bound=dict(
        tt=m["tt"] if m["tt"] is not None else 250.0, ff=(m["ff"] if m["ff"] is not None else 202.5) - 1.0, tol=40.0)))
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


def test_ff_hold_missing_overlay_is_not_run():
    for overlay in (None, "", "skipped vclks 0", "skipped vclks 2"):
        for slack in (12.0, -2.0):
            rec = record(ff_hold=slack)
            rec["corners"]["ff"]["overlay"] = overlay
            rec = signoff.evaluate(rec)
            h = rec["checks"]["hold_ff"]
            assert h["verdict"] == "NOT RUN"
            assert h["wns_ps"] == slack  # retain the diagnostic raw-SDC result
            assert "overlay was not applied" in h["reason"]
            assert rec["verdict"] == "NOT SIGNED"


def test_spread_over_80_is_information_only():
    rec = signoff.evaluate(record(spread_tt=85.4))
    assert rec["checks"]["clock"]["verdict"] == "PASS"
    assert rec["checks"]["clock"]["spread_info_only"]


def test_related_pair_skew_missing_or_over_limit_blocks():
    rec = signoff.evaluate(record(pair_setup=85.4))
    assert rec["checks"]["clock"]["verdict"] == "FAIL"
    assert any("TT setup related pair skew 85.4 ps > 80 (a -> b)" in p for p in rec["checks"]["clock"]["problems"])
    rec = record()
    del rec["corners"]["ff"]["pair_skew"]
    assert signoff.evaluate(rec)["checks"]["clock"]["verdict"] == "FAIL"
    rec = record()
    rec["corners"]["tt"]["pair_skew"]["done"] = False
    assert signoff.evaluate(rec)["checks"]["clock"]["verdict"] == "FAIL"


def test_pair_skew_parsed_from_session():
    ps = record()["corners"]["ff"]["pair_skew"]
    assert ps["done"] and ps["counts"]["pairs"] == 2
    h = ps["checks"]["min"]
    assert h["worst_abs_ps"] == 25.0 and h["worst_signed_ps"] == 25.0 and h["worst_crpr_ps"] == 4.0
    assert h["worst_launch"] == "a" and h["worst_capture"] == "b" and not h["bounded"]
    assert ps["checks"]["max"]["worst_signed_ps"] == -30.0


def test_pair_skew_at_limit_passes_and_hold_side_fails_at_ff():
    assert signoff.evaluate(record(pair_hold=80.0))["checks"]["clock"]["verdict"] == "PASS"
    rec = signoff.evaluate(record(pair_hold=80.5))
    assert any(p.startswith("FF hold related pair skew 80.5") for p in rec["checks"]["clock"]["problems"])


def test_pair_skew_verify_mismatch_blocks():
    rec = record()
    rec["corners"]["tt"]["pair_skew"]["checks"]["min"]["verify_ps"] = 3.0
    rec = signoff.evaluate(rec)
    assert rec["checks"]["clock"]["verdict"] == "FAIL"
    assert any("cross-check" in p for p in rec["checks"]["clock"]["problems"])


def test_session_measures_pairs_before_source_latency_zeroing():
    t = signoff.session_tcl("tt", [], "/base/6_final.spef")
    assert t.index("ot_ps_measure") < t.index("set_clock_latency -source 0")
    assert t.index("unset_timing_derate") < t.index("ot_ps_measure")
    assert t.count("read_sdc /sdc/golden.sdc") == 1
    assert "@PAIR" not in t and "proc ot_ps_measure" in t


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


def test_hard_core_latency_contract(tmp_path):
    """COORD 10-24: a hard-core kit (typed core.json clock_contract) publishes its insertion; others keep the target."""
    import json as _j
    import signoff as _S
    kit = tmp_path / "kit"
    kit.mkdir()
    assert _S.hard_core_latency_contract(dict(kit=str(kit))) is None
    (kit / "boundary_guard_context.json").write_text(_j.dumps(dict(
        schema="opentallas.core_boundary_guard_context.v1", source_core_json="core.json", clock_ports=["ck"],
        unused_clock_ports=[], reset_ports=[], data_pin_exemptions=[])))
    (kit / "core.json").write_text(_j.dumps(dict(boundary_role={"ck": "clk"})))
    assert _S.hard_core_latency_contract(dict(kit=str(kit))) is None
    (kit / "core.json").write_text(_j.dumps(dict(boundary_role={"ck": "clk"}, clock_contract=dict(
        kind="hard_core_latency", parent="tap_balance early tap"))))
    assert _S.hard_core_latency_contract(dict(kit=str(kit)))["kind"] == "hard_core_latency"
    (kit / "core.json").write_text(_j.dumps(dict(clock_contract=dict(kind="anything_else"))))
    assert _S.hard_core_latency_contract(dict(kit=str(kit))) is None


def test_summary_line_shows_pair_skew_and_spread_info():
    line = signoff.summary_line(signoff.evaluate(record(pair_setup=41.0, pair_hold=22.0)))
    assert "pair skew TT/FF 41.0/41.0" in line and "spread info" in line
    rec = record()
    del rec["corners"]["tt"]["pair_skew"]
    assert "pair skew TT/FF nan/30.0" in signoff.summary_line(signoff.evaluate(rec))


def test_pair_skew_registers_without_clock_arrival_block():
    rec = record()
    assert rec["corners"]["tt"]["pair_skew"]["method"] == "tag"
    rec["corners"]["ff"]["pair_skew"]["counts"]["no_clock_arrival"] = 2
    rec = signoff.evaluate(rec)
    assert rec["checks"]["clock"]["verdict"] == "FAIL"
    assert any("FF: 2 registers without a unique propagated clock arrival" in p for p in rec["checks"]["clock"]["problems"])


def test_ff_vclk_optin_keeps_raw_and_shared_io_contract():
    default = signoff.session_tcl('ff', [], True)
    enabled = signoff.session_tcl('ff', [], True, ff_vclk='pin-flop-mean')
    tt = signoff.session_tcl('tt', [], True, ff_vclk='pin-flop-mean')
    assert 'so FF_VCLK applied' not in default
    assert 'so FF_VCLK applied' not in tt
    assert enabled.index('so_timing SDC') < enabled.index('so FF_VCLK applied') < enabled.index('so_timing STD')
    assert 'set_clock_latency -source $so_ff_mean [lindex $so_vclk 0]' in enabled
    assert 'set_input_delay -min [expr {-40}]' in enabled
    assert 'set_output_delay -min 0' in enabled
    assert 'set_clock_uncertainty' not in signoff.FF_VCLK_TCL
    assert 'set_input_delay' not in signoff.FF_VCLK_TCL
    assert 'set_output_delay' not in signoff.FF_VCLK_TCL
    assert '$so_ff_bad == 0' in enabled
    assert 'set so_reference_ok 0' in enabled


def test_ff_vclk_missing_measurement_blocks_optimistic_mutant():
    # A checker mutant could retain a positive STD slack after dropping the
    # measurement.  It must remain NOT RUN even with every other gate clean.
    for reference in (None, 'unavailable mode pin_flop_mean samples 0 missing 1'):
        rec = record()
        rec['policy'] = {'ff_vclk': 'pin-flop-mean'}
        rec['corners']['ff']['ff_vclk_reference'] = reference
        signoff.evaluate(rec)
        assert rec['checks']['hold_ff']['verdict'] == 'NOT RUN'
        assert rec['verdict'] == 'NOT SIGNED'
    rec = record()
    rec['policy'] = {'ff_vclk': 'pin-flop-mean'}
    rec['corners']['ff']['ff_vclk_reference'] = 'applied mode pin_flop_mean clock vclk latency_ps 193.28 samples 457 missing 0'
    signoff.evaluate(rec)
    assert rec['checks']['hold_ff']['verdict'] == 'PASS'


def test_ff_vclk_cli_requires_measured_contract():
    import pytest
    with pytest.raises(SystemExit) as e:
        signoff.main(['run', '--base', '/unused', '--out', '/unused', '--ff-vclk', 'pin-flop-mean'])
    assert e.value.code == 2


def test_ff_ref_missing_without_ff_reference():
    """COORD 10-25 (HBM argmax la1/s2f2): ff_vclk sdc without a per-corner FF bound never signs FF hold off."""
    rec = signoff.evaluate(record(policy=dict(ff_vclk="sdc")))
    h = rec["checks"]["hold_ff"]
    assert h["verdict"] == "FAIL" and h["reason"].startswith("FAIL_SIGNOFF ff_ref_missing")
    assert rec["verdict"] == "NOT SIGNED" and any("ff_ref_missing" in r for r in rec["reasons"])


def test_ff_ref_equal_to_tt_with_far_ff_mean_fails():
    rec = record(policy=dict(ff_vclk="sdc", insertion_bound=dict(tt=250.0, ff=250.0, tol=40.0)))
    mean = rec["corners"]["ff"]["insertion_pinflops"]["mean"]
    rec["policy"]["insertion_bound"].update(tt=mean + 10.5, ff=mean + 10.5)
    h = signoff.evaluate(rec)["checks"]["hold_ff"]
    assert h["verdict"] == "FAIL" and "equals the TT value" in h["reason"]
    rec = record(policy=dict(ff_vclk="sdc", insertion_bound=dict(tt=mean + 9.5, ff=mean + 9.5, tol=40.0)))
    assert signoff.evaluate(rec)["checks"]["hold_ff"]["verdict"] == "PASS"


def test_bound_ff_core_contract():
    """FLOW-FIX 10-25: a hard-core kit with a declared FF insertion times FF hold against it (bound-ff), no rebind."""
    rec = record(policy=dict(ff_vclk="bound-ff", ff_vclk_bound_ps=198.4))
    rec["corners"]["ff"]["ff_vclk_reference"] = "applied mode bound_ff clock vclk latency_ps 198.400000"
    h = signoff.evaluate(rec)["checks"]["hold_ff"]
    assert h["verdict"] == "PASS" and not h.get("reason")
    rec = record(policy=dict(ff_vclk="bound-ff"))           # declared value missing -> fail closed
    rec["corners"]["ff"]["ff_vclk_reference"] = "applied mode bound_ff clock vclk latency_ps 198.400000"
    assert signoff.evaluate(rec)["checks"]["hold_ff"]["reason"].startswith("FAIL_SIGNOFF ff_ref_missing")
    rec = record(policy=dict(ff_vclk="bound-ff", ff_vclk_bound_ps=198.4))   # bound not applied in the session
    rec["corners"]["ff"]["ff_vclk_reference"] = "unavailable mode bound_ff vclks 2"
    assert signoff.evaluate(rec)["checks"]["hold_ff"]["verdict"] == "NOT RUN"


def test_bound_ff_session_tcl():
    t = signoff.session_tcl("ff", [], None, ff_vclk="bound-ff", ff_bound_ps=198.4)
    assert "set_clock_latency -source 198.400000" in t and "mode bound_ff" in t
    assert "mode bound_ff" not in signoff.session_tcl("tt", [], None, ff_vclk="bound-ff", ff_bound_ps=198.4)
    with pytest.raises(ValueError):
        signoff.session_tcl("ff", [], None, ff_vclk="bound-ff")
