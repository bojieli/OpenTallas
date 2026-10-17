`timescale 1ns/1ps
// TKM-E86 2026-10-17: lockstep of ot_hgi_coll_tkm_tile_e86 (row-group roots ot_hgi_coll_tkm_tile_rg, lean comparators)
// against the reference ot_hgi_coll_tkm_tile #(.EW(86),.PT(64)) (one root, ot_tkm_lt) on random clr / conv / insert /
// up_in / tau stimulus with frequent key ties.  Every output compared every edge.  MUT=1 (expect FAIL): clk_g5 of the
// DUT is driven a half period late (one row group's root not phase-0), proving each root clocks its own rows.
module tb_hgi_coll_tkm_tile_rg_lockstep #(parameter integer MUT = 0, parameter integer NCYC = 200000, parameter integer SEED = 1);
 localparam integer EW = 86;
 reg clk = 0; always #0.5 clk = ~clk;
 wire clk_m = (MUT == 1) ? ~clk : clk;
 reg [5:0] tid, tau_t; reg [6:0] tau_l; reg clr, conv, ins_v; reg [4*EW-1:0] ins_b, up_in;
 wire r_ovf_v, d_ovf_v, r_busy, d_busy; wire [4*EW-1:0] r_ovf_b, d_ovf_b, r_up_out, d_up_out; wire [EW-2:0] r_tau, d_tau;
 ot_hgi_coll_tkm_tile #(.EW(EW), .PT(64)) u_ref(.clk(clk), .tid(tid), .clr(clr), .conv(conv), .tau_t(tau_t), .tau_l(tau_l),
  .ins_v(ins_v), .ins_b(ins_b), .ovf_v(r_ovf_v), .ovf_b(r_ovf_b), .up_in(up_in), .up_out(r_up_out), .tau_o(r_tau), .busy(r_busy));
 ot_hgi_coll_tkm_tile_e86 u_dut(.clk_g0(clk), .clk_g1(clk), .clk_g2(clk), .clk_g3(clk), .clk_g4(clk), .clk_g5(clk_m),
  .clk_g6(clk), .clk_g7(clk), .clk_g8(clk), .tid(tid), .clr(clr), .conv(conv), .tau_t(tau_t), .tau_l(tau_l),
  .ins_v(ins_v), .ins_b(ins_b), .ovf_v(d_ovf_v), .ovf_b(d_ovf_b), .up_in(up_in), .up_out(d_up_out), .tau_o(d_tau), .busy(d_busy));
 integer seed, errs, cyc, nins, nconv, novf, ntau;
 reg [EW-2:0] pool [0:7];
 function [EW-1:0] elem(input integer s);
  reg [31:0] r; begin
   r = $random(seed);
   if (r[2:0] == 0) elem = '0;                                       // empty element (nz 0, key 0)
   else if (r[4:3] != 0) elem = {pool[r[7:5]], r[8]};                  // tie-heavy: one of 8 pooled keys
   else elem = {{$random(seed), $random(seed), $random(seed)} | 85'h1 << 84, r[9]};
  end
 endfunction
 initial begin
  seed = SEED; errs = 0; nins = 0; nconv = 0; novf = 0; ntau = 0;
  for (integer k = 0; k < 8; k = k + 1) pool[k] = {1'b1, $random(seed), $random(seed), $random(seed)};
  tid = 0; tau_t = 0; tau_l = 0; clr = 1; conv = 0; ins_v = 0; ins_b = '0; up_in = '0;
  for (cyc = 0; cyc < NCYC; cyc = cyc + 1) begin
   @(negedge clk);
   if (cyc > 4 && (r_ovf_v !== d_ovf_v || (r_ovf_v && r_ovf_b !== d_ovf_b) || r_up_out !== d_up_out || r_tau !== d_tau || r_busy !== d_busy)) begin
    errs = errs + 1;
    if (errs <= 5) $display("TKM_RG_LOCKSTEP MISMATCH cyc %0d ovf %b/%b up %0d tau %0d busy %b/%b", cyc, r_ovf_v, d_ovf_v,
                            r_up_out !== d_up_out, r_tau !== d_tau, r_busy, d_busy);
   end
   if (r_ovf_v) novf = novf + 1; if (r_tau != 0) ntau = ntau + 1;
   begin : drive
    reg [31:0] r; r = $random(seed);
    clr = (r[9:0] == 0) || cyc < 3;
    conv = !clr && (r[13:10] == 0);                                   // conveyor bursts
    ins_v = !clr && !conv && r[15:14] != 0;
    ins_b = {elem(0), elem(1), elem(2), elem(3)};
    up_in = {elem(4), elem(5), elem(6), elem(7)};
    tid = r[21:16] & 6'h3; tau_t = r[27:22] & 6'h3; tau_l = $random(seed);
    nins = nins + ins_v; nconv = nconv + conv;
   end
  end
  $display("TKM_RG_LOCKSTEP cycles %0d inserts %0d conveys %0d ovf %0d tau %0d mismatches %0d", NCYC, nins, nconv, novf, ntau, errs);
  if (errs == 0 && novf > 0 && ntau > 0) $display("TKM_RG_LOCKSTEP PASS");
  else begin $display("TKM_RG_LOCKSTEP FAIL"); $fatal(1); end
  $finish;
 end
endmodule
