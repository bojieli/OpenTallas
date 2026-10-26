`timescale 1ns/1ps
// PATH-QC-SRAMIF miter: ORIG (main vm8 leaf) vs NEW (MIF=1) in lockstep, random stimulus, N cycles.
// Check: new.q(t+1) == orig.q(t) every cycle after warm-up; fault(t) equal every cycle.
module tb;
  parameter integer N = 20000;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n;
  // btab
  reg bs_re; reg [23:0] bs_addr; reg tw_we; reg [1:0] tw_kind; reg [8:0] tw_addr; reg [1023:0] tw_data;
  wire [255:0] o_bq, n_bq; wire o_f, n_f;
  qfd_dv_s8x_btab #(.MIF(1), .ROW_WRITE_RELAY(0)) ob (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(o_bq), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(o_f));
  qfd_dv_s8x_btab #(.MIF(1), .ROW_WRITE_RELAY(1), .WR_HALF_CYCLE(1), .RD_HALF_CYCLE(1)) nb (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(n_bq), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(n_f));
  qfd_dv_s8x_btab #(.MIF(0)) zb (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault());
  // prog
  reg p_re; reg [8:0] p_idx; reg [1:0] tw_kind_p;
  wire [456:0] o_pq, n_pq, z_pq;
  qfd_dv_s8x_prog #(.MIF(1), .ROW_WRITE_RELAY(0)) op (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(o_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  qfd_dv_s8x_prog #(.MIF(1), .ROW_WRITE_RELAY(1), .WR_HALF_CYCLE(1), .RD_HALF_CYCLE(1)) np (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(n_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  qfd_dv_s8x_prog #(.MIF(0)) zp (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(z_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  reg [255:0] o_bq_d; reg [456:0] o_pq_d;
  always @(posedge ck) begin o_bq_d <= o_bq; o_pq_d <= o_pq; end
  integer c, i, eb = 0, ep = 0, ef = 0, ez = 0, nzb = 0, nzp = 0, rdb = 0;

  // Observe the inputs consumed by real SRAMs BEFORE NBA at each rising clock edge.
  genvar br;
  generate for (br=0; br<4; br=br+1) begin : g_bwrite_check
    always @(posedge ck) if (c > 12) begin
      if (ob.g_btb[br].u_m.r_ce_in !== nb.g_btb[br].u_m.r_ce_in) $fatal(1,"BTAB consumed readenable row%0d c%0d",br,c);
      if (ob.g_btb[br].u_m.r_ce_in && ob.g_btb[br].u_m.r_addr_in !== nb.g_btb[br].u_m.r_addr_in) $fatal(1,"BTAB consumed readaddr row%0d c%0d",br,c);
      if (ob.g_btb[br].u_m.w_ce_in !== nb.g_btb[br].u_m.w_ce_in) $fatal(1,"BTAB consumed enable row%0d c%0d",br,c);
      if (ob.g_btb[br].u_m.w_ce_in && ({ob.g_btb[br].u_m.w_addr_in,ob.g_btb[br].u_m.wd_in} !== {nb.g_btb[br].u_m.w_addr_in,nb.g_btb[br].u_m.wd_in})) $fatal(1,"BTAB consumed write row%0d c%0d",br,c);
    end
  end
  for (br=0;br<2;br=br+1) begin : g_pwrite_check
    always @(posedge ck) if (c > 12) begin
      if ({op.g_prog[br].u_lo.r_ce_in,op.g_prog[br].u_hi.r_ce_in} !== {np.g_prog[br].u_lo.r_ce_in,np.g_prog[br].u_hi.r_ce_in}) $fatal(1,"PROG consumed readenable bank%0d c%0d",br,c);
      if (op.g_prog[br].u_lo.r_ce_in && {op.g_prog[br].u_lo.r_addr_in,op.g_prog[br].u_hi.r_addr_in} !== {np.g_prog[br].u_lo.r_addr_in,np.g_prog[br].u_hi.r_addr_in}) $fatal(1,"PROG consumed readaddr bank%0d c%0d",br,c);
      if ({op.g_prog[br].u_lo.w_ce_in,op.g_prog[br].u_hi.w_ce_in} !== {np.g_prog[br].u_lo.w_ce_in,np.g_prog[br].u_hi.w_ce_in}) $fatal(1,"PROG consumed enable bank%0d c%0d",br,c);
      if (op.g_prog[br].u_lo.w_ce_in && ({op.g_prog[br].u_lo.w_addr_in,op.g_prog[br].u_lo.wd_in,op.g_prog[br].u_hi.w_addr_in,op.g_prog[br].u_hi.wd_in} !== {np.g_prog[br].u_lo.w_addr_in,np.g_prog[br].u_lo.wd_in,np.g_prog[br].u_hi.w_addr_in,np.g_prog[br].u_hi.wd_in})) $fatal(1,"PROG consumed write bank%0d c%0d",br,c);
    end
  end endgenerate

  integer seed = 1;
  reg [63:0] xs;
  function [31:0] r32; input dummy; begin xs = xs ^ (xs << 13); xs = xs ^ (xs >> 7); xs = xs ^ (xs << 17); r32 = xs[31:0]; end endfunction
  task rnd; begin
    bs_re = (r32(0) & 3) != 0;
    bs_addr = {((r32(0) & 31) == 0) ? r32(0) : 15'd0, 9'd0} | (r32(0) & 9'h1ff);
    tw_we = (r32(0) & 3) == 0;
    tw_kind = ((r32(0) & 7) == 0) ? r32(0) : 2'd2;
    tw_kind_p = ((r32(0) & 7) == 0) ? r32(0) : 2'd3;
    tw_addr = r32(0);
    for (i = 0; i < 32; i = i + 1) tw_data[32*i +: 32] = r32(0);
    p_re = (r32(0) & 3) != 0;
    p_idx = r32(0);
    if ((c % 16) == 0) begin bs_addr[8:2] = tw_addr[8:2]; p_idx[8:1] = tw_addr[7:0]; end
  end endtask
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    xs = 64'h9E3779B97F4A7C15 ^ {32'd0, seed};
    rst_n = 0; rnd;
    for (c = 0; c < N; c = c + 1) begin
      @(negedge ck);
      if (c > 4) rst_n = (c % 499) > 2;
      if (c > 12) begin
        if (n_bq !== o_bq) begin eb = eb + 1; if (eb < 4) $display("BTAB MISMATCH c=%0d", c); end
        if (n_pq !== o_pq) begin ep = ep + 1; if (ep < 4) $display("PROG MISMATCH c=%0d", c); end
        if (n_f !== o_f) begin ef = ef + 1; if (ef < 4) $display("FAULT MISMATCH c=%0d", c); end
        
        if (o_bq_d != 0) nzb = nzb + 1;
        if (o_pq_d != 0) nzp = nzp + 1;
      end
      rnd;
    end
    $display("MITER N=%0d seed=%0d btab_mism=%0d prog_mism=%0d fault_mism=%0d mif0_vs_orig_prog=%0d nonzero_cmp btab=%0d prog=%0d",
             N, seed, eb, ep, ef, ez, nzb, nzp);
    if (eb || ep || ef) $fatal(1, "ROW_WRITE_RELAY MISMATCH");
    $finish;
  end
endmodule
