`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11: cycle equivalence of the selector landing FIFO swap (hfd_idx_sel MEMV != 0): the flop
// hfd_idx_fifo (W 609, AW 7) and ot_fifo_sram_fwft (W 609, DEPTH 128, 3 x 128x256 macros) driven by the SAME pushes and
// pops (pop = ne && random, as the selector's fire; pushes bounded by the scorer credit = depth) must show the same
// not-empty flag and the same head every cycle.  +MUT: one head bit of the SRAM FIFO flipped -> must FAIL.
module tb_hfd_idx_lfifo_eq;
  localparam integer W = 609, AW = 7;
  reg ck = 0; always #0.5 ck = ~ck;
  reg rst_n = 0, we = 0; reg [W-1:0] wd = 0; reg rnd_pop = 0;
  wire ne_a, hv_b, ovf; wire [W-1:0] rd_a, hd_b; wire [AW:0] cnt;
  wire pop = ne_a && rnd_pop;
  hfd_idx_fifo #(.W(W), .AW(AW)) u_a (.ck(ck), .rst_n(rst_n), .we(we), .wd(wd), .re(pop), .rd(rd_a), .ne(ne_a), .cnt(cnt));
  ot_fifo_sram_fwft #(.W(W), .DEPTH(1 << AW), .MACRO(2)) u_b (.clk(ck), .rst_n(rst_n), .push(we), .wdata(wd), .pop(pop),
    .hv(hv_b), .head(hd_b), .ovf(ovf));
  integer mut = 0, errs = 0, pushes = 0, pops = 0, cyc, occ = 0, i, seed = 7, phase;
  wire [W-1:0] hd_m = hd_b ^ ((mut != 0 && pops == 300) ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
  always @(posedge ck) if (rst_n) begin
    if (ne_a !== hv_b || (ne_a && rd_a !== hd_m) || ovf) begin
      if (errs < 5) $display("ERR cyc %0d ne %b/%b ovf %b", cyc, ne_a, hv_b, ovf);
      errs = errs + 1;
    end
    if (pop) pops = pops + 1;
  end
  initial begin
    if ($test$plusargs("MUT")) mut = 1;
    repeat (4) @(negedge ck); rst_n = 1; repeat (2) @(negedge ck);
    for (cyc = 0; cyc < 200000; cyc = cyc + 1) begin
      phase = (cyc / 5000) % 4;               // bursty: fill, drain, mixed, sparse
      occ = occ + we - (ne_a && rnd_pop);
      we = (occ < (1 << AW) - 2) && (($random(seed) & 3) < ((phase == 0) ? 4 : (phase == 1) ? 0 : (phase == 2) ? 2 : 1));
      for (i = 0; i < W; i = i + 32) wd[i +: 32] = $random(seed);
      rnd_pop = (($random(seed) & 3) < ((phase == 0) ? 0 : (phase == 1) ? 4 : (phase == 2) ? 2 : 3));
      if (we) pushes = pushes + 1;
      @(negedge ck);
    end
    we = 0; rnd_pop = 1; repeat (400) @(negedge ck);
    $display("summary: %0d pushes, %0d pops, %0d mismatching cycles", pushes, pops, errs);
    if (errs == 0 && pops == pushes && pops > 1000) $display("HFD_IDX_LFIFO_EQ PASS"); else $display("HFD_IDX_LFIFO_EQ FAIL");
    $finish;
  end
endmodule
