import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_param_check as B

RING = """// ring
module ot_ring #(parameter integer W = 1, parameter integer NARROW = 0) (input wire clk, input wire [W-1:0] d);
endmodule
"""
DLY = """module ot_dly #(parameter W = 1, D = 2) (input wire clk); localparam Z = 3; endmodule
"""


def _tree(tmp, ring=RING, part=None):
    (tmp / "rtl" / "common").mkdir(parents=True)
    (tmp / "rtl" / "common" / "ot_ring.sv").write_text(ring)
    (tmp / "rtl" / "common" / "ot_dly.sv").write_text(DLY)
    b = tmp / "bind" / "rtl"
    b.mkdir(parents=True)
    (b / "t_part.sv").write_text(part or (
        "module t_part(input wire clk);\n"
        "  ot_ring #(.W(4), .NARROW(1), .LITE(1)) u_cland_a (.clk(clk), .d(4'd0));\n"
        "  ot_dly #(.W((8)), .D(3)) u_d (.clk(clk));\n"
        "  hard_macro #(.X(1)) u_h (.clk(clk));\n"
        "  // ot_ring #(.GHOST(1)) u_c (.clk(clk));\n"
        "endmodule\n"))
    return tmp, b


def test_missing_parameter_is_an_error(tmp_path):
    t, b = _tree(tmp_path)
    r = B.check(t, b)
    assert r["verdict"] == "FAIL"
    assert len(r["errors"]) == 2 and "ot_ring.LITE" in r["errors"][1] and "u_cland_a" in r["errors"][1]
    assert r["undefined_modules"] == 1 and r["errors"][0].startswith("BOUND-PARAM hard_macro.UNDEFINED:")   # BPC-UNDEF-FATAL-1123
    assert not any("GHOST" in e for e in r["errors"])   # comments are ignored


def test_declared_parameters_pass_including_comma_continued_lists(tmp_path):
    t, b = _tree(tmp_path, ring=RING.replace("NARROW = 0)", "NARROW = 0, parameter integer LITE = 0)"))
    r = B.check(t, b)
    assert r["verdict"] == "FAIL" and r["params_checked"] == 5 and r["coverage"] == "5/6", r     # hard_macro.X unchecked
    (t / "rtl" / "common" / "hard_macro.sv").write_text("module hard_macro #(parameter X = 0) (input wire clk); endmodule\n")
    r = B.check(t, b)
    assert r["verdict"] == "PASS" and r["coverage"] == "6/6", r


def test_partial_definitions_warn(tmp_path):
    t, b = _tree(tmp_path, ring=RING.replace("NARROW = 0)", "NARROW = 0, parameter integer LITE = 0)"))
    (t / "results").mkdir()
    (t / "results" / "old_ot_ring.sv").write_text(RING)
    (t / "rtl" / "common" / "hard_macro.sv").write_text("module hard_macro #(parameter X = 0) (input wire clk); endmodule\n")
    r = B.check(t, b)
    assert r["verdict"] == "PASS" and any("ot_ring.LITE" in w for w in r["warnings"])


def test_cli_exit_code(tmp_path):
    t, b = _tree(tmp_path)
    assert B.main(["--tree", str(t), "--rtl-dir", str(b)]) == 1


def test_module_headers_of_the_bound_parts_are_not_instantiations(tmp_path):
    part = ("module t_part #(parameter S_a = 0) (input wire clk);\n"
            "  wire x;\n"
            "  ot_ring #(.W(4), .NARROW(1)) u_cland_a (.clk(clk), .d(4'd0));\n"
            "endmodule\n"
            "module top; t_part #(.S_a(1)) u_p (.clk(1'b0)); endmodule\n")
    t, b = _tree(tmp_path, part=part)
    r = B.check(t, b)
    assert r["verdict"] == "PASS" and r["params_checked"] == 3, r       # t_part.S_a: defined in the bind RTL itself (BPC-UNDEF-FATAL-1123)


def test_undefined_module_fails_with_coverage_and_bind_rtl_defs_count(tmp_path, capsys):
    """BPC-UNDEF-FATAL-1123 (COORD): KV A1 checked 92/570 parameters with 29 undefined modules and still read PASS"""
    t, b = _tree(tmp_path, ring=RING.replace("NARROW = 0)", "NARROW = 0, parameter integer LITE = 0)"))
    assert B.main(["--tree", str(t), "--rtl-dir", str(b)]) == 1
    out = capsys.readouterr().out
    assert "BOUND-PARAM hard_macro.UNDEFINED" in out and "coverage=5/6" in out and "undefined_modules=1" in out
    (b / "bind_cells.sv").write_text("module hard_macro #(parameter X = 0) (input wire clk); endmodule\n")   # bind's own cell file
    r = B.check(t, b)
    assert r["verdict"] == "PASS" and r["undefined_modules"] == 0 and r["coverage"] == "6/6", r
