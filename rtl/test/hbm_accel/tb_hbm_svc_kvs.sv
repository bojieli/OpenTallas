`timescale 1ps/1ps
// hbm-system 2026-10-08: PER-PC KV STREAM bench of the r25 stream service (ot_hbm_svc_core KVS = 1), one stack.
//   e kind 1 stream descriptor {row0, nsec, mask 32 PCs} -> every PC streams sectors j = 0 .. nsec-1 of its region
//   through its own lane kvs[p] -> checked: each (p, j) exactly once, data = the controller's pattern at the K
//   address the dskv_wb / stream-PC map gives (pc, bank {j[9:7], j[1:0]}, row row0 + j >> 10, column j[6:2]).
// Timed HBM3E stack ot_hdc_v41x_idx_hbm (REFpb, FR-FCFS, 1.0 TB/s peak = 32 sectors per 1.024 ns), MEM_MODE 1.
// Prints KVS lines: nsec, cycles from the descriptor's launch to kvs_done, delivered bytes, fraction of peak.
// Plusargs: +nsec=N +reps=R +phase_ns=T (start offset against the refresh schedule) +mut=1 (drop lane 5 beats).
module tb_hbm_svc_kvs #(parameter integer KNO = 15, parameter integer XST = 2);
  localparam integer TH = 833, TCK = 1024;
  reg ck = 0, efck = 0, rst_n = 0;
  always #(TCK/2) ck = ~ck;
  always #(TH/2) efck = ~efck;
  wire phy_clk, phy_rst_n, fclk;
  wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v, kr_rdy; wire [959:0] k_addr; wire [127:0] k_len, kr_beat;
  wire [543:0] k_tag, kr_tag; wire [8191:0] k_wdata, kr_data; wire [1023:0] k_wstrb;
  wire [8*1099-1:0] line; wire [1037:0] kv; wire [1023:0] ik; wire [7:0] q_rdy;
  wire [32*269-1:0] kvs; wire kvs_done;
  reg [127:0] e_d = 0;
  ot_hbm_svc_core #(.SM_PC0({5'd28, 5'd24, 5'd20, 5'd16, 5'd12, 5'd8, 5'd4, 5'd0}),
    .RSP_ST(128'h10111101210021002211322133212110), .REQ_ST(32'h11112332), .W_ST(32'hec985300),
    .FWD(8'b01010101), .KV_PC(16), .IK_PC(17), .KV_ST(0), .IK_ST(0), .E_ST(11), .XST(XST), .KVS(1), .KNO(KNO)) u_svc (
    .ck(ck), .rst(rst_n), .q_d({8*42{1'b0}}), .q_v(8'd0), .q_fclk(8'd0), .q_rdy(q_rdy), .line(line), .fclk(fclk),
    .e_d(e_d), .e_fclk(efck), .kv(kv), .ik(ik), .phy_clk(phy_clk), .phy_rst_n(phy_rst_n),
    .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we), .k_wdata(k_wdata),
    .k_wstrb(k_wstrb), .kr_v(kr_v), .kr_rdy(kr_rdy), .kr_tag(kr_tag), .kr_beat(kr_beat), .kr_data(kr_data),
    .w_v(), .w_rdy(1'b0), .w_addr(), .w_len(), .w_tag(), .w_room(8'd0), .wr_v(8'd0), .wr_rdy(), .wr_tag(80'd0),
    .wr_beat(40'd0), .wr_data(2048'd0), .wq_d(292'd0), .wq_fclk(1'b0), .wq_g(), .k_wr_done(k_wr_done),
    .kvs(kvs), .kvs_done(kvs_done));
  ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(1024), .TAGW(17), .LENW(4), .BEATW(4),
    .QD(64), .REFPB(3), .MEM_MODE(1), .CLK_PS(TCK)) u_m (
    .clk(phy_clk), .rst_n(phy_rst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len),
    .req_tag(k_tag), .req_we(k_we), .req_wdata(k_wdata), .req_wstrb(k_wstrb), .wr_done(k_wr_done),
    .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
  // ---- independent reference: inverse map written from the controller decode, the controller's pattern
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
  function automatic integer pc_of(input [29:0] s);
    pc_of = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31;
  endfunction
  // ---- checker
  integer nsec, reps, phase, mut, row0, err = 0, got = 0, r, p, w, k;
  reg seen [0:31][0:4095];
  always @(posedge ck) if (rst_n) for (p = 0; p < 32; p = p + 1) if (kvs[p*269] && !(mut == 1 && p == 5)) begin : chk
    integer j; reg [29:0] s;
    j = kvs[p*269 + 1 +: 12];
    s = kaddr(p, j, row0);
    if (j >= nsec) begin err = err + 1; if (err < 5) $display("ERR lane %0d j %0d past nsec", p, j); end
    else if (seen[p][j]) begin err = err + 1; if (err < 5) $display("ERR lane %0d j %0d twice", p, j); end
    else if (pc_of(s) != p) begin err = err + 1; if (err < 5) $display("ERR map: PC %0d j %0d -> PC %0d", p, j, pc_of(s)); end
    else if (kvs[p*269 + 13 +: 256] !== pat(s)) begin err = err + 1; if (err < 5) $display("ERR lane %0d j %0d data", p, j); end
    else begin seen[p][j] = 1'b1; got = got + 1; end
  end
  integer t0, t1, cyc0;
  real frac;
  initial begin
    if (!$value$plusargs("nsec=%d", nsec)) nsec = 17;
    if (!$value$plusargs("reps=%d", reps)) reps = 2;
    if (!$value$plusargs("phase_ns=%d", phase)) phase = 0;
    if (!$value$plusargs("mut=%d", mut)) mut = 0;
    repeat (10) @(posedge ck); rst_n = 1;
    #(phase * 1000 + 3000);
    for (r = 0; r < reps; r = r + 1) begin
      for (p = 0; p < 32; p = p + 1) for (w = 0; w < 4096; w = w + 1) seen[p][w] = 1'b0;
      got = 0;
      row0 = 64 + 8 * r;
      @(posedge efck);
      e_d <= {57'd0, 10'(r), 32'hffff_ffff, 12'(nsec), 15'(row0), 2'd1, 1'b1};
      t0 = $time;
      @(posedge efck); e_d[0] <= 1'b0;
      k = 0;
      while (!kvs_done && k < 2000000) begin @(posedge ck); k = k + 1; end
      t1 = $time;
      @(posedge ck); @(posedge ck);
      if (got != 32 * nsec) begin err = err + 1; $display("ERR rep %0d delivered %0d of %0d", r, got, 32 * nsec); end
      frac = (32.0 * nsec * 32.0) / ((t1 - t0) / 1000.0) / 1000.0;     // TB/s (bytes / ns / 1000)
      $display("KVS nsec=%0d rep=%0d phase_ns=%0d t_ns=%0.1f bytes=%0d tbs=%0.4f frac_peak=%0.4f", nsec, r, phase,
               (t1 - t0) / 1000.0, 32 * nsec * 32, frac, frac / 1.0);
      repeat (200) @(posedge ck);
    end
    $display("KVS_BENCH errors=%0d %s", err, err ? "FAIL" : "PASS");
    $finish;
  end
endmodule
