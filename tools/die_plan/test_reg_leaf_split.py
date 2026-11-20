"""REG-LEAF-SPLIT 11-19 (reg_leaf_split.py, plan partition_types[T].reg_leaf_split): kept copies of a pure registered leaf."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reg_leaf_split as R  # noqa: E402
import schema  # noqa: E402

PART = """module part (input wire clk, input wire [9:0] a, input wire [1:0] e, output wire [5:0] o0, output wire [5:0] o1);
    wire [1:0] w_t1_e_b;
    wire [9:0] w_t1_ti_b;
    wire [1:0] w_t2_e_b;
    wire [9:0] w_t2_ti_b;
    wire [5:0] w_o0, w_o1;
    assign o0 = w_o0;
    assign o1 = w_o1;
    qkh_head_tstage u_t1 (
        .ck(clk),
        .e_a(e),
        .e_b(w_t1_e_b),
        .ti_a(a),
        .ti_b(w_t1_ti_b)
    );
    cons u_c0 (
        .x(w_t2_ti_b[1:0]),
        .y(w_t2_e_b[1:0]),
        .r(w_t2_ti_b[5:2]),
        .o(w_o0)
    );
    cons u_c1 (
        .x(w_t2_ti_b[1:0]),
        .y(w_t2_e_b[1:0]),
        .r(w_t2_ti_b[9:6]),
        .o(w_o1)
    );
    qkh_head_gather_stage #(.MUT(0)) u_t2 (
        .ck(clk),
        .e_a(w_t1_e_b[1:0]),
        .e_b(w_t2_e_b),
        .ti_a(w_t1_ti_b[9:0]),
        .ti_b(w_t2_ti_b)
    );
