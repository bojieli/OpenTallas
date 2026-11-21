"""FABLE-PD-HEAD-1650 finding 1 (COORD r190): TT setup repair step between CTS and GRT, opt-in (gen env OT_TT_SETUP_REPAIR=1)."""
import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

TCLSH = shutil.which("tclsh")


def _kit(tmp, monkeypatch, on):
    monkeypatch.delenv("OT_TT_SETUP_REPAIR", raising=False)
    if on:
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", "1")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp), [])
    return Path(tmp) / "fa"


def test_default_kit_has_no_tt_step_files(tmp_path, monkeypatch):
    k = _kit(tmp_path, monkeypatch, False)
    assert not (k / "tt_setup_repair.tcl").exists() and not (k / "tt_setup_repair.on").exists()


def test_flag_writes_the_step_files(tmp_path, monkeypatch):
    k = _kit(tmp_path, monkeypatch, True)
    assert (k / "tt_setup_repair.on").read_text().strip() == "cts"
    assert (k / "tt_setup_repair.tcl").read_text() == (HERE / "tt_setup_repair.tcl").read_text()
    assert (k / "grt_pg_replay.tcl").read_text() == (HERE / "grt_pg_replay.tcl").read_text()


def test_run_kit_step_is_flag_gated_fail_open_and_between_cts_and_grt():
    t = gen_phys.RUN_KIT
    i = t.index("tt_setup_repair.on")
    assert t.index("$M cts SKIP_CTS_REPAIR_TIMING=1") < i < t.index("hold_gate.tcl")
    assert "OT_TT_SETUP_REPAIR FALLBACK" in t and "4_cts.odb unchanged" in t         # failure keeps the CTS result


def test_tcl_step_repairs_setup_only_in_the_tt_scene():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert "print-TC_LIB_FILES" in t and "repair_timing -setup " in t and "-hold" not in t.replace("hold repair", "")
    assert "SETUP_SLACK_MARGIN" not in t.split("\n", 8)[-1].replace("SETUP_SLACK_MARGIN is NOT used", "")
    assert "set_clock_latency -source $::env(OT_VCLK_TT)" in t and "core_taps_ff" not in t


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_tcl_is_syntactically_complete():
    out = subprocess.run([TCLSH], input=f"set f [open {HERE / 'tt_setup_repair.tcl'}]; puts [info complete [read $f]]\n", capture_output=True, text=True)
    assert out.stdout.strip() == "1"


def test_modes_cts_grt_both_write_the_mode_into_the_flag_file(tmp_path, monkeypatch):
    for env, want in (("1", "cts"), ("cts", "cts"), ("grt", "grt"), ("both", "both")):
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", env)
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / env), [])
        assert (tmp_path / env / "fa" / "tt_setup_repair.on").read_text().strip() == want
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "0")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "off"), [])
    assert not (tmp_path / "off" / "fa" / "tt_setup_repair.on").exists()


def test_grt_step_runs_before_the_postcts_gate_reads_tt_and_routes_incrementally():
    t = gen_phys.RUN_KIT
    i = t.index("OT_TT_SETUP_RC=grt")
    assert t.index("OT_VCLK_CORNER=ff \\$MF grt CORNER=BC") < i < t.index("O5=\\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1)")
    assert "5_1_grt.odb unchanged" in t
    x = (HERE / "tt_setup_repair.tcl").read_text()
    assert "global_route -start_incremental -allow_congestion" in x and "global_route -end_incremental -allow_congestion" in x and "estimate_parasitics -global_routing" in x


def test_effective_mode_is_in_every_kit_config_and_json(tmp_path, monkeypatch):
    for env, want in (("0", "off"), ("1", "cts"), ("grt", "grt"), ("both", "both")):
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", env)
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / env), [])
        k = tmp_path / env / "fa"
        assert f"export OT_TT_SETUP_REPAIR = {want}" in (k / "config.mk").read_text().splitlines()
        import json
        assert json.loads((k / "kit_effective_env.json").read_text())["OT_TT_SETUP_REPAIR"] == want
    monkeypatch.delenv("OT_TT_SETUP_REPAIR", raising=False)
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "unset"), [])
    assert "export OT_TT_SETUP_REPAIR = off" in (tmp_path / "unset" / "fa" / "config.mk").read_text().splitlines()


