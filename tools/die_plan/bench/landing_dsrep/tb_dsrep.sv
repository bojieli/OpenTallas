// DIE-S81-85 11-09 (iqf__t1 DSREP): lock-step bench, ot_dp_clk_landing DSREP=1 (gold) vs DSREP=4 (gate), W=513/514, WNEG=1.
// Same fclk/clk/rst/d into both; q, ready, fault compared at every clk edge.  Two reset epochs (re-align), random
// words every fclk edge, fclk phase 3/10 vs clk.  PASS needs >= 1000 compared cycles with ready=1 and 0 mismatches.
// The mutant build (run.sh: ot_meso_fifo.sv copy whose last select copy never turns on) must FAIL.
`timescale 1ns/1ps
module tb_dsrep;
  localparam int W = `TBW;
  logic clk = 0, fclk = 0, rst_n = 0;
  logic [W-1:0] d = '0;
  wire [W-1:0] q0, q1; wire r0, r1, e0, e1;
  ot_dp_clk_landing #(.W(W), .WNEG(1))            gold (.fclk(fclk), .clk(clk), .rst_n(rst_n), .d(d), .q(q0), .ready(r0), .fault(e0));
  ot_dp_clk_landing #(.W(W), .WNEG(1), .DSREP(4)) gate (.fclk(fclk), .clk(clk), .rst_n(rst_n), .d(d), .q(q1), .ready(r1), .fault(e1));
  always #5 clk = ~clk;
  initial begin #3; forever #5 fclk = ~fclk; end
  always @(posedge fclk) begin
    #1;
    for (int i = 0; i < W; i++) d[i] = $urandom % 2;
  end
  int cyc = 0, cmp = 0, rdy = 0, bad = 0;
  always @(posedge clk) begin
    #2;
    cyc++;
    if (cyc == 20) rst_n = 1;
    if (cyc == 1500) rst_n = 0;
    if (cyc == 1520) rst_n = 1;
    if (cyc > 20) begin
      cmp++;
      if (r0) rdy++;
      if (q0 !== q1 || r0 !== r1 || e0 !== e1) begin
        bad++;
        if (bad <= 5) $display("MISMATCH cyc %0d ready %b/%b fault %b/%b q_diff_bits %0d", cyc, r0, r1, e0, e1, $countones(q0 ^ q1));
      end
    end
    if (cyc == 3000) begin
      $display("TB_DSREP W=%0d compared %0d ready_cycles %0d mismatches %0d fault %b", W, cmp, rdy, bad, e0);
      if (bad == 0 && rdy >= 1000 && !e0) $display("TB_DSREP PASS"); else $display("TB_DSREP FAIL");
      $finish;
    end
  end
endmodule
