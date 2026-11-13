"""R-CLOCK HOLD BUILD (HOLD-TAP-1 11-13; was HEAD-TILE-PREGRT-HOLD DH59-TILE 11-03) + clock.tap_core_etap plan form:
the placement-basis FF hold build is ON for every type, plan clock.pregrt_ff_hold false writes nothing."""
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


def test_default_is_on_for_every_type(tmp_path):
    assert PG.enabled({}) and PG.enabled({"clock": {}}) and PG.enabled({"clock": {"pregrt_ff_hold": True}})
    assert not PG.enabled({"clock": {"pregrt_ff_hold": False}})
    assert _kit(tmp_path, {}) is True
    assert PG.config_lines({"clock": {}}) == [PG.CONFIG, "export OT_PREGRT_HOLD_GUARD = 45"]
    assert PG.config_lines({"clock": {"pregrt_hold_guard_ps": 40}})[1] == "export OT_PREGRT_HOLD_GUARD = 40"
    with pytest.raises(ValueError):
        PG.config_lines({"clock": {"pregrt_hold_guard_ps": 150}})


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
    _kit(tmp_path, {})
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
    _kit(tmp_path, {})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "foreach pg_tag {all xt}" in t and "set pg_dg [expr {$pg_guard - $pg_pm}]" in t
    # the guard pass: port hold excepted, every tap port early latency widened, repair, then both restored
    a = t.index("set_false_path -hold -from $pg_in")
    w = t.index("set_clock_latency -source -early -clock $pg_ck [expr {$pg_e - $pg_dg}] [get_ports $pg_p]")
    r = t.index("repair_timing -hold -hold_margin $pg_pm -max_buffer_percent 100")
    z = t.index("set_clock_latency -source -early -clock $pg_ck $pg_e [get_ports $pg_p]")
    b = t.index("unset_path_exceptions -hold -from $pg_in")
    assert a < w < r < z < b
    assert "set_false_path -hold -to $pg_out" in t and "unset_path_exceptions -hold -to $pg_out" in t
    assert "OT_PREGRT_HOLD_PORT_MARGIN" in t and "OT_PREGRT_HOLD_GUARD" in t
    assert "cross-tap guard not applied" in t          # a kit without tap window lines keeps the base margin only


def test_tap_window_lines_are_the_generator_form(tmp_path):
    """the tcl reads the window ports from the lines gen_phys.tap_window_tcl writes (same regular expression)"""
    _kit(tmp_path, {})
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
    _kit(tmp_path, {})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    lock, rep, rel = t.index("setPlacementStatus FIRM"), t.index("repair_timing -hold"), t.index("foreach pg_i $pg_lock { $pg_i setPlacementStatus PLACED }")
    assert lock < rep < t.index("detailed_placement") < rel < t.index("write_db")


def test_fail_safe_conditions(tmp_path):
    _kit(tmp_path, {})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    assert "TT setup loss" in t and "no hold gain" in t and "tool error" in t
    assert "min($pg_s0, 0.0) - 1.0" in t          # a positive TT setup may be spent down to 0, never below


def test_class_report_and_open_list(tmp_path):
    _kit(tmp_path, {})
    t = (tmp_path / "pregrt_ff_hold.tcl").read_text()
    for c in ("port_in", "same_tap", "cross_tap", "port_out"):
        assert c in t
    assert "pg_classes before" in t and "pregrt_ff_hold_open.tsv" in t


def test_tcl_parses(tmp_path):
    tclsh = shutil.which("tclsh")
    if not tclsh:
        pytest.skip("no tclsh")
    _kit(tmp_path, {})
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
        PG.install({"clock": {}}, tmp_path)


def test_run_kit_step_is_guarded_advisory_and_before_grt():
    rk = gen_phys.RUN_KIT
    assert rk.count("grep -q '^export OT_PREGRT_FF_HOLD = 1' /work/config.mk") == 1
    assert rk.index("/work/hold_gate.log") < rk.index("/work/pregrt_ff_hold.tcl") < rk.index("OT_VCLK_CORNER=ff")
    step = rk[rk.index("grep -q '^export OT_PREGRT_FF_HOLD = 1'"):rk.index("HM=; if [")]
    assert "print-TC_LIB_FILES" in step and "TLIBS=" in step and "OT_PREGRT_HOLD_GUARD=" in step
    # a failed build never stops the kit: no FAIL_POSTCTS, rc stays 0, the temporary database is removed
    assert "FAIL_POSTCTS" not in step and "rc=6" not in step and "pgrc=" in step
    assert "OT_PREGRT_FF_HOLD FALLBACK step rc" in step and '.pg_tmp' in step


def test_schema_keys():
    ck = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["tap_core_etap"] == {"type": "boolean"} and ck["pregrt_ff_hold"] == {"type": "boolean"}
    assert ck["pregrt_hold_guard_ps"] == {"type": "number", "minimum": 0, "maximum": 100}
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert (on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
            ["pregrt_hold_guard_ps"]) == ck["pregrt_hold_guard_ps"]
