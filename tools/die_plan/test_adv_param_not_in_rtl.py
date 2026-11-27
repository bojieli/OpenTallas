"""pytest: ADV-PARAM-NOT-IN-RTL (P-PLAN-AHEAD-OF-RTL): the S81 WREG row case (6 types set WREG, the leaf RTL lacks it)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_param_not_in_rtl as A  # noqa: E402

LEAF_NOW = """// as-built leaf: no WREG yet
module ot_s81sl_vpw #(parameter integer W = 8, parameter DEPTH = 4, parameter [3:0] MODE = 4'd1,
                      parameter string TAG = "x") (input clk, input [W-1:0] d, output [W-1:0] q);
  localparam LP = 3;
endmodule
module ot_other #(parameter A = 1) (input clk); endmodule
"""
LEAF_LANDED = LEAF_NOW.replace("parameter DEPTH = 4,", "parameter DEPTH = 4, parameter WREG = 0,")


def _plan(n_types=6, param="WREG", module="ot_s81sl_vpw"):
    pt = {f"t{i}": dict(leaf_params=[dict(module=module, params={param: 1})]) for i in range(n_types)}
    pt["clean"] = {"module": "m"}
    return {"partition_types": pt}


def _tree(tmp_path, rtl):
    d = tmp_path / "tree" / "rtl" / "dsrom_sys"
    d.mkdir(parents=True)
    (d / "leaf.sv").write_text(rtl)
    return str(tmp_path / "tree")


def test_wreg_row_six_types_missing(tmp_path):
    out = A.findings(_plan(6), "p.json", tree=_tree(tmp_path, LEAF_NOW))
    assert len(out) == 2
    assert "ot_s81sl_vpw.WREG: PARAM-NOT-IN-RTL" in out[0] and "6 type rule(s)" in out[0]
    assert "6 type rule(s) set a parameter the RTL does not declare" in out[-1]
    assert all(x.startswith("WARN ADV-PARAM-NOT-IN-RTL") for x in out)


def test_rtl_landed_is_clean(tmp_path):
    out = A.findings(_plan(6), "p.json", tree=_tree(tmp_path, LEAF_LANDED))
    assert len(out) == 1 and "0 type rule(s) set a parameter" in out[0]


def test_declared_params_all_forms(tmp_path):
    tree = _tree(tmp_path, LEAF_NOW)
    for p in ("W", "DEPTH", "MODE", "TAG"):
        assert "0 type rule(s) set" in A.findings(_plan(2, p), "p", tree=tree)[-1], p


def test_asbuilt_declare_and_netlist_count(tmp_path):
    tree = _tree(tmp_path, LEAF_NOW)
    (tmp_path / "nl.v").write_text("ot_s81sl_vpw #(.W(4), .WREG(1)) u_x (.clk(c));\n")
    ab = tmp_path / "ab.json"
    ab.write_text(json.dumps({"netlist": ["nl.v"], "base": ".", "param_regen": {"declare": {"ot_other": {"ZB": 0}}}}))
    assert "0 type rule(s) set" in A.findings(_plan(3), "p", tree=tree, asbuilt=str(ab))[-1]      # NETLIST declares WREG
    assert "0 type rule(s) set" in A.findings(_plan(3, "ZB", "ot_other"), "p", tree=tree, asbuilt=str(ab))[-1]   # DECLARE
    assert "PARAM-NOT-IN-RTL" in A.findings(_plan(1, "NOPE"), "p", tree=tree, asbuilt=str(ab))[0]


def test_unknown_master_not_checked_never_clean(tmp_path):
    out = A.findings(_plan(2, module="ot_nope"), "p", tree=_tree(tmp_path, LEAF_NOW))
    assert "ot_nope: NOT-CHECKED" in out[0] and "1 master(s) not checked" in out[-1]


def test_no_leaf_params_silent():
    assert A.findings({"partition_types": {"t": {"module": "m"}}}, "p", tree=None) == []


def test_registered_in_plan_advisory():
    import plan_advisory as PA
    assert ("PARAM-NOT-IN-RTL", "adv_param_not_in_rtl") in PA.CHECKS
