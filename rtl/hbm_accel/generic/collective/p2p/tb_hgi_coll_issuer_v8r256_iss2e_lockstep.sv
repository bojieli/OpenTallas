`timescale 1ns/1ps
// HBM-TAPS 11-12 ISS2E lock-step bench (DO_NOT_COUNT): reference issuer (ot_hgi_coll_issuer_m256v8, unchanged)
// and the ISS2E issuer (ot_hgi_coll_issuer_m256v8e) driven by the same random cfg / start stimulus.  Each design logs its issued
// uop stream (uop_pc, iteration, uop_d1 hash), done pulses and the fault rise; the compare script checks the two logs
// are identical (EQ_CYCLE_SHIFTED: same events, same order, timing free).
// plusargs: +seed=N +progs=N +rows=N +log_ref=F +log_dut=F
`define RND(n) ((($random(seed)) & 32'h7fffffff) % (n))
`define RNW ($random(seed))
module tb;
  reg clk = 0, rst_n = 0;
  reg [36:0] cfg = 0; reg start = 0; reg [7:0] start_pc = 0;
  always #1 clk = ~clk;
  wire r_busy, r_done, r_fault, r_uv; wire [7:0] r_pc; wire [1535:0] r_d1; wire [31:0] r_it; wire [87:0] r_ts;
  wire d_busy, d_done, d_fault, d_uv; wire [7:0] d_pc; wire [1535:0] d_d1; wire [31:0] d_it; wire [87:0] d_ts;
  wire r_b3, r_d3, r_s3, r_b2, r_s2, d_b3, d_d3, d_s3, d_b2, d_s2;
  ot_hgi_coll_issuer_m256v8 u_ref(.clk_control(clk), .rst_n(rst_n), .cfg(cfg), .start(start), .start_pc(start_pc),
    .busy(r_busy), .done(r_done), .fault(r_fault), .uop_v(r_uv), .uop_pc(r_pc), .uop_d1(r_d1),
    .busy_d3(r_b3), .done_d3(r_d3), .start_d3(r_s3), .busy_d2(r_b2), .start_d2(r_s2), .tap_iteration(r_it), .tap_steps(r_ts));
  ot_hgi_coll_issuer_m256v8e u_dut(.clk_control(clk), .rst_n(rst_n), .cfg(cfg), .start(start), .start_pc(start_pc),
    .busy(d_busy), .done(d_done), .fault(d_fault), .uop_v(d_uv), .uop_pc(d_pc), .uop_d1(d_d1),
    .busy_d3(d_b3), .done_d3(d_d3), .start_d3(d_s3), .busy_d2(d_b2), .start_d2(d_s2), .tap_iteration(d_it), .tap_steps(d_ts));

  integer seed, progs, rows, fr, fd, cyc = 0, nuop_r = 0, nuop_d = 0;
  reg [1023:0] log_ref, log_dut;
  always @(posedge clk) cyc <= cyc + 1;
  function [31:0] h32(input [1535:0] x); integer i; begin h32 = 32'h811c9dc5;
    for (i = 0; i < 48; i = i + 1) h32 = (h32 ^ x[i*32 +: 32]) * 32'h01000193; end endfunction
  // event loggers: uop issued (uop_d1 is valid one edge after uop_v), done pulse, fault rise
  reg r_uv1 = 0, d_uv1 = 0, r_f1 = 0, d_f1 = 0; reg [7:0] r_pc1, d_pc1; reg [31:0] r_it1, d_it1;
`ifdef OT_COLL_ISS8E_PAD_MASK
  localparam [1535:0] PADM_TB = `OT_COLL_ISS8E_PAD_MASK;     // the intended mask (the DUT mutant flips its own copy)
`endif
  reg d_uv2 = 0, d_done1 = 0; reg [7:0] d_pc2; reg [31:0] d_it2; reg [1535:0] d_d1q;
  always @(posedge clk) begin d_uv2 <= d_uv1; d_pc2 <= d_pc1; d_it2 <= d_it1; d_d1q <= d_d1; d_done1 <= d_done; end
  always @(posedge clk) begin
    r_uv1 <= r_uv; r_pc1 <= r_pc; r_it1 <= r_it;
    d_uv1 <= d_uv; d_pc1 <= d_pc; d_it1 <= d_it;
    if (r_uv1) begin $fdisplay(fr, "U %0d %0d %08x", r_pc1, r_it1, h32(r_d1)); nuop_r = nuop_r + 1; end
`ifdef OT_COLL_ISS8E_PAD_MASK
    // pad: masked bits arrive one edge after the row; DUT events are logged one edge later with the row's word rebuilt
    // from the two edges (unmasked bits from the row edge, masked bits from the next edge)
    if (d_uv2) begin $fdisplay(fd, "U %0d %0d %08x", d_pc2, d_it2, h32((d_d1q & ~PADM_TB) | (d_d1 & PADM_TB))); nuop_d = nuop_d + 1; end
    if (r_done) $fdisplay(fr, "D"); if (d_done1) $fdisplay(fd, "D");
`else
    if (d_uv1) begin $fdisplay(fd, "U %0d %0d %08x", d_pc1, d_it1, h32(d_d1)); nuop_d = nuop_d + 1; end
    if (r_done) $fdisplay(fr, "D"); if (d_done) $fdisplay(fd, "D");
`endif
    r_f1 <= r_fault; d_f1 <= d_fault;
    if (r_fault && !r_f1) $fdisplay(fr, "F"); if (d_fault && !d_f1) $fdisplay(fd, "F");
  end
  task cmd(input [3:0] mode, input [31:0] d); begin
    @(negedge clk) cfg = {1'b1, mode, d}; @(negedge clk) cfg = 0;
    repeat (`RND(3)) @(negedge clk);
  end endtask
  task sel(input [7:0] row, input [1:0] bank); cmd(4'd0, {22'd0, row[7:6], bank, row[5:0]}); endtask
  // record word x[63:0]: next {x54,x51,x5:0}, tgt {x55,x52,x11:6}, lid x49:45, halt x44, cnt x43:12 (has = |cnt)
  function [63:0] rec(input [7:0] nx, input [7:0] tg, input [4:0] lid, input halt, input [31:0] cnt);
    reg [63:0] x; begin
      x = 64'd0; x[5:0] = nx[5:0]; x[51] = nx[6]; x[54] = nx[7]; x[11:6] = tg[5:0]; x[52] = tg[6]; x[55] = tg[7];
      x[49:45] = lid; x[44] = halt; x[43:12] = cnt; rec = x; end endfunction
  integer p, r, b, f, k, w, n, nr, lidset, kk, ncap = 0, nlaunch = 0;
  reg [7:0] nx, tg, ld; reg [31:0] cnt; reg [63:0] meta; reg [7:0] rws [0:63]; reg [255:0] used;
  function [31:0] rcount(input integer q);
    case (q % 9) 0: rcount = 0; 1: rcount = 1; 2: rcount = 2; 3: rcount = 3; 4: rcount = 4 + `RND(13);
      5: rcount = 32'h8000_0000; 6: rcount = 32'hffff_ffff; 7: rcount = 2 + `RND(5); default: rcount = 0; endcase
  endfunction
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("progs=%d", progs)) progs = 20;
    if (!$value$plusargs("rows=%d", rows)) rows = 24;
    if (!$value$plusargs("log_ref=%s", log_ref)) log_ref = "ref.log";
    if (!$value$plusargs("log_dut=%s", log_dut)) log_dut = "dut.log";
    fr = $fopen(log_ref, "w"); fd = $fopen(log_dut, "w");
    for (p = 0; p < progs; p = p + 1) begin
      rst_n = 0; cfg = 0; start = 0; repeat (4) @(negedge clk); rst_n = 1; repeat (2) @(negedge clk);
      $fdisplay(fr, "P %0d", p); $fdisplay(fd, "P %0d", p);
      // the v8r256 miter's programme menu (tb_hgi_coll_issuer_v8r256_miter.sv): distinct rows over 0..255 (or dense),
      // loop ids < lidset or = row & 31 (counter forwarding), counts 0/1/2/3/small/2^31/2^32-1, halts, missing banks
      // and metadata.  Timing-defined stimuli (start while busy, stray cfg while busy) are left out: the ISS2E busy
      // window is longer by design, so their outcome is timing, not function.
      nr = 1 + `RND(rows); lidset = 1 + `RND(4); used = 0;
      for (r = 0; r < nr; r = r + 1) begin
        if (p % 3 == 0) rws[r] = (p * 37 + r) % 256;
        else begin kk = `RND(256); while (used[kk]) kk = (kk + 1) % 256; rws[r] = kk; end
        used[rws[r]] = 1;
      end
      for (r = 0; r < nr; r = r + 1) begin
        for (b = 0; b < 3; b = b + 1) if (`RND(60) != 0) begin
          sel(rws[r], b[1:0]); for (f = 0; f < 16; f = f + 1) cmd(4'd1, `RNW); end
        cnt = rcount(`RND(9)); nx = rws[`RND(nr)]; tg = rws[`RND(nr)]; ld = `RND(lidset);
        if (`RND(5) == 0) ld = rws[r] & 8'd31;
        meta = 0; meta[5:0] = nx[5:0]; meta[51] = nx[6]; meta[54] = nx[7]; meta[11:6] = tg[5:0]; meta[52] = tg[6]; meta[55] = tg[7];
        meta[43:12] = cnt; meta[44] = (r == nr - 1) ? (`RND(3) != 0) : (`RND(7) == 0);
        meta[50:45] = ld[5:0]; meta[53] = ld[6]; meta[56] = ld[7];
        if (`RND(50) != 0) begin sel(rws[r], 2'd0); cmd(4'd2, meta[31:0]); cmd(4'd3, meta[63:32]); end
      end
      for (k = 0; k < 3; k = k + 1) begin
        start_pc = rws[`RND(nr)]; repeat (6 + `RND(3)) @(negedge clk);
        start = 1; @(negedge clk) start = 0; nlaunch = nlaunch + 1;
        n = 0; while (n < 1500 && (r_busy || d_busy)) begin @(negedge clk); n = n + 1; end
        if (n >= 1500) begin $fdisplay(fr, "T"); $fdisplay(fd, "T"); ncap = ncap + 1; k = 3; end
        repeat (8) @(negedge clk);
      end
    end
    $display("TB_DONE seed %0d progs %0d launches %0d capped %0d uops ref %0d dut %0d cycles %0d", seed, progs, nlaunch, ncap, nuop_r, nuop_d, cyc);
    $fclose(fr); $fclose(fd); $finish;
  end
endmodule
