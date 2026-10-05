`timescale 1ps/1fs
// Retained PVE1 s4 benchmark; ONLY source selectors changed.
// Original donor /home/ubuntu/hbm-fmax-svc/s4/tb_stream_pc_wr_lockstep.sv.
// Reference is exact routed49fa snapshot; candidate AQ cut.
// Lockstep equivalence bench, WR_EN = 1: main's STREAM4 stream PC (sha256 a2cfb09b..., renamed copy
// ot_hbm_r14_stream_pc_s4_ref) vs the edited ot_hbm_r14_stream_pc (r9), same random inputs (descriptors,
// grants, credits, go, next_posted AND queued accesses: writes, and tagged reads when AQR = 1), every output
// compared on every cycle.  Usage: +SEED=n +CYC=n; -G REFM PCI WQN WP (1/WP access per cycle) PULLIN AQR.
module tb_svc_aq_head_ready_lockstep;
  parameter integer REFM = 1, PCI = 0, PH = 0, WQN = 4, WP = 3, PULLIN = 0, AQR = 0;
  reg clk = 0, rst_n = 0;
  always #417 clk = ~clk;
  reg desc_v, go, next_posted, row_gnt, wr_v; reg [18:0] desc_row; reg [10:0] desc_n; reg [2:0] cred_ret;
  reg [4:0] wr_bank, wr_col; reg wr_rd;
  wire [49:0] oa, ob, oc;
  ot_hbm_r14_stream_pc #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WR_EN(1),.WQ(WQN),.PULLIN(PULLIN),.AQ_RD(AQR)) a(.clk(clk),.rst_n(rst_n),
    .desc_v(desc_v),.desc_r(oa[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
    .row_v(oa[1]),.row_prio(oa[2]),.row_gnt(row_gnt),.row_op(oa[5:3]),.row_bank(oa[10:6]),.row_row(oa[29:11]),
    .col_v(oa[30]),.col_bank(oa[35:31]),.col_col(oa[40:36]),.cred_ret(cred_ret),.busy(oa[41]),.ref_fault(oa[42]),
    .wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(oa[43]),.col_we(oa[44]),.wr_rd(wr_rd),.col_aq(oa[45]));
  ot_hbm_r14_stream_pc_aq_head_ready_cut #(.AQ_HEAD_READY_LOOKAHEAD(1),.AQ_HOLD_LOOKAHEAD(1),.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WR_EN(1),.WQ(WQN),.PULLIN(PULLIN),.AQ_RD(AQR)) b(.clk(clk),.rst_n(rst_n),
    .desc_v(desc_v),.desc_r(ob[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
    .row_v(ob[1]),.row_prio(ob[2]),.row_gnt(row_gnt),.row_op(ob[5:3]),.row_bank(ob[10:6]),.row_row(ob[29:11]),
    .col_v(ob[30]),.col_bank(ob[35:31]),.col_col(ob[40:36]),.cred_ret(cred_ret),.busy(ob[41]),.ref_fault(ob[42]),
    .wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(ob[43]),.col_we(ob[44]),.wr_rd(wr_rd),.col_aq(ob[45]));
  ot_hbm_r14_stream_pc_aq_head_ready_cut #(.AQ_HEAD_READY_LOOKAHEAD(0),.AQ_HOLD_LOOKAHEAD(1),.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WR_EN(1),.WQ(WQN),.PULLIN(PULLIN),.AQ_RD(AQR)) c(.clk(clk),.rst_n(rst_n),
    .desc_v(desc_v),.desc_r(oc[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
    .row_v(oc[1]),.row_prio(oc[2]),.row_gnt(row_gnt),.row_op(oc[5:3]),.row_bank(oc[10:6]),.row_row(oc[29:11]),
    .col_v(oc[30]),.col_bank(oc[35:31]),.col_col(oc[40:36]),.cred_ret(cred_ret),.busy(oc[41]),.ref_fault(oc[42]),
    .wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(oc[43]),.col_we(oc[44]),.wr_rd(wr_rd),.col_aq(oc[45]));
  assign oa[49:46] = 0; assign ob[49:46] = 0; assign oc[49:46] = 0;
  reg pbusy = 0;
  integer seed, seed0, cyc, i, mism = 0, acts = 0, wacts = 0, rds = 0, wrs = 0, refs = 0, descs = 0, faults = 0, pushes = 0, aqs = 0;
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1; seed0 = seed;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 200000;
    desc_v = 0; go = 0; next_posted = 0; row_gnt = 0; desc_row = 0; desc_n = 0; cred_ret = 0;
    wr_v = 0; wr_bank = 0; wr_col = 0; wr_rd = 0;
    repeat (3) @(posedge clk); #10 rst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge clk);
      if (oa !== ob || oa !== oc) begin mism = mism + 1; if (mism < 10) $display("MISMATCH cyc=%0d a=%h b=%h", i, oa, ob); end
      if (rst_n && (a.on.wq_n !== b.on.wq_n || a.on.row_fire !== b.on.row_fire))
        $fatal(1, "QUEUE_OR_GRANT_DEBT cycle=%0d", i);
      if (rst_n && b.on.head_bank_ready_q !== (b.on.wq_ne && |(b.on.hb_oh & b.on.rdyr_q)))
        $fatal(1, "HEAD_READY_INVARIANT cycle=%0d", i);
      // Exercise warm reset as an actual input; all implementations see the same edge.
      if (i != 0 && i % 17003 == 0) begin rst_n = 0; @(negedge clk); rst_n = 1; end
      if (oa[1] && row_gnt && oa[5:3] == 1) acts = acts + 1;
      if (oa[1] && row_gnt && oa[5:3] == 6) refs = refs + 1;
      if (oa[45]) aqs = aqs + 1;
      if (oa[30] && !oa[44] && !oa[45]) rds = rds + 1;
      if (oa[44]) wrs = wrs + 1;
      if (oa[42]) faults = faults + 1;
      if (oa[41] && !pbusy) descs = descs + 1; pbusy = oa[41];
      if (wr_v && oa[43]) pushes = pushes + 1;
      row_gnt = oa[2] || (($unsigned($random(seed)) % 8) != 0);
      if (oa[42]) begin rst_n = 0; @(negedge clk); rst_n = 1; end
      cred_ret = oa[30] ? (($unsigned($random(seed)) % 4 == 0) ? 3'd0 : 3'd1) : (($unsigned($random(seed)) % 3 == 0) ? 3'd1 : 3'd0);
      desc_v = ($unsigned($random(seed)) % 16) == 0;
      desc_n = (($unsigned($random(seed)) % 4) == 0) ? 11'($unsigned($random(seed)) % 2048) : 11'd1024;
      desc_row = 19'($unsigned($random(seed)));
      go = ($unsigned($random(seed)) % 4) == 0;
      next_posted = ($unsigned($random(seed)) % 5) == 0;
      // writes: bursts to the last set (the service's write-back region) or anywhere
      wr_v = ($unsigned($random(seed)) % WP) == 0;
      wr_bank = (($unsigned($random(seed)) % 2) == 0) ? {3'(($unsigned($random(seed)) % 8)), 2'($unsigned($random(seed)))} : 5'($unsigned($random(seed)));
      wr_col = 5'($unsigned($random(seed)));
      wr_rd = AQR && (($unsigned($random(seed)) % 2) == 0);
    end
    $display("SUMMARY wr_lockstep PULLIN=%0d AQR=%0d REFM=%0d PC=%0d PH=%0d WQ=%0d WP=%0d seed=%0d cycles=%0d mismatches=%0d acts=%0d rds=%0d wrs=%0d aqrds=%0d pushes=%0d refpb=%0d busy_starts=%0d fault_cycles=%0d verdict=%s",
             PULLIN, AQR, REFM, PCI, PH, WQN, WP, seed0, cyc, mism, acts, rds, wrs, aqs, pushes, refs, descs, faults, (mism == 0) ? "PASS" : "FAIL");
    if (mism != 0 || faults != 0 || acts == 0 || refs == 0 || pushes == 0 || aqs == 0)
      $fatal(1, "SEMANTIC_GATE missing coverage or mismatch");
    $finish;
  end
endmodule
