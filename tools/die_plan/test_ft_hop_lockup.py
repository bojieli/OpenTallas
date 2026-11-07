"""TYPE-SAFE-1 11-06 (OWNER 18:5x): structurally hold-safe ft station hops = a negative-level lockup latch (ot_dp_lk)
between station k and k+1 (plan clock.ft_hop_lockup), clocked from the LAUNCH station's tap (clock_taps.tcl) and placed
at the hop midpoint (face_flops.tcl).  Covers: the plan switch, the bound / gen RTL, strict bind proof (bind_verify
transport stages 0), the REAL face_flops.tcl walkers + latch pass (tclsh, OpenDB mocked), the REAL clock_taps.tcl
follow-D pass, and an iverilog lock-step bench of the latched chain against the plain chain with mutants."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import gen_rtl  # noqa: E402

EX = HERE / "examples" / "bind_tiny"


def test_plan_switch():
    f = gen_rtl.ft_hop_lockup
    assert not f({}, "t") and not f({"clock": {}}, "t")
    assert f({"clock": {"ft_hop_lockup": {"all": True}}}, "t")
    assert not f({"clock": {"ft_hop_lockup": {"all": True, "except": ["t"]}}}, "t")
    assert f({"clock": {"ft_hop_lockup": {"types": ["t"]}}}, "t") and not f({"clock": {"ft_hop_lockup": {"types": ["u"]}}}, "t")
    assert bind.ft_hop_lockup({"clock": {"ft_hop_lockup": {"types": ["t"]}}}, "t")


def test_bind_cell_is_gen_rtl_cell():
    c = bind.ft_hop_lockup_cell()
    assert c in gen_rtl.CELLS and "module ot_dp_lk" in c and "if (!clk) q = d;" in c and "keep_hierarchy" in c


# ------------------------------------------------------------------ bind end to end (needs Yosys like test_bind.py)
HAVE_YOSYS = bool(shutil.which("docker")) or bool(__import__("os").environ.get("OT_BIND_YOSYS"))


@pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys")
@pytest.mark.parametrize("on", [False, True])
def test_bind_ft_hop_latches_prove(tmp_path, on):
    P = json.loads((EX / "die_plan_lanes.json").read_text())
    P["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    P["latency"]["lanes"]["a0y"].update(cycles=5, stations=3)   # the plan lane through tf carries the 2 extra stations
    if on:
        P.setdefault("clock", {})["ft_hop_lockup"] = {"types": ["tf"]}
    P["asbuilt"]["base"] = str(EX)
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(P))
    out = tmp_path / "o"
    for c in ("elab", "bind", "verify"):
        rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
        if rc:
            break
    ft = (out / "rtl" / "bt_tf.sv").read_text()
    cells = (out / "rtl" / "bind_cells.sv").read_text()
    if on:
        assert ft.count("ot_dp_lk #(.W(9))") == 2 and "u_fl_y_o_0" in ft and "u_fl_y_o_1" in ft, ft
        assert "u_fl_y_o_2" not in ft                       # no latch after the last station (out face)
        assert "module ot_dp_lk" in cells
    else:
        assert "ot_dp_lk" not in ft and "module ot_dp_lk" not in cells
    assert ft.count("ot_dp_st #(.W(8))") == 3
    v = json.loads((out / "verify_report.json").read_text())
    assert rc == 0 and v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0, v.get("mismatches", [])[:3]


# ------------------------------------------------------------------ face_flops.tcl walkers + hop-latch pass
FF = (HERE / "face_flops.tcl").read_text()
MOCK = r'''
proc object {name entries} {
 set ::props($name) $entries
 proc $name {method args} {return [dict get [set ::props([lindex [info level 0] 0])] $method]}
}
proc mt {name io sig nm} { object $name [dict create getIoType $io getSigType $sig getName $nm] }
mt mi INPUT SIGNAL A; mt mo OUTPUT SIGNAL Y; mt mD INPUT SIGNAL D; mt mQ OUTPUT SIGNAL QN; mt mC INPUT CLOCK CLK
mt mLQ OUTPUT SIGNAL Q
foreach {m n} {mff DFFHQNx1_ASAP7_75t_R mbuf BUFx2_ASAP7_75t_R minv INVx1_ASAP7_75t_R mlat DLLx1_ASAP7_75t_R} {
 object $m [dict create getName $n getWidth 1080]
}
proc conn {net it} { lappend ::nets($net) $it; object $net [dict create getITerms $::nets($net)] }
proc cell {name master ins outs} {
 set its {}
 foreach {pin net} $ins { set it ${name}.$pin; object $it [dict create getInst $name getMTerm [expr {$pin eq "D" ? "mD" : ($pin eq "CLK" ? "mC" : "mi")}] getSigType [expr {$pin eq "CLK" ? "CLOCK" : "SIGNAL"}] getNet $net]; conn $net $it; lappend its $it }
 foreach {pin net} $outs { set it ${name}.$pin; object $it [dict create getInst $name getMTerm [expr {$pin eq "QN" ? "mQ" : ($pin eq "Q" ? "mLQ" : "mo")}] getSigType SIGNAL getNet $net]; conn $net $it; lappend its $it }
 object $name [dict create getName $name getMaster $master getITerms $its getLocation {0 0}]
 lappend ::insts $name
}
proc bbox {name x y} { object $name [dict create xMin $x xMax $x yMin $y yMax $y] }
# slot tx: k=3, W face -> E face, pins at y=50 um, frame 0..300 um; s0 -> INV -> L0 -> s1 -> BUF -> L1 -> s2 -> out
proc design {latched pfx} {
 set ::insts {}
 cell buf_in mbuf {A n_in} {Y n_b}
 cell "${pfx}u_ft_tx_s0/q\[0\]\$_DFF_P_" mff {D n_b CLK clk} {QN n_s0}
 cell inv01 minv {A n_s0} {Y n_s0b}
 if {$latched} { cell "${pfx}u_fl_tx_s0/q\[0\]\$_DLATCH_N_" mlat {D n_s0b CLK clk} {Q n_l0}; set d1 n_l0 } else { set d1 n_s0b }
 cell "${pfx}u_ft_tx_s1/q\[0\]\$_DFF_P_" mff [list D $d1 CLK clk] {QN n_s1}
 cell buf12 mbuf {A n_s1} {Y n_s1b}
 if {$latched} { cell "${pfx}u_fl_tx_s1/q\[0\]\$_DLATCH_N_" mlat {D n_s1b CLK clk} {Q n_l1}; set d2 n_l1 } else { set d2 n_s1b }
 cell "${pfx}u_ft_tx_s2/q\[0\]\$_DFF_P_" mff [list D $d2 CLK clk] {QN n_out}
 bbox bbi 0 50000; bbox bbo 300000 50000
 object bti [dict create getSigType SIGNAL getIoType INPUT getName {tx_i[0]} getNet n_in getBBox bbi]
 object bto [dict create getSigType SIGNAL getIoType OUTPUT getName {tx_o[0]} getNet n_out getBBox bbo]
 object blk [dict create getBTerms {bti bto} getInsts $::insts]
 proc blk {method args} { if {$method eq "findBTerm"} { return [expr {[lindex $args 0] eq {tx_o[0]} ? "bto" : "NULL"}] }; return [dict get $::props(blk) $method] }
}
set ff_blk blk; set ff_dbu 1000; set ff_out stdout
'''


def _procs(src):
    out = []
    for m in re.finditer(r"^proc (\w+) \{", src, re.M):
        i = m.start(); depth = 0; groups = 0; k = src.index("{", i)
        while groups < 2:
            if src[k] == "{":
                depth += 1
            elif src[k] == "}":
                depth -= 1
                if depth == 0:
                    groups += 1
            k += 1
        out.append(src[i:k])
    return "\n".join(out)


def _ff_run(latched, pfx="", extra=""):
    a = FF.index("set ff_st 0; set ff_st_miss 0")
    passes = FF[a:FF.index("close $ff_out", a)]
    body = (MOCK + _procs(FF) + "\n"
            + "proc ff_put_near {f x y} { dict set ::props($f) getLocation [list [expr {round($x)}] [expr {round($y)}]]; "
              "return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + f"design {int(latched)} {{{pfx}}}\nset ff_done {{}}\nset ff_ft [dict create tx [list 3 W E {{}}]]\n"
            + extra + passes
            + '\nputs "RESULT st=$ff_st miss=$ff_st_miss hl=$ff_hl hlmiss=$ff_hl_miss"\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
@pytest.mark.parametrize("pfx", ["", "u_bound."])
def test_face_flops_walks_through_hop_latch_and_places_it_mid_hop(pfx):
    out = _ff_run(True, pfx)
    assert "RESULT st=2 miss=0 hl=2 hlmiss=0" in out, out
    st = {r[1]: float(r[2]) for r in (ln.split("\t") for ln in out.splitlines()) if r[1:2] and r[1].startswith("st")}
    assert st == {"st1": 100.0, "st2": 200.0}, out
    hl = [ln.split("\t") for ln in out.splitlines() if "\thl\t" in ln]
    # L0 between s0 (station 0 stays where the face pass put it: mock origin 0) and s1 (100 um); L1 between s1 and s2
    assert [(r[0].split("/")[0], float(r[2])) for r in hl] == [(f"{pfx}u_fl_tx_s0", 50.0), (f"{pfx}u_fl_tx_s1", 150.0)], hl


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_face_flops_unlatched_unchanged():
    out = _ff_run(False)
    assert "RESULT st=2 miss=0 hl=0 hlmiss=0" in out, out
    assert "hop latches" not in out


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_landed_backward_walk_passes_the_latch():
    tcl = (MOCK + _procs(FF) + "\ndesign 1 {}\n"
           + "set f [ff_d_driver {u_ft_tx_s2/q[0]$_DFF_P_}]\nputs \"D2=$f\"\n"
           + "set g [ff_d_driver $f]\nputs \"D1=$g\"\n")
    r = subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True)
    assert "D2=u_ft_tx_s1/q[0]$_DFF_P_" in r.stdout and "D1=u_ft_tx_s0/q[0]$_DFF_P_" in r.stdout, r.stdout + r.stderr


# ------------------------------------------------------------------ iverilog lock-step bench + mutants
BENCH = r'''
`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0; reg [8:0] din;
  wire [8:0] g, m;
  gold u_g (.clk(clk), .rst_n(rst_n), .i(din), .o(g));
  dut  u_m (.clk(clk), .rst_n(rst_n), .i(din), .o(m));
  integer c, bad = 0;
  always #5 clk = ~clk;
  initial begin
    din = 0;
    #12 rst_n = 1;
    for (c = 0; c < 400; c = c + 1) begin
      @(negedge clk); din = $random;
      @(posedge clk); #1 if (g !== m) bad = bad + 1;
    end
    if (bad) $display("MISMATCH %0d", bad); else $display("LOCKSTEP PASS");
    $finish;
  end
endmodule
'''


def _chain(name, k, lk, mutant=None):
    W = 8
    s = [f"module {name} (input wire clk, input wire rst_n, input wire [{W}:0] i, output wire [{W}:0] o);"]
    prev = "i"
    for j in range(k):
        nxt = "o" if j == k - 1 else f"s{j}"
        if j < k - 1:
            s.append(f"  wire [{W}:0] {nxt};")
        s.append(f"  ot_dp_st #(.W({W})) u_ft_{j} (.clk(clk), .rst_n(rst_n), .d({prev}[{W - 1}:0]), .ea({prev}[{W}]), "
                 f".q({nxt}[{W - 1}:0]), .eq({nxt}[{W}]));")
        prev = nxt
        if lk and j < k - 1:
            s.append(f"  wire [{W}:0] {nxt}_l;")
            if mutant == "flop" and j == 0:       # a flop instead of the latch: +1 cycle
                s.append(f"  reg [{W}:0] r{j}; always @(posedge clk) r{j} <= {nxt}; assign {nxt}_l = r{j};")
            elif mutant == "swap" and j == 0:     # two bits swapped through the latch
                s.append(f"  ot_dp_lk #(.W({W + 1})) u_fl_{j} (.clk(clk), .d({{{nxt}[{W}:2], {nxt}[0], {nxt}[1]}}), .q({nxt}_l));")
            elif mutant == "noepoch" and j == 0:  # epoch bit not latched (tied)
                s.append(f"  ot_dp_lk #(.W({W})) u_fl_{j} (.clk(clk), .d({nxt}[{W - 1}:0]), .q({nxt}_l[{W - 1}:0])); "
                         f"assign {nxt}_l[{W}] = 1'b1;")
            else:
                s.append(f"  ot_dp_lk #(.W({W + 1})) u_fl_{j} (.clk(clk), .d({nxt}), .q({nxt}_l));")
            prev = f"{nxt}_l"
    s.append("endmodule")
    return "\n".join(s) + "\n"


def _cells():
    c = gen_rtl.CELLS
    return "\n".join(re.search(rf"((?:\(\*[^\n]*\*\)\n)*module {m}\b.*?\nendmodule\n)", c, re.S).group(1)
                     for m in ("ot_dp_st", "ot_dp_lk")) if "module ot_dp_st " in c or "module ot_dp_st #" in c else c


@pytest.mark.skipif(not shutil.which("iverilog"), reason="no iverilog")
@pytest.mark.parametrize("mutant,expect", [(None, "LOCKSTEP PASS"), ("flop", "MISMATCH"), ("swap", "MISMATCH"),
                                            ("noepoch", "MISMATCH")])
def test_lockstep_bench_and_mutants(tmp_path, mutant, expect):
    src = tmp_path / "t.v"
    src.write_text("`timescale 1ns/1ps\n" + _cells().replace("`default_nettype none", "") + _chain("gold", 4, False)
                   + _chain("dut", 4, True, mutant) + BENCH)
    r = subprocess.run(["iverilog", "-o", str(tmp_path / "a.out"), str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(["vvp", str(tmp_path / "a.out")], capture_output=True, text=True)
    assert expect in r.stdout, r.stdout + r.stderr


def test_gen_rtl_wrapper_emits_hop_latches():
    """the gen_rtl station loop text: a latch after every station but the last, the next station reads it"""
    src = (HERE / "gen_rtl.py").read_text()
    assert "lk = ft_hop_lockup(P.raw, tn)" in src and "u_fl_{n}_s{j}" in src
