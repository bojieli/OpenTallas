`timescale 1ns/1ps
// HBM-P5-RTLB 10-23: lock-step bench of the over-cap side split twin ot_hbm_su_static_side_s against the pinned
// ot_hbm_su_static_side, one stimulus, every edge:
//   (1) y identical (!==) on EVERY edge (0-edge cost on every side data result, all four functions, random fn_out);
//   (2) fault_s(t) === rest_faults_pinned(t) | softplus_fault_pinned(t-1)  (the softplus fault pin register, +1 edge);
// Stimulus: v 3/4, fn uniform over 0..7 (side codes 2/3/6/7), x from a mix of finite values, negatives, +-0, +-inf,
// NaN and subnormals (so every unit faults sometimes); coverage counts reported and required.
// SMUT (passed to the twin): 1 = y_sp +1 register without re-alignment -> (1) FAILS; 2 = no fault pin register -> (2) FAILS.
module tb_hbm_su_static_side_s;
 parameter integer SMUT=0, N=20000, SEED=1;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0, v=0; reg [2:0] fn=0, fn_out=0; reg [31:0] x=0;
 wire [31:0] y_p, y_s; wire f_p, f_s;
 ot_hbm_su_static_side ref0(.clk({6{clk}}),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(y_p),.fault(f_p));
 ot_hbm_su_static_side_s #(.SMUT(SMUT)) dut(.clk({6{clk}}),.rst_n(rst_n),.v(v),.fn(fn),.x(x),.fn_out(fn_out),.y(y_s),.fault(f_s));
 wire rest_p = ref0.f_rsq | ref0.f_sq | ref0.f_eg1 | ref0.f_eg2 | ref0.f_eg3 | ref0.f_eg4;
 wire sp_p = ref0.f_sp;
 reg sp_p_d=0; always @(posedge clk) sp_p_d <= sp_p;
 integer nn=N, seed, i, cmp=0, checks=0, errors=0, n_sp=0, n_spf=0, n_y=0, n_fault=0, n_side=0;
 function automatic [31:0] rx(input integer dummy); reg [3:0] k; begin
  k=$random(seed);
  case(k)
   0: rx=32'h7FC00000 | ($random(seed) & 32'h003FFFFF);      // NaN
   1: rx=($random(seed) & 1) ? 32'hFF800000 : 32'h7F800000;   // +-inf
   2: rx=($random(seed) & 1) ? 32'h80000000 : 32'h00000000;   // +-0
   3: rx=$random(seed) & 32'h807FFFFF;                         // subnormal
   4,5,6: rx={1'b1, 8'(8'd100 + ($random(seed) & 8'h3F)), 23'($random(seed))};  // negative, |x| ~ 2^-27..2^36
   default: rx={1'b0, 8'(8'd100 + ($random(seed) & 8'h3F)), 23'($random(seed))};
  endcase end endfunction
 always @(posedge clk) if(cmp) begin
  #1; checks=checks+1;
  if(y_s!==y_p) begin errors=errors+1; if(errors<6) $display("SIDE_S Y MISMATCH t=%0t fn_out=%0d dut=%h ref=%h", $time, fn_out, y_s, y_p); end
  if(f_s!==(rest_p|sp_p_d)) begin errors=errors+1; if(errors<6) $display("SIDE_S FAULT MISMATCH t=%0t dut=%b rest=%b sp(t-1)=%b", $time, f_s, rest_p, sp_p_d); end
  if(sp_p) n_spf=n_spf+1; if(f_p) n_fault=n_fault+1;
 end
 initial begin
  seed=SEED; if($value$plusargs("SEED=%d", i)) seed=i; if($value$plusargs("N=%d", i)) nn=i;
  repeat(4) @(negedge clk); rst_n=1;
  repeat(400) @(negedge clk);          // flush the non-reset datapath registers (X) through the deepest unit (162)
  cmp=1;
  for(i=0;i<nn;i=i+1) begin
   v=($random(seed) & 3)!=0; fn=$random(seed); fn_out=$random(seed); x=rx(0);
   if(v && fn==6) n_sp=n_sp+1; if(v && (fn==2||fn==3||fn==6||fn==7)) n_side=n_side+1;
   @(negedge clk);
  end
  v=0; repeat(300) @(negedge clk);
  if(errors==0 && n_sp>1000 && n_spf>10 && n_fault>10)
   $display("SIDE_S PASS checks=%0d side_issues=%0d spsqrt=%0d sp_fault_pulses=%0d fault_edges=%0d SMUT=%0d", checks, n_side, n_sp, n_spf, n_fault, SMUT);
  else $display("SIDE_S FAIL errors=%0d checks=%0d spsqrt=%0d sp_fault_pulses=%0d fault_edges=%0d SMUT=%0d", errors, checks, n_sp, n_spf, n_fault, SMUT);
  $finish;
 end
endmodule
