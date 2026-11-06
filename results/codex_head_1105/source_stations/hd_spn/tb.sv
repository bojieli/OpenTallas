`timescale 1ns/1ps
module tb; localparam integer MODE=`MODE; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc=0,last_fall=0,errors=0,checks=0,conservative=0;
reg [564:0] xw_o_d=0;
wire rst_n_t37=rst_n;
reg [564:0] xe_o_d=0;
wire rst_n_t36=rst_n;
reg [564:0] bw_i_q=0;
reg bw_i_eq=0;
reg [564:0] be_i_q=0;
reg be_i_eq=0;
reg [564:0] x_o_d=0;
wire rst_n_t52=rst_n;
reg [564:0] b_i_q=0;
reg b_i_eq=0;
wire[564:0] ste_q,st_q;wire ste_e,st_e;reg free_epoch=0;ot_dp_ste #(.W(565)) boundary_ref(.clk(clk),.rst_n(rst_n),.d(xw_o_d),.ea(free_epoch),.q(ste_q),.eq(ste_e));ot_dp_st #(.W(565)) boundary_new(.clk(clk),.rst_n(rst_n),.d(xw_o_d),.ea(free_epoch),.q(st_q),.eq(st_e));
reg [564:0] h_xw_o[0:0]; reg [0:0] he_xw_o=0; integer tog_xw_o=0; reg[564:0] prev_xw_o=0; integer j_xw_o; initial for(j_xw_o=0;j_xw_o<1;j_xw_o=j_xw_o+1) h_xw_o[j_xw_o]=0;
wire[564:0] xw_o_is0_q; wire xw_o_is0_eq;
ot_dp_st #(.W(565)) u_ist_xw_o_0 (.clk(clk), .rst_n(rst_n), .d(xw_o_d), .ea(rst_n_t37), .q(xw_o_is0_q), .eq(xw_o_is0_eq));
always @(posedge clk) begin h_xw_o[0]<=xw_o_d; he_xw_o[0]<=rst_n_t37; for(j_xw_o=1;j_xw_o<1;j_xw_o=j_xw_o+1) begin h_xw_o[j_xw_o]<=h_xw_o[j_xw_o-1];he_xw_o[j_xw_o]<=he_xw_o[j_xw_o-1]; end end
reg [564:0] h_xe_o[0:1]; reg [1:0] he_xe_o=0; integer tog_xe_o=0; reg[564:0] prev_xe_o=0; integer j_xe_o; initial for(j_xe_o=0;j_xe_o<2;j_xe_o=j_xe_o+1) h_xe_o[j_xe_o]=0;
wire[564:0] xe_o_is0_q; wire xe_o_is0_eq;
ot_dp_st #(.W(565)) u_ist_xe_o_0 (.clk(clk), .rst_n(rst_n), .d(xe_o_d), .ea(rst_n_t36), .q(xe_o_is0_q), .eq(xe_o_is0_eq));
wire[564:0] xe_o_is1_q; wire xe_o_is1_eq;
ot_dp_st #(.W(565)) u_ist_xe_o_1 (.clk(clk), .rst_n(rst_n), .d(xe_o_is0_q), .ea(xe_o_is0_eq), .q(xe_o_is1_q), .eq(xe_o_is1_eq));
always @(posedge clk) begin h_xe_o[0]<=xe_o_d; he_xe_o[0]<=rst_n_t36; for(j_xe_o=1;j_xe_o<2;j_xe_o=j_xe_o+1) begin h_xe_o[j_xe_o]<=h_xe_o[j_xe_o-1];he_xe_o[j_xe_o]<=he_xe_o[j_xe_o-1]; end end
reg [564:0] h_bw_i[0:4]; reg [4:0] he_bw_i=0; integer tog_bw_i=0; reg[564:0] prev_bw_i=0; integer j_bw_i; initial for(j_bw_i=0;j_bw_i<5;j_bw_i=j_bw_i+1) h_bw_i[j_bw_i]=0;
wire[564:0] bw_i_is0_q; wire bw_i_is0_eq;
ot_dp_st #(.W(565)) u_ist_bw_i_0 (.clk(clk), .rst_n(rst_n), .d(bw_i_q), .ea(bw_i_eq), .q(bw_i_is0_q), .eq(bw_i_is0_eq));
wire[564:0] bw_i_is1_q; wire bw_i_is1_eq;
ot_dp_st #(.W(565)) u_ist_bw_i_1 (.clk(clk), .rst_n(rst_n), .d(bw_i_is0_q), .ea(bw_i_is0_eq), .q(bw_i_is1_q), .eq(bw_i_is1_eq));
wire[564:0] bw_i_is2_q; wire bw_i_is2_eq;
ot_dp_st #(.W(565)) u_ist_bw_i_2 (.clk(clk), .rst_n(rst_n), .d(bw_i_is1_q), .ea(bw_i_is1_eq), .q(bw_i_is2_q), .eq(bw_i_is2_eq));
wire[564:0] bw_i_is3_q; wire bw_i_is3_eq;
ot_dp_st #(.W(565)) u_ist_bw_i_3 (.clk(clk), .rst_n(rst_n), .d(bw_i_is2_q), .ea(bw_i_is2_eq), .q(bw_i_is3_q), .eq(bw_i_is3_eq));
wire[564:0] bw_i_is4_q; wire bw_i_is4_eq;
ot_dp_st #(.W(565)) u_ist_bw_i_4 (.clk(clk), .rst_n(rst_n), .d(bw_i_is3_q), .ea(bw_i_is3_eq), .q(bw_i_is4_q), .eq(bw_i_is4_eq));
always @(posedge clk) begin h_bw_i[0]<=bw_i_q; he_bw_i[0]<=bw_i_eq; for(j_bw_i=1;j_bw_i<5;j_bw_i=j_bw_i+1) begin h_bw_i[j_bw_i]<=h_bw_i[j_bw_i-1];he_bw_i[j_bw_i]<=he_bw_i[j_bw_i-1]; end end
reg [564:0] h_be_i[0:3]; reg [3:0] he_be_i=0; integer tog_be_i=0; reg[564:0] prev_be_i=0; integer j_be_i; initial for(j_be_i=0;j_be_i<4;j_be_i=j_be_i+1) h_be_i[j_be_i]=0;
wire[564:0] be_i_is0_q; wire be_i_is0_eq;
ot_dp_st #(.W(565)) u_ist_be_i_0 (.clk(clk), .rst_n(rst_n), .d(be_i_q), .ea(be_i_eq), .q(be_i_is0_q), .eq(be_i_is0_eq));
wire[564:0] be_i_is1_q; wire be_i_is1_eq;
ot_dp_st #(.W(565)) u_ist_be_i_1 (.clk(clk), .rst_n(rst_n), .d(be_i_is0_q), .ea(be_i_is0_eq), .q(be_i_is1_q), .eq(be_i_is1_eq));
wire[564:0] be_i_is2_q; wire be_i_is2_eq;
ot_dp_st #(.W(565)) u_ist_be_i_2 (.clk(clk), .rst_n(rst_n), .d(be_i_is1_q), .ea(be_i_is1_eq), .q(be_i_is2_q), .eq(be_i_is2_eq));
wire[564:0] be_i_is3_q; wire be_i_is3_eq;
ot_dp_st #(.W(565)) u_ist_be_i_3 (.clk(clk), .rst_n(rst_n), .d(be_i_is2_q), .ea(be_i_is2_eq), .q(be_i_is3_q), .eq(be_i_is3_eq));
always @(posedge clk) begin h_be_i[0]<=be_i_q; he_be_i[0]<=be_i_eq; for(j_be_i=1;j_be_i<4;j_be_i=j_be_i+1) begin h_be_i[j_be_i]<=h_be_i[j_be_i-1];he_be_i[j_be_i]<=he_be_i[j_be_i-1]; end end
reg [564:0] h_x_o[0:5]; reg [5:0] he_x_o=0; integer tog_x_o=0; reg[564:0] prev_x_o=0; integer j_x_o; initial for(j_x_o=0;j_x_o<6;j_x_o=j_x_o+1) h_x_o[j_x_o]=0;
wire[564:0] x_o_is0_q; wire x_o_is0_eq;
ot_dp_st #(.W(565)) u_ist_x_o_0 (.clk(clk), .rst_n(rst_n), .d(x_o_d), .ea(rst_n_t52), .q(x_o_is0_q), .eq(x_o_is0_eq));
wire[564:0] x_o_is1_q; wire x_o_is1_eq;
ot_dp_st #(.W(565)) u_ist_x_o_1 (.clk(clk), .rst_n(rst_n), .d(x_o_is0_q), .ea(x_o_is0_eq), .q(x_o_is1_q), .eq(x_o_is1_eq));
wire[564:0] x_o_is2_q; wire x_o_is2_eq;
ot_dp_st #(.W(565)) u_ist_x_o_2 (.clk(clk), .rst_n(rst_n), .d(x_o_is1_q), .ea(x_o_is1_eq), .q(x_o_is2_q), .eq(x_o_is2_eq));
wire[564:0] x_o_is3_q; wire x_o_is3_eq;
ot_dp_st #(.W(565)) u_ist_x_o_3 (.clk(clk), .rst_n(rst_n), .d(x_o_is2_q), .ea(x_o_is2_eq), .q(x_o_is3_q), .eq(x_o_is3_eq));
wire[564:0] x_o_is4_q; wire x_o_is4_eq;
ot_dp_st #(.W(565)) u_ist_x_o_4 (.clk(clk), .rst_n(rst_n), .d(x_o_is3_q), .ea(x_o_is3_eq), .q(x_o_is4_q), .eq(x_o_is4_eq));
wire[564:0] x_o_is5_q; wire x_o_is5_eq;
ot_dp_st #(.W(565)) u_ist_x_o_5 (.clk(clk), .rst_n(rst_n), .d(MODE==2 ? x_o_is3_q : x_o_is4_q), .ea(x_o_is4_eq), .q(x_o_is5_q), .eq(x_o_is5_eq));
always @(posedge clk) begin h_x_o[0]<=x_o_d; he_x_o[0]<=rst_n_t52; for(j_x_o=1;j_x_o<6;j_x_o=j_x_o+1) begin h_x_o[j_x_o]<=h_x_o[j_x_o-1];he_x_o[j_x_o]<=he_x_o[j_x_o-1]; end end
reg [564:0] h_b_i[0:5]; reg [5:0] he_b_i=0; integer tog_b_i=0; reg[564:0] prev_b_i=0; integer j_b_i; initial for(j_b_i=0;j_b_i<6;j_b_i=j_b_i+1) h_b_i[j_b_i]=0;
wire[564:0] b_i_is0_q; wire b_i_is0_eq;
ot_dp_st #(.W(565)) u_ist_b_i_0 (.clk(clk), .rst_n(rst_n), .d(MODE==3 ? bw_i_q : b_i_q), .ea(b_i_eq), .q(b_i_is0_q), .eq(b_i_is0_eq));
wire[564:0] b_i_is1_q; wire b_i_is1_eq;
ot_dp_st #(.W(565)) u_ist_b_i_1 (.clk(clk), .rst_n(rst_n), .d(b_i_is0_q), .ea(b_i_is0_eq), .q(b_i_is1_q), .eq(b_i_is1_eq));
wire[564:0] b_i_is2_q; wire b_i_is2_eq;
ot_dp_st #(.W(565)) u_ist_b_i_2 (.clk(clk), .rst_n(rst_n), .d(b_i_is1_q), .ea(b_i_is1_eq), .q(b_i_is2_q), .eq(b_i_is2_eq));
wire[564:0] b_i_is3_q; wire b_i_is3_eq;
ot_dp_st #(.W(565)) u_ist_b_i_3 (.clk(clk), .rst_n(rst_n), .d(b_i_is2_q), .ea(b_i_is2_eq), .q(b_i_is3_q), .eq(b_i_is3_eq));
wire[564:0] b_i_is4_q; wire b_i_is4_eq;
ot_dp_st #(.W(565)) u_ist_b_i_4 (.clk(clk), .rst_n(rst_n), .d(b_i_is3_q), .ea(b_i_is3_eq), .q(b_i_is4_q), .eq(b_i_is4_eq));
wire[564:0] b_i_is5_q; wire b_i_is5_eq;
ot_dp_st #(.W(565)) u_ist_b_i_5 (.clk(clk), .rst_n(rst_n), .d(MODE==1 ? b_i_is3_q : b_i_is4_q), .ea(b_i_is4_eq), .q(b_i_is5_q), .eq(b_i_is5_eq));
always @(posedge clk) begin h_b_i[0]<=b_i_q; he_b_i[0]<=b_i_eq; for(j_b_i=1;j_b_i<6;j_b_i=j_b_i+1) begin h_b_i[j_b_i]<=h_b_i[j_b_i-1];he_b_i[j_b_i]<=he_b_i[j_b_i-1]; end end
always @(negedge clk) begin cyc=cyc+1;
if(cyc>10) begin
checks=checks+2;if(st_q!==ste_q)errors=errors+1;if(st_e!==ste_e)errors=errors+1;
checks=checks+1;if(xw_o_is0_q!==h_xw_o[0]) errors=errors+1;
checks=checks+1;if(xw_o_is0_eq!==he_xw_o[0]) begin if(!xw_o_is0_eq&&he_xw_o[0]&&cyc-last_fall<=2) conservative=conservative+1;else errors=errors+1;end
if(xw_o_d!==prev_xw_o)tog_xw_o=tog_xw_o+1;prev_xw_o=xw_o_d;
checks=checks+1;if(xe_o_is1_q!==h_xe_o[1]) errors=errors+1;
checks=checks+1;if(xe_o_is1_eq!==he_xe_o[1]) begin if(!xe_o_is1_eq&&he_xe_o[1]&&cyc-last_fall<=3) conservative=conservative+1;else errors=errors+1;end
if(xe_o_d!==prev_xe_o)tog_xe_o=tog_xe_o+1;prev_xe_o=xe_o_d;
checks=checks+1;if(bw_i_is4_q!==h_bw_i[4]) errors=errors+1;
checks=checks+1;if(bw_i_is4_eq!==he_bw_i[4]) begin if(!bw_i_is4_eq&&he_bw_i[4]&&cyc-last_fall<=6) conservative=conservative+1;else errors=errors+1;end
if(bw_i_q!==prev_bw_i)tog_bw_i=tog_bw_i+1;prev_bw_i=bw_i_q;
checks=checks+1;if(be_i_is3_q!==h_be_i[3]) errors=errors+1;
checks=checks+1;if(be_i_is3_eq!==he_be_i[3]) begin if(!be_i_is3_eq&&he_be_i[3]&&cyc-last_fall<=5) conservative=conservative+1;else errors=errors+1;end
if(be_i_q!==prev_be_i)tog_be_i=tog_be_i+1;prev_be_i=be_i_q;
checks=checks+1;if(x_o_is5_q!==h_x_o[5]) errors=errors+1;
checks=checks+1;if(x_o_is5_eq!==he_x_o[5]) begin if(!x_o_is5_eq&&he_x_o[5]&&cyc-last_fall<=7) conservative=conservative+1;else errors=errors+1;end
if(x_o_d!==prev_x_o)tog_x_o=tog_x_o+1;prev_x_o=x_o_d;
checks=checks+1;if(b_i_is5_q!==h_b_i[5]) errors=errors+1;
checks=checks+1;if(b_i_is5_eq!==he_b_i[5]) begin if(!b_i_is5_eq&&he_b_i[5]&&cyc-last_fall<=7) conservative=conservative+1;else errors=errors+1;end
if(b_i_q!==prev_b_i)tog_b_i=tog_b_i+1;prev_b_i=b_i_q;
end
rst_n=(cyc%127>=7);if(cyc%127==0)last_fall=cyc;free_epoch<=rst_n & $urandom;
xw_o_d<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
xe_o_d<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
bw_i_q<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
bw_i_eq<=rst_n & $urandom;
be_i_q<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
be_i_eq<=rst_n & $urandom;
x_o_d<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
b_i_q<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
b_i_eq<=rst_n & $urandom;
if(cyc==1024)begin
if(tog_xw_o<900)$fatal(1,"vacuous payload xw_o");
if(tog_xe_o<900)$fatal(1,"vacuous payload xe_o");
if(tog_bw_i<900)$fatal(1,"vacuous payload bw_i");
if(tog_be_i<900)$fatal(1,"vacuous payload be_i");
if(tog_x_o<900)$fatal(1,"vacuous payload x_o");
if(tog_b_i<900)$fatal(1,"vacuous payload b_i");
$display("STATION_CHAIN checks=%0d errors=%0d mode=%0d conservative=%0d",checks,errors,MODE,conservative);if((MODE==0&&errors)||(MODE!=0&&!errors))$fatal(1,"incorrect exact/control verdict");$finish;end end endmodule
