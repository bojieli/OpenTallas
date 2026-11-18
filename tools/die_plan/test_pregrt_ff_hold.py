"""R-CLOCK HOLD BUILD (HOLD-TAP-1 11-13; was HEAD-TILE-PREGRT-HOLD DH59-TILE 11-03) + clock.tap_core_etap plan form:
the placement-basis FF hold build is OPT-IN (plan clock.pregrt_ff_hold true; COORD 11-13 07:2x default-preserving)."""
import json
import re
import shutil
import subprocess
from pathlib import Path
import pytest
import gen_phys
import pregrt_ff_hold as PG
import schema

HERE = Path(__file__).resolve().parent


def _kit(tmp_path, clock):
    (tmp_path / "hold_gate.tcl").write_text((HERE / "hold_gate.tcl").read_text())
    return PG.install({"clock": clock}, tmp_path)


def test_opt_out_writes_nothing(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text("x\n" + PG.MARK + "y\n")
    assert PG.install({"clock": {"pregrt_ff_hold": False}}, tmp_path) is False
    assert not (tmp_path / "pregrt_ff_hold.tcl").exists()
    assert PG.config_lines({"clock": {"pregrt_ff_hold": False}}) == []


def test_default_is_off_and_opt_in(tmp_path):
    # COORD 11-13 07:2x: default-preserving; a kit generated from a plan without the key is byte-identical to before
    assert not PG.enabled({}) and not PG.enabled({"clock": {}}) and not PG.enabled({"clock": {"pregrt_ff_hold": False}})
    assert PG.enabled({"clock": {"pregrt_ff_hold": True}})
    assert _kit(tmp_path, {}) is False and not (tmp_path / "pregrt_ff_hold.tcl").exists()
    assert PG.config_lines({}) == [] and PG.config_lines({"clock": {"pregrt_hold_guard_ps": 40}}) == []
    on = {"pregrt_ff_hold": True}
    assert PG.config_lines({"clock": on}) == [PG.CONFIG, "export OT_PREGRT_HOLD_GUARD = 45"]
    assert PG.config_lines({"clock": dict(on, pregrt_hold_guard_ps=40)})[1] == "export OT_PREGRT_HOLD_GUARD = 40"
    with pytest.raises(ValueError):
        PG.config_lines({"clock": dict(on, pregrt_hold_guard_ps=150)})


def test_on_keeps_the_gate_context_and_drops_the_verdict(tmp_path):
    assert _kit(tmp_path, {"pregrt_ff_hold": True}) is True
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "ot_io_hold_apply" in t and "OT_FWD_RING_INPUTS" in t       # same boundary contract as the gate
    assert "OT_HOLD_GATE FAIL" not in t and "OT_HOLD_STOP_PS" not in t  # no verdict: only sign-off blocks
    assert "repair_timing -hold" in t and "detailed_placement" in t and "check_placement" in t
    assert t.rstrip().endswith("}")
    # the database is replaced through a temporary file, and only on the success branch
    assert t.count("write_db $::env(ODB).pg_tmp") == 1 and "file rename -force $::env(ODB).pg_tmp $::env(ODB)" in t
    assert t.index("OT_PREGRT_FF_HOLD FALLBACK") < t.index("write_db $::env(ODB).pg_tmp")


def test_two_scene_read_replaces_the_single_read_once(tmp_path):
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    # TT setup scene + FF hold scene when the runner passes TLIBS; the FF-only read is kept for an older runner
    assert "define_scene TC -mode tt -liberty $::env(TLIBS)" in t and "define_scene BC -mode ff -liberty $::env(PLIBS)" in t
    assert t.index("foreach l [concat $::env(TLIBS) $::env(PLIBS)] { read_liberty $l }") < t.index("define_scene TC")
    assert "set_false_path -hold -from [all_clocks]" in t and "set_false_path -setup -from [all_clocks]" in t
    # the overlay of the gate (vclk FF bind, input / output min delays) runs after the scene read, in mode ff
    assert t.index("set_mode ff\n  set_propagated_clock [all_clocks]\n  set_false_path -setup") < t.index("ot_vclk_bind ff")
    assert "} else {\n  foreach l $::env(PLIBS) { read_liberty $l }\n  read_db $::env(ODB)\n  read_sdc $::env(SDC)\n" in t
    assert t.count("read_db $::env(ODB)") == 2 and t.count(PG.READ) == 0


def test_route_guard_is_cross_tap_only(tmp_path):
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "foreach pg_tag {all rr xt}" in t and "set pg_dg [expr {$pg_guard - $pg_pm}]" in t
    # the guard pass: port hold excepted, every tap port early latency widened, repair, then both restored
    a = t.index("set_false_path -hold -from $pg_in", t.index('if {$pg_tag eq "xt"} {'))     # the xt pass (the rr pass has its own, HOLD-MARGIN-FAMILY)
    w = t.index("set_clock_latency -source -early -clock $pg_ck [expr {$pg_e - $pg_dg}] [get_ports $pg_p]")
    r = t.index("repair_timing -hold -hold_margin $pg_mrg -max_buffer_percent 100")
    z = t.index("set_clock_latency -source -early -clock $pg_ck $pg_e [get_ports $pg_p]")
    b = t.rindex("unset_path_exceptions -hold -from $pg_in")
    assert a < w < r < z < b
    assert "set_false_path -hold -to $pg_out" in t and "unset_path_exceptions -hold -to $pg_out" in t
    assert "OT_PREGRT_HOLD_PORT_MARGIN" in t and "OT_PREGRT_HOLD_GUARD" in t
    assert "cross-tap guard not applied" in t          # a kit without tap window lines keeps the base margin only


def test_tap_window_lines_are_the_generator_form(tmp_path):
    """the tcl reads the window ports from the lines gen_phys.tap_window_tcl writes (same regular expression)"""
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    pat = r"^set_clock_latency -source -early -clock (\S+) (-?[0-9.]+) \[get_ports \{?([^\}\]]+)\}?\]\s*$"
    assert "regexp {" + pat + "} $pg_l" in t
    py = re.compile(pat)
    m = py.match("set_clock_latency -source -early -clock clk -40.0000 [get_ports {clk clk_t1 clk_t2}]")
    assert m and m.group(1) == "clk" and float(m.group(2)) == -40.0 and m.group(3).split() == ["clk", "clk_t1", "clk_t2"]
    assert py.match("set_clock_latency -source -early -clock fclk_in_cland_dn_0 -50.0000 [get_ports {fclk_in_cland_dn_0}]")
    assert not py.match("set_clock_latency -source -late -clock clk 0.0000 [get_ports {clk clk_t1}]")
    assert not py.match("set_clock_latency -source 450.0000 [get_clocks vclk]")
    # the generator still writes that form
    src = (HERE / "gen_phys.py").read_text()
    assert 'f"set_clock_latency -source -early -clock {ck} {t_lib(-v) + 0.0:.4f} "' in src
    assert 'f"set_clock_latency -source -early -clock {ck} {t_lib(e):.4f} [get_ports' in src


def test_clock_network_is_firm_during_the_build_and_released(tmp_path):
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    lock, rep, rel = t.index("setPlacementStatus FIRM"), t.index("repair_timing -hold"), t.index("foreach pg_i $pg_lock { $pg_i setPlacementStatus PLACED }")
    assert lock < rep < t.index("detailed_placement") < rel < t.index("write_db")


def test_fail_safe_conditions(tmp_path):
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "TT setup loss" in t and "no hold gain" in t and "tool error" in t
    assert "proc pg_verdict" in t and "[pg_verdict $pg_w0 $pg_w1 $pg_n0 $pg_s0 $pg_s1 [sta::endpoint_violation_count min] $pg_tn0 [pg_tns]]" in t
    # QC-MCLK lever 3: the pass loop goes on while a pass still removes >= 5 % of the violating endpoints
    assert "[sta::endpoint_violation_count min] > 0.95 * $pg_np" in t


def _verdict(tmp_path, args, env=None):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    m = re.search(r"proc pg_verdict .*?\n\}\n", t, re.S)
    assert m
    chk = tmp_path / "v.tcl"
    chk.write_text(m.group(0) + "puts [pg_verdict " + " ".join(str(a) for a in args) + "]\n")
    import os
    r = subprocess.run([tclsh, str(chk)], capture_output=True, text=True, env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# args: w0 w1 n0 s0 s1.  HOLD-GRT-1: the measured FALLBACK cases of the QC hold-stall types.
@pytest.mark.parametrize("args,ok", [
    ((-113.7, 4.9, 15238, -8.12, -9.62), True),        # slw_stm_v1: -1.5 ps, above the -42 gate
    ((-108.1, 4.8, 4768, -515.45, -518.27), True),     # slw_hc0: 2.8 ps below a floor already far under the gate
    ((-107.9, 4.9, 2873, 12.79, 0.81), True),          # positive slack spent, stays above 0
    ((-100.0, 4.9, 100, 30.0, -30.0), True),           # spent below 0 but above the gate
    ((-100.0, 4.9, 100, -20.0, -80.0), False),         # 60 ps loss through the gate: still rejected
    ((-84.15, -84.15, 515, -562.4, -562.4), False),    # no hold gain
    ((0.0, 0.0, 0, -50.0, -50.0), True),               # no debt, nothing changed
    # QC-MCLK lever 3 (args + n1 t0 t1): cbn_q01 kept its worst latch endpoint, 21,467 -> 2,707 endpoints, TNS -1.26 us -> -78 ns
    ((-211.66, -211.66, 21467, -461.86, -461.86, 2707, -1260000.0, -78000.0), True),
    ((-211.66, -211.66, 21467, -461.86, -461.86, 21467, -1260000.0, -1260000.0), False),   # nothing closed
    ((-211.66, -211.66, 21467, -461.86, -461.86, 2707, -1260000.0, -1300000.0), False),    # fewer endpoints, worse TNS
    ((-211.66, -211.66, 21467, -20.0, -80.0, 2707, -1260000.0, -78000.0), False),           # setup gate still rejects
])
def test_accept_verdict(tmp_path, args, ok):
    v = _verdict(tmp_path, args)
    assert (v == "") is ok, v


def test_accept_verdict_env_gate_and_tol(tmp_path):
    assert _verdict(tmp_path, (-100.0, 4.9, 100, -515.0, -525.0)).startswith("TT setup loss")
    assert _verdict(tmp_path, (-100.0, 4.9, 100, -515.0, -525.0), {"OT_PREGRT_SETUP_TOL": "15"}) == ""
    assert _verdict(tmp_path, (-100.0, 4.9, 100, -10.0, -30.0), {"OT_PREGRT_SETUP_GATE": "-10"}).startswith("TT setup loss")


def test_class_report_and_open_list(tmp_path):
    _kit(tmp_path, {"pregrt_ff_hold": True})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    for c in ("port_in", "same_tap", "cross_tap", "port_out"):
        assert c in t
    assert "pg_classes before" in t and "pregrt_ff_hold_open.tsv" in t


def test_tcl_parses(tmp_path):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    _kit(tmp_path, {"pregrt_ff_hold": True})
    chk = tmp_path / "chk.tcl"
    chk.write_text('set f [open [lindex $argv 0]]; set t [read $f]; close $f\n'
                   'if {![info complete $t]} { puts INCOMPLETE; exit 1 }\nputs OK\n')
    r = subprocess.run([tclsh, str(chk), str(tmp_path / "pregrt_ff_hold.tcl")], capture_output=True, text=True)
    assert r.stdout.strip() == "OK", r.stdout + r.stderr


def test_marker_missing_fails_closed(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text("no marker\n")
    with pytest.raises(ValueError):
        PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path)


def test_changed_gate_read_fails_closed(tmp_path):
    (tmp_path / "hold_gate.tcl").write_text("read_db $::env(ODB)\n" + PG.MARK + "y\n")
    with pytest.raises(ValueError):
        PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path)


def test_run_kit_step_is_guarded_advisory_and_before_grt():
    rk = gen_phys.RUN_KIT
    assert rk.count("grep -q '^export OT_PREGRT_FF_HOLD = 1' /work/config.mk") == 1
    assert rk.index("/work/hold_gate.log") < rk.index("/work/pregrt_ff_hold.tcl") < rk.index("OT_VCLK_CORNER=ff")
    step = rk[rk.index("grep -q '^export OT_PREGRT_FF_HOLD = 1'"):rk.index("HM=; if [")]
    assert "print-TC_LIB_FILES" in step and "TLIBS=" in step and "OT_PREGRT_HOLD_GUARD=" in step
    # a failed build never stops the kit: no FAIL_POSTCTS, rc stays 0, the temporary database is removed
    assert "FAIL_POSTCTS" not in step and "rc=6" not in step and "pgrc=" in step
    assert "OT_PREGRT_FF_HOLD FALLBACK step rc" in step and '.pg_tmp' in step
    # COORD 11-13 07:2x: both fallbacks (tool rc, the build's own guard) print one classified line autopilot records
    assert step.count("PREGRT_HOLD_FALLBACK tool rc") == 1 and step.count("PREGRT_HOLD_FALLBACK guard") == 1


def test_schema_keys():
    ck = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["tap_core_etap"] == {"type": "boolean"} and ck["pregrt_ff_hold"] == {"type": "boolean"}
    assert ck["pregrt_hold_guard_ps"] == {"type": "number", "minimum": 0, "maximum": 100}
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert (on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
            ["pregrt_hold_guard_ps"]) == ck["pregrt_hold_guard_ps"]


def test_classification_uses_launch_clock_net_not_data_net(tmp_path):
    """A shared data net must not make different clock trees appear to be one tap."""
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    proc = "proc pg_classes" + PG.TAIL.split("proc pg_classes", 1)[1].split("\n}\n", 1)[0] + "\n}\n"
    script = r"""
namespace eval sta {}
proc find_timing_paths {args} { return {path_same path_cross} }
proc get_property {p key} {
  if {$key eq "startpoint"} {return launch}
  if {$p eq "path_same"} {return cap_same}
  return cap_cross
}
proc sta::time_sta_ui {v} {return $v}
proc sta::sta_to_db_pin {v} {return $v}
proc path_same {op} {return -5}
proc path_cross {op} {return -9}
proc launch {op} {return launch_inst}
proc cap_same {op} {return cap_same_inst}
proc cap_cross {op} {return cap_cross_inst}
proc pg_clk_iterm {inst} {return ${inst}_clock}
proc pg_tap_of {pin} {
  # A DATA pin would trace to the common data source, and misclassify the crossing.
  if {$pin eq "launch"} {error "launch DATA pin queried as a clock"}
  if {$pin eq "cap_cross_inst_clock"} {return tap_B}
  return tap_A
}
"""
    f = tmp_path / "classify.tcl"
    f.write_text(script + proc + "pg_classes test\n")
    result = subprocess.run([tclsh, str(f)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "same_tap 1 ws -5.00 cross_tap 1 ws -9.00" in result.stdout


def test_legalize_failure_keeps_the_repair(tmp_path):
    """PREGRT-LEGAL-1: negotiation legalizer failure -> diamond retry -> residue logged, repaired DB kept (no FALLBACK)."""
    tcl = (_kit(tmp_path, {"pregrt_ff_hold": True}) and (tmp_path / "pregrt_ff_hold.tcl").read_text())
    i = tcl.index("PREGRT-LEGAL-1")
    seg = tcl[i:tcl.index("estimate_parasitics -placement", i)]
    assert seg.index("detailed_placement; check_placement -verbose") < seg.index("detailed_placement -use_diamond_legalizer")
    assert "legalize RESIDUE" in seg and "repaired DB kept" in seg
    # the residue branch sets no pg_fail: only the outer tool-error catch and the setup/hold gain checks can fall back
    assert "set pg_fail" not in seg
    assert "check_placement -verbose\n  estimate_parasitics" not in tcl


def test_pregrt_nonport_scope_default():
    """PREGRT-NONPORT 11-18: the pass excepts hold from input ports by default (same scope as the GRT repair)."""
    from pathlib import Path
    t = (Path(__file__).with_name("pregrt_ff_hold.py")).read_text()
    assert "OT_PREGRT_HOLD_PORTS" in t and "pg_np_apply" in t and "pg_np_end" in t
    assert t.index("pg_np_apply\n") < t.index("foreach pg_tag {all rr xt}")
