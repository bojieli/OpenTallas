// tput-map-1011/F1 2026-10-11: PRODUCTION-SHAPE THROUGHPUT bench of the SVC.STREAM op class (the r25 per-PC weight /
// KV stream of the segmented stream service, hfd_svc_{SW,SE}_s*).  One stack: the PS segment family (gen_svc_seg.py
// segments joined by hfd_svc_<fam>_seg, default rtl/seg_psfc) drives the TIMED HBM3E stack ot_hdc_v41x_idx_hbm (NPC 32,
// REFpb, FR-FCFS, MEM_MODE 1, 1.0 TB/s = 32 sectors per 1.024 ns) through the r16g PHY bundle (tb_svc_physide).
// Stimulus = the Qwen AR 8K SM weight-stream shape: back-to-back stream descriptors on the e link, all 32 PCs, nsec
// sectors a PC each (+nsec, default 4092; +nstr streams, default 2 -> 8,184 sectors a PC = 8.4 MB a stack, the gu record's
// ~7.9 MB a stack), the second descriptor posted while the first runs (the e port holds it).  Every row on ks[port] is
// checked exactly once against the controller's pattern at its kport_map address (same map as tb_hbm_svc_kvs).
// Prints SVCTPUT lines: end-to-end (descriptor -> last row) and steady (first row -> last row) fraction of the stack peak.
// OT_TPUT_RW = the controller model's reorder window (16 = FR-FCFS default; 1 = in-order per PC).
// Plusargs: +nsec=N +nstr=S +phase_ns=T (start offset vs the refresh schedule) +cred=1 (credited streams, consumer returns
// one credit a forwarded cycle per landed row).  Defines: FAM_NE (SE segments under hfd_svc_NE_seg), else SW.
`ifndef OT_TPUT_RW
`define OT_TPUT_RW 16
`endif
`timescale 1ps/1ps
module tb_svc_ps_stream_tput;
  localparam integer TCK = 1024, TFW = 833;
  localparam [7:0] FWDV = 8'b01010101;
  reg ck = 0, rst = 0, fck = 0;
  always #(TCK/2) ck = ~ck;
  always #(TFW/2) fck = ~fck;
  reg ev = 0; reg [127:1] ed = 0;
  wire [22237:0] phy;
  // ---------------------------------------------------------------- timed HBM3E stack behind the PHY bundle
  wire pclk, prst_n;
  wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v, kr_rdy; wire [959:0] k_addr; wire [127:0] k_len, kr_beat;
  wire [543:0] k_tag, kr_tag; wire [8191:0] k_wdata, kr_data; wire [1023:0] k_wstrb;
  wire w_v; wire [23:0] w_addr; wire [5:0] w_len; wire [9:0] w_tag; wire [7:0] wr_rdy;
  tb_svc_physide u_ps (.phy(phy), .clk(pclk), .rst_n(prst_n), .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len),
    .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .kr_v(kr_v),
    .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data), .w_v(w_v), .w_rdy(1'b0), .w_addr(w_addr),
    .w_len(w_len), .w_tag(w_tag), .w_room(8'd0), .wr_v(8'd0), .wr_rdy(wr_rdy), .wr_tag(80'd0), .wr_beat(40'd0),
    .wr_data(2048'd0), .k_oor(1'b0), .w_oor(1'b0), .refreshes(64'd0), .w_reads(32'd0));
  ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(1024), .TAGW(17), .LENW(4), .BEATW(4),
    .QD(64), .RW(`OT_TPUT_RW), .REFPB(3), .MEM_MODE(1), .CLK_PS(TCK)) u_m (
    .clk(pclk), .rst_n(prst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len),
    .req_tag(k_tag), .req_we(k_we), .req_wdata(k_wdata), .req_wstrb(k_wstrb), .wr_done(k_wr_done),
    .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
  // ---------------------------------------------------------------- DUT: SM request ports idle (no legacy traffic)
  wire [44:0] tq0 = {fck, 44'd0}; wire [43:0] tq1; assign tq1[42:0] = 43'd0;
  wire [44:0] tq2 = {fck, 44'd0}; wire [43:0] tq3; assign tq3[42:0] = 43'd0;
  wire [44:0] tq4 = {fck, 44'd0}; wire [43:0] tq5; assign tq5[42:0] = 43'd0;
  wire [44:0] tq6 = {fck, 44'd0}; wire [43:0] tq7; assign tq7[42:0] = 43'd0;
  wire [1101:0] tl0, tl2, tl4, tl6; wire [1098:0] tl1, tl3, tl5, tl7;
  wire [1040:0] tkv; wire [1025:0] tik;
  wire [1101:0] ks [0:7]; reg kq [0:7]; wire [1:0] kqf [0:7]; wire [1:0] kd;
  genvar gq;
  generate for (gq = 0; gq < 8; gq = gq + 1) begin : gkf assign kqf[gq] = {fck, kq[gq]}; end endgenerate
`ifdef FAM_NE
  hfd_svc_NE_seg dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy), .kd(kd), .ks0(ks[0]), .kq0(kqf[0]), .ks1(ks[1]), .kq1(kqf[1]), .ks2(ks[2]), .kq2(kqf[2]), .ks3(ks[3]), .kq3(kqf[3]), .ks4(ks[4]), .kq4(kqf[4]), .ks5(ks[5]), .kq5(kqf[5]), .ks6(ks[6]), .kq6(kqf[6]), .ks7(ks[7]), .kq7(kqf[7]),
    .qsm28(tq0), .lsm28(tl0), .qsm24(tq1), .lsm24(tl1), .qsm29(tq2), .lsm29(tl2), .qsm25(tq3), .lsm25(tl3), .qsm30(tq4), .lsm30(tl4), .qsm26(tq5), .lsm26(tl5), .qsm31(tq6), .lsm31(tl6), .qsm27(tq7), .lsm27(tl7));
`else
  hfd_svc_SW_seg dut (.ck(ck), .rst(rst), .e({fck, ed, ev}), .kv(tkv), .ik(tik), .phy(phy), .kd(kd), .ks0(ks[0]), .kq0(kqf[0]), .ks1(ks[1]), .kq1(kqf[1]), .ks2(ks[2]), .kq2(kqf[2]), .ks3(ks[3]), .kq3(kqf[3]), .ks4(ks[4]), .kq4(kqf[4]), .ks5(ks[5]), .kq5(kqf[5]), .ks6(ks[6]), .kq6(kqf[6]), .ks7(ks[7]), .kq7(kqf[7]),
    .qsm4(tq0), .lsm4(tl0), .qsm0(tq1), .lsm0(tl1), .qsm5(tq2), .lsm5(tl2), .qsm1(tq3), .lsm1(tl3), .qsm6(tq4), .lsm6(tl4), .qsm2(tq5), .lsm2(tl5), .qsm7(tq6), .lsm7(tl6), .qsm3(tq7), .lsm3(tl7));
`endif
  // ---------------------------------------------------------------- reference: kport_map address + controller pattern
  function automatic [29:0] kaddr(input integer pc, input integer j, input integer row0);
    integer row, bank, col, bhi, blo, hi5;
    begin
      row = row0 + (j >> 10); bank = (((j >> 7) & 7) << 2) | (j & 3); col = (j >> 2) & 31;
      bhi = (bank >> 2) ^ ((row >> 2) & 7); blo = (bank & 3) ^ (row & 3); hi5 = ((row & 3) << 3) | bhi;
      kaddr = 30'((row << 15) | (bhi << 12) | (col << 7) | (((pc ^ col ^ hi5) & 31) << 2) | blo);
    end
  endfunction
  function automatic [255:0] pat(input [29:0] s);
    integer w;
    begin for (w = 0; w < 8; w = w + 1) pat[32*w +: 32] = (s * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995; end
  endfunction
  // ---------------------------------------------------------------- row checker
  integer nsec, nstr, phase, cred, err = 0, rows = 0, kds = 0, cr_pend [0:7];
  integer srow0 [0:7]; reg [12:0] stag [0:7];
  reg seen [0:7][0:31][0:1023];
  time t_first = 0, t_last = 0;
  integer kr, sl, si, sk, c;
  initial for (c = 0; c < 8; c = c + 1) begin kq[c] = 1'b0; cr_pend[c] = 0; end
  always @(posedge ck) if (rst) for (kr = 0; kr < 8; kr = kr + 1) if (ks[kr][0]) begin : rowchk
    reg [63:0] meta; reg [4:0] pcid; reg [9:0] rq; reg [3:0] sm; reg [1023:0] want; integer s;
    meta = ks[kr][1098:1035]; pcid = meta[18:14]; sm = meta[13:10]; rq = ks[kr][10:1];
    s = -1; for (sk = 0; sk < nstr; sk = sk + 1) if (stag[sk] == meta[32:20]) s = sk;   // own loop variable (si is the stimulus loop's)
    for (sl = 0; sl < 4; sl = sl + 1) want[sl*256 +: 256] = pat(kaddr(pcid, 4 * rq + sl, (s < 0) ? 0 : srow0[s]));
    if (s < 0) begin err = err + 1; if (err < 6) $display("ERR row with unknown stream tag %0d", meta[32:20]); end
    else if (pcid[4:2] != kr || meta[19] != 1'b0) begin err = err + 1; if (err < 6) $display("ERR row port %0d pc %0d", kr, pcid); end
    else if (seen[s][pcid][rq]) begin err = err + 1; if (err < 6) $display("ERR duplicate row s %0d pc %0d rq %0d", s, pcid, rq); end
    else if (ks[kr][1034:11] !== want || sm !== 4'hf) begin err = err + 1;
      if (err < 6) begin : dbg
        integer jj, ss; $display("ERR row data s %0d pc %0d rq %0d smask %b t=%0t", s, pcid, rq, sm, $time);
        for (ss = 0; ss < 4; ss = ss + 1) begin
          for (jj = 0; jj < 4 * nsec + 64; jj = jj + 1) if (ks[kr][11 + ss*256 +: 256] === pat(kaddr(pcid, jj, srow0[s]))) $display("   slot %0d = sector j %0d (want %0d)", ss, jj, 4 * rq + ss);
          if (ks[kr][11 + ss*256 +: 256] !== want[ss*256 +: 256]) $display("   slot %0d mismatch data[31:0]=%h", ss, ks[kr][11 + ss*256 +: 32]);
        end
      end end
    else begin seen[s][pcid][rq] = 1'b1; rows = rows + 1; if (rows == 1) t_first = $time; t_last = $time;
      if (cred) cr_pend[kr] = cr_pend[kr] + 1; end
  end
  always @(posedge ck) if (kd[0]) kds = kds + 1;
  generate for (gq = 0; gq < 8; gq = gq + 1) begin : gkq
    always @(posedge fck) begin
      kq[gq] <= 1'b0;
      if (cred && cr_pend[gq] > 0) begin kq[gq] <= 1'b1; cr_pend[gq] = cr_pend[gq] - 1; end
    end
  end endgenerate
  // ---------------------------------------------------------------- stimulus
  time t0, t1;
  integer k, want_rows, p;
  real bytes, fe2e, fst;
  initial begin
    if (!$value$plusargs("nsec=%d", nsec)) nsec = 4092;
    if (!$value$plusargs("nstr=%d", nstr)) nstr = 2;
    if (!$value$plusargs("phase_ns=%d", phase)) phase = 0;
    if (!$value$plusargs("cred=%d", cred)) cred = 0;
    for (si = 0; si < 8; si = si + 1) for (p = 0; p < 32; p = p + 1) for (k = 0; k < 1024; k = k + 1) seen[si][p][k] = 1'b0;
    repeat (8) @(posedge ck); rst = 1;
    repeat (64) @(negedge ck);
    #(phase * 1000 + 3000);
    want_rows = nstr * 32 * ((nsec + 3) / 4);
    for (si = 0; si < nstr; si = si + 1) begin
      srow0[si] = 64 + 8 * si; stag[si] = 13'(100 + si);
      @(posedge fck);
      // PS stream descriptor (tb_svc_ps_body.svh packing): {1, nocr, 41'0, tag 13, blocks 10, mask 32, nsec 12, row0 15, kind 1}
      ed <= {1'b1, cred ? 1'b0 : 1'b1, 41'd0, stag[si], 10'd0, 32'hFFFF_FFFF, 12'(nsec), 15'(srow0[si]), 2'd1};
      ev <= 1'b1;
      if (si == 0) t0 = $time;
      @(posedge fck); ev <= 1'b0;
      // the e port holds one queued descriptor: post the next once this one is current (after the previous kd)
      if (si + 1 < nstr) begin k = 0; while (kds < si && k < 2000000) begin @(posedge ck); k = k + 1; end end
    end
    k = 0;
    while (!(rows >= want_rows && kds >= nstr) && k < 4000000) begin @(posedge ck); k = k + 1; end
    t1 = $time;
    repeat (100) @(posedge ck);
    if (rows != want_rows) begin err = err + 1; $display("ERR delivered %0d of %0d rows", rows, want_rows); end
    if (kds != nstr) begin err = err + 1; $display("ERR kd pulses %0d of %0d", kds, nstr); end
    bytes = 1.0 * want_rows * 128.0;
    fe2e = bytes / ((t_last - t0) / 1000.0) / 1000.0;      // TB/s = bytes / ns / 1000; stack peak 1.0 TB/s
    fst = bytes / ((t_last - t_first) / 1000.0) / 1000.0;
    $display("SVCTPUT nsec=%0d nstr=%0d phase_ns=%0d cred=%0d rows=%0d bytes=%0.0f t_e2e_ns=%0.1f t_steady_ns=%0.1f frac_e2e=%0.4f frac_steady=%0.4f errors=%0d",
             nsec, nstr, phase, cred, rows, bytes, (t_last - t0) / 1000.0, (t_last - t_first) / 1000.0, fe2e, fst, err);
    $display("SVCTPUT_BENCH errors=%0d %s", err, err ? "FAIL" : "PASS");
    $finish;
  end
endmodule