endmodule
"""
ROW = {"leaf": "u_t2", "copies": [{"name": "a", "pins": ["u_c0.*"], "site_um": [10, 20]},
                                  {"name": "b", "pins": ["u_c1.*"], "site_um": [30.5, 40]}]}


def test_absent_is_nothing(tmp_path):
    (tmp_path / "p.sv").write_text(PART)
    assert R.apply(tmp_path, "t", {}) == (None, None)
    assert (tmp_path / "p.sv").read_text() == PART and not (tmp_path / "reg_leaf_split_cells.sv").exists()


def test_split_maps_every_pin_bit_to_its_old_source():
    new, rec = R.split_text(PART, ROW)
    assert [(c["inst"], c["bits"]) for c in rec["copies"]] == [("u_t2_rls_a", 8), ("u_t2_rls_b", 8)]
    assert rec["bits"] == 12 and rec["flops_added"] == 16
    assert "#(.MUT(0)) u_t2 (" not in new and "w_t2_ti_b" not in new and "w_t2_e_b" not in new
    # wires declared where the leaf outputs were, before any use
    assert new.index("wire [7:0] w_t2_rls_a_q;") < new.index(".x(w_t2_rls_a_q")
    # copy a: ti[1:0], ti[5:2] then e[1:0] (out port order) -> d = {e, ti[5:2], ti[1:0]} in run form
    assert "ot_dp_dly_keep #(.W(8), .D(1)) u_t2_rls_a (.clk(clk), .d({w_t1_e_b[1:0], w_t1_ti_b[5:0]}), .q(w_t2_rls_a_q));" in new
    assert ".r(w_t2_rls_b_q[5:2])" in new and ".y(w_t2_rls_b_q[7:6])" in new


def _sim(tmp_path, text):
    """iverilog: 40 random cycles of the part, outputs per cycle"""
    tb = """module tb; reg clk = 0; reg [9:0] a; reg [1:0] e; wire [5:0] o0, o1; integer i;
    part dut(.clk(clk), .a(a), .e(e), .o0(o0), .o1(o1));
    initial begin a = 0; e = 0; for (i = 0; i < 40; i = i + 1) begin a = $random; e = $random; #1 clk = 1; #1 clk = 0;
    $display("%h %h", o0, o1); end $finish; end endmodule
    module cons (input wire [1:0] x, input wire [1:0] y, input wire [3:0] r, output wire [5:0] o); assign o = {x ^ y, r}; endmodule
    module qkh_head_tstage (input wire ck, input wire [9:0] ti_a, input wire [1:0] e_a, output reg [9:0] ti_b, output reg [1:0] e_b);
    always @(posedge ck) begin ti_b <= ti_a; e_b <= e_a; end endmodule
    module qkh_head_gather_stage #(parameter integer MUT = 0) (input wire ck, input wire [9:0] ti_a, input wire [1:0] e_a,
    output wire [9:0] ti_b, output wire [1:0] e_b);
    qkh_head_tstage u_reg(.ck(ck), .ti_a(ti_a), .e_a(e_a), .ti_b(ti_b), .e_b(e_b)); endmodule
    """
    import bind_pad_tail_split as TS
    d = tmp_path / str(abs(hash(text)))
    d.mkdir()
    (d / "a.sv").write_text(text + tb + TS.KEEP_CELL)
    subprocess.run(["iverilog", "-g2012", "-o", str(d / "x"), str(d / "a.sv")], check=True)
    out = subprocess.run(["vvp", "-n", str(d / "x")], check=True, capture_output=True, text=True).stdout
    out = "\n".join(l for l in out.splitlines() if "$finish" not in l)
    return out


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_split_is_cycle_equivalent(tmp_path):
    new, _ = R.split_text(PART, ROW)
    ref = _sim(tmp_path, PART)
    assert ref.count("\n") >= 39 and "xx" not in ref.splitlines()[-1] and _sim(tmp_path, new) == ref


@pytest.mark.parametrize("row,msg", [
    (dict(ROW, copies=[dict(ROW["copies"][0], pins=["u_c0.x"]), ROW["copies"][1]]), "matches 0 copies"),
    (dict(ROW, copies=[dict(ROW["copies"][0], pins=["u_c*"]), ROW["copies"][1]]), "matches 2 copies"),
    (dict(ROW, copies=ROW["copies"] + [{"name": "c", "pins": ["u_zz.*"], "site_um": [0, 0]}]), "match no consumer pin"),
    (dict(ROW, leaf="u_nope"), "found 0 instance"),
    (dict(ROW, leaf="u_c0"), "not a known pure"),
])
def test_fail_closed(row, msg):
    with pytest.raises(ValueError, match=msg):
        R.split_text(PART, row)


def test_fail_closed_on_impure_param_and_stray_use():
    with pytest.raises(ValueError, match="parameter MUT=43"):
        R.split_text(PART.replace("#(.MUT(0))", "#(.MUT(43))"), ROW)
    with pytest.raises(ValueError, match="outside a port connection"):
        R.split_text(PART.replace("    assign o1 = w_o1;", "    assign o1 = w_o1 ^ w_t2_ti_b[5:0];"), ROW)


def test_config_rejects_bad_rows():
    for bad in ([{"leaf": "u_t2", "copies": [ROW["copies"][0]]}],
                [{"leaf": "u_t2", "copies": [ROW["copies"][0], dict(ROW["copies"][1], name="a")]}],
                [dict(ROW, extra=1)],
                [{"leaf": "u_t2", "copies": [ROW["copies"][0], dict(ROW["copies"][1], site_um=[1])]}]):
        with pytest.raises(ValueError):
            R.config({"reg_leaf_split": bad})


def test_apply_and_install_write_kit_files(tmp_path):
    rtl = tmp_path / "rtl"
    rtl.mkdir()
    (rtl / "p_bound.sv").write_text(PART)
    rec, extra = R.apply(rtl, "t", {"reg_leaf_split": [ROW]})
    assert extra == rtl / "reg_leaf_split_cells.sv" and "module ot_dp_dly_keep" in extra.read_text()
    assert "u_t2_rls_b" in (rtl / "p_bound.sv").read_text()
    assert rec["flops_removed"] == 12 and rec["flops_added"] == 16 and rec["leaves"][0]["file"] == "p_bound.sv"
    (tmp_path / "istations.tcl").write_text("set is_n 0\nis_place {*x*} 1 2 a\nclose $is_fh\nputs done\n")
    R.install(tmp_path, rec)
    ist = (tmp_path / "istations.tcl").read_text().split("\n")
    assert ist[2:5] == ["is_place {*u_t2_rls_a[./]*} 10.0 20.0 rls:u_t2_rls_a",
                        "is_place {*u_t2_rls_b[./]*} 30.5 40.0 rls:u_t2_rls_b", "close $is_fh"]
    assert json.loads((tmp_path / "reg_leaf_split.json").read_text())["leaves"][0]["leaf"] == "u_t2"


def test_install_without_istations_writes_full_form(tmp_path):
    _, rec = R.split_text(PART, ROW)
    R.install(tmp_path, dict(type="t", leaves=[rec]))
    s = (tmp_path / "istations.tcl").read_text()
    assert "proc is_place" in s and "is_place {*u_t2_rls_a[./]*} 10.0 20.0" in s and "is_coverage_gate" not in s


def test_existing_keep_cell_not_duplicated(tmp_path):
    import bind_pad_tail_split as TS
    (tmp_path / "p.sv").write_text(PART)
    (tmp_path / "bind_cells.sv").write_text(TS.KEEP_CELL)
    _, extra = R.apply(tmp_path, "t", {"reg_leaf_split": [ROW]})
    assert extra is None


def test_schema_accepts_row():
    sub = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["reg_leaf_split"]
    assert sub["items"]["required"] == ["leaf", "copies"]
