`timescale 1ps/1fs
// Lockstep: HEAD WR_EN PC (5f0d5c50d, renamed) vs the merged (r8 + WR_EN) PC; WR_EN=1, random
// descriptors, credits, grants and write pushes; every output compared every cycle.
module tb_wr_lockstep;
  parameter integer REFM = 1, PCI = 0, PH = 0, WREN = 1;
  reg clk = 0, rst_n = 0;
  always #512 clk = ~clk;
  reg desc_v, go, next_posted, row_gnt, wr_v; reg [18:0] desc_row; reg [10:0] desc_n; reg [2:0] cred_ret;
  reg [4:0] wr_bank, wr_col;
  wire [47:0] oa, ob;
`define PORTS(o) .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_r(o[0]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted), \
    .row_v(o[1]),.row_prio(o[2]),.row_gnt(row_gnt),.row_op(o[5:3]),.row_bank(o[10:6]),.row_row(o[29:11]), \
    .col_v(o[30]),.col_bank(o[35:31]),.col_col(o[40:36]),.cred_ret(cred_ret),.busy(o[41]),.ref_fault(o[42]), \
    .wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(o[43]),.col_we(o[44])
  ot_hbm_r14_stream_pc_wr_ref #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WR_EN(WREN)) a(`PORTS(oa));
  ot_hbm_r14_stream_pc        #(.ENABLE(1),.REF_MODE(REFM),.PC(PCI),.REF_PHASE(PH),.WR_EN(WREN)) b(`PORTS(ob));
  assign oa[47:45] = 0; assign ob[47:45] = 0;
  integer seed, cyc, i, mism = 0, acts = 0, rds = 0, wrs = 0, refs = 0, descs = 0, faults = 0;
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("CYC=%d", cyc)) cyc = 200000;
    desc_v = 0; go = 0; next_posted = 0; row_gnt = 0; desc_row = 0; desc_n = 0; cred_ret = 0; wr_v = 0; wr_bank = 0; wr_col = 0;
    repeat (3) @(posedge clk); #10 rst_n = 1;
    for (i = 0; i < cyc; i = i + 1) begin
      @(negedge clk);
      if (oa !== ob) begin mism = mism + 1; if (mism < 10) $display("MISMATCH cyc=%0d a=%h b=%h", i, oa, ob); end
      if (oa[1] && row_gnt && oa[5:3] == 1) acts = acts + 1;
      if (oa[1] && row_gnt && oa[5:3] == 6) refs = refs + 1;
      if (oa[30] && !oa[44]) rds = rds + 1;
      if (oa[44]) wrs = wrs + 1;
      if (oa[42]) faults = faults + 1;
      if (desc_v && oa[0]) descs = descs + 1;
      row_gnt = oa[2] || (($urandom(seed) % 8) != 0); seed = seed + 1;
      if (oa[42]) begin rst_n = 0; @(negedge clk); rst_n = 1; end
      cred_ret = (oa[30] && !oa[44]) ? (($urandom(seed) % 4 == 0) ? 3'd0 : 3'd1) : (($urandom(seed+7) % 3 == 0) ? 3'd1 : 3'd0);
      desc_v = (($urandom(seed+3) % 16) == 0) && oa[0];
      desc_n = (($urandom(seed+5) % 4) == 0) ? 11'($urandom(seed+9) % 2048) : 11'd1024;
      desc_row = 19'($urandom(seed+11));
      go = ($urandom(seed+13) % 4) == 0;
      next_posted = ($urandom(seed+17) % 5) == 0;
      wr_v = ($urandom(seed+19) % 6) == 0;
      wr_bank = ((($urandom(seed+23) % 3) == 0) ? 5'($urandom(seed+29)) : {oa[41] ? 3'd7 : 3'($urandom(seed+31)), 2'($urandom(seed+37))});
      wr_col = 5'($urandom(seed+41));
    end
    $display("SUMMARY wr-lockstep REFM=%0d PC=%0d PH=%0d WREN=%0d seed=%0d cycles=%0d mismatches=%0d acts=%0d rds=%0d wrs=%0d refpb=%0d descs=%0d fault_cycles=%0d verdict=%s",
             REFM, PCI, PH, WREN, seed, cyc, mism, acts, rds, wrs, refs, descs, faults, (mism == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
