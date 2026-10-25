`timescale 1ns/1ps
// tb_hbm_su_qcore_w2 (HBM-BIND 2026-10-24): the B2 2-writer SU core vs the as-built 4-writer core bound the way the
// 16-SM die binds it (writer 2 = NW leg, writer 3 = NE leg; SW / SE writers idle), both at the die parameters
// (COLLPORT 1, RF_LOCAL 1, PRETREE 1, ROW_EN 2, WDEC 1).  Random commands / reads / reducer traffic; the two writers
// hit the SAME address on ~1/4 of their writes so the NE-over-NW priority is exercised.  Every output, every edge.
// PASS line: QCORE_W2 PASS checks=N errors=0.  MUTW 1 (swapped writers) must FAIL.
module tb_hbm_su_qcore_w2;
 parameter integer MUTW = 0, NCYC = 20000;
 reg clk = 0, rst_n = 0; always #1 clk = ~clk;  // --timing (Verilator) or iverilog
 reg [53:0] rd; reg [73:0] rc; reg [1:0] dr; reg [127:0] sx; reg [1:0] wv; reg [15:0] wa; reg [63:0] wd;
 reg rrv; reg [4:0] rra; reg [255:0] rrd; reg [31:0] sfx; reg [267:0] st;
 wire [127:0] bw_a, bw_b; wire [35:0] bc_a, bc_b; wire [255:0] ds_a, ds_b; wire sv_a, sv_b, rv_a, rv_b, f_a, f_b;
 wire [31:0] tg_a, tg_b, x_a, x_b;
 ot_hbm_su_static_qcore_r13_w2 #(.COLLPORT(1),.RF_LOCAL(1),.PRETREE(1),.ROW_EN(2),.WDEC(1),.MUTW(MUTW)) dut(
  .clk_ctl(clk),.rst_n(rst_n),.rf_rd_cmd(rd),.red_cmd(rc),.rf_drain_cmd(dr),.slice_x(sx),.rf_wv(wv),.rf_wa(wa),.rf_wd(wd),
  .rf_bword(bw_a),.rf_bcmd(bc_a),.rf_dsec(ds_a),.red_sv(sv_a),.red_tag(tg_a),.red_x(x_a),.red_rf_v(rv_a),
  .rr_wv(rrv),.rr_wa(rra),.rr_wd(rrd),.sfu_x(sfx),.slice_t(st),.fault(f_a));
 ot_hbm_su_static_qcore_r13 #(.COLLPORT(1),.RF_LOCAL(1),.PRETREE(1),.ROW_EN(2),.WDEC(1)) ref4(
  .clk_ctl(clk),.rst_n(rst_n),.rf_rd_cmd(rd),.red_cmd(rc),.rf_drain_cmd(dr),.slice_x(sx),
  .rf_wv({wv, 2'b00}),.rf_wa({wa, 16'd0}),.rf_wd({wd, 64'd0}),
  .rf_bword(bw_b),.rf_bcmd(bc_b),.rf_dsec(ds_b),.red_sv(sv_b),.red_tag(tg_b),.red_x(x_b),.red_rf_v(rv_b),
  .rr_wv(rrv),.rr_wa(rra),.rr_wd(rrd),.sfu_x(sfx),.slice_t(st),.fault(f_b));
 function automatic [31:0] r32; r32 = $urandom; endfunction
 integer i, k, checks = 0, errors = 0;
 task automatic drive;
  rd = {r32(), r32()}; rc = {r32(), r32(), r32()}; dr = $urandom; sx = {r32(), r32(), r32(), r32()};
  wv = $urandom; wa = {r32()} & 16'h3f3f; if (($urandom % 4) == 0) wa[15:8] = wa[7:0];
  wd = {r32(), r32()}; rrv = ($urandom % 8) == 0; rra = $urandom; for (k = 0; k < 8; k = k + 1) rrd[k*32 +: 32] = r32();
  sfx = r32(); for (k = 0; k < 9; k = k + 1) st[k*32 +: 32] = r32();
 endtask
 initial begin
  drive; repeat (4) @(negedge clk); rst_n = 1;
  for (i = 0; i < NCYC; i = i + 1) begin
   @(negedge clk); drive;
   if (i % 4096 == 4095) rst_n = 0; else rst_n = 1;
   checks = checks + 1;
   if ({bw_a, bc_a, ds_a, sv_a, tg_a, x_a, rv_a, f_a} !== {bw_b, bc_b, ds_b, sv_b, tg_b, x_b, rv_b, f_b}) begin
    errors = errors + 1; if (errors < 4) $display("ERR cycle %0d", i);
   end
  end
  $display("QCORE_W2 %s checks=%0d errors=%0d MUTW=%0d", errors == 0 ? "PASS" : "FAIL", checks, errors, MUTW);
  $finish;
 end
endmodule
