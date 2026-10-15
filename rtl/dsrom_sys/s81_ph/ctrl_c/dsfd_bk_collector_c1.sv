`timescale 1ns/1ps
// dsfd_bk_collector_c1 (s81-die-rtl-bind 2026-10-14, die item F5): the collector slab master of a die with ONE HBM stack
// (S81 layer1: stack SW only; the TP4 peers' rows meet in the collective's rows_allgather, not here).  The 4-stack
// master dsfd_bk_collector_c joins the DONE heads of four stack lanes: on a 1-stack die three of them have no producer,
// so its DONE never leaves (the col engine would hang).  This master has the SW lane only:
//   lane tile dsfd_colt_lane (CLOSED, unchanged) -> HOPS die stations -> dsfd_colt_mrgn NQ 1 (dsfd_colt_mrg over the
//   present lanes) -> vd / vf, and the col engine endpoint dsfd_dw_ep_c on a snoop of vd (as dsfd_bk_collector_c).
module dsfd_bk_collector_c1 #(parameter integer HOPS = 7, parameter integer DEPTH = 256, parameter integer DM = 12,
                              parameter integer PACE = 2) (
    input wire [514:0] cSW,
    input wire [0:0] ck, input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    wire [512:0] tw, fw; wire [3:0] tf, ff; wire tcr, fcr;
    dsfd_colt_lane #(.DEPTH(DEPTH), .DM(DM)) u_l (.ck(ck), .rst(rst), .c_in(cSW), .f_cr(fcr), .t_w(tw), .t_f(tf));
    reg [512:0] sw [0:HOPS]; reg [3:0] sf [0:HOPS]; reg sc [0:HOPS];
    integer h;
    always @(*) begin sw[0] = tw; sf[0] = tf; sc[0] = tcr; end
    always @(posedge ck[0]) for (h = 1; h <= HOPS; h = h + 1) begin sw[h] <= sw[h-1]; sf[h] <= sf[h-1]; sc[h] <= sc[h-1]; end
    assign fw = sw[HOPS]; assign ff = sf[HOPS]; assign fcr = sc[HOPS];
    dsfd_colt_mrgn #(.NQ(1), .DM(DM), .PACE(PACE)) u_m (.ck(ck), .rst(rst), .f_w(fw), .f_f(ff), .t_cr(tcr), .vd(vd), .vf(vf));
    dsfd_dw_ep_c u_dw (.ck(ck), .rst(rst), .vh({vd[513:502], vd[493:482], vd[1], vd[0]}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
