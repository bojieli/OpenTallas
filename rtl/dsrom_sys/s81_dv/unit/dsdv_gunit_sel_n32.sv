`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DRIVE-S81-GUNIT (2026-10-20): NATIVE-32 select-network primitives for dsdv_gunit_l1f.  Bit for bit and edge for edge
// dsdv_gunit_sel.sv's dsdv_sel_cx8_2 / dsdv_sel_x2 / dsdv_sel_fold_cx / dsdv_sel_sort8 (same records, same order, same
// registers); only the select fan-out is restructured so that no mapped driver has more than 32 loads:
//   * the old exchange select s drove 2 x EW = 82 mux inputs and the first compare c1 drove 2 x EW + picks; here every
//     compare whose result selects a record is computed S = 4 times in its own kept-hierarchy comparator
//     (dsdv_seln_gt), and copy k selects only record bit slice k (<= 11 bits) of both records: <= 22 mux loads + picks;
//   * the second exchange's compare (one compare deep, as dsdv_sel_x2) is picked S times, copy k by c1 copy k, from the
//     four candidate compares (each candidate drives S = 4 pick muxes).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module dsdv_seln_gt #(parameter integer W = 40) (input wire [W-1:0] a, input wire [W-1:0] b, output wire y);
    assign y = a > b;
endmodule

// slice bounds of record bit b (EW bits, S slices): slice of bit b = b * S / EW
module dsdv_seln_x2 #(
    parameter integer EW  = 41,
    parameter integer J2  = 1,
    parameter integer KB2 = 8,
    parameter integer S   = 4
) (
    input  wire [8*EW-1:0] u,
    input  wire [8*EW-1:0] w,
    input  wire [8*S-1:0]  c1,          // copy k of c1[i] at [8 k + i]
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] t;
    genvar i, b, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_t
            for (b = 0; b < EW; b = b + 1) begin : g_b
                assign t[EW*i + b] = c1[8 * (b * S / EW) + i] ? u[EW*i + b] : w[EW*i + b];
            end
        end
        for (i = 0; i < 8; i = i + 1) begin : g_p
            localparam integer L = i ^ J2;
            if (L > i) begin : g_ce
                wire g_uu, g_uw, g_wu, g_ww;
                dsdv_seln_gt #(.W(EW-1)) u_uu (.a(u[EW*i+1 +: EW-1]), .b(u[EW*L+1 +: EW-1]), .y(g_uu));
                dsdv_seln_gt #(.W(EW-1)) u_uw (.a(u[EW*i+1 +: EW-1]), .b(w[EW*L+1 +: EW-1]), .y(g_uw));
                dsdv_seln_gt #(.W(EW-1)) u_wu (.a(w[EW*i+1 +: EW-1]), .b(u[EW*L+1 +: EW-1]), .y(g_wu));
                dsdv_seln_gt #(.W(EW-1)) u_ww (.a(w[EW*i+1 +: EW-1]), .b(w[EW*L+1 +: EW-1]), .y(g_ww));
                wire [S-1:0] s;
                for (k = 0; k < S; k = k + 1) begin : g_k
                    wire ci = c1[8 * k + i], cl = c1[8 * k + L];
                    wire gt = ci ? (cl ? g_uu : g_uw) : (cl ? g_wu : g_ww);
                    assign s[k] = (gt == ((i & KB2) == 0));
                end
                for (b = 0; b < EW; b = b + 1) begin : g_b
                    assign q[EW*i + b] = s[b * S / EW] ? t[EW*i + b] : t[EW*L + b];
                    assign q[EW*L + b] = s[b * S / EW] ? t[EW*L + b] : t[EW*i + b];
                end
            end
        end
    endgenerate
endmodule

// two chained compare-exchanges (J1, KB1) then (J2, KB2), one compare deep (= dsdv_sel_cx8_2)
module dsdv_seln_cx8_2 #(
    parameter integer EW  = 41,
    parameter integer J1  = 1,
    parameter integer KB1 = 2,
    parameter integer J2  = 2,
    parameter integer KB2 = 4,
    parameter integer S   = 4
) (
    input  wire [8*EW-1:0] d,
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] w;
    wire [8*S-1:0] c1;
    genvar i, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_w
            assign w[EW*i +: EW] = d[EW*(i ^ J1) +: EW];
        end
        for (i = 0; i < 8; i = i + 1) begin : g_p
            localparam integer P = i ^ J1;
            if (P > i) begin : g_pair                      // LO = i, HI = P: one compare per copy, both records
                for (k = 0; k < S; k = k + 1) begin : g_k
                    wire g;
                    dsdv_seln_gt #(.W(EW-1)) u_c (.a(d[EW*i+1 +: EW-1]), .b(d[EW*P+1 +: EW-1]), .y(g));
                    assign c1[8 * k + i] = (g == ((i & KB1) == 0));
                    assign c1[8 * k + P] = (g == ((i & KB1) == 0));
                end
            end
        end
    endgenerate
    dsdv_seln_x2 #(.EW(EW), .J2(J2), .KB2(KB2), .S(S)) u_x2 (.u(d), .w(w), .c1(c1), .q(q));
endmodule

// merge8 stage 1: fold c[i] = max(a[i], b[7-i]) then compare-exchange (8, 4), one compare deep (= dsdv_sel_fold_cx)
module dsdv_seln_fold_cx #(
    parameter integer EW = 41,
    parameter integer S  = 4
) (
    input  wire [8*EW-1:0] a,
    input  wire [8*EW-1:0] b,
    output wire [8*EW-1:0] q
);
    wire [8*EW-1:0] w;
    wire [8*S-1:0] c1;
    genvar i, k;
    generate
        for (i = 0; i < 8; i = i + 1) begin : g_f
            assign w[EW*i +: EW] = b[EW*(7-i) +: EW];
            for (k = 0; k < S; k = k + 1) begin : g_k
                dsdv_seln_gt #(.W(EW-1)) u_c (.a(a[EW*i+1 +: EW-1]), .b(b[EW*(7-i)+1 +: EW-1]), .y(c1[8 * k + i]));
            end
        end
    endgenerate
    dsdv_seln_x2 #(.EW(EW), .J2(4), .KB2(8), .S(S)) u_x2 (.u(a), .w(w), .c1(c1), .q(q));
endmodule

// full bitonic sorter of 8 records, descending, CPS 2 (3 registered stages of two exchanges) (= dsdv_sel_sort8 CPS 2,
// ZQ 0).  Flags reset (valid-only reset); records unreset.
module dsdv_seln_sort8 #(
    parameter integer EW  = 41,
    parameter integer FW  = 3,
    parameter integer S   = 4
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [FW-1:0]   fi,
    input  wire [8*EW-1:0] d,
    output wire [FW-1:0]   fo,
    output wire [8*EW-1:0] q
);
    localparam integer NS = 3, LW = 8 * EW;
    reg  [NS*LW-1:0] r;
    reg  [NS*FW-1:0] f;
    genvar s;
    generate
        for (s = 0; s < NS; s = s + 1) begin : g_s
            // exchanges 2 s, 2 s + 1 of (KB, J) = (2,1) (4,2) (4,1) (8,4) (8,2) (8,1)
            localparam integer J1 = (s == 0) ? 1 : (s == 1) ? 1 : 2;
            localparam integer K1 = (s == 0) ? 2 : (s == 1) ? 4 : 8;
            localparam integer J2 = (s == 0) ? 2 : (s == 1) ? 4 : 1;
            localparam integer K2 = (s == 0) ? 4 : 8;
            wire [LW-1:0] ti, to;
            wire [FW-1:0] fin;
            if (s == 0) begin : g_i0
                assign ti = d; assign fin = fi;
            end else begin : g_in
                assign ti = r[LW*(s-1) +: LW]; assign fin = f[FW*(s-1) +: FW];
            end
            dsdv_seln_cx8_2 #(.EW(EW), .J1(J1), .KB1(K1), .J2(J2), .KB2(K2), .S(S)) u (.d(ti), .q(to));
            always @(posedge clk or negedge rst_n)
                if (!rst_n) f[FW*s +: FW] <= {FW{1'b0}}; else f[FW*s +: FW] <= fin;
            always @(posedge clk) r[LW*s +: LW] <= to;
        end
    endgenerate
    assign q  = r[LW*(NS-1) +: LW];
    assign fo = f[FW*(NS-1) +: FW];
endmodule
