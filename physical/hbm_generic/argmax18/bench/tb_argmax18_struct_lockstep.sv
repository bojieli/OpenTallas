`timescale 1ns/1ps
// CLOCK-RESET/argmax 2026-10-25: lockstep STRUCT=1 vs STRUCT=0 (the qualified value leaf) of ot_hgi_argmax18_m.
// Random rows (lengths 1..40 beats, back-to-back and gapped), random masks, values with NaN / +-0 / ties / infinities,
// random bias_en per beat, cfg changes, two asynchronous resets mid-stream.  Every output compared on every cycle:
// out_v / fault / out_range_fault 4-state (!==); out_idx / out_nan / out_value whenever the reference out_v is 1.
module tb_argmax18_struct_lockstep;
 parameter integer FLAT = 7;
 parameter integer FAST = 1;
 parameter integer NCYC = 4000;
 parameter integer SEED = 1;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,in_v=0,in_last=0,in_bias_en=0;
 reg [7:0] in_mask=0; reg [255:0] in_vals=0,in_bias=0; reg [6:0] cfg_rank=0; reg [17:0] cfg_imm_a=0;
 wire v0,v1,n0,n1,f0,f1,r0,r1; wire [17:0] i0,i1; wire [31:0] x0,x1;
 ot_hgi_argmax18_m #(.GENERIC18(1),.FLAT(FLAT),.FAST(FAST),.STRUCT(0)) ref0(clk,rst_n,in_v,in_last,in_bias_en,in_mask,in_vals,in_bias,cfg_rank,cfg_imm_a,v0,i0,n0,f0,r0,x0);
 ot_hgi_argmax18_m #(.GENERIC18(1),.FLAT(FLAT),.FAST(FAST),.STRUCT(1)) dut1(clk,rst_n,in_v,in_last,in_bias_en,in_mask,in_vals,in_bias,cfg_rank,cfg_imm_a,v1,i1,n1,f1,r1,x1);
 integer cyc=0, rows=0, outs=0, errs=0, left=0, seed=SEED, j;
 function [31:0] rval(input integer r);
  integer c; begin c = $urandom%16;
   case (c)
    0: rval = 32'h7fc00000 | ($urandom & 32'h003fffff) | 1;   // NaN
    1: rval = 32'h80000000; 2: rval = 32'h00000000;            // -0 / +0
    3: rval = 32'h7f800000; 4: rval = 32'hff800000;            // +-inf
    5,6,7: rval = 32'h40000000 | ($urandom%4);                // near ties
    default: rval = $urandom;
   endcase end
 endfunction
 always @(posedge clk) begin
  #0.1;
  cyc = cyc + 1;
  if (v0 !== v1 || f0 !== f1 || r0 !== r1) begin errs=errs+1; if (errs<10) $display("MISMATCH ctl cyc=%0d v %b/%b f %b/%b r %b/%b",cyc,v0,v1,f0,f1,r0,r1); end
  if (v0 === 1'b1) begin outs = outs + 1;
   if (i0 !== i1 || n0 !== n1 || x0 !== x1) begin errs=errs+1; if (errs<10) $display("MISMATCH data cyc=%0d idx %h/%h nan %b/%b val %h/%h",cyc,i0,i1,n0,n1,x0,x1); end
  end
 end
 initial begin
  j = $urandom(seed);
  repeat (3) @(negedge clk); rst_n = 1;
  while (cyc < NCYC) begin
   @(negedge clk);
   if (cyc == NCYC/3 || cyc == (2*NCYC)/3 + 5) begin rst_n = 0; @(negedge clk); @(negedge clk); rst_n = 1; end
   if (left == 0 && ($urandom%4 != 0)) begin left = 1 + $urandom%40; rows = rows + 1; cfg_rank = $urandom; cfg_imm_a = $urandom; end
   if (left > 0 && ($urandom%8 != 0)) begin
    in_v = 1; in_last = (left == 1); left = left - 1;
    in_mask = ($urandom%3 == 0) ? $urandom : 8'hff; in_bias_en = ($urandom%3 == 0);
    for (j = 0; j < 8; j = j + 1) begin in_vals[32*j +: 32] = rval(0); in_bias[32*j +: 32] = rval(0); end
   end else begin
    in_v = ($urandom%16 == 0) ? 1'b0 : 1'b0; in_last = $urandom; in_mask = $urandom; in_bias_en = $urandom;
    for (j = 0; j < 8; j = j + 1) begin in_vals[32*j +: 32] = $urandom; in_bias[32*j +: 32] = $urandom; end
   end
  end
  $display("LOCKSTEP FLAT=%0d FAST=%0d cycles=%0d rows=%0d outputs=%0d mismatches=%0d %s", FLAT, FAST, cyc, rows, outs, errs, errs==0 && outs>100 ? "PASS" : "FAIL");
  $finish;
 end
endmodule
