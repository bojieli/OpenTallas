"""tests for tools/die_plan/kit_seq_lec.py and lec_asap7_dffasrhqn.v (KV-PV-CAP 11-24)"""
import re, shutil, subprocess, sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_seq_lec as K  # noqa: E402

NET = ("module \\$paramod\\ot_dp_lk\\W=s32'00000000000000000000000100000010 (clk, d, q);\n  input clk;\nendmodule\n"
       "module \\$paramod\\ot_dp_lk\\W=s32'00000000000000000000000000000001 (clk, d, q);\nendmodule\n")


def test_lk_gate_widths():
    t = K.lk_gate(NET)
    assert t.count("assign q = d;") == 2 and "input [257:0] d;" in t and "input [0:0] d;" in t


def test_script_reads_asrh_model_after_liberty_and_before_netlist(tmp_path):
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/a.sv \\\n  /work/rtl/m_bb.v\n"
                                        "export VERILOG_DEFINES = -DSYNTHESIS -DX\nexport ADDITIONAL_LIBS = /work/macros/m_tt.lib\n")
    cfg = K.config(tmp_path)
    s = K.script(tmp_path, cfg, tmp_path / "net.v", tmp_path / "o").splitlines()
    i_lib = max(i for i, l in enumerate(s) if l.startswith("read_liberty -ignore_miss_func"))
    i_asrh = s.index(f"read_verilog -overwrite {K.ASRH}")
    i_net = s.index(f"read_verilog {tmp_path / 'net.v'}")
    assert i_lib < i_asrh < i_net
    assert s[0].startswith("read_verilog -sv -DSYNTHESIS -DX -defer ") and s[0].endswith(f"{tmp_path}/rtl/a.sv")
    assert f"read_verilog -sv -lib {tmp_path}/rtl/m_bb.v" in s and f"read_liberty -lib -ignore_redef {tmp_path}/macros/m_tt.lib" in s
    g = s.index("rename top gate")
    assert "setattr -set init 1'1 w:*.IQN" in s[i_net:g]


def test_verdict_parse():
    assert K.verdict("... Networks are equivalent.") == "PROVED"
    assert K.verdict("Output 0 of miter was asserted in frame 6.\nNetworks are not equivalent.") == "CEX"
    assert K.verdict("ABC rc=0") == "NO_VERDICT"


def test_asrh_model_text_matches_liberty_ff():
    t = K.ASRH.read_text()
    assert "module DFFASRHQNx1_ASAP7_75t_R (input CLK, input D, input RESETN, input SETN, output QN);" in t
    body = re.sub(r"//.*", "", t)
    assert re.search(r"if \(!SETN\) IQN <= 1'b0;\s*else if \(!RESETN\) IQN <= 1'b1;\s*else IQN <= ~D;", body)
    assert "assign QN = IQN;" in body


T = """module t(input CLK, input D, input RESETN, input SETN, output QN);
  DFFASRHQNx1_ASAP7_75t_R u (.CLK(CLK), .D(D), .RESETN(RESETN), .SETN(SETN), .QN(QN));
endmodule
"""


@pytest.mark.skipif(shutil.which("yosys") is None, reason="needs yosys")
@pytest.mark.parametrize("d,want", [(1, [0, 0, 0]), (0, [0, 1, 1])])
def test_asrh_model_follows_d_out_of_reset(tmp_path, d, want):
    (tmp_path / "t.v").write_text(T)
    r = subprocess.run(["yosys", "-p", f"read_verilog {K.ASRH}; read_verilog {tmp_path}/t.v; hierarchy -top t; proc; flatten; "
                        f"async2sync; opt_clean; sat -seq 3 -set RESETN 1 -set SETN 1 -set D {d} -show QN -set-init-zero t"],
                       capture_output=True, text=True)
    got = [int(m[1]) for m in re.finditer(r"^\s+\d+ \\QN\s+(\d+)", r.stdout, re.M)]
    assert got == want, r.stdout[-800:]
