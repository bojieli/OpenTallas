`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst=0;reg [543:0] d=0;
wire [2175:0] bank;wire [11:0] epo;wire [3:0] vld;wire [543:0] a,b;
ot_pl_land_w #(.W(544),.D(4)) ow(ck,rst,d,bank,epo,vld);
ot_pl_land_r #(.W(544),.D(4),.K(2)) orr(ck,rst,bank,epo,vld,a);
ot_s81_rck_rx_in_land #(.W(544)) n(ck,rst,rst,d,b);
integer c,j,checks=0,errors=0;
initial begin
for(c=0;c<10000;c=c+1)begin
 @(negedge ck);rst=(c%701>=7);for(j=0;j<17;j=j+1)d[j*32+:32]=$urandom;
 @(posedge ck);#0.001;
 if(c>10)begin checks=checks+1;if(a!==b)begin errors=errors+1;if(errors<5)$display("mismatch cycle%0d reset%b",c,rst);end end
end
$display("RXB_FACE checks=%0d errors=%0d",checks,errors);
if(errors)$fatal(1,"RXB_FACE FAILED");$finish;
end
endmodule