def test_effective_env_json_lists_the_pg_and_pgcap_keys_that_act_at_gen_time(tmp_path, monkeypatch):
    import json
    for k in [k for k in __import__("os").environ if k.startswith(("OT_PG_", "OT_PGCAP"))]:
        monkeypatch.delenv(k)
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "both")
    monkeypatch.setenv("OT_PGCAP", "1")                # the C3b switch itself (no trailing underscore)
    monkeypatch.setenv("OT_PG_DIE_PHASE", "1")
    monkeypatch.setenv("OT_PG_CELL_KEEPOUT", "0")
    monkeypatch.setenv("OT_PGCAP_ADJ", "1.0")
    monkeypatch.setenv("OT_PG_PIN_CHECK", "")          # empty = not set
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path), [])
    got = json.loads((tmp_path / "fa" / "kit_effective_env.json").read_text())
    assert got == {"OT_PGCAP": "1", "OT_PGCAP_ADJ": "1.0", "OT_PG_CELL_KEEPOUT": "0", "OT_PG_DIE_PHASE": "1", "OT_TT_SETUP_REPAIR": "both"}


def test_calibrated_keys_reach_config_only_when_set_and_valid(tmp_path, monkeypatch):
    """FABLE-FIX-QC-HCFE 11-15: OT_TT_SETUP_CSCALE / _DESIGN / _MARGIN / _CLAYERS ride in config.mk (the step reads them there)."""
    keys = ("OT_TT_SETUP_CSCALE", "OT_TT_SETUP_DESIGN", "OT_TT_SETUP_MARGIN", "OT_TT_SETUP_CLAYERS")
    for k in keys:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "both")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "plain"), [])
    assert not any(k in (tmp_path / "plain" / "fa" / "config.mk").read_text() for k in keys)
    monkeypatch.setenv("OT_TT_SETUP_CSCALE", "1.45")
    monkeypatch.setenv("OT_TT_SETUP_DESIGN", "1")
    monkeypatch.setenv("OT_TT_SETUP_MARGIN", "30")
    monkeypatch.setenv("OT_TT_SETUP_CLAYERS", "M2,M3,M4,M5,M6,M7")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "cal"), [])
    lines = (tmp_path / "cal" / "fa" / "config.mk").read_text().splitlines()
    for want in ("export OT_TT_SETUP_CSCALE = 1.45", "export OT_TT_SETUP_DESIGN = 1", "export OT_TT_SETUP_MARGIN = 30",
                 "export OT_TT_SETUP_CLAYERS = M2,M3,M4,M5,M6,M7"):
        assert want in lines
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "0")                                    # no step, no keys
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "off"), [])
    assert not any(k in (tmp_path / "off" / "fa" / "config.mk").read_text() for k in keys)
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "both")
    for k, bad in (("OT_TT_SETUP_CSCALE", "0"), ("OT_TT_SETUP_CSCALE", "x"), ("OT_TT_SETUP_DESIGN", "2"), ("OT_TT_SETUP_MARGIN", "a b"),
                   ("OT_TT_SETUP_CLAYERS", "M2 M3")):
        monkeypatch.setenv(k, bad)
        with pytest.raises(ValueError):
            gen_phys.tt_setup_repair_cfg()
        monkeypatch.setenv(k, {"OT_TT_SETUP_CSCALE": "1.45", "OT_TT_SETUP_DESIGN": "1", "OT_TT_SETUP_MARGIN": "30",
                               "OT_TT_SETUP_CLAYERS": "M2,M3,M4,M5,M6,M7"}[k])


