`timescale 1ns/1ps
module tb_crom_return3_aliases #(parameter integer MUT=0);
 reg ck=0;always #1 ck=~ck;reg rst_n=0;reg[512:0]a=0;
 wire[512:0]canonical,above,below;
 qfd_crom_return3 u0(.ck(ck),.rst_n(rst_n),.a(a),.b(canonical));
 qfd_crom_return3_above #(.MUT(MUT==1))u1(.ck(ck),.rst_n(rst_n),.a(a),.b(above));
 qfd_crom_return3_below #(.MUT(MUT==2))u2(.ck(ck),.rst_n(rst_n),.a(a),.b(below));
 reg[512:0]h0=0,h1=0,h2=0;integer cycle=0,checks=0,errors=0,k;reg[31:0]seed=32'h1ac2de7f;
 always@(posedge ck)begin
 if(!rst_n)begin h0<=0;h1<=0;h2<=0;end
 else begin h0<=a;h1<=h0;h2<=h1;end
 end
 initial begin
 for(cycle=0;cycle<500;cycle=cycle+1)begin
 @(negedge ck);rst_n=!(cycle<4||(cycle>=200&&cycle<204));
 a=0;
 if(cycle>=8&&!(cycle>=200&&cycle<208))begin
 for(k=0;k<17;k=k+1)begin
 seed=seed^(seed<<13);seed=seed^(seed>>17);seed=seed^(seed<<5);
 if(k<16)a[k*32+:32]=seed;else a[512]=seed[0];
 end end
 @(posedge ck);#0.01;
 if(cycle>=8&&!(cycle>=200&&cycle<208))begin
 checks=checks+1;
 if(canonical!==h2||above!==h2||below!==h2)begin
 errors=errors+1;if(errors<4)$display("E3_MISMATCH cycle=%0d",cycle);
 end end
 end
 $display("CROM_RETURN3_ALIAS checks=%0d errors=%0d",checks,errors);
 if(checks!=484||errors)$fatal(1,"real return alias latency/identity mismatch");
 $finish;
 end
endmodule
