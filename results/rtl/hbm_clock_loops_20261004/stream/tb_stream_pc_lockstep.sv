`timescale 1ps/1fs
// Lockstep equivalence bench: r6 stream PC (renamed copy) vs the edited PC, same random inputs,
// every output compared on every cycle. Usage: +SEED=n +CYC=n; -GREFM=0/1 -GPCI=0/1.
module tb_stream_pc_lockstep;
  parameter integer REFM = 1, PCI = 0, PH = 0;
  reg clk = 0, rst_n = 0;
  always #512 clk = ~clk;
  reg desc_v, go, next_posted, row_gnt; reg [18:0] desc_row; reg [10:0] desc_n; reg [2:0] cred_ret;
  wire [47:0] oa, ob;
  ot_hbm_r14_stream_pc_r6 #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH)) a(.clk(clk),.rst_n(rst_n),
    .desc_v(desc_v),.desc_r(oa[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
    .row_v(oa[1]),.row_prio(oa[2]),.row_gnt(row_gnt),.row_op(oa[5:3]),.row_bank(oa[10:6]),.row_row(oa[29:11]),
    .col_v(oa[30]),.col_bank(oa[35:31]),.col_col(oa[40:36]),.cred_ret(cred_ret),.busy(oa[41]),.ref_fault(oa[42]));
  ot_hbm_r14_stream_pc #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH)) b(.clk(clk),.rst_n(rst_n),
    .desc_v(desc_v),.desc_r(ob[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
    .row_v(ob[1]),.row_prio(ob[2]),.row_gnt(row_gnt),.row_op(ob[5:3]),.row_bank(ob[10:6]),.row_row(ob[29:11]),
    .col_v(ob[30]),.col_bank(ob[35:31]),.col_col(ob[40:36]),.cred_ret(cred_ret),.busy(ob[41]),.ref_fault(ob[42]));
  assign oa[47:43] = 0; assign ob[47:43] = 0;
  integer seed, cyc, i, mism = 0, acts = 0, rds = 0, refs = 0, descs = 0, faults = 0;
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 200000;
    desc_v = 0; go = 0; next_posted = 0; row_gnt = 0; desc_row = 0; desc_n = 0; cred_ret = 0;
    repeat (3) @(posedge clk); #10 rst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge clk);
      if (oa !== ob) begin mism = mism + 1; if (mism < 10) $display("MISMATCH cyc=%0d a=%h b=%h", i, oa, ob); end
      if (oa[1] && row_gnt && oa[5:3] == 1) acts = acts + 1;
      if (oa[1] && row_gnt && oa[5:3] == 6) refs = refs + 1;
      if (oa[30]) rds = rds + 1;
      if (oa[42]) faults = faults + 1;
      if (desc_v && oa[0]) descs = descs + 1;
      // stimulus: mostly-granted row slot, credits returned like a consumer, descriptors of random length
      // refresh-class row commands are always granted (the stack's slot rule); others 7/8
      row_gnt = oa[2] || (($urandom(seed) % 8) != 0); seed = seed + 1;
      // a latched fault blocks descriptors forever: re-reset both copies to keep covering
      if (oa[42]) begin rst_n = 0; @(negedge clk); rst_n = 1; end
      cred_ret = oa[30] ? (($urandom(seed) % 4 == 0) ? 3'd0 : 3'd1) : (($urandom(seed+7) % 3 == 0) ? 3'd1 : 3'd0);
      desc_v = ($urandom(seed+3) % 16) == 0;
      desc_n = (($urandom(seed+5) % 4) == 0) ? 11'($urandom(seed+9) % 2048) : 11'd1024;
      desc_row = 19'($urandom(seed+11));
      go = ($urandom(seed+13) % 4) == 0;
      next_posted = ($urandom(seed+17) % 5) == 0;
    end
    $display("SUMMARY lockstep REFM=%0d PC=%0d PH=%0d seed=%0d cycles=%0d mismatches=%0d acts=%0d rds=%0d refpb=%0d descs=%0d fault_cycles=%0d verdict=%s",
             REFM, PCI, PH, seed, cyc, mism, acts, rds, refs, descs, faults, (mism == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