def test_tcl_scales_layer_c_only_on_the_grt_basis_and_repairs_design_on_request():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert 'if {$ot_tt_rc eq "grt" && $ot_tt_cs != 1.0}' in t and "-capacitance [expr {$c * $ot_tt_cs}]" in t
    assert "OT_TT_SETUP_MARGIN|OT_TT_SETUP_CSCALE|OT_TT_SETUP_CLAYERS|OT_TT_SETUP_DESIGN" in t          # read from config.mk
    i = t.index("global_route -start_incremental -allow_congestion")
    assert i < t.index("repair_design -verbose") < t.index("ot_bounded_repair tt_setup_repair") < t.index("global_route -end_incremental")      # the chunk proc (repair_timing) runs between them
    assert "repair_timing -setup -setup_margin" in t.split("proc ::ot_tt_chunk")[1].split("proc ::ot_tt_measure")[0]
    assert "if {$w0 < $mg || $ot_tt_design}" in t


def _bounded_tcl(script, env=None, delay_ms=0):
    """run hold_cap.tcl's bounded repair in tclsh with stubs: repair_timing_helper_orig counts its calls, sta::worst_slack follows a slack script"""
    hc = (HERE.parents[1] / "physical/die_plan/hbm_arch_cores/hold_cap.tcl").read_text()
    prog = ("""
namespace eval sta {}
proc repair_timing_helper {args} {}
set ::calls 0
set ::seq {SEQ}
set ::i 0
proc sta::worst_slack {which} { set v [lindex $::seq [expr {min($::i, [llength $::seq]-1)}]]; return [lindex $v [expr {$which eq "-max" ? 0 : 1}]] }
""" + hc + """
rename ::ot_repair_timing_helper_orig ::ot_stub_orig
proc ::ot_repair_timing_helper_orig {args} { incr ::calls; incr ::i; after DELAYMS; puts "CALL $args" }
repair_timing_helper -setup
puts "CALLS $::calls"
""").replace("SEQ", script).replace("DELAYMS", str(delay_ms))
    import os
    e = dict(os.environ, **(env or {}))
    return subprocess.run([TCLSH], input=prog, capture_output=True, text=True, env=e).stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_stalled_repair_stops_after_three_flat_chunks():
    out = _bounded_tcl("{-270 -5} {-270 -5} {-270 -5} {-270 -5} {-270 -5} {-270 -5} {-270 -5}")
    assert "OT_REPAIR_STALL repair_timing_helper stop after 600 iterations" in out and "CALLS 3" in out
    assert out.count("-max_iterations 200") == 3


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_improving_repair_continues_until_met_or_the_old_cap():
    out = _bounded_tcl("{-300 -5} {-250 -5} {-200 -5} {-100 -5} {0 0}")
    assert "CALLS 4" in out and "OT_REPAIR_STALL" not in out                          # slack >= 0 ends it
    out = _bounded_tcl("{-300 -5} {-290 -5} {-280 -5} {-270 -5} {-260 -5} {-250 -5} {-240 -5}", {"OT_MAX_ITERATIONS": "600"})
    assert "CALLS 3" in out and "OT_REPAIR_STALL" not in out                          # the old total cap (here 600 = 3 chunks) still bounds it


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_wall_time_cap_stops_a_slowly_improving_repair():
    seq = " ".join("{%d -5}" % (-300 + 10 * k) for k in range(40))
    out = _bounded_tcl(seq, {"OT_REPAIR_MAX_S": "1", "OT_REPAIR_CHUNK": "50"}, delay_ms=1200)
    assert "OT_REPAIR_WALLCAP repair_timing_helper stop after 50 iterations" in out and "OT_REPAIR_STALL" not in out and "CALLS 1" in out


def test_tt_setup_step_and_hold_cap_use_the_bounded_repair_and_are_complete_tcl():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert "ot_bounded_repair tt_setup_repair" in t and "-max_iterations $n" in t and "repair_timing -setup -setup_margin $mg -repair_tns 100 -skip_last_gasp -verbose {*}$extra\n" not in t
    h = (HERE.parents[1] / "physical/die_plan/hbm_arch_cores/hold_cap.tcl").read_text()
    assert "ot_bounded_repair repair_timing_helper" in h and "OT_REPAIR_STALL" in h and "OT_REPAIR_WALLCAP" in h
    if TCLSH:
        for f in (HERE / "tt_setup_repair.tcl", HERE.parents[1] / "physical/die_plan/hbm_arch_cores/hold_cap.tcl"):
            out = subprocess.run([TCLSH], input=f"set f [open {f}]; puts [info complete [read $f]]\n", capture_output=True, text=True)
            assert out.stdout.strip() == "1", f


