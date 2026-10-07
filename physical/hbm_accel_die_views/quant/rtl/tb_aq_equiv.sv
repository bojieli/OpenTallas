`timescale 1ns/1ps
`ifndef DUTP
`define DUTP .MLAT(5)
`endif
// Exactness of ot_hfd_actquant_m (margin-first port) against the original ot_hdc_actquant and ot_dsrom_actquant_f12:
// identical random input stream (special values mixed in, random fp4, random valid gaps); the three output streams
// (q, e, y, fault on vo) must agree item for item.
module tb_aq_equiv;
 reg clk=0; always #0.5 clk=~clk;
 reg rst_n=0, v=0, fp4=0; reg [1023:0] x=0;
 wire vo0,vo1,vo2,f0,f1,f2; wire [255:0] q0,q1,q2; wire signed [9:0] e0,e1,e2; wire [511:0] y0,y1,y2;
 ot_hdc_actquant a0(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(vo0),.q(q0),.e(e0),.y(y0),.fault(f0));
 ot_dsrom_actquant_f12 #(.MLAT(5)) a1(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(vo1),.q(q1),.e(e1),.y(y1),.fault(f1));
 `DUT #(`DUTP) a2(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(vo2),.q(q2),.e(e2),.y(y2),.fault(f2));
 localparam W = 256+10+512+1;
 reg [W-1:0] Q0[0:200000], Q1[0:200000], Q2[0:200000]; integer n0=0,n1=0,n2=0, i, k, mism=0, cyc;
 always @(posedge clk) begin
  if (vo0) begin Q0[n0] <= {q0,e0,y0,f0}; n0 <= n0+1; end
  if (vo1) begin Q1[n1] <= {q1,e1,y1,f1}; n1 <= n1+1; end
  if (vo2) begin Q2[n2] <= {q2,e2,y2,f2}; n2 <= n2+1; end
 end
 function [31:0] elem(input integer kind);
  reg [31:0] r; begin r = $urandom;
   case (kind % 12)
    0: elem = 32'h0; 1: elem = 32'h80000000; 2: elem = {r[31], 8'd0, r[22:0]};          // zeros, subnormals
    3: elem = {r[31], 8'd1 + r[2:0], r[22:0]};                                            // tiny normals
    4: elem = {r[31], 8'd254 - r[2:0], r[22:0]};                                          // huge
    5: elem = {r[31], 8'd127 + r[3:0] - 8'd8, r[22:0]};                                   // near 1
    6: elem = {r[31], 8'd100 + r[5:0], 23'd0};                                            // powers of two
    7: elem = {r[31], 8'd120 + r[4:0], r[22:20], 20'd0};                                  // few mantissa bits (ties)
    default: elem = {r[31], (r[30:23] == 8'hFF) ? 8'hFE : r[30:23], r[22:0]};
   endcase end
 endfunction
 integer mode;
 initial begin
  repeat (4) @(posedge clk); rst_n = 1;
  for (cyc = 0; cyc < `NB; cyc = cyc + 1) begin
   @(negedge clk);
   v = ($urandom % 8) != 0; fp4 = $urandom % 2; mode = $urandom % 6;
   for (k = 0; k < 32; k = k + 1) begin
    x[32*k +: 32] = elem(mode == 0 ? $urandom : (mode == 1 ? 8 : (mode == 2 ? (k % 12) : (mode == 3 ? $urandom % 6 : $urandom % 4))));
    if (mode == 5) x[32*k + 23 +: 8] = 8'd104 + ($urandom % 14);          // around the FP8 floor 1e-4 (2^-13.3)
   end
   if (($urandom % 2000) == 0) x[32*($urandom%32) +: 32] = {1'b0, 8'hFF, 23'd0};          // a nonfinite: fault
  end
  @(negedge clk); v = 0; repeat (40) @(posedge clk);
  for (i = 0; i < n0; i = i + 1) if (Q0[i] !== Q1[i] || Q0[i] !== Q2[i]) begin mism = mism + 1; if (mism < 5) $display("MISMATCH item %0d", i); end
  $display("AQ_EQUIV blocks=%0d/%0d/%0d mismatches=%0d", n0, n1, n2, mism);
  if (mism || n0 != n1 || n0 != n2 || n0 == 0) $fatal(1, "FAIL"); $finish;
 end
endmodule
