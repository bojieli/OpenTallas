`timescale 1ps/1ps
// FUSED.QDQ_* B2 QUARTER throughput bench (el1011-qdqtput, 2026-10-12): ot_hgi_qdq_q (normative record bus) on the real
// HBM B2 VM slice (ot_vms_slice: 8 bank tiles + hub + ring stops; sid 0, ring ports idle) through its 8-lane wide read
// group 0 / write group 0, with S lanestation-like relay stages each way (SPEC.md sec 2a: the cluster's local lane group).
// Vectors: tools/hgi_unit_tput/qdq_vectors.py (the DS-V4.1 1M production shapes and golden).  Every record's operands are
// placed at (production base + 4,096 k) mod 65,536 words, i.e. slice-local (bank phase unchanged; the 16 regions are
// disjoint).  The bench preloads every A through the slice's packet client (untimed), then dispatches the records BACK TO
// BACK as the CP's unit queue does: a record goes on the bus on any cycle the unit reports ready, independent of the
// previous record's done; the dones are counted in order.  Per record it prints
//   TPUT k op <op> n <n> issue <cycle> ret <cycle> gap <ret - previous ret> cost <sim price>
// and, after the last done, reads every O back through the packet client and compares each word with the golden.
// MUT 1: the record header drops the A operand bit -> the unit faults (must FAIL);
// MUT 2: engine lane-to-sector mutant (assembly takes sector j from lane j ^ 1) -> wrong words (must FAIL).
module tb_hgi_qdq_q_tput;
 parameter integer MUT = 0, S = 1, SPANPIPE = 0, PIN4 = 0;
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [682:0] rec = 0; wire [2:0] ret;
 reg [337:0] bq = 0; wire [273:0] br;
 wire [8*16-1:0] rq; wire [7:0] rq_cr, wq_cr, wq_done; wire [8*257-1:0] rr; wire [8*280-1:0] wq;
 generate if (PIN4) begin : g_pin4
 ot_hgi_qdq_q_pin4 #(.MUT(MUT == 2 ? 1 : 0), .SPANPIPE(SPANPIPE)) dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret),
   .wrq(rq), .wrq_cr(rq_cr), .wrr_p0(rr[513:0]), .wrr_p1(rr[1027:514]), .wrr_p2(rr[1541:1028]), .wrr_p3(rr[2055:1542]), .wwq(wq), .wwq_cr(wq_cr), .wwq_done(wq_done),
   .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1));
 end else begin : g_core
 ot_hgi_qdq_q #(.MUT(MUT == 2 ? 1 : 0), .SPANPIPE(SPANPIPE)) dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret),
   .wrq(rq), .wrq_cr(rq_cr), .wrr(rr), .wwq(wq), .wwq_cr(wq_cr), .wwq_done(wq_done),
   .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1));
 end endgenerate

 // S relay stages each way (the lanestation + chain flops between the client and the slice face)
 reg [8*16-1:0] rq_d [0:S]; reg [8*280-1:0] wq_d [0:S]; reg [7:0] rcr_d [0:S], wcr_d [0:S], wdn_d [0:S];
 reg [8*257-1:0] rr_d [0:S];
 wire [7:0] s_rcr, s_wcr, s_wdn; wire [8*257-1:0] s_rr;
 integer i;
 always @* begin rq_d[0] = rq; wq_d[0] = wq; rcr_d[0] = s_rcr; wcr_d[0] = s_wcr; wdn_d[0] = s_wdn; rr_d[0] = s_rr; end
 always @(posedge clk) for (i = 1; i <= S; i = i + 1) begin
   rq_d[i] <= rq_d[i-1]; wq_d[i] <= wq_d[i-1]; rcr_d[i] <= rcr_d[i-1]; wcr_d[i] <= wcr_d[i-1]; wdn_d[i] <= wdn_d[i-1];
   rr_d[i] <= rr_d[i-1];
 end
 assign rq_cr = rcr_d[S]; assign wq_cr = wcr_d[S]; assign wq_done = wdn_d[S]; assign rr = rr_d[S];
 // client lane {v, sector 15} -> bank lane {v, sec16 = {m 0, sector}}
 wire [8*17-1:0] b_rq; wire [8*281-1:0] b_wq;
 genvar g;
 for (g = 0; g < 8; g = g + 1) begin : g_l
   assign b_rq[g*17 +: 17] = {rq_d[S][g*16 + 15], 1'b0, rq_d[S][g*16 +: 15]};
   assign b_wq[g*281 +: 281] = {wq_d[S][g*280 + 279], 1'b0, wq_d[S][g*280 +: 279]};
 end
 wire [8*18-1:0] bank_status; wire [2:0] hub_status;
 // lane credits = the slice's own default (4 + 2 x 3 contract relay stages, SPEC v0.8 D-B2-12): no bench override
 ot_vms_slice #(.NC(1), .RG(1), .WG(1)) vm (.clk(clk), .rst_n(rst_n), .sid(2'd0), .cq(bq), .cr(br),
   .rq(b_rq), .rq_cr(s_rcr), .rr(s_rr), .wq(b_wq), .wq_cr(s_wcr), .wq_done(s_wdn),
   .dq('0), .dq_done(), .vcb('0), .vcb_cr(), .kq_done(), .cw_in('0), .cw_in_cr(), .cw_out(), .cw_out_cr(2'b0),
   .ccw_in('0), .ccw_in_cr(), .ccw_out(), .ccw_out_cr(2'b0), .bank_status(bank_status), .hub_status(hub_status), .mirror_busy());
 reg [255:0] gin [0:127]; reg [255:0] gout [0:127];
 integer nrec, fd, k, s, j, op [0:15], n [0:15], ab [0:15], ob [0:15], cost [0:15], blk [0:15], iss [0:15];
 integer cyc = 0, words = 0, bad = 0, bk = 0, total_cost = 0, nret = 0, t0 = 0, prev = 0, started = 0;
 integer rows = 1;   // +ROWS=m: every record walks m rows (row stride = n, in place; rows > 0 read / write beyond the vectors:
                     // only row 0 is compared) -- exercises the read walk's row advance, which the m = 1 production shapes do not
 string dir, fn;
 reg [255:0] sd;
 always @(posedge clk) cyc <= cyc + 1;
 task vm_write(input [14:0] sec, input [255:0] d);
  begin @(negedge clk); bq = {1'b1, 1'b1, {12'd0, sec, 5'd0}, d, 32'hffffffff, 16'h0001}; @(negedge clk); bq[337] = 0;
   while (!br[273]) @(negedge clk); end
 endtask
 task vm_read(input [14:0] sec);
  begin @(negedge clk); bq = {1'b1, 1'b0, {12'd0, sec, 5'd0}, 256'd0, 32'd0, 16'h0002}; @(negedge clk); bq[337] = 0;
   while (!br[273]) @(negedge clk); sd = br[255:0]; end
 endtask
 function [255:0] desc(input [2:0] fmt, input [39:0] base, input [19:0] nn, input [19:0] mm, input [31:0] stride);
  begin desc = 256'd0; desc[1:0] = 2'd1; desc[4:2] = fmt; desc[47:8] = base; desc[67:48] = nn; desc[87:68] = mm; desc[119:88] = stride; end
 endfunction
 // done monitor (in order)
 always @(negedge clk) if (started && rst_n) begin
   if (ret[2]) $fatal(1, "FATAL: fault after %0d dones (MUT %0d)", nret, MUT);
   if (ret[1]) begin
     $display("TPUT %0d op %0d n %0d issue %0d ret %0d gap %0d cost %0d", nret, op[nret], n[nret], iss[nret], cyc - t0,
              cyc - t0 - prev, cost[nret]);
     prev = cyc - t0; nret = nret + 1;
   end
 end
 reg [127:0] h; reg [255:0] da, dd;
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "FATAL: +DIR");
  void'($value$plusargs("ROWS=%d", rows));
  fd = $fopen({dir, "/recs.txt"}, "r"); void'($fscanf(fd, "%d", nrec));
  for (k = 0; k < nrec; k = k + 1) begin
   void'($fscanf(fd, "%d %d %d %d %d %d", op[k], n[k], ab[k], ob[k], cost[k], blk[k]));
   ab[k] = ab[k] % 65536; ob[k] = ob[k] % 65536;          // slice-local (sid 0), bank phase unchanged
  end
  // multi-row walk: IN PLACE (O = A, legal: a beat is read before it is written), so the m-row range stays inside the
  // record's own region (the production bases are >= 1,792 words apart)
  if (rows > 1) for (k = 0; k < nrec; k = k + 1) begin
   if (rows * n[k] > 1792) $fatal(1, "FATAL: +ROWS too large for the record regions");
   ob[k] = ab[k];
  end
  $fclose(fd);
  repeat (4) @(posedge clk); rst_n = 1; repeat (8) @(posedge clk);
  for (k = 0; k < nrec; k = k + 1) begin           // preload (untimed)
   fn = $sformatf("%s/in_%0d.hex", dir, k); $readmemh(fn, gin, 0, n[k] / 8 - 1);
   for (s = 0; s < n[k] / 8; s = s + 1) vm_write(15'(ab[k] / 8 + s), gin[s]);
  end
  repeat (8) @(negedge clk);
  t0 = cyc; started = 1;
  for (k = 0; k < nrec; k = k + 1) begin
   while (!ret[0]) @(negedge clk);
   h = 128'd0; h[127:124] = 4'd4; h[123:118] = 6'(op[k]); h[99:93] = (MUT == 1) ? 7'b0010000 : 7'b0010001;
   if (op[k] == 6) h[71:64] = 8'd16;
   da = desc(3'd0, 40'(ab[k]), 20'(n[k]), 20'(rows), rows > 1 ? 32'(n[k]) : 32'd0);
   dd = desc(3'd0, 40'(ob[k]), 20'(n[k]), 20'(rows), rows > 1 ? 32'(n[k]) : 32'd0);
   rec = {21'(n[k]), 21'(n[k]), dd, da, h, 1'b1}; iss[k] = cyc - t0; total_cost = total_cost + cost[k];
   @(negedge clk); rec[0] = 0;
  end
  while (nret < nrec) begin @(negedge clk); if (cyc - t0 > 200000) $fatal(1, "FATAL: liveness (%0d dones)", nret); end
  for (k = 0; k < nrec; k = k + 1) begin
   bk = bad; fn = $sformatf("%s/out_%0d.hex", dir, k); $readmemh(fn, gout, 0, n[k] / 8 - 1);
   for (s = 0; s < n[k] / 8; s = s + 1) begin
    vm_read(15'(ob[k] / 8 + s));
    for (j = 0; j < 8; j = j + 1) begin
     if (sd[j*32 +: 32] !== gout[s][j*32 +: 32]) begin
      if (bad < 8) $display("MISMATCH rec %0d word %0d: %h != %h", k, 8*s + j, sd[j*32 +: 32], gout[s][j*32 +: 32]);
      bad = bad + 1;
     end
     words = words + 1;
    end
   end
   $display("EXACT %0d mismatch %0d", k, bad - bk);
  end
  for (k = 0; k < 8; k = k + 1) if (bank_status[k*18 + 17]) $fatal(1, "FATAL: bank %0d status %h", k, bank_status[k*18 +: 18]);
  if (bad) $fatal(1, "FATAL: %0d of %0d words mismatch", bad, words);
  if (rows > 1) $display("PASS HGI_QDQ_Q_ROWS rows=%0d records=%0d words=%0d cycles=%0d S=%0d", rows, nrec, words, prev, S);
  else
  $display("PASS HGI_QDQ_Q_TPUT records=%0d words=%0d cycles=%0d priced=%0d S=%0d", nrec, words, prev, total_cost, S);
  $finish;
 end
endmodule
