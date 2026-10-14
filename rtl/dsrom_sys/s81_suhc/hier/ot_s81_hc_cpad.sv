`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_cpad (s81-suhc-hier-1011 comb v2, 2026-10-11): the centre chain's pad registers (hard tile, bottom row).
// Pure delay: the return rows crd stages 1 .. RP-1 (stage 0 = the ot_s81_hc_ccr capture, stage RP = the
// ot_s81_hc_crx capture) and the forward bus fv / fd stages 2 .. FP-1 (stage 1 = ot_s81_hc_cseq's centre copy,
// stage FP = the ot_s81_hc_ccf capture).  The first stage of each line is the input capture, the last the output.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_cpad #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_WR = 8, S_RT = 4, ML = 5, AL = 4,
    parameter integer MUT = 0, AMUT = 0, RF = 1, RT = 1, RW = 2, YD = 16, HALF = 0, RLY = 1, DW = 3 + RW, RET_EXTRA = 0
) (
    input  wire                 sk, srs,
    input  wire [RDW-1:0]       crd_i,
    output wire [RDW-1:0]       crd_o,
    input  wire [FVW-1:0]       fv_i,
    input  wire [FSW-1:0]       fd_i,
    output wire [FVW-1:0]       fv_o,
    output wire [FSW-1:0]       fd_o
);
    // the comb's geometry (identical to ot_s81_hc_comb; defaults = the hardened NG 256 HIER=1 configuration)
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer FVW = S_RD + 5, RVW = S_RT + 4;
    localparam integer YW  = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FSW = O_D + S_RD * 512, FDW = O_D + FDD;
    localparam integer P_T = 0, P_I = S_RT, P_Q = P_I + 8 * S_RT, P_PI = P_Q + 16 * S_RT, P_D = P_PI + 8,
                       RDW = P_D + 512 * S_RT;
    localparam integer WSL = 1 + 14 + 16 + 512;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    localparam integer HOP = 2 + RLY;                             // registers a sub-tile hop (each bus)
    localparam integer PAD = HOP * (NP - L1) * (HALF ? 2 : 1);    // the centre chain is short by NP - L1 octets
    localparam integer FP = 2 + RF + PAD;                         // forward: send + capture + RF + padding
    localparam integer RP = RT + 2 + PAD + RET_EXTRA * (NP - L1) * (HALF ? 2 : 1);                         // return: relay + send + capture + padding
    reg [1:0] rsr;                                                // tile-local reset relay (2 flops at the pin)
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    ot_hdc_delay #(.W(RDW), .D(RP - 1)) u_prd (.clk(sk), .rst_n(rs_n), .d(crd_i), .q(crd_o));
    ot_hdc_delay #(.W(FVW), .D(FP - 2), .RESET(1)) u_pfv (.clk(sk), .rst_n(rs_n), .d(fv_i), .q(fv_o));
    ot_hdc_delay #(.W(FSW), .D(FP - 2)) u_pfd (.clk(sk), .rst_n(rs_n), .d(fd_i), .q(fd_o));
endmodule
