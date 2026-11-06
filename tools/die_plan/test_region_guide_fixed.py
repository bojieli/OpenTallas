"""KW-FIX-23 (COORD 12:4x, s81 slice_station__t52 a14): every guide instance present but already FIRM (OT_CLAND placed
them in reserved bands) is a no-op guide, not a stale one; only 'no listed instance exists' stays an error."""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
STUB = r'''
namespace eval ord {proc get_db_block {} {return blk}; proc get_db_tech {} {return tech}}
proc tech {m} {return 1000}
proc blk {m args} {switch $m {findInst {set n [lindex $args 0]; if {$n in $::have} {return ins} {return NULL}} getInsts {return {}}}}
proc ins {m args} {switch $m {getMaster {return mst} getPlacementStatus {return FIRM} getGroup {return NULL}}}
proc mst {m args} {switch $m {isCore {return 1}}}
set ::have [lindex $argv 1]
if {[catch {source [lindex $argv 0]} e]} {puts "ERR $e"} else {puts OK}
'''


def run(tmp_path, have):
    (tmp_path / "region_guide.tsv").write_text("R\trg_a\t0\t0\t10\t10\nI\trg_a\tu_x/q_reg\nI\trg_a\tu_y/q_reg\n")
    (tmp_path / "region_guide.tcl").write_text((HERE / "region_guide.tcl").read_text())
    (tmp_path / "stub.tcl").write_text(STUB)
    r = subprocess.run(["tclsh", str(tmp_path / "stub.tcl"), str(tmp_path / "region_guide.tcl"), have],
                       capture_output=True, text=True, timeout=60)
    return r.stdout


def test_all_fixed_is_no_op(tmp_path):
    out = run(tmp_path, "u_x/q_reg u_y/q_reg")
    assert "fixed/grouped skipped 2" in out and out.strip().endswith("OK")


def test_none_present_still_stale(tmp_path):
    assert "ERR OT_REGION_GUIDE: no spec instance matched the design (stale guide)" in run(tmp_path, "nothing")
