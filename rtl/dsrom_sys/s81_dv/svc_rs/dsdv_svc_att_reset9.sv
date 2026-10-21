`timescale 1ns/1ps
// GENERATED SOURCE CANDIDATE by tools/s81_dv/svc_rs/reset_profile/gen_profile.py
// No default adoption or native/physical claim.
module dsdv_svc_att_reset9 #(
    parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0, parameter integer PFIFO = 512,
    parameter integer PMEM = 1, parameter integer PVQ = 8, parameter integer DQ = 8,
    parameter integer PV_IDENTITY = 0,
    parameter bit SRAM_MACRO = 0, parameter bit QMEM_SRAM = 0,
    parameter integer TEXT = 0, parameter integer TLX = 0, parameter integer TXD = 0,
    parameter integer NTP = 0, parameter integer NTX = (NTP > 0) ? NTP : 4
) (
    input  wire clk, input wire rst_n, input wire reset_early9, input wire [3:0] sid, input wire [3:0] tile, input wire [7:0] gd,
    input  wire [7:0] pvs, input wire root,
    input  wire q_v, input wire [511:0] q_d, input wire hw_v, input wire [290:0] hw_d,
    output wire [2*341-1:0] qrq, input wire [1:0] qrk, input wire [1:0] qwd, input wire [1:0] qrv,
    input  wire [2*256-1:0] qr_data, input wire [2*17-1:0] qr_tag, input wire [2*4-1:0] qr_beat,
    output wire l_v, output wire [2131:0] l_d, output wire pv_ov, output wire [512:0] pv_od,
    output wire sm_st, output wire [3:0] sm_kind, output wire [7:0] sm_jid, output wire sm_rv, output wire sm_rp,
    output wire [2:0] sm_rj, output wire [511:0] sm_rd,
    output wire go_o, output wire [9:0] tjob_o, output wire done, output wire [7:0] tagj,
    output wire [1:0] hcr, output wire [1:0] hack, output wire fault, output wire [31:0] fault_code,
    output wire [15:0] pio_o, pvo_o, jc_o, output wire [1:0] st_o,
    output wire [NTX*1618-1:0] tx_i, input wire [NTX*529-1:0] tx_o
);
`ifdef OT_SVC_ATT_PINREG
    reg pq_v, phw_v; reg [511:0] pq_d; reg [290:0] phw_d;
    reg [1:0] pqrk, pqwd, pqrv; reg [2*256-1:0] pqr_data; reg [2*17-1:0] pqr_tag; reg [2*4-1:0] pqr_beat;
    reg fault_q; wire fault_c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pq_v <= 1'b0; phw_v <= 1'b0; pqrk <= '0; pqwd <= '0; pqrv <= '0; fault_q <= 1'b0; end
        else begin pq_v <= q_v; phw_v <= hw_v; pqrk <= qrk; pqwd <= qwd; pqrv <= qrv; fault_q <= fault_c; end
    always @(posedge clk) begin pq_d <= q_d; phw_d <= hw_d; pqr_data <= qr_data; pqr_tag <= qr_tag; pqr_beat <= qr_beat; end
    assign fault = fault_q;
`else
    wire pq_v = q_v, phw_v = hw_v; wire [511:0] pq_d = q_d; wire [290:0] phw_d = hw_d;
    wire [1:0] pqrk = qrk, pqwd = qwd, pqrv = qrv; wire [2*256-1:0] pqr_data = qr_data; wire [2*17-1:0] pqr_tag = qr_tag;
    wire [2*4-1:0] pqr_beat = qr_beat; wire fault_c;
    assign fault = fault_c;
`endif
    wire[511:0]reset_leaf9;
    ot_s81svc_reset9_rl2_n32 u_reset9(.clk(clk),.reset_early9(reset_early9),.reset_leaf(reset_leaf9));
    dsdv_svc_att_core #(.RESET_PROFILE(1),.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .PFIFO(PFIFO), .PMEM(PMEM), .PVQ(PVQ), .DQ(DQ),
                        .PV_IDENTITY(PV_IDENTITY), .SRAM_MACRO(SRAM_MACRO), .QMEM_SRAM(QMEM_SRAM), .TEXT(TEXT), .TLX(TLX), .TXD(TXD),
                        .NTP(NTP)) u_core (
        .clk(clk), .rst_n(rst_n), .reset_leaf(reset_leaf9), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(root),
        .q_v(pq_v), .q_d(pq_d), .hw_v(phw_v), .hw_d(phw_d),
        .qrq(qrq), .qrk(pqrk), .qwd(pqwd), .qrv(pqrv), .qr_data(pqr_data), .qr_tag(pqr_tag), .qr_beat(pqr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(pv_ov), .pv_od(pv_od),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go_o), .tjob_o(tjob_o), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(fault_c),
        .fault_code(fault_code), .pio_o(pio_o), .pvo_o(pvo_o), .jc_o(jc_o), .st_o(st_o), .tx_i(tx_i), .tx_o(tx_o));
endmodule
