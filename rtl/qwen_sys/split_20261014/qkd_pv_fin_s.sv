`timescale 1ns/1ps
// KV-PLAN-FIN 2026-10-17: qkd_pv_fin_s -- the PV final join as ONE 512-b BEAT-STREAM slice (die element pvfin).
//
// Replaces the die use of ot_qwen_tp8_pv256_finalize_static_cal (32 x ot_qwen_tp8_pv_join16_static_cal = 512 FP32 adders +
// 512 FP32 multipliers fed by two 16,384-b words) with the SAME arithmetic per 512-b block, time-multiplexed over the 32
// result beats: beat b (= finalize block b = PV column s = b) is
//     out[32 l +: 32] = fp32_mul( fp32_add(p0_b[32 l +: 32], p1_b[32 l +: 32]), rz[32 (b / 8) +: 32] ),  l = 0..15
// with the operands in the reference's order (adder a = pair 0, b = pair 1; multiplier a = sum, b = reciprocal of head
// b / 8), the same ot_hdc_fp32_add_lat / ot_hdc_fp32_mul_lat units and latencies, so every beat is bit-identical to the
// reference's out_data[512 b +: 512] (lockstep bench rtl/test/qwen_split/tb_qkd_pv_fin_s.sv).
//
// Why (die plan, results/arch/qwen_kv_pvfin_1017/plan.json): each PV pair's 16,384-b result leaves 32 column joins spread
// over its 11 mm frame at 32 different static ages (qkd_pvw_die_t COL_D: 0 .. -42 edges); a 16-kb word gathered at one
// face is a 2 x 16,384-b star (~360 Mbit.mm of die wire, ~690k relay flops) and needs deskew pads.  The pair successor
// carries its 32 column words on ONE 512-b registered result trunk to its strip (which faces the attention hub); this
// slice sits between the two strips beside the hub (the reciprocal source) and emits the 32 beats in order to the
// attention result face (STREAM=1), which no longer buffers 16,384 b.
//
// Static schedule (edge n = the n-th edge after the start edge; "slot X" = sampled at edge X):
//   cal = {R_AGE, P1_AGE, P0_AGE}: pair 0 beat b is sampled at edge P0_AGE + b, pair 1 beat b at P1_AGE + b,
//   the 4 head reciprocals (128 b) at edge R_AGE.  LASTP = max(P0_AGE, P1_AGE); |P0_AGE - P1_AGE| <= SKEW (the earlier
//   stream waits in a SKEW-deep tap line).  LAST = max(P0_AGE, P1_AGE, R_AGE) = the reference's LAST_CAPTURE.
//   add issue  b: edge LASTP + 1 + b            (ADD_AGE + b)
//   sum  slot  b: edge ADD_AGE + ADD_LAT + b    (SUM_AGE + b; sum b -> sbuf[b])
//   mul issue  b: edge LAST + ADD_LAT + 2 + b   (MUL_AGE + b; operand sbuf[b])
//   product    b: edge MUL_AGE + MUL_LAT + b    (PRODUCT_AGE + b; out_* registered, high for the following cycle)
// QXF-FACE 10-18 (TOKEN-XDIE-QWEN F3): the product timeline follows the reference / compiler law max(P0, P1, R) (the
// reference ot_qwen_tp8_pv256_finalize_static_cal adds at LAST_CAPTURE + 1 = max(P0, P1, R) + 1).  The die's calendar
// generator runs STRETCH=1 (kv_static_programme.attention_calendar: R = SERVICE_END - 49 - PV_START, so the service ends
// on the link's fixed RESULT slot, TX_FIRST 1750); its R lies 106 (T = 8192) .. 832 (T = 256) edges after LASTP.  The
// pair streams cannot wait (each beat passes once), so the 32 sums are kept in sbuf (32 x 512 b, written in beat order
// at SUM_AGE + b, read in beat order at MUL_AGE + b; MUL_AGE = SUM_AGE + 1 when R <= LASTP, i.e. the old timeline).
// Before this, R > LASTP + ADD_LAT + 1 was refused as an unmeetable calendar (every STRETCH=1 command faulted) and
// R in (LASTP, LASTP + 8] produced the result max(P0, P1) - based, earlier than the reference.
// Every input is checked against its compiled slot (valid exactly in the window, beat index, epoch); a mismatch, an
// adder / multiplier error flag, a unit valid off its slot, a start while active or an unmeetable calendar sets the
// sticky fault and stops the command.  No ready / credit signal exists (static cycle schedule).
// Pins: every input is registered at the pin (control *_q, data = tap 0 of the operand line) and every output is a flop;
// the pin stage delays every input by the same one edge, so the ages above hold at the pins and the first output beat
// leaves PRODUCT_AGE + 1 edges after the start pin edge (the reference: PRODUCT_AGE).
// MUT (bench negative controls only): 1 = reciprocal head index (b + 1) / 8, 2 = pair-0 operand one tap late,
//   3 = R left out of the join age (multiply on max(P0, P1): the pre-10-18 timeline, no R check).
module qkd_pv_fin_s #(
 parameter integer ADD_LAT=7,
 parameter integer MUL_LAT=6,
 parameter integer SKEW=2,
 parameter integer MUT=0
)(
 input wire ck,rst_n,
 input wire start,input wire [15:0] epoch,input wire [47:0] cal,
 input wire p0_valid,input wire [4:0] p0_beat,input wire [15:0] p0_epoch,input wire [511:0] p0_data,
 input wire p1_valid,input wire [4:0] p1_beat,input wire [15:0] p1_epoch,input wire [511:0] p1_data,
 input wire rz_valid,input wire [15:0] rz_epoch,input wire [127:0] rz,
 output reg out_valid,output reg [4:0] out_beat,output reg [15:0] out_epoch,output reg [511:0] out_data,
 output reg fault
);
 // pin registers (control); the data pins land in tap 0 of the operand lines
 reg start_q,p0v_q,p1v_q,rzv_q;reg [15:0] epoch_q,p0e_q,p1e_q,rze_q;reg [47:0] cal_q;reg [4:0] p0b_q,p1b_q;reg [127:0] rz_q;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin start_q<=0;p0v_q<=0;p1v_q<=0;rzv_q<=0;end
  else begin start_q<=start;p0v_q<=p0_valid;p1v_q<=p1_valid;rzv_q<=rz_valid;end
 always @(posedge ck)begin epoch_q<=epoch;cal_q<=cal;p0b_q<=p0_beat;p1b_q<=p1_beat;p0e_q<=p0_epoch;p1e_q<=p1_epoch;
  rze_q<=rz_epoch;rz_q<=rz;end
 reg active;reg [15:0] age,ep,P0,P1,RA,MUL_AGE;
 wire [15:0] LASTP=(P0>P1)?P0:P1;
 wire [15:0] D0=LASTP-P0,D1=LASTP-P1;
 wire [15:0] ADD_AGE=LASTP+16'd1,SUM_AGE=ADD_AGE+16'(ADD_LAT),PRODUCT_AGE=MUL_AGE+16'(MUL_LAT);
 wire [15:0] n=age+16'd1;                                  // the edge that ends this cycle
 function automatic win(input [15:0] x,input [15:0] lo);win=(x>=lo)&&(x<lo+16'd32);endfunction
 wire p0_slot=active&&win(n,P0),p1_slot=active&&win(n,P1),r_slot=active&&n==RA;
 wire add_slot=active&&win(n,ADD_AGE),sum_slot=active&&win(n,SUM_AGE);
 wire mul_slot=active&&win(n,MUL_AGE),product_slot=active&&win(n,PRODUCT_AGE);
 wire [4:0] b_p0=5'(n-P0),b_p1=5'(n-P1),b_prod=5'(n-PRODUCT_AGE);
 // calendar of a new command (checked on the start edge)
 wire [15:0] c0=cal_q[15:0],c1=cal_q[31:16],cr=cal_q[47:32];
 wire [15:0] c_lastp=(c0>c1)?c0:c1;
 wire [15:0] c_last=(MUT==3||c_lastp>cr)?c_lastp:cr;          // max(P0, P1, R)
 wire [15:0] c_skew=(c0>c1)?(c0-c1):(c1-c0);
 wire cal_bad=(c0<16'd1)||(c1<16'd1)||(cr<16'd1)||(c_skew>16'(SKEW))||({1'b0,c_last}+17'd64+17'(ADD_LAT+MUL_LAT)>17'hffff);
 // operand tap lines: tap 0 = the pin register (= this cycle's registered input), tap k = the beat k edges older
 reg [511:0] t0[0:SKEW+1],t1[0:SKEW+1];
 integer k;
 always @(posedge ck)begin
  t0[0]<=p0_data;t1[0]<=p1_data;
  for(k=1;k<=SKEW+1;k=k+1)begin t0[k]<=t0[k-1];t1[k]<=t1[k-1];end
 end
 wire [15:0] D0m=(MUT==2&&D0<SKEW)?D0+16'd1:D0;
 wire [511:0] opa=t0[D0m[7:0]+8'd1],opb=t1[D1[7:0]+8'd1];   // +1: the registered copy sampled at the slot edge
 reg [511:0] sbuf[0:31];reg [4:0] wptr,rptr;reg [127:0] rzr;   // sums of this command, beat order
 wire [511:0] saved_sum=sbuf[rptr];
 wire [2:0] hb=(MUT==1)?3'(({1'b0,rptr}+6'd1)>>3):3'(rptr>>3);
 wire [31:0] rzh=(hb==3'd0)?rzr[31:0]:(hb==3'd1)?rzr[63:32]:(hb==3'd2)?rzr[95:64]:rzr[127:96];
 wire [511:0] sum,product;wire [15:0] av,mv;wire [31:0] ae,me;
 genvar l;
 generate for(l=0;l<16;l=l+1)begin:g_lane
  ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add(.clk(ck),.rst_n(rst_n),.valid_in(add_slot&&!fault),
   .a(opa[32*l+:32]),.b(opb[32*l+:32]),.y(sum[32*l+:32]),.err(ae[2*l+:2]),.valid_out(av[l]));
  ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul(.clk(ck),.rst_n(rst_n),.valid_in(mul_slot&&!fault),
   .a(saved_sum[32*l+:32]),.b(rzh),.y(product[32*l+:32]),.err(me[2*l+:2]),.valid_out(mv[l]));
 end endgenerate
 wire bad=(p0v_q!=p0_slot)||(p1v_q!=p1_slot)||(rzv_q!=r_slot)||
          (p0_slot&&(p0b_q!=b_p0||p0e_q!=ep))||(p1_slot&&(p1b_q!=b_p1||p1e_q!=ep))||(r_slot&&rze_q!=ep)||
          (av!={16{sum_slot}})||(mv!={16{product_slot}})||(sum_slot&&|ae)||(product_slot&&|me);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin active<=0;age<=0;ep<=0;P0<=16'hffff;P1<=16'hffff;RA<=16'hffff;MUL_AGE<=16'hffff;fault<=0;
   out_valid<=0;out_beat<=0;out_epoch<=0;wptr<=0;rptr<=0;end
  else begin
   out_valid<=0;
   if(start_q)begin
    if(active||cal_bad)begin fault<=1;active<=0;end
    else begin active<=1;age<=0;ep<=epoch_q;P0<=c0;P1<=c1;RA<=cr;MUL_AGE<=c_last+16'(ADD_LAT+2);wptr<=0;rptr<=0;end
   end else if(active&&!fault)begin
    age<=n;
    if(bad)begin fault<=1;active<=0;end
    else begin
     if(sum_slot)wptr<=wptr+5'd1;
     if(mul_slot)rptr<=rptr+5'd1;
     if(product_slot)begin out_valid<=1;out_beat<=b_prod;out_epoch<=ep;end
     if(n==PRODUCT_AGE+16'd31)active<=0;
    end
   end else if(!active&&(p0v_q||p1v_q||rzv_q))fault<=1;
  end
 end
 always @(posedge ck)begin
  if(r_slot)rzr<=rz_q;
  if(sum_slot)sbuf[wptr]<=sum;
  if(product_slot)out_data<=product;
 end
endmodule
