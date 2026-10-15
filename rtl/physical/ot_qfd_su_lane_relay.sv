`timescale 1ns/1ps
// Exact state cut from c6c44c12c ot_hdc_vstream_static_entries.g_lane.
// No tile state, group relay, memory state, or extra pipeline stage lives here.
module ot_qfd_su_lane_relay #(
    parameter integer AW=24, NW=18, WR=16, RD=2,
    parameter integer RTREE=1,
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
    output wire rst_l,
    output wire [GBW-1:0] b_q,
    output wire [2:0] bv_q,
    output wire lv_q,
    output wire [PDW-1:0] p_q,
    output wire [OVW-1:0] o_vq,
    output wire [ODW-1:0] o_dq
);
    generate if (RTREE != 0) begin:g_rl
        reg rl;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rl<=1'b0; else rl<=1'b1;
        assign rst_l=rl;
    end else begin:g_rw
        assign rst_l=rst_n;
    end endgenerate
    // Original LOFF offset sums remain in the parent, before these unchanged flops.
    ot_hdc_delay #(.W(GBW),.D(RD-1)) u_bd (.clk(clk),.rst_n(rst_l),.d(b_d),.q(b_q));
    ot_hdc_delay #(.W(3),.D(RD-1),.RESET(1)) u_bv (.clk(clk),.rst_n(rst_l),.d(b_v),.q(bv_q));
    ot_hdc_delay #(.W(1),.D(RD),.RESET(1)) u_lv (.clk(clk),.rst_n(rst_l),.d(live),.q(lv_q));
    ot_hdc_delay #(.W(PDW),.D(RD)) u_pd (.clk(clk),.rst_n(rst_l),.d({cura,curb,curc,curd,mem_q}),.q(p_q));
    ot_hdc_delay #(.W(OVW),.D(RD),.RESET(1)) u_ov (.clk(clk),.rst_n(rst_l),.d(o_v),.q(o_vq));
    ot_hdc_delay #(.W(ODW),.D(RD)) u_od (.clk(clk),.rst_n(rst_l),.d(o_d),.q(o_dq));
endmodule
