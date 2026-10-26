`timescale 1ns/1ps
// Datapath abstracted ONLY here; actual four-head miter runs separately.
module ot_hdc_v41x_attn_hgrp_s #(parameter H=16,HG=1,TD=32,NBANK=5,BW=3,PWORDS=2,FPL=4,FML=6,F12=1,PCOLP=1,WPRE=2)(input clk,rst_n,input[7:0]gid,input ld_v,ld_mode,input[BW-1:0]ld_bank,input[7:0]ld_grp,input[1023:0]ld_w,input[HG*64-1:0]ld_wp,input ld_w2v,iv,input[BW-1:0]ibank,input[575:0]ib,output ov,output[HG*32-1:0]oy,output[HG-1:0]oflt);
assign ov=0;assign oy=0;assign oflt=0;
endmodule
module tb;
reg clk=0,rst_n=0,v=0;wire out_v;reg hist0=0,hist1=0;integer i,bad=0,seed=3121;
ot_s81c_attn_hcore dut(.clk(clk),.rst_n(rst_n),.gid(8'd0),.ld_v(1'b0),.ld_mode(1'b0),.ld_bank(3'd0),.ld_grp(8'd0),.ld_w(512'd0),.ld_wp(64'd0),.ld_w2v(1'b0),.iv(1'b0),.ibank(3'd0),.ib(576'd0),.ov(),.oy(),.oflt());
ot_s81c_hcore_load_stage sender(.clk(clk),.rst_n(rst_n),.ld_v(v),.ld_mode(1'b0),.ld_bank(3'd0),.ld_grp(8'd0),.ld_w(1024'd0),.ld_w2v(1'b0),.out_v(out_v),.out_mode(),.out_bank(),.out_grp(),.out_w(),.out_w2v());
reg expected_v,held;
initial begin
for(i=0;i<1000;i=i+1)begin
#5;clk=1;hist1=hist0;hist0=rst_n;expected_v=rst_n&&v;
#1;if(i>2 && dut.rst_core_n!==hist1)bad=bad+1;
if(out_v!==expected_v)bad=bad+1;
held=dut.rst_core_n;
#1;rst_n=($random(seed)&3)!=0;v=$random(seed)&1;
#1;if(i>2&&dut.rst_core_n!==held)bad=bad+1;
#2;clk=0;
end
$display("PRIVATE_RESET cycles=1000 bad=%0d",bad);
if(bad!=0)$fatal(1,"timed reset mechanism mismatch");
$finish;end
endmodule
