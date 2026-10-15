`timescale 1ns/1ps
// Native KV die adapter plus CRC/retry layer. Legacy adapter keeps its proved
// production SPL profile. The PHY-facing width is 583, never the inner 548.
// ck drives the adapter; llr_ck0 drives control and llr_ck1..4 replay leaves.
// Their compensated physical clocks share one logical domain.
module qkd_d2d #(
    parameter integer W = 528, FW = 548, PW = FW + 35,
    parameter integer QD = 8, UCX = 64, FCR_RES = 32,
    parameter integer SPL = 1, MUT = 0, LLR_MUT = 0
) (
    input wire ck,
    input wire llr_ck0, llr_ck1, llr_ck2, llr_ck3, llr_ck4,
    input wire rst_n,
    input wire [2:0] t_v,
    input wire [3*W-1:0] t_d,
    output wire [2:0] t_cr,
    output wire [3:0] r_v,
    output wire [4*W-1:0] r_d,
    input wire [3:0] r_cr,
    input wire tx_up,
    output wire tx_v,
    output wire [PW-1:0] tx_flit,
    input wire rx_v,
    input wire [PW-1:0] rx_flit,
    output wire fault,
    output wire [7:0] fault_cause // {LLR3, adapter5}; bridge consumes low5
);
    wire a_up, a_tv, a_rv, af, lf;
    wire [FW-1:0] a_td, a_rd;
    wire [4:0] ac;
    wire [2:0] lc;
    ot_qkvd_kv_end #(.W(W), .FW(FW), .QD(QD), .UCX(UCX),
        .FCR_RES(FCR_RES), .SPL(SPL), .MUT(MUT)) u_adapter (
        .clk(ck), .rst_n(rst_n), .t_v(t_v), .t_d(t_d), .t_cr(t_cr),
        .r_v(r_v), .r_d(r_d), .r_cr(r_cr), .tx_up(a_up), .tx_v(a_tv),
        .tx_flit(a_td), .rx_v(a_rv), .rx_flit(a_rd), .fault(af), .fault_cause(ac));
    ot_qkvd_d2d_llr_split #(.FW(FW), .PW(PW), .MUT(LLR_MUT)) u_llr (
        .ck({llr_ck4, llr_ck3, llr_ck2, llr_ck1, llr_ck0}), .rst_n(rst_n),
        .a_tx_up(a_up), .a_tx_v(a_tv), .a_tx_flit(a_td), .a_rx_v(a_rv), .a_rx_flit(a_rd),
        .p_tx_up(tx_up), .p_tx_v(tx_v), .p_tx_flit(tx_flit), .p_rx_v(rx_v), .p_rx_flit(rx_flit),
        .fault(lf), .fault_cause(lc));
    assign fault = af | lf;
    assign fault_cause = {lc, ac};
endmodule
