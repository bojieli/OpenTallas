"""tests of rst_reach_placed.py (C-LEG405-R3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rst_reach_placed as R  # noqa: E402

TCL = """rtr_place rst_root_n {u_bound[./]u_rst_in[./]*} 0.000 0.000 rentry
rtr_place rst_rl_0 {u_bound[./]u_rrl_0[./]*} 275.000 0.000 rrl:pad1
rtr_place rst_rl_1 {u_bound[./]u_rrl_1[./]*} 550.000 0.000 rrl:pad2
rtr_place rst_rl_2 {u_bound[./]u_rrl_2[./]*} 700.000 0.000 rrl:pad3
foreach {q d} {rst_rl_0 rst_root_n rst_rl_1 rst_rl_0 rst_rl_2 rst_rl_1 } {
"""


def ff(x1, x2):
    return (f"u_bound.u_rst_in/q$_DFF_P_\trentry\t0\t0\t-\nu_bound.u_rrl_0/q$_DFF_P_\trrl:pad1\t275\t0\t-\n"
            f"u_bound.u_rrl_1/q$_DFF_P_\trrl:pad2\t{x1}\t0\t-\nu_bound.u_rrl_2/q$_DFF_P_\trrl:pad3\t{x2}\t0\t-\n")


def test_pass_and_fail_trees_have_the_same_plan_hop_but_different_placed_hop():
    ok, bad = R.tree_report(TCL, ff(550, 700)), R.tree_report(TCL, ff(590, 700))
    assert ok["plan_max"] == bad["plan_max"] == 275.0
    assert ok["verdict"] == "PASS" and bad["verdict"] == "FAIL" and bad["placed_max"] == 315.0
    f = bad["failing"][0]
    assert (f["plan_hop"], f["placed_hop"], f["drift_q"]) == (275.0, 315.0, 40.0)


def test_headroom_term_counts_near_cap_edges():
    r = R.tree_report(TCL, ff(550, 700))
    assert r["near_cap_edges"] == 2 and r["expected_fails"] > 0
    assert R.expected_fails([200.0, 250.0]) == 0 and R.expected_fails([275.0]) > R.expected_fails([266.0]) * 0.99


def test_unmeasured_without_placed_rows():
    assert R.tree_report(TCL, "")["verdict"] == "UNMEASURED"


def test_gate_is_the_kit_own_rtr_lim_not_the_kv_300():
    # HEAD kit: rtr_lim 405.  A 315 um placed hop FAILs against 300 (KV) but PASSes against the kit's own 405 gate.
    tcl = TCL + "set rtr_lim [expr {405 * $ff_dbu}]\n"
    assert R.kit_gate_um(tcl) == 405.0 and R.kit_gate_um(TCL) == 300.0
    assert R.tree_report(TCL, ff(590, 700))["verdict"] == "FAIL"
    r = R.tree_report(tcl, ff(590, 700), R.kit_gate_um(tcl))
    assert r["verdict"] == "PASS" and r["gate_um"] == 405.0
    assert R.tree_report(tcl, ff(590, 1000), 405.0)["verdict"] == "FAIL"


def test_plan_gate_reads_reset_reach_cap_um_else_300(tmp_path):
    assert R.plan_gate_um({"reset": {"reach_cap_um": 405}}) == 405.0
    assert R.plan_gate_um({"reset": {}}) == 300.0 and R.plan_gate_um({}) == 300.0 and R.plan_gate_um(None) == 300.0
    p = tmp_path / "plan.json"
    p.write_text('{"partition_types": {}, "reset": {"reach_cap_um": 405}}')
    assert R.plan_gate_um(str(p)) == 405.0
    assert R.plan_gate_um(str(tmp_path / "missing.json")) == 300.0


def test_gen_report_gate_order_kit_then_plan_then_300(tmp_path):
    g = tmp_path / "g"
    (g / "run/results/a/b/base").mkdir(parents=True)
    (g / "run/results/a/b/base/ot_face_flops.txt").write_text(ff(590, 700))
    # no rtr_lim in the kit: the plan's 405 applies (315 um placed hop PASSes), else 300 (FAIL)
    (g / "reset_tree.tcl").write_text(TCL)
    assert R.gen_report(str(g))["verdict"] == "FAIL"
    assert R.gen_report(str(g), 405.0)["verdict"] == "PASS" and R.gen_report(str(g), 405.0)["gate_um"] == 405.0
    # the kit's own rtr_lim wins over the plan cap
    (g / "reset_tree.tcl").write_text(TCL + "set rtr_lim [expr {300 * $ff_dbu}]\n")
    assert R.gen_report(str(g), 405.0)["gate_um"] == 300.0
