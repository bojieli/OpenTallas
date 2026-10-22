`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DRIVE-S81-GUNIT (2026-10-20): NATIVE-32 select-network primitives for dsdv_gunit_l1f.  Bit for bit and edge for edge
// dsdv_gunit_sel.sv's dsdv_sel_cx8_2 / dsdv_sel_x2 / dsdv_sel_fold_cx / dsdv_sel_sort8 (same records, same order, same
// registers); only the select fan-out is restructured so that no mapped driver has more than 32 loads:
//   * the old exchange select s drove 2 x EW = 82 mux inputs and the first compare c1 drove 2 x EW + picks; here every
//     compare whose result selects a record is computed S times (GUNIT2: S = 8) in its own kept-hierarchy comparator
//     (dsdv_seln_gt40), and copy k selects only record bit slice k (<= 11 bits) of both records: <= 22 mux loads + picks;
//   * the second exchange's compare (one compare deep, as dsdv_sel_x2) is picked S times, copy k by c1 copy k, from the
//     four candidate compares (each candidate drives S pick muxes).
// ---------------------------------------------------------------------------------------------------------------------
// GUNIT2 (10-20, native census through the hierarchy and through buffers / inverters): the census counts every leaf pin
// a driver reaches, so (a) a record bit loads (pins per comparator input) x (comparators it feeds): the comparator is
// a fixed tree of kept 4-bit compares (<= ~3 pins per input bit) and each record register is KEPT TWICE (copy A feeds
// only the S select compares, copy B the four candidate compares of the second exchange and the data muxes); (b) a
// select loads 2 pins per muxed bit (AND-OR + inverter): S = 8 compare copies (record slices of <= 6 bits) and every
// record mux is a kept dsdv_seln_mux1, so a select reaches <= 2 x 2 x 6 + picks.  Same records, order and registers.
(* keep_hierarchy *)
module dsdv_seln_cmp4 (input wire [3:0] a, input wire [3:0] b, output wire gt, output wire eq);
    assign gt = a > b;
    assign eq = a == b;
endmodule

// unsigned a > b, 40 bits: 10 kept 4-bit compares, then the group combine
(* keep_hierarchy *)
module dsdv_seln_gt40 (input wire [39:0] a, input wire [39:0] b, output wire y);
    wire [9:0] g, e;
    genvar n;
    generate
        for (n = 0; n < 10; n = n + 1) begin : g_n
            (* keep = 1 *) dsdv_seln_cmp4 u (.a(a[4 * n +: 4]), .b(b[4 * n +: 4]), .gt(g[n]), .eq(e[n]));
        end
    endgenerate
    wire [4:0] g2, e2;                          // pairs (2 m + 1, 2 m)
    generate
        for (n = 0; n < 5; n = n + 1) begin : g_m
            assign g2[n] = g[2 * n + 1] | (e[2 * n + 1] & g[2 * n]);
            assign e2[n] = e[2 * n + 1] & e[2 * n];
        end
    endgenerate
    assign y = g2[4] | (e2[4] & (g2[3] | (e2[3] & (g2[2] | (e2[2] & (g2[1] | (e2[1] & g2[0])))))));
endmodule

// one record bit select (kept: the select reaches exactly this mux)
(* keep_hierarchy *)
module dsdv_seln_mux1 (input wire s, input wire a, input wire b, output wire y);
    assign y = s ? a : b;
endmodule

// slice bounds of record bit b (EW bits, S slices): slice of bit b = b * S / EW
module dsdv_seln_x2 #(
    parameter integer EW  = 41,
    parameter integer J2  = 1,
    parameter integer KB2 = 8,
    parameter integer S   = 8
) (
    input  wire [8*EW-1:0] u,           // copy B records
    input  wire [8*EW-1:0] w,
    input  wire [8*S-1:0]  c1,          // copy k of c1[i] at [8 k + i]
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] t;
    genvar i, b, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_t
            for (b = 0; b < EW; b = b + 1) begin : g_b
                (* keep = 1 *) dsdv_seln_mux1 u_m (.s(c1[8 * (b * S / EW) + i]), .a(u[EW*i + b]), .b(w[EW*i + b]), .y(t[EW*i + b]));
            end
        end
        for (i = 0; i < 8; i = i + 1) begin : g_p
            localparam integer L = i ^ J2;
            if (L > i) begin : g_ce
                wire g_uu, g_uw, g_wu, g_ww;
                (* keep = 1 *) dsdv_seln_gt40 u_uu (.a(u[EW*i+1 +: EW-1]), .b(u[EW*L+1 +: EW-1]), .y(g_uu));
                (* keep = 1 *) dsdv_seln_gt40 u_uw (.a(u[EW*i+1 +: EW-1]), .b(w[EW*L+1 +: EW-1]), .y(g_uw));
                (* keep = 1 *) dsdv_seln_gt40 u_wu (.a(w[EW*i+1 +: EW-1]), .b(u[EW*L+1 +: EW-1]), .y(g_wu));
                (* keep = 1 *) dsdv_seln_gt40 u_ww (.a(w[EW*i+1 +: EW-1]), .b(w[EW*L+1 +: EW-1]), .y(g_ww));
                wire [S-1:0] s;
                for (k = 0; k < S; k = k + 1) begin : g_k
                    wire ci = c1[8 * k + i], cl = c1[8 * k + L];
                    wire gt = ci ? (cl ? g_uu : g_uw) : (cl ? g_wu : g_ww);
                    assign s[k] = (gt == ((i & KB2) == 0));
                end
                for (b = 0; b < EW; b = b + 1) begin : g_b
                    (* keep = 1 *) dsdv_seln_mux1 u_qi (.s(s[b * S / EW]), .a(t[EW*i + b]), .b(t[EW*L + b]), .y(q[EW*i + b]));
                    (* keep = 1 *) dsdv_seln_mux1 u_ql (.s(s[b * S / EW]), .a(t[EW*L + b]), .b(t[EW*i + b]), .y(q[EW*L + b]));
                end
            end
        end
    endgenerate
endmodule

// two chained compare-exchanges (J1, KB1) then (J2, KB2), one compare deep (= dsdv_sel_cx8_2); da / db = copies A / B
module dsdv_seln_cx8_2 #(
    parameter integer EW  = 41,
    parameter integer J1  = 1,
    parameter integer KB1 = 2,
    parameter integer J2  = 2,
    parameter integer KB2 = 4,
    parameter integer S   = 8
) (
    input  wire [8*EW-1:0] da,
    input  wire [8*EW-1:0] db,
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] w;
    wire [8*S-1:0] c1;
    genvar i, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_w
            assign w[EW*i +: EW] = db[EW*(i ^ J1) +: EW];
        end
        for (i = 0; i < 8; i = i + 1) begin : g_p
            localparam integer P = i ^ J1;
            if (P > i) begin : g_pair                      // LO = i, HI = P: one compare per copy, both records
                for (k = 0; k < S; k = k + 1) begin : g_k
                    wire g;
                    (* keep = 1 *) dsdv_seln_gt40 u_c (.a(da[EW*i+1 +: EW-1]), .b(da[EW*P+1 +: EW-1]), .y(g));
                    assign c1[8 * k + i] = (g == ((i & KB1) == 0));
                    assign c1[8 * k + P] = (g == ((i & KB1) == 0));
                end
            end
        end
    endgenerate
    dsdv_seln_x2 #(.EW(EW), .J2(J2), .KB2(KB2), .S(S)) u_x2 (.u(db), .w(w), .c1(c1), .q(q));
endmodule

// merge8 stage 1: fold c[i] = max(a[i], b[7-i]) then compare-exchange (8, 4), one compare deep (= dsdv_sel_fold_cx)
module dsdv_seln_fold_cx #(
    parameter integer EW = 41,
    parameter integer S  = 8
) (
    input  wire [8*EW-1:0] aa, input wire [8*EW-1:0] ab,     // a copies A / B
    input  wire [8*EW-1:0] ba, input wire [8*EW-1:0] bb,     // b copies A / B
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] w;
    wire [8*S-1:0] c1;
    genvar i, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_f
            assign w[EW*i +: EW] = bb[EW*(7-i) +: EW];
            for (k = 0; k < S; k = k + 1) begin : g_k
                (* keep = 1 *) dsdv_seln_gt40 u_c (.a(aa[EW*i+1 +: EW-1]), .b(ba[EW*(7-i)+1 +: EW-1]), .y(c1[8 * k + i]));
            end
        end
    endgenerate
    dsdv_seln_x2 #(.EW(EW), .J2(4), .KB2(8), .S(S)) u_x2 (.u(ab), .w(w), .c1(c1), .q(q));
endmodule

// full bitonic sorter of 8 records, descending, CPS 2 (3 registered stages of two exchanges) (= dsdv_sel_sort8 CPS 2,
// ZQ 0).  Flags reset (valid-only reset); records unreset; every stage register kept twice (copies A / B).
module dsdv_seln_sort8 #(
    parameter integer EW  = 41,
    parameter integer FW  = 3,
    parameter integer S   = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [FW-1:0]   fi,
    input  wire [8*EW-1:0] da,
    input  wire [8*EW-1:0] db,
    output wire [FW-1:0]   fo,
    output wire [8*EW-1:0] qa,
    output wire [8*EW-1:0] qb
);
    localparam integer NS = 3, LW = 8 * EW;
    (* keep *) reg [NS*LW-1:0] ra;
    (* keep *) reg [NS*LW-1:0] rb;
    reg  [NS*FW-1:0] f;
    genvar s;
    generate
        for (s = 0; s < NS; s = s + 1) begin : g_s
            // exchanges 2 s, 2 s + 1 of (KB, J) = (2,1) (4,2) (4,1) (8,4) (8,2) (8,1)
            localparam integer J1 = (s == 0) ? 1 : (s == 1) ? 1 : 2;
            localparam integer K1 = (s == 0) ? 2 : (s == 1) ? 4 : 8;
            localparam integer J2 = (s == 0) ? 2 : (s == 1) ? 4 : 1;
            localparam integer K2 = (s == 0) ? 4 : 8;
            wire [LW-1:0] tia, tib, to;
            wire [FW-1:0] fin;
            if (s == 0) begin : g_i0
                assign tia = da; assign tib = db; assign fin = fi;
            end else begin : g_in
                assign tia = ra[LW*(s-1) +: LW]; assign tib = rb[LW*(s-1) +: LW]; assign fin = f[FW*(s-1) +: FW];
            end
            dsdv_seln_cx8_2 #(.EW(EW), .J1(J1), .KB1(K1), .J2(J2), .KB2(K2), .S(S)) u (.da(tia), .db(tib), .q(to));
            always @(posedge clk or negedge rst_n)
                if (!rst_n) f[FW*s +: FW] <= {FW{1'b0}}; else f[FW*s +: FW] <= fin;
            always @(posedge clk) begin ra[LW*s +: LW] <= to; rb[LW*s +: LW] <= to; end
        end
    endgenerate
    assign qa = ra[LW*(NS-1) +: LW];
    assign qb = rb[LW*(NS-1) +: LW];
    assign fo = f[FW*(NS-1) +: FW];
endmodule
