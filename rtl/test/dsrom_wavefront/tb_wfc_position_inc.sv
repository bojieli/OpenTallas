`timescale 1ns/1ps
module tb_wfc_position_inc;
 reg [20:0] a=0;reg [30:0] b=0;reg c=0;
 wire [20:0] x;wire [30:0] y;wire z;
 ot_dsrom_wfc_position_inc #(.W(21)) u21(a,x);
 ot_dsrom_wfc_position_inc #(.W(31)) u31(b,y);
 ot_dsrom_wfc_position_inc #(.W(1)) u1(c,z);
 integer i;
 task check;
 begin
  #1;
  if(x!==21'(a+1)||y!==31'(b+1)||z!==1'(c+1))$fatal(1,"parallel position carry mismatch");
 end endtask
 initial begin
  for(i=0;i<32;i=i+1)begin a=21'((64'd1<<i)-1);b=31'((64'd1<<i)-1);c=i%2;check();end
  for(i=0;i<4096;i=i+1)begin a=$random;b=$random;c=i%2;check();end
  $display("POSITION_PREFIX PASS widths1/21/31 4128 vectors incl every carry/wrap boundary");$finish;
 end
endmodule
