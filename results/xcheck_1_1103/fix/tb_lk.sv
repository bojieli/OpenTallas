`timescale 1ns/1ps
module tb; reg clk=0, rst_n=0; reg [3:0] d=0; wire [3:0] fq, q; wire eq;
 ot_dp_ste #(.W(4)) f (.clk(clk), .rst_n(rst_n), .d(d), .ea(rst_n), .q(fq), .eq(eq));
 ot_dp_lk #(.W(4)) l (.clk(clk), .d(fq), .q(q));
 always #0.4165 clk=~clk; integer i, bad=0;
 initial begin #1 rst_n=1; for (i=0;i<20;i=i+1) begin @(negedge clk) d=i; @(posedge clk) #0.01 ; @(negedge clk) #0.01 if (q!==fq) bad=bad+1; @(posedge clk) #0 if (q!==fq) bad=bad+1; end
  if (bad==0) $display("LK PASS"); else $display("LK FAIL %0d", bad); $finish; end
endmodule
