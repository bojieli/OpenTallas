`timescale 1ns/1ps
module tb;
parameter integer MUT=0;
reg ck=0;always #5 ck=~ck;
reg [547:0] src=0;
reg [547:0] prod;
reg [16:0] zprod,zold;
wire [547:0] transported;wire [16:0] ztransported;
reg [547:0] landed;reg [16:0] zl;
reg [547:0] gold[0:12];integer age=0,i,j;reg [547:0] x;
function [16:0] flags(input [547:0] a);integer k;begin
 flags[0]=|a[31:19];flags[1]=|a[31:5];
 for(k=1;k<16;k=k+1)flags[k+1]=|a[32*k+:32];end endfunction
wire [16:0] zsend=(MUT==1)?zprod^17'h10000:(MUT==2)?zold:zprod;
ot_kv_z17_transport_private d(.ck(ck),.payload_in(prod),.zero_in(zsend),.payload_out(transported),.zero_out(ztransported));
always @(posedge ck)begin
 prod<=src;zprod<=flags(src);zold<=zprod;
 landed<=transported;zl<=ztransported;
 gold[0]<=src;for(i=1;i<13;i=i+1)gold[i]<=gold[i-1];
 age=age+1;
 #1;
 if(age>=13)begin
 if(landed!==gold[12])$fatal(1,"PAYLOAD_AGE_FAIL age=%0d",age);
 if(zl!==flags(landed))$fatal(1,"COHORT_FAIL age=%0d zero=%h ref=%h",age,zl,flags(landed));
 end
end
initial begin
 for(j=0;j<13;j=j+1)gold[j]=0;
 // Arbitrary startup is deliberately not certified. No valid/reset mask in RTL.
 for(j=0;j<548;j=j+1)begin @(negedge ck);src=548'b1<<j;end
 for(j=0;j<548;j=j+1)begin @(negedge ck);src=0;src[j]=1'bx;end
 for(j=0;j<548;j=j+1)begin @(negedge ck);src=0;src[j]=1'bz;end
 for(j=0;j<64;j=j+1)begin @(negedge ck);src=0;end
 $display("TRANSPORT_PASS edges=%0d exact13captures includes X/Z",age);$finish;
end
endmodule
