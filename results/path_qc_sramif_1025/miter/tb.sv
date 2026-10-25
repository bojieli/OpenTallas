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
  ORIG_btab ob (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(o_bq), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(o_f));
  qfd_dv_s8x_btab #(.MIF(1)) nb (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(n_bq), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault(n_f));
  qfd_dv_s8x_btab #(.MIF(0)) zb (.ck(ck), .rst_n(rst_n), .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(), .tw_we(tw_we), .tw_kind(tw_kind), .tw_addr(tw_addr[8:2]), .tw_data(tw_data), .fault());
  // prog
  reg p_re; reg [8:0] p_idx; reg [1:0] tw_kind_p;
  wire [456:0] o_pq, n_pq, z_pq;
  ORIG_prog op (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(o_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  qfd_dv_s8x_prog #(.MIF(1)) np (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(n_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  qfd_dv_s8x_prog #(.MIF(0)) zp (.ck(ck), .p_re(p_re), .p_idx(p_idx), .p_q(z_pq), .tw_we(tw_we), .tw_kind(tw_kind_p), .tw_addr(tw_addr[7:0]), .tw_d0(tw_data[456:0]), .tw_d1(tw_data[968:512]));
  reg [255:0] o_bq_d; reg [456:0] o_pq_d;
  always @(posedge ck) begin o_bq_d <= o_bq; o_pq_d <= o_pq; end
  integer c, i, eb = 0, ep = 0, ef = 0, ez = 0, nzb = 0, nzp = 0, rdb = 0;
  integer seed = 1;
  task rnd; begin
    bs_re = ($random(seed) & 3) != 0;
    bs_addr = {(($random(seed) & 31) == 0) ? $random(seed) : 15'd0, 9'd0} | ($random(seed) & 9'h1ff);
    tw_we = ($random(seed) & 3) == 0;
    tw_kind = (($random(seed) & 7) == 0) ? $random(seed) : 2'd2;
    tw_kind_p = (($random(seed) & 7) == 0) ? $random(seed) : 2'd3;
    tw_addr = $random(seed);
    for (i = 0; i < 32; i = i + 1) tw_data[32*i +: 32] = $random(seed);
    p_re = ($random(seed) & 3) != 0;
    p_idx = $random(seed);
  end endtask
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    rst_n = 0; rnd;
    for (c = 0; c < N; c = c + 1) begin
      @(negedge ck);
      if (c > 4) rst_n = 1;
      if (c > 12) begin
        if (n_bq !== o_bq_d) begin eb = eb + 1; if (eb < 4) $display("BTAB MISMATCH c=%0d", c); end
        if (n_pq !== o_pq_d) begin ep = ep + 1; if (ep < 4) $display("PROG MISMATCH c=%0d", c); end
        if (n_f !== o_f) begin ef = ef + 1; if (ef < 4) $display("FAULT MISMATCH c=%0d", c); end
        if (z_pq !== o_pq) ez = ez + 1;
        if (o_bq_d != 0) nzb = nzb + 1;
        if (o_pq_d != 0) nzp = nzp + 1;
      end
      rnd;
    end
    $display("MITER N=%0d seed=%0d btab_mism=%0d prog_mism=%0d fault_mism=%0d mif0_vs_orig_prog=%0d nonzero_cmp btab=%0d prog=%0d",
             N, seed, eb, ep, ef, ez, nzb, nzp);
    $finish;
  end
endmodule
