`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; reg arst_n=0; integer cycle,bitn,seed=73,errors=0;
reg [514:0] u2_i;
wire [514:0] u2_o, ref_u2_o;
reg [512:0] d2_i;
wire [512:0] d2_o, ref_d2_o;
reg [514:0] u1_i;
wire [514:0] u1_o, ref_u1_o;
reg [512:0] d1_i;
wire [512:0] d1_o, ref_d1_o;
n3_reference u_original(.clk(clk),.arst_n(arst_n),.u2_i(u2_i),.u2_o(ref_u2_o),.d2_i(d2_i),.d2_o(ref_d2_o),.u1_i(u1_i),.u1_o(ref_u1_o),.d1_i(d1_i),.d1_o(ref_d1_o));
ot_s81hd_st_n3_transit u_hd_st_n3_transit(.clk(clk),.arst_n(arst_n),.u2_i(u2_i),.u2_o(u2_o),.d2_i(d2_i),.d2_o(d2_o));
ot_s81hd_st_n3_turn u_hd_st_n3_turn(.clk(clk),.arst_n(arst_n),.u1_i(u1_i),.u1_o(u1_o),.d1_i(d1_i),.d1_o(d1_o));
initial begin
u2_i='0;
d2_i='0;
u1_i='0;
d1_i='0;
repeat(5) @(negedge clk); arst_n=1;
for(cycle=0;cycle<400;cycle=cycle+1)begin @(negedge clk);
for(bitn=0;bitn<=514;bitn=bitn+1)u2_i[bitn]=$urandom();
for(bitn=0;bitn<=512;bitn=bitn+1)d2_i[bitn]=$urandom();
for(bitn=0;bitn<=514;bitn=bitn+1)u1_i[bitn]=$urandom();
for(bitn=0;bitn<=512;bitn=bitn+1)d1_i[bitn]=$urandom();
@(posedge clk); #1; if(cycle>20) begin
if(u2_o!==ref_u2_o)errors=errors+1;
if(d2_o!==ref_d2_o)errors=errors+1;
if(u1_o!==ref_u1_o)errors=errors+1;
if(d1_o!==ref_d1_o)errors=errors+1;
end end if(errors)$fatal(1,"N3_SPLIT_FAIL errors=%0d",errors);$display("N3_SPLIT_PASS cycles=400 four_fullwidth_paths=4");$finish;end endmodule