`timescale 1ns/1ps
module tb #(parameter integer MUT=0);
reg clk=0;always #1 clk=~clk;
reg rst_n=0,sv=0,md=0;reg[7:0]si=0,sd=0;
reg vr;reg[7:0]ir,d1,d2;reg[9:0]we_ref;
wire[9:0]we;wire[7:0]payload;
ot_s81dv_ecol_byteowner #(.NVL(5),.V0(6)) dut(.clk(clk),.rst_n(rst_n),.s_v(sv),.s_i(si+8'(MUT)),.s_byte(sd),.mode_owned(md),.we(we),.payload(payload));
always @(posedge clk or negedge rst_n)if(!rst_n)begin vr<=0;we_ref<=0;end else begin
vr<=sv;
for(integer i=0;i<10;i=i+1)we_ref[i]<=vr&&md&&(ir==30+i);
end
always @(posedge clk)begin ir<=si;d1<=sd;d2<=d1;end
integer checks=0;
initial begin
repeat(6)@(negedge clk);rst_n=1;
for(integer c=0;c<10000;c=c+1)begin
 @(negedge clk);
 if(c>2)begin
  if(we!==we_ref)$fatal(1,"COLLECTOR_N9_MISMATCH en cyc%0d",c);
  if((|we_ref)&&payload!==d2)$fatal(1,"COLLECTOR_N9_MISMATCH payload cyc%0d",c);
  checks++;
 end
 sv=($urandom%4)!=0;md=($urandom%3)!=0;si=(c%3==0)?8'(30+c%10):8'($urandom);sd=$urandom;
 if(c%997==0)rst_n=0;else if(c%997==4)rst_n=1;
end
$display("COLLECTOR_N9_PASS checks%0d",checks);$finish;
end
endmodule
