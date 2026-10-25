`timescale 1ns/1ps
// PATH-QC-RP1-F59 miter: ORIG_rp1 (main qfd_dv_s8_crh_rp1, renamed) vs qfd_dv_s8_crh_rp1 #(.MIF(1)) in lockstep with identical
// random stimulus (legal + illegal reads, kind-1 half/full table writes, other kinds, reset); behavioural SRAM model.
// Rows restricted to 0..15 so reads hit written rows and same-row read/write timing is exercised.
// Check every cycle after warm-up: new.q(t+1) == orig.q(t); fault(t) equal.  Also MIF=0 vs ORIG (must be 0 mismatches).
module tb;
  parameter integer N = 20000;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n;
  reg [7:0] cr_re; reg [8*24-1:0] cr_addr; reg tw_we; reg [1:0] tw_kind; reg [23:0] tw_addr; reg [511:0] tw_d;
  wire [255:0] o_q, n_q, z_q; wire o_f, n_f, z_f;
  ORIG_rp1 ov (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(o_q), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(o_f));
  qfd_dv_s8_crh_rp1 #(.MIF(1)) nv (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(n_q), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(n_f));
  qfd_dv_s8_crh_rp1 #(.MIF(0)) zv (.ck(ck), .rst_n(rst_n), .cr_re(cr_re), .cr_addr(cr_addr), .q(z_q), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr), .tw_d(tw_d), .fault(z_f));
  reg [255:0] o_q_d; always @(posedge ck) o_q_d <= o_q;
  integer c, i, e = 0, ef = 0, ez = 0, nz = 0, seed = 1, nw = 0, nr = 0;
  reg [63:0] xs;
  function [31:0] r32; input dummy; begin xs = xs ^ (xs << 13); xs = xs ^ (xs >> 7); xs = xs ^ (xs << 17); r32 = xs[31:0]; end endfunction
  reg [23:0] base; reg [3:0] row;
  task rnd; begin
    // reads: lanes share row + bank (legal), per-lane offsets addr[2:0]; occasionally illegal (fault path)
    row = r32(0); base = {10'd0, 6'd0, row, 4'd0} | (r32(0) & 24'h8);
    cr_re = (r32(0) & 3) == 0 ? 8'd0 : ((r32(0) & 15) == 0 ? r32(0) : 8'hff);
    for (i = 0; i < 8; i = i + 1) cr_addr[24*i +: 24] = ((r32(0) & 63) == 0) ? r32(0) : (base | (r32(0) & 7));
    // table writes: kind 1 mostly (half 0x/10/11), rows 0..15; other kinds + illegal addresses sometimes
    tw_we = (r32(0) & 1) == 0;
    tw_kind = ((r32(0) & 7) == 0) ? r32(0) : 2'd1;
    tw_addr = ((r32(0) & 31) == 0) ? r32(0) : {12'd0, 2'(r32(0)), 6'd0, 4'(r32(0))};
    for (i = 0; i < 16; i = i + 1) tw_d[32*i +: 32] = r32(0);
  end endtask
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    xs = 64'h9E3779B97F4A7C15 ^ {32'd0, seed};
    rst_n = 0; rnd;
    for (c = 0; c < N; c = c + 1) begin
      @(negedge ck);
      if (c > 4) rst_n = 1;
      if (c > 12) begin
        if (n_q !== o_q_d) begin e = e + 1; if (e < 4) $display("RP1 MISMATCH c=%0d", c); end
        if (n_f !== o_f) begin ef = ef + 1; if (ef < 4) $display("FAULT MISMATCH c=%0d", c); end
        if (z_q !== o_q || z_f !== o_f) ez = ez + 1;
        if (o_q_d != 0) nz = nz + 1;
        if (tw_we && tw_kind == 1) nw = nw + 1;
        if (cr_re[0]) nr = nr + 1;
      end
      rnd;
    end
    $display("MITER_RP1 N=%0d seed=%0d q_mism=%0d fault_mism=%0d mif0_vs_orig=%0d nonzero_cmp=%0d reads=%0d kind1_writes=%0d", N, seed, e, ef, ez, nz, nr, nw);
    $finish;
  end
endmodule
