"""HOLD-PAD-FLOW 11-24: planned hold pad (hold_pad.tcl) and its place in the pre-GRT hold build (pregrt_ff_hold.py)."""
import shutil
import subprocess
from pathlib import Path
import pytest
import pregrt_ff_hold as PG

HERE = Path(__file__).resolve().parent

# endpoints: name hold_slack tt_setup_slack (- = no setup path) kind (reg | macro | port | async)
STUB = r"""
set ::ins {}
proc ord::get_db_block {} { return blk }
proc blk {m} { return [lrepeat 40000 i] }
proc get_lib_cells {args} { return HB4 }
proc unset_dont_use {args} {}
proc all_registers {args} { set o {}; foreach e $::E { if {[lindex $e 3] eq "async"} { lappend o [lindex $e 0] } }; return $o }
proc get_full_name {p} { return $p }
proc find_timing_paths {args} {
  set o {}
  if {[lsearch $args -to] >= 0} {
    set to [lindex $args [expr {[lsearch $args -to] + 1}]]
    foreach e $::E { if {[lindex $e 0] in $to && [lindex $e 2] ne "-"} { lappend o [list max [lindex $e 0] [lindex $e 2]] } }
    return $o
  }
  set sm [lindex $args [expr {[lsearch $args -slack_max] + 1}]]
  foreach e $::E { if {[lindex $e 1] <= $sm} { lappend o [list min [lindex $e 0] [lindex $e 1]] } }
  return $o
}
proc get_property {pe k} { expr {$k eq "slack" ? [lindex $pe 2] : [lindex $pe 1]} }
proc sta::sta_to_db_pin {p} {
  foreach e $::E { if {[lindex $e 0] eq $p} { if {[lindex $e 3] eq "port"} { return NULL } ; return "it:[lindex $e 3]" } }
}
proc it:reg {m} { return [dict get {getInst inst getNet net getMTerm mt} $m] }
proc it:macro {m} { return [dict get {getInst minst getNet net getMTerm mt} $m] }
proc inst {m} { return [dict get {getMaster mst getLocation {2000 4000}} $m] }
proc minst {m} { return [dict get {getMaster mmst} $m] }
proc mst {m} { return [dict get {isBlock 0 isSequential 1} $m] }
proc mmst {m} { return [dict get {isBlock 1 isSequential 0} $m] }
proc net {m} { return SIGNAL }
proc mt {m} { return [dict get {getSigType SIGNAL getName D} $m] }
proc ord::dbu_to_microns {v} { expr {$v / 1000.0} }
proc insert_buffer {args} { lappend ::ins $args }
"""


