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
// Words leave the slice on the even edges after reset release (x cadence 2); every word sets the crs4 bundle markers
// x[0] and x[566].  On odd edges G's slice output is random garbage (the TX must drop it) and R gets random payload with
// an all-zero bubble.  PASS = on every edge (1) the word G lands at frame A and B (the RX x_land) is IDENTICAL to
// the word R lands there, (2) the frame internal bands r0->r1, r1->r0, r1->r2, r2->r1 and (3) ret are identical in G
// and R, and the landed words and bands change >50 times (non-vacuous: ret alone retires only a few results per run).  ROMs use a deterministic hash model (identical in G and R).
// MUT 1: R not delayed (must FAIL: the declared +1 is needed); MUT 2: G slice garbage replaces the words on even edges
// for one lane (must FAIL); MUT 3: words on the wrong parity (odd edges; must FAIL: the x cadence 2 contract).
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
  parameter integer H = 2, MUT = 0, NE = 6000;
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
  wire [4*BL-1:0] gb0;
  ot_s81_xc_gear_tx #(.NG(1), .GEN(1'b1)) u_gtx (.ck({4{clk}}), .rst_n(rst_n), .xc(sf_g), .xb(gb0));
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
  integer e = 0, errs = 0, chg = 0, words = 0, lchg = 0, bchg = 0; reg [69:0] pa = 0, pb = 0; reg ph = 1;
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
      if (gA_land !== rA_in || gB_land !== rB_in) begin errs = errs + 1; if (errs < 5) $display("XEQ_LAND_MISMATCH edge %0d A %0d B %0d", e, gA_land !== rA_in, gB_land !== rB_in); end
      if (gbands !== rbands || gbandsB !== rbandsB) begin errs = errs + 1; if (errs < 5) $display("XEQ_BAND_MISMATCH edge %0d A %0d B %0d", e, gbands !== rbands, gbandsB !== rbandsB); end
      if (gA_land !== pl) lchg = lchg + 1;
      if (gbands !== pbd) bchg = bchg + 1;
      pl = gA_land; pbd = gbands;
      if (g_retA !== pa || g_retB !== pb) chg = chg + 1;
      pa = g_retA; pb = g_retB;
    end
  end
  initial begin
    repeat (8) @(posedge clk); @(negedge clk); rst_n = 1;
    // the TX parity: the first edge after release is a word edge at the TX, so with the face flop in front the first
    // stimulus tick after release is an odd (non-word) tick.  MUT 3 shifts the words to the wrong parity.
    ph = (MUT == 3) ? 1 : 0;
    while (e < NE) begin
      if (ph) begin
        w_now = rnd(0); w_now[0] = 1'b1; w_now[566] = 1'b1; w_r_now = w_now; words = words + 1;
        if (MUT == 2) w_now[LW*1 +: 32] = ~w_now[LW*1 +: 32];
      end else begin
        w_now = rnd(1); w_r_now = 0;
      end
      @(negedge clk); ph = ~ph;
    end
    if (errs == 0 && lchg > 50 && bchg > 50) $display("XEQ PASS H=%0d edges=%0d words=%0d land_changes=%0d band_changes=%0d ret_changes=%0d", H, e, words, lchg, bchg, chg);
    else $display("XEQ FAIL H=%0d MUT=%0d errs=%0d land_changes=%0d band_changes=%0d ret_changes=%0d", H, MUT, errs, lchg, bchg, chg);
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
