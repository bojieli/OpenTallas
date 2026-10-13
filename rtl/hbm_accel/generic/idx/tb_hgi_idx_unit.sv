`timescale 1ps/1ps
// ot_hgi_idx_unit bench (hgi-takeover): every hbm-sim CF-TOPK conformance vector (tools/hgi_idx_unit_vectors.py) as a
// record on the die record bus; VM = a packet-protocol model (up to 4 requests outstanding, in order, random latency).  A vector
// passes when every expected VM output word matches and no other VM word was written, or, for a faulting vector, the
// record faults.  topk_k512_n4096_m1_asc expects a FAULT here: order = 1 is legal only for k <= 8 (HGI-1 G15, spec
// c80ed5d7c; the hbm-sim vector predates the confirmation).
module tb_hgi_idx_unit;
 parameter integer MUT = 0, PREF = 0, TOPKW = 0, TWIW = 4;   // TOPKW: opt-in heap engine + packed writes (hgi-1010/g2)
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [2074:0] rec = 0; wire [2:0] ret; wire [337:0] vmq; reg [273:0] vmr = 0;
 ot_hgi_idx_unit #(.MUT(MUT), .PREF(PREF), .TOPKW(TOPKW), .TWIW(TWIW)) dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret), .vmq(vmq), .vmr(vmr),
  .sel_fs(), .sel_qb(), .sel_qbr(1'b0), .sel_kin(), .sel_to(612'd0), .sel_toc(), .sel_co(72'd0), .sel_coc(), .sel_ev(2'b00));
 // the vectors carry the v1 ABOR record; the unit takes {die, pos, n_R, n_O, n_D, n_C, n_B, n_A, R, O, D, C, B, A, hdr, v}
 function automatic [2074:0] widen(input [1236:0] o);
  widen = {256'd0, 8'd0, 20'd0, o[1236:1195], 42'd0, o[1194:1153], o[1152:641], 512'd0, o[640:0]};
 endfunction
 reg [31:0] vm [0:262143]; reg wr_mark [0:262143];
 reg [1236:0] rmem [0:0]; reg [52:0] lin [0:300000]; reg [52:0] lout [0:300000];
 integer nv, v, st, i, j, q, fails = 0, cyc, del = 0; reg pend = 0; reg [337:0] held;
 string dir, idn; integer fl, rc;
 // VM packet model (hgi-1010/g): up to 4 requests outstanding (more is a bench fatal), served in order, each a random
 // 2..5 cycles after the previous one is served or it was issued (so PREF = 1's 4-deep prefetch is exercised).
 reg [337:0] vq [0:7]; integer vqt [0:7]; integer qh = 0, qn = 0, maxq = 0, tnow = 0, tl = 0;
 always @(posedge clk) begin
  tnow = tnow + 1;
  vmr[273] <= 1'b0;
  if (qn > 0 && vqt[qh % 8] <= tnow) begin
   held = vq[qh % 8]; qh = qh + 1; qn = qn - 1;
   vmr[273] <= 1'b1; vmr[272:257] <= held[15:0]; vmr[256] <= held[336];
   for (q = 0; q < 8; q = q + 1) begin
    if (held[336]) begin
     if (&held[16 + q*4 +: 4]) begin vm[{held[323:309], 3'(q)}] = held[48 + q*32 +: 32]; wr_mark[{held[323:309], 3'(q)}] = 1; end
     vmr[q*32 +: 32] <= 32'd0;
    end else vmr[q*32 +: 32] <= vm[{held[323:309], 3'(q)}];
   end
  end
  if (vmq[337]) begin
   if (qn >= 4) $fatal(1, "FATAL: more than 4 VM requests outstanding");
   tl = (tnow + 2 + $urandom % 4 > tl + 1) ? tnow + 2 + $urandom % 4 : tl + 1;
   vq[(qh + qn) % 8] = vmq; vqt[(qh + qn) % 8] = tl; qn = qn + 1; if (qn > maxq) maxq = qn;
  end
 end
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) dir = "/tmp/idxv";
  fl = $fopen({dir, "/list.txt"}, "r"); rc = $fscanf(fl, "%d", nv);
  repeat (3) @(posedge clk); rst_n = 1;
  for (v = 0; v < nv; v = v + 1) begin
   rc = $fscanf(fl, "%d %d %s", i, st, idn);
   if (idn == "topk_k512_n4096_m1_asc") st = 3;
   for (i = 0; i < 262144; i = i + 1) begin vm[i] = 0; wr_mark[i] = 0; end
   $readmemh($sformatf("%s/vec_%0d.rec.mem", dir, v), rmem);
   $readmemh($sformatf("%s/vec_%0d.vmin.mem", dir, v), lin);
   $readmemh($sformatf("%s/vec_%0d.vmout.mem", dir, v), lout);
   for (i = 0; lin[i] !== 53'h1fffffffffffff && lin[i] !== 53'hfffffffffffff; i = i + 1) vm[lin[i][49:32]] = lin[i][31:0];
   @(negedge clk); rec = widen(rmem[0]); @(negedge clk); rec[0] = 1'b0;
   cyc = 0; while (!ret[1] && !ret[2] && cyc < 400000) begin @(negedge clk); cyc = cyc + 1; end
   if (st != 0) begin
    if (!ret[2]) begin $display("FATAL: %s expected a fault", idn); fails = fails + 1; end
    else $display("IDX %s: fault as expected", idn);
   end else if (!ret[1] || ret[2]) begin $display("FATAL: %s no done / fault (cyc %0d)", idn, cyc); fails = fails + 1; end
   else begin
    j = 0;
    for (i = 0; lout[i] !== 53'h1fffffffffffff && lout[i] !== 53'hfffffffffffff; i = i + 1) begin
     if (vm[lout[i][49:32]] !== lout[i][31:0]) begin
      if (j < 4) $display("FATAL: %s word %0d = %h, expected %h", idn, lout[i][49:32], vm[lout[i][49:32]], lout[i][31:0]);
      j = j + 1;
     end
     wr_mark[lout[i][49:32]] = 0;
    end
    for (i = 0; i < 262144; i = i + 1) if (wr_mark[i] && vm[i] !== 0) j = j + 1;   // writes outside the expected set
    if (j) fails = fails + 1; else $display("IDX %s: exact (%0d cycles)", idn, cyc);
   end
   repeat (4) @(negedge clk);
  end
  if (fails) $display("FATAL: IDX unit %0d vectors failed", fails);
  else $display("PASS HGI-IDX unit CF-TOPK vectors=%0d (PREF %0d, max VM requests outstanding %0d)", nv, PREF, maxq);
  $finish;
 end
endmodule
