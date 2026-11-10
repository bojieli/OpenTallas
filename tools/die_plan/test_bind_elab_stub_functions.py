"""bind_elab.lib_stubs: a non-ANSI module with functions/tasks (yosys write_verilog form) must stub only its header
ports; function/task arguments are not module ports, and a generate guard before the first port declaration must
not hide it (KV-PLAN-2 11-10, KV-HOST-WI parent.sv: extra ports a/b/s, missing host_upstream_quiet)."""
from pathlib import Path
import os, re, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import bind_elab as B

NONANSI = ('module m_fn #(parameter N = 1) (clk, x, y);\n'
           '  generate if (N != 1) begin : g_guard\n    m_missing u_guard ();\n  end endgenerate\n'
           '  input clk;\n  input [7:0] x;\n  output [7:0] y;\n'
           '  function [31:0] _f_;\n    input [31:0] a;\n    input [255:0] b;\n    input [7:0] s;\n'
           '    _f_ = a;\n  endfunction\n'
           '  task t_;\n    input [3:0] q;\n    begin end\n  endtask\n'
           '  assign y = _f_(x, 0, 0);\nendmodule\n')


def _stub(tmp_path, text):
    src = tmp_path / "m_fn.v"
    src.write_text(text)
    out = tmp_path / "lib_stubs.sv"
    B.lib_stubs([str(src)], out)
    return out.read_text()


def _decls(txt):
    return re.findall(r"\b(?:input|output|inout)\b[^;]*?(\w+)\s*;", txt)


def test_nonansi_stub_keeps_header_ports_only(tmp_path):
    txt = _stub(tmp_path, NONANSI)
    assert sorted(_decls(txt)) == ["clk", "x", "y"]
    assert "_f_ = a" not in txt and "endtask" not in txt and "u_guard" not in txt


def test_nonansi_stub_without_functions_unchanged(tmp_path):
    txt = _stub(tmp_path, "module m2(a, z);\n  input a;\n  output z;\n  assign z = a;\nendmodule\n")
    assert sorted(_decls(txt)) == ["a", "z"]


@pytest.mark.skipif(not os.environ.get("OT_BIND_YOSYS"), reason="needs OT_BIND_YOSYS")
def test_yosys_parses_nonansi_function_stub(tmp_path):
    _stub(tmp_path, NONANSI)
    r = subprocess.run([os.environ["OT_BIND_YOSYS"], "-q", "-p", f"read_verilog -sv -lib {tmp_path / 'lib_stubs.sv'}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
