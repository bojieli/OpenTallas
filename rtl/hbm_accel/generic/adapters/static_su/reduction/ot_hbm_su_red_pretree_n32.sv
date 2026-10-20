// Additive native32 source prototype. Original pretree sources unchanged.
`timescale 1ns/1ps
`default_nettype none
module ot_hbm_su_red_pretree_node_n32 #(parameter integer LAT=6)(
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
 ot_hdc_fp32_add_n32 #(.LAT(LAT),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(ia),.b(ib),.y(y),.err(e),.valid_out(vo));
 reg [LAT-1:0] md;
 always @(posedge clk) md<={md[LAT-2:0],mode_in};
 // Same-edge copies of the last mode stage; exact splitter proves D/clock identity.
 (* keep=1 *) reg [14:0] md_cp;
 always @(posedge clk) md_cp<={15{md[LAT-2]}};
 (* keep=1, ot_rst_split=1 *) wire [15:0] mode_family={md_cp,md[LAT-1]};
 assign mode_out=md[LAT-1]; assign vy=vo; assign err=vo&&(e!=2'd0);
endmodule

module ot_hbm_su_red_pretree_j_n32 #(parameter integer LAT=6,MUT=0)(
 input wire clk, rst_n,
 input wire [4*67-1:0] slice_t,
 output reg tree_v, output reg [31:0] tree_x, output reg tree_max,
 output reg fault
);
 reg [4*67-1:0] t_p;                   // pin register beside the reducer
 always @(posedge clk) t_p<=slice_t;
 // Copy only controls whose actual R9 native census exceeds32. Data pins
 // remain the original single capture; no output latency or value changes.
 (* keep=1 *) reg [30:0] mode_cp;
 always @(posedge clk) mode_cp<={31{slice_t[66]}};
 (* keep=1, ot_rst_split=1 *) wire [31:0] mode_family={mode_cp,t_p[66]};
 for(genvar k=0;k<8;k=k+1)begin:g_valid_copy
  localparam integer B=67*(k%4)+33*(k/4)+32;
  (* keep=1 *) reg [6:0] cp;
  always @(posedge clk)cp<={7{slice_t[B]}};
  (* keep=1, ot_rst_split=1 *) wire [7:0] family={cp,t_p[B]};
 end
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
  ot_hbm_su_red_pretree_node_n32 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(m0),.va(l0_v[A]),.a(l0_x[A]),
   .vb(l0_v[B]),.b(l0_x[B]),.mode_out(l1_m[i]),.vy(l1_v[i]),.y(l1_x[i]),.err(l1_e[i]));
 end
 wire [1:0] l2_m,l2_v,l2_e; wire [31:0] l2_x [0:1];
 for(genvar i=0;i<2;i=i+1) begin:g_l2
  ot_hbm_su_red_pretree_node_n32 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(l1_m[2*i]),.va(l1_v[2*i]),.a(l1_x[2*i]),
   .vb(l1_v[2*i+1]),.b(l1_x[2*i+1]),.mode_out(l2_m[i]),.vy(l2_v[i]),.y(l2_x[i]),.err(l2_e[i]));
 end
 wire l3_m,l3_v,l3_e; wire [31:0] l3_x;
 ot_hbm_su_red_pretree_node_n32 #(.LAT(LAT)) u_n3(.clk(clk),.rst_n(rst_n),.mode_in(l2_m[0]),.va(l2_v[0]),.a(l2_x[0]),
  .vb(l2_v[1]),.b(l2_x[1]),.mode_out(l3_m),.vy(l3_v),.y(l3_x),.err(l3_e));
 always @(posedge clk) begin tree_x<=l3_x; tree_max<=l3_m; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin tree_v<=1'b0; fault<=1'b0; end
  else begin tree_v<=l3_v; if((|l1_e)||(|l2_e)||l3_e) fault<=1'b1; end
endmodule
`default_nettype wire
