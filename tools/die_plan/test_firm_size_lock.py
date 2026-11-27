"""HEAD-INT-R2 11-26 (C-FIRM-RESIZE-OVERLAP): ot_firm_size_restore, the PRE_DETAIL_PLACE half of the sizing-only FIRM lock
(face_flops.tcl OT_FIRM_RESIZE_FREEZE=1 records masters, face_flops_release.tcl swaps still-FIRM grown cells back).  OpenDB mocked in tclsh."""
import shutil
import subprocess
from pathlib import Path

import pytest

REL = Path(__file__).with_name("face_flops_release.tcl").read_text()
PROC = REL[REL.index("proc ot_firm_size_restore"):REL.index("ot_firm_size_restore $ff_blk")]
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

MOCK = r"""
set ::M {DFFHQNx1_ASAP7_75t_R DFFHQNx2_ASAP7_75t_R}
set ::I {%(INSTS)s}
namespace eval ord { proc get_db {} { return db } }
proc db {op args} { if {$op eq "findMaster"} { if {[lindex $args 0] in $::M} { return "M:[lindex $args 0]" }; return NULL } }
proc blk {op args} { if {$op eq "findInst"} { set n [lindex $args 0]; foreach x $::I { if {[lindex $x 0] eq $n} { return "I:$n" } }; return NULL } }
proc unknown {cmd args} {
  if {[string match I:* $cmd]} { set n [string range $cmd 2 end]
    foreach k [array names ::S] {}
    switch [lindex $args 0] {
      getPlacementStatus { return [lindex [inst $n] 2] }
      getMaster { return "M:[lindex [inst $n] 1]" }
      swapMaster { set m [string range [lindex $args 1] 2 end]; if {[lindex [inst $n] 3] eq "nosw"} { return 0 }; puts "SWAP $n $m"; set ::I [lmap x $::I { if {[lindex $x 0] eq $n} { lset x 1 $m }; set x }]; return 1 } } }
  if {[string match M:* $cmd]} { if {[lindex $args 0] eq "getName"} { return [string range $cmd 2 end] } }
  error "unknown $cmd $args"
}
proc inst {n} { foreach x $::I { if {[lindex $x 0] eq $n} { return $x } } }
"""


def _run(tmp_path, insts, lock, proc=PROC):
    (tmp_path / "ot_firm_size_lock.txt").write_text("".join(f"{n}\t{m}\n" for n, m in lock))
    body = MOCK % dict(INSTS=" ".join("{" + " ".join(i) + "}" for i in insts))
    script = body + f"set ::env(RESULTS_DIR) {tmp_path}\n" + proc + "\not_firm_size_restore blk\nputs FINAL:$::I\n"
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr + out.stdout
    return out.stdout


X1, X2 = "DFFHQNx1_ASAP7_75t_R", "DFFHQNx2_ASAP7_75t_R"
ROWS = [("g", X2, "FIRM"), ("k", X1, "FIRM"), ("p", X2, "PLACED"), ("z", X2, "FIRM", "nosw")]
LOCK = [("g", X1), ("k", X1), ("p", X1), ("z", X1), ("gone", X1)]


@needs_tcl
def test_restore_swaps_every_grown_listed_cell(tmp_path):
    out = _run(tmp_path, ROWS, LOCK)
    assert out.count("SWAP") == 2 and "SWAP g " + X1 in out and "SWAP p " + X1 in out, out
    assert "restored 2 FIRM cells to their locked master (1 kept it, 2 missing / not swappable)" in out, out


@needs_tcl
def test_no_lock_file_changes_nothing(tmp_path):
    script = MOCK % dict(INSTS="") + f"set ::env(RESULTS_DIR) {tmp_path}\n" + PROC + "\not_firm_size_restore blk\nputs DONE\n"
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert out.returncode == 0 and "SWAP" not in out.stdout and "OT_FIRM_SIZE_LOCK" not in out.stdout and "DONE" in out.stdout


def test_hook_is_called_in_release_before_gen_appended_scans():
    assert REL.count("ot_firm_size_restore $ff_blk") == 1 and "set ff_blk [ord::get_db_block]" in REL
    assert "dont_touch" not in PROC.lower().replace("dont_touch is not", "")


# ---- mutants: each seeded defect must be caught by the tests above ----
MUTANTS = {
    "skip_placed": ('if {[[$i getMaster] getName] eq $mn}', 'if {[$i getPlacementStatus] ne "FIRM" || [[$i getMaster] getName] eq $mn}'),
    "swap_unchanged_again": ('if {[[$i getMaster] getName] eq $mn} { incr same; continue }', ""),
    "ignore_swap_failure": ('if {![$i swapMaster $m]} { incr miss; continue }', "$i swapMaster $m"),
    "wrong_master": ('set m [$db findMaster $mn]', 'set m [$db findMaster DFFHQNx2_ASAP7_75t_R]'),
}


@needs_tcl
@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_mutants_are_caught(tmp_path, name):
    old, new = MUTANTS[name]
    assert old in PROC
    with pytest.raises(AssertionError):
        out = _run(tmp_path, ROWS, LOCK, PROC.replace(old, new))
        assert out.count("SWAP") == 2 and "SWAP g " + X1 in out and "SWAP p " + X1 in out, out
        assert "restored 2 FIRM cells to their locked master (1 kept it, 2 missing / not swappable)" in out, out
