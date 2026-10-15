`timescale 1ns/1ps
// Three related1:1phase0 clock roots; exact109edge candidate.
// Clock0 clamp+EXP;clock1 alignedG/U/route/tag;clock2 DEN/DIV/MUL/BF16/valid.
// Opt-in structural candidate. Exact frozen Horner/FP32 rounding order, no
// inactive vector-op delay slots. LM5/LA4 have NOT been physically qualified
// in this composition. No ready, queues, credit or data-dependent latency.
module ot_hgi_sfu_fused_glu_split #(
 parameter integer LM=5, LA=4,
 parameter integer MUT_SECOND_MUL=0
)(
 input wire [2:0] clk,input wire rst_n, v,
 input wire [31:0] gate, up, route,
 input wire [31:0] tag,
 output reg vo,
 output reg [31:0] y,
 output wire [31:0] out_tag,
 output wire fault
);
 localparam integer EXP=7*LM+8*LA+4;
 localparam integer DEN=1+EXP+1+LA;
 localparam integer DIV=DEN+21;
 localparam integer MUL1=DIV+LM;
 localparam integer DEPTH=MUL1+LM+1;
 wire [DEPTH:0] vd;
 ot_hdc_vline #(.D(DEPTH)) u_v(clk[2],rst_n,v,vd);
 function automatic [31:0] key(input [31:0] x);
  key=x[31] ? ~x : {1'b1,x[30:0]};
 endfunction
 reg [31:0] g_clamp,u_clip;
 // Same total-order compares as frozen pre_a/c_m, with canonical finite lim.
 always @(posedge clk[0]) begin
  g_clamp <= key(gate)<=key(32'h7f7fffff) ? gate:32'h7f7fffff;
  u_clip <= key(up)>=key(32'hff7fffff) ?
            (key(up)<=key(32'h7f7fffff) ? up:32'h7f7fffff):32'hff7fffff;
 end
 wire [31:0] exp_y,den_y,div_y,mul1_y,mul2_y;
 wire fe,fa,fd,fm1,fm2;
 ot_hdc_v41x_exp #(.LM(LM),.LA(LA)) u_exp(
  .clk(clk[0]),.rst_n(rst_n),.v(vd[1]),.x({~g_clamp[31],g_clamp[30:0]}),
  .y(exp_y),.vo(),.fault(fe));
 reg [31:0] den_r;
 always @(posedge clk[2]) den_r<=exp_y;
 ot_hdc_qadd_lat #(.KEEP(1),.LAT(LA)) u_den(
  clk[2],rst_n,vd[1+EXP+1],den_r,32'h3f800000,den_y,fa);
 wire [31:0] g_div,u_mul,route_mul;
 ot_hdc_delay #(.W(32),.D(DEN-1)) u_gd(clk[1],rst_n,g_clamp,g_div);
 ot_hdc_delay #(.W(32),.D(DIV-1)) u_ud(clk[1],rst_n,u_clip,u_mul);
 ot_hdc_delay #(.W(32),.D(MUL1)) u_rd(clk[1],rst_n,route,route_mul);
 ot_dsrom_fdiv_f12 u_div(.clk(clk[2]),.rst_n(rst_n),.v(vd[DEN]),
  .a(g_div),.b(den_y),.y(div_y),.vo(),.fault(fd));
 ot_hdc_qmul_lat #(.LAT(LM)) u_mul1(clk[2],rst_n,vd[DIV],div_y,u_mul,mul1_y,fm1);
 // Negative control changes the actual second FP32 multiplier operand.
 wire [31:0] route_operand=route_mul ^ (MUT_SECOND_MUL!=0 ? 32'h00800000:32'd0);
 ot_hdc_qmul_lat #(.LAT(LM)) u_mul2(clk[2],rst_n,vd[MUL1],mul1_y,route_operand,mul2_y,fm2);
 wire [31:0] bf=(mul2_y+32'h7fff+{31'd0,mul2_y[16]})&32'hffff0000;
 always @(posedge clk[2] or negedge rst_n)
  if(!rst_n) vo<=1'b0; else vo<=vd[DEPTH-1];
 always @(posedge clk[2]) y<=bf;
 ot_hdc_delay #(.W(32),.D(DEPTH)) u_td(clk[1],rst_n,tag,out_tag);
 assign fault=fe|fa|fd|fm1|fm2;
endmodule
