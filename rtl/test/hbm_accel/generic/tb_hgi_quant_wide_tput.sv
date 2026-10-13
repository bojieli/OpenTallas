`timescale 1ps/1ps
// tput-gate-1010 (2026-10-10): the WIDE quant unit (ot_hgi_quant_wide on the VM unit's RP / W2 lane group, LQ credits)
// on the same vectors / protocol as tb_hgi_quant_tput (copied below).  WMUT 1 = wide tag mutant (must FAIL), WMUT 3 = every
// record forced to the packet path (control: must PASS at the packet rate).
// FUSED.QDQ_* THROUGHPUT bench (hgi-1010/g): ot_hgi_quant_unit (normative record bus) <-> the real ot_hgi_vm_unit
// (client 0) with the bench as VM client 1.  The bench preloads every record's A operand through client 1 (untimed),
// then dispatches the records sequentially by default (OVERLAP=1 decouples admission from retirement) (a record is on the bus the cycle the unit reports ready: the CP's unit
// queue holds the next one), timing each from cycle 0 = the first dispatch.  Per record it prints
//   TPUT k <op> <n> issue <cycle> ret <cycle> cost <sim price>
// and, after the last record, reads every O back through client 1 and compares each word with the released golden.
// Vectors: tools/hgi_unit_tput/qdq_vectors.py (recs.txt, in_<k>.hex, out_<k>.hex).
// MUT 1: the record header drops the A operand bit -> the unit faults (must FAIL);
// MUT 2: transport mutant 4 (responses paired with the newest request) -> wrong words (must FAIL).
module tb_hgi_quant_wide_tput;
 parameter integer MUT = 0, SERIAL_SHAPE = 0, WMUT = 0, LQ = 16, WQ = 0, OVERLAP = 0, ACKSKEW = 0, DEPENDENCY = 0;
 reg clk = 0; always #416 clk = ~clk; reg rst_n = 0;
 reg [682:0] rec = 0; wire [2:0] ret; wire [337:0] vmq; wire [273:0] vmr0;
 reg [337:0] bq = 0; wire [273:0] br; wire [18:0] status;
 wire [32*16-1:0] rq; wire [31:0] rq_cr, w2_cr, w2_done; wire [32*257-1:0] rr; wire [32*280-1:0] w2q;
 wire [31:0] ack;
 generate if (ACKSKEW != 0) begin : g_skew
  reg [ACKSKEW-1:0] delayed = 0;
  always @(posedge clk) if (!rst_n) delayed<=0; else delayed<={delayed[ACKSKEW-2:0],w2_done[0]};
  assign ack={w2_done[31:1],delayed[ACKSKEW-1]};
 end else assign ack=w2_done; endgenerate
 ot_hgi_quant_unit #(.MUT(MUT == 2 ? 4 : 0), .SERIAL_SHAPE(SERIAL_SHAPE), .WIDE(1), .WLQ(LQ), .WMUT(WMUT), .WQ(WQ)) dut (.clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret),
   .vmq(vmq), .vmr(vmr0), .wrq(rq), .wrq_cr(rq_cr), .wrr(rr), .wwq(w2q), .wwq_cr(w2_cr), .wwq_done(ack),
   .rg_req(), .rg_gnt(1'b1), .wg_req(), .wg_gnt(1'b1));
 ot_hgi_vm_unit #(.NC(2), .RP(32), .W2(32), .LQ(LQ)) vm (.clk(clk), .rst_n(rst_n), .cq({bq, vmq}), .cr({br, vmr0}), .status(status),
   .wq(280'd0), .wq_done(), .rq(rq), .rq_cr(rq_cr), .rr(rr), .w2q(w2q), .w2q_cr(w2_cr), .w2q_done(w2_done));
 reg [255:0] gin [0:127]; reg [255:0] gout [0:127];
 integer nrec, fd, k, s, j, op [0:15], n [0:15], ab [0:15], ob [0:15], cost [0:15], blk [0:15];
 integer cyc = 0, issue, words = 0, bad = 0, bk = 0, total_busy = 0, total_cost = 0;
 string dir, fn;
 // OVERLAP=1 separates command admission from retirement.  The historical loop below waits
 // for each completion before presenting the next record, which cannot exercise record overlap.
 integer retired = 0, issue_at [0:15], ret_at [0:15];
 reg measure = 0;
 integer lane_acks[0:31], lane_target[0:15][0:31];
 always @(posedge clk) if (measure) for(integer b=0;b<32;b=b+1) lane_acks[b]=lane_acks[b]+integer'(ack[b]);
 always @(negedge clk) if (measure && OVERLAP) begin
  if (ret[2]) $fatal(1, "FATAL: record %0d fault (MUT %0d)", retired, MUT);
  if (ret[1]) begin
   if (retired >= nrec) $fatal(1, "FATAL: extra completion");
   if (WQ==3 && WMUT!=3) for(integer b=0;b<32;b=b+1)
    if (lane_acks[b] < lane_target[retired][b])
     $fatal(1,"FATAL: premature retirement record %0d lane %0d ack %0d target %0d",retired,b,lane_acks[b],lane_target[retired][b]);
   ret_at[retired] = cyc - t0;
   $display("TPUT %0d op %0d n %0d issue %0d ret %0d cost %0d", retired, op[retired], n[retired], issue_at[retired], ret_at[retired], cost[retired]);
   retired = retired + 1;
  end
 end
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
 reg [127:0] h; reg [255:0] da, dd; integer t0, t1;
 initial begin
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "FATAL: +DIR");
  fd = $fopen({dir, "/recs.txt"}, "r"); void'($fscanf(fd, "%d", nrec));
  for (k = 0; k < nrec; k = k + 1) void'($fscanf(fd, "%d %d %d %d %d %d", op[k], n[k], ab[k], ob[k], cost[k], blk[k]));
  $fclose(fd);
  repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
  for (k = 0; k < nrec; k = k + 1) begin           // preload (untimed)
   fn = $sformatf("%s/in_%0d.hex", dir, k); $readmemh(fn, gin, 0, n[k] / 8 - 1);
   for (s = 0; s < n[k] / 8; s = s + 1) if (!(DEPENDENCY && k==1)) vm_write(15'(ab[k] / 8 + s), gin[s]);
  end
  repeat (8) @(negedge clk);
  for(integer b=0;b<32;b=b+1) lane_acks[b]=0;
  for(integer r=0;r<nrec;r=r+1) begin
   for(integer b=0;b<32;b=b+1) lane_target[r][b]= r==0 ? 0 : lane_target[r-1][b];
   for(integer s=0;s<n[r]/8;s=s+1) lane_target[r][(ob[r]/8+s)%32]=lane_target[r][(ob[r]/8+s)%32]+1;
  end
  t0 = cyc; measure = 1;
  for (k = 0; k < nrec; k = k + 1) begin
   while (!ret[0]) @(negedge clk);
   h = 128'd0; h[127:124] = 4'd4; h[123:118] = 6'(op[k]); h[99:93] = (MUT == 1) ? 7'b0010000 : 7'b0010001;
   if (op[k] == 6) h[71:64] = 8'd16;
   da = desc(3'd0, 40'(ab[k]), 20'(n[k]), 20'd1, 32'd0); dd = desc(3'd0, 40'(ob[k]), 20'(n[k]), 20'd1, 32'd0);
   rec = {21'(n[k]), 21'(n[k]), dd, da, h, 1'b1}; issue = cyc - t0; issue_at[k] = issue; @(negedge clk); rec[0] = 0;
   if (!OVERLAP) begin
   while (!ret[1] && !ret[2]) begin @(negedge clk); if (cyc - t0 > 2000000) $fatal(1, "FATAL: liveness"); end
   if (ret[2]) $fatal(1, "FATAL: record %0d fault (MUT %0d)", k, MUT);
   t1 = cyc - t0;
   $display("TPUT %0d op %0d n %0d issue %0d ret %0d cost %0d", k, op[k], n[k], issue, t1, cost[k]);
   end
   total_cost = total_cost + cost[k];
   @(negedge clk);
  end
  if (OVERLAP) begin
   while (retired != nrec) begin @(posedge clk); if (cyc - t0 > 2000000) $fatal(1, "FATAL: overlap liveness"); end
   t1 = ret_at[nrec-1];
  end
  measure = 0;
  total_busy = t1;
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
  if (status[18:16] != 0) $fatal(1, "FATAL: VM status %b", status[18:16]);
  if (bad) $fatal(1, "FATAL: %0d of %0d words mismatch", bad, words);
  $display("PASS HGI_QDQ_WIDE_TPUT records=%0d words=%0d cycles=%0d priced=%0d", nrec, words, total_busy, total_cost);
  $finish;
 end
endmodule
