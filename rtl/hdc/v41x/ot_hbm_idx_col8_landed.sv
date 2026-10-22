`timescale 1ns/1ps
`default_nettype none
// D4/K2 fixed-latency landing, 12-bit local groups, equal-depth reset forests.
module ot_hidx_col8_land #(parameter integer W=12)(input wire cw,cr,rst_n,input wire[W-1:0] d,output wire[W-1:0] q);
 localparam integer C=(W+11)/12;
 wire[C-1:0] rw,rr;
 ot_hidx_rst_tree_f32 #(.REGIONS(C)) u_rw(.clk(cw),.rst_n_in(rst_n),.rst_n(rw));
 ot_hidx_rst_tree_f32 #(.REGIONS(C)) u_rr(.clk(cr),.rst_n_in(rst_n),.rst_n(rr));
 for(genvar c=0;c<C;c=c+1)begin:g_chunk
  localparam integer N=(W-12*c<12)?W-12*c:12;
  wire[4*N-1:0] bank;wire[3:0] valid;
  ot_pl_land_phys_local_w #(.W(N),.D(4),.ID(c)) u_w(.ck(cw),.rsi(rw[c]),.i(d[12*c+:N]),.bank(bank),.vld(valid));
  ot_pl_land_phys_local_r #(.W(N),.D(4),.K(2),.ID(c)) u_r(.ck(cr),.rsi(rr[c]),.bank(bank),.vld(valid),.o(q[12*c+:N]));
 end
endmodule
module ot_hidx_col8_landed(input wire ctl,input wire[3:0] cp,input wire rst_n,
 input wire qv_b,input wire[567:0] q_b,input wire[543:0] key,input wire[63:0] hid,
 output wire[31:0] cs_out,output wire cf_out,output wire[3:0] prdy);
 wire[8:0] reset_leaf;
 ot_hidx_rst_tree_f32 #(.REGIONS(9)) u_reset(.clk(ctl),.rst_n_in(rst_n),.rst_n(reset_leaf));
 wire[1176:0] inp[0:4];wire[31:0] cs[0:4];wire cf[0:4];wire[3:0] pon;
 assign inp[0]={qv_b,q_b,key,hid};assign cs[0]=0;assign cf[0]=0;
 wire[1176:0] in0;
 ot_hidx_col8_land #(.W(1177)) l0(.cw(ctl),.cr(cp[0]),.rst_n(reset_leaf[0]),.d(inp[0]),.q(in0));
 assign inp[1]=in0[1176:0];
 ot_hidx_score_pair8_r0 u_pair0(.clk(cp[0]),.rst_n(reset_leaf[0]),.qv_b(inp[1][1176]),.q_b(inp[1][1175:608]),.key(inp[1][607:64]),.hid(inp[1][0+:16]),.cs_out(cs[1]),.cf_out(cf[1]),.prdy(pon[0]));
 wire[1209:0] in1;
 ot_hidx_col8_land #(.W(1210)) l1(.cw(cp[0]),.cr(cp[1]),.rst_n(reset_leaf[1]),.d({cs[1],cf[1],inp[1]}),.q(in1));
 assign inp[2]=in1[1176:0];
 wire[31:0] s1=in1[1209:1178];wire f1=in1[1177];
 ot_hidx_score_pair8_r1 u_pair1(.clk(cp[1]),.rst_n(reset_leaf[1]),.qv_b(inp[2][1176]),.q_b(inp[2][1175:608]),.key(inp[2][607:64]),.hid(inp[2][16+:16]),.cs_in(s1),.cf_in(f1),.cs_out(cs[2]),.cf_out(cf[2]),.prdy(pon[1]));
 wire[1209:0] in2;
 ot_hidx_col8_land #(.W(1210)) l2(.cw(cp[1]),.cr(cp[2]),.rst_n(reset_leaf[2]),.d({cs[2],cf[2],inp[2]}),.q(in2));
 assign inp[3]=in2[1176:0];
 wire[31:0] s2=in2[1209:1178];wire f2=in2[1177];
 ot_hidx_score_pair8_r2 u_pair2(.clk(cp[2]),.rst_n(reset_leaf[2]),.qv_b(inp[3][1176]),.q_b(inp[3][1175:608]),.key(inp[3][607:64]),.hid(inp[3][32+:16]),.cs_in(s2),.cf_in(f2),.cs_out(cs[3]),.cf_out(cf[3]),.prdy(pon[2]));
 wire[1209:0] in3;
 ot_hidx_col8_land #(.W(1210)) l3(.cw(cp[2]),.cr(cp[3]),.rst_n(reset_leaf[3]),.d({cs[3],cf[3],inp[3]}),.q(in3));
 assign inp[4]=in3[1176:0];
 wire[31:0] s3=in3[1209:1178];wire f3=in3[1177];
 ot_hidx_score_pair8_r3 u_pair3(.clk(cp[3]),.rst_n(reset_leaf[3]),.qv_b(inp[4][1176]),.q_b(inp[4][1175:608]),.key(inp[4][607:64]),.hid(inp[4][48+:16]),.cs_in(s3),.cf_in(f3),.cs_out(cs[4]),.cf_out(cf[4]),.prdy(pon[3]));
 ot_hidx_col8_land #(.W(33)) lret(.cw(cp[3]),.cr(ctl),.rst_n(reset_leaf[4]),.d({cs[4],cf[4]}),.q({cs_out,cf_out}));
 ot_hidx_col8_land #(.W(1)) lrdy0(.cw(cp[0]),.cr(ctl),.rst_n(reset_leaf[5]),.d(pon[0]),.q(prdy[0]));
 ot_hidx_col8_land #(.W(1)) lrdy1(.cw(cp[1]),.cr(ctl),.rst_n(reset_leaf[6]),.d(pon[1]),.q(prdy[1]));
 ot_hidx_col8_land #(.W(1)) lrdy2(.cw(cp[2]),.cr(ctl),.rst_n(reset_leaf[7]),.d(pon[2]),.q(prdy[2]));
 ot_hidx_col8_land #(.W(1)) lrdy3(.cw(cp[3]),.cr(ctl),.rst_n(reset_leaf[8]),.d(pon[3]),.q(prdy[3]));
endmodule
`default_nettype wire
