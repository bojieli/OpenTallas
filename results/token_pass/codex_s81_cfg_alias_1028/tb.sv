`timescale 1ns/1ps
module tb;
reg clk=0;always #0.4165 clk=~clk;
reg [11:0] addr=0;wire[71:0]r0,r1,c0,c1,good,bad;integer mut=0;
ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01_c0_0")) ref0(clk,1'b1,addr,r0);
ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01_c0_1")) ref1(clk,1'b1,addr,r1);
ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01.u_r0.u_c0_0")) actual0(clk,1'b1,addr,c0);
ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01.u_r0.u_c0_1")) actual1(clk,1'b1,addr,good);
ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01.u_r0.u_c0_0")) wrong_identity(clk,1'b1,addr,bad);
assign c1=mut?bad:good;
initial begin
if($value$plusargs("MUT=%d",mut))begin end
for(integer n=0;n<4096;n=n+1)begin
 @(negedge clk);addr=12'(n);@(posedge clk);#0.001;
 if(c0!==r0 || c1!==r1)$fatal(1,"BOUND_CFG_ALIAS_DIFF addr%0d mutant%0d",n,mut);
end
$display("BOUND_CFG_ALIAS_PASS 8192words 72bits 833ps");$finish;
end endmodule
