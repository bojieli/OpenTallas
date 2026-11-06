`timescale 1ps/1fs
module ot_dp_rgate(input wire clk,d,run,output reg q);
`ifdef MUTANT
 always @(posedge clk) q <= d | run;
`else
 always @(posedge clk) q <= d & run;
`endif
endmodule
module tb;
 reg clk=0;always #416.5 clk=~clk;
 reg [7:0] lane=8'hxx;reg[3:0] taps=0;wire[7:0] q;
 for(genvar i=0;i<8;i=i+1)begin:g
  ot_dp_rgate u(clk,lane[i],taps[i/2],q[i]);
 end
 integer checks=0;
 task reset_window;
  begin
   taps=0;
   for(integer k=0;k<20;k=k+1)begin
    lane=k[0]?8'hxx:8'hff;@(posedge clk);#0.001;
    if(q!==0)$fatal(1,"resetmask failed q=%h",q);
    checks=checks+8;@(negedge clk);
   end
  end
 endtask
 initial begin
  repeat(3)begin
   reset_window();lane=0;taps=15;@(posedge clk);#0.001;
   if(q!==0)$fatal(1,"release with lowlane");
   @(negedge clk);lane=255;#1;if(q!==0)$fatal(1,"gate skipped registered edge");
   @(posedge clk);#0.001;if(q!==255)$fatal(1,"gate not released oneedge later");checks=checks+16;
   @(negedge clk);
  end
  $display("PC_LEAF_MASK_PASS checks=%0d reset_edges=20 release_added_edges=1 data_cycles=0",checks);$finish;
 end
endmodule
