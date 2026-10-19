"""KEEP-MODULE AUDIT (ROOT-KEEP 10-18): a kit keep entry that matches nothing after synthesis FAILs the gate;
$paramod-renamed survivors count as matches; a #(...) instance of a kept module FAILs before the fleet run."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keep_module_audit as KA
import pre_route_gate as G

KIT_ENV = ("EXTRA=(--orfs-var ADDER_MAP_FILE= --orfs-var 'SYNTH_KEEP_MODULES=ot_keep_reg ot_other_ff' "
           "--orfs-var PLACE_DENSITY_LB_ADDON=)\n")

# yosys netlist shape: kept paramod module written as an escaped identifier; ot_other_ff kept by exact name
NETLIST = r"""
module \$paramod\ot_keep_reg\W=256 (clk, d, q);
  input clk; input [255:0] d; output [255:0] q;
  DFFHQNx1_ASAP7_75t_R \q_reg[0]  (.CLK(clk), .D(d[0]), .QN(q[0]));
endmodule
module ot_other_ff (clk, d, q);
  input clk; input d; output q;
  DFFHQNx1_ASAP7_75t_R q_reg (.CLK(clk), .D(d), .QN(q));
endmodule
module top (clk, d, q);
  input clk; input [255:0] d; output [255:0] q;
  \$paramod\ot_keep_reg\W=256  u_ret_l (.clk(clk), .d(d), .q(q));
  \$paramod\ot_keep_reg\W=256  u_ret_f (.clk(clk), .d(d), .q(q));
  ot_other_ff u_o (.clk(clk), .d(d[0]), .q(q[0]));
endmodule
"""

# the lgtap r2 failure: the copy was flattened, only std cells remain
FLATTENED = r"""
module top (clk, d, q);
  input clk; input [255:0] d; output [255:0] q;
  DFFHQNx1_ASAP7_75t_R \return_d_reg[0]  (.CLK(clk), .D(d[0]), .QN(q[0]));
endmodule
"""


def test_entries_from_kit_env_and_spec():
    spec = {"route": {"synth_keep_modules": ["ot_other_ff", "ot_add_l5"]}}
    assert KA.keep_entries(KIT_ENV, spec) == ["ot_keep_reg", "ot_other_ff", "ot_add_l5"]
    assert KA.keep_entries("EXTRA=(--orfs-var A=1)\n", {}) == []


def test_paramod_and_slang_names_match():
    assert KA.entry_matches("ot_keep_reg", r"\$paramod\ot_keep_reg\W=256")
    assert KA.entry_matches("ot_keep_reg", "$paramod$3f2a9c\\ot_keep_reg")
    assert KA.entry_matches("ot_keep_reg", "ot_keep_reg$1")
    assert KA.entry_matches("ot_keep_reg", "ot_keep_reg")
    assert not KA.entry_matches("ot_keep_reg", r"\$paramod\ot_keep_reg_wide\W=256")
    assert not KA.entry_matches("ot_keep_reg", "ot_keep_reg_wide")


def test_netlist_summary_counts_through_hierarchy():
    s = KA.netlist_summary(NETLIST, "top")
    assert r"$paramod\ot_keep_reg\W=256" in s["modules"]
    assert s["cells"][r"$paramod\ot_keep_reg\W=256"] == 2
    assert s["cells"]["DFFHQNx1_ASAP7_75t_R"] == 3


def _remote_gate(tmp_path, netlist, warns=""):
    (tmp_path / "kit.env").write_text(KIT_ENV)
    out = warns + "GATE_KEEP_NETLIST " + __import__("json").dumps(KA.netlist_summary(netlist, "top")) + "\n"
    g = G.Gate()
    G.check_keep_modules(g, tmp_path, {"route": {}}, out)
    return g


def test_surviving_paramod_copy_passes(tmp_path):
    g = _remote_gate(tmp_path, NETLIST)
    assert g.verdict != "FAIL"
    assert any("ot_keep_reg" in i["message"] and "2 instances" in i["message"] for i in g.items)


def test_flattened_copy_fails(tmp_path):
    w = 'GATE_KEEPWARN Warning: Selection "ot_keep_reg" did not match any module.\n'
    g = _remote_gate(tmp_path, FLATTENED, w)
    assert g.verdict == "FAIL"
    fail = [i for i in g.items if i["severity"] == "FAIL"]
    assert fail[0]["check"] == "keep_modules" and "ot_keep_reg" in fail[0]["message"] and "ot_other_ff" in fail[0]["message"]
    assert "did not match any module" in fail[0]["message"]


def test_old_remote_log_without_record_warns(tmp_path):
    (tmp_path / "kit.env").write_text(KIT_ENV)
    g = G.Gate()
    G.check_keep_modules(g, tmp_path, {"route": {}}, "GATE_FLOW_RC=0\n")
    assert g.verdict == "WARN"


def test_kit_without_keep_entries_is_untouched(tmp_path):
    (tmp_path / "kit.env").write_text("EXTRA=(--orfs-var PLACE_DENSITY_LB_ADDON=)\n")
    g = G.Gate()
    G.check_keep_modules(g, tmp_path, {"route": {}}, "")
    G.check_keep_static(g, tmp_path, {"route": {}, "sources": []})
    assert g.items == []


def test_static_parameterised_instance_fails(tmp_path):
    (tmp_path / "kit.env").write_text(KIT_ENV)
    rtl = tmp_path / "t.sv"
    rtl.write_text("module top(input clk);\n  // ot_other_ff #(.X(1)) commented (ignored)\n"
                   "  ot_keep_reg #(.W(256)) u_ret_l(.clk(clk));\n  ot_other_ff u_o(.clk(clk));\nendmodule\n")
    g = G.Gate()
    G.check_keep_static(g, tmp_path, {"route": {}, "sources": [str(rtl)]})
    fails = [i for i in g.items if i["severity"] == "FAIL"]
    assert len(fails) == 1 and "ot_keep_reg" in fails[0]["message"] and "u_ret_l" in fails[0]["message"]


def test_static_slang_frontend_is_exempt(tmp_path):
    (tmp_path / "kit.env").write_text(KIT_ENV.replace("--orfs-var PLACE", "--orfs-var SYNTH_HDL_FRONTEND=slang --orfs-var PLACE"))
    rtl = tmp_path / "t.sv"
    rtl.write_text("module top(input clk);\n  ot_keep_reg #(.W(256)) u_ret_l(.clk(clk));\nendmodule\n")
    g = G.Gate()
    G.check_keep_static(g, tmp_path, {"route": {}, "sources": [str(rtl)]})
    assert g.verdict != "FAIL"


def test_static_keep_hierarchy_attribute_is_exempt(tmp_path):
    # qfd_xs_leaf_banked: #(.BANK(bk)) instances of a module whose definition carries (* keep_hierarchy *)
    (tmp_path / "kit.env").write_text(KIT_ENV)
    rtl = tmp_path / "t.sv"
    rtl.write_text("module top(input clk);\n  ot_keep_reg #(.W(256)) u_ret_l(.clk(clk));\nendmodule\n"
                   '(* keep_hierarchy = "yes" *) module ot_keep_reg #(parameter integer W=1)(input clk);\nendmodule\n')
    g = G.Gate()
    G.check_keep_static(g, tmp_path, {"route": {}, "sources": [str(rtl)]})
    assert g.verdict != "FAIL"
