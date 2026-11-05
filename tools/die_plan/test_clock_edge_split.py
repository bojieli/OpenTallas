"""DIE-QC-75 11-05: plain PHY-edge clocks split by region; forwarded rings, /N clocks and types without such a port stay out."""
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import gen_phys as G

HERE = Path(__file__).parent


def plan(edges):
    return SimpleNamespace(types={"t": {"clock": {"tap_um": [100.0, 100.0], "edge_clocks": edges}}})


def test_ports_filter(monkeypatch):
    edges = [dict(port="clk_coll", tap_um=[1, 1], period_mult=1), dict(port="clk_coll_blk", tap_um=[2, 1], period_mult=6),
             dict(port="fclk_in_ft0_i", tap_um=[3, 1], period_mult=1),
             dict(port="clk_lat", tap_um=[4, 1], period_mult=1, source_latency_ps=[1, 2])]
    monkeypatch.setattr(G, "edge_clock_pins", lambda P, tn: [(e["port"], 0, 0, e["period_mult"]) for e in edges])
    assert G.edge_split_ports(plan(edges), "t") == ["clk_coll"]


def run_split(tmp_path, n_sinks, env):
    """the odb block as a Tcl stub: 2 macros + n flops in a row; prints the OT_EDGE_SPLIT line + connect log"""
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    stub = """
namespace eval ord {}; namespace eval odb {}
proc ord::get_db_block {} {return blk}
proc ord::get_db {} {return db}
proc db {m args} {return master}
proc master {m args} {return {mi mo mp}}
proc mi {m} {switch $m {getSigType {return SIGNAL} getIoType {return INPUT} getName {return A}}}
proc mo {m} {switch $m {getSigType {return SIGNAL} getIoType {return OUTPUT} getName {return Y}}}
proc mp {m} {switch $m {getSigType {return POWER} getIoType {return INPUT} getName {return VDD}}}
proc blk {m args} {switch $m {getInsts {return {}} getDbUnitsPerMicron {return 1000} findBTerm {if {[lindex $args 0] eq {clk_x[0]}} {return bt}; return NULL}}}
proc bbx {m} {return 0}
proc bt {m} {switch $m {getNet {return root} getBBox {return bbx}}}
set ::conn {}
proc root {m} {global its; return $its}
set its {}
proc mkit {name x y blockp} {
  proc $name {m args} "switch \\$m {isInputSignal {return 1} getInst {return ${name}_i} disconnect {} connect {lappend ::conn $name\\[lindex \\$args 0\\]}}"
  proc ${name}_i {m} "switch \\$m {isBlock {return $blockp} getLocation {return {$x $y}}}"
  lappend ::its $name
}
for {set i 0} {$i < %N%} {incr i} { mkit f$i [expr {$i * 100000}] 0 0 }
mkit m0 0 50000 1; mkit m1 10000 50000 1
proc odb::dbInst_create {b ma n} {proc ::$n {m args} {switch $m {findITerm {return nop} setLocation {} setPlacementStatus {}}}; return $n}
proc nop {args} {}
proc odb::dbNet_create {b n} {proc ::$n {m args} {}; return $n}
""".replace("%N%", str(n_sinks))
    e = "".join(f"set ::env({k}) {{{v}}}\n" for k, v in env.items())
    tcl = stub + e + f"source {HERE / 'clock_edge_split.tcl'}\n"
    f = tmp_path / "t.tcl"
    f.write_text(tcl)
    r = subprocess.run(["tclsh", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_split_groups_and_macro_root(tmp_path):
    o = run_split(tmp_path, 40, dict(OT_EDGE_SPLIT_PORTS="clk_x", OT_EDGE_SPLIT_MAX_SINKS=10, OT_EDGE_SPLIT_SPAN_UM=100000))
    assert "40 register sinks + 2 macro" in o and "5 roots" in o and "m0:2@" in o


def test_small_domain_left_alone(tmp_path):
    o = run_split(tmp_path, 3, dict(OT_EDGE_SPLIT_PORTS="clk_x", OT_EDGE_SPLIT_MAX_SINKS=10, OT_EDGE_SPLIT_SPAN_UM=100000))
    assert "one group, left alone" in o


def test_off_switch_and_unset(tmp_path):
    assert run_split(tmp_path, 40, dict(OT_EDGE_SPLIT_PORTS="clk_x", OT_EDGE_SPLIT=0)) == ""
    assert run_split(tmp_path, 40, {}) == ""
