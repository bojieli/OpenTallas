`timescale 1ns/1ps
`default_nettype none
// HBM-B-RTL1 2026-10-17: lockstep of the plan (b) delivery lane ot_hbm_svc_vmdel_lane_n #(NPC 2) against the d4f lane
// ot_hbm_svc_vmdel_lane (NPC 4) on the same landing traffic.  Both lanes see the same begin / start / epochs and the SAME
// fills on PC slots 0 and 1; the d4f lane's slots 2 and 3 get their own fills (so its block can complete).  Four blocks
// (double-buffer banks 0/1, two epochs, two bases).  Checks: the NPC-2 dq stream equals the d4f stream restricted to
// groups 0/1, beat for beat: same data, mask, bank, valid; sector = base + slot*16 + group*8 (d4f: base + slot*32 +
// group*8); each NPC-2 beat (slot s, group g) leaves start + 2 + (2s + g) edges after the start edge (d4f: 4s + g);
// block_ready rises on the same edge as the d4f lane when slots 0/1 complete last; no fault.  MUT 1 = the NPC-2 lane's
// two fill slots swapped, MUT 2 = start issued one block too early (last fill missing -> start rejected, sticky fault).
// Also: ot_hbm_svc_vmdel_lane_n #(NPC 4) (u_c) == the d4f lane (u_a) on every output every edge; MUT 3 = u_c's fill_v[2]
// dropped on one beat (must FAIL).
`ifndef MUT
`define MUT 0
`endif
module tb_hbm_svc_vmdel_lane_n_lockstep;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg begin_v=0, begin_bank=0, start=0, start_bank=0; reg [15:0] begin_epoch=0, start_epoch=0, base=0;
 reg [3:0] fv=0, fb=0; reg [23:0] fs=0; reg [63:0] fe=0; reg [1023:0] fd=0;
 wire a_f0,a_f1,a_pb,b_f0,b_f1,b_pb,a_bz,b_bz,a_ft,b_ft; wire [1:0] a_br,b_br; wire [280:0] a_dq,b_dq;
 ot_hbm_svc_vmdel_lane u_a(.clk(clk),.rst_n(rst_n),.bank_id(3'd5),.begin_v_i(begin_v),.begin_bank_i(begin_bank),
  .begin_epoch_i(begin_epoch),.start_i(start),.start_bank_i(start_bank),.start_epoch_i(start_epoch),.start_base_sector_i(base),
  .fill_v_i(fv),.fill_bank_i(fb),.fill_slot_i(fs),.fill_epoch_i(fe),.fill_data_i(fd),
  .full0_all({8{a_f0}}),.full1_all({8{a_f1}}),.pcbad_all({8{a_pb}}),.full0(a_f0),.full1(a_f1),.pcbad(a_pb),
  .block_ready(a_br),.busy(a_bz),.fault(a_ft),.dq(a_dq));
 reg mute=0;
 wire [1:0] bfv = mute ? 2'b00 : (`MUT==1) ? {fv[0],fv[1]} : fv[1:0];
 wire [1:0] bfb = (`MUT==1) ? {fb[0],fb[1]} : fb[1:0];
 wire [11:0] bfs = (`MUT==1) ? {fs[5:0],fs[11:6]} : fs[11:0];
 wire [31:0] bfe = (`MUT==1) ? {fe[15:0],fe[31:16]} : fe[31:0];
 wire [511:0] bfd = (`MUT==1) ? {fd[255:0],fd[511:256]} : fd[511:0];
 ot_hbm_svc_vmdel_lane_n #(.NPC(2)) u_b(.clk(clk),.rst_n(rst_n),.bank_id(3'd5),.begin_v_i(begin_v),.begin_bank_i(begin_bank),
  .begin_epoch_i(begin_epoch),.start_i(start),.start_bank_i(start_bank),.start_epoch_i(start_epoch),.start_base_sector_i(base),
  .fill_v_i(bfv),.fill_bank_i(bfb),.fill_slot_i(bfs),.fill_epoch_i(bfe),.fill_data_i(bfd),
  .full0_all({8{b_f0}}),.full1_all({8{b_f1}}),.pcbad_all({8{b_pb}}),.full0(b_f0),.full1(b_f1),.pcbad(b_pb),
  .block_ready(b_br),.busy(b_bz),.fault(b_ft),.dq(b_dq));
 wire c_f0,c_f1,c_pb,c_bz,c_ft; wire [1:0] c_br; wire [280:0] c_dq; reg cmut=0;
 ot_hbm_svc_vmdel_lane_n #(.NPC(4)) u_c(.clk(clk),.rst_n(rst_n),.bank_id(3'd5),.begin_v_i(begin_v),.begin_bank_i(begin_bank),
  .begin_epoch_i(begin_epoch),.start_i(start),.start_bank_i(start_bank),.start_epoch_i(start_epoch),.start_base_sector_i(base),
  .fill_v_i(fv & ~{1'b0,cmut,2'b0}),.fill_bank_i(fb),.fill_slot_i(fs),.fill_epoch_i(fe),.fill_data_i(fd),
  .full0_all({8{c_f0}}),.full1_all({8{c_f1}}),.pcbad_all({8{c_pb}}),.full0(c_f0),.full1(c_f1),.pcbad(c_pb),
  .block_ready(c_br),.busy(c_bz),.fault(c_ft),.dq(c_dq));
 integer nc4=0, e4=0;
 always @(negedge clk) if(rst_n) begin nc4=nc4+1; if({c_dq,c_br,c_bz,c_ft,c_f0,c_f1,c_pb}!=={a_dq,a_br,a_bz,a_ft,a_f0,a_f1,a_pb}) e4=e4+1; end
 // beat queues
 reg [280:0] qa [0:4095]; integer ta [0:4095]; reg [280:0] qb [0:4095]; integer tb_ [0:4095];
 integer na=0, nb=0, cyc=0, errs=0, k, blk, s, g, nblk=0, tstart [0:7]; reg [15:0] bases [0:7];
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(a_dq[280]) begin qa[na]=a_dq; ta[na]=cyc; na=na+1; end
  if(b_dq[280]) begin qb[nb]=b_dq; tb_[nb]=cyc; nb=nb+1; end
 end
 task fill(input integer bk, input [15:0] ep, input integer blkid);
  integer sl, p; reg [3:0] ord;
  begin
   for(sl=0; sl<64; sl=sl+1) begin
    // slots 0/1 (shared) and 2/3 (d4f only) arrive in a rotating order; slot 0/1 finish LAST on odd blocks
    @(negedge clk); fv=4'b1111; fb={4{1'(bk)}}; fs={4{6'(sl)}}; fe={4{ep}};
    cmut=(`MUT==3 && blkid==2 && sl==10);
    for(p=0;p<4;p=p+1) fd[p*256+:256]={8{32'(blkid*1000000+p*100000+sl*100+7)}} ^ {8{$urandom}};
    if(blkid%2==1 && sl==63) begin fv=4'b1100; @(negedge clk); fv=4'b0011; fb={4{1'(bk)}}; fs={4{6'(sl)}}; fe={4{ep}}; mute=(`MUT==2 && blkid==3); end
   end
   @(negedge clk); fv=0; mute=0;
  end
 endtask
 initial begin
  repeat(4) @(negedge clk); rst_n=1; repeat(4) @(negedge clk);
  for(blk=0; blk<4; blk=blk+1) begin
   @(negedge clk); begin_v=1; begin_bank=1'(blk); begin_epoch=16'(100+blk); @(negedge clk); begin_v=0;
   repeat(3) @(negedge clk);
   fill(blk%2, 16'(100+blk), blk);
   repeat(6) @(negedge clk);           // STATUS_LAT 2 + lane LAT: block_ready settled
   if(a_br[blk%2]!==1'b1 || b_br[blk%2]!==1'b1) begin errs=errs+1; $display("block %0d ready a %b b %b", blk, a_br, b_br); end
   @(negedge clk); start=1; start_bank=1'(blk); start_epoch=16'(100+blk); base=(blk<2)?16'd0:16'd2048; bases[blk]=base; tstart[blk]=cyc;
   @(negedge clk); start=0;
   repeat(300) @(negedge clk);
  end
  repeat(20) @(negedge clk);
  // compare: NPC-2 beats == d4f beats with group < 2
  k=0;
  for(s=0; s<na; s=s+1) begin : CMP
   reg [15:0] sec; integer idx, sl_, gr, j;
   sec={qa[s][279:267],3'b0};
   blk=s/256; idx=(sec-bases[blk])/8; sl_=idx/4; gr=idx%4;
   if(gr<2) begin
    j=blk*128+sl_*2+gr;
    if(j>=nb) begin errs=errs+1; end
    else begin
     if(qb[j][263:0]!==qa[s][263:0] || {qb[j][279:267],3'b0}!==bases[blk]+16'(sl_*16+gr*8) || qb[j][266:264]!==qa[s][266:264]) begin
      errs=errs+1; if(errs<6) $display("MISMATCH blk %0d slot %0d group %0d", blk, sl_, gr); end
     if(tb_[j]-tstart[blk]!==ta[blk*256]-tstart[blk]+sl_*2+gr) begin errs=errs+1; if(errs<6) $display("TIMING blk %0d slot %0d group %0d: %0d", blk, sl_, gr, tb_[j]-tstart[blk]); end
     k=k+1;
    end
   end
  end
  if(a_ft||b_ft) begin errs=errs+1; $display("FAULT a %b b %b", a_ft, b_ft); end
  if(e4!=0) begin errs=errs+1; $display("NPC4 copy != d4f lane on %0d of %0d edges", e4, nc4); end
  $display("NPC4 equivalence edges %0d mismatches %0d", nc4, e4);
  $display("d4f beats %0d, NPC2 beats %0d, compared %0d, first-beat edge after start %0d", na, nb, k, ta[0]-tstart[0]);
  if(errs==0 && na==1024 && nb==512 && k==512) $display("VMDEL_N_LOCKSTEP PASS MUT=%0d", `MUT);
  else $display("VMDEL_N_LOCKSTEP FAIL MUT=%0d errors=%0d", `MUT, errs);
  $finish;
 end
endmodule
`default_nettype wire
