`timescale 1ns/1ps
`default_nettype none
// QW-CB16REG 10-20 (main line a): HARDENED landing ring = one CB16 region crossing as one closed tile + one closed
// station.  The flat CB16 parent (qfd_c_b16_fullm / fulln) placed each crossing as two soft halves -- the writer ring
// qfd_c_land_w1k on the SOURCE region root (56 x 56 um bay) and the reader qfd_c_land_r1k on the DESTINATION root
// (43 x 43 um bay, up to ~400 um away, joined by a 4 x W bank bus) -- so each region root fanned out to 6.7k-20.9k ring
// flops over 1-2 mm: within-region TT spread 410-813 ps, WNS -1.4..-1.7 ns at the readers (fulln/fullnb/fullm 10-20).
// Split here at the reader's OUTPUT register instead of at the bank:
//   qfd_c_ringx<W> (hard, 108 x 64.8 um, ck_w + ck_r): writer ring + the reader's slot selection (its one-hot / warm /
//       reset copies on ck_r) -> o = wg ? (OR over slots of bank[s] & oh[s] & vld[s]) : 0, i.e. EXACTLY the D input of
//       qfd_c_land_r1k's output register (combinational out of the tile: bank (ck_w) / select (ck_r) registers -> 2-3
//       gates -> pin);
//   the reader's output register = one closed station qfd_c_stn<W> on ck_r at the destination (the parent adds it).
// The region crossing is the W-bit select -> station wire (single-cycle, W bits instead of the 4 x W bank bus); the
// three reach legs (source -> tile in face, tile out face -> station, station -> destination) each stay <= 400 um as the
// soft plan's (source -> writer, bank, reader -> destination).  Same function / epochs / latency (0 added cycles):
// tile + station == qfd_c_land_w1k + qfd_c_land_r1k (bench tools/qwen_cluster/bench_ring_t.sh, lockstep every bit).
module qfd_c_land_r1k_sel #(
    parameter integer W  = 514,
    parameter integer D  = 4,
    parameter integer K  = 2,
    parameter integer GS = 30,
    parameter integer G  = 15,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D),
    parameter integer NGS = (W + GS - 1) / GS
) (
    input  wire              ck,
    input  wire              rsi,
    input  wire [D*W-1:0]    bank,
    input  wire [D*NGS-1:0]  vld,
    output wire [W-1:0]      o                    // D input of qfd_c_land_r1k's output register
);
    localparam integer S0 = (D - K) % D;
    reg            rq;
    reg [AW:0]     rc;
    always @(posedge ck) rq <= rsi;
    always @(posedge ck)
        if (!rq) rc <= {(AW + 1){1'b0}};
        else     rc <= rc + 1'b1;
    genvar g, h, s;
    generate for (g = 0; g < NGS; g = g + 1) begin : g_grp
        localparam integer B0 = g * GS;
        localparam integer NS = (W - B0 < GS) ? W - B0 : GS;
        localparam integer NH = (NS + G - 1) / G;
        (* keep = 1 *) reg         rqg;
        (* keep = 1 *) reg         wg;
        always @(posedge ck) rqg <= rsi;
        always @(posedge ck)
            if (!rqg) wg <= 1'b0;
            else if (rc == K - 1) wg <= 1'b1;
        for (h = 0; h < NH; h = h + 1) begin : g_sub
            localparam integer L = B0 + h * G;
            localparam integer N = (NS - h * G < G) ? NS - h * G : G;
            (* keep = 1 *) reg [D-1:0] oh;
            wire [N-1:0] term [0:D-1];
            always @(posedge ck)
                if (!rqg) oh <= {{(D-1){1'b0}}, 1'b1} << S0;
                else      oh <= {oh[D-2:0], oh[D-1]};
            for (s = 0; s < D; s = s + 1) begin : g_s
                assign term[s] = bank[s*W + L +: N] & {N{oh[s] & vld[g*D + s] & wg}};
            end
            reg [N-1:0] chosen;
            integer t;
            always @* begin
                chosen = {N{1'b0}};
                for (t = 0; t < D; t = t + 1) chosen = chosen | term[t];
            end
            assign o[L +: N] = chosen;
        end
    end endgenerate
endmodule

module qfd_c_ringx_t #(
    parameter integer W = 516,
    parameter integer D = 4,
    parameter integer K = 2
) (
    input  wire         ck_w,
    input  wire         rsi_w,
    input  wire [W-1:0] i,
    input  wire         ck_r,
    input  wire         rsi_r,
    output wire [W-1:0] o
);
    localparam integer AW  = (D <= 2) ? 1 : $clog2(D);
    localparam integer NGS = (W + 30 - 1) / 30;
    wire [D*W-1:0]      bank;
    wire [D*(AW+1)-1:0] epo;
    wire [D*NGS-1:0]    vld;
    qfd_c_land_w1k #(.W(W), .D(D)) u_w (.ck(ck_w), .rsi(rsi_w), .i(i), .bank(bank), .epo(epo), .vld(vld));
    qfd_c_land_r1k_sel #(.W(W), .D(D), .K(K)) u_r (.ck(ck_r), .rsi(rsi_r), .bank(bank), .vld(vld), .o(o));
endmodule

// fixed-width tops (one closed master each; the parent instantiates these + one qfd_c_stn<W> on ck_r after each)
module qfd_c_ringx516 (input wire ck_w, rsi_w, input wire [515:0] i, input wire ck_r, rsi_r, output wire [515:0] o);
    qfd_c_ringx_t #(.W(516), .D(4), .K(2)) u_ring (.ck_w(ck_w), .rsi_w(rsi_w), .i(i), .ck_r(ck_r), .rsi_r(rsi_r), .o(o));
endmodule
module qfd_c_ringx514 (input wire ck_w, rsi_w, input wire [513:0] i, input wire ck_r, rsi_r, output wire [513:0] o);
    qfd_c_ringx_t #(.W(514), .D(4), .K(2)) u_ring (.ck_w(ck_w), .rsi_w(rsi_w), .i(i), .ck_r(ck_r), .rsi_r(rsi_r), .o(o));
endmodule
`default_nettype wire
