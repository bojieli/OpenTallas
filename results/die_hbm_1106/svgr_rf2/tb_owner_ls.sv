`timescale 1ns/1ps
// DIE-HBM-82-SVGR 11-06: lock-step ot_svgr_owner_rf (RF1, reference) vs ot_svgr_owner_rf2 (RF2) under random blocks.
// Declared RF2 change: the owner issues from the 2nd edge of a block (per-block terms registered). The reference sees
// block_active delayed by that one edge (ref_active = block_active && blk_d); every output must then match each cycle.
module tb;
 parameter integer MUT=0, SEED=1, N=400000;
 localparam integer AW=5, LB=2;
 reg clk=0, rst_n=0; always #1 clk=~clk;
 reg [4:0] pc_id=5'd9;
 reg descriptor_v=0, block_active=0; reg [29:0] base=0; reg [19:0] pcs=0; reg [14:0] rowb=0; reg [11:0] total=0;
 reg [LB-1:0] bank=0; reg [15:0] epoch=0; reg stop=0, k_ready=0, kr_v=0, take=0; reg [16:0] kr_tag=0; reg [3:0] kr_beat=0;
 reg blk_d=0; always @(posedge clk) blk_d<=block_active;
 wire ref_active=block_active&&blk_d;
 wire [31:0] r1h=32'd1<<kr_tag[AW-1:0];
 wire a_kv,b_kv,a_ok,b_ok,a_f,b_f,a_d,b_d; wire [29:0] a_ad,b_ad; wire [3:0] a_l,b_l; wire [16:0] a_t,b_t;
 wire [10:0] a_o,b_o; wire [15:0] a_e,b_e; wire [LB-1:0] a_b,b_b;
 ot_svgr_owner_rf #(.OWNER_AW(AW),.LB(LB)) A(.pc_id(pc_id),.clk(clk),.rst_n(rst_n),.descriptor_v(descriptor_v),
  .block_active(ref_active),.block_base(base),.block_pcs(pcs),.block_row_base(rowb),.block_total(total),.block_bank(bank),
  .block_epoch(epoch),.stop(stop),.k_ready(k_ready),.kr_v(kr_v),.kr_tag(kr_tag),.kr_beat(kr_beat),.response_take(take),
  .k_v(a_kv),.k_addr(a_ad),.k_len(a_l),.k_tag(a_t),.response_ok(a_ok),.response_ordinal(a_o),.response_epoch(a_e),
  .response_bank(a_b),.fault(a_f),.issue_done(a_d));
 ot_svgr_owner_rf2 #(.OWNER_AW(AW),.LB(LB),.MUT(MUT)) B(.pc_id(pc_id),.clk(clk),.rst_n(rst_n),.descriptor_v(descriptor_v),
  .block_active(block_active),.block_base(base),.block_pcs(pcs),.block_row_base(rowb),.block_total(total),.block_bank(bank),
  .block_epoch(epoch),.stop(stop),.k_ready(k_ready),.kr_v(kr_v),.kr_tag(kr_tag),.kr_ret1h(r1h),.kr_beat(kr_beat),.response_take(take),
  .k_v(b_kv),.k_addr(b_ad),.k_len(b_l),.k_tag(b_t),.response_ok(b_ok),.response_ordinal(b_o),.response_epoch(b_e),
  .response_bank(b_b),.fault(b_f),.issue_done(b_d));
 // outstanding requests (issued by the reference), returned in order beat by beat
 reg [16:0] qt[0:63]; reg [3:0] ql[0:63]; integer qh=0, qn=0, beat=0, cyc=0, mism=0, issued=0, resp=0, blocks=0, idle=0;
 integer s; integer i;
 always @(negedge clk) if(rst_n) begin
  cyc=cyc+1;
  // k_addr/k_len are don't-care while k_v is 0 (RF1 decodes them from the live block, RF2 from the registered terms)
  if({a_kv,a_kv?{a_ad,a_l}:34'd0,a_t,a_ok,a_o,a_e,a_b,a_f,a_d}!=={b_kv,b_kv?{b_ad,b_l}:34'd0,b_t,b_ok,b_o,b_e,b_b,b_f,b_d}) begin
   mism=mism+1;
   if(mism<=5) $display("MISMATCH cyc %0d ref kv%0d ad%h l%0d t%0d ok%0d o%0d e%0d b%0d f%0d d%0d | rf2 kv%0d ad%h l%0d t%0d ok%0d o%0d e%0d b%0d f%0d d%0d",
     cyc,a_kv,a_ad,a_l,a_t,a_ok,a_o,a_e,a_b,a_f,a_d,b_kv,b_ad,b_l,b_t,b_ok,b_o,b_e,b_b,b_f,b_d);
  end
 end
 initial begin
  s=SEED; i=$urandom(s);
  repeat(3) @(posedge clk); #0.2 rst_n=1;
  for(i=0;i<N;i=i+1) begin
   @(posedge clk); #0.2;
   // record the reference request accepted on the edge just taken
   descriptor_v=0;
   if(!block_active && qn==0 && $urandom%4==0) begin
    descriptor_v=1; block_active=1; blocks=blocks+1;
    base=$urandom; rowb=$urandom; total=$urandom%40; bank=$urandom; epoch=$urandom;
    pcs=$urandom;
    case($urandom%4) 0: pcs[4:0]=pc_id; 1: pcs[9:5]=pc_id; 2: pcs[14:10]=pc_id; default: pcs[19:15]=pc_id; endcase
    if($urandom%5==0) pcs[19:15]=5'd31;
    idle=0;
   end else if(block_active && a_d && qn==0) begin
    idle=idle+1; if(idle>2) block_active=0;
   end
   stop=($urandom%500==0);
   k_ready=($urandom%3!=0);
   kr_v=0; take=0;
   if(qn>0 && $urandom%2==0) begin kr_v=1; kr_tag=qt[qh]; kr_beat=beat; end
   #0.3;
   if(kr_v && a_ok) take=1;
   #0.3;
   if(take) begin resp=resp+1; beat=beat+1; if(beat>=ql[qh]) begin beat=0; qh=(qh+1)%64; qn=qn-1; end end
   if(a_kv && k_ready) begin qt[(qh+qn)%64]=a_t; ql[(qh+qn)%64]=a_l; qn=qn+1; issued=issued+1; end
   if(a_f) begin // fault is sticky: reset both and go on
    rst_n=0; block_active=0; qn=0; beat=0; @(posedge clk); #0.2 rst_n=1;
   end
  end
  $display("OWNER_LS MUT=%0d SEED=%0d cycles=%0d blocks=%0d issued=%0d resp_beats=%0d mismatches=%0d %s",MUT,SEED,cyc,blocks,issued,resp,mism,mism==0?"PASS":"FAIL");
  $finish;
 end
endmodule
