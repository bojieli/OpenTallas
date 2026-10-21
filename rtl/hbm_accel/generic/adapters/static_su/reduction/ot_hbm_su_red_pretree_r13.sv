// r13 (HBM-QCORE9 2026-10-20): copy of r11 with module suffix _r13 and FP adders = Codex FP6 ot_hdc_fp32_add_n32 (same LAT/DRST, bit-exact).
// HBM-QCORE8 2026-10-20 r11: qcore pre-tree join for native <= 32 loads. Same function / edges as ot_hbm_su_red_pretree_j.
// r10 census: kept byte modules alone do not cut a net's loads (the census counts through hierarchy), so here every node
// gets its mode / valid as 4 per-byte kept DRIVER copies (pin copies at level 1, kept last-stage copies at levels 2/3),
// and each byte module has its own comparator.  vy copies are kept LAT-stage reset pipes of the node's valid_in = exactly
// the adder's valid_out (ot_hdc_fp32_add_lat: valid_in delayed LAT edges, reset 0).  FP adders: ot_hdc_fp32_add_lat.
`timescale 1ns/1ps
`default_nettype none
(* keep_hierarchy *)
module ot_hbm_su_red_pt_sel8_r13 #(parameter integer K=0)(input wire mode, va, vb, input wire [31:0] a, b, output wire [7:0] ia, ib);
 wire agt=(a[31]!=b[31])?!a[31]:(a[31]?(a[30:0]<b[30:0]):(a[30:0]>b[30:0]));
 wire [7:0] a8=a[K*8+:8], b8=b[K*8+:8];
 wire [7:0] mx=(va&&vb)?(agt?a8:b8):(va?a8:b8);
 assign ia=mode?mx:(va?a8:8'd0);
 assign ib=mode?8'd0:(vb?b8:8'd0);
endmodule

