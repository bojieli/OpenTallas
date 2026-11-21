`timescale 1ns/1ps
// FAM-S81-SERDES-R2 11-21: one-clock hard-core wrapper of the landed KP4 decoder (wiring only, no logic, 0 cycles).
// ot_pdie_serdes_col drives all four region clocks of ot_s81_kp4_dec_native_flat_lp from pma_rck (its only use), so the
// core exposes ONE clock port ck = ck_syn = ck_dly = ck_chn = ck_out (as ot_s81_rck_dec / RX-BACK, S81-RCK-11).
module ot_s81_kp4_dec_lp_core #(parameter integer MUT = 0) (
    input  wire ck, input wire rst_n, input wire p_v, input wire [543:0] p_d,
    output wire q_v, output wire [511:0] q_d, output wire q_first, output wire q_unc, output wire [4:0] q_nerr,
    output wire [7:0] q_seq, output wire lock, output wire [31:0] n_corr, output wire [31:0] n_unc, output wire [31:0] n_relock);
    ot_s81_kp4_dec_native_flat_lp #(.MUT(MUT)) u_lp (.rst_n(rst_n), .p_v(p_v), .p_d(p_d), .q_v(q_v), .q_d(q_d), .q_first(q_first),
        .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .lock(lock), .n_corr(n_corr), .n_unc(n_unc), .n_relock(n_relock),
        .ck_syn(ck), .ck_dly(ck), .ck_chn(ck), .ck_out(ck));
endmodule
