`timescale 1ns/1ps
// Q3 full64-lane exact descriptor. This only packs values that the SU already
// rounded onto E4M3; f32_e4m3 is copied byte-for-byte from the pinned service.
// Two bases encode fixed K stride16 or V stride1. Every active address must
// reconstruct exactly; otherwise the packet is suppressed and fault is sticky.
// PIPE=1 (sys-takeover 2026-10-09, opt-in, default 0 = byte-identical behaviour of the original): the routed original
// failed TT -425.55 on in_addr -> bad_q (32-deep first-active chain, 64 compares and a 64-way OR in one cycle).
// PIPE=1 splits it into two register stages, +1 write edge (3 -> 4), the same values and fault behaviour:
//   P1 (lane-local): both candidate bases addr-k*16 / addr-k (with borrow), own-stride select, E4M3 code,
//      off-grid / out-of-range flag and the first-active one-hot (prefix OR) per 32-lane group;
//   P2: one-hot AND-OR select of the group base and its stride, per-lane equality -> 64 registered bad bits;
//   out: OR of the 64 bad bits gates o_mask and sets the sticky fault (as bad_q did).
// Equivalence: base+k*s == addr (AW+1-bit, no overflow)  <=>  addr-k*s == base with no borrow.
module ot_qfd_su_kv624 #(parameter integer AW=24, MUT_ADDR=0, PIPE=0)(
 input wire clk,rst_n,input wire [63:0] i_mask,
 input wire [64*AW-1:0] i_addr,input wire [2047:0] i_data,
 output reg [63:0] o_mask,output reg [AW-1:0] o_a0,o_a1,
 output reg [511:0] o_data,output reg fault
);
    function automatic [8:0] f32_e4m3(input [31:0] b);   // {bad, code}
        reg [7:0] e; reg [22:0] m;
        begin
            e = b[30:23]; m = b[22:0];
            if (e == 0 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd0};
            else if (e >= 8'd121 && e <= 8'd135 && m[19:0] == 0) f32_e4m3 = {1'b0, b[31], e[3:0] - 4'd8, m[22:20]};
            else if (e == 8'd120 && m[20:0] == 0) f32_e4m3 = {1'b0, b[31], 4'd0, 1'b1, m[22:21]};
            else if (e == 8'd119 && m[21:0] == 0) f32_e4m3 = {1'b0, b[31], 5'd0, 1'b1, m[22]};
            else if (e == 8'd118 && m == 0) f32_e4m3 = {1'b0, b[31], 7'd1};
            else f32_e4m3 = {1'b1, 8'd0};
        end
    endfunction
 reg [63:0] in_mask;reg [1535:0] in_addr;reg [2047:0] in_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin in_mask<=0;in_addr<=0;in_data<=0;end
  else begin in_mask<=i_mask;in_addr<=i_addr;in_data<=i_data;end
 end

 localparam integer VBASE=131072*16;
 generate if (PIPE == 0) begin : g_orig
 reg [AW-1:0] bases[0:1];reg found[0:1];
 reg [511:0] codes;reg bad;integer i,g,stride;reg [8:0] code;
 reg [AW:0] expected;reg [AW-1:0] addr;
 always @(*)begin
  bases[0]=0;bases[1]=0;found[0]=0;found[1]=0;codes=0;bad=0;code=0;addr=0;expected=0;g=0;stride=0;
  for(i=0;i<64;i=i+1)begin
   g=i/32;addr=in_addr[i*AW+:AW];stride=(addr<VBASE)?16:1;
   if(in_mask[i]&&!found[g])begin bases[g]=addr-AW'((i%32)*stride);found[g]=1;end
  end
  for(i=0;i<64;i=i+1)begin
   g=i/32;addr=in_addr[i*AW+:AW];stride=(bases[g]<VBASE)?16:1;
   expected={1'b0,bases[g]}+(AW+1)'((i%32)*stride+(MUT_ADDR!=0?1:0));
   code=f32_e4m3(in_data[i*32+:32]);codes[i*8+:8]=code[7:0];
   if(in_mask[i]&&(code[8]||expected[AW]||expected[AW-1:0]!=addr||addr>=2*VBASE))bad=1;
  end
 end
 reg [63:0] mask_q;reg [AW-1:0] a0_q,a1_q;reg [511:0] data_q;reg bad_q;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin mask_q<=0;a0_q<=0;a1_q<=0;data_q<=0;bad_q<=0;o_mask<=0;o_a0<=0;o_a1<=0;o_data<=0;fault<=0;end
  else begin
   mask_q<=in_mask;a0_q<=bases[0];a1_q<=bases[1];data_q<=codes;bad_q<=bad;
   o_mask<=(bad_q||fault)?64'd0:mask_q;o_a0<=a0_q;o_a1<=a1_q;o_data<=data_q;
   fault<=fault||bad_q;
  end
 end
 end else begin : g_pipe
 // ---- P1: lane-local ----
 reg [AW:0] p1_c16[0:63], p1_c1[0:63];
 reg [63:0] p1_s16, p1_sb, p1_pre, p1_mask, p1_first;
 reg [511:0] p1_code;
 integer j, kk; reg [AW:0] t16, t1; reg [AW-1:0] ad, own; reg [8:0] cd; reg seen0, seen1;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   p1_s16<=0;p1_sb<=0;p1_pre<=0;p1_mask<=0;p1_first<=0;p1_code<=0;
   for(j=0;j<64;j=j+1) begin p1_c16[j]<=0; p1_c1[j]<=0; end
  end else begin
   seen0=1'b0; seen1=1'b0;
   for(j=0;j<64;j=j+1) begin
    kk=j%32; ad=in_addr[j*AW+:AW];
    t16={1'b0,ad}-(AW+1)'(kk*16+(MUT_ADDR!=0?1:0)); t1={1'b0,ad}-(AW+1)'(kk+(MUT_ADDR!=0?1:0));
    own=(ad<VBASE)?(ad-AW'(kk*16)):(ad-AW'(kk));
    cd=f32_e4m3(in_data[j*32+:32]);
    p1_c16[j]<=t16; p1_c1[j]<=t1; p1_s16[j]<=(ad<VBASE); p1_sb[j]<=(own<VBASE);
    p1_code[j*8+:8]<=cd[7:0]; p1_pre[j]<=cd[8]||(ad>=2*VBASE); p1_mask[j]<=in_mask[j];
    if(j<32) begin p1_first[j]<=in_mask[j]&&!seen0; seen0=seen0||in_mask[j]; end
    else     begin p1_first[j]<=in_mask[j]&&!seen1; seen1=seen1||in_mask[j]; end
   end
  end
 end
 // ---- P2: group base select + per-lane equality ----
 reg [AW-1:0] bsel[0:1]; reg sbsel[0:1]; reg [AW-1:0] ownv; reg [AW:0] cand; integer m, gg;
 reg [63:0] bad_v; reg [63:0] p2_bad, mask_q; reg [511:0] p2_code; reg [AW-1:0] p2_b0, p2_b1;
 always @(*) begin
  bsel[0]=0;bsel[1]=0;sbsel[0]=0;sbsel[1]=0;bad_v=0;ownv=0;cand=0;gg=0;
  for(m=0;m<64;m=m+1) begin
   gg=m/32; ownv=p1_s16[m]?p1_c16[m][AW-1:0]:p1_c1[m][AW-1:0];
   if(MUT_ADDR!=0) ownv=p1_s16[m]?(p1_c16[m][AW-1:0]+AW'(1)):(p1_c1[m][AW-1:0]+AW'(1));
   bsel[gg]=bsel[gg]|({AW{p1_first[m]}}&ownv); sbsel[gg]=sbsel[gg]|(p1_first[m]&p1_sb[m]);
  end
  for(m=0;m<64;m=m+1) begin
   gg=m/32; cand=sbsel[gg]?p1_c16[m]:p1_c1[m];
   bad_v[m]=p1_mask[m]&&(p1_pre[m]||cand[AW]||cand[AW-1:0]!=bsel[gg]);
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin p2_bad<=0;mask_q<=0;p2_code<=0;p2_b0<=0;p2_b1<=0; end
  else begin p2_bad<=bad_v;mask_q<=p1_mask;p2_code<=p1_code;p2_b0<=bsel[0];p2_b1<=bsel[1]; end
 end
 // ---- out (same names as the original output stage: mask_q is the boundary reference glob) ----
 wire bad_q = |p2_bad;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin o_mask<=0;o_a0<=0;o_a1<=0;o_data<=0;fault<=0;end
  else begin
   o_mask<=(bad_q||fault)?64'd0:mask_q;o_a0<=p2_b0;o_a1<=p2_b1;o_data<=p2_code;
   fault<=fault||bad_q;
  end
 end
 end endgenerate
endmodule