(* keep_hierarchy *)
module ot_hbm_su_red_pt_kq_r13 #(parameter integer N=1,RST=0)(input wire clk, rst_n, input wire d, (* keep = 1 *) output wire q);
 reg [N-1:0] p;
 if(RST!=0)begin:g_r always @(posedge clk or negedge rst_n) if(!rst_n) p<={N{1'b0}}; else p<={p[N-2+(N==1):0],d}; end
 else begin:g_n always @(posedge clk) p<={p[N-2+(N==1):0],d}; end
 assign q=p[N-1];
endmodule

module ot_hbm_su_red_pretree_node_r13 #(parameter integer LAT=6)(
 input wire clk, rst_n,
 input wire [3:0] mode_in,             // per-byte copies, 1 = MAX
 input wire [3:0] va, input wire [31:0] a,
 input wire [3:0] vb, input wire [31:0] b,
 output wire [3:0] mode_out, output wire [3:0] vy, output wire [31:0] y, output wire err
);
 wire [31:0] ia, ib;
 for(genvar k=0;k<4;k=k+1)begin:g_sel
  ot_hbm_su_red_pt_sel8_r13 #(.K(k)) u_s(.mode(mode_in[k]),.va(va[k]),.vb(vb[k]),.a(a),.b(b),.ia(ia[k*8+:8]),.ib(ib[k*8+:8]));
 end
 wire v=va[0]||vb[0];
 wire [1:0] e; wire vo;
 ot_hdc_fp32_add_n32 #(.LAT(LAT),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(ia),.b(ib),.y(y),.err(e),.valid_out(vo));
 // mode: shared LAT-1 stages, last stage in 4 kept copies; valid: 4 kept LAT-stage reset pipes (== the adder's valid_out)
 reg [LAT-2:0] md;
 always @(posedge clk) md<={md[LAT-3:0],mode_in[0]};
 for(genvar k=0;k<4;k=k+1)begin:g_cp
  ot_hbm_su_red_pt_kq_r13 #(.N(1),.RST(0)) u_m(.clk(clk),.rst_n(rst_n),.d(md[LAT-2]),.q(mode_out[k]));
  ot_hbm_su_red_pt_kq_r13 #(.N(LAT),.RST(1)) u_v(.clk(clk),.rst_n(rst_n),.d(v),.q(vy[k]));
 end
 assign err=vo&&(e!=2'd0);
endmodule

module ot_hbm_su_red_pretree_j_r13 #(parameter integer LAT=6,MUT=0)(
 input wire clk, rst_n,
 input wire [4*67-1:0] slice_t,
 output reg tree_v, output reg [31:0] tree_x, output reg tree_max,
 output reg fault
);
 reg [4*67-1:0] t_p;                   // pin register beside the reducer (data; mode / valid as kept copies below)
 always @(posedge clk) t_p<=slice_t;
 wire [31:0] l0_x [0:7];
 for(genvar k=0;k<8;k=k+1) begin:g_leaf
  localparam integer S=k%4, H=k/4;
  assign l0_x[k]=t_p[67*S+33*H+:32];
 end
 wire [3:0] l1_m [0:3]; wire [3:0] l1_v [0:3]; wire [3:0] l1_e; wire [31:0] l1_x [0:3];
 for(genvar i=0;i<4;i=i+1) begin:g_l1
  localparam integer A=(MUT==2&&i<2)?i:2*i, B=(MUT==2&&i<2)?i+2:2*i+1;
  localparam integer BA=67*(A%4)+33*(A/4)+32, BB=67*(B%4)+33*(B/4)+32;
  wire [3:0] m_c, va_c, vb_c;
  for(genvar k=0;k<4;k=k+1)begin:g_pc        // pin copies of the mode / leaf valid bits (same edge as t_p)
   ot_hbm_su_red_pt_kq_r13 #(.N(1),.RST(0)) u_m(.clk(clk),.rst_n(rst_n),.d(slice_t[66]),.q(m_c[k]));
   ot_hbm_su_red_pt_kq_r13 #(.N(1),.RST(0)) u_a(.clk(clk),.rst_n(rst_n),.d(slice_t[BA]),.q(va_c[k]));
   ot_hbm_su_red_pt_kq_r13 #(.N(1),.RST(0)) u_b(.clk(clk),.rst_n(rst_n),.d(slice_t[BB]),.q(vb_c[k]));
  end
  ot_hbm_su_red_pretree_node_r13 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(m_c),.va(va_c),.a(l0_x[A]),
   .vb(vb_c),.b(l0_x[B]),.mode_out(l1_m[i]),.vy(l1_v[i]),.y(l1_x[i]),.err(l1_e[i]));
 end
 wire [3:0] l2_m [0:1]; wire [3:0] l2_v [0:1]; wire [1:0] l2_e; wire [31:0] l2_x [0:1];
 for(genvar i=0;i<2;i=i+1) begin:g_l2
  ot_hbm_su_red_pretree_node_r13 #(.LAT(LAT)) u_n(.clk(clk),.rst_n(rst_n),.mode_in(l1_m[2*i]),.va(l1_v[2*i]),.a(l1_x[2*i]),
   .vb(l1_v[2*i+1]),.b(l1_x[2*i+1]),.mode_out(l2_m[i]),.vy(l2_v[i]),.y(l2_x[i]),.err(l2_e[i]));
 end
 wire [3:0] l3_m, l3_v; wire l3_e; wire [31:0] l3_x;
 ot_hbm_su_red_pretree_node_r13 #(.LAT(LAT)) u_n3(.clk(clk),.rst_n(rst_n),.mode_in(l2_m[0]),.va(l2_v[0]),.a(l2_x[0]),
  .vb(l2_v[1]),.b(l2_x[1]),.mode_out(l3_m),.vy(l3_v),.y(l3_x),.err(l3_e));
 always @(posedge clk) begin tree_x<=l3_x; tree_max<=l3_m[0]; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin tree_v<=1'b0; fault<=1'b0; end
  else begin tree_v<=l3_v[0]; if((|l1_e)||(|l2_e)||l3_e) fault<=1'b1; end
endmodule
`default_nettype wire
