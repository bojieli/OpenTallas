`timescale 1ns/1ps
module phase_ring_check #(parameter integer D=64,MUT=0)(input wire clk,rst_n,input wire[69:0]i,output integer errors);
wire[69:0]o;
ot_s81sl_cap_phase_ring #(.D(D),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.i(i),.o(o));
reg[69:0]history[0:511];integer n,j;reg[69:0]want;
initial begin errors=0;n=0;for(j=0;j<512;j++)history[j]=0;end
always @(posedge clk)begin
 for(j=D-1;j>0;j--)history[j]=history[j-1];
 history[0]=i;if(!dut.rs[0])history[0][1]=0;
 want=history[D-1];n++;
 #1;
 if(!rst_n || !dut.rs[1])begin if(o[1]!==0)begin errors++;$display("RESET_VALID D=%0d n=%0d",D,n);end end
 else if(o[1]!==want[1] || (o[1] && o!==want))begin
  errors++;if(errors<5)$display("RING_MISMATCH D=%0d MUT=%0d n=%0d got=%h want=%h",D,MUT,n,o,want);
 end
 // Reset invalidates every pre-reset pending word; no quiet input interval.
 if(!rst_n)for(j=0;j<512;j++)history[j][1]=0;
end
endmodule
module tb_s81sl_cap_phase_ring #(parameter integer MUT=0);
reg clk=0,rst_n=0;always #5 clk=~clk;integer n=-1;reg[69:0]i=0;wire integer errors[0:6];
genvar l;generate for(l=0;l<7;l++)begin:g
 phase_ring_check #(.D(64*(l+1)),.MUT(MUT)) c(.clk(clk),.rst_n(rst_n),.i(i),.errors(errors[l]));
end endgenerate
always @(negedge clk)begin
 n++;
 rst_n=!(n<4 || (n>=100&&n<106) || (n>=900&&n<911));
 i={6'(n),32'(n*32'h10204081),32'(n*32'h80a04001)};i[1]=(n%7!=0);i[0]=rst_n;
 if(n==2200)begin
  for(integer z=0;z<7;z++)if(errors[z])$fatal(1,"RING_FAIL MUT=%0d D=%0d errors=%0d",MUT,64*(z+1),errors[z]);
  $display("RING_PASS MUT=%0d all7delays continuous_input cold_and_midstream_reset",MUT);$finish;
 end
end
endmodule
