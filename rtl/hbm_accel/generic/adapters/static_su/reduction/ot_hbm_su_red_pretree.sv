`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SU reducer ingress widening (HH-6 / HBM-SURED 2026-10-18, coordinator 0ix (5); HH-5 re-price: the as-built ingress of
// ONE lane value per edge per quarter costs DS AR -5.71%, MTP -17.58%, Qwen -47.76% > the 5% accepted-cost limit).
// The quarter's 128 lockstep lanes emit one 128-word issue block per edge; the pre-tree turns that block into its
// golden csum8 subtree in a fixed number of edges, and the reducer takes it as ONE external operand (qcore_r5 PRETREE).
// Order (hdc_golden_v41.csum, chunk 8): word w of the block = quarter lane w; chunk c = words 8c..8c+7 summed
// sequentially from +0; chunk sums joined by an aligned pairwise tree (16 chunks -> 1). Words w >= cnt are padding:
// ADD mode feeds +0 (x + +0 = x exactly, zeros canonical, as the golden's +0 padding), MAX mode excludes them.
// MAX mode uses the reducer's ordered compare (canonical +0) and pushes the winner through the same adder with +0
// (exact identity), so one FP32 adder serves both modes and both modes have the same fixed latency.
//   ot_hbm_su_red_pretree_node  one tree node, LAT edges, inputs {v,x} x 2, mode bit carried
//   ot_hbm_su_red_pretree_s     per pgslice G: its 32 lanes = quarter words 16G..16G+15 (half A) and 64+16G..+15
//                               (half B): 4 chunk chains (canonical x0 + 7 nodes, lane k skewed (k-1)*LAT) + 1 node per
//                               half -> two 16-word subtrees, registered at E+1+8*LAT+1 (E+50 at LAT 6)
//   ot_hbm_su_red_pretree_j     in the quarter core: pin register (+1), 3 node levels over the 8 16-word subtrees in word
//                               order (k<4: slice k half A, k>=4: slice k-4 half B), output register -> E+3*LAT+2 more
// tree_cmd {v, max, cntB5, cntA5} (per slice, compiler-computed: cntA = clamp(cnt-16G,0,16), cntB = clamp(cnt-64-16G,0,16)
// for a block of cnt valid words; ONE master for all 16 slices of the die) is sampled at the edge E at which the lanes'
// ro_x hold the block (as red_sel samples one lane).
// No stall, no ready: every edge can start a block.  FAULT (sticky): a counted lane without ro_v, an adder error.
// MUT (bench, must FAIL): 1 chunk order x1<->x2; 2 join pairing (s0+s2),(s1+s3); 3 max bit ignored (always add);
//   4 padding off by one (w <= cnt counted).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_red_pretree_node #(parameter integer LAT=6)(
 input wire clk, rst_n,
 input wire mode_in,                   // 1 = MAX
 input wire va, input wire [31:0] a,
 input wire vb, input wire [31:0] b,
 output wire mode_out, output wire vy, output wire [31:0] y, output wire err
);
 // reducer compare: finite ordered, a wins ties only when it is not negative (canonical result after the +0 add)
 wire agt=(a[31]!=b[31])?!a[31]:(a[31]?(a[30:0]<b[30:0]):(a[30:0]>b[30:0]));
 wire [31:0] mx=(va&&vb)?(agt?a:b):(va?a:b);
 wire [31:0] ia=mode_in?mx:(va?a:32'd0);
 wire [31:0] ib=mode_in?32'd0:(vb?b:32'd0);
 wire v=va||vb;
 wire [1:0] e; wire vo;
 ot_hdc_fp32_add_lat #(.LAT(LAT),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(ia),.b(ib),.y(y),.err(e),.valid_out(vo));
 reg [LAT-1:0] md;
 always @(posedge clk) md<={md[LAT-2:0],mode_in};
 assign mode_out=md[LAT-1]; assign vy=vo; assign err=vo&&(e!=2'd0);
endmodule

module ot_hbm_su_red_pretree_s #(parameter integer LAT=6,MUT=0)(
 input wire clk, rst_n,
 input wire [11:0] tree_cmd,           // {v, max, cntB5, cntA5}
 input wire [1023:0] ro_x, input wire [31:0] ro_v,
 output reg [66:0] tree_o,             // {max, vB, xB, vA, xA}
 output reg fault
);
 // stage 1: capture the block (edge E)
 reg [31:0] x1 [0:31]; reg [31:0] v1; reg m1; reg bad1; integer n;
 always @(posedge clk) begin
  for(n=0;n<32;n=n+1) x1[n]<=ro_x[n*32+:32];
  m1<=(MUT==3)?1'b0:tree_cmd[10];
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin v1<=32'd0; bad1<=1'b0; end
  else begin
   bad1<=1'b0;
   for(n=0;n<32;n=n+1) begin : lv
    reg [4:0] cn; reg on;
    cn=(n<16)?tree_cmd[4:0]:tree_cmd[9:5];
    on=tree_cmd[11]&&(5'(n%16)<cn);
    v1[n]<=(MUT==4)?(tree_cmd[11]&&5'(n%16)<=cn):on;
    if(on&&!ro_v[n]) bad1<=1'b1;
   end
  end
 // chunk chains: chunk c = lanes 8c..8c+7 (c 0,1 half A; 2,3 half B)
 wire [3:0] c_m, c_v; wire [31:0] c_x [0:3]; wire [3:0] c_err;
 for(genvar c=0;c<4;c=c+1) begin:g_chunk
  wire [7:0] m_k, v_k; wire [31:0] x_k [0:7]; wire [7:0] e_k;
  // acc_0 = +0 + x0 = x0 with a canonical zero (exactly the golden's first add)
  wire [31:0] x0=x1[8*c];
  assign m_k[0]=m1; assign v_k[0]=v1[8*c]; assign x_k[0]=(x0[30:0]==31'd0)?32'd0:x0; assign e_k[0]=1'b0;
  for(genvar k=1;k<8;k=k+1) begin:g_k
   localparam integer SRC=(MUT==1&&k==1)?2:(MUT==1&&k==2)?1:k;
   localparam integer D=(k-1)*LAT;             // lane k joins the chain (k-1)*LAT edges after capture
   wire [32:0] dl;
   if(D==0) begin:g_d0 assign dl={v1[8*c+SRC],x1[8*c+SRC]}; end
   else begin:g_dl
    reg [32:0] sh [0:D-1]; integer i;
    always @(posedge clk) begin
     sh[0]<={v1[8*c+SRC],x1[8*c+SRC]};
     for(i=1;i<D;i=i+1) sh[i]<=sh[i-1];
    end
    assign dl=sh[D-1];
   end
   ot_hbm_su_red_pretree_node #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(m_k[k-1]),.va(v_k[k-1]),.a(x_k[k-1]),
    .vb(dl[32]),.b(dl[31:0]),.mode_out(m_k[k]),.vy(v_k[k]),.y(x_k[k]),.err(e_k[k]));
  end
  assign c_m[c]=m_k[7]; assign c_v[c]=v_k[7]; assign c_x[c]=x_k[7]; assign c_err[c]=|e_k;
 end
 // one node per half: (chunk 2h) + (chunk 2h+1)
 wire [1:0] h_m,h_v,h_e; wire [31:0] h_x [0:1];
 for(genvar h=0;h<2;h=h+1) begin:g_half
  ot_hbm_su_red_pretree_node #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(c_m[2*h]),.va(c_v[2*h]),.a(c_x[2*h]),
   .vb(c_v[2*h+1]),.b(c_x[2*h+1]),.mode_out(h_m[h]),.vy(h_v[h]),.y(h_x[h]),.err(h_e[h]));
 end
 always @(posedge clk) tree_o<={h_m[0],h_v[1],h_x[1],h_v[0],h_x[0]};
 always @(posedge clk or negedge rst_n)
  if(!rst_n) fault<=1'b0; else if(bad1||(|c_err)||(|h_e)) fault<=1'b1;
endmodule

module ot_hbm_su_red_pretree_j #(parameter integer LAT=6,MUT=0)(
 input wire clk, rst_n,
 input wire [4*67-1:0] slice_t,
 output reg tree_v, output reg [31:0] tree_x, output reg tree_max,
 output reg fault
);
 reg [4*67-1:0] t_p;                   // pin register beside the reducer
 always @(posedge clk) t_p<=slice_t;
 wire [7:0] l0_v; wire [31:0] l0_x [0:7];
 for(genvar k=0;k<8;k=k+1) begin:g_leaf
  localparam integer S=k%4, H=k/4;
  assign l0_v[k]=t_p[67*S+33*H+32]; assign l0_x[k]=t_p[67*S+33*H+:32];
 end
 wire m0=t_p[66];
 // level 1: (s0+s1),(s2+s3),(s4+s5),(s6+s7); MUT 2 pairs (s0+s2),(s1+s3)
 wire [3:0] l1_m,l1_v,l1_e; wire [31:0] l1_x [0:3];
 for(genvar i=0;i<4;i=i+1) begin:g_l1
  localparam integer A=(MUT==2&&i<2)?i:2*i, B=(MUT==2&&i<2)?i+2:2*i+1;
  ot_hbm_su_red_pretree_node #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(m0),.va(l0_v[A]),.a(l0_x[A]),
   .vb(l0_v[B]),.b(l0_x[B]),.mode_out(l1_m[i]),.vy(l1_v[i]),.y(l1_x[i]),.err(l1_e[i]));
 end
 wire [1:0] l2_m,l2_v,l2_e; wire [31:0] l2_x [0:1];
 for(genvar i=0;i<2;i=i+1) begin:g_l2
  ot_hbm_su_red_pretree_node #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(l1_m[2*i]),.va(l1_v[2*i]),.a(l1_x[2*i]),
   .vb(l1_v[2*i+1]),.b(l1_x[2*i+1]),.mode_out(l2_m[i]),.vy(l2_v[i]),.y(l2_x[i]),.err(l2_e[i]));
 end
 wire l3_m,l3_v,l3_e; wire [31:0] l3_x;
 ot_hbm_su_red_pretree_node #(.LAT(LAT)) u_n3(.clk(clk),.rst_n(rst_n),.mode_in(l2_m[0]),.va(l2_v[0]),.a(l2_x[0]),
  .vb(l2_v[1]),.b(l2_x[1]),.mode_out(l3_m),.vy(l3_v),.y(l3_x),.err(l3_e));
 always @(posedge clk) begin tree_x<=l3_x; tree_max<=l3_m; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin tree_v<=1'b0; fault<=1'b0; end
  else begin tree_v<=l3_v; if((|l1_e)||(|l2_e)||l3_e) fault<=1'b1; end
endmodule
`default_nettype wire
