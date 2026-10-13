`timescale 1ns/1ps
module tb_compact_delay;
  parameter integer LAT=21;
  reg clk=0;
  always #5 clk=~clk;
  reg [511:0] d=0;
  wire [511:0] q;
  ot_qwen_tree_delay #(.DW(512),.LAT(LAT)) dut(.clk(clk),.d(d),.q(q));
  function automatic [511:0] word(input integer t);
    integer lane;
    begin
      word=0;
      if(t>=0 && t<128 && t%7!=3)
        for(lane=0;lane<16;lane=lane+1)
          word[lane*32+:32]=(32'h9e3779b9*(t+1)) ^ (32'h7f4a7c15*(lane+1));
    end
  endfunction
  integer c,errors=0;
  initial begin
    for(c=0;c<128+LAT;c=c+1) begin
      @(negedge clk);d=word(c);#1;
      if(c>=LAT && q !== word(c-LAT)) errors=errors+1;
      @(posedge clk);#1;
      if(LAT==0) begin
        if(q !== word(c)) errors=errors+1;
      end else if(c>=LAT-1 && q !== word(c-LAT+1)) errors=errors+1;
    end
    if(errors) begin $display("COMPACT_DELAY FAIL LAT=%0d errors=%0d",LAT,errors);$fatal(1);end
    $display("COMPACT_DELAY PASS LAT=%0d",LAT);$finish;
  end
endmodule
