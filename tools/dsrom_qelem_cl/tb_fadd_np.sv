`timescale 1ns/1ps
// tb_fadd_np (S81-QXPQ3 2026-10-20): ot_v41_fadd_np against ot_v41_fadd (CUT 1_0111_1011) on the same operand stream:
// y / err / valid_out and every kept copy (yk, vk) must equal the reference every cycle (=== after the first valid),
// and the EXT0 form (step 0 bundle from ot_v41_fadd_s0) must equal it too.  Operands: random words plus classes that
// reach every step (zeros of both signs, subnormals, equal / near exponents for cancellation, max finite for overflow,
// infinities / NaNs, round-carry patterns).  +define+OT_NP_FADD_MUT must FAIL.
module tb_fadd_np;
 reg clk = 0; always #0.5 clk = ~clk;
 reg rst_n = 0, v = 0; reg [31:0] a = 0, b = 0;
 wire [31:0] ry, ny, ey; wire [1:0] re, ne, ee; wire rv, nv, ev; wire [63:0] nyk; wire [1:0] nvk; wire [31:0] eyk; wire evk;
 ot_v41_fadd #(.CUT(9'b1_0111_1011)) u_r (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ry), .err(re), .valid_out(rv));
 ot_v41_fadd_np #(.NYK(2), .NVK(2)) u_n (.clk(clk), .rst_v(rst_n), .rst_y(rst_n), .rst_k({rst_n, rst_n}), .valid_in(v), .a(a), .b(b),
   .o0_ext(105'd0), .y(ny), .err(ne), .valid_out(nv), .yk(nyk), .vk(nvk));
 wire [104:0] s0;
 ot_v41_fadd_s0 u_s0 (.valid_in(v), .a(a), .b(b), .o0(s0));
 ot_v41_fadd_np #(.EXT0(1), .NYK(1), .NVK(1)) u_e (.clk(clk), .rst_v(rst_n), .rst_y(rst_n), .rst_k(rst_n), .valid_in(1'b0),
   .a(32'd0), .b(32'd0), .o0_ext(s0), .y(ey), .err(ee), .valid_out(ev), .yk(eyk), .vk(evk));
 integer cyc = 0, bad = 0, nval = 0, seed = 1;
 function automatic [31:0] pick(input integer k);
   reg [31:0] r; integer c;
   begin
     r = $urandom; c = $urandom % 16;
     case (c)
       0: r = {r[31], 31'd0};                                  // +-0
       1: r = {r[31], 8'd0, r[22:0]};                          // subnormal
       2: r = {r[31], 8'hff, (r[0] ? 23'd0 : r[22:0])};        // inf / NaN
       3: r = {r[31], 8'hfe, r[22:0]};                         // near overflow
       4: r = {r[31], 8'd1, r[22:0]};                          // min normal
       5: r = {r[31], 8'd127 + 8'(r[3:0]), 23'h7fffff ^ 23'(r[6:4])};   // round-carry patterns
       default: ;
     endcase
     pick = r;
   end
 endfunction
 always @(negedge clk) begin
   cyc = cyc + 1;
   if (rst_n) begin
     if ({ry, re, rv} !== {ny, ne, nv} || {2{ry}} !== nyk || {2{rv}} !== nvk || {ry, re, rv} !== {ey, ee, ev} || ry !== eyk || rv !== evk) begin
       bad = bad + 1; if (bad <= 5) $display("FADD_NP MISMATCH cyc %0d ref %h/%0d/%b np %h/%0d/%b ext %h/%0d/%b", cyc, ry, re, rv, ny, ne, nv, ey, ee, ev);
     end
     if (rv) nval = nval + 1;
   end
   #0.01;
   v = ($urandom % 8) != 0;
   a = pick(0); b = pick(1);
   if ($urandom % 6 == 0) b = {~a[31], a[30:0]} ^ 32'($urandom % 4);   // cancellation
   if ($urandom % 7 == 0) b = {b[31], a[30:23] - 8'($urandom % 30), b[22:0]};   // exponent distance 0..29
 end
 initial begin
   void'($value$plusargs("seed=%d", seed)); void'($urandom(seed));
   #5.01 rst_n = 1;
   #400000;
   $display("FADD_NP cycles=%0d valid=%0d bad=%0d", cyc, nval, bad);
   if (bad == 0 && nval > 1000) $display("FADD_NP PASS"); else $display("FADD_NP FAIL");
   $finish;
 end
endmodule