def _chunk_tcl(rsz_at, est_fails, other_error_at=0, msg="RSZ-0074 found route to 3 pins, expected 4", seq="{-300} {-250} {-200} {-150} {-100} {-50} {0}"):
    """FLOW-FIX-2045: the real procs of tt_setup_repair.tcl (estimate ladder, bounded loop, chunk) in tclsh; repair_timing throws RSZ-0074 at call rsz_at, estimate_parasitics fails est_fails times after it"""
    t = (HERE / "tt_setup_repair.tcl").read_text()
    a = t.index("proc ot_tt_est {}")
    b = t.index("ot_tt_est\n# r222")
    c = t.index("proc ::ot_bounded_repair")
    d = t.index("lassign [ot_tt_wns before]")
    prog = ("""
namespace eval sta {}
set ot_tt_rc grt
set ::calls 0
set ::i 0
set ::seq [list SEQ]
set ::estfail 0
proc sta::worst_slack {w} { return [lindex $::seq [expr {min($::i, [llength $::seq]-1)}]] }
proc repair_timing {args} {
  incr ::calls
  if {$::calls == RSZAT} { incr ::i; set ::estfail ESTFAILS; error RSZMSG }
  if {$::calls == OTHERAT} { error "RSZ-0001 something else" }
  incr ::i
}
proc set_dont_touch {args} { puts "DT $args" }
proc get_nets {n} { return "N:$n" }
proc global_route {args} { puts "GR $args" }
proc estimate_parasitics {args} { if {$::estfail > 0} { incr ::estfail -1; error "RSZ-0074 still broken" } }
""" + t[a:b] + t[c:d] + """
set rc [catch {ot_bounded_repair tt_setup_repair [list ::ot_tt_chunk 0 {}] ::ot_tt_measure 4000} done]
puts "RC $rc DONE $done CALLS $::calls"
""").replace("SEQ", seq).replace("RSZAT", str(rsz_at)).replace("ESTFAILS", str(est_fails)).replace("OTHERAT", str(other_error_at)).replace("RSZMSG", "{" + msg + "}")
    return subprocess.run([TCLSH], input=prog, capture_output=True, text=True).stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_rsz_0074_inside_a_chunk_keeps_the_repair_and_goes_on():
    out = _chunk_tcl(rsz_at=2, est_fails=1)                      # the first estimate after the error fails once: the incremental re-route clears it
    assert "WARNING RSZ-0074 inside repair_timing" in out and "RSZ-0074 cleared by an incremental re-route" in out
    assert "OT_REPAIR_ABORT" not in out and "RC 0" in out and "CALLS 6" in out          # slack reaches 0 after 6 chunks (the errored one included): the repair went on after the error


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_unrepairable_route_stops_the_repair_but_keeps_the_dbs_improvement():
    out = _chunk_tcl(rsz_at=2, est_fails=99)
    assert "route not repairable after the chunk" in out and "OT_REPAIR_ABORT tt_setup_repair stop after 400 iterations" in out
    assert "RC 0 DONE 400 CALLS 2" in out                                                  # no error escapes: the caller goes on to write the DB


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_other_errors_still_propagate():
    out = _chunk_tcl(rsz_at=99, est_fails=0, other_error_at=2)
    assert "RC 1" in out and "OT_REPAIR_ABORT" not in out


def test_post_repair_steps_and_final_measure_never_discard_the_repaired_db():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert "a step after the repair failed" in t and "final measure failed" in t
    assert t.index("a step after the repair failed") < t.index("write_db $out")


