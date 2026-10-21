`timescale 1ns/1ps
module tbm;
  reg clk=0, rst_n=0, v=0; reg [31:0] a=0,b=0;
  wire [31:0] y0,y1,r0,r1; wire f0,f1,g0,g1,vo0,vo1;
  ot_hdc_qmul_lat #(5) u0(clk,rst_n,v,a,b,y0,f0);
  ot_s81dv_qmul_n32 #(5) u1(clk,rst_n,v,a,b,y1,f1);
  ot_dsrom_rsqrt #(.LM(5),.LA(6)) s0(.clk(clk),.rst_n(rst_n),.v(v),.x(a),.y(r0),.vo(vo0),.fault(g0));
  ot_s81dv_rsqrt_n32 #(.LM(5),.LA(6)) s1(.clk(clk),.rst_n(rst_n),.v(v),.x(a),.y(r1),.vo(vo1),.fault(g1));
  integer i, bad=0, badr=0; reg [31:0] r;
  function [31:0] pick(input [31:0] x, input [3:0] k);
    case(k) 0: pick=32'h0; 1: pick=32'h80000000; 2: pick=32'h7f800000; 3: pick={x[31],8'h00,x[22:0]};
      4: pick={x[31],8'h01,x[22:0]}; 5: pick={x[31],8'hfe,x[22:0]}; 6: pick={x[31],8'h40|x[27:23],x[22:0]};
      7: pick={x[31],8'h3f,x[22:0]}; 8: pick={x[31],8'h0f,x[22:0]};
      default: pick=x; endcase
  endfunction
  always #1 clk=~clk;
  initial begin
    #5 rst_n=1;
    for(i=0;i<2000000;i=i+1) begin
      @(negedge clk);
      v=$random; r=$random; a=pick($random, r[3:0]); b=pick($random, r[7:4]);
      if (r[8]) a[31]=0;
      if (y0!==y1 || f0!==f1) begin bad=bad+1; if (bad<5) $display("MUL MISMATCH %h %h", y0,y1); end
      if (r0!==r1 || g0!==g1 || vo0!==vo1) begin badr=badr+1; if (badr<5) $display("RSQ MISMATCH %h %h", r0,r1); end
    end
    $display("EQ_MUL done bad=%0d badr=%0d", bad, badr); $finish;
  end
endmodule
