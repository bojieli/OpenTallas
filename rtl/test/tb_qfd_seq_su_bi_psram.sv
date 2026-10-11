`timescale 1ns/1ps
// tb_qfd_seq_su_bi_psram (hardcore-1010 D, 2026-10-10; generated from the ot_qfd_seq_su_bi port list): LOCKSTEP
// equivalence of the SRAM program store (PSRAM 1) against the flop store (PSRAM 0).  Both instances get the same
// stimulus: a random program (64 x 1,024) and descriptors loaded through pw / dw while idle, then h_start pulses (with a
// reset every 400 cycles, which restarts the sequencer and keeps the store) and fully random inputs on every other port for NCYC cycles.  Every output, and the captured program word prog_q, must
// match on every cycle; the run must issue >= MINRD program reads.  PMUT = 1 (read one edge late) must FAIL.
// fe-h: U1_HQ2 = 1 (two-word FIFO head, register-only fill enable) must also match; U1_HQ2 = 2 (overwrite mutant) must FAIL.
module tb_qfd_seq_su_bi_psram;
    parameter integer NCYC = 20000, SEED = 1, PMUT = 0, MINRD = 50;
    parameter integer U1_PSRAM = 1, U1_HQ2 = 0;      // the instance under test (u0 = PSRAM 0, HQ2 0); fe-h: HQ2 1, mutant HQ2 2
    localparam integer W = 16, G = 6144, AW = 24, NW = 18, SW = 64;
    reg clk = 0, rst_n = 1;
    initial #0.1 rst_n = 0;                          // a real negedge: every async reset fires (4-state sim)
    always #0.5 clk = ~clk;
    integer seed = SEED, cyc = 0, bad = 0, nrd = 0, nld = 0, k, i;
    reg [23:0] xacc = 0;
    reg  [1-1:0] h_start = 0;
    reg  [NW-1:0] tp_token = 0;
    reg  [NW-1:0] tp_pos = 0;
    reg  [1-1:0] kv_write_drained = 0;
    reg  [512-1:0] vm_rq = 0;
    reg  [1-1:0] c_ready = 0;
    reg  [1-1:0] r_valid = 0;
    reg  [512-1:0] r_data = 0;
    reg  [1-1:0] r_last = 0;
    reg  [2-1:0] r_rank = 0;
    reg  [1-1:0] r_err = 0;
    reg  [1-1:0] pw_v = 0;
    reg  [10-1:0] pw_addr = 0;
    reg  [64-1:0] pw_data = 0;
    reg  [1-1:0] dw_v = 0;
    reg  [3-1:0] dw_addr = 0;
    reg  [64-1:0] dw_data = 0;
    reg  [1-1:0] pi_su_rt_active = 0;
    reg  [8-1:0] pi_su_rt_inflight = 0;
    reg  [1-1:0] pi_su_ready = 0;
    reg  [1-1:0] pi_su_idle = 0;
    reg  [1-1:0] pi_su_wrom_re = 0;
    reg  [AW-1:0] pi_su_wrom_addr = 0;
    reg  [SW-1:0] pi_su_kv_we = 0;
    reg  [16-1:0] pi_su_progress = 0;
    reg  [16-1:0] pi_su_progress_rows = 0;
    reg  [1-1:0] pi_su_fault = 0;
    reg  [24-1:0] x_oacc = 0;
    reg  [1-1:0] x_oidle = 0;
    reg  [16-1:0] x_oprog = 0;
    reg  [1-1:0] x_ofin = 0;
    reg  [NW-1:0] x_fidx = 0;
    reg  [32-1:0] x_fval = 0;
    reg  [24-1:0] pi_su_acc = 0;
    wire [1-1:0] s_done_0, s_done_1;
    wire [NW-1:0] seq_ntok_0, seq_ntok_1;
    wire [32-1:0] seq_nval_0, seq_nval_1;
    wire [1-1:0] s_fault_0, s_fault_1;
    wire [1-1:0] core_fault_0, core_fault_1;
    wire [1-1:0] coll_busy_0, coll_busy_1;
    wire [1-1:0] kv_write_flush_0, kv_write_flush_1;
    wire [1-1:0] vm_re_0, vm_re_1;
    wire [8-1:0] vm_raddr_0, vm_raddr_1;
    wire [1-1:0] vm_we_0, vm_we_1;
    wire [8-1:0] vm_waddr_0, vm_waddr_1;
    wire [512-1:0] vm_wdata_0, vm_wdata_1;
    wire [1-1:0] c_valid_0, c_valid_1;
    wire [512-1:0] c_data_0, c_data_1;
    wire [1-1:0] c_last_0, c_last_1;
    wire [1-1:0] c_mode_0, c_mode_1;
    wire [32-1:0] c_tag_0, c_tag_1;
    wire [1-1:0] rom_fault_0, rom_fault_1;
    wire [1-1:0] su_asrc_0, su_asrc_1;
    wire [NW-1:0] su_tok_0, su_tok_1;
    wire [1-1:0] po_su_go_0, po_su_go_1;
    wire [NW-1:0] po_su_i_nout_0, po_su_i_nout_1;
    wire [NW-1:0] po_su_i_nin_0, po_su_i_nin_1;
    wire [1-1:0] po_su_i_asrc_0, po_su_i_asrc_1;
    wire [AW-1:0] po_su_i_abase_0, po_su_i_abase_1;
    wire [AW-1:0] po_su_i_aso_0, po_su_i_aso_1;
    wire [AW-1:0] po_su_i_asi_0, po_su_i_asi_1;
    wire [1-1:0] po_su_i_bsrc_0, po_su_i_bsrc_1;
    wire [AW-1:0] po_su_i_bbase_0, po_su_i_bbase_1;
    wire [AW-1:0] po_su_i_bso_0, po_su_i_bso_1;
    wire [AW-1:0] po_su_i_bsi_0, po_su_i_bsi_1;
    wire [1-1:0] po_su_i_csrc_0, po_su_i_csrc_1;
    wire [AW-1:0] po_su_i_cbase_0, po_su_i_cbase_1;
    wire [AW-1:0] po_su_i_cso_0, po_su_i_cso_1;
    wire [AW-1:0] po_su_i_csi_0, po_su_i_csi_1;
    wire [2-1:0] po_su_i_ma_0, po_su_i_ma_1;
    wire [2-1:0] po_su_i_mb_0, po_su_i_mb_1;
    wire [3-1:0] po_su_i_ad_0, po_su_i_ad_1;
    wire [3-1:0] po_su_i_sfu_0, po_su_i_sfu_1;
    wire [1-1:0] po_su_i_mc_0, po_su_i_mc_1;
    wire [1-1:0] po_su_i_md_0, po_su_i_md_1;
    wire [2-1:0] po_su_i_dst_0, po_su_i_dst_1;
    wire [AW-1:0] po_su_i_dbase_0, po_su_i_dbase_1;
    wire [AW-1:0] po_su_i_dso_0, po_su_i_dso_1;
    wire [AW-1:0] po_su_i_dsi_0, po_su_i_dsi_1;
    wire [2-1:0] po_su_i_red_0, po_su_i_red_1;
    wire [1-1:0] po_su_i_redsq_0, po_su_i_redsq_1;
    wire [AW-1:0] po_su_i_rbase_0, po_su_i_rbase_1;
    wire [AW-1:0] po_su_i_rso_0, po_su_i_rso_1;
    wire [32-1:0] po_su_i_imm1_0, po_su_i_imm1_1;
    wire [32-1:0] po_su_i_imm2_0, po_su_i_imm2_1;
    wire [1-1:0] me_start_o_0, me_start_o_1;
    wire [NW-1:0] me_token_o_0, me_token_o_1;
    wire [NW-1:0] me_pos_o_0, me_pos_o_1;
    wire [12-1:0] me_prog_base_o_0, me_prog_base_o_1;
    wire [24-1:0] su_acc_o_0, su_acc_o_1;
    wire [1-1:0] su_idle_o_0, su_idle_o_1;
    wire [16-1:0] su_prog_o_0, su_prog_o_1;
    wire [16-1:0] su_rows_o_0, su_rows_o_1;
    ot_qfd_seq_su_bi #(.PSRAM(0), .PMUT(0)) u0 (
        .clk(clk), .rst_n(rst_n),
        .h_start(h_start),
        .stage_in(6'd0), .cb_st_rdy(1'b1), .cb_st_rdy_stage(6'd0),   // constant buffer always resident (d7e8ac5da gate)
        .tp_token(tp_token),
        .tp_pos(tp_pos),
        .kv_write_drained(kv_write_drained),
        .vm_rq(vm_rq),
        .c_ready(c_ready),
        .r_valid(r_valid),
        .r_data(r_data),
        .r_last(r_last),
        .r_rank(r_rank),
        .r_err(r_err),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .dw_v(dw_v),
        .dw_addr(dw_addr),
        .dw_data(dw_data),
        .pi_su_rt_active(pi_su_rt_active),
        .pi_su_rt_inflight(pi_su_rt_inflight),
        .pi_su_ready(pi_su_ready),
        .pi_su_idle(pi_su_idle),
        .pi_su_wrom_re(pi_su_wrom_re),
        .pi_su_wrom_addr(pi_su_wrom_addr),
        .pi_su_kv_we(pi_su_kv_we),
        .pi_su_progress(pi_su_progress),
        .pi_su_progress_rows(pi_su_progress_rows),
        .pi_su_fault(pi_su_fault),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_ofin(x_ofin),
        .x_fidx(x_fidx),
        .x_fval(x_fval),
        .pi_su_acc(pi_su_acc),
        .s_done(s_done_0),
        .seq_ntok(seq_ntok_0),
        .seq_nval(seq_nval_0),
        .s_fault(s_fault_0),
        .core_fault(core_fault_0),
        .coll_busy(coll_busy_0),
        .kv_write_flush(kv_write_flush_0),
        .vm_re(vm_re_0),
        .vm_raddr(vm_raddr_0),
        .vm_we(vm_we_0),
        .vm_waddr(vm_waddr_0),
        .vm_wdata(vm_wdata_0),
        .c_valid(c_valid_0),
        .c_data(c_data_0),
        .c_last(c_last_0),
        .c_mode(c_mode_0),
        .c_tag(c_tag_0),
        .rom_fault(rom_fault_0),
        .su_asrc(su_asrc_0),
        .su_tok(su_tok_0),
        .po_su_go(po_su_go_0),
        .po_su_i_nout(po_su_i_nout_0),
        .po_su_i_nin(po_su_i_nin_0),
        .po_su_i_asrc(po_su_i_asrc_0),
        .po_su_i_abase(po_su_i_abase_0),
        .po_su_i_aso(po_su_i_aso_0),
        .po_su_i_asi(po_su_i_asi_0),
        .po_su_i_bsrc(po_su_i_bsrc_0),
        .po_su_i_bbase(po_su_i_bbase_0),
        .po_su_i_bso(po_su_i_bso_0),
        .po_su_i_bsi(po_su_i_bsi_0),
        .po_su_i_csrc(po_su_i_csrc_0),
        .po_su_i_cbase(po_su_i_cbase_0),
        .po_su_i_cso(po_su_i_cso_0),
        .po_su_i_csi(po_su_i_csi_0),
        .po_su_i_ma(po_su_i_ma_0),
        .po_su_i_mb(po_su_i_mb_0),
        .po_su_i_ad(po_su_i_ad_0),
        .po_su_i_sfu(po_su_i_sfu_0),
        .po_su_i_mc(po_su_i_mc_0),
        .po_su_i_md(po_su_i_md_0),
        .po_su_i_dst(po_su_i_dst_0),
        .po_su_i_dbase(po_su_i_dbase_0),
        .po_su_i_dso(po_su_i_dso_0),
        .po_su_i_dsi(po_su_i_dsi_0),
        .po_su_i_red(po_su_i_red_0),
        .po_su_i_redsq(po_su_i_redsq_0),
        .po_su_i_rbase(po_su_i_rbase_0),
        .po_su_i_rso(po_su_i_rso_0),
        .po_su_i_imm1(po_su_i_imm1_0),
        .po_su_i_imm2(po_su_i_imm2_0),
        .me_start_o(me_start_o_0),
        .me_token_o(me_token_o_0),
        .me_pos_o(me_pos_o_0),
        .me_prog_base_o(me_prog_base_o_0),
        .su_acc_o(su_acc_o_0),
        .su_idle_o(su_idle_o_0),
        .su_prog_o(su_prog_o_0),
        .su_rows_o(su_rows_o_0));
    ot_qfd_seq_su_bi #(.PSRAM(U1_PSRAM), .PMUT(PMUT), .HQ2(U1_HQ2)) u1 (
        .clk(clk), .rst_n(rst_n),
        .h_start(h_start),
        .stage_in(6'd0), .cb_st_rdy(1'b1), .cb_st_rdy_stage(6'd0),   // constant buffer always resident (d7e8ac5da gate)
        .tp_token(tp_token),
        .tp_pos(tp_pos),
        .kv_write_drained(kv_write_drained),
        .vm_rq(vm_rq),
        .c_ready(c_ready),
        .r_valid(r_valid),
        .r_data(r_data),
        .r_last(r_last),
        .r_rank(r_rank),
        .r_err(r_err),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .dw_v(dw_v),
        .dw_addr(dw_addr),
        .dw_data(dw_data),
        .pi_su_rt_active(pi_su_rt_active),
        .pi_su_rt_inflight(pi_su_rt_inflight),
        .pi_su_ready(pi_su_ready),
        .pi_su_idle(pi_su_idle),
        .pi_su_wrom_re(pi_su_wrom_re),
        .pi_su_wrom_addr(pi_su_wrom_addr),
        .pi_su_kv_we(pi_su_kv_we),
        .pi_su_progress(pi_su_progress),
        .pi_su_progress_rows(pi_su_progress_rows),
        .pi_su_fault(pi_su_fault),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_ofin(x_ofin),
        .x_fidx(x_fidx),
        .x_fval(x_fval),
        .pi_su_acc(pi_su_acc),
        .s_done(s_done_1),
        .seq_ntok(seq_ntok_1),
        .seq_nval(seq_nval_1),
        .s_fault(s_fault_1),
        .core_fault(core_fault_1),
        .coll_busy(coll_busy_1),
        .kv_write_flush(kv_write_flush_1),
        .vm_re(vm_re_1),
        .vm_raddr(vm_raddr_1),
        .vm_we(vm_we_1),
        .vm_waddr(vm_waddr_1),
        .vm_wdata(vm_wdata_1),
        .c_valid(c_valid_1),
        .c_data(c_data_1),
        .c_last(c_last_1),
        .c_mode(c_mode_1),
        .c_tag(c_tag_1),
        .rom_fault(rom_fault_1),
        .su_asrc(su_asrc_1),
        .su_tok(su_tok_1),
        .po_su_go(po_su_go_1),
        .po_su_i_nout(po_su_i_nout_1),
        .po_su_i_nin(po_su_i_nin_1),
        .po_su_i_asrc(po_su_i_asrc_1),
        .po_su_i_abase(po_su_i_abase_1),
        .po_su_i_aso(po_su_i_aso_1),
        .po_su_i_asi(po_su_i_asi_1),
        .po_su_i_bsrc(po_su_i_bsrc_1),
        .po_su_i_bbase(po_su_i_bbase_1),
        .po_su_i_bso(po_su_i_bso_1),
        .po_su_i_bsi(po_su_i_bsi_1),
        .po_su_i_csrc(po_su_i_csrc_1),
        .po_su_i_cbase(po_su_i_cbase_1),
        .po_su_i_cso(po_su_i_cso_1),
        .po_su_i_csi(po_su_i_csi_1),
        .po_su_i_ma(po_su_i_ma_1),
        .po_su_i_mb(po_su_i_mb_1),
        .po_su_i_ad(po_su_i_ad_1),
        .po_su_i_sfu(po_su_i_sfu_1),
        .po_su_i_mc(po_su_i_mc_1),
        .po_su_i_md(po_su_i_md_1),
        .po_su_i_dst(po_su_i_dst_1),
        .po_su_i_dbase(po_su_i_dbase_1),
        .po_su_i_dso(po_su_i_dso_1),
        .po_su_i_dsi(po_su_i_dsi_1),
        .po_su_i_red(po_su_i_red_1),
        .po_su_i_redsq(po_su_i_redsq_1),
        .po_su_i_rbase(po_su_i_rbase_1),
        .po_su_i_rso(po_su_i_rso_1),
        .po_su_i_imm1(po_su_i_imm1_1),
        .po_su_i_imm2(po_su_i_imm2_1),
        .me_start_o(me_start_o_1),
        .me_token_o(me_token_o_1),
        .me_pos_o(me_pos_o_1),
        .me_prog_base_o(me_prog_base_o_1),
        .su_acc_o(su_acc_o_1),
        .su_idle_o(su_idle_o_1),
        .su_prog_o(su_prog_o_1),
        .su_rows_o(su_rows_o_1));
    task automatic rand_inputs;
        begin
            tp_token = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            tp_pos = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            kv_write_drained = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            vm_rq = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            c_ready = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            r_valid = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            r_data = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            r_last = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            r_rank = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            r_err = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_rt_active = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_rt_inflight = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_ready = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_idle = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_wrom_re = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_wrom_addr = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_kv_we = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_progress = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_progress_rows = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oacc = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oidle = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oprog = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_ofin = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_fidx = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_fval = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pi_su_acc = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
        end
    endtask
    wire out_mismatch = (s_done_0 !== s_done_1) || (seq_ntok_0 !== seq_ntok_1) || (seq_nval_0 !== seq_nval_1) || (s_fault_0 !== s_fault_1) || (core_fault_0 !== core_fault_1) || (coll_busy_0 !== coll_busy_1) || (kv_write_flush_0 !== kv_write_flush_1) || (vm_re_0 !== vm_re_1) || (vm_raddr_0 !== vm_raddr_1) || (vm_we_0 !== vm_we_1) || (vm_waddr_0 !== vm_waddr_1) || (vm_wdata_0 !== vm_wdata_1) || (c_valid_0 !== c_valid_1) || (c_data_0 !== c_data_1) || (c_last_0 !== c_last_1) || (c_mode_0 !== c_mode_1) || (c_tag_0 !== c_tag_1) || (rom_fault_0 !== rom_fault_1) || (su_asrc_0 !== su_asrc_1) || (su_tok_0 !== su_tok_1) || (po_su_go_0 !== po_su_go_1) || (po_su_i_nout_0 !== po_su_i_nout_1) || (po_su_i_nin_0 !== po_su_i_nin_1) || (po_su_i_asrc_0 !== po_su_i_asrc_1) || (po_su_i_abase_0 !== po_su_i_abase_1) || (po_su_i_aso_0 !== po_su_i_aso_1) || (po_su_i_asi_0 !== po_su_i_asi_1) || (po_su_i_bsrc_0 !== po_su_i_bsrc_1) || (po_su_i_bbase_0 !== po_su_i_bbase_1) || (po_su_i_bso_0 !== po_su_i_bso_1) || (po_su_i_bsi_0 !== po_su_i_bsi_1) || (po_su_i_csrc_0 !== po_su_i_csrc_1) || (po_su_i_cbase_0 !== po_su_i_cbase_1) || (po_su_i_cso_0 !== po_su_i_cso_1) || (po_su_i_csi_0 !== po_su_i_csi_1) || (po_su_i_ma_0 !== po_su_i_ma_1) || (po_su_i_mb_0 !== po_su_i_mb_1) || (po_su_i_ad_0 !== po_su_i_ad_1) || (po_su_i_sfu_0 !== po_su_i_sfu_1) || (po_su_i_mc_0 !== po_su_i_mc_1) || (po_su_i_md_0 !== po_su_i_md_1) || (po_su_i_dst_0 !== po_su_i_dst_1) || (po_su_i_dbase_0 !== po_su_i_dbase_1) || (po_su_i_dso_0 !== po_su_i_dso_1) || (po_su_i_dsi_0 !== po_su_i_dsi_1) || (po_su_i_red_0 !== po_su_i_red_1) || (po_su_i_redsq_0 !== po_su_i_redsq_1) || (po_su_i_rbase_0 !== po_su_i_rbase_1) || (po_su_i_rso_0 !== po_su_i_rso_1) || (po_su_i_imm1_0 !== po_su_i_imm1_1) || (po_su_i_imm2_0 !== po_su_i_imm2_1) || (me_start_o_0 !== me_start_o_1) || (me_token_o_0 !== me_token_o_1) || (me_pos_o_0 !== me_pos_o_1) || (me_prog_base_o_0 !== me_prog_base_o_1) || (su_acc_o_0 !== su_acc_o_1) || (su_idle_o_0 !== su_idle_o_1) || (su_prog_o_0 !== su_prog_o_1) || (su_rows_o_0 !== su_rows_o_1);
    wire pq_mismatch = (u0.prog_q !== u1.prog_q);
    initial begin
        seed = SEED;   // the 5.050 simulator ignores the declaration initialiser for $random's seed: every SEED ran one stream
        repeat (6) @(posedge clk);
        rst_n = 1;
        repeat (6) @(posedge clk);
        // boot load: the program store (64 words x 16 slices) and the 8 descriptors, while the sequencer is idle
        for (k = 0; k < 1024; k = k + 1) begin
            @(negedge clk); pw_v = 1; pw_addr = k; pw_data = {$random(seed), $random(seed)};
            if (k % 16 == 0) begin         // slice 0: unit / barrier / chase / waits biased toward progress (mostly ME / SU ops)
                pw_data[1:0] = (($random(seed) & 15) == 0) ? 2'd0 : (($random(seed) & 1) ? 2'd1 : 2'd2);
                pw_data[3:2] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                pw_data[21:20] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
            end
        end
        for (k = 0; k < 8; k = k + 1) begin
            @(negedge clk); pw_v = 0; dw_v = 1; dw_addr = k;
            dw_data = {20'($random(seed)), 6'd0, 6'(k * 7 % 48), 32'($random(seed))};   // program base [43:32] inside the store
        end
        @(negedge clk); dw_v = 0;
        repeat (8) @(posedge clk);
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge clk);
            rand_inputs;
            // status inputs follow the ICUT contract (a unit's ready / idle / drained never fall without its own go; the
            // other unit's accepted-op count only climbs), else the controllers' own ICUT assertion fires on the stimulus
            pi_su_ready = 1; pi_su_idle = 1; kv_write_drained = 1; x_oidle = 1; c_ready = 1; pi_su_rt_active = 0;
            pi_su_rt_inflight = 0;
            x_oacc = 24'd0;                          // the other unit never advances: ME ops without a dependency skip
            x_ofin = ($random(seed) & 3) == 0;
            rst_n = (i % 400) != 399;                // a reset every 400 cycles restarts the sequencer (store kept)
            h_start = (i % 400) == 12;
        end
        @(negedge clk); h_start = 0;
        repeat (20) @(posedge clk);
        if (bad == 0 && nrd >= MINRD) $display("PASS seq_su_bi_psram cycles=%0d program_reads=%0d loads=%0d", cyc, nrd, nld);
        else $display("FAIL seq_su_bi_psram mismatches=%0d program_reads=%0d (min %0d) loads=%0d", bad, nrd, MINRD, nld);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (u0.prog_re_r) nrd = nrd + 1;
        // 4-state sanity: the controllers' state must be known (else two X instances would match vacuously)
        if ($isunknown({u0.u_ctrl.st, u0.u_ctrl.fq_n, u0.u_ctrl.nx_v, u0.u_ctrl.issue, u0.u_ctrl.load, u1.u_ctrl.issue, u1.u_ctrl.load})) begin
            bad = bad + 1;
            if (bad <= 5) $display("XSTATE cyc=%0d", cyc);
        end
        if (u0.u_ctrl.load) nld = nld + 1;
        if (out_mismatch || pq_mismatch) begin
            bad = bad + 1;
            if (bad <= 5) $display("MISMATCH cyc=%0d outputs=%b prog_q=%b", cyc, out_mismatch, pq_mismatch);
        end
    end
endmodule
