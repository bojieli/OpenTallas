`timescale 1ps/1ps
module tb_pad_native;
 reg clk=0;always #416 clk=~clk;
 reg rst_n=0;reg[14:0]dc=0;reg[255:0]dd=0;
 wire[14:0]qc;wire[255:0]qd;
 ot_hnx_fused_pad dut(.clk(clk),.rst_n(rst_n),.k(6'd4),.dc(dc),.dd(dd),.qc(qc),.qd(qd));
 integer cyc=0;reg[14:0]refc[0:7];reg[255:0]refd[0:7];integer hits[0:7];integer seen=0;
 always @(posedge clk)begin
  cyc<=cyc+1;refc[0]<=dc;refd[0]<=dd;for(integer i=1;i<8;i=i+1)begin refc[i]<=refc[i-1];refd[i]<=refd[i-1];end
 end
 always @(negedge clk)if(cyc>70)begin
  if(cyc<99)$display("PADTRACE cycle=%0d in=%h out=%h data=%h wp=%d ra=%d rdc=%h arr11=%h mask=%h ce=%b ok=%b",cyc,dc,qc,qd,dut.wp,dut.ra,dut.rdc,dut.u_c.arr[11],dut.u_c.w_mask_in,dut.u_c.w_ce_in,dut.ok_q);
  if(qc)begin seen=seen+1;for(integer i=0;i<8;i=i+1)if(qc==refc[i]&&qd==refd[i])hits[i]=hits[i]+1;end
 end
 initial begin
 for(integer i=0;i<8;i=i+1)begin hits[i]=0;refc[i]=0;refd[i]=0;end
 repeat(5)@(negedge clk);rst_n=1;repeat(75)@(negedge clk);
 for(integer j=1;j<=4;j=j+1)begin #1;dc=15'(j);dd=256'(j*101);@(negedge clk);#1;dc=0;dd=0;repeat(10)@(negedge clk);end
 repeat(20)@(negedge clk);for(integer i=0;i<8;i=i+1)$display("PADSHIFT index=%0d hits=%0d seen=%0d",i,hits[i],seen);$finish;
 end
endmodule
