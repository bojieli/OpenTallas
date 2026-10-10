`timescale 1ns/1ps
module tb_mtp_p2_pin_output #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,iv=0,ready=0;wire ir,ov;reg [593:0] din;wire [593:0] dout;
 integer sent=0,got=0,cycles=0;reg stalled=0;reg [593:0] held;
 function automatic [593:0] value(input integer n);
 integer j;begin for(j=0;j<594;j=j+1)value[j]=((n*37+j*11)>>(j%7))&1;end
 endfunction
 ot_mtp_p2_pin_output #(.MUT(MUT)) dut(clk,rst_n,iv,ir,din,ov,ready,dout);
 always @(negedge clk)begin
 if(rst_n)begin iv=sent<128;din=value(sent);ready=(cycles%11>=5);end
 end
 always @(posedge clk)begin
 cycles=cycles+1;
 if(rst_n)begin
 if(stalled&&(!ov||dout!==held))$fatal(1,"PIN stalled output changed");
 stalled=ov&&!ready;if(stalled)held=dout;
 if(iv&&ir)sent=sent+1;
 if(ov&&ready)begin if(dout!==value(got))$fatal(1,"PIN drop/duplicate/data at %0d",got);got=got+1;end
 if(got==128)begin if(sent!=128)$fatal(1,"PIN counts");$display("PIN PASS sent128 got128 cycles%0d",cycles);$finish;end
 if(cycles>1600)$fatal(1,"PIN no progress");
 end
 end
 initial begin repeat(3)@(negedge clk);rst_n=1;end
endmodule
