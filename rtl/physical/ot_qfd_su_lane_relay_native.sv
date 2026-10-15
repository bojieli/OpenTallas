`timescale 1ns/1ps
// Exact RTREE0 hardleaf: reset remains a parent wire, no reset passthrough port.
module ot_qfd_su_lane_relay_native #(
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
    ot_qfd_su_lane_relay #(.AW(AW),.NW(NW),.WR(WR),.RD(RD),.RTREE(0)) u_native (
        .clk(clk),.rst_n(rst_n),.b_d(b_d),.b_v(b_v),.live(live),.cura(cura),.curb(curb),.curc(curc),.curd(curd),.mem_q(mem_q),.o_v(o_v),.o_d(o_d),.b_q(b_q),.bv_q(bv_q),.lv_q(lv_q),.p_q(p_q),.o_vq(o_vq),.o_dq(o_dq),.rst_l());
endmodule
