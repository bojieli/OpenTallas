`timescale 1ns/1ps
module tb_rawleaf_activity;
reg clk=0,rst_n=0,v_d=0,first_d=0;reg[3:0]split_d=0;reg[255:0]w_d=0;reg[127:0]x_d=0;
wire[63:0]t_out;wire[49:0]fault_q;
always #0.41665 clk=~clk;
ot_qwen_tile_lsl_rawfault_m3 dut(.*);
integer c,j,valids=0,nonzero=0;
initial begin $dumpfile("rawleaf.vcd");$dumpvars(0,tb_rawleaf_activity);end
initial begin
repeat(4)@(posedge clk);#0.01;rst_n=1;
for(c=0;c<2048;c=c+1)begin
 @(negedge clk);v_d=(c%8<2);first_d=(c%16<8);split_d=c%3;if(v_d)valids=valids+1;
 for(j=0;j<8;j=j+1)w_d[j*32+:32]=(c%13<4)?32'h7f800000:(c%13<7)?32'h7fc00000:$random;
 for(j=0;j<4;j=j+1)x_d[j*32+:32]=(c%17<6)?32'h7f800000:$random;
 @(posedge clk);#0.01;if(c>80 && |t_out)nonzero=nonzero+1;
end
v_d=0;repeat(80)@(posedge clk);
$display("RAWLEAF_ACTIVITY cycles=%0d valid_inputs=%0d nonzero_output_cycles=%0d",c,valids,nonzero);$finish;
end
endmodule
