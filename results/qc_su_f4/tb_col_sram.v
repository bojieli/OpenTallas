// QC-SU-F4: functional equivalence bench, column view ot_sram_1r1w_1024x256_m1b2_r2c2_ns vs the m2 reference
// ot_sram_1r1w_1024x256_m2_r2c2 (behavioural models from sram_gen.py).  Same random stream into both: random read /
// write enables, addresses (incl. same-address read+write = read-before-write), data and per-bit masks; rd_out compared
// every cycle after a read.  Repair pins tied 0 as in the cores.  A mutant run (+define+MUT) flips one written bit of the
// column view's data input on one write and must be caught.
`timescale 1ns/1ps
module tb;
  reg clk = 0; always #0.5 clk = ~clk;
  reg rce, wce; reg [9:0] ra, wa; reg [255:0] wd, wm;
  wire [255:0] q_ref, q_col;
`ifdef MUT
  wire [255:0] wd_c = (wa == 10'd77 && wce) ? (wd ^ 256'd1 << 200) : wd;
`else
  wire [255:0] wd_c = wd;
`endif
  ot_sram_1r1w_1024x256_m2_r2c2 u_ref (.clk(clk), .r_ce_in(rce), .r_addr_in(ra), .rd_out(q_ref), .w_ce_in(wce),
      .w_addr_in(wa), .wd_in(wd), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
  ot_sram_1r1w_1024x256_m1b2_r2c2_ns u_col (.clk(clk), .r_ce_in(rce), .r_addr_in(ra), .rd_out(q_col), .w_ce_in(wce),
      .w_addr_in(wa), .wd_in(wd_c), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(20'd0), .cr_en(2'b00), .cr_sel(16'd0));
  integer cyc, reads, mism, nz, k; reg rd_d;
  function [255:0] rnd256; input dummy; integer j; begin for (j = 0; j < 8; j = j + 1) rnd256[32*j +: 32] = $random; end endfunction
  initial begin
    reads = 0; mism = 0; nz = 0; rd_d = 0; k = 32'h0F4C0115; k = $random(k);
    for (cyc = 0; cyc < 200000; cyc = cyc + 1) begin
      @(negedge clk);
      if (rd_d) begin reads = reads + 1; if (q_ref !== q_col) mism = mism + 1; if (q_ref != 0) nz = nz + 1; end
      rce = ($random & 3) != 0; wce = ($random & 1);
      ra = (cyc < 40000) ? (cyc % 1024) : $random; wa = ($random & 7) == 0 ? ra : $random;   // 1/8 same-address
      wd = rnd256(0); wm = ($random & 3) == 0 ? {256{1'b1}} : rnd256(0);
      if (cyc < 2048) begin rce = 0; wce = 1; wa = cyc % 1024; wm = {256{1'b1}}; end        // fill every word once
      rd_d = rce;
    end
    $display("COLSRAM cycles %0d reads %0d nonzero %0d mismatches %0d %s", cyc, reads, nz, mism, mism == 0 ? "PASS" : "FAIL");
    $finish;
  end
endmodule
