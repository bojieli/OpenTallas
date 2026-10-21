`timescale 1ns/1ps
// GENERATED SOURCE CANDIDATE by tools/s81_dv/svc_rs/reset_profile/gen_profile.py
// No default adoption or native/physical claim.
module dsdv_svc_rs_attw1_r9 #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                          parameter integer SRAM_MACRO = 0, parameter integer ROOT = 0, parameter integer PMEM = 1, parameter integer PV_IDENTITY = 0,
                          parameter integer TEXT = 0, parameter integer TLX = 0, parameter integer TXD = 0,
                          parameter integer NTP = 1, parameter integer ROLE_EXT = 0) (   // ATTN1: one physical engine tile (only tx_i0 / tx_o0)
    input  wire             ck,
    input  wire             rst,
    input wire reset_early11,
    input  wire [3:0]       sid,
    input  wire [804:0]     cs,
    output wire [2*341-1:0] qrq,
    input  wire [1:0]       qrk,
    input  wire [1:0]       qwd,
    input  wire [1:0]       qrv,
    input  wire [2*256-1:0] qr_data,
    input  wire [2*17-1:0]  qr_tag,
    input  wire [2*4-1:0]   qr_beat,
    output wire             l_v,
    output wire [2131:0]    l_d,
    output wire             pv_ov,
    output wire [512:0]     pv_od,
    output wire             sm_st,
    output wire [3:0]       sm_kind,
    output wire [7:0]       sm_jid,
    output wire             sm_rv,
    output wire             sm_rp,
    output wire [2:0]       sm_rj,
    output wire [511:0]     sm_rd,
    output wire             go_o,
    output wire [9:0]       tjob_o,
    output wire             done,
    output wire [7:0]       tagj,
    output wire [1:0]       hcr,
    output wire [1:0]       hack,
    output wire             fault,
    output wire [31:0] fault_code, output wire [15:0] pio_o, pvo_o, jc_o, output wire [1:0] st_o,
    input wire [21:0] role_i, input wire [7:0] pvs_i,
    // SVC4 landed engine (TEXT 1): engine tile t's input bundle (1,618 b) out / output bundle (529 b) back, one port per
    // tile so each lands in its own region (dsdv_svc_attw_f -> dsdv_svc_attw_f_lp); unused when TEXT 0
    output wire [1617:0]    tx_i0,
    input  wire [528:0]     tx_o0
);
    wire rn; wire [21:0] role, role_local; wire [7:0] pvs, pvs_local;
    assign role=ROLE_EXT ? role_i : role_local; assign pvs=ROLE_EXT ? pvs_i : pvs_local;
    dsdv_svc_rs_rl #(.ST(ST)) u_rl (.ck(ck), .rst(rst), .sid(sid), .rn(rn), .role(role_local), .pvs(pvs_local));
    wire [3:0] tile = role[3:0];
`ifdef RS_MUT_GD
    wire [7:0] gd = role[21:14] + 8'(sid == 4'd0);    // bench negative control: one slice starts a cycle late
`else
    wire [7:0] gd = role[21:14];
`endif
    wire [31:0] a_fc; assign fault_code=a_fc;
    localparam integer NTX = (NTP > 0) ? NTP : 4;
    wire [NTX*1618-1:0] txi; wire [NTX*529-1:0] txo;
    assign tx_i0 = txi; assign txo = tx_o0;
    generate if (NTX != 1) begin : g_bad
        initial $error("dsdv_svc_rs_attw1: NTP must be 1");
    end endgenerate
    dsdv_svc_att_reset9 #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO != 0), .PMEM(PMEM), .PV_IDENTITY(PV_IDENTITY), .TEXT(TEXT), .TLX(TLX),
                   .TXD(TXD), .NTP(NTP)) u_att (
        .clk(ck), .rst_n(rn), .reset_early9(reset_early11), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(ROOT != 0),
        .q_v(cs[0]), .q_d(cs[512:1]), .hw_v(cs[513]), .hw_d(cs[804:514]),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go_o), .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault), .fault_code(a_fc), .pio_o(pio_o), .pvo_o(pvo_o), .jc_o(jc_o), .st_o(st_o),
        .tx_i(txi), .tx_o(txo));
endmodule
