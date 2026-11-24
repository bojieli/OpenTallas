"""reset_hold_check (QC-RSTCNT 11-24): needed reset hold of a bound die vs root counter + host contract."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_hold_check as RHC  # noqa: E402
import reset_tree as RT  # noqa: E402

SRC = """module p_src (input wire clk, input wire rst_n, output wire [0:0] o_x);
  wire a;
  core_a u_core (.clk(clk), .rst_n(rst_n), .y(a));
  ot_dp_dly #(.D(5)) u_d (.clk(clk), .d(a), .q(o_x));
endmodule
"""
CONS = """module p_cons (input wire clk, input wire rst_n, input wire [0:0] i_x);
  core_b u_core (.clk(clk), .rst_n(rst_n), .x(i_x));
endmodule
"""
TOP = """module top (input wire clk, input wire rst_n);
  wire [0:0] w;
  p_src s0 (.clk(clk), .rst_n(rst_n), .o_x(w));
  p_cons c0 (.clk(clk), .rst_n(rst_n), .i_x(w));
endmodule
"""


def bind_dir(tmp_path, rel_src=10, rel_cons=4):
    d = tmp_path / "bind"
    (d / "rtl").mkdir(parents=True)
    (d / "rtl" / "p_src.sv").write_text(SRC)
    (d / "rtl" / "p_cons.sv").write_text(CONS)
    (d / "rtl" / "top.sv").write_text(TOP)
    (d / "bind_reset.json").write_text(json.dumps({"parts": {"s0": {"release": rel_src}, "c0": {"release": rel_cons}}}))
    return d


def test_need_is_transport_minus_release_gap(tmp_path):
    d = bind_dir(tmp_path)
    rows = RHC.measure(str(d / "rtl"), "top.sv", str(d / "bind_reset.json"), log=lambda *a: None)
    wave = [r for r in rows if r["cls"] == "wave"]
    # core_a released at 10, 5-cycle reset-less delay line, core_b released at 4 + 1: needs 10 + 5 - 5 = 10 clk of hold
    assert [(r["inst"], r["pin"], r["need_hold"]) for r in wave] == [("c0", "u_core.x", 10)]
    assert RHC.short_at(rows, 9)["pins"] == 1 and RHC.short_at(rows, 10)["pins"] == 0


def test_uniform_shift_leaves_need_unchanged(tmp_path):
    a = bind_dir(tmp_path / "a")
    b = bind_dir(tmp_path / "b", 10 + 259, 4 + 259)
    na = RHC.summary(RHC.measure(str(a / "rtl"), "top.sv", str(a / "bind_reset.json"), log=lambda *x: None))["need"]
    nb = RHC.summary(RHC.measure(str(b / "rtl"), "top.sv", str(b / "bind_reset.json"), log=lambda *x: None))["need"]
    assert na == nb == 10


def test_main_report_only_and_enforce(tmp_path, capsys):
    d = bind_dir(tmp_path)
    out = tmp_path / "o.json"
    assert RHC.main([str(d), "--top", "top.sv", "--counter", "5", "--json", str(out)]) == 0      # report-only
    r = json.loads(out.read_text())
    assert r["verdict"] == "SHORT" and r["need"] == 10 and r["short"]["pins"] == 1
    assert RHC.main([str(d), "--top", "top.sv", "--counter", "5", "--enforce"]) == 1
    assert RHC.main([str(d), "--top", "top.sv", "--counter", "5", "--host-contract", "5", "--enforce"]) == 0
    assert "RESET-HOLD PASS" in capsys.readouterr().out


def test_provided_reads_the_plan_counter(tmp_path):
    from test_reset_hold import hold_plan
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(hold_plan(256)))
    assert RHC.provided(str(p), 128) == dict(counter=256 + RT.LOCKQ_EXTRA, host_contract=128, total=256 + RT.LOCKQ_EXTRA + 128)
