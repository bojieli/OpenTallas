"""DIE-HEAD-29 10-29: nested_check reads the source the way synthesis does.  HEAD SOURCE7 nested leaf-pin FAIL
136 unbound / 67 unknown / 452 unresolved was all parser: `ifdef OT_MESO_CA_FV formal-only ports in the
ot_dp_clk_landing_cas ANSI header, .p(((a) & b)) nested parentheses, {a, b} concatenations and $clog2 widths.
Each fix must still FAIL closed on a real defect."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import port_bind_gate as PBG  # noqa: E402

LEAF = """module leaf #(parameter integer W = 2, parameter integer DEPTH = 8) (
    input  wire         clk,
    input  wire [$clog2(DEPTH)+3:0] strap_k,
    input  wire [W-1:0] d,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now
`endif
);
endmodule
"""


def _wr(conn, decl="    wire a, b, f;\n    wire [6:0] k;\n"):
    return {"w.sv": "module w (\n    input wire clk\n);\n" + decl +
            "    leaf #(.W(2), .DEPTH(8)) u_l (.clk(clk), " + conn + ");\nendmodule\n"}


GOOD = ".strap_k(k), .d({a, b}), .fault(f)"


def test_synthesis_view_passes():
    r = PBG.nested_check(_wr(GOOD), [LEAF])
    assert r["verdict"] == "PASS", r


def test_formal_define_requires_formal_ports():
    r = PBG.nested_check(_wr(GOOD), [LEAF], defines=("SYNTHESIS", "OT_MESO_CA_FV"))
    assert r["verdict"] == "FAIL" and r["unbound"] == 2, r


def test_real_unbound_still_fails():
    r = PBG.nested_check(_wr(".strap_k(k), .d({a, b})"), [LEAF])
    assert r["verdict"] == "FAIL" and r["unbound"] == 1, r


def test_concat_width_mismatch_caught():
    r = PBG.nested_check(_wr(".strap_k(k), .d({a, b, f}), .fault(f)"), [LEAF])
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 1, r


def test_clog2_width_mismatch_caught():
    r = PBG.nested_check(_wr(".strap_k(k[5:0]), .d({a, b}), .fault(f)"), [LEAF])
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 1, r


def test_nested_parentheses_bound_and_sized():
    r = PBG.nested_check(_wr(".strap_k(k), .d({a, b}), .fault(((a) & b))"), [LEAF])
    assert r["verdict"] == "PASS", r
    r = PBG.nested_check(_wr(".strap_k(k), .d({a, b}), .fault(((k) | b))"), [LEAF])
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 1, r


def test_unsizable_expression_is_unresolved():
    r = PBG.nested_check(_wr(".strap_k(k), .d({2{a}}), .fault(a ? b : f)"), [LEAF])
    assert r["verdict"] == "FAIL" and r["unresolved"] == 2, r


def test_preprocess_else_and_nesting():
    t = "a\n`ifdef X\nb\n`ifndef Y\nc\n`endif\n`else\nd\n`endif\ne"
    assert PBG.preprocess(t, ("X",)).split() == ["a", "b", "c", "e"]
    assert PBG.preprocess(t, ("X", "Y")).split() == ["a", "b", "e"]
    assert PBG.preprocess(t, ()).split() == ["a", "d", "e"]
    with pytest.raises(ValueError):
        PBG.preprocess("`ifdef X\na", ())
