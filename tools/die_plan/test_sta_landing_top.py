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


def test_header_boundary_preserves_internal_nets_and_mutant_is_detected(tmp_path):
    import die_sta as D
    text, _ = SLT.apply(TOP, NET, PORTS.get)
    good = tmp_path / "good.v"
    good.write_text(text)
    mod = D.read_verilog(good)["die_top"]
    assert {p[1] for p in mod.ports} == {"clk", "rst_n", "pst_a"}
    assert ("landing_f0", None, None) in mod.wires
    assert "wire landing_f0;" not in text.split(");", 1)[0]
    # The private real4 predecessor inserted declarations one line too early.
    # Real netlist parsing catches the resulting phantom top inputs rather than
    # merely checking that the desired wire text appears somewhere in the file.
    source = Path(SLT.__file__).read_text()
    original = "out[end + 1:end + 1] = decl"
    assert original in source
    mutant = {"__name__": "sta_landing_top_header_mutant"}
    exec(compile(source.replace(original, "out[end:end] = decl", 1),
                 "sta_landing_top_header_mutant.py", "exec"), mutant)
    bad_text, _ = mutant["apply"](TOP, NET, PORTS.get)
    bad = tmp_path / "bad.v"
    bad.write_text(bad_text)
    bad_ports = {p[1] for p in D.read_verilog(bad)["die_top"].ports}
    assert "landing_f0" in bad_ports and ";" in bad_ports
