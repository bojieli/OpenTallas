`timescale 1ns/1ps
// dsfd_sp_ctrl_e (s81-ctl-1011, 2026-10-11): the layer-die (ROLE 0) control-plane master with ENGINE-SPLIT die ports
// and hop_tx retired (decision 10-10 22:02; physical/s81_ctrl/ADAPTER_CONTRACT_1011.json v2).  Generator:
// --ctrl-slab --ctrl-adapters.
//   c<e> = {cv[e], cd[e] 84}  one-cycle command pulse + descriptor to engine e's slab endpoint (ot_s81_slab_ep)
//   d<e> = {dv[e], dt[e] 8}   one-cycle validated done pulse + tag from engine e's slab endpoint
//   s<e> = {online, fault}    engine e's endpoint status (level); a fault raises flt and fvec[15] (sticky)
// Program memory through pw_* / prog_len, static user bound cfg_users, inbound stage messages i_* (the collective
// slab's control lane c_rx), payload VM write port vwe / vwa / vwd, status flt / fvec / stk / snap.
// Removed against dsfd_sp_ctrl: o_* (the hop_tx framer is retired: the stage hand-off is a descriptor on the
// collective / WFC kit engine port), vre / vra / vrq / vrv (only hop_tx read the VM), hop_go (hop_tx's go);
// am_* / boot_ok / hc_* / cpl_* belong to the head / source roles (dsfd_sp_ctrl_e_h / _src, not this layer shell):
// their core inputs are held inactive here by role, not functional tie-offs of this die.
// Engines absent on a layer die (head 8, emb 9, eng 10, spare 11 unless the WFC kit binds it) keep their ports; the
// die gate (die_port_audit) requires each to be bound or declared role-absent with no program op routed to it.
module dsfd_sp_ctrl_e #(parameter integer MY_ID=0, SRC_LO=0, SRC_HI=4094, parameter [15:0] TYPE_MASK=16'h000A) (
    input wire ck, input wire rs,
    input wire pw_v, input wire [6:0] pw_a, input wire [27:0] pw_d, input wire [7:0] prog_len, input wire [11:0] cfg_users,
    input wire i_v, output wire i_r, input wire [511:0] i_d, input wire i_l,
    output wire [84:0] c0, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11,
    input  wire [8:0]  d0, d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11,
    input  wire [1:0]  s0, s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11,
    output wire vwe, output wire [13:0] vwa, output wire [511:0] vwd,
    output reg flt, output reg [15:0] fvec, output wire stk, output wire [15:0] snap
);
    wire c_flt; wire [15:0] c_fvec;
    wire [11:0] cv; wire [12*84-1:0] cd; reg [11:0] dv; reg [12*8-1:0] dt;
    wire o_v, o_l, vre, hc_r, cpl_v; wire [511:0] o_d; wire [13:0] vra; wire [113:0] cpl_d;
    // engine done pins: captured in pin flops (die inputs land in a flop)
    always @(posedge ck or negedge rs)
        if (!rs) dv <= 12'd0;
        else dv <= {d11[8], d10[8], d9[8], d8[8], d7[8], d6[8], d5[8], d4[8], d3[8], d2[8], d1[8], d0[8]};
    always @(posedge ck) dt <= {d11[7:0], d10[7:0], d9[7:0], d8[7:0], d7[7:0], d6[7:0], d5[7:0], d4[7:0], d3[7:0], d2[7:0], d1[7:0], d0[7:0]};
    // engine command pins: launched from flops
    reg [12*85-1:0] cq;
    integer k;
    always @(posedge ck or negedge rs)
        if (!rs) for (k = 0; k < 12; k = k + 1) cq[85*k + 84] <= 1'b0;
        else for (k = 0; k < 12; k = k + 1) cq[85*k + 84] <= cv[k];
    always @(posedge ck) for (k = 0; k < 12; k = k + 1) cq[85*k +: 84] <= cd[84*k +: 84];
    assign {c11, c10, c9, c8, c7, c6, c5, c4, c3, c2, c1, c0} = cq;
    dsfd_sp_ctrl_core #(.USE_VM_RVALID(0), .OUT_DEPTH(4), .ROLE(0), .HOP_TX(0), .MY_ID(MY_ID), .SRC_LO(SRC_LO),
        .SRC_HI(SRC_HI), .TYPE_MASK(TYPE_MASK)) u (
        .ck(ck), .rs(rs), .pw_v(pw_v), .pw_a(pw_a), .pw_d(pw_d), .prog_len(prog_len), .cfg_users(cfg_users),
        .i_v(i_v), .i_r(i_r), .i_d(i_d), .i_l(i_l), .o_v(o_v), .o_r(1'b1), .o_d(o_d), .o_l(o_l),
        .cv(cv), .cd(cd), .dv(dv), .dt(dt), .hop_go(1'b0),
        .vwe(vwe), .vwa(vwa), .vwd(vwd), .vre(vre), .vra(vra), .vrq(512'd0), .vrv(1'b0),
        .am_v(1'b0), .am_pos(21'd0), .am_tok(21'd0), .am_val(32'd0), .boot_ok(1'b1),
        .hc_v(1'b0), .hc_r(hc_r), .hc_op(2'd0), .hc_tag(8'd0), .hc_user(8'd0), .hc_pos(21'd0), .hc_tok(21'd0),
        .cpl_v(cpl_v), .cpl_r(1'b1), .cpl_d(cpl_d),
        .flt(c_flt), .fvec(c_fvec), .stk(stk), .snap(snap));
    // endpoint status pins: captured, faults made sticky into the die's control-plane fault
    reg [11:0] ef_q; reg ef_s;
    always @(posedge ck or negedge rs)
        if (!rs) begin ef_q <= 12'd0; ef_s <= 1'b0; flt <= 1'b0; fvec <= 16'd0; end
        else begin
            ef_q <= {s11[0], s10[0], s9[0], s8[0], s7[0], s6[0], s5[0], s4[0], s3[0], s2[0], s1[0], s0[0]};
            if (|ef_q) ef_s <= 1'b1;
            flt <= c_flt | ef_s; fvec <= {c_fvec[15] | ef_s, c_fvec[14:0]};
        end
endmodule