def _rb_tcl(seq, env=None):
    """physical/common_flow/repair_bound.tcl sourced over a stub ORFS repair_timing_helper (counts calls and prints its args)"""
    rb = HERE.parents[1] / "physical/common_flow/repair_bound.tcl"
    prog = (f"""
namespace eval sta {{}}
set ::calls 0
set ::i 0
proc repair_timing_helper {{args}} {{ incr ::calls; incr ::i; puts "HELPER $args" }}
proc sta::worst_slack {{w}} {{ set v [lindex {{SEQ}} [expr {{min($::i, 99)}}]]; return [lindex $v [expr {{$w eq "-max" ? 0 : 1}}]] }}
source {rb}
repair_timing_helper -setup_margin 0 -repair_tns 100
puts "CALLS $::calls"
""").replace("{SEQ}", "[list " + seq + "]")
    import os
    return subprocess.run([TCLSH], input=prog, capture_output=True, text=True, env=dict(os.environ, **(env or {}))).stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_post_grt_repair_with_wns_stuck_at_minus_242_stops_after_three_chunks_of_50():
    out = _rb_tcl("{-242.069 -3} " * 30)
    assert "OT_REPAIR_STALL post_grt_repair stop after 150 iterations" in out and "CALLS 3" in out
    assert out.count("-max_iterations 50") == 3 and "HELPER -setup_margin 0 -repair_tns 100 -max_iterations 50" in out


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_post_grt_repair_keeps_going_while_it_improves_and_can_be_switched_off():
    out = _rb_tcl(" ".join("{%d 0}" % (-242 + 20 * k) for k in range(30)))
    assert "OT_REPAIR_STALL" not in out and "CALLS 13" in out                              # reaches slack >= 0 after 13 chunks
    off = _rb_tcl("{-242 -3} " * 5, {"OT_REPAIR_BOUND": "0"})
    assert "CALLS 1" in off and "max_iterations" not in off                                 # the original helper, untouched


def test_repair_bound_is_complete_tcl():
    f = HERE.parents[1] / "physical/common_flow/repair_bound.tcl"
    if TCLSH:
        out = subprocess.run([TCLSH], input=f"set f [open {f}]; puts [info complete [read $f]]\n", capture_output=True, text=True)
        assert out.stdout.strip() == "1"


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_rsz_0074_names_a_net_it_is_set_dont_touch_before_the_reroute_and_the_repair_resumes():
    """FABLE-FIX-S81-LEPE 11-20: 'Failed to build tree from global routes for pin wire155183/Y and net net155182 at grid (216885, 311505)' inside repair_timing"""
    out = _chunk_tcl(rsz_at=2, est_fails=1, msg="RSZ-0074 Failed to build tree from global routes for pin wire155183/Y and net net155182 at grid (216885, 311505): found route to 1 pins, expected 2")
    assert "DT N:net155182" in out and "net net155182 set dont_touch (1 so far)" in out
    assert out.index("DT N:net155182") < out.index("GR -allow_congestion -start_incremental")     # before the re-route
    assert "RSZ-0074 cleared by an incremental re-route" in out and "OT_REPAIR_ABORT" not in out and "RC 0" in out and "CALLS 6" in out


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_a_message_without_a_net_sets_nothing_dont_touch():
    out = _chunk_tcl(rsz_at=2, est_fails=1)
    assert "DT " not in out and "dont_touch" not in out


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_rsz0074_net_name_is_unquoted_for_dont_touch():
    """RSZ-CRASH-2200: OpenROAD quotes the net (and net \x27net155182\x27 at grid); the captured name must be bare or get_nets / set_dont_touch fail and the same net kills the next chunk."""
    import re
    t = (HERE / "tt_setup_repair.tcl").read_text()
    m = re.search(r"regexp (\{and net [^}]*\}) \$err -> ot_nn", t)
    assert m, "net-name regexp not found"
    msg = "[ERROR RSZ-0074] Failed to build tree from global routes for pin \x27wire155183/Y\x27 and net \x27net155182\x27 at grid (216885, 311505): found route to 1 pins, expected 2"
    out = subprocess.run([TCLSH], input="set err {%s}\nif {[regexp %s $err -> n]} {puts \"<$n>\"}\n" % (msg, m.group(1)), capture_output=True, text=True)
    assert out.stdout.strip() == "<net155182>", out.stdout + out.stderr
