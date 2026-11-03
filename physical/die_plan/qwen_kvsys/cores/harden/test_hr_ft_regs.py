"""DIE-KV-62/hr 11-02: hr_ft_regs face register on a declared wire feed-through."""
import importlib.util
import json
from pathlib import Path

import pytest

H = Path(__file__).resolve().parent


def _m():
    spec = importlib.util.spec_from_file_location("hr_ft_regs_t", H / "hr_ft_regs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RTL = """module c(ck, rst_n, f, f_i, x);
  input [0:0] ck;
  input [0:0] rst_n;
  output [1:0] f;
  wire [1:0] f;
  input [1:0] f_i;
  wire [1:0] f_i;
  output x;
  assign \\u.f [1] = f_i[1];
  assign f[1] = f_i[1];
  assign f[0] = f_i[0];
  assign x = 1'b0;
endmodule
"""
SPEC = dict(regs=[dict(out="f", clock="ck", reset_n="rst_n", reset_value=0)], ruling="r", reason="why")


def test_ft_register_replaces_port_wires():
    M = _m()
    out, rep = M.transform(RTL, SPEC)
    assert "assign f[1] = f_i[1];" not in out and "assign f[0] = f_i[0];" not in out
    assert "always @(posedge ck, negedge rst_n)" in out and "ot_ftreg_f <= {f_i[1], f_i[0]};" in out
    assert "if (!rst_n) ot_ftreg_f <= 2'd0;" in out and "assign f = ot_ftreg_f;" in out
    assert out.index("assign f = ot_ftreg_f;") < out.index("endmodule")
    assert "assign \\u.f [1] = f_i[1];" in out         # internal alias untouched
    assert rep == [dict(out="f", src=["f_i[0]", "f_i[1]"], clock="ck", reset_n="rst_n", reset_value=0,
                        added_edges=1, flops=2)]


def test_ft_register_fail_closed():
    M = _m()
    with pytest.raises(SystemExit, match="direct port assigns"):
        M.transform(RTL.replace("  assign f[0] = f_i[0];\n", ""), SPEC)
    with pytest.raises(SystemExit, match="no input port nope"):
        M.transform(RTL, dict(SPEC, regs=[dict(SPEC["regs"][0], clock="nope")]))
    with pytest.raises(SystemExit, match="ruling and reason"):
        M.transform(RTL, dict(SPEC, ruling=""))


def test_recipes_hr_core_guard_order():
    r = json.load(open(H / "recipes_kv.json"))
    assert "u_native__legacy_tk" in r["qkd_hr_core_guard"]["timed_face"]["buses"]
    assert r["qkd_hr_core_guard"]["hard_children"].endswith("qkd_hr_core_guard_macro_plan.json")
    o = r["qkd_hr_core_order"]
    assert "u_chain__chain_fault" not in o["timed_face"]["buses"]          # a feed-through is never a timed face
    assert o["ft_face_regs"]["regs"][0]["out"] == "u_chain__chain_fault"
