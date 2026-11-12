`timescale 1ns/1ps
`ifdef XEQ_H10
`define XEQ_FR(k) col_h10_l4_lp_asb_``k
`else
`define XEQ_FR(k) col_h9_l4_lp_asb_``k
`endif
// BUS-GEAR-1/-2 (2026-11-12) x-feed gear EQ bench with the declared cycles: one slice x group (4 lanes) -> slice face
// flop -> H half-cycle forwarded-clock stations -> frame A (x form, real r0/r1/r2 bands) -> A's xo -> H stations ->
// frame B (nx form).
//   G (geared):    face flop -> ot_s81_xc_gear_tx -> dsfd_dvrlyh_139 stations -> col_h<9|10>_l4_lp_asb_xg -> ... -> _asb_nxg
//   R (reference): the slice word stream DELAYED BY THE DECLARED 1 EDGE -> face flop -> dsfd_dvrlyh_276 stations ->
//                  _asb_x -> _asb_nx (the ungeared die)
// Stimulus = the real slice xc format: every edge carries the crs4 bundle markers x[0] / x[566] = 1 (ot_s81sl_mk) and
// the word valid xw_v at x[1] / x[567]; a word edge has xw_v = 1 and payload, a bubble edge xw_v = 0 and random payload
// (G and R get DIFFERENT random bubble payload).  Words are 2..4 edges apart (x cadence 2 = never on consecutive edges)
// and the first word sits SEED % 4 edges after release, so word edges take both parities in every run: the TX is
// framed by xw_v, not by a reset parity.  PASS = (1) ret of frames A and B identical in G and R on every edge, (2) on
// every edge where R lands a word (xw_v = 1) G lands the IDENTICAL 1104-b word at frames A and B (RX x_land vs the
// reference frame input: the declared +1 edge), (3) on every other edge G lands no word (x[1] = x[567] = 0), (4) the TX
// fault flt stays 0, and > 50 words are compared at each frame.  On bubble edges the RX upper beat is don't-care by design
// (OGATE 0), so the frame internal bands are compared for information only (band_diff_edges).
// MUT 1: R not delayed (must FAIL: the declared +1 is needed); MUT 2: one lane of G's words corrupted (must FAIL);
// MUT 3: one pair of words on consecutive edges (breaks the cadence-2 contract: must FAIL and raise flt).
// MUT 4: TX phase-lock removed (ot_s81_xc_gear_tx MUT 1 = reset-parity framing): must FAIL (words lost on the other parity).
// +define+XEQ_H10 runs the col_h10 frames instead of col_h9.
module ot_rom_4096x72_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [71:0] rd_out);
    always @(posedge clk) if (ce_in) rd_out <= {addr_in * 12'd2654, addr_in ^ 12'h5a5, addr_in * 12'd40503, addr_in + 12'd1,
                                                 ~addr_in, addr_in * 12'd7};
endmodule

module ot_rom_4096x274_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [273:0] rd_out);
    integer q; reg [275:0] t;
    always @(posedge clk) if (ce_in) begin
        for (q = 0; q < 274; q = q + 12) t[q +: 12] = addr_in * (12'd2654 + q[11:0]) ^ (addr_in >> (q % 7));
        rd_out <= t[273:0];
    end
endmodule

// ASAP7 ICG behavioural model (same latch form as physical/die_plan/s81/bind/models/cells_used.v ICGx4), used by the
// frame ROM elements; identical in G and R.
module ICGx1_ASAP7_75t_R (input wire CLK, input wire ENA, input wire SE, output wire GCLK);
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!CLK) en_l = ENA | SE;
    /* verilator lint_on COMBDLY */
    assign GCLK = CLK & en_l;
endmodule

