"""A zero-bit source connection is an open port, never an empty concatenation or tie."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E
from bind_compose import compose


class Rules:
    def part_of(self, path):
        return "tile" if path.startswith("top.") else None


def test_empty_source_ports_remain_open_and_live_path_compiles(tmp_path):
    f = E.Flat()
    f.new(3)
    f.top_ports = {"d": ("input", [1]), "q": ("output", [2])}
    f.cells = [E.Cell("top.leaf", "leaf", {},
                      {"d": [1], "q": [2], "unused_input": [], "unused_output": []},
                      {"d": "input", "q": "output", "unused_input": "input", "unused_output": "output"},
                      "leaf")]
    endpoint = lambda port: dict(member="top.leaf", port=port, bit=0)
    spec = {"cores": [dict(inst="top.core", module="composed", members=["top.leaf"], ports={
        "d": dict(dir="input", bits=[[endpoint("d")]]),
        "q": dict(dir="output", bits=[[endpoint("q")]])})]}
    sources, receipt = compose(f, Rules(), spec, E.Cell)
    rtl = sources[0][1]
    assert receipt["terminal_equality"]
    assert receipt["cores"][0]["terminal_count"] == 2
    assert f.cells[0].ports == {"d": [1], "q": [2]}
    # This is a frontend/behavior check, not merely a spelling assertion: input
    # opens retain Z, while the real input/output path still carries both values.
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        pytest.skip("Icarus is required for the generated-Verilog regression")
    source = tmp_path / "open_ports.sv"
    source.write_text(rtl + """
module leaf(input wire d, unused_input, output wire q, unused_output);
  assign q=d;
  assign unused_output=d;
endmodule
module tb;
  reg d=0; wire q;
  composed dut(.d(d), .q(q));
  initial begin
    #1;
    if(q !== 1'b0 || dut.m0.unused_input !== 1'bz) $fatal(1,"low/open changed");
    d=1; #1;
    if(q !== 1'b1 || dut.m0.unused_input !== 1'bz) $fatal(1,"high/open changed");
    $display("OPEN_PORTS_PASS"); $finish;
  end
endmodule
""")
    binary = tmp_path / "sim"
    subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", str(binary), str(source)],
                   check=True, capture_output=True, text=True)
    result = subprocess.run(["vvp", str(binary)], check=True, capture_output=True, text=True)
    assert "OPEN_PORTS_PASS" in result.stdout
