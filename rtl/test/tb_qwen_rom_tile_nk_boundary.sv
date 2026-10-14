`timescale 1ns/1ps
// NK wrapper contract bench; real datapath exactness is gated separately by rom_pipe.
module ot_qwen_rom_tile_w12 #(parameter NW=18,GT=6144,SMIN=7,CODE_BANKS=5,KV_VB=131072,KV_NH=2,MEM_EXTRA=1,ACC_LAT=7,FAST_ISSUE=1,KV_PREP=4,MUL_LAT=8,TREE_LAT=7,ROM_PIPE=1,ROM_ARELAY=2,ROM_CAP2=1,ROM_CAPX=2,LRST=3,ARPB=1,MPR=1,HIER=2,HIER_HARD=1,TOREG=1,TIDR=1,LRR=1,XTX=2,ANR=1,BAW=12,KV_SLICE=1,RPH=0, RQR=0,NDH=0,BMUT=0)(
input clk,rst_n,input [15:0] tile_id,input ib_go,input [3*NW+13*24+13-1:0]ib,input [127:0]xl,output [511:0]t_out,output t_vout,input [511:0]n_a,n_b,input n_va,output [511:0]n_y,output n_vy,output fault,input kvw_ce,input[6:0]kvw_addr,input[511:0]kvw_data,kvw_mask);
assign t_out=n_a^n_b; assign t_vout=ib_go; assign n_y=n_a+n_b;assign n_vy=n_va;assign fault=^ib;
initial if(KV_SLICE!=0 || XTX!=2) $fatal(1,"NK parameters KV_SLICE/XTX");
always @(posedge clk) if(kvw_ce || kvw_addr || kvw_data || kvw_mask) $fatal(1,"NK absent KV write contract");
endmodule
module tb_qwen_rom_tile_nk_boundary;
parameter NEG=0;
reg clk=0,rst_n=0,go=0,va=0;always #1 clk=~clk;
reg[378:0]ib=0;reg[511:0]a=0,b=0;wire[511:0]to,ny;wire tv,nv,fault;
reg prev=0;integer i,bad=0,checks=0;
ot_qwen_rom_tile_nk #(.GT(6144),.SMIN(7),.CODE_BANKS(5),.KV_VB(131072),.KV_NH(2),.MEM_EXTRA(1),.ACC_LAT(7),.FAST_ISSUE(1),.KV_PREP(4),.MUL_LAT(8),.TREE_LAT(7),.ROM_PIPE(1),.ROM_ARELAY(2),.ROM_CAP2(1),.ROM_CAPX(2),.LRST(3),.ARPB(1),.MPR(1),.HIER(2),.HIER_HARD(1),.TOREG(1),.TIDR(1),.LRR(1),.XTX(2),.ANR(1))dut(clk,rst_n,16'h42,go,ib,128'd0,to,tv,a,b,va,ny,nv,fault);
initial begin
repeat(3) @(negedge clk);rst_n=1;
for(i=0;i<1000;i=i+1)begin
@(negedge clk);prev=^ib;ib={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};a={$random,$random};b={$random,$random};go=$random;va=$random;#0.01;
if(to!==(a^b)||ny!==(a+b)||tv!==go||nv!==va||fault!==(NEG ? (^ib) : prev))bad=bad+1;
checks=checks+1;
end
if(bad==0)$display("PASS nk_boundary checks=%0d",checks);else $display("FAIL nk_boundary checks=%0d mismatches=%0d",checks,bad);
$finish;
end
endmodule
