"""output_net_identity.tcl: an output BTerm moved onto a new net (inserted output delay buffer) must not leave the
old internal net carrying the port name, or write_verilog aliases the old driver onto the port (cycle, 566 pads on
SPEPRD3).  Mock ODB API under plain tclsh."""
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).with_name("output_net_identity.tcl")

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
# nets: id name bterms ; bterms: name dir net
array set nname {1 xw_o[0] 2 ot_buf_0_n 3 in_a 4 y_o 5 z_o 6 z_o_new}
array set nbt {1 {} 2 {bt_xw} 3 {bt_in} 4 {bt_y} 5 {} 6 {bt_z}}
array set btn {bt_xw {xw_o[0] OUTPUT 2} bt_in {in_a INPUT 3} bt_y {y_o OUTPUT 4} bt_z {z_o OUTPUT 6}}
proc blk {m args} {
  switch $m {
    getBTerms {return [lsort [array names ::btn]]}
    findNet {foreach id [array names ::nname] {if {$::nname($id) eq [lindex $args 0]} {return net$id}}; return NULL}
  }
}
foreach b [array names btn] {
  proc $b {m} [string map [list @B $b] {
    lassign $::btn(@B) n d id
    switch $m {getName {return $n} getIoType {return $d} getNet {return net$id}}
  }]
}
foreach id [array names nname] {
  proc net$id {m args} [string map [list @I $id] {
    switch $m {getName {return $::nname(@I)} getId {return @I} getBTerms {return $::nbt(@I)}
               rename {set ::nname(@I) [lindex $args 0]}}
  }]
}
'''


def run(extra):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    return subprocess.run(["tclsh"], input=MOCK + f"source {TCL}\n" + extra, text=True, capture_output=True)


def test_renames_only_colliding_internal_nets_and_is_idempotent():
    r = run('set a [ot_output_net_identity]; set b [ot_output_net_identity]\n'
            'puts "RES $a $b $::nname(1) $::nname(2) $::nname(4) $::nname(5) $::nname(6)"\n')
    assert r.returncode == 0, r.stderr
    res = [l for l in r.stdout.splitlines() if l.startswith("RES")][0].split()
    # xw_o[0] (old internal net 1) and z_o (net 5) collide; y_o already on its own net; input untouched
    assert res[1:3] == ["2", "0"]
    assert res[3] == "ot_export_internal_1" and res[4] == "ot_buf_0_n"
    assert res[5] == "y_o" and res[6] == "ot_export_internal_5" and res[7] == "z_o_new"
    assert "OT_OUTPUT_NET_IDENTITY xw_o[0] -> ot_export_internal_1 output_net=ot_buf_0_n" in r.stdout


def test_old_net_still_owning_a_bterm_fails_closed():
    r = run('set ::nbt(1) {bt_other}\ncatch {ot_output_net_identity} e\nputs "ERR $e"\n')
    assert "ERR OT_OUTPUT_NET_IDENTITY conflicting BTerm net" in r.stdout


def test_existing_replacement_name_fails_closed():
    r = run('set ::nname(3) ot_export_internal_1\ncatch {ot_output_net_identity} e\nputs "ERR $e"\n')
    assert "ERR OT_OUTPUT_NET_IDENTITY duplicate ot_export_internal_1" in r.stdout


def test_prd_mk_stages_and_runs_it_before_clock_freeze_assert():
    t = TCL.with_name("prd_mk.sh").read_text()
    assert "output_net_identity.tcl prd_hook.tcl" in t
    i = t.index("echo 'ot_output_net_identity'")
    assert t.index("ot_pg_require_bound post_route_drv") < i < t.index("{ot_clk_freeze_assert post_chain}")
