"""Kit-netlist core tracer (FABLE-FIX-S81-LEAF 11-19): nested cores, buffer / flop chains, kept sub-modules."""
import importlib.util
from pathlib import Path

H = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("ccfn", H / "core_conns_from_netlist.py")
N = importlib.util.module_from_spec(_s); _s.loader.exec_module(N)

NET = r"""
module ot_dp_rrelay(clk, d, q);
  input clk;
  input [1:0] d;
  output [1:0] q;
  wire [1:0] n;
  DFFHQNx1_ASAP7_75t_R \r[0]$_DFF_P_  (
    .CLK(clk),
    .D(d[0]),
    .QN(n[0])
  );
  INVx1_ASAP7_75t_R _1_ (
    .A(n[0]),
    .Y(q[0])
  );
  DFFHQNx1_ASAP7_75t_R \r[1]$_DFF_P_  (
    .CLK(clk),
    .D(d[1]),
    .QN(n[1])
  );
  INVx1_ASAP7_75t_R _2_ (
    .A(n[1]),
    .Y(q[1])
  );
endmodule

module top(clk, pi);
  input clk;
  input pi;
  wire \u_bound.u_core.a_o[1] ;
  wire \u_bound.u_core.a_o[0] ;
  wire [1:0] rq;
  wire b0;
  wire f0;
  wire g0;
  wire [3:0] \u_bound.u_core.x ;
  core_a \u_bound.u_core.g_q[0].u_a  (
    .ck(clk),
    .o({ \u_bound.u_core.a_o[1] , \u_bound.u_core.a_o[0]  }),
    .i({ g0, pi, 2'h0 })
  );
  ot_dp_rrelay \u_bound.u_r  (
    .clk(clk),
    .d({ \u_bound.u_core.a_o[1] , \u_bound.u_core.a_o[0]  }),
    .q(rq)
  );
  BUFx2_ASAP7_75t_R _5_ (
    .A(rq[0]),
    .Y(b0)
  );
  DFFHQNx1_ASAP7_75t_R _6_ (
    .CLK(clk),
    .D(b0),
    .QN(f0)
  );
  NAND2x1_ASAP7_75t_R _7_ (
    .A(rq[1]),
    .B(pi),
    .Y(g0)
  );
  core_b \u_bound.u_core.u_b  (
    .ck(clk),
    .d({ g0, f0, \u_bound.u_core.a_o[0] , rq[1] }),
    .q(\u_bound.u_core.x )
  );
endmodule
"""
CORES = {
    "u_bound.u_core.g_q[0].u_a": ("u_w.g_q[0].u_a", dict(ck="INPUT", o="OUTPUT", i="INPUT"), dict(o=[1, 0], i=[3, 2, 1, 0])),
    "u_bound.u_core.u_b": ("u_w.u_b", dict(ck="INPUT", d="INPUT", q="OUTPUT"), dict(d=[3, 2, 1, 0], q=[3, 2, 1, 0])),
}


def test_nested_cores_through_buffer_flop_and_kept_submodule():
    res = N.trace(NET, CORES)
    assert res["top"] == "top" and res["cores_found"] == ["u_w.g_q[0].u_a", "u_w.u_b"]
    got = {(p["core"], p["port"], p["partner"], p["stages_existing"], tuple(map(tuple, p["bit_ranges"]))) for p in res["paths"]}
    assert got == {
        ("u_w.u_b", "d", "u_w.g_q[0].u_a.o", 0, ((1, 1),)),      # direct wire, bit 1 <- o[0]
        ("u_w.u_b", "d", "u_w.g_q[0].u_a.o", 1, ((0, 0),)),      # kept relay module: 1 flop, bit 0 <- o[1]
        ("u_w.u_b", "d", "u_w.g_q[0].u_a.o", 2, ((2, 2),)),      # relay + buffer + flop: 2 stages
    }
    # logic, top ports and constants end the walk and are only counted
    assert res["stops"] == {"logic": 2, "top port": 3, "constant": 2}


def test_expression_bits():
    w = {"a": (3, 0), "x.y[2]": (0, 0)}
    assert N.expr_bits("{ a[2:1], \\x.y[2] , 1'h0, a[0] }", w) == [("a", 2), ("a", 1), ("x.y[2]", 0), None, ("a", 0)]
    assert N.expr_bits("a", w) == [("a", 3), ("a", 2), ("a", 1), ("a", 0)]
