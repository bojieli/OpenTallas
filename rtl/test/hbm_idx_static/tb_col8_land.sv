`timescale 1ns/1ps
module tb_col8_land;
 reg cw=0,cr=0,rst=0;always #5 cw=~cw;initial begin #2;forever #5 cr=~cr;end
 reg[1209:0] d=0;wire[1209:0]q;reg[1209:0] expected[0:2];integer n=0,checks=0;
 ot_hidx_col8_land #(.W(1210)) dut(.cw(cw),.cr(cr),.rst_n(rst),.d(d),.q(q));
 always@(posedge cw)begin n<=n+1;d<={d[1192:0],d[1209:1193]^17'(n)};expected[0]<=d;expected[1]<=expected[0];expected[2]<=expected[1];end
 always@(negedge cr)if(n>40)begin
 if(q!==expected[2])$fatal(1,"COL8_LAND_FAIL cycle=%0d",n);
 checks=checks+1;if(checks==256)begin $display("COL8_LAND_PASS checks=%0d width=1210 phase=2ns latency=3",checks);$finish;end end
 initial begin repeat(5)@(negedge cw);rst=1;end
endmodule
