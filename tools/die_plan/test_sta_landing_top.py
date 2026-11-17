"""sta_landing_top.apply: landing nets wired where the part has the pin, dropped (reported) where it does not."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sta_landing_top as SLT

TOP = """module die_top (
    input  wire clk,
    input  wire rst_n
);
    wire w_a;
    pa a0 (
        .clk(clk),
        .x_o(w_a)
    );
    pb b0 (
        .clk(clk),
        .x_i(w_a)
    );
    pc c0 (
        .clk(clk)
    );
endmodule
"""
NET = dict(edges=2, wires=["landing_f0", "landing_s0"],
           bindings={"a0": {"fclk_out_x": "landing_f0", "cland_tstart_in": "pst_a"},
                     "b0": {"fclk_in_x": "landing_f0"},
                     "c0": {"fclk_in_y": "landing_f0"}},
           boundary_inputs=["pst_a"], boundary_outputs=[], boundary_aliases={})
PORTS = {"pa": {"clk", "x_o", "fclk_out_x", "cland_tstart_in"}, "pb": {"clk", "x_i", "fclk_in_x"}, "pc": {"clk"}}


def test_apply_wires_and_reports():
    text, rep = SLT.apply(TOP, NET, PORTS.get)
    assert "        .cland_tstart_in(pst_a)," in text and "        .fclk_out_x(landing_f0)\n    );" in text
    assert "        .x_o(w_a)," in text and "        .fclk_in_x(landing_f0)" in text
    assert "    input  wire pst_a," in text.split(");", 1)[0]
    assert "    wire landing_f0;" in text and "wire pst_a;" not in text
    assert rep["connected_bindings"] == 3 and rep["dropped_bindings"] == 1
    assert rep["dropped_by_instance"] == {"c0": 1} and rep["boundary_inputs"] == 1


def test_already_bound_pin_not_duplicated():
    top = TOP.replace("        .x_i(w_a)\n", "        .x_i(w_a),\n        .fclk_in_x(old)\n")
    text, rep = SLT.apply(top, NET, PORTS.get)
    assert text.count(".fclk_in_x(") == 1 and rep["already_connected"] == 1


def test_module_ports_ansi_and_plain():
    v = "module pa (clk, q);\n  input clk;\n  output [3:0] q;\nendmodule\nmodule pb (\n    input wire clk,\n    output wire y\n);\nendmodule\n"
    assert SLT.module_ports(v, "pa") == {"clk", "q"}
    assert SLT.module_ports(v, "pb") == {"clk", "y"}
    assert SLT.module_ports(v, "pz") is None
