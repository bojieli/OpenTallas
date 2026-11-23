"""HOLD-SAMELEAF-1 (S81 rc35, 11-23): the reg-to-reg family hold margin does not pad capture registers whose whole launch cone
sits on their own clock leaf net (self-loops, same-leaf zero-logic pairs).  Off (gen env unset) = byte-identical kit."""
import shutil
import subprocess
from pathlib import Path

import pytest

import pregrt_ff_hold as PG

HERE = Path(__file__).resolve().parent
SL = HERE / "hold_same_leaf.tcl"

# tclsh mock of the few OpenROAD commands the scope uses: two leaf nets (one with an unresolvable pin), exceptions kept in ::exc
MOCK = r"""
set ::log {}; set ::exc {}; set ::mode tt; set ::drift 0
proc get_pins {q n} { return [expr {[string match gone/* $n] ? {} : [list P:$n]}] }
proc set_false_path {h f from t to} { lappend ::exc [list $from $to]; lappend ::log "FP $::mode [llength $from]>[llength $to]" }
proc unset_path_exceptions {h f from t to} {
  set i [lsearch -exact $::exc [list $from $to]]; if {$i < 0} { error "no such exception" }
  set ::exc [lreplace $::exc $i $i]; lappend ::log "UNFP $::mode"
}
proc write_sdc {args} { set f [open [lindex $args end] w]; puts $f "sdc exc=[llength $::exc] drift=$::drift"; close $f; if {$::drift < 0} { set ::drift 1 } }
proc read_sdc {args} { lappend ::log "READ $args" }
proc set_mode {m} { set ::mode $m }
namespace eval sta { proc cmd_mode_name {} { return $::mode } }
proc repair_timing {args} { lappend ::log "RT $::mode exc=[llength $::exc] $args"; if {"-boom" in $args} { error boom }; return done }
"""
GROUPS = "proc pg_sl_groups {} { return {{{a/CLK b/CLK} {a/D b/D}} {{c/CLK gone/CLK} {c/D gone/D}} {{gone/CLK} {gone/D}}} }\n"


