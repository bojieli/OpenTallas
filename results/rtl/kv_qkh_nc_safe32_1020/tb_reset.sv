`timescale 1ns/1ps
module tb_reset;
 parameter integer MUT=0;
 reg clk=0,rst=0;always #1 clk=~clk;
 wire [127:0] a,b;
 ot_rst_relay #(.REGIONS(128),.SYNC_STAGES(2),.TREE_STAGES(1)) refdut(.clk(clk),.rst_n_in(rst),.rst_n(a));
 ot_rst_relay_bounded32 #(.REGIONS(128),.MUT(MUT)) dut(.clk(clk),.rst_n_in(rst),.rst_n(b));
 integer errors=0,checks=0,i;
 always @(posedge clk) begin #0.1;checks=checks+1;if($time>4 && a!==b) errors=errors+1;end
 initial begin
  #0.3;rst=1;#0.2;rst=0;
  for(i=0;i<200;i=i+1) begin #5.7;rst=1;#19.3;rst=0;#0.1;if(a!==b)errors=errors+1;end
  #10;
  if(errors==0)$display("BOUNDED_RESET PASS checks=%0d mut=%0d",checks,MUT);
  else begin $display("BOUNDED_RESET FAIL errors=%0d checks=%0d mut=%0d",errors,checks,MUT);$fatal;end
  $finish;
 end
endmodule
