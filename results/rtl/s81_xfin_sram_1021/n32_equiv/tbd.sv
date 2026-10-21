`timescale 1ns/1ps
module tbd;
  reg clk=0, rst_n=0, v=0; reg [31:0] x=0;
  wire [31:0] y0,y1; wire f0,f1,v0,v1;
  ot_dsrom_divc #(.F(5),.K(10)) u0(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y0),.vo(v0),.fault(f0));
  ot_s81dv_divc_n32 #(.F(5),.K(10)) u1(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y1),.vo(v1),.fault(f1));
  integer i, bad=0; reg [31:0] r;
  always #1 clk=~clk;
  initial begin
    #5 rst_n=1; repeat (4) @(negedge clk);
    for(i=0;i<2000000;i=i+1) begin
      @(negedge clk);
      v=$random; r=$random; x=$random;
      case (r[2:0]) 0: x[30:23]=0; 1: x[30:23]=r[10:3]&8'h0f; 2: x[30:23]=8'hff; 3: x[30:0]=0; default: ; endcase
      if (y0!==y1 || f0!==f1 || v0!==v1) begin bad=bad+1; if (bad<5) $display("DIV MISMATCH %h %h", y0,y1); end
    end
    $display("EQ_DIV done bad=%0d", bad); $finish;
  end
endmodule
