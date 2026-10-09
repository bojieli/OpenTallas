`timescale 1ns/1ps
// hgi-takeover 2026-10-09: IDX.OWNED (ot_hgi_idx_owned) against tools/hgi_idx_owned_vectors.py: O (owned local rows,
// padded), R (per-entry gathered row) and D (M) exact; the out-of-range id case must fault.  VM: fast-path model
// (4 outstanding, in order).  MUT=1 (owner from the id instead of id div B) must FAIL.
module tb_hgi_idx_owned;
  parameter integer MUT = 0;
  reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
  reg go = 0; reg [7:0] blk, grp, die; reg [19:0] k; wire done, fault; wire [337:0] vmq; reg [273:0] vmr = 0;
  ot_hgi_idx_owned #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .go(go), .blk(blk), .grp(grp), .die(die), .k(k),
    .a_base(18'h01003), .o_base(18'h02005), .r_base(18'h03001), .d_base(18'h04007), .done(done), .fault(fault), .vmq(vmq), .vmr(vmr));
  reg [31:0] vm [0:262143];
  reg [337:0] vqq [0:7]; integer vqt [0:7]; integer qh2 = 0, qn2 = 0, maxo2 = 0, tnow = 0, tlast = 0;
  always @(posedge clk) begin
    tnow = tnow + 1;
    vmr[273] <= 1'b0;
    if (qn2 > 0 && vqt[qh2 % 8] <= tnow) begin : serve
      reg [337:0] vq; vq = vqq[qh2 % 8]; qh2 = qh2 + 1; qn2 = qn2 - 1;
      for (integer w = 0; w < 8; w = w + 1) begin
        if (vq[336] && &vq[16 + 4*w +: 4]) vm[{vq[323:309], 3'(w)}] = vq[48 + 32*w +: 32];
        vmr[32*w +: 32] <= vq[336] ? 32'd0 : vm[{vq[323:309], 3'(w)}];
      end
      vmr[256] <= vq[336]; vmr[272:257] <= vq[15:0]; vmr[273] <= 1'b1;
    end
    if (vmq[337]) begin
      if (qn2 >= 4) $fatal(1, "VM: more than 4 outstanding");
      vqq[(qh2 + qn2) % 8] = vmq;
      tlast = (tnow + 6 + ($urandom % 3) > tlast + 1) ? tnow + 6 + ($urandom % 3) : tlast + 1;
      vqt[(qh2 + qn2) % 8] = tlast; qn2 = qn2 + 1; if (qn2 > maxo2) maxo2 = qn2;
    end
  end
  reg [31:0] ea [0:4095]; reg [31:0] eo [0:4095]; reg [31:0] er [0:4095];
  string dir; integer fd, rc, nc, c, B, G, D, K, F, M, NO, t, bad;
  initial begin
    if (!$value$plusargs("DIR=%s", dir)) dir = "/tmp/ovec";
    fd = $fopen({dir, "/cases.txt"}, "r"); rc = $fscanf(fd, "%d", nc); bad = 0;
    repeat (3) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
    for (c = 0; c < nc; c = c + 1) begin
      rc = $fscanf(fd, "%d %d %d %d %d %d %d", B, G, D, K, F, M, NO);
      $readmemh($sformatf("%s/case_%0d.a.mem", dir, c), ea); $readmemh($sformatf("%s/case_%0d.o.mem", dir, c), eo);
      $readmemh($sformatf("%s/case_%0d.r.mem", dir, c), er);
      for (integer x = 0; x < K; x = x + 1) vm[18'h01003 + x] = ea[x];
      for (integer x = 0; x < 4096; x = x + 1) begin vm[18'h02005 + x] = 32'hDEAD0000 + x; vm[18'h03001 + x] = 32'hBEEF0000 + x; end
      vm[18'h04007] = 32'hFFFFFFFF;
      blk = 8'(B); grp = 8'(G); die = 8'(D); k = 20'(K);
      @(negedge clk); go = 1; @(negedge clk); go = 0; t = 0;
      while (!done && !fault && t < 200000) begin @(negedge clk); t = t + 1; end
      if (F) begin
        if (!fault) begin $display("FAIL case %0d: out-of-range id not rejected", c); bad = bad + 1; end
        else $display("OWNED case %0d: out-of-range id faults as required", c);
      end else if (!done) begin $display("FAIL case %0d: done=%0d fault=%0d", c, done, fault); bad = bad + 1; end
      else begin : chk
        integer e; e = 0;
        for (integer x = 0; x < NO; x = x + 1) if (vm[18'h02005 + x] !== eo[x]) begin if (e < 3) $display("  O[%0d] %h want %h", x, vm[18'h02005 + x], eo[x]); e = e + 1; end
        if (vm[18'h02005 + NO] !== 32'hDEAD0000 + NO) e = e + 1;
        for (integer x = 0; x < K; x = x + 1) if (vm[18'h03001 + x] !== er[x]) begin if (e < 3) $display("  R[%0d] %h want %h", x, vm[18'h03001 + x], er[x]); e = e + 1; end
        if (vm[18'h04007] !== M) e = e + 1;
        if (e) begin $display("FAIL case %0d: %0d mismatches (M %0d want %0d)", c, e, vm[18'h04007], M); bad = bad + 1; end
        else $display("OWNED case %0d: B=%0d G=%0d die=%0d K=%0d M=%0d EXACT cycles=%0d", c, B, G, D, K, M, t);
      end
      repeat (5) @(negedge clk);
    end
    if (bad == 0) $display("PASS HGI_IDX_OWNED cases=%0d max_outstanding=%0d", nc, maxo2); else $display("FATAL: HGI_IDX_OWNED %0d cases failed", bad);
    $finish;
  end
endmodule
