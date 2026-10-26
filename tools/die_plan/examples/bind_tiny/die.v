// bind_tiny as-built die (GEN style: no ports, relays / clock / reset / fault cells without RTL)
module tdie ();
  wire ck; wire rs; wire rs_r1;
  wire [7:0] y0; wire [7:0] y0_r1; wire [7:0] y0_r2; wire [7:0] y1; wire [7:0] y1_r1;
  wire f0; wire f1; wire fo; wire [8:0] sq;
  tclkrx clk_rx (.pll(1'b0), .ck(ck));
  trstsync rst_s (.ck(ck), .q(rs));
  trep rst_rep0 (.clk(ck), .d(rs), .q(rs_r1));
  par #(.K(1)) p0 (.ck(ck), .rst_n(rs_r1), .x(y1_r1), .id(4'd5), .y(y0), .f(f0));
  par #(.K(2)) p1 (.ck(ck), .rst_n(rs), .x(y0_r2), .id(4'd6), .y(y1), .f(f1));
  trly_8 rly0 (.ck(ck), .a(y0), .b(y0_r1));
  trly_8 rly1 (.ck(ck), .a(y0_r1), .b(y0_r2));
  trly_8 rly2 (.ck(ck), .a(y1), .b(y1_r1));
  tfor2 for0 (.a0(f0), .a1(f1), .y(fo));
  lf_sink snk (.clk(ck), .flt(fo), .d0(y0), .d1(y1), .q(sq));
endmodule
