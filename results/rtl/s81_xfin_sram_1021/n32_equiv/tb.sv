`timescale 1ns/1ps
module tb;
  reg clk=0, rst_n=0, v=0; reg [31:0] a=0,b=0;
  wire [31:0] y0,y1; wire f0,f1;
  ot_dsrom_qadd #(.LAT(6)) u0(clk,rst_n,v,a,b,y0,f0);
  ot_s81dv_qadd_n32 #(.LAT(6)) u1(clk,rst_n,v,a,b,y1,f1);
  integer i, bad=0; reg [31:0] r;
  function [31:0] pick(input [31:0] x, input [3:0] k);
    case(k) 0: pick=32'h0; 1: pick=32'h80000000; 2: pick=32'h7f800000; 3: pick={x[31],8'h00,x[22:0]};
      4: pick={x[31],8'h01,x[22:0]}; 5: pick={x[31],8'hfe,x[22:0]}; 6: pick={x[31],x[30:23]&8'h87,x[22:0]};
      default: pick=x; endcase
  endfunction
  always #1 clk=~clk;
  initial begin
    #5 rst_n=1;
    for(i=0;i<2000000;i=i+1) begin
      @(negedge clk);
      v=$random; r=$random; a=pick($random, r[3:0]); b=pick($random, r[7:4]);
      if (r[8]) b = {~a[31], a[30:0]} ^ ($random & 32'h0000000f);
      if (r[9]) b = {b[31], a[30:23] + (r[12:10]-3), b[22:0]};
      if (y0!==y1 || f0!==f1) begin bad=bad+1; if (bad<5) $display("MISMATCH %h %h f %b %b", y0,y1,f0,f1); end
    end
    $display("EQ_ADD done bad=%0d", bad); $finish;
  end
endmodule
