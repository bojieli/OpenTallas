`timescale 1ps/1fs
// TOKSIM-HBM-idxdma 2026-10-19: DMA.LOAD HBM side on the die-bound PC controller leaf ot_hbm_svc_pc_ctrl_leaf_cfg_h9b
// (64 instances ctl_<Q>_pXX in GEN2e3 die.v, default params = the die's #(OREG,KREG,KRREG,RREG,WPAY,QREG = 1)).
// From tb_hbm_pc_h9b_txn (H-PC): same request generator / owner hash, one DUT, kr_rdy held 1 (static consumer slot).
// DRAM (the PHY/stack, the only modelled boundary): a column read returns its beat RL HBM edges after col_v
// (RL 23 = ceil((CL 12.5 ns + burst 1.024 + PHY response 10 ns) / 1.024), the native-controller receipt's read latency;
// RL 14 = the H-PC txn bench model). Golden: every kr beat carries, in order, the data of the DRAM column read that
// produced it (hash of the read sequence number), with the request's tag and beat numbers 0..len-1.
// A record = NREQ_REC requests of LEN beats (32 B each) offered back to back (k_v held, k_rdy honoured) after the
// controller is idle; cycles in HBM edges (1024 ps) from the first k_v edge to the first / last kr beat.
module tb_toksim_pc_load;
  parameter integer RL = 23, NREQ_REC = 1, LEN = 1, NREC = 6, GAP = 600;
  reg clk = 0; always #512 clk = ~clk;
  reg rst_n = 0; reg [4:0] pc_id = 5'd9;
  reg kv = 0; reg [29:0] ka = 0; reg [3:0] kl = 0; reg [16:0] kt = 0;
  wire k_rdy, kr_v, k_wr_done, row_v, col_v, col_we, pc_fault; wire [5:0] of;
  wire [16:0] kr_tag; wire [3:0] kr_beat; wire [255:0] kr_data, col_data; wire [31:0] col_strb;
  wire [2:0] row_op; wire [4:0] row_bank, col_bank, col_col; wire [18:0] row_row;
  reg dv = 0; reg [255:0] dd = 0;
  ot_hbm_svc_pc_ctrl_leaf_cfg_h9b b(.clk(clk), .rst_n(rst_n), .pc_id(pc_id), .refresh_reload(8'd151),
    .k_v(kv), .k_rdy(k_rdy), .k_we(1'b0), .k_addr(ka), .k_len(kl), .k_tag(kt), .k_wdata(256'd0), .k_wstrb(32'd0),
    .kr_v(kr_v), .kr_rdy(1'b1), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data), .k_wr_done(k_wr_done),
    .row_v(row_v), .row_op(row_op), .row_bank(row_bank), .row_row(row_row), .col_v(col_v), .col_we(col_we),
    .col_bank(col_bank), .col_col(col_col), .col_data(col_data), .col_strb(col_strb), .dram_rvalid(dv), .dram_rdata(dd),
    .pc_fault(pc_fault), .owner_fault_split(of));
  integer now = 0, rqw = 0, rqr = 0, rq [0:4095], nbt = 0, errors = 0, ebeat = 0, etag = 0, t_first = -1, t_last = -1;
  reg [255:0] exq [0:4095]; integer exw = 0, exr = 0;
  function automatic [255:0] beat(input integer s); beat = {8{32'(s) * 32'h9e3779b1 ^ 32'h5a5a0000}}; endfunction
  always @(posedge clk) begin
    now = now + 1;
    if (!rst_n) dv <= 0; else begin
      if (col_v && !col_we) begin rq[rqw % 4096] = now + RL; exq[rqw % 4096] = beat(rqw); rqw = rqw + 1; end
      if (rqr != rqw && rq[rqr % 4096] <= now) begin dv <= 1; dd <= beat(rqr); rqr = rqr + 1; end else dv <= 0;
      if (kr_v) begin
        if (kr_data !== exq[exr % 4096] || kr_tag !== 17'(etag) || kr_beat !== 4'(ebeat)) begin
          errors = errors + 1; if (errors < 6) $display("GOLDEN MISMATCH beat %0d tag %0d/%0d beat %0d/%0d", nbt, kr_tag, etag, kr_beat, ebeat); end
        exr = exr + 1; nbt = nbt + 1; if (t_first < 0) t_first = now; t_last = now;
        ebeat = ebeat + 1; if (ebeat == LEN) begin ebeat = 0; etag = etag + 1; end
      end
      if (pc_fault || |of) begin errors = errors + 1; if (errors < 6) $display("FAULT of=%b edge %0d", of, now); end
    end
  end
  reg [31:0] rng = 32'h1d872b41; function [31:0] nx(input [31:0] r); nx = {r[30:0], r[31] ^ r[21] ^ r[1] ^ r[0]}; endfunction
  integer r, i, t0, tag = 0, cf, cl, sf = 0, sl = 0, mnf = 1 << 30, mxf = 0, mnl = 1 << 30, mxl = 0; reg [29:0] a; reg [4:0] x;
  initial begin
    rst_n = 0; repeat (6) @(posedge clk); @(negedge clk); #1 rst_n = 1; repeat (GAP) @(negedge clk);
    for (r = 0; r < NREC; r = r + 1) begin
      t_first = -1; t_last = -1;
      rng = nx(rng); a = rng[29:0]; a[29:15] = 15'(5 + r);
      for (i = 0; i < NREQ_REC; i = i + 1) begin
        @(negedge clk); #1;
        a[14:7] = 8'(r * 37 + i); a[1:0] = 0; x = pc_id ^ a[11:7] ^ a[16:12]; a[6:2] = x;
        kv = 1; ka = a; kl = 4'(LEN); kt = 17'(tag);
        if (i == 0) t0 = now + 1;
        @(posedge clk); while (!k_rdy) @(posedge clk);   // k_rdy is a register; sampled with k_v on this edge
        tag = tag + 1;
      end
      @(negedge clk); #1 kv = 0;
      repeat (GAP) @(negedge clk);
      cf = t_first - t0; cl = t_last - t0;
      $display("TOKSIM_PC rec %0d reqs %0d len %0d k_v_edge %0d first_beat %0d last_beat %0d hbm_edges_first %0d hbm_edges_last %0d", r, NREQ_REC, LEN, t0, t_first, t_last, cf, cl);
      sf = sf + cf; sl = sl + cl; if (cf < mnf) mnf = cf; if (cf > mxf) mxf = cf; if (cl < mnl) mnl = cl; if (cl > mxl) mxl = cl;
    end
    $display("TOKSIM_PC_LOAD RL %0d reqs %0d len %0d records %0d beats %0d errors %0d first min %0d max %0d mean %0.2f last min %0d max %0d mean %0.2f (HBM 1024 ps edges)",
             RL, NREQ_REC, LEN, NREC, nbt, errors, mnf, mxf, 1.0 * sf / NREC, mnl, mxl, 1.0 * sl / NREC);
    if (errors == 0 && nbt == NREC * NREQ_REC * LEN) $display("TOKSIM_PC_LOAD PASS"); else $display("TOKSIM_PC_LOAD FAIL");
    $finish;
  end
endmodule
