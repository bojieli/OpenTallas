`timescale 1ns/1ps
module tb_copy_reset;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg [55:0]cp=0;reg [2366:0]su_va=0;reg [6143:0]vq=0;
 wire [4506:0]got,exp;
 qfd_su_static_copy_entries dut(.ck_copy(ck),.rst_n(rst_n),.cp(cp),.su_va(su_va),.vq(vq),.va(got[4506:2140]),.xsw(got[2139:3]),.cp_active(got[2]),.cp_done(got[1]),.fault(got[0]));
 qfd_su_static_copy reference(.ck(ck),.rst_n(rst_n),.cp(cp),.su_va(su_va),.vq(vq),.va(exp[4506:2140]),.xsw(exp[2139:3]),.cp_active(exp[2]),.cp_done(exp[1]),.fault(exp[0]));
 integer cycle,j,checks=0;
 initial begin
 for(cycle=0;cycle<700;cycle=cycle+1)begin
 @(negedge ck);#1;
 rst_n=!(cycle<3 || cycle==80 || (cycle>=260&&cycle<264) || cycle==450);
 cp=0;
 if(cycle%97==6)cp={7'd64,24'd8192,24'd8192,1'b1};
 if(cycle%97==9)cp={7'd4,24'd0,24'd0,1'b1}; // overlap fault
 if(cycle%97==92)cp={7'd0,24'd0,24'd0,1'b1}; // bound fault
 for(j=0;j<192;j=j+1)vq[32*j+:32]=$random;
 su_va[48]=cycle%97==15; // genuine conflicting active descriptor
 #1;
 if(cycle>3&&got!==exp)$fatal(1,"FAIL copy asynchronous reset/source mismatch cycle%0d",cycle);
 @(posedge ck);#1;
 if(cycle>3&&got!==exp)$fatal(1,"FAIL copy clock/source mismatch cycle%0d",cycle);
 checks=checks+1;
 end
 $display("PASS copy reset/source checks%0d resetepochs4 overlap/bounds/descriptorfaults",checks);$finish;
 end
endmodule