def run(tmp_path, ends, margin, env="", budget=0):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    e = " ".join("{%s}" % " ".join(str(x) for x in row) for row in ends)
    (tmp_path / "t.tcl").write_text("namespace eval ord {}\nnamespace eval sta {}\n" + STUB + env + f"\nset ::E {{{e}}}\n"
                                    + (HERE / "hold_pad.tcl").read_text()
                                    + f"\nputs \"N [ot_hold_pad t {margin} {budget} {tmp_path}]\"\n"
                                    + "foreach i $::ins { puts \"INS [lindex $i 1] [lindex $i 3] [lindex $i 5]\" }\n")
    r = subprocess.run(["tclsh", str(tmp_path / "t.tcl")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = (tmp_path / "hold_pad_t.tsv").read_text().splitlines()[1:]
    return r.stdout.splitlines(), {x.split("\t")[0]: x.split("\t")[1:] for x in rows}


def test_count_is_computed_from_the_slack_and_capped_by_tt_headroom(tmp_path):
    out, plan = run(tmp_path, [("a/D", -72.31, 200, "reg"),     # ceil((20+72.31)/37) = 3
                               ("b/D", -10, 70, "reg"),         # wants 1, headroom floor(70/60) = 1
                               ("c/D", -60, 70, "reg"),         # wants 3, headroom 1 -> cut
                               ("d/D", -5, 30, "reg"),          # no headroom -> left to the in-flow repair
                               ("e/D", 0, "-", "reg"),          # no setup path: unlimited
                               ("f/D", -300, 1000, "reg"),      # clamped at 4
                               ("m/A", -50, 500, "macro"),      # macro pin: skipped
                               ("p", -50, 500, "port"),         # port: skipped
                               ("r/RN", -50, 500, "async"),     # async: skipped
                               ("ok/D", 25, 10, "reg")], 20)    # above the margin: not a target
    assert plan["a/D"][2] == "3" and plan["b/D"][2] == "1" and plan["e/D"][2] == "1"
    assert plan["c/D"][2:] == ["1", "setup_cut"] and plan["d/D"][2:] == ["0", "setup_blocked"]
    assert plan["f/D"][2:] == ["4", "clamped 4"]
    assert not {"m/A", "p", "r/RN", "ok/D"} & set(plan)
    assert "N 10" in out
    ins = [x for x in out if x.startswith("INS")]
    assert len(ins) == 10 and all(x.endswith(" 2.0 4.0") for x in ins)
    assert ins[0].startswith("INS HB4xp67_ASAP7_75t_R f/D")           # worst endpoint first
    s = next(x for x in out if x.startswith("OT_HOLD_PAD t"))
    assert "ends 6 padded 5 cells 10" in s and "setup_blocked 1 setup_cut 1 clamped 1" in s and "skipped_nonreg 3" in s


def test_budget_and_env_knobs(tmp_path):
    env = "set ::env(OT_HOLD_PAD_FF_PS) 10\nset ::env(OT_HOLD_PAD_SETUP_FLOOR) -50\nset ::env(OT_HOLD_PAD_MAX_PER_END) 9\n"
    out, plan = run(tmp_path, [("a/D", -25, 10, "reg"), ("b/D", -15, 500, "reg")], 5, env, budget=2)
    assert plan["a/D"][2] == "1"        # wants 3, headroom floor((10+50)/60) = 1
    assert plan["b/D"][2:] == ["0", "budget"]   # wants 2: 1 + 2 > budget 2
    assert "N 1" in out


def test_mode_default_env_and_validation(monkeypatch):
    monkeypatch.delenv(PG.PAD_ENV, raising=False)
    assert PG.pad_mode() == "rr"
    t = PG.tail_text(-1)
    assert "proc ot_hold_pad" in t and '$::env(OT_PREGRT_HOLD_PAD) : "rr"' in t and "@PG_HOLD" not in t
    monkeypatch.setenv(PG.PAD_ENV, "0")
    assert '$::env(OT_PREGRT_HOLD_PAD) : "0"' in PG.tail_text(-1)
    monkeypatch.setenv(PG.PAD_ENV, "yes")
    with pytest.raises(ValueError):
        PG.pad_mode()


def test_rr_pass_pads_and_other_passes_pad_only_the_stalled_residual(monkeypatch):
    monkeypatch.delenv(PG.PAD_ENV, raising=False)
    t = PG.tail_text(-1)
    assert "[pg_pad_on $pg_tag] ? [pg_pad_pass $pg_tag $pg_ps $pg_mrg $pg_inst_before] : [pg_repair_hold" in t
    assert 'if {$pg_pad_mode eq "rr" && $pg_tag ne "rr" && [pg_hold] < $pg_mrg}' in t
    # the pad never adds an RC refresh of its own (the GRT form rewrites exactly two)
    assert "estimate_parasitics" not in (HERE / "hold_pad.tcl").read_text()


def test_pad_dispatch_and_fallback(tmp_path):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    t = PG.tail_text(-1)
    seg = t[t.index("set pg_pad_mode"):t.index('puts "OT_PREGRT_FF_HOLD pad mode')]
    (tmp_path / "d.tcl").write_text("""
proc pg_repair_hold {tag m i} { puts "RT $tag"; return 7 }
proc ot_hold_pad {args} { if {$::fail} { error boom } ; puts "PAD $args"; return 3 }
set ::fail 0
""" + seg + """
foreach m {rr all 0} {
  set ::env(OT_PREGRT_HOLD_PAD) $m; set pg_pad_mode $::env(OT_PREGRT_HOLD_PAD)
  foreach tag {all rr xt} { puts "$m $tag [pg_pad_on $tag]" }
}
set pg_pad_mode rr
puts "ret [pg_pad_pass rr 1 40 100]"
set ::fail 1
puts "ret [pg_pad_pass rr 2 40 100]"
""")
    r = subprocess.run(["tclsh", str(tmp_path / "d.tcl")], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    assert r.returncode == 0, r.stderr
    assert lines[:9] == ["rr all 0", "rr rr 1", "rr xt 0", "all all 1", "all rr 1", "all xt 1", "0 all 0", "0 rr 0", "0 xt 0"]
    assert lines[9].startswith("PAD rr1 40 0 ") and lines[10] == "ret 0"
    assert "tool error (boom): repair_timing for this pass" in lines[11] and lines[12:] == ["RT rr", "ret 7"]


def _old_kit(tmp_path, auto=-1, same_leaf=False):
    kd = tmp_path / "kit"
    kd.mkdir()
    hg = (HERE / "hold_gate.tcl").read_text()
    (kd / "hold_gate.tcl").write_text(hg)
    old = hg.split(PG.MARK)[0] + f"# an older pinned-snapshot build\nset pg_auto {auto}\nrepair_timing -hold -hold_margin 40 -max_buffer_percent 100\n"
    if same_leaf:
        old += "pg_sl_begin OT_PREGRT_FF_HOLD $pg_rm $pg_pm\n"
    (kd / "pregrt_ff_hold.tcl").write_text(old)
    (kd / "pregrt_ff_hold.tcl").chmod(0o640)
    return kd


def test_refresh_regenerates_an_old_kit_build_and_keeps_its_settings(tmp_path, monkeypatch):
    monkeypatch.delenv(PG.PAD_ENV, raising=False)
    monkeypatch.delenv(PG.SAME_LEAF_ENV, raising=False)
    kd = _old_kit(tmp_path, auto=100, same_leaf=True)
    ino = (kd / "pregrt_ff_hold.tcl").stat().st_ino
    s = PG.refresh(kd)
    assert s.startswith("refreshed (auto 100, basis placement, same_leaf 1, pad rr)"), s
    new = (kd / "pregrt_ff_hold.tcl").read_text()
    assert "set pg_auto 100" in new and "proc ot_hold_pad" in new and "pg_sl_begin OT_PREGRT_FF_HOLD" in new
    assert (kd / "pregrt_ff_hold.tcl").stat().st_ino != ino and (kd / "pregrt_ff_hold.tcl").stat().st_mode & 0o777 == 0o640
    assert PG.refresh(kd) == "same"
    assert PG.SAME_LEAF_ENV not in __import__("os").environ      # the process env is restored


def test_refresh_is_fail_safe(tmp_path):
    kd = tmp_path / "k"
    kd.mkdir()
    assert PG.refresh(kd).startswith("absent")
    (kd / "hold_gate.tcl").write_text("no marker\n")
    (kd / "pregrt_ff_hold.tcl").write_text("set pg_auto -1\n")
    assert PG.refresh(kd).startswith("left:") and (kd / "pregrt_ff_hold.tcl").read_text() == "set pg_auto -1\n"
    (kd / "pregrt_ff_hold.tcl").write_text("no auto line\n")
    assert PG.refresh(kd).startswith("left: no 'set pg_auto'")
