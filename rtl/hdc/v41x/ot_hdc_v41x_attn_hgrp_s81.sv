`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SVC3 (LEAD2-S81, 10-19): the S81 attention HEAD GROUP as one parameter-free hard element.
//
// dsdv_svc_att's engine ot_hdc_v41x_attn_s (production build, no SVCQ_ENG_FG3) uses TILE_S = 1: each of its
// NT = 4 tiles is ot_hdc_v41x_attn_tile_s = H/HG = 4 copies of ot_hdc_v41x_attn_hgrp_s (4 heads, own R0 boundary
// registers / dequantiser / skew lines, kept load-register copies, registered outputs), the tile level is wiring.
// This module is that group at the S81 parameters, so it hardens ONCE and binds 16 x per engine:
//   H 16, HG 4, TD 32, NBANK 5, BW 3 (PWORDS 2 + ILV 1), PWORDS 2, FPL 4, FML 6, F12 1, PCOLP 1.
// PCOLP 1: each head's p-mode columns arrive pre-selected on ld_wp (tile wiring) instead of the gsel AND-OR over
// the groups -- same bits, same cycle (tile_s lockstep vs tile_l, tools/s81_dv/svc_rs/hgrp_bench.sh).
// Zero added cycles: same ports and cycles as hgrp_s / tile_l at FML 6.
// OT_HGRP_MUT (bench mutants only): 1 = group head index ignores gid (heads 0..3 in every group);
//                                   2 = fault flag of head 0 dropped.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_hgrp_s81 (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        gid,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [2:0]        ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [2*32*16-1:0] ld_w,
    input  wire [4*2*2*16-1:0] ld_wp,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [2:0]        ibank,
    input  wire [32*18-1:0]  ib,
    output wire              ov,
    output wire [4*32-1:0]   oy,
    output wire [3:0]        oflt
);
`ifdef OT_HGRP_MUT
    localparam integer MUT = `OT_HGRP_MUT;
`else
    localparam integer MUT = 0;
`endif
    wire [7:0] gid_m = (MUT == 1) ? 8'd0 : gid;
    wire [3:0] of_i;
    ot_hdc_v41x_attn_hgrp_s #(.H(16), .HG(4), .TD(32), .NBANK(5), .BW(3), .PWORDS(2), .FPL(4), .FML(6), .F12(1),
                              .PCOLP(1)) u_g (
        .clk(clk), .rst_n(rst_n), .gid(gid_m), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp),
        .ld_w(ld_w), .ld_wp(ld_wp), .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov), .oy(oy),
        .oflt(of_i));
    assign oflt = (MUT == 2) ? {of_i[3:1], 1'b0} : of_i;
endmodule
