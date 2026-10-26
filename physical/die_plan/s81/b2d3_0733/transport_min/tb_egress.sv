`timescale 1ps/1fs
module tb_egress;
  reg clk=0;
  always #416.5 clk=~clk;
  reg rst_n=0;
  reg [275:0] raw=0;
  wire [276:0] got;
  s81_egress_min dut(clk,rst_n,raw,got);
  reg [275:0] history[0:2];
  reg [2:0] epoch=0;
  integer c=0, bad=0, b, n;
  initial begin
    for(n=0;n<10000;n=n+1)begin
      @(negedge clk);
      rst_n=(n%113)>2;
      for(b=0;b<276;b=b+1)raw[b]=$urandom;
      if(n%31==0)begin raw=0;raw[n%276]=1;end
      @(posedge clk);
      history[2]=history[1];history[1]=history[0];history[0]=raw;
      if(!rst_n)epoch=0;else epoch={epoch[1:0],1'b1};
      #1;
      if(n>=3 && got!=={epoch[2],history[2]})bad=bad+1;
    end
    $display("EGRESS edges=10000 mismatches=%0d added_source_cycles=2",bad);
    if(bad==0)$display("TRANSPORT_PASS");else $display("TRANSPORT_FAIL");
    $finish;
  end
endmodule
