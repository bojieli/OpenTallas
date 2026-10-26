`timescale 1ns/1ps
// S81U-BK2 (2026-10-17): child leaf of dsdv_bk_sel (dsdv_bk_sel.sv).
// select control leaf: dsfd_selt_c (SEARCH_PIPE, DM 4, PACE 2, MRG_PIPE, RQPIPE, SLAT 4, XDX 1: the control the closed
// PIPE2 / QIO quarter tiles need) with per-face ports (a kit port sits on ONE face).
// S81U-BK3 (vertical cut): S face = quarters 0 (SW) / 1 (SE) (the S quarter row), N face = quarters 2 (NW) / 3 (NE),
// vd on the E face (the glue leaf sits E of it).  Its forwarded-clock output vf is not used on the V rung.
module dsdv_bksel_c (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    input  wire [2*865-1:0] f_s_s, f_s_n,     // {quarter 1, quarter 0} / {quarter 3, quarter 2}
    input  wire [2*354-1:0] f_o_s, f_o_n,
    output wire [2*66-1:0]  t_c_s, t_c_n,
    output wire [1:0]       t_cr_s, t_cr_n,
    output wire [366:0]     vd    // S81-KITS-RTLC 10-24: packed {vd[512:502], vd[356:1]} (dsdv_bk_g VD_PK)
);
    localparam integer CB = 66, SB = 865, OB = 354;
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire vf_unused; wire [513:0] vdw;
    dsfd_selt_c #(.SEARCH_PIPE(1), .DM(4), .PACE(2), .MRG_PIPE(1), .RQPIPE(1), .SLAT(4), .XDX(1)) u_c (.ck(ck), .rst(rst),
        .f_s({f_s_n, f_s_s}), .f_o({f_o_n, f_o_s}), .t_c(tc), .t_cr(tcr), .vd(vdw), .vf(vf_unused));
    assign vd = {vdw[512:502], vdw[356:1]};             // vdw[513], vdw[501:357]: constant 0; vdw[0]: unread (dropped pins)
    assign t_c_s = tc[0 +: 2*CB]; assign t_c_n = tc[2*CB +: 2*CB];
    assign t_cr_s = tcr[1:0]; assign t_cr_n = tcr[3:2];
endmodule

// S81U-BK3: the selector quarter leaf dsfd_selt_q2 (DM 4, SAFE, CMP_RETIME, PIPE2, QIO, ILD, FRPR: the closed s81b-selt_q2-frprildb
// configuration)
module dsdv_bksel_q (
    input  wire [0:0]   ck,
    input  wire [0:0]   rst,
    input  wire [514:0] lane,
    input  wire [65:0]  f_c,
    input  wire [0:0]   f_cr,
    output wire [864:0] t_s,
    output wire [353:0] t_o
);
`ifdef OT_S81PH_SEL_HQ
    // S81-TOPK7 hierarchical quarter (ot_s81ph_hq_tile.sv): same ports / function / edges, native-census-clean structure
`ifndef OT_S81PH_SEL_HQ_MUT
`define OT_S81PH_SEL_HQ_MUT 0
`endif
    dsfd_selt_q_hq #(.DM(4), .MUT(`OT_S81PH_SEL_HQ_MUT)) u_q (.ck(ck), .rst(rst), .lane(lane), .f_c(f_c), .f_cr(f_cr),
        .t_s(t_s), .t_o(t_o));
`else
    dsfd_selt_q2 #(.DM(4), .CMP_RETIME(1), .PIPE2(1), .QIO(1), .ILD(1), .FRPR(1)) u_q (.ck(ck), .rst(rst), .lane(lane),
        .f_c(f_c), .f_cr(f_cr), .t_s(t_s), .t_o(t_o));
`endif
endmodule
