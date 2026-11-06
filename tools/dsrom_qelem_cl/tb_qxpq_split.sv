`timescale 1ns/1ps
// tb_qxpq_split (DIE-S81-65 2026-11-05, S81 rom_q 2-way split): all-output lock-step of ot_v41_rom_elem_q_qxpq_w10_gb_split
// (two NB = 1 halves, MSEL 0 / 1) against the NB = 2 element ot_v41_rom_elem_q_qxpq_w10_gb at the rom_q kit parameters
// (MTP1 EARLY1 FAST1 PP1 QTIMING_FIX1 QPIPE1 QZ1 QY1 QX10 PQ1 QM5 QS5 RSTP1 CGR0 OLAT0 IFN1, GO_BOUNDARY1).  Every
// output must match on every edge (reset windows and invalid cycles included), and the halves' walking / bank_free /
// sh_free / busy must be equal on every edge (the wrapper takes the pair's from u_w).  Stimulus = tb_qxpq_go_boundary's
// PQ load protocol (25-word loads, last word = address 3NSEG, random modes / timing / mid-run resets); every input
// launches from a TB rising-edge sender flop (IFN plan contract).  Mutants that must fail: OT_QXPQ_SPLIT_MUT_MSEL
// (the second half built MSEL 0: reads the first macro's rows), OT_PQT_MUT_WRAP (ref NB = 2 tag table with the old wrapped second-macro index: shows the
// stimulus reaches segment NSEG-1 of the second macro).
module tb_qxpq_split;
 integer SEED = 1;
 reg clk = 0; always #0.5 clk = ~clk;
 reg rst = 0;
 reg cfg_v = 0, go = 0, xs_v = 0;
 reg [4:0] cfg_a = 0; reg [47:0] cfg_d = 0; reg [1:0] go_tag = 0;
 reg [7:0] xs_p = 0; reg [2:0] xs_b = 0, xs_pos = 0; reg [1:0] xs_sv = 2'b11;
 reg [255:0] xs_q0 = 0, xs_q1 = 0; reg [9:0] xs_e0 = 10'd127, xs_e1 = 10'd127;
 reg s_cfg_v=0, s_go=0, s_xs_v=0; reg [4:0] s_cfg_a=0; reg [47:0] s_cfg_d=0; reg [1:0] s_go_tag=0; reg [7:0] s_xs_p=0; reg [2:0] s_xs_b=0, s_xs_pos=0;
 reg [255:0] s_xs_q0=0, s_xs_q1=0; reg [9:0] s_xs_e0=10'd127, s_xs_e1=10'd127;
 always @(posedge clk) begin s_cfg_v<=cfg_v; s_go<=go; s_xs_v<=xs_v; s_cfg_a<=cfg_a; s_cfg_d<=cfg_d; s_go_tag<=go_tag; s_xs_p<=xs_p; s_xs_b<=xs_b;
   s_xs_pos<=xs_pos; s_xs_q0<=xs_q0; s_xs_q1<=xs_q1; s_xs_e0<=xs_e0; s_xs_e1<=xs_e1; end
 localparam integer OW = 1+1+1+2+64+32+10+10+2+6+1+1;
 wire [1:0] av, bv, ae, be; wire [63:0] ad, bd; wire [31:0] ar, br; wire [9:0] asg, bsg, an, bn; wire [5:0] ap, bp;
 wire ab, bb, af, bf, awk, bwk, abf, bbf, ash, bsh;
`define QP .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8), .QZ_NE(4), .QY(1), .QX(10), .PQ(1), .QW(0), .QM(5), .QS(5), .GO_BOUNDARY(1), .RSTP(1), .CGR(0), .OLAT(0), .IFN(1)
 ot_v41_rom_elem_q_qxpq_w10_gb #(`QP, .NB(2), .INSTANCE("r")) ref_e (
  .clk(clk), .rst_n(rst), .cfg_v(s_cfg_v), .cfg_a(s_cfg_a), .cfg_d(s_cfg_d), .go(s_go), .go_tag(s_go_tag),
  .walking(awk), .bank_free(abf), .sh_free(ash),
  .xs_v(s_xs_v), .xs_p(s_xs_p), .xs_b(s_xs_b), .xs_q0(s_xs_q0), .xs_e0(s_xs_e0), .xs_q1(s_xs_q1), .xs_e1(s_xs_e1),
  .xs_pos(s_xs_pos), .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_rom_elem_q_qxpq_w10_gb_split #(`QP, .INSTANCE("r")) dut_e (
  .clk(clk), .rst_n(rst), .cfg_v(s_cfg_v), .cfg_a(s_cfg_a), .cfg_d(s_cfg_d), .go(s_go), .go_tag(s_go_tag),
  .walking(bwk), .bank_free(bbf), .sh_free(bsh),
  .xs_v(s_xs_v), .xs_p(s_xs_p), .xs_b(s_xs_b), .xs_q0(s_xs_q0), .xs_e0(s_xs_e0), .xs_q1(s_xs_q1), .xs_e1(s_xs_e1),
  .xs_pos(s_xs_pos), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf));
 wire [OW-1:0] ro = {awk, abf, ash, av, ad, ar, asg, an, ae, ap, ab, af};
 wire [OW-1:0] dov = {bwk, bbf, bsh, bv, bd, br, bsg, bn, be, bp, bb, bf};
 wire [3:0] st_w = {dut_e.u_w.u_h.o_walking, dut_e.u_w.u_h.o_bank_free, dut_e.u_w.u_h.o_sh_free, dut_e.u_w.u_h.o_busy};
 wire [3:0] st_e = {dut_e.u_e.u_h.o_walking, dut_e.u_e.u_h.o_bank_free, dut_e.u_e.u_h.o_sh_free, dut_e.u_e.u_h.o_busy};
 integer cyc = 0, mism = 0, first_mism = -1, st_mism = 0;
 integer pv_seen = 0, pv1_seen = 0, seg7_hi = 0, go_cnt = 0, cfg_cnt = 0, xs_cnt = 0, busy_seen = 0, flt_seen = 0, flt_e_only = 0, idle_hi = 0;
 always @(negedge clk) begin
   cyc = cyc + 1;
   if (ro !== dov) begin
     mism = mism + 1;
     if (first_mism < 0) first_mism = cyc;
     if (mism <= 4) $display("MISMATCH cyc %0d ref %h dut %h", cyc, ro, dov);
   end
   if (st_w !== st_e) begin st_mism = st_mism + 1; if (st_mism <= 4) $display("HALF_STATUS_MISMATCH cyc %0d w %b e %b", cyc, st_w, st_e); end
   if (av != 0) pv_seen = pv_seen + 1;
   if (av[1]) pv1_seen = pv1_seen + 1;
   if (av[1] && ar[29:16] == 14'd107) seg7_hi = seg7_hi + 1;   // a second-macro partial of segment 7 (row 107)
   if (ab) busy_seen = busy_seen + 1;
   if (af) flt_seen = flt_seen + 1;
   if (dut_e.e_fault && !dut_e.w_fault) flt_e_only = flt_e_only + 1;
 end
 integer resets = 0, phases = 0, early_go = 0;
 task automatic tick(input integer n); repeat(n) @(posedge clk); endtask
 task automatic cfg(input integer a, input [47:0] d);
   @(negedge clk); #0.01; cfg_v = 1; cfg_a = 5'(a); cfg_d = d; cfg_cnt = cfg_cnt + 1;
 endtask
 task automatic rnd_x;
   for (integer i = 0; i < 8; i = i + 1) begin xs_q0[32*i +: 32] = $urandom; xs_q1[32*i +: 32] = $urandom; end
   xs_e0 = 10'd100 + 10'($urandom % 50); xs_e1 = 10'd100 + 10'($urandom % 50);
 endtask
 task automatic wait_until_free(input integer lim);
   integer w; w = 0;
   while (!(abf && ash && !awk) && w < lim) begin
     if (ref_e.u_e.n_run) beat(0, 12); else begin @(negedge clk); w = w + 1; end
   end
 endtask
 task automatic configure(input integer mode);
   integer nu, base, fp4, lo, hi, valid, plast, qlast; reg [47:0] d;
   reg [47:0] rw [0:7];
   wait_until_free(4000);
   plast = (mode == 0) ? 2 : (mode == 3 ? $urandom % 3 : 0);
   qlast = 0;
   for (integer c = 0; c < 8; c = c + 1) begin
     fp4 = (mode == 3) ? $urandom % 2 : (mode != 1);
     lo = (mode == 3) ? $urandom % 2 : 1; hi = (mode == 3) ? $urandom % 2 : 1;
     // first-macro row c+1 (bit 15 = idle half in mode 3, 1 in 6), second-macro row c+101 / idle: the halves differ
     d = 48'(($urandom % 6 == 0 && mode == 3) ? 16'h8000 : c + 1) | (48'(1 + $urandom % 3) << 16) | (48'd1 << 21) | (48'(fp4) << 26)
       | (48'(lo) << 27) | (48'(hi) << 28) | (48'($urandom % 8192) << 29);
     cfg(c, d);
     rw[c] = (mode == 3 && $urandom % 4 == 0) ? 48'h8000 : 48'(c + 101);
     if (mode == 0) nu = (c == 0) ? 9 : ((c == 3) ? 3 : ((c == 7) ? 2 : 0));
     else if (mode == 3) nu = ($urandom % 3 == 0) ? 0 : 1 + $urandom % 12;
     else nu = 1;
     valid = (nu != 0);
     base = (mode == 3) ? $urandom % 256 : ((c == 0) ? 252 : (32 * c));
     if (nu > 8 && qlast < 1) qlast = 1;
     d = 48'(valid) | (48'(base) << 1) | (48'(nu) << 9) | (48'(c) << 16) | (48'(c) << 19) | (48'(mode == 2) << 22);
     cfg(8 + c, d);
   end
   if (mode == 0) qlast = 1;
   cfg(16, 48'(qlast) | (48'(plast) << 3) | (48'(2 * ($urandom % 64)) << 6));
   for (integer c = 0; c < 8; c = c + 1) cfg(17 + c, rw[c]);       // address 24 = the last word of the load
   @(negedge clk); #0.01; cfg_v = 0;
 endtask
 task automatic beat(input integer kind, input integer gap);
   @(negedge clk); #0.01;
   rnd_x;
   xs_v = (kind != 4); xs_p = ref_e.u_e.n_pair; xs_b = ref_e.u_e.n_b; xs_pos = ref_e.u_e.n_pos;
   xs_sv = ($urandom % 8 == 0) ? 2'($urandom) : 2'b11;
   case (kind)
     1: xs_p = xs_p + 8'd1;
     2: xs_b = xs_b + 3'd1;
     3: xs_pos = xs_pos + 3'd1;
     5: begin xs_p = $urandom; xs_b = $urandom; xs_pos = $urandom % 3; end
   endcase
   if (xs_v) xs_cnt = xs_cnt + 1;
   tick(1); @(negedge clk); #0.01; xs_v = 0; rnd_x;
   tick(gap);
 endtask
 task automatic phase(input integer mode, input integer rnd_timing);
   integer sent, g;
   configure(mode);
   begin integer w, q; w = 0; while (ash && w < 24) begin @(negedge clk); w = w + 1; end
     q = 0; w = 0; while (q < 10 && w < 20000) begin
       if (ref_e.u_e.n_run) begin beat(0, 12); q = 0; end
       else begin @(negedge clk); w = w + 1; if (ash && !awk) q = q + 1; else q = 0; end
     end end
   @(negedge clk); #0.01; go = 1; go_tag = $urandom; go_cnt = go_cnt + 1; tick(1);
   @(negedge clk); #0.01; go = 0; tick(rnd_timing ? $urandom % 6 : 4);
   sent = 0;
   while (ref_e.u_e.n_run && sent < 3000) begin
     g = rnd_timing ? 5 + $urandom % 12 : 12;
     if (rnd_timing && $urandom % 10 == 0) beat(1 + $urandom % 5, 1 + $urandom % 4);
     beat(0, g); sent = sent + 1;
   end
   phases = phases + 1;
 endtask
 task automatic die_reset(input integer n);
   @(negedge clk); #0.01; rst = 0; cfg_v = 0; go = 0; xs_v = 0; resets = resets + 1; tick(n);
   @(negedge clk); #0.01; rst = 1;
 endtask
 integer NPH = 300;
 initial begin
   void'($value$plusargs("seed=%d", SEED)); void'($value$plusargs("phases=%d", NPH));
   void'($urandom(SEED));
   rst = 0; tick(6); @(negedge clk); #0.01; rst = 1;
   for (integer p = 0; p < NPH; p = p + 1) begin
     phase((p % 5 == 0) ? p / 5 % 3 : 3, p % 2);
     tick($urandom % 40);
     if ($urandom % 12 == 0) begin
       die_reset(2 + $urandom % 5);
       if ($urandom % 2) begin cfg(0, 48'h1 | (48'd1 << 21)); @(negedge clk); #0.01; cfg_v = 0; early_go = early_go + 1; end
       else begin @(negedge clk); #0.01; go = 1; @(negedge clk); #0.01; go = 0; early_go = early_go + 1; end
       tick(200);
       die_reset(3);
     end
   end
   tick(400);
   $display("QXPQ_SPLIT cycles=%0d mism=%0d first_mism=%0d half_status_mism=%0d phases=%0d resets=%0d early=%0d go=%0d cfg=%0d xs=%0d pv_cycles=%0d pv1_cycles=%0d pv1_seg7row=%0d busy=%0d fault=%0d fault_e_only=%0d",
     cyc, mism, first_mism, st_mism, phases, resets, early_go, go_cnt, cfg_cnt, xs_cnt, pv_seen, pv1_seen, seg7_hi, busy_seen, flt_seen, flt_e_only);
   if (mism == 0 && st_mism == 0 && pv1_seen >= 200 && seg7_hi > 0) $display("QXPQ_SPLIT PASS");
   else $display("QXPQ_SPLIT FAIL");
   $finish;
 end
endmodule

// Address-hashed ROM fixture (tb_qxpq_go_boundary's, plus a second-macro flip of bits 63:0; ref and dut see the same words); synchronous read/hold like the behavioral ROM.  The
// instance name ends in the bank ("_0" / "_1"); bank 1 returns the word with bits 127:0 (codes, never an exponent) inverted.
module ot_rom_4096x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 function automatic [273:0] word(input [11:0] a);
   reg [31:0] h; integer i;
   begin
     h = {20'd0, a} * 32'h9E3779B1 + 32'h7F4A7C15;
     for (i=0;i<9;i=i+1) begin word[32*i+:32] = h; h = h * 32'h85EBCA6B + 32'hC2B2AE35 + i; end
     word[273:256] = h[17:0];
     word[135:128] = 8'd120 + {5'd0, a[2:0]}; word[271:264] = 8'd124 + {5'd0, a[3:1]};
     word[263:256] = 8'd122 + {5'd0, a[4:2]};
   end
 endfunction
 string inst = INSTANCE;
 bit bk1;
 initial bk1 = inst.len() > 0 && inst.getc(inst.len() - 1) == "1";
 bit mb1;                              // tb_qxpq_split: the pair's second macro ("...b_0" / "...b_1") holds other words
 initial mb1 = inst.len() > 2 && inst.getc(inst.len() - 3) == "b";
 wire [273:0] flip = (bk1 ? {146'd0, {128{1'b1}}} : 274'd0) ^ (mb1 ? {210'd0, {64{1'b1}}} : 274'd0);   // bits 127:0 = codes
 bit nan_sparse = 0;
 initial nan_sparse = $test$plusargs("nan_sparse");
 // +nan_sparse: no byte of bits 255:0 is a NaN code (see the bench header), ref and dut alike
 function automatic [273:0] clean(input [273:0] w);
   clean = w;
   for (integer i=0;i<32;i=i+1) if (clean[8*i+:7] == 7'h7F) clean[8*i+:7] = 7'h7E;
 endfunction
 always @(posedge clk) if(ce_in) rd_out <= nan_sparse ? clean(word(addr_in) ^ flip) : (word(addr_in) ^ flip);
endmodule
module ot_rom_8192x274_m8 #(parameter INSTANCE="")(
 input wire clk,ce_in,input wire [12:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk) if(ce_in) rd_out <= {2'b0,8'd127,{16{8'h22}},8'd127,{16{8'h22}}};
endmodule
