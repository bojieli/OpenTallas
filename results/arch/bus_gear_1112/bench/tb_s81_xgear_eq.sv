`timescale 1ns/1ps
// BUS-GEAR-1 (2026-11-12) x-feed gear EQ bench with the declared cycles: one slice x group (4 lanes) -> H half-cycle
// forwarded-clock stations -> frame A (col_h9 x form, real r0/r1/r2 bands) -> A's xo -> H stations -> frame B (nx form).
//   G (geared):    ot_s81_xc_gear_tx -> dsfd_dvrlyh_139 stations -> col_h9_l4_lp_asb_xg -> ... -> col_h9_l4_lp_asb_nxg
//   R (reference): the slice word stream DELAYED BY THE DECLARED 2 EDGES -> dsfd_dvrlyh_276 stations -> asb_x -> asb_nx
// Words leave the slice on the even edges after reset release (x cadence 2); every word sets the crs4 bundle markers
// x[0] and x[566].  On odd edges G's slice output is random garbage (the TX must drop it) and R gets random payload with
// both markers 0 (a bubble).  PASS = frames A and B of G and R produce IDENTICAL ret on every edge, and ret is not
// constant (the frames consumed the words).  ROMs use a deterministic hash model (identical in G and R).
// MUT 1: R not delayed (must FAIL: the declared +2 is needed); MUT 2: G slice garbage replaces the words on even edges
// for one lane (must FAIL).
module ot_rom_4096x72_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (
    input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [71:0] rd_out);
    always @(posedge clk) if (ce_in) rd_out <= {addr_in * 12'd2654, addr_in ^ 12'h5a5, addr_in * 12'd40503, addr_in + 12'd1,
                                                 ~addr_in, addr_in * 12'd7};
endmodule

module tb;
  parameter integer H = 2, MUT = 0, NE = 6000;
  localparam integer LW = 276, BL = 139;
  reg clk = 0; always #0.416 clk = ~clk;
  reg rst_n = 0;
  reg [4*LW-1:0] w_now = 0;                 // the slice xc word on this edge (G)
  reg [4*LW-1:0] w_r_now = 0;               // R's view of this edge before the delay (word or bubble)
  reg [4*LW-1:0] r_q1 = 0;                  // R's delay line of the slice stream
  // R's slice face flop rb0 launches the word 2 edges after G's slice face flop (w_now): 1 delay + rb0
  wire [4*LW-1:0] r_in = (MUT == 1) ? w_r_now : r_q1;
  // ---------------- G
  wire [4*BL-1:0] gb0;
  ot_s81_xc_gear_tx #(.NG(1), .GEN(1'b1)) u_gtx (.ck({4{clk}}), .rst_n(rst_n), .xc(w_now), .xb(gb0));
  wire [4*BL-1:0] gA_in, gA_xo, gB_in; wire [3:0] gA_xok; wire [69:0] g_retA, g_retB;
  st139 #(.H(H)) u_gs1 (.ck(clk), .rs(rst_n), .i(gb0), .o(gA_in));
  col_h9_l4_lp_asb_xg #(.INSTANCE("u_f_0L02")) u_gA (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(gA_in),
      .xo(gA_xo), .xok(gA_xok), .ret(g_retA));
  st139 #(.H(H)) u_gs2 (.ck(clk), .rs(rst_n), .i(gA_xo), .o(gB_in));
  col_h9_l4_lp_asb_nxg #(.INSTANCE("u_f_0L03")) u_gB (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(gB_in), .ret(g_retB));
  // ---------------- R
  reg [4*LW-1:0] rb0 = 0; always @(posedge clk) rb0 <= r_in;      // the slice's own xc face flop (G: the TX register)
  wire [4*LW-1:0] rA_in, rA_xo, rB_in; wire [3:0] rA_xok; wire [69:0] r_retA, r_retB;
  st276 #(.H(H)) u_rs1 (.ck(clk), .rs(rst_n), .i(rb0), .o(rA_in));
  col_h9_l4_lp_asb_x #(.INSTANCE("u_f_0L02")) u_rA (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(rA_in),
      .xo(rA_xo), .xok(rA_xok), .ret(r_retA));
  st276 #(.H(H)) u_rs2 (.ck(clk), .rs(rst_n), .i(rA_xo), .o(rB_in));
  col_h9_l4_lp_asb_nx #(.INSTANCE("u_f_0L03")) u_rB (.ck_r0(clk), .ck_r1(clk), .ck_r2(clk), .rst_n(rst_n), .x(rB_in), .ret(r_retB));
  // ---------------- stimulus: words on even edges after release
  function [4*LW-1:0] rnd; input integer d; integer q; reg [4*LW+31:0] t;
    begin t = 0; for (q = 0; q < 4*LW; q = q + 32) t[q +: 32] = $random; rnd = t[4*LW-1:0]; end endfunction
  integer e = 0, errs = 0, chg = 0, words = 0; reg [69:0] pa = 0, pb = 0; reg ph = 1;
  always @(posedge clk) begin
    r_q1 <= w_r_now;
    if (rst_n) begin
      e = e + 1;
      if (g_retA !== r_retA || g_retB !== r_retB) begin errs = errs + 1; if (errs < 5) $display("XEQ_MISMATCH edge %0d A %0d B %0d", e, g_retA !== r_retA, g_retB !== r_retB); end
      if (g_retA !== pa || g_retB !== pb) chg = chg + 1;
      pa = g_retA; pb = g_retB;
    end
  end
  initial begin
    repeat (8) @(posedge clk); @(negedge clk); rst_n = 1;
    // the TX parity: first posedge after release = word edge
    ph = 1;
    while (e < NE) begin
      if (ph) begin
        w_now = rnd(0); w_now[0] = 1'b1; w_now[566] = 1'b1; w_r_now = w_now; words = words + 1;
        if (MUT == 2) w_now[LW*1 +: 32] = ~w_now[LW*1 +: 32];
      end else begin
        w_now = rnd(1); w_r_now = rnd(2); w_r_now[0] = 1'b0; w_r_now[566] = 1'b0;
      end
      @(negedge clk); ph = ~ph;
    end
    if (errs == 0 && chg > 50) $display("XEQ PASS H=%0d edges=%0d words=%0d ret_changes=%0d", H, e, words, chg);
    else $display("XEQ FAIL H=%0d MUT=%0d errs=%0d ret_changes=%0d", H, MUT, errs, chg);
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
