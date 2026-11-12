// CLAND-SLEW-1 (GEN-CLASS-1 11-12): lock-step bench of the count-aligned rings with the reach-based read-select
// copies: ot_dp_clk_landing_ca DSREP=1 (gold) vs DSREP=8 (gate), and ot_dp_clk_landing_cas DSREP=1 vs 8, W = `TBW.
// Same fclk/clk/starts/d into all; q, ready, fault compared at every clk edge.  Two reset epochs, random words every
// fclk edge, fclk phase 3/10 vs clk.  PASS needs >= 1000 compared cycles with ready=1 and 0 mismatches.  The mutant
// build (run_ca.sh: ot_meso_fifo.sv copy whose last select copy never turns on) must FAIL.
`timescale 1ns/1ps
module tb_dsrep_ca;
  localparam int W = `TBW;
  localparam int K = 2;
  logic clk = 0, fclk = 0, rst_n = 0, t_rst_n = 0;
  logic [W-1:0] d = '0;
  wire [W-1:0] qa0, qa1, qs0, qs1; wire ra0, ra1, rs0, rs1, ea0, ea1, es0, es1;
  ot_dp_clk_landing_ca  #(.W(W), .DEPTH(4), .K(K))             ca0 (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d), .q(qa0), .ready(ra0), .fault(ea0));
  ot_dp_clk_landing_ca  #(.W(W), .DEPTH(4), .K(K), .DSREP(8))  ca1 (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .d(d), .q(qa1), .ready(ra1), .fault(ea1));
  ot_dp_clk_landing_cas #(.W(W), .DEPTH(4))                    cs0 (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(1'b1), .strap_k(6'(K)), .d(d), .q(qs0), .ready(rs0), .fault(es0));
  ot_dp_clk_landing_cas #(.W(W), .DEPTH(4), .DSREP(8))         cs1 (.fclk(fclk), .t_rst_n(t_rst_n), .clk(clk), .rst_n(rst_n), .rst_xn(1'b1), .strap_k(6'(K)), .d(d), .q(qs1), .ready(rs1), .fault(es1));
  always #5 clk = ~clk;
  initial begin #3; forever #5 fclk = ~fclk; end
  always @(posedge fclk) begin
    #1;
    t_rst_n <= rst_n;                              // sender start forwarded with fclk
    for (int i = 0; i < W; i++) d[i] = $urandom % 2;
  end
  int cyc = 0, cmp = 0, rdy = 0, bad = 0, flt = 0;
  always @(posedge clk) begin
    #2;
    cyc++;
    if (cyc == 20) rst_n = 1;
    if (cyc == 1500) rst_n = 0;
    if (cyc == 1520) rst_n = 1;
    if (cyc > 20) begin
      cmp++;
      if (ra0 && rs0) rdy++;
      if (ea0 || es0) flt++;
      if (qa0 !== qa1 || ra0 !== ra1 || ea0 !== ea1 || qs0 !== qs1 || rs0 !== rs1 || es0 !== es1) begin
        bad++;
        if (bad <= 3) $display("MISMATCH cyc %0d ca q %0d/%0d r %b/%b f %b/%b  cas q %0d/%0d r %b/%b f %b/%b", cyc,
                               qa0 == qa1, 1, ra0, ra1, ea0, ea1, qs0 == qs1, 1, rs0, rs1, es0, es1);
      end
    end
    if (cyc == 3000) begin
      $display("TB_DSREP_CA W=%0d compared %0d ready_cycles %0d mismatches %0d fault %0d", W, cmp, rdy, bad, flt);
      if (bad == 0 && rdy >= 1000) $display("TB_DSREP_CA PASS"); else $display("TB_DSREP_CA FAIL");
      $finish;
    end
  end
endmodule