def _tcl(tmp_path, body):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh not installed")
    s = tmp_path / "t.tcl"
    s.write_text(MOCK + f"source {SL}\n" + GROUPS + body + '\nputs [join $::log "\\n"]\nputs "left [llength $::exc] files [llength [glob -nocomplain pg_same_leaf_*]]"\n')
    r = subprocess.run(["tclsh", str(s)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_off_is_byte_identical(tmp_path, monkeypatch):
    gate = (HERE / "hold_gate.tcl").read_text()
    monkeypatch.delenv(PG.SAME_LEAF_ENV, raising=False)
    off = PG.tcl_text(gate)
    assert "pg_sl_" not in off and f"export {PG.SAME_LEAF_ENV} = 1" not in PG.config_lines({"clock": {"pregrt_ff_hold": True}})
    monkeypatch.setenv(PG.SAME_LEAF_ENV, "0")
    assert PG.tcl_text(gate) == off
    (tmp_path / "hold_gate.tcl").write_text(gate)
    assert PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path) and not (tmp_path / "hold_same_leaf.tcl").exists()
    monkeypatch.setenv(PG.SAME_LEAF_ENV, "yes")
    with pytest.raises(ValueError):
        PG.same_leaf_on()


def test_on_scopes_only_the_family_pass(tmp_path, monkeypatch):
    gate = (HERE / "hold_gate.tcl").read_text()
    monkeypatch.delenv(PG.SAME_LEAF_ENV, raising=False)
    off = PG.tcl_text(gate)
    monkeypatch.setenv(PG.SAME_LEAF_ENV, "1")
    on = PG.tcl_text(gate)
    # the scope opens after the port exceptions of the rr pass and closes before they are removed; nothing else changes
    a = on.index("pg_sl_begin OT_PREGRT_FF_HOLD $pg_rm $pg_pm")
    assert on.index("set pg_mrg $pg_rm") < a < on.index("for {set pg_ps 1}") < on.index("      pg_sl_end\n") < on.index('if {$pg_tag eq "xt"} {\n      set pg_xt')
    assert on.count("pg_sl_begin OT_PREGRT") == 1 and on.count("      pg_sl_end\n") == 1
    stripped = on.replace(SL.read_text(), "")
    stripped = stripped.replace("      pg_sl_begin OT_PREGRT_FF_HOLD $pg_rm $pg_pm\n", "").replace("      pg_sl_end\n", "")
    assert stripped == off
    assert PG.tcl_text(gate, rc_basis="global_routing").count("pg_sl_begin OT_PREGRT") == 1      # the closed-GRT form carries it too
    assert PG.config_lines({"clock": {"pregrt_ff_hold": True}})[-1] == f"export {PG.SAME_LEAF_ENV} = 1"
    assert PG.config_lines({"clock": {"pregrt_ff_hold": False}}) == []
    (tmp_path / "hold_gate.tcl").write_text(gate)
    assert PG.install({"clock": {"pregrt_ff_hold": True}}, tmp_path)
    assert (tmp_path / "hold_same_leaf.tcl").read_text() == SL.read_text()
    # the GRT hook sources the kit copy only when the kit says so
    g = (HERE / "hold_guard_grt.tcl").read_text()
    assert g.index("OT_HOLD_SAME_LEAF") < g.index("rename ::repair_timing_helper") and "pg_sl_install" in g


def test_begin_excepts_the_paths_inside_each_leaf_and_end_restores(tmp_path):
    out = _tcl(tmp_path, 'puts "n [pg_sl_begin T 30 5]"\nputs "mid [llength $::exc]"\npg_sl_end')
    lines = out.splitlines()
    # one exception per leaf net, clock pins -> data pins; a leaf with no resolvable pin is skipped; all removed, SDC replayed and compared
    assert "n 3" in lines and "mid 2" in lines and lines.count("FP tt 2>2") == 1 and lines.count("FP tt 1>1") == 1
    assert lines.count("UNFP tt") == 2 and any(l.startswith("READ ") for l in lines) and lines[-1] == "left 0 files 0"
    assert "3 registers on 2 clock leaf nets keep margin 5 in the margin 30 pass" in out


def test_begin_is_off_at_or_below_the_base_and_restore_mismatch_fails_closed(tmp_path):
    out = _tcl(tmp_path, 'puts "n [pg_sl_begin T 5 5]"\npg_sl_end')
    assert "n 0" in out and "FP" not in out and "READ" not in out
    out = _tcl(tmp_path, 'set ::drift -1\npg_sl_begin T 30 5\nputs "rc [catch {pg_sl_end} e] $e"')
    assert "rc 1 same-leaf scope restore differs" in out


def test_two_mode_restore_reads_into_the_current_mode(tmp_path):
    out = _tcl(tmp_path, 'set ::pg_two 1\nset_mode ff\npg_sl_begin T 30 5\npg_sl_end')
    assert any(l.startswith("READ -mode ff ") for l in out.splitlines())


def test_grt_wrapper(tmp_path):
    out = _tcl(tmp_path, """set ::ot_mm_synced 1
puts "i [pg_sl_install][pg_sl_install]"
repair_timing -setup -setup_margin 0
repair_timing -hold -hold_margin 5
repair_timing -hold -hold_margin 30 -max_buffer_percent 100
repair_timing -setup_margin 0 -hold_margin 30
catch {repair_timing -hold -hold_margin 30 -boom}""")
    lines = out.splitlines()
    assert "i 10" in lines                                                   # installed once
    assert "RT tt exc=0 -setup -setup_margin 0" in lines and "RT tt exc=0 -hold -hold_margin 5" in lines      # pass-through
    # two-mode session: the scope is written and removed in mode ff, the repair runs in the caller's mode inside it,
    # then a hold-only base-margin pass runs with the scope gone
    i = lines.index("RT tt exc=2 -hold -hold_margin 30 -max_buffer_percent 100")
    assert lines[i - 1] == "FP ff 1>1" and lines[i + 1] == "UNFP ff"
    assert "RT tt exc=0 -hold -hold_margin 5.0 -max_buffer_percent 100" in lines[i:]
    # the combined (no flag) form repairs hold too; its base pass is hold-only and keeps the other arguments
    assert "RT tt exc=2 -setup_margin 0 -hold_margin 30" in lines and "RT tt exc=0 -setup_margin 0 -hold_margin 5.0 -hold" in lines
    j = lines.index("RT tt exc=2 -hold -hold_margin 30 -boom")
    assert lines[j + 1] == "UNFP ff" and not any("-boom" in l and "5.0" in l for l in lines)      # removed on error, no base pass
    assert lines[-1] == "left 0 files 0"


def test_grt_wrapper_not_applied_is_plain_repair(tmp_path):
    out = _tcl(tmp_path, 'proc set_false_path {args} { error nope }\npg_sl_install\nputs [repair_timing -hold -hold_margin 30]')
    assert "OT_HOLD_SAME_LEAF not applied (nope)" in out and "RT tt exc=0 -hold -hold_margin 30" in out and "done" in out
    assert out.count("RT ") == 1
