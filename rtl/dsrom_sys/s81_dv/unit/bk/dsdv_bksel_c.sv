`timescale 1ns/1ps
// S81U-BK2 (2026-10-17): child leaf of dsdv_bk_sel (dsdv_bk_sel.sv).
// select control leaf: dsfd_selt_c (SEARCH_PIPE, DM 4, PACE 2, MRG_PIPE, RQPIPE, SLAT 4, XDX 1: the control the closed
// PIPE2 / QIO quarter tiles need) with per-face ports (a kit port sits on ONE face): W = quarters 0 (SW) / 2 (NW),
// E = quarters 1 (SE) / 3 (NE), vd + clock + reset on S (the glue leaf dsdv_bk_g sits S of it).  Its forwarded-clock output vf is not used on the V rung.
module dsdv_bksel_c (
    input  wire [0:0]      ck,
    input  wire [0:0]      rst,
    input  wire [2*865-1:0] f_s_w, f_s_e,     // {quarter 2, quarter 0} / {quarter 3, quarter 1}
    input  wire [2*354-1:0] f_o_w, f_o_e,
    output wire [2*66-1:0]  t_c_w, t_c_e,
    output wire [1:0]       t_cr_w, t_cr_e,
    output wire [513:0]     vd
);
    localparam integer CB = 66, SB = 865, OB = 354;
    wire [4*CB-1:0] tc; wire [3:0] tcr; wire vf_unused;
    dsfd_selt_c #(.SEARCH_PIPE(1), .DM(4), .PACE(2), .MRG_PIPE(1), .RQPIPE(1), .SLAT(4), .XDX(1)) u_c (.ck(ck), .rst(rst),
        .f_s({f_s_e[SB +: SB], f_s_w[SB +: SB], f_s_e[0 +: SB], f_s_w[0 +: SB]}),
        .f_o({f_o_e[OB +: OB], f_o_w[OB +: OB], f_o_e[0 +: OB], f_o_w[0 +: OB]}),
        .t_c(tc), .t_cr(tcr), .vd(vd), .vf(vf_unused));
    assign t_c_w = {tc[2*CB +: CB], tc[0 +: CB]}; assign t_c_e = {tc[3*CB +: CB], tc[1*CB +: CB]};
    assign t_cr_w = {tcr[2], tcr[0]}; assign t_cr_e = {tcr[3], tcr[1]};
endmodule
