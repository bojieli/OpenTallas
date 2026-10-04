`timescale 1ps/1fs
// Lockstep equivalence bench, WB_EN = 1: the r0 write-capable stream PC (sha256 8189205b..., renamed copy
// ot_hbm_accel_stream_pc_wb_r0_ref) vs the edited ot_hbm_accel_stream_pc_wb, same random inputs (descriptors,
// grants, credits, go, next_posted, notice AND posted writes with their own rows), every output compared on
// every cycle.  Writes draw rows from a small set (NROW) so same-bank different-row conflicts, row hits and
// write-open banks all occur.  Verilator 5.050: --binary --timing.  Plusargs +SEED +CYC; -G REFM PCI WQN WP NROW BANKS.
module tb_stream_pc_wb_lockstep;
  parameter integer REFM = 1, PCI = 0, PH = 0, WQN = 8, WP = 3, NROW = 3, BANKS = 32, GNT8 = 7, WBE = 1;
  reg clk = 0, rst_n = 0;
  always #417 clk = ~clk;
  reg desc_v, go, next_posted, notice, row_gnt, wq_v; reg [18:0] desc_row, wq_row; reg [10:0] desc_n; reg [2:0] cred_ret;
  reg [4:0] wq_bank, wq_col; reg [255:0] wq_data;
  wire [348:0] oa, ob;
  ot_hbm_accel_stream_pc_wb_r0_ref #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WB_EN(WBE),.WQ(WQN),.CRED(64)) a(
    .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_r(oa[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),
    .next_posted(next_posted),.notice(notice),.row_v(oa[1]),.row_prio(oa[2]),.row_gnt(row_gnt),.row_op(oa[5:3]),
    .row_bank(oa[10:6]),.row_row(oa[29:11]),.col_v(oa[30]),.col_bank(oa[35:31]),.col_col(oa[40:36]),.cred_ret(cred_ret),
    .busy(oa[41]),.ref_fault(oa[42]),.wq_v(wq_v),.wq_bank(wq_bank),.wq_row(wq_row),.wq_col(wq_col),.wq_data(wq_data),
    .wq_r(oa[43]),.col_we(oa[44]),.col_wdata(oa[300:45]),.col_row(oa[319:301]),.wr_ack(oa[320]),.wq_empty(oa[321]));
  ot_hbm_accel_stream_pc_wb #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WB_EN(WBE),.WQ(WQN),.CRED(64)) b(
    .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_r(ob[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),
    .next_posted(next_posted),.notice(notice),.row_v(ob[1]),.row_prio(ob[2]),.row_gnt(row_gnt),.row_op(ob[5:3]),
    .row_bank(ob[10:6]),.row_row(ob[29:11]),.col_v(ob[30]),.col_bank(ob[35:31]),.col_col(ob[40:36]),.cred_ret(cred_ret),
    .busy(ob[41]),.ref_fault(ob[42]),.wq_v(wq_v),.wq_bank(wq_bank),.wq_row(wq_row),.wq_col(wq_col),.wq_data(wq_data),
    .wq_r(ob[43]),.col_we(ob[44]),.col_wdata(ob[300:45]),.col_row(ob[319:301]),.wr_ack(ob[320]),.wq_empty(ob[321]));
  assign oa[348:322] = 0; assign ob[348:322] = 0;
  integer seed, cyc, i, mism = 0, acts = 0, wacts = 0, wpres = 0, rds = 0, wrs = 0, refs = 0, descs = 0, faults = 0, pushes = 0;
  reg pbusy = 0;
  function automatic integer rnd(input integer m); rnd = $urandom % m; endfunction
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 200000;
    void'($urandom(seed));
    desc_v = 0; go = 0; next_posted = 0; notice = 0; row_gnt = 0; desc_row = 0; desc_n = 0; cred_ret = 0;
    wq_v = 0; wq_bank = 0; wq_row = 0; wq_col = 0; wq_data = 0;
    repeat (3) @(posedge clk); #10 rst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge clk);
      if (oa !== ob) begin mism = mism + 1; if (mism < 10) $display("MISMATCH cyc=%0d a=%h b=%h", i, oa, ob); end
      if (oa[1] && row_gnt && oa[5:3] == 1) begin acts = acts + 1; if (oa[29:11] >= 19'd500000) wacts = wacts + 1; end
      if (oa[1] && row_gnt && oa[5:3] == 0 && oa[29:11] >= 19'd500000) wpres = wpres + 1;
      if (oa[1] && row_gnt && oa[5:3] == 6) refs = refs + 1;
      if (oa[30] && !oa[44]) rds = rds + 1;
      if (oa[44]) wrs = wrs + 1;
      if (oa[42]) faults = faults + 1;
      if (oa[41] && !pbusy) descs = descs + 1; pbusy = oa[41];
      if (wq_v && oa[43]) pushes = pushes + 1;
      row_gnt = oa[2] || (rnd(8) < GNT8);
      if (oa[42]) begin rst_n = 0; @(negedge clk); rst_n = 1; end
      cred_ret = oa[30] ? ((rnd(4) == 0) ? 3'd0 : 3'd1) : ((rnd(3) == 0) ? 3'd1 : 3'd0);
      desc_v = rnd(16) == 0;
      desc_n = (rnd(4) == 0) ? 11'(rnd(2048)) : 11'd1024;
      desc_row = 19'(rnd(400000));           // stream rows < 400000; write rows >= 500000 (counted apart)
      go = rnd(4) == 0;
      next_posted = rnd(5) == 0;
      notice = rnd(3) == 0;
      wq_v = rnd(WP) == 0;
      wq_bank = 5'(rnd(BANKS));
      wq_row = 19'(500000 + rnd(NROW));
      wq_col = 5'(rnd(32));
      wq_data = {8{32'($urandom)}};
    end
    $display("SUMMARY wb_lockstep WB_EN=%0d REFM=%0d PC=%0d PH=%0d WQ=%0d WP=%0d NROW=%0d BANKS=%0d GNT8=%0d seed=%0d cycles=%0d mismatches=%0d acts=%0d wacts=%0d wpres=%0d rds=%0d wrs=%0d pushes=%0d refpb=%0d busy_starts=%0d fault_cycles=%0d verdict=%s",
             WBE, REFM, PCI, PH, WQN, WP, NROW, BANKS, GNT8, seed, cyc, mism, acts, wacts, wpres, rds, wrs, pushes, refs, descs, faults,
             (mism == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
