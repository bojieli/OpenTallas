"""FLOW-CLASS-25 11-06 (COORD 18:0x (3a), DIE-HBM-82-Q3EL 15:46): the routed-SPEF re-read of prd_hook.tcl skips the
SPEF section of every net whose connectivity the ECO changed (STA-1651 class: a split net lost its routed wire delay,
false FF hold -33 ps, 1900 hold buffers); unchanged nets keep the routed SPEF; OT_PRD_SPEF_CHANGED=reread = old."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

SPEF = """*SPEF "ieee 1481-1999"
*DESIGN "hc_x"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]

*NAME_MAP
*1 n_long
*2 n_keep
*3 dq\\[69\\]
*4 _1_

*PORTS
*3 I

*D_NET *1 0.5
*CONN
*I *4:Y O
*I u_ff:D I
*CAP
1 *1:1 0.5
*END

*D_NET *2 0.25
*CONN
*I *4:A I
*END

*D_NET *3 0.75
*CONN
*P *3 I
*I u_sram:wd_in I
*END

*D_NET plain_net 0.1
*CONN
*END
"""


def _procs():
    s = (HERE / "prd_hook.tcl").read_text()
    a = s.index("proc ot_prd_spef_read")
    b = s.index("\nproc ot_prd_spef_arm")
    e = s.index("\n}\n", s.index("proc ::estimate_parasitics", b)) + 3
    return s[a:e]


# mock OpenDB: nets with iterm ids; split_net moves terms like repair_design buffering; read_spef records the D_NETs
MOCK = r"""
set ::nets [dict create n_long {1 2 3} n_keep {4} {dq\[69\]} {5} plain_net {6} vdd {}]
set ::sig [dict create vdd POWER]
proc mknet {name} {
  set h net_[incr ::nid]
  dict set ::h2n $h $name
  proc $h {m args} "netm [list $name] \$m"
  return $h
}
proc netm {name m} {
  switch $m {
    getName {return $name}
    getSigType {return [expr {[dict exists $::sig $name] ? [dict get $::sig $name] : "SIGNAL"}]}
    getITerms {return [lmap i [dict get $::nets $name] {set _ it_$i}]}
    getBTerms {return {}}
  }
}
proc it_handle {i} { proc it_$i {m} "return $i" }
for {set i 1} {$i < 100} {incr i} { it_handle $i }
proc block {m args} {
  switch $m {
    getNets {return [lmap n [dict keys $::nets] {mknet $n}]}
    findNet {set n [lindex $args 0]; return [expr {[dict exists $::nets $n] ? [mknet $n] : "NULL"}]}
  }
}
namespace eval ord { proc get_db_block {} { return block } }
proc read_spef {args} {
  set f [lindex $args end]
  set fh [open $f r]; set t [read $fh]; close $fh
  set d [regexp -all -inline -line {^\*D_NET \S+} $t]
  puts "READ [lrange $args 0 end-1] [file tail $f] [llength $d] {$d}"
}
proc estimate_parasitics {args} { puts "EST $args" }
"""


def _run(tmp_path, body, env=""):
    spef = tmp_path / "6_final.spef"
    spef.write_text(SPEF)
    tcl = MOCK + env + _procs() + f"ot_prd_spef_arm {spef}\n" + body + \
        "puts LEFT[llength [glob -nocomplain -dir [file dirname " + "{" + str(spef) + "}" + "] ot_prd_eco_*]]\n"
    with open(tmp_path / "t.tcl", "w") as f:
        f.write(tcl)
    r = subprocess.run(["tclsh", str(tmp_path / "t.tcl")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


SPLIT = "dict set ::nets n_long {1 7}\ndict set ::nets n_buf {8 2 3}\n"   # buffer 7->8 inserted on n_long


def test_unchanged_session_rereads_everything(tmp_path):
    out = _run(tmp_path, "estimate_parasitics -placement\n")
    reads = [l for l in out.splitlines() if l.startswith("READ")]
    assert len(reads) == 2 and all(" 6_final.spef 4 " in l for l in reads)
    assert "connectivity of 4 signal nets recorded" in out and "LEFT0" in out


def test_split_net_keeps_estimate_others_keep_routed_spef(tmp_path):
    out = _run(tmp_path, SPLIT + "dict set ::nets {dq\\[69\\]} {9}\nestimate_parasitics -placement\n")
    reads = [l for l in out.splitlines() if l.startswith("READ")]
    assert " 4 " in reads[0]
    last = reads[-1]
    assert "ot_prd_eco_" in last and " 2 " in last and "*D_NET *2" in last and "*D_NET plain_net" in last
    assert "*D_NET *1" not in last and "*D_NET *3" not in last   # escaped name (dq\[69\]) matched via the name map
    assert "2 ECO-changed nets keep the estimate (2 routed SPEF nets skipped)" in out
    assert out.index("EST -placement") < out.index(last)
    assert "LEFT0" in out                                        # the filtered copy is removed after the read


def test_two_mode_reads_the_same_filtered_copy_in_both_scenes(tmp_path):
    env = "set ::ot_mm_active 1\nproc ot_mm_sc {} { return WC }\n"
    out = _run(tmp_path, SPLIT + "estimate_parasitics -global_routing\n", env=env)
    reads = [l for l in out.splitlines() if l.startswith("READ")]
    assert reads[-2].startswith("READ -corner WC ot_prd_eco_") and reads[-1].startswith("READ -corner BC ot_prd_eco_")
    assert all(" 3 " in r for r in reads[-2:])


def test_opt_out_rereads_changed_nets(tmp_path):
    out = _run(tmp_path, SPLIT + "estimate_parasitics -placement\n", env="set ::env(OT_PRD_SPEF_CHANGED) reread\n")
    reads = [l for l in out.splitlines() if l.startswith("READ")]
    assert all(" 6_final.spef 4 " in l for l in reads) and "OT_PRD_SPEF_CHANGED=reread" in out


def test_removed_net_is_skipped_too(tmp_path):
    out = _run(tmp_path, "dict unset ::nets n_keep\nestimate_parasitics -placement\n")
    last = [l for l in out.splitlines() if l.startswith("READ")][-1]
    assert " 3 " in last and "*D_NET *2" not in last
