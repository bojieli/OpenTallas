`timescale 1ns/1ps
// DefaultOFF additive successor. Pinned legacy and liveR1 sources are untouched.
// Publication/valid/reset eligibility is preserved; parent protection is OPEN.
(* keep_hierarchy = 1 *) module ot_hbm_router_lane_local(
 input wire clk,rst_n,v,first,last,input wire [41:0] x,
 output wire [251:0] q,output reg finished
);
 reg [41:0] x_q;
 reg x_v,x_first,x_last,c_v,c_first,c_last;
 reg [5:0] ge_q,valid_q;
 reg [40:0] payload_q[0:5];
 integer i;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   x_v<=0;x_first<=0;x_last<=0;c_v<=0;c_first<=0;c_last<=0;
   valid_q<=0;finished<=0;
  end else begin
   x_v<=v;x_first<=first;x_last<=last;
   c_v<=x_v;c_first<=x_first;c_last<=x_last;
   finished<=c_v&&c_last;
   if(c_v)for(i=0;i<6;i=i+1)begin
    if(ge_q[i])valid_q[i]<=valid_q[i];
    else if(i==0)valid_q[i]<=1;
    else if(ge_q[i-1])valid_q[i]<=1;
    else valid_q[i]<=!c_first&&valid_q[i-1];
   end
  end
 end
 always @(posedge clk)begin
  if(v)x_q<=x;
  for(i=0;i<6;i=i+1)
   ge_q[i]<=!x_first&&valid_q[i]&&(payload_q[i][9+:32]>=x_q[9+:32]);
  if(c_v)for(i=0;i<6;i=i+1)begin
   if(ge_q[i])payload_q[i]<=payload_q[i];
   else if(i==0)payload_q[i]<=x_q[40:0];
   else if(ge_q[i-1])payload_q[i]<=x_q[40:0];
   else payload_q[i]<=payload_q[i-1];
  end
 end
 genvar g;
 generate for(g=0;g<6;g=g+1)begin:entry
  // Invalid storage cannot influence rank or observable invalid IDs.
  assign q[g*42+:42]=valid_q[g]?{1'b1,payload_q[g]}:42'b0;
 end endgenerate
endmodule

// Real candidates and three independent14bit comparisons are captured before
// payload selection. No new arithmetic/reduction order is introduced.
module ot_hbm_router_pair_cut(input wire clk,input wire [41:0] a,b,
 output reg [41:0] hi,lo);
 reg [41:0] a_q,b_q;
 reg [2:0] gt_q,eq_q;
 wire take_a=gt_q[2]||(eq_q[2]&&gt_q[1])||
             (eq_q[2]&&eq_q[1]&&gt_q[0]);
 genvar c;
 always @(posedge clk)begin a_q<=a;b_q<=b;end
 generate for(c=0;c<3;c=c+1)begin:chunk
  always @(posedge clk)begin
   gt_q[c]<=a[c*14+:14]>b[c*14+:14];
   eq_q[c]<=a[c*14+:14]==b[c*14+:14];
  end
 end endgenerate
 always @(posedge clk)begin
  hi<=take_a?a_q:b_q;lo<=take_a?b_q:a_q;
 end
endmodule

module ot_hbm_router_cs_cut #(parameter integer KB=8,J=4,DESC=1)(
 input wire clk,input wire [335:0] d,output wire [335:0] q);
 genvar i;
 generate for(i=0;i<8;i=i+1)begin:pair
  localparam integer L=i^J;
  localparam integer UP=(((i&KB)==0)?1:0)^(DESC!=0);
  if(L>i)begin:active
   wire [41:0] hi,lo;
   ot_hbm_router_pair_cut cut(.clk(clk),.a(d[i*42+:42]),
    .b(d[L*42+:42]),.hi(hi),.lo(lo));
   assign q[i*42+:42]=UP?lo:hi;
   assign q[L*42+:42]=UP?hi:lo;
  end
 end endgenerate
endmodule

module ot_hbm_router_merge6_cut(input wire clk,input wire [251:0] a,b,
 output wire [251:0] q);
 wire [335:0] aa={84'b0,a},bb={84'b0,b};
 wire [335:0] s0,s1,s2,s3;
 genvar i;
 generate for(i=0;i<8;i=i+1)begin:pick
  if(i<2||i>=6)begin:bypass
   reg [41:0] d0,d1;
   always @(posedge clk)begin
    d0<=i<2?aa[i*42+:42]:bb[(7-i)*42+:42];d1<=d0;
   end
   assign s0[i*42+:42]=d1;
  end else begin:compare
   wire [41:0] unused_lo;
   ot_hbm_router_pair_cut cut(.clk(clk),.a(aa[i*42+:42]),
    .b(bb[(7-i)*42+:42]),.hi(s0[i*42+:42]),.lo(unused_lo));
  end
 end endgenerate
 ot_hbm_router_cs_cut #(.KB(8),.J(4),.DESC(1)) c1(.clk(clk),.d(s0),.q(s1));
 ot_hbm_router_cs_cut #(.KB(8),.J(2),.DESC(1)) c2(.clk(clk),.d(s1),.q(s2));
 ot_hbm_router_cs_cut #(.KB(8),.J(1),.DESC(1)) c3(.clk(clk),.d(s2),.q(s3));
 assign q=s3[0+:252];
endmodule

module ot_hbm_router_topk_successor #(parameter integer ENABLE=0)(
 input wire clk,rst_n,in_valid,in_last,input wire [511:0] in_vals,
 output wire out_valid,output wire [53:0] out_ids
);
 generate if(!ENABLE)begin:g_off
  ot_gpu_router_topk_f #(.N(384),.P(16),.K(6),.IW(9)) original(
   .clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_last(in_last),
   .in_vals(in_vals),.out_valid(out_valid),.out_ids(out_ids));
 end else begin:g_on
  reg [8:0] beat_base;
  reg [1:0] fresh_bank;
  wire bank=beat_base[4];
  wire [251:0] lvl[0:62];
  wire [31:0] lane_done;
  function automatic [31:0] okey(input [31:0] f);
   reg [31:0] c;
   begin c = f == 32'h80000000 ? 32'b0 : f; okey = c[31] ? ~c : (c | 32'h80000000);end
  endfunction
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin beat_base<=0;fresh_bank<=2'b11;end
   else if(in_valid)begin
    beat_base<=in_last?9'b0:beat_base+9'd16;
    if(in_last)fresh_bank<=2'b11;
    else fresh_bank[bank]<=0;
   end
  end
  genvar g;
  for(g=0;g<32;g=g+1)begin:g_lane
   localparam integer B=g/16,J=g%16;
   wire [8:0] id=beat_base+9'(J);
   ot_hbm_router_lane_local u_lane(
    .clk(clk),.rst_n(rst_n),.v(in_valid&&(bank==B)),
    .first(fresh_bank[B]),.last(in_last),
    .x({1'b1,okey(in_vals[J*32+:32]),~id}),
    .q(lvl[31+g]),.finished(lane_done[g]));
  end
  for(g=0;g<31;g=g+1)begin:g_node
   ot_hbm_router_merge6_cut m(.clk(clk),.a(lvl[2*g+1]),.b(lvl[2*g+2]),.q(lvl[g]));
  end
  reg [46:0] vpipe;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)vpipe<=0;else vpipe<={vpipe[45:0],|lane_done};
  wire [79:0] id0,i1,i2,i3,i4,i5,i6;
  for(g=0;g<8;g=g+1)begin:g_id
   if(g<6)assign id0[g*10+:10]={~lvl[0][g*42+41],~lvl[0][g*42+:9]};
   else assign id0[g*10+:10]=10'h3ff;
  end
  ot_gpu_topk_cs #(.W(10),.KB(2),.J(1),.DESC(0)) s1(.clk(clk),.d(id0),.q(i1));
  ot_gpu_topk_cs #(.W(10),.KB(4),.J(2),.DESC(0)) s2(.clk(clk),.d(i1),.q(i2));
  ot_gpu_topk_cs #(.W(10),.KB(4),.J(1),.DESC(0)) s3(.clk(clk),.d(i2),.q(i3));
  ot_gpu_topk_cs #(.W(10),.KB(8),.J(4),.DESC(0)) s4(.clk(clk),.d(i3),.q(i4));
  ot_gpu_topk_cs #(.W(10),.KB(8),.J(2),.DESC(0)) s5(.clk(clk),.d(i4),.q(i5));
  ot_gpu_topk_cs #(.W(10),.KB(8),.J(1),.DESC(0)) s6(.clk(clk),.d(i5),.q(i6));
  assign out_valid=vpipe[45];
  for(g=0;g<6;g=g+1)begin:g_out
   assign out_ids[g*9+:9]=i6[g*10+:9];
  end
 end endgenerate
endmodule
