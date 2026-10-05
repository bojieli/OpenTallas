`timescale 1ns/1ps
module clock_top;
reg clk=0;
always #5 clk=~clk;
tb_hdc_fsqrt_equiv tb(.clk(clk));
endmodule
