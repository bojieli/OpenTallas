// DIE-HBM-61 RE-FORM C4 (2026-11-03): lockstep ot_hbm_r14_stream_pc_strap_h9 WP_REG=1 (new) vs origin/main
// (_old, no WP_REG) with the cfg_h9b parameter set. Declared cycle shift 0: every output compared on every edge,
// plus the write-queue state (wq_pv, wq_older, ent_q). PASS needs pushes, queue-full cycles and pops.
`timescale 1ns/1ps
module tb;
  parameter integer P = 2, T = 0, SEED = 1;
  reg clk = 0, rst_n = 0; reg [7:0] rr = 0;
  reg desc_v = 0; reg [18:0] desc_row = 0; reg [10:0] desc_n = 0; reg go = 1, np = 0, row_gnt = 1;
  reg [2:0] cred = 0; reg wr_v = 0, wr_rd = 0; reg [4:0] wr_bank = 0, wr_col = 0; reg sp = 0; reg [7:0] rl = 8'd5;
  wire [52:0] oa, ob;
`define H9P .ENABLE(1),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.PHYS_WACT(P), \
      .TIMING_833(T),.T_CCDS(T?2:1),.COL_TDM(T?1:0),.ROW_CADENCE(T?2:1), \
      .T_RCD(T?24:19),.T_RP(T?20:16),.T_RAS(T?34:28),.T_RTP(T?7:6),.T_CCDL(T?4:3), \
      .T_RRDS(T?4:3),.T_RRDL(4),.T_FAW(T?19:15),.T_RFC(T?421:342),.T_RFCPB(T?241:196), \
      .T_REFI(T?4681:3808),.T_REFIPB(T?144:118),.T_RREFD(T?10:8), \
      .T_RTW(T?12:10),.T_WTR(T?17:14),.T_WRR(T?34:28),.T_RCDW(T?12:10)
`define H9C(o) .reset_regions(rr),.clk(clk),.rst_n(rst_n),.slot_parity(sp),.refresh_reload(rl),.desc_v(desc_v),.desc_r(o[0]), \
      .desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(np),.row_v(o[1]),.row_prio(o[2]),.row_gnt(row_gnt), \
      .row_op(o[5:3]),.row_bank(o[10:6]),.row_row(o[29:11]),.col_v(o[30]),.col_bank(o[35:31]),.col_col(o[40:36]), \
      .cred_ret(cred),.busy(o[41]),.ref_fault(o[42]),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(o[43]), \
      .col_we(o[44]),.wr_rd(wr_rd),.col_aq(o[45])
  assign oa[52:46] = 0; assign ob[52:46] = 0;
  ot_hbm_r14_stream_pc_strap_h9 #(`H9P,.WP_REG(1)) dn(`H9C(oa));
  ot_hbm_r14_stream_pc_strap_h9_old #(`H9P) dold(`H9C(ob));
  always #1 clk = ~clk;
  integer cyc = 0, errs = 0, pushes = 0, fulls = 0, pops = 0, inv = 0, seed, wbias;
  initial begin
    seed = SEED; wbias = 70;
    repeat (3) @(posedge clk);
    rst_n = 1;
    for (cyc = 0; cyc < 40000; cyc = cyc + 1) begin
      @(negedge clk);
      // reset regions: all released together (the relay releases them as one); a mid-run full re-reset
      rr = (cyc < 8 || (cyc % 9001) < 3) ? 8'h00 : 8'hff;
      if (cyc == 0) wbias = $urandom(seed) % 2 + 70;
      if (cyc % 5000 == 0) wbias = ($urandom % 2) ? 2 + $urandom % 8 : 30 + $urandom % 70;
      sp = $urandom; desc_v = ($urandom % 100) < 20; desc_row = $urandom; desc_n = $urandom % 64;
      go = ($urandom % 100) < 90; np = $urandom; row_gnt = ($urandom % 100) < 85; cred = $urandom % 3;
      wr_v = ($urandom % 100) < wbias; wr_bank = $urandom; wr_col = $urandom; wr_rd = ($urandom % 100) < 30;
      #0.5;
      if (oa !== ob || (cyc > 8 && ^oa === 1'bx)) begin errs = errs + 1; if (errs < 10) $display("ERR cyc %0d out new %h old %h", cyc, oa, ob); end
      if (dn.on.wq_pv !== dold.on.wq_pv || dn.on.wq_older !== dold.on.wq_older || dn.on.ent_q !== dold.on.ent_q) begin
        errs = errs + 1; if (errs < 10) $display("ERR cyc %0d queue state", cyc); end
      if (&rr && wr_v && ob[43]) pushes = pushes + 1;
      if (&rr && !ob[43]) fulls = fulls + 1;
      if (&rr && ob[44] | ob[45]) pops = pops + 1;
      if (&rr && dn.on.wp_oh !== (32'b1 << 5'(dn.on.wq_rp + dn.on.wq_n))) inv = inv + 1;
    end
    $display("H9_WPREG_EQ P=%0d T=%0d checks=%0d errors=%0d pushes=%0d full_cycles=%0d pops=%0d inv_viol=%0d %s",
             P, T, cyc, errs, pushes, fulls, pops, inv,
             (errs == 0 && inv == 0 && pushes > 500 && fulls > 200 && pops > 500) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
