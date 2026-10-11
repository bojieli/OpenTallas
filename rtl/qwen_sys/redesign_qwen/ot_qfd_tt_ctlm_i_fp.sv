`timescale 1ns/1ps
// ot_qfd_tt_ctlm_i_fp (fe-push-qwen-1010, 2026-10-10): route top = ot_qfd_tt_ctlm_i with PSRAM = 1 (the 64 x 1,024
// program store as two ot_sram_1r1w_64x512_m1_r2c2 macros) and HQ2 = 1 (two-word controller FIFO head, register-only
// fill enable).  A wrapper, not --param: yosys 0.68 asserts on a re-processed parameterised ctlm_i top (kit note).
// Same ports, same pins as ot_qfd_tt_ctlm_i (module defaults DCU_M = DUC_M = 2, XW 24, IS = OS = 1).
module ot_qfd_tt_ctlm_i_fp (
    input  wire clk, input wire rst_n,
    // token start, program writes (the program-store copy), the SU snapshot, KV / supply readiness
    input  wire h_start, input wire [18-1:0] token, input wire [18-1:0] pos, input wire [11:0] prog_base,
    input  wire pw_v, input wire [9:0] pw_addr, input wire [63:0] pw_data,
    input  wire [24-1:0] x_oacc, input wire x_oidle, input wire [15:0] x_oprog, input wire [15:0] x_orows,
    input  wire kv_ok, input wire kv_write_drained, input wire me_mem_ok,
    // the ME snapshot, the KV descriptor, the engine clock enable
    output wire [24-1:0] me_acc_o, output wire me_idle_o, output wire [15:0] me_prog_o, output wire m_fin_o,
    output wire [18-1:0] m_fidx_o, output wire [31:0] m_fval_o,
    output wire kvd_v, output wire [24-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js, kvd_wcs, output wire [3:0] kvd_split,
    output wire [2:0] kvd_jsh, output wire [18-1:0] kvd_tiles, kvd_k, kvd_nout, output wire kvd_kindk,
    output wire [18-1:0] kvd_pos, output wire me_clk_en, output wire c_fault,
    // ot_qfd_tt_ctl's non-issue ports
    input  wire up_fault, input wire [15:0] land_cnt,
    output wire scale_re, output wire [48-1:0] scale_gre, output wire [48*24-1:0] scale_addr,
    input  wire x_rdy, output wire x_dv, output wire [24-1:0] x_dc, x_dcs, output wire [3:0] x_dsp,
    output wire [13:0] t_sel_e, t_tv_e, input wire [16-1:0] tr_fault,
    output wire p_v_e2, output wire [113-1:0] p_f_e2, input wire [12*51-1:0] p_am,
    input  wire [12-1:0] p_fault, input wire fab_fault,
    output wire ov, output wire mx_we, output wire [24-1:0] mx_addr, output wire [16-1:0] mx_mask,
    output wire [16*32-1:0] mx_data
);
    ot_qfd_tt_ctlm_i #(.PSRAM(1), .HQ2(1)) u_c (
        .clk(clk), .rst_n(rst_n), .h_start(h_start), .token(token), .pos(pos), .prog_base(prog_base), .pw_v(pw_v), .pw_addr(pw_addr), .pw_data(pw_data), .x_oacc(x_oacc), .x_oidle(x_oidle), .x_oprog(x_oprog), .x_orows(x_orows), .kv_ok(kv_ok), .kv_write_drained(kv_write_drained), .me_mem_ok(me_mem_ok), .me_acc_o(me_acc_o), .me_idle_o(me_idle_o), .me_prog_o(me_prog_o), .m_fin_o(m_fin_o), .m_fidx_o(m_fidx_o), .m_fval_o(m_fval_o), .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js), .kvd_wcs(kvd_wcs), .kvd_split(kvd_split), .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout), .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .me_clk_en(me_clk_en), .c_fault(c_fault), .up_fault(up_fault), .land_cnt(land_cnt), .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr), .x_rdy(x_rdy), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp), .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault), .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault), .fab_fault(fab_fault), .ov(ov), .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data));
endmodule
