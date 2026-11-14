"""face_guard_core.py: ports declared in the kit ft_ports.json (pushdown feed-through pairs) are skipped like clock/reset pins;
a kit without ft_ports.json keeps failing a port-to-port buffer as a feedthrough.
    python3 -m pytest -q physical/die_plan/hbm_arch_cores/test_face_guard_core_ft.py"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[2] / "tools" / "die_plan"
NET = r"""
module top(clk, a, o, ft_i, ft_o);
  input clk; input [1:0] a; output [1:0] o; input ft_i; output ft_o;
  wire _0_; wire _1_; wire [1:0] q;
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[0]$_DFF_P_  (.CLK(clk), .D(a[0]), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \u_bin_a.q[1]$_DFF_P_  (.CLK(clk), .D(a[1]), .QN(q[1]));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[0]$_DFF_P_  (.CLK(clk), .D(q[0]), .QN(_0_));
  DFFHQNx1_ASAP7_75t_R \u_bout_o.q[1]$_DFF_P_  (.CLK(clk), .D(q[1]), .QN(_1_));
  INVx3_ASAP7_75t_R _2_ (.A(_0_), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(_1_), .Y(o[1]));
  BUFx24_ASAP7_75t_R u_isl_ck0 (.A(ft_i), .Y(ft_o));
endmodule
"""


def run(tmp, with_ft):
    shutil.copy2(HERE / "face_guard_core.py", tmp)
    shutil.copy2(TOOLS / "face_guard.py", tmp)
    kd = tmp / "kit"
    kd.mkdir()
    (kd / "freeze.json").write_text(json.dumps(dict(design="top", clocks=["clk"], resets=[])))
    pins = [dict(bus=b, bit=i) for b in ("a", "o") for i in range(2)]
    pins += [dict(bus="ft_i", bit=None), dict(bus="ft_o", bit=None)]
    (kd / "pins.json").write_text(json.dumps(pins))
    if with_ft:
        (kd / "ft_ports.json").write_text(json.dumps(dict(ports=[dict(name="ft_i", direction="INPUT"),
                                                               dict(name="ft_o", direction="OUTPUT")])))
    (tmp / "net.v").write_text(NET)
    p = subprocess.run([sys.executable, "-I", str(tmp / "face_guard_core.py"), str(tmp / "net.v"), str(kd)],
                       capture_output=True, text=True)
    return p.returncode, json.loads((kd / "face_guard.json").read_text())


def test_declared_ft_ports_are_skipped(tmp_path):
    rc, r = run(tmp_path, True)
    assert rc == 0 and r["verdict"] == "PASS", r
    assert "ft_i" in r["skip_re"] and "ft_o" in r["skip_re"]


def test_undeclared_feedthrough_still_fails(tmp_path):
    rc, r = run(tmp_path, False)
    assert rc == 1 and "feedthrough" in r["fail_counts"], r
