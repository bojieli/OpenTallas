"""bind_verify native stubs: typed string parameters of slang-only leaves (ROM VIAMAP) must not break native Yosys."""
from pathlib import Path
import os, subprocess, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
import bind_verify as V

ROM = ('module ot_rom_x #(parameter string VIAMAP = "", parameter string INSTANCE = "") (\n'
       '    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [71:0] rd_out);\n'
       '  always @(posedge clk) rd_out <= 0;\nendmodule\n')


def _stub(tmp_path, text, name):
    src = tmp_path / name
    src.write_text(text)
    (tmp_path / "verify").mkdir(exist_ok=True)
    return src, V.native_lib_stubs([str(src)], tmp_path / "verify")


def test_native_stub_drops_string_type_keeps_defaults_and_original(tmp_path):
    src, out = _stub(tmp_path, ROM, "ot_rom_x.v")
    assert len(out) == 1
    txt = Path(out[0]).read_text()
    assert "parameter string" not in txt
    assert 'parameter VIAMAP = ""' in txt and 'parameter INSTANCE = ""' in txt
    assert "rd_out <= 0" not in txt          # still an interface-only stub
    assert src.read_text() == ROM            # real source untouched


def test_native_stub_unchanged_without_string_params(tmp_path):
    _src, out = _stub(tmp_path, "module plain #(parameter N = 3) (input wire a);\nendmodule\n", "plain.v")
    assert out == [str(tmp_path / "verify" / "lib_stubs.sv")]
    assert V.native_lib_stubs([], tmp_path / "verify") == []


@pytest.mark.skipif(not os.environ.get("OT_BIND_YOSYS"), reason="needs OT_BIND_YOSYS")
def test_native_yosys_parses_staged_stub_and_rejects_raw(tmp_path):
    _src, out = _stub(tmp_path, ROM, "ot_rom_x.v")
    y = os.environ["OT_BIND_YOSYS"]
    r = subprocess.run([y, "-q", "-p", f"read_verilog -sv -lib {out[0]}"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    raw = tmp_path / "verify" / "lib_stubs.sv"
    r = subprocess.run([y, "-q", "-p", f"read_verilog -sv -lib {raw}"], capture_output=True, text=True)
    assert r.returncode != 0                 # the exact unstaged defect is still caught
