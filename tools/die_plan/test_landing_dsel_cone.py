"""HEAD-TOOLS-RINGDSEL (ALLFIX-HEAD C5): opt-in band key dsel_cone places the u_dsel AND-OR cone FIRM behind its y flop."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_place as LP  # noqa: E402
from test_landing_place_spread import _P  # noqa: E402

TCL = (HERE / "landing_placement.tcl").read_text()
R = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i", "ring_place": "ff"}


def test_plan_key_emits_prefix_list_only_when_set():
    assert "cland_dsel_cone" not in LP.tcl(_P({"i": dict(R)}), "t").split("proc cland_group_insts")[0]
    out = LP.tcl(_P({"i": dict(R, dsel_cone=True), "j": dict(R, instance="u_cland_j")}), "t")
    assert "set cland_dsel_cone {u_cland_i}\n" in out
    # absent key: the plan-generated text is byte-identical to before (default {} comes from the placement source)
    assert LP._dsel_cone_tcl({"bands": {"i": dict(R)}}) == ""


def test_plan_key_fails_closed():
    with pytest.raises(ValueError):
        LP.tcl(_P({"i": dict(R, dsel_cone="yes")}), "t")
    with pytest.raises(ValueError):
        LP.tcl(_P({"i": {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i", "dsel_cone": True}}), "t")


def test_place_ff_hook_is_wired_and_fails_closed():
    assert "if {![info exists cland_dsel_cone]} { set cland_dsel_cone {} }" in TCL
    assert "lappend combinsts $i; continue" in TCL
    assert "[lsearch -exact $::cland_dsel_cone $prefix] >= 0" in TCL
    assert "OT_CLAND dsel_cone requested for $prefix but no u_dsel AND-OR cone cell reaches a keyed y flop" in TCL
    # the cone area is part of the band fill need, before the spread is derived
    assert TCL.index("u_dsel AND-OR cone cells FIRM") < TCL.index("set sp [expr {max(1.0,$cland_ff_fill*$barea")


def _assign(combs, fanout, ykeys):
    proc = re.search(r"proc cland_dsel_cone_assign \{combs fanout ykeys\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    fo = " ".join("{%s} {%s}" % (k, " ".join("{%s}" % x for x in v)) for k, v in fanout.items())
    yk = " ".join("{%s} {%s}" % kv for kv in ykeys.items())
    body = proc + "set r [cland_dsel_cone_assign {%s} [dict create %s] [dict create %s]]\n" % (
        " ".join("{%s}" % c for c in combs), fo, yk) + "foreach e $r { puts [join $e \"\\t\"] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.strip().split("\n")
    return dict(l.split("\t") for l in out if l)


S0 = "u/ring.dch[0].u_dsel/"
S1 = "u/ring.dch[1].u_dsel/"
Y0, Y1 = S0 + "y[3]$_DFF_P_", S1 + "y[3]$_DFF_P_"
K0, K1 = "u/ring.s_d|000000003|999999998|y0", "u/ring.s_d|000000067|999999998|y1"


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_cone_cells_key_right_behind_their_y_flop():
    a, b, o = S0 + "_1_", S0 + "_2_", S0 + "_3_"
    got = _assign([a, b, o], {a: [o], b: [o], o: [Y0]}, {Y0: K0})
    assert got == {c: "u/ring.s_d|000000003|999999999|" + c for c in (a, b, o)}
    # sorts after the y flop's own key and before the next bit
    assert K0 < got[o] < "u/ring.s_d|000000004|000000000|x"


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_other_scope_dead_end_and_deep_cells_are_left_alone():
    a, x, dead = S0 + "_1_", S1 + "_9_", S0 + "_dead_"
    # a feeds the other chunk's y only (scope mismatch); dead drives a non-y sequential; x belongs to chunk 1
    got = _assign([a, x, dead], {a: [Y1], dead: ["u/other/ff"], x: [Y1]}, {Y0: K0, Y1: K1})
    assert list(got) == [x] and got[x].startswith("u/ring.s_d|000000067|999999999|")
    chain = [S0 + "_c%d_" % i for i in range(8)]
    fo = {chain[i]: [chain[i + 1]] for i in range(7)}
    fo[chain[7]] = [Y0]
    got = _assign(chain, fo, {Y0: K0})
    assert set(got) == set(chain[2:])      # more than 6 comb levels from the y flop: not part of the cone


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_cell_reaching_two_y_flops_takes_the_lowest_key():
    Ya, Yb = S0 + "y[1]$_DFF_P_", S0 + "y[2]$_DFF_P_"
    a = S0 + "_s_"
    got = _assign([a], {a: [Yb, Ya]}, {Ya: "b|000000001|999999998|a", Yb: "b|000000002|999999998|b"})
    assert got[a] == "b|000000001|999999999|" + a


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_db_wrapper_walks_nets_and_pairs_cells_with_instances():
    # mock odb objects: inst/iterm/net commands; a -> o -> y(D); o's net also feeds a non-y flop
    procs = "".join(re.search(r"proc %s \{.*?\n\}\n" % n, TCL, re.S).group(0)
                    for n in ("cland_dsel_cone_assign", "cland_dsel_cone_cells"))
    mock = r'''
proc mkinst {id name its} { proc $id {cmd} "switch \$cmd getName {return {$name}} getITerms {return {$its}}" }
proc mkit {id out net inst} { proc $id {cmd} "switch \$cmd isOutputSignal {return $out} isInputSignal {return [expr {!$out}]} getNet {return {$net}} getInst {return {$inst}}" }
proc mknet {id its} { proc $id {cmd} "switch \$cmd getITerms {return {$its}}" }
set s {u/r.dch\[0\].u_dsel/}
mkinst ia "${s}_a_" {ia_o}; mkit ia_o 1 na ia
mkinst io "${s}_o_" {io_i io_o}; mkit io_i 0 na io; mkit io_o 1 no io
mkinst iy "${s}y\[3\]\$_DFF_P_" {iy_d}; mkit iy_d 0 no iy
mkinst ix "u/other/ff" {ix_d}; mkit ix_d 0 no ix
mknet na {ia_o io_i}; mknet no {io_o iy_d ix_d}
set r [cland_dsel_cone_cells {ia io} [list [list "u/r.s_d|000000003|999999998|y" iy]]]
foreach e $r { puts "[lindex $e 0] [[lindex $e 1] getName]" }
'''
    out = subprocess.run(["tclsh"], input=procs + mock, capture_output=True, text=True, check=True).stdout.strip().split("\n")
    assert len(out) == 2 and {l.split()[1].split("/")[-1] for l in out} == {"_a_", "_o_"}
    assert all(l.startswith("u/r.s_d|000000003|999999999|") for l in out)
