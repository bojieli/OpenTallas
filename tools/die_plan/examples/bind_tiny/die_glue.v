// bind_tiny variant (test_glue_transport_absorbed, TOK-QK/C 10-24 C1): the two partitions' fault bits are joined by
// glue of a dissolved parent (jn, mapped to the sink partition S) and reach the sink over two relays -- the shape of the
// KV host SerDes rx_v = AND(sys_SW, sys_SE) whose as-built transport the binder kept as an intra ot_dp_dly (valid 4 late)
module tdie ();
  wire ck; wire rs; wire rs_r1;
  wire [7:0] y0; wire [7:0] y0_r1; wire [7:0] y0_r2; wire [7:0] y1; wire [7:0] y1_r1;
  wire f0; wire f1; wire fj; wire fj_r1; wire fj_r2; wire [8:0] sq;
  tclkrx clk_rx (.pll(1'b0), .ck(ck));
  trstsync rst_s (.ck(ck), .q(rs));
  trep rst_rep0 (.clk(ck), .d(rs), .q(rs_r1));
  par #(.K(1)) p0 (.ck(ck), .rst_n(rs_r1), .x(y1_r1), .id(4'd5), .y(y0), .f(f0));
  par #(.K(2)) p1 (.ck(ck), .rst_n(rs), .x(y0_r2), .id(4'd6), .y(y1), .f(f1));
  trly_8 rly0 (.ck(ck), .a(y0), .b(y0_r1));
  trly_8 rly1 (.ck(ck), .a(y0_r1), .b(y0_r2));
  trly_8 rly2 (.ck(ck), .a(y1), .b(y1_r1));
  jn j0 (.a(f0), .b(f1), .y(fj));
  trly_1 rlyf0 (.ck(ck), .a(fj), .b(fj_r1));
  trly_1 rlyf1 (.ck(ck), .a(fj_r1), .b(fj_r2));
  lf_sink snk (.clk(ck), .flt(fj_r2), .d0(y0), .d1(y1), .q(sq));
endmodule
// structural join (dissolved; its glue is re-homed to the sink partition)
module jn (input wire a, input wire b, output wire y);
  assign y = a & b;
endmodule
