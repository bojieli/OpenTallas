"""ROOT-RST 2026-10-19: textbook_lint reset_landing -- a reset INPUT port reaching more than rst_land_max sinks through
BUF / INV (no landing register at the face) is a finding, REFUSE tier when the gate lists the check (pre_route_gate
GATE_REFUSE).  Cases: kp4_dec-style port -> buffer tree -> 4 hard-child rst_n pins; a sync-reset port -> AND gates in
front of D; a landed port (rst_l0 D only); an async synchroniser (2 reset pins); S81 rsv_* data ports are not resets."""
import json

import textbook_lint as TL

HDR = "module top (clk, {ports});\n  input clk;\n"


def netlist(body, ports):
    decl = "".join(f"  {d} {p};\n" for d, p in ports)
    return HDR.format(ports=", ".join(p for _, p in ports)) + decl + body + "endmodule\n"


def lint(tmp_path, text, **kw):
    f = tmp_path / "n.v"
    f.write_text(text)
    return TL.run(str(f), None, kw.pop("th", None), "top", kw.pop("mode", "refuse"),
                  refuse_checks=kw.pop("refuse_checks", ("reset_landing",)))


UNLANDED = netlist("""  wire r1, r2;
  BUFx4_ASAP7_75t_R b0 (.A(rst_n), .Y(r1));
  BUFx4_ASAP7_75t_R b1 (.A(r1), .Y(r2));
  ot_child u_syn (.clk(clk), .rst_n(r2), .q(q0));
  ot_child u_chn (.clk(clk), .rst_n(r2), .q(q1));
  ot_child u_dly (.clk(clk), .rst_n(r1), .q(q2));
  ot_child u_out (.clk(clk), .rst_n(r1), .q(q3));
""", [("input", "rst_n"), ("output", "q0"), ("output", "q1"), ("output", "q2"), ("output", "q3")])

LANDED = netlist("""  wire l0, l1, n0, n1, x;
  DFFHQNx1_ASAP7_75t_R rst_l0 (.CLK(clk), .D(rst_n), .QN(n0));
  INVx1_ASAP7_75t_R i0 (.A(n0), .Y(l0));
  DFFHQNx1_ASAP7_75t_R rst_l1 (.CLK(clk), .D(l0), .QN(n1));
  INVx1_ASAP7_75t_R i1 (.A(n1), .Y(l1));
  ot_child u_syn (.clk(clk), .rst_n(l1), .q(q0));
  ot_child u_chn (.clk(clk), .rst_n(l1), .q(q1));
  ot_child u_dly (.clk(clk), .rst_n(l1), .q(q2));
""", [("input", "rst_n"), ("output", "q0"), ("output", "q1"), ("output", "q2")])

SYNC_AND = netlist("""  wire a0, a1, a2, n0, n1, n2;
  AND2x2_ASAP7_75t_R g0 (.A(rst_n), .B(d), .Y(a0));
  AND2x2_ASAP7_75t_R g1 (.A(rst_n), .B(d), .Y(a1));
  AND2x2_ASAP7_75t_R g2 (.A(rst_n), .B(d), .Y(a2));
  DFFHQNx1_ASAP7_75t_R f0 (.CLK(clk), .D(a0), .QN(n0));
  DFFHQNx1_ASAP7_75t_R f1 (.CLK(clk), .D(a1), .QN(n1));
  DFFHQNx1_ASAP7_75t_R f2 (.CLK(clk), .D(a2), .QN(q));
""", [("input", "rst_n"), ("input", "d"), ("output", "q")])

ASYNC_SYNC = netlist("""  wire n0, s0;
  ASYNC_DFFHx2_ASAP7_75t_R s_0 (.CLK(clk), .D(d), .RESET(rst_n), .SET(t), .QN(n0));
  ASYNC_DFFHx2_ASAP7_75t_R s_1 (.CLK(clk), .D(n0), .RESET(rst_n), .SET(t), .QN(q));
""", [("input", "rst_n"), ("input", "d"), ("input", "t"), ("output", "q")])

RSV = netlist("""  wire r1;
  BUFx4_ASAP7_75t_R b0 (.A(rsv_08), .Y(r1));
  ot_child u0 (.clk(clk), .rst_n(r1), .q(q0));
  ot_child u1 (.clk(clk), .rst_n(r1), .q(q1));
  ot_child u2 (.clk(clk), .rst_n(r1), .q(q2));
""", [("input", "rsv_08"), ("output", "q0"), ("output", "q1"), ("output", "q2")])


def test_unlanded_reset_tree_to_hard_children_refuses(tmp_path):
    r = lint(tmp_path, UNLANDED)
    assert r["verdict"] == "REFUSE" and r["refusing_checks"] == ["reset_landing"]
    (rec,) = r["metrics"]["reset_landing"]
    assert rec == {"port": "rst_n", "sinks": 4, "flops": 0, "macros": 4}
    assert "landing register" in r["findings"]["reset_landing"][0]


def test_route_time_lint_only_warns(tmp_path):
    # the closure loop's route-time lint keeps its REFUSE_CHECKS: an in-flight route is never stopped by the new check
    assert "reset_landing" not in TL.REFUSE_CHECKS
    r = lint(tmp_path, UNLANDED, refuse_checks=TL.REFUSE_CHECKS)
    assert r["verdict"] == "WARN" and "reset_landing" in r["findings"]


def test_landed_reset_passes(tmp_path):
    r = lint(tmp_path, LANDED)
    assert "reset_landing" not in r["findings"]
    assert r["metrics"]["reset_landing"] == [{"port": "rst_n", "sinks": 1, "flops": 1, "macros": 0}]


def test_sync_reset_gates_count_as_sinks(tmp_path):
    r = lint(tmp_path, SYNC_AND)
    assert r["verdict"] == "REFUSE"
    assert r["metrics"]["reset_landing"][0]["sinks"] == 3


def test_async_synchroniser_two_pins_passes(tmp_path):
    r = lint(tmp_path, ASYNC_SYNC)
    assert "reset_landing" not in r["findings"]
    assert r["metrics"]["reset_landing"][0]["sinks"] == 2


def test_threshold_and_waiver(tmp_path):
    assert lint(tmp_path, UNLANDED, th={"rst_land_max": 4})["verdict"] == "PASS"
    f = tmp_path / "n.v"
    f.write_text(UNLANDED)
    r = TL.run(str(f), None, None, "top", "refuse", waive=("reset_landing",), refuse_checks=("reset_landing",))
    assert r["verdict"] != "REFUSE" and r["waived"] == ["reset_landing"]


def test_declared_reset_and_rsv_data_port(tmp_path):
    assert lint(tmp_path, RSV)["metrics"]["reset_landing"] == []          # rsv_* is not a reset name
    r = lint(tmp_path, RSV, th={"reset_ports": "rsv_08"})                 # ... unless the kit declares it
    assert r["verdict"] == "REFUSE"


def test_info_line(tmp_path, capsys):
    f = tmp_path / "n.v"
    f.write_text(UNLANDED)
    rc = TL.main(["check", "--netlist", str(f), "--top", "top", "--mode", "refuse", "--refuse-checks",
                  "clock_domain,high_fanout,wire_reach,reset_landing"])
    out = capsys.readouterr().out
    assert rc == 3
    info = next(ln for ln in out.splitlines() if ln.startswith("textbook_lint: INFO reset_landing "))
    assert json.loads(info.split(" ", 3)[3])["ports"][0]["sinks"] == 4
    assert "textbook_lint: REFUSE reset_landing: reset port rst_n" in out
