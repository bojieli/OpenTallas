"""parse_leaf_ports: Verilog attributes on ANSI port declarations do not hide direction/width (DIE-HEAD-39 10-30)."""
from pathlib import Path

import gen_rtl

REPO = Path(__file__).resolve().parents[2]


def test_attributed_ports_keep_direction_and_width():
    text = """module m (
    input wire clk, d,
    (* keep *) output reg q,
    (* keep, dont_touch = "true" *) output logic [3:0] export_q,
    (* keep *)
    input wire [1:0] s
);
endmodule
"""
    assert gen_rtl.parse_leaf_ports(text, "m") == {
        "clk": ("input", ""), "d": ("input", ""), "q": ("output", ""),
        "export_q": ("output", "[3:0]"), "s": ("input", "[1:0]")}


def test_actual_head_raw_export_pair_and_status_copy_headers():
    src = (REPO / "rtl/common/ot_dp_clk_landing_ca.sv").read_text()
    pair = gen_rtl.parse_leaf_ports(src, "ot_dp_head_raw_export_pair")
    assert pair == {"clk": ("input", ""), "d": ("input", ""), "q": ("output", ""), "export_q": ("output", "")}
    st = gen_rtl.parse_leaf_ports(src, "ot_meso_ca_status_copy")
    assert st["written"] == ("output", "[DEPTH-1:0]") and st["lap_q"] == ("output", "[DEPTH-1:0]")


def test_unattributed_headers_unchanged():
    text = "module n (input wire a, b, output wire [7:0] y /* c */, output z // t\n);\nendmodule\n"
    assert gen_rtl.parse_leaf_ports(text, "n") == {"a": ("input", ""), "b": ("input", ""),
                                                   "y": ("output", "[7:0]"), "z": ("output", "")}
