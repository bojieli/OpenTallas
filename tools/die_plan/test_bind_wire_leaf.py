"""tests for bind_wire_leaf.py (BIN-COPY, FABLE-FIX-QC-N N4.1): a leaf is pure wiring only when its RTL proves it
python3 -m pytest tools/die_plan/test_bind_wire_leaf.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_wire_leaf as WL  # noqa: E402

FRS = """// kept leaf
module qfd_dv_s8_frs (
    input  wire           ck,             // region membership only; no logic here
    input  wire [1027:0]  rs_s,
    output wire [127:0]   rs_s_r0, rs_s_r7,
    output wire [3:0]     rs_s_c
);
    assign rs_s_c  = {rs_s[1027:1026], rs_s[513:512]};
    assign rs_s_r0 = {rs_s[577:514], rs_s[63:0]};
    /* block
       comment */
    assign rs_s_r7 = {rs_s[1025:962], rs_s[511:448]};
endmodule
module other (input wire a, output wire y);
    assign y = ~a;
endmodule
"""


def test_frs_map():
    m = WL.wire_map(FRS, "qfd_dv_s8_frs")
    assert [m[("rs_s_c", i)] for i in range(4)] == [("rs_s", 512), ("rs_s", 513), ("rs_s", 1026), ("rs_s", 1027)]
    assert m[("rs_s_r0", 0)] == ("rs_s", 0) and m[("rs_s_r0", 64)] == ("rs_s", 514) and m[("rs_s_r7", 127)] == ("rs_s", 1025)
    assert len(m) == 4 + 128 + 128 and not any(i == "ck" for i, _b in m.values())


def test_offset_ranges_scalars_and_bit_selects():
    t = "module w (input wire [8:1] a, input wire s, output wire [3:2] y, output wire z, output wire u);\n" \
        "  assign y = {a[8], s};\n  assign z = a[1];\nendmodule\n"
    m = WL.wire_map(t, "w")
    # positions are 0-based from each port's lsb (the binder's bit numbering)
    assert m == {("y", 1): ("a", 7), ("y", 0): ("s", 0), ("z", 0): ("a", 0)}       # u undriven: absent


@pytest.mark.parametrize("body,msg", [
    ("assign y = ~a;", "not a plain input port reference"),
    ("assign y = a & b;", "not a plain input port reference"),
    ("assign y = 2'b00;", "not a plain input port reference"),
    ("wire [1:0] t; assign t = a; assign y = t;", "not a plain assign"),
    ("always @(*) y = a;", "not a plain assign"),
    ("sub u (.a(a), .y(y));", "not a plain assign"),
    ("assign y = a; assign y[0] = b[0];", "driven twice"),
    ("assign y = {a, b};", "assign width"),
    ("assign y = a[2:1];", "outside the port range"),
    ("assign a = b;", "not a plain output port reference"),
])
def test_fail_closed(body, msg):
    t = f"module w (input wire [1:0] a, input wire [1:0] b, output wire [1:0] y);\n  {body}\nendmodule\n"
    with pytest.raises(ValueError, match=msg):
        WL.wire_map(t, "w")


def test_header_forms_fail_closed():
    with pytest.raises(ValueError, match="parameterised"):
        WL.wire_map("module w #(parameter W = 1) (input wire a, output wire y); assign y = a; endmodule", "w")
    with pytest.raises(ValueError, match="not a plain input / output wire"):
        WL.wire_map("module w (input wire [W-1:0] a, output wire y); assign y = a[0]; endmodule", "w")
    with pytest.raises(ValueError, match="not a plain input / output wire"):
        WL.wire_map("module w (input wire a, output reg y); assign y = a; endmodule", "w")
    with pytest.raises(ValueError, match="module not found"):
        WL.wire_map(FRS, "nope")
    with pytest.raises(ValueError, match="not a plain input port reference"):
        WL.wire_map(FRS, "other")


def test_from_files_and_disagreeing_definitions(tmp_path):
    a, b, c = tmp_path / "a.sv", tmp_path / "b.sv", tmp_path / "c.sv"
    a.write_text("module w (input wire [1:0] a, output wire [1:0] y); assign y = a; endmodule\n")
    b.write_text("module w (input wire [1:0] a, output wire [1:0] y); assign y = {a[0], a[1]}; endmodule\n")
    c.write_text("module x (input wire a, output wire y); assign y = a; endmodule\n")
    assert WL.from_files([str(c), str(a)], "w") == {("y", 1): ("a", 1), ("y", 0): ("a", 0)}
    with pytest.raises(ValueError, match="different wiring"):
        WL.from_files([str(a), str(b)], "w")
    with pytest.raises(ValueError, match="no RTL source"):
        WL.from_files([str(c), str(tmp_path / "missing.sv")], "w")
    ab = dict(rtl_roots=[], files=["a.sv"], prefer=[])
    assert WL.leaf_map(ab, str(tmp_path), "w")[("y", 0)] == ("a", 0)