module tb;
  parameter integer H = 2, NE = 6000;
  integer MUT = 0, SEED = 1;                // runtime: +MUT=<n> +SEED=<n> (one build per H)
  localparam integer LW = 276, BL = 139;
  reg clk = 0; always #0.416 clk = ~clk;
  reg rst_n = 0;
  reg [4*LW-1:0] w_now = 0;                 // the slice xc word on this edge (G)
  reg [4*LW-1:0] w_r_now = 0;               // R's view of this edge before the delay (word or bubble)
  reg [4*LW-1:0] r_q1 = 0;                  // R's delay line of the slice stream
  // R's slice face flop rb0 launches the word 1 edge (the declared beat) after G's slice face flop sf_g
  wire [4*LW-1:0] r_in = (MUT == 1) ? w_r_now : r_q1;
  reg [4*LW-1:0] sf_g = 0; always @(posedge clk) sf_g <= w_now;  // G: the slice's own xc face flop
  // ---------------- G
  wire [4*BL-1:0] gb_v, gb_p, gb0; wire g_flt_v, g_flt_p, g_flt;
  ot_s81_xc_gear_tx #(.NG(1), .GEN(1'b1)) u_gtx (.ck({4{clk}}), .rst_n(rst_n), .xc(sf_g), .xb(gb_v), .flt(g_flt_v));
  // MUT 4: the same TX with the xw_v phase-lock removed (reset-parity framing) must FAIL for some start parity
  ot_s81_xc_gear_tx #(.NG(1), .GEN(1'b1), .MUT(1)) u_gtx_p (.ck({4{clk}}), .rst_n(rst_n), .xc(sf_g), .xb(gb_p), .flt(g_flt_p));
  assign gb0 = (MUT == 4) ? gb_p : gb_v; assign g_flt = (MUT == 4) ? 1'b0 : g_flt_v;
  wire [4*BL-1:0] gA_in, gA_xo, gB_in; wire [3:0] gA_xok; wire [69:0] g_retA, g_retB;
  st139 #(.H(H)) u_gs1 (.ck(clk), .rs(rst_n), .i(gb0), .o(gA_in));
  `XEQ_FR(xg) #(.INSTANCE("u_f_0L02")) u_gA (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(gA_in),
      .xo(gA_xo), .xok(gA_xok), .ret(g_retA));
  st139 #(.H(H)) u_gs2 (.ck(clk), .rs(rst_n), .i(gA_xo), .o(gB_in));
  `XEQ_FR(nxg) #(.INSTANCE("u_f_0L03")) u_gB (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(gB_in), .ret(g_retB));
  // ---------------- R
  reg [4*LW-1:0] rb0 = 0; always @(posedge clk) rb0 <= r_in;      // R: the slice's own xc face flop
  wire [4*LW-1:0] rA_in, rA_xo, rB_in; wire [3:0] rA_xok; wire [69:0] r_retA, r_retB;
  st276 #(.H(H)) u_rs1 (.ck(clk), .rs(rst_n), .i(rb0), .o(rA_in));
  `XEQ_FR(x) #(.INSTANCE("u_f_0L02")) u_rA (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(rA_in),
      .xo(rA_xo), .xok(rA_xok), .ret(r_retA));
  st276 #(.H(H)) u_rs2 (.ck(clk), .rs(rst_n), .i(rA_xo), .o(rB_in));
  `XEQ_FR(nx) #(.INSTANCE("u_f_0L03")) u_rB (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(rB_in), .ret(r_retB));
  // ---------------- stimulus: words on even edges after release
  function [4*LW-1:0] rnd; input integer d; integer q; reg [4*LW+31:0] t;
    begin t = 0; for (q = 0; q < 4*LW; q = q + 32) t[q +: 32] = $random; rnd = t[4*LW-1:0]; end endfunction
  integer e = 0, errs = 0, chg = 0, words = 0, lchg = 0, bchg = 0, wa = 0, wb = 0, bdiff = 0, t = 0, sd = 1; reg [69:0] pa = 0, pb = 0;
  wire [4*LW-1:0] gA_land = u_gA.x_land, gB_land = u_gB.x_land;
  wire [2*1167+261+321-1:0] gbands = {u_gA.r0_o0, u_gA.r1_o0, u_gA.r1_o1, u_gA.r2_o0},
                            rbands = {u_rA.r0_o0, u_rA.r1_o0, u_rA.r1_o1, u_rA.r2_o0};
  wire [2*1167+261+321-1:0] gbandsB = {u_gB.r0_o0, u_gB.r1_o0, u_gB.r1_o1, u_gB.r2_o0},
                            rbandsB = {u_rB.r0_o0, u_rB.r1_o0, u_rB.r1_o1, u_rB.r2_o0};
  reg [4*LW-1:0] pl = 0; reg [2*1167+261+321-1:0] pbd = 0;
  always @(posedge clk) begin
    r_q1 <= w_r_now;
    if (rst_n) begin
      e = e + 1;
      if (g_retA !== r_retA || g_retB !== r_retB) begin errs = errs + 1; if (errs < 5) $display("XEQ_MISMATCH edge %0d A %0d B %0d", e, g_retA !== r_retA, g_retB !== r_retB); end
      if (rA_in[1]) begin wa = wa + 1; if (gA_land !== rA_in) begin errs = errs + 1; if (errs < 5) $display("XEQ_LAND_MISMATCH A edge %0d", e); end end
      else if (gA_land[1] | gA_land[567]) begin errs = errs + 1; if (errs < 5) $display("XEQ_PHANTOM A edge %0d", e); end
      if (rB_in[1]) begin wb = wb + 1; if (gB_land !== rB_in) begin errs = errs + 1; if (errs < 5) $display("XEQ_LAND_MISMATCH B edge %0d", e); end end
      else if (gB_land[1] | gB_land[567]) begin errs = errs + 1; if (errs < 5) $display("XEQ_PHANTOM B edge %0d", e); end
      if (gbands !== rbands || gbandsB !== rbandsB) bdiff = bdiff + 1;
      if (gA_land !== pl) lchg = lchg + 1;
      if (gbands !== pbd) bchg = bchg + 1;
      pl = gA_land; pbd = gbands;
      if (g_retA !== pa || g_retB !== pb) chg = chg + 1;
      pa = g_retA; pb = g_retB;
    end
  end
  initial begin
    if (!$value$plusargs("MUT=%d", MUT)) MUT = 0;
    if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
    sd = SEED;
    repeat (8) @(posedge clk); @(negedge clk); rst_n = 1;
    t = SEED % 4;                            // idle edges before the first word (start parity)
    while (e < NE) begin
      if (t == 0) begin
        w_now = rnd(0); w_now[0] = 1'b1; w_now[566] = 1'b1; w_now[1] = 1'b1; w_now[567] = 1'b1;
        w_r_now = w_now; words = words + 1;
        if (MUT == 2) w_now[LW*1 +: 32] = ~w_now[LW*1 +: 32];
        t = (MUT == 3 && words == 200) ? 0 : 1 + (($random(sd) & 32'h7fffffff) % 3);   // next word 2..4 edges later
      end else begin
        w_now = rnd(1); w_now[0] = 1'b1; w_now[566] = 1'b1; w_now[1] = 1'b0; w_now[567] = 1'b0;
        w_r_now = rnd(2); w_r_now[0] = 1'b1; w_r_now[566] = 1'b1; w_r_now[1] = 1'b0; w_r_now[567] = 1'b0;
        t = t - 1;
      end
      @(negedge clk);
    end
    if (g_flt) begin errs = errs + 1; $display("XEQ_TX_FAULT flt=1 (word on a beat-1 edge)"); end
    if (errs == 0 && wa > 50 && wb > 50) $display("XEQ PASS H=%0d SEED=%0d edges=%0d words=%0d cmpA=%0d cmpB=%0d ret_changes=%0d band_diff_edges=%0d flt=%0d", H, SEED, e, words, wa, wb, chg, bdiff, g_flt);
    else $display("XEQ FAIL H=%0d MUT=%0d SEED=%0d errs=%0d cmpA=%0d cmpB=%0d ret_changes=%0d band_diff_edges=%0d flt=%0d", H, MUT, SEED, errs, wa, wb, chg, bdiff, g_flt);
    $finish;
  end
endmodule

// H stations of the half-cycle forwarded-clock relay chain (forwarded clock = previous station's ck_o)
module st139 #(parameter integer H = 2) (input wire ck, input wire rs, input wire [555:0] i, output wire [555:0] o);
  genvar k, s;
  generate for (k = 0; k < 4; k = k + 1) begin : g_l
    wire [138:0] d [0:H]; wire c [0:H];
    assign d[0] = i[139*k +: 139]; assign c[0] = ck;
    for (s = 0; s < H; s = s + 1) begin : g_s
      dsfd_dvrlyh_139_NS u (.ck(c[s]), .rs(rs), .i(d[s]), .o(d[s+1]), .ck_o(c[s+1]));
    end
    assign o[139*k +: 139] = d[H];
  end endgenerate
endmodule
module st276 #(parameter integer H = 2) (input wire ck, input wire rs, input wire [1103:0] i, output wire [1103:0] o);
  genvar k, s;
  generate for (k = 0; k < 4; k = k + 1) begin : g_l
    wire [275:0] d [0:H]; wire c [0:H];
    assign d[0] = i[276*k +: 276]; assign c[0] = ck;
    for (s = 0; s < H; s = s + 1) begin : g_s
      dsfd_dvrlyh_276_NS u (.ck(c[s]), .rs(rs), .i(d[s]), .o(d[s+1]), .ck_o(c[s+1]));
    end
    assign o[276*k +: 276] = d[H];
  end endgenerate
endmodule
