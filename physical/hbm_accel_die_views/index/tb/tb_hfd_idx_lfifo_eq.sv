`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11: equivalence of the selector landing FIFO swap (hfd_idx_sel MEMV != 0): the flop
// hfd_idx_fifo (W 609, AW 7) and ot_fifo_sram_fwft (W 609, DEPTH 128, 3 x 128x256 macros) get the SAME pushes; each
// is drained by its own consumer with the same random pop enable (the selector's fire is a handshake on ne; credits
// return on pop).  Every popped record must equal, in order, the flop FIFO's; bubbles (flop ne, SRAM empty) are counted
// and must stay below 1%.  +MUT: one popped bit of the SRAM FIFO flipped -> must FAIL.
module tb_hfd_idx_lfifo_eq;
  localparam integer W = 609, AW = 7;
  reg ck = 0; always #0.5 ck = ~ck;
  reg rst_n = 0, we = 0; reg [W-1:0] wd = 0; reg rnd_pop = 0;
  wire ne_a, hv_b, ovf; wire [W-1:0] rd_a, hd_b; wire [AW:0] cnt;
  wire pop = ne_a && rnd_pop, pop_b = hv_b && rnd_pop;
  hfd_idx_fifo #(.W(W), .AW(AW)) u_a (.ck(ck), .rst_n(rst_n), .we(we), .wd(wd), .re(pop), .rd(rd_a), .ne(ne_a), .cnt(cnt));
  ot_fifo_sram_fwft #(.W(W), .DEPTH(1 << AW), .MACRO(2)) u_b (.clk(ck), .rst_n(rst_n), .push(we), .wdata(wd), .pop(pop_b),
    .hv(hv_b), .head(hd_b), .ovf(ovf));
  integer mut = 0, errs = 0, pushes = 0, pops = 0, pops_b = 0, bub = 0, cyc, occ = 0, i, seed = 7, phase;
  reg [W-1:0] qa [0:262143];
  wire [W-1:0] hd_m = hd_b ^ ((mut != 0 && pops_b == 300) ? {{(W-1){1'b0}}, 1'b1} : {W{1'b0}});
  always @(posedge ck) if (rst_n) begin
    if (pop) begin qa[pops] = rd_a; pops = pops + 1; end
    if (pop_b) begin
      if (pops_b >= pops) begin if (errs < 5) $display("ERR pop_b ahead"); errs = errs + 1; end
      else if (hd_m !== qa[pops_b]) begin if (errs < 5) $display("ERR record %0d differs", pops_b); errs = errs + 1; end
      pops_b = pops_b + 1;
    end
    if (ne_a && !hv_b) bub = bub + 1;
    if (ovf) begin if (errs < 5) $display("ERR ovf"); errs = errs + 1; end
  end
  initial begin
    if ($test$plusargs("MUT")) mut = 1;
    repeat (4) @(negedge ck); rst_n = 1; repeat (2) @(negedge ck);
    for (cyc = 0; cyc < 200000; cyc = cyc + 1) begin
      phase = (cyc / 5000) % 4;               // bursty: fill, drain, mixed, sparse
      occ = pushes - pops_b;
      we = (occ < (1 << AW) - 2) && (($random(seed) & 3) < ((phase == 0) ? 4 : (phase == 1) ? 0 : (phase == 2) ? 2 : 1));
      for (i = 0; i < W; i = i + 32) wd[i +: 32] = $random(seed);
      rnd_pop = (($random(seed) & 3) < ((phase == 0) ? 0 : (phase == 1) ? 4 : (phase == 2) ? 2 : 3));
      if (we) pushes = pushes + 1;
      @(negedge ck);
    end
    we = 0; rnd_pop = 1; repeat (400) @(negedge ck);
    $display("summary: %0d pushes, %0d / %0d pops, %0d bubble cycles, %0d errors", pushes, pops, pops_b, bub, errs);
    if (errs == 0 && pops == pushes && pops_b == pushes && pops > 1000 && bub * 100 < cyc) $display("HFD_IDX_LFIFO_EQ PASS"); else $display("HFD_IDX_LFIFO_EQ FAIL");
    $finish;
  end
endmodule
