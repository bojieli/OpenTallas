`timescale 1ns/1ps
// q15 port-tiles (2026-10-15): one TP8 slab result port as its own hardened leaf (clock entry ck_group<g>: 10,455
// sinks): the group's scale merge register (OR of its four ROM-column m5 words, formerly g_group.merged) plus the
// ot_qwen_me_spport_w12 port (HARD_MUL: four closed ot_qwen_slab_pg_lanes children on ck_mul[3:0]).  Same logic,
// parameters and latency as the former inline instances of qfd_slab_result_half; pt_id is the port's die strap.
module qfd_slab_port_leaf (
    input  wire          ck,
    input  wire          ck_mul0, ck_mul1, ck_mul2, ck_mul3,   // scalar entries: one face pin at each lane clock pin
    input  wire          rst_n,
    input  wire [4:0]    pt_id,      // die strap 8*BAND+4*HALF+q (< 24), captured at its pin flop
    input  wire [1023:0] colq,
    input  wire [511:0]  lv_in,
    input  wire          a_v_e2,
    input  wire [112:0]  a_f_e2,
    output wire          o_we,
    output wire [23:0]   o_addr,
    output wire [15:0]   o_mask,
    output wire [511:0]  o_data,
    output wire          o_ov,
    output wire [50:0]   am,
    output wire          fault
);
    (* keep *) reg [4:0] pt_q;   // static strap: the pin flop removes the strap from every in->reg cone
    always @(posedge ck) pt_q <= pt_id;
    (* keep *) reg [255:0] merged;
    always @(posedge ck)
        merged <= colq[255:0] | colq[511:256] | colq[767:512] | colq[1023:768];
    ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),
        .SMIN(7),.PQ(1),.TREE_LAT(7),.SCALE_LAT(8),.BANDF(1),.TCUT(7),.HARD_MUL(1),.QOTS_SMALL(1)) u_port (
        .clk(ck),.ck_mul({12'd0,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),.rst_n(rst_n),.pt_id({11'd0,pt_q}),
        .lv_in(lv_in),.a_v_e2(a_v_e2),.a_f_e2(a_f_e2),.scale_q(merged),
        .o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),
        .o_data(o_data),.o_ov(o_ov),.am(am),.fault(fault));
endmodule
