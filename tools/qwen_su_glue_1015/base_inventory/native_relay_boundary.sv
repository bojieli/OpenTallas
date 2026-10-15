(* blackbox *) module ot_qfd_su_lane_relay_native #(
    parameter integer AW=24, NW=18, WR=16, RD=2,
    parameter integer GBW=NW+(NW+1)+5*AW+6+8+9+64+WR*16,
    parameter integer PDW=4*AW+3*32+64,
    parameter integer OVW=11,
    parameter integer ODW=7*AW+2*32+32+2+1+AW
)(
    input wire clk, rst_n,
    input wire [GBW-1:0] b_d,
    input wire [2:0] b_v,
    input wire live,
    input wire [AW-1:0] cura,curb,curc,curd,
    input wire [159:0] mem_q,
    input wire [OVW-1:0] o_v,
    input wire [ODW-1:0] o_d,
    output wire [GBW-1:0] b_q,
    output wire [2:0] bv_q,
    output wire lv_q,
    output wire [PDW-1:0] p_q,
    output wire [OVW-1:0] o_vq,
    output wire [ODW-1:0] o_dq
);
endmodule
