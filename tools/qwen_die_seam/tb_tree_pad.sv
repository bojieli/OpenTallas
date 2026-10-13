`timescale 1ns/1ps
// Minimum seam: real station RTL at the actual 512-bit tree width.
// Proves padding preserves complete words and cycle identity, not node arithmetic.
module tb_tree_pad;
  parameter integer PAD=1;
  parameter integer MUT=0;
  reg clk=0, rst_n=0;
  always #5 clk=~clk;
  reg [511:0] source_word=0;
  wire [511:0] chain [0:PAD];
  assign chain[0]=source_word;
  genvar k;
  generate for(k=0;k<PAD;k=k+1) begin:g
    wire [511:0] q;
    ot_qwen_die_station #(.DW(512),.TAP(0),.SPLIT(0)) dut
      (.clk(clk),.rst_n(rst_n),.a_d(chain[k]),.a_r(),.b_d(q),.b_r(1'b1),
       .t_d(),.t_r(1'b1),.c_d(),.c_r(1'b1));
    if(MUT==1 && k==PAD-1) assign chain[k+1]=chain[k];
    else if(MUT==2 && k==PAD-1) assign chain[k+1]=q ^ 512'd1;
    else assign chain[k+1]=q;
  end endgenerate
  function automatic [511:0] word(input integer t);
    integer lane;
    begin
      word=0;
      // Bursts and bubbles; transaction number occurs in every lane.
      if(t>=0 && t<128 && t%7!=3)
        for(lane=0;lane<16;lane=lane+1)
          word[lane*32+:32]=(32'h9e3779b9*(t+1)) ^ (32'h7f4a7c15*(lane+1));
    end
  endfunction
  integer c, errors=0;
  initial begin
    repeat(2) @(negedge clk);
    rst_n=1;
    for(c=0;c<128+PAD;c=c+1) begin
      @(negedge clk);source_word=word(c);#1;
      if(c>=PAD && chain[PAD] !== word(c-PAD)) errors=errors+1;
      @(posedge clk);#1;
      if(c>=PAD-1 && chain[PAD] !== word(c-PAD+1)) errors=errors+1;
    end
    if(errors) begin $display("TREE_PAD FAIL PAD=%0d MUT=%0d errors=%0d",PAD,MUT,errors);$fatal(1);end
    $display("TREE_PAD PASS PAD=%0d MUT=%0d",PAD,MUT);$finish;
  end
endmodule
