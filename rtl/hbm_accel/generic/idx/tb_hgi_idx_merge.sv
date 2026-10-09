`timescale 1ns/1ps
// hgi-takeover 2026-10-09: IDX.MERGE (ot_hgi_idx_merge) against tools/hgi_idx_merge_vectors.py: every case's O / R in VM
// must equal the golden lexsort prefix exactly (and nothing past it written); the unsorted case must fault.  VM model:
// one request outstanding, random 2..6-cycle latency.  +DIR=<vectors>; MUT=1: ties to the higher id (must FAIL).
module tb_hgi_idx_merge;
  parameter integer MUT = 0;
  reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
  reg go = 0; reg [11:0] k; reg key; reg [7:0] g; reg [19:0] n; wire done, fault; wire [337:0] vmq; reg [273:0] vmr = 0;
  ot_hgi_idx_merge #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .go(go), .k(k), .key_id(key), .g(g), .n(n),
    .a_base(18'h01000), .b_base(18'h10000), .o_base(18'h30000), .r_base(18'h31000), .a_str(18'(n)), .b_str(18'(n)),
    .has_r(1'b1), .done(done), .fault(fault), .vmq(vmq), .vmr(vmr));
  reg [31:0] vm [0:262143]; integer vdel = -1; reg [337:0] vq;
  always @(posedge clk) begin
    vmr[273] <= 1'b0;
    if (vmq[337]) begin if (vdel >= 0) $fatal(1, "VM: 2 outstanding"); vq = vmq; vdel = 2 + ($urandom % 5); end
    else if (vdel > 0) vdel = vdel - 1;
    else if (vdel == 0) begin
      vdel = -1;
      for (integer w = 0; w < 8; w = w + 1) begin
        if (vq[336] && &vq[16 + 4*w +: 4]) vm[{vq[323:309], 3'(w)}] = vq[48 + 32*w +: 32];
        vmr[32*w +: 32] <= vq[336] ? 32'd0 : vm[{vq[323:309], 3'(w)}];
      end
      vmr[273] <= 1'b1;
    end
  end
  reg [31:0] mv [0:65535]; reg [31:0] mi [0:65535]; reg [31:0] eo [0:4095]; reg [31:0] er [0:4095];
  string dir; integer fd, rc, nc, c, G, N, K, KEY, F, NE, t, bad, cyc;
  always @(posedge clk) cyc <= cyc + 1;
  initial begin
    if (!$value$plusargs("DIR=%s", dir)) dir = "/tmp/mvec";
    fd = $fopen({dir, "/cases.txt"}, "r"); rc = $fscanf(fd, "%d", nc); cyc = 0; bad = 0;
    repeat (3) @(negedge clk); rst_n = 1; repeat (3) @(negedge clk);
    for (c = 0; c < nc; c = c + 1) begin
      rc = $fscanf(fd, "%d %d %d %d %d %d", G, N, K, KEY, F, NE);
      $readmemh($sformatf("%s/case_%0d.v.mem", dir, c), mv); $readmemh($sformatf("%s/case_%0d.i.mem", dir, c), mi);
      if (NE > 0) begin $readmemh($sformatf("%s/case_%0d.o.mem", dir, c), eo); $readmemh($sformatf("%s/case_%0d.r.mem", dir, c), er); end
      for (integer x = 0; x < G * N; x = x + 1) begin vm[18'h01000 + x] = mv[x]; vm[18'h10000 + x] = mi[x]; end
      for (integer x = 0; x < 4096; x = x + 1) begin vm[18'h30000 + x] = 32'hDEAD0000 + x; vm[18'h31000 + x] = 32'hBEEF0000 + x; end
      g = 8'(G); n = 20'(N); k = 12'(K); key = KEY[0];
      @(negedge clk); go = 1; @(negedge clk); go = 0; t = cyc;
      while (!done && !fault && cyc - t < 2000000) @(negedge clk);
      if (F) begin
        if (!fault) begin $display("FAIL case %0d: unsorted run not rejected", c); bad = bad + 1; end
        else $display("MERGE case %0d: unsorted run faults as required", c);
      end else if (!done || fault) begin $display("FAIL case %0d: done=%0d fault=%0d", c, done, fault); bad = bad + 1; end
      else begin : chk
        integer e; e = 0;
        for (integer x = 0; x < NE; x = x + 1) if (vm[18'h30000 + x] !== eo[x] || vm[18'h31000 + x] !== er[x]) begin
          if (e < 3) $display("  case %0d [%0d] got %h/%h want %h/%h", c, x, vm[18'h30000 + x], vm[18'h31000 + x], eo[x], er[x]);
          e = e + 1; end
        if (vm[18'h30000 + NE] !== 32'hDEAD0000 + NE) e = e + 1;
        if (e) begin $display("FAIL case %0d: %0d mismatches", c, e); bad = bad + 1; end
        else $display("MERGE case %0d: G=%0d n=%0d k=%0d key=%0d out=%0d EXACT cycles=%0d", c, G, N, K, KEY, NE, cyc - t);
      end
      repeat (5) @(negedge clk);
    end
    if (bad == 0) $display("PASS HGI_IDX_MERGE cases=%0d", nc); else $display("FATAL: HGI_IDX_MERGE %0d cases failed", bad);
    $finish;
  end
endmodule
