`timescale 1ns/1ps
// DIE-QC-33 A0 ICG reset-relay bench (small vehicle: real qfd_tile_nk_a0c ICG=2 wrapper + real ot_a0_icg_hop + real
// ot_rst_relay, body = port stub, engine idle).  Independent model of the release: exp = rst_n delayed by
// K_REL = 2 + ICG_RRST rising edges, async assert.  Every negedge: each of the 36 B-hop reset pins == exp, and the drain
// counter dr == its model (reload while exp low, count down after).  +ICG_MUT=10 (hop tx3 on raw rst_n) and
// +ICG_MUT=11 (relay depth K_REL - 1) must FAIL; nominal must PASS.
module tb_a0_rrst;
localparam integer RR = 1, K_REL = 2 + RR, DRAIN = 64;
reg ck = 0; always #0.5 ck = ~ck;
reg rs = 0;
wire [513:0] t_out, n_y; wire hi, lo;
qfd_tile_nk_a0c #(.REGROOT_MODE(9), .ICG(2), .ICG_RRST(RR)) u_dut (.ck(ck), .rst_n(rs), .tile_id(16'd48), .tie_hi(hi), .tie_lo(lo),
  .tap(508'd0), .t_out(t_out), .n_a(514'd0), .n_b(514'd0), .n_y(n_y));
reg [7:0] sh; always @(posedge ck or negedge rs) if (!rs) sh <= 0; else sh <= {sh[6:0], 1'b1};
wire exp_r = sh[K_REL-1];
reg [7:0] drm; always @(posedge ck or negedge exp_r) if (!exp_r) drm <= DRAIN; else if (drm != 0) drm <= drm - 1;
`define H(n) u_dut.g_icg.g_hop.u_hop_``n``.rst_n
wire [35:0] hr = {`H(ck), `H(rp0), `H(rp1), `H(rp2), `H(rp3), `H(rp4), `H(rp5), `H(rp6), `H(rp7), `H(rp8), `H(rp9),
  `H(tx0), `H(tx1), `H(tx2), `H(tx3), `H(tx4), `H(tx5), `H(tx6), `H(tx7), `H(rsw), `H(rnw), `H(dw), `H(de), `H(rs), `H(rn),
  `H(fa2), `H(fa3), `H(lsl0), `H(lsl1), `H(lsl2), `H(lsl3), `H(lsl4), `H(lsl5), `H(lsl6), `H(lsl7), `H(node)};
integer cyc, errh = 0, errd = 0, checks = 0, first = -1, lows = 0;
initial begin
  for (cyc = 0; cyc < 400; cyc = cyc + 1) begin
    if (cyc == 8) rs = 1;
    if (cyc == 150) rs = 0;            // pulse: assert must be immediate, release delayed K_REL again
    if (cyc == 153) rs = 1;
    if (cyc == 260) rs = 0;            // 1-cycle pulse, shorter than K_REL
    if (cyc == 261) rs = 1;
    @(negedge ck);
    checks = checks + 1;
    if (!exp_r) lows = lows + 1;
    if (hr !== {36{exp_r}}) begin errh = errh + 1; if (first < 0) first = cyc; end
    if (u_dut.g_icg.dr !== drm) begin errd = errd + 1; if (first < 0) first = cyc; end
  end
  if (errh || errd) $display("A0RRST_FAIL MUT=%0d K_REL=%0d hop_reset_errors=%0d dr_errors=%0d first=%0d checks=%0d", u_dut.g_icg.mut, K_REL, errh, errd, first, checks);
  else $display("A0RRST_PASS MUT=%0d K_REL=%0d checks=%0d reset_low_cycles=%0d hop_pins=36 dr_ok", u_dut.g_icg.mut, K_REL, checks, lows);
  $finish;
end
endmodule
