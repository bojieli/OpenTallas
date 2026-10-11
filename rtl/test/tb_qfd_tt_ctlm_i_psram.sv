`timescale 1ns/1ps
// tb_qfd_tt_ctlm_i_psram (fe-push-qwen-1010, 2026-10-10; generated from the ot_qfd_tt_ctlm_i port list by the same
// recipe as tb_qfd_seq_su_bi_psram): LOCKSTEP equivalence of u1 (PSRAM U1_PSRAM, HQ2 U1_HQ2) against u0 (PSRAM 0 = the
// flop program store, HQ2 0).  Same stimulus to both: a random 64 x 1,024 program loaded through pw while idle, then
// h_start pulses (a reset every 400 cycles restarts the controller and keeps the store) and random inputs on every other
// port for NCYC cycles.  Every output, and the captured program word prog_q, must match on every cycle; the run must
// issue >= MINRD program reads.  Built with +define+OT_ICUT_NONFATAL: with the real ME unit (ot_qfd_tt_ctl) behind the
// in-tile shell and a random program, the ME unit's readiness can fall without a go, so the controller's ICUT check fires
// identically in u0 and u1 (counted as icut_stim, reported, not fatal); the comparison is still every output every cycle.
// Negative controls: PMUT = 1 (read one edge late) and U1_HQ2 = 2 (head overwrite) FAIL.
module tb_qfd_tt_ctlm_i_psram;
    parameter integer NCYC = 20000, SEED = 1, PMUT = 0, MINRD = 50, TW = 400;   // TW: cycles per token window
    parameter integer U1_PSRAM = 1, U1_HQ2 = 0;
    reg clk = 0, rst_n = 1;
    initial #0.1 rst_n = 0;
    always #0.5 clk = ~clk;
    integer seed = SEED, cyc = 0, bad = 0, nrd = 0, nld = 0, nicut = 0, k, i;
    reg [11:0] pbase = 0;
    reg [15:0] xprog = 0, xrows = 0, lcnt = 0;
    reg [23:0] xacc = 0;
    reg  h_start = 0;
    reg [18-1:0] token = 0;
    reg [18-1:0] pos = 0;
    reg [11:0] prog_base = 0;
    reg  pw_v = 0;
    reg [9:0] pw_addr = 0;
    reg [63:0] pw_data = 0;
    reg [24-1:0] x_oacc = 0;
    reg  x_oidle = 0;
    reg [15:0] x_oprog = 0;
    reg [15:0] x_orows = 0;
    reg  kv_ok = 0;
    reg  kv_write_drained = 0;
    reg  me_mem_ok = 0;
    reg  up_fault = 0;
    reg [15:0] land_cnt = 0;
    reg  x_rdy = 0;
    reg [16-1:0] tr_fault = 0;
    reg [12*51-1:0] p_am = 0;
    reg [12-1:0] p_fault = 0;
    reg  fab_fault = 0;
    wire [24-1:0] me_acc_o_0, me_acc_o_1;
    wire  me_idle_o_0, me_idle_o_1;
    wire [15:0] me_prog_o_0, me_prog_o_1;
    wire  m_fin_o_0, m_fin_o_1;
    wire [18-1:0] m_fidx_o_0, m_fidx_o_1;
    wire [31:0] m_fval_o_0, m_fval_o_1;
    wire  kvd_v_0, kvd_v_1;
    wire [24-1:0] kvd_wbase_0, kvd_wbase_1;
    wire [24-1:0] kvd_ts_0, kvd_ts_1;
    wire [24-1:0] kvd_ks_0, kvd_ks_1;
    wire [24-1:0] kvd_js_0, kvd_js_1;
    wire [24-1:0] kvd_wcs_0, kvd_wcs_1;
    wire [3:0] kvd_split_0, kvd_split_1;
    wire [2:0] kvd_jsh_0, kvd_jsh_1;
    wire [18-1:0] kvd_tiles_0, kvd_tiles_1;
    wire [18-1:0] kvd_k_0, kvd_k_1;
    wire [18-1:0] kvd_nout_0, kvd_nout_1;
    wire  kvd_kindk_0, kvd_kindk_1;
    wire [18-1:0] kvd_pos_0, kvd_pos_1;
    wire  me_clk_en_0, me_clk_en_1;
    wire  c_fault_0, c_fault_1;
    wire  scale_re_0, scale_re_1;
    wire [48-1:0] scale_gre_0, scale_gre_1;
    wire [48*24-1:0] scale_addr_0, scale_addr_1;
    wire  x_dv_0, x_dv_1;
    wire [24-1:0] x_dc_0, x_dc_1;
    wire [24-1:0] x_dcs_0, x_dcs_1;
    wire [3:0] x_dsp_0, x_dsp_1;
    wire [13:0] t_sel_e_0, t_sel_e_1;
    wire [13:0] t_tv_e_0, t_tv_e_1;
    wire  p_v_e2_0, p_v_e2_1;
    wire [113-1:0] p_f_e2_0, p_f_e2_1;
    wire  ov_0, ov_1;
    wire  mx_we_0, mx_we_1;
    wire [24-1:0] mx_addr_0, mx_addr_1;
    wire [16-1:0] mx_mask_0, mx_mask_1;
    wire [16*32-1:0] mx_data_0, mx_data_1;
    ot_qfd_tt_ctlm_i #(.PSRAM(0), .PMUT(0), .HQ2(0)) u0 (
        .clk(clk), .rst_n(rst_n),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok(me_mem_ok),
        .up_fault(up_fault),
        .land_cnt(land_cnt),
        .x_rdy(x_rdy),
        .tr_fault(tr_fault),
        .p_am(p_am),
        .p_fault(p_fault),
        .fab_fault(fab_fault),
        .me_acc_o(me_acc_o_0),
        .me_idle_o(me_idle_o_0),
        .me_prog_o(me_prog_o_0),
        .m_fin_o(m_fin_o_0),
        .m_fidx_o(m_fidx_o_0),
        .m_fval_o(m_fval_o_0),
        .kvd_v(kvd_v_0),
        .kvd_wbase(kvd_wbase_0),
        .kvd_ts(kvd_ts_0),
        .kvd_ks(kvd_ks_0),
        .kvd_js(kvd_js_0),
        .kvd_wcs(kvd_wcs_0),
        .kvd_split(kvd_split_0),
        .kvd_jsh(kvd_jsh_0),
        .kvd_tiles(kvd_tiles_0),
        .kvd_k(kvd_k_0),
        .kvd_nout(kvd_nout_0),
        .kvd_kindk(kvd_kindk_0),
        .kvd_pos(kvd_pos_0),
        .me_clk_en(me_clk_en_0),
        .c_fault(c_fault_0),
        .scale_re(scale_re_0),
        .scale_gre(scale_gre_0),
        .scale_addr(scale_addr_0),
        .x_dv(x_dv_0),
        .x_dc(x_dc_0),
        .x_dcs(x_dcs_0),
        .x_dsp(x_dsp_0),
        .t_sel_e(t_sel_e_0),
        .t_tv_e(t_tv_e_0),
        .p_v_e2(p_v_e2_0),
        .p_f_e2(p_f_e2_0),
        .ov(ov_0),
        .mx_we(mx_we_0),
        .mx_addr(mx_addr_0),
        .mx_mask(mx_mask_0),
        .mx_data(mx_data_0));
    ot_qfd_tt_ctlm_i #(.PSRAM(U1_PSRAM), .PMUT(PMUT), .HQ2(U1_HQ2)) u1 (
        .clk(clk), .rst_n(rst_n),
        .h_start(h_start),
        .token(token),
        .pos(pos),
        .prog_base(prog_base),
        .pw_v(pw_v),
        .pw_addr(pw_addr),
        .pw_data(pw_data),
        .x_oacc(x_oacc),
        .x_oidle(x_oidle),
        .x_oprog(x_oprog),
        .x_orows(x_orows),
        .kv_ok(kv_ok),
        .kv_write_drained(kv_write_drained),
        .me_mem_ok(me_mem_ok),
        .up_fault(up_fault),
        .land_cnt(land_cnt),
        .x_rdy(x_rdy),
        .tr_fault(tr_fault),
        .p_am(p_am),
        .p_fault(p_fault),
        .fab_fault(fab_fault),
        .me_acc_o(me_acc_o_1),
        .me_idle_o(me_idle_o_1),
        .me_prog_o(me_prog_o_1),
        .m_fin_o(m_fin_o_1),
        .m_fidx_o(m_fidx_o_1),
        .m_fval_o(m_fval_o_1),
        .kvd_v(kvd_v_1),
        .kvd_wbase(kvd_wbase_1),
        .kvd_ts(kvd_ts_1),
        .kvd_ks(kvd_ks_1),
        .kvd_js(kvd_js_1),
        .kvd_wcs(kvd_wcs_1),
        .kvd_split(kvd_split_1),
        .kvd_jsh(kvd_jsh_1),
        .kvd_tiles(kvd_tiles_1),
        .kvd_k(kvd_k_1),
        .kvd_nout(kvd_nout_1),
        .kvd_kindk(kvd_kindk_1),
        .kvd_pos(kvd_pos_1),
        .me_clk_en(me_clk_en_1),
        .c_fault(c_fault_1),
        .scale_re(scale_re_1),
        .scale_gre(scale_gre_1),
        .scale_addr(scale_addr_1),
        .x_dv(x_dv_1),
        .x_dc(x_dc_1),
        .x_dcs(x_dcs_1),
        .x_dsp(x_dsp_1),
        .t_sel_e(t_sel_e_1),
        .t_tv_e(t_tv_e_1),
        .p_v_e2(p_v_e2_1),
        .p_f_e2(p_f_e2_1),
        .ov(ov_1),
        .mx_we(mx_we_1),
        .mx_addr(mx_addr_1),
        .mx_mask(mx_mask_1),
        .mx_data(mx_data_1));
    task automatic rand_inputs;
        begin
            token = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            pos = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            prog_base = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oacc = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oidle = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_oprog = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_orows = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            kv_ok = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            kv_write_drained = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            me_mem_ok = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            up_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            land_cnt = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            x_rdy = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            tr_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            p_am = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            p_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
            fab_fault = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
        end
    endtask
    wire out_mismatch = (me_acc_o_0 !== me_acc_o_1) || (me_idle_o_0 !== me_idle_o_1) || (me_prog_o_0 !== me_prog_o_1) || (m_fin_o_0 !== m_fin_o_1) || (m_fidx_o_0 !== m_fidx_o_1) || (m_fval_o_0 !== m_fval_o_1) || (kvd_v_0 !== kvd_v_1) || (kvd_wbase_0 !== kvd_wbase_1) || (kvd_ts_0 !== kvd_ts_1) || (kvd_ks_0 !== kvd_ks_1) || (kvd_js_0 !== kvd_js_1) || (kvd_wcs_0 !== kvd_wcs_1) || (kvd_split_0 !== kvd_split_1) || (kvd_jsh_0 !== kvd_jsh_1) || (kvd_tiles_0 !== kvd_tiles_1) || (kvd_k_0 !== kvd_k_1) || (kvd_nout_0 !== kvd_nout_1) || (kvd_kindk_0 !== kvd_kindk_1) || (kvd_pos_0 !== kvd_pos_1) || (me_clk_en_0 !== me_clk_en_1) || (c_fault_0 !== c_fault_1) || (scale_re_0 !== scale_re_1) || (scale_gre_0 !== scale_gre_1) || (scale_addr_0 !== scale_addr_1) || (x_dv_0 !== x_dv_1) || (x_dc_0 !== x_dc_1) || (x_dcs_0 !== x_dcs_1) || (x_dsp_0 !== x_dsp_1) || (t_sel_e_0 !== t_sel_e_1) || (t_tv_e_0 !== t_tv_e_1) || (p_v_e2_0 !== p_v_e2_1) || (p_f_e2_0 !== p_f_e2_1) || (ov_0 !== ov_1) || (mx_we_0 !== mx_we_1) || (mx_addr_0 !== mx_addr_1) || (mx_mask_0 !== mx_mask_1) || (mx_data_0 !== mx_data_1);
    wire pq_mismatch = (u0.prog_q !== u1.prog_q);
    initial begin
        seed = SEED;   // the 5.050 simulator ignores the declaration initialiser for $random's seed: every SEED ran one stream
        repeat (6) @(posedge clk);
        rst_n = 1;
        repeat (6) @(posedge clk);
        // boot load: the program store (64 words x 16 slices) while the controller is idle
        for (k = 0; k < 1024; k = k + 1) begin
            @(negedge clk); pw_v = 1; pw_addr = k; pw_data = {$random(seed), $random(seed)};
            if (k % 16 == 0) begin         // slice 0: unit / barrier / chase / waits biased toward progress (barrier / chase / waits rare)
                // mostly SU ops (the other unit: they skip, so the fetch FIFO / head / store reads run at full rate), some ME
                // ops (this unit: issue; an ME op of the real ot_qfd_tt_ctl can hold the unit busy for the rest of the token),
                // rare END
                pw_data[1:0] = (($random(seed) & 31) == 0) ? 2'd0 : (($random(seed) & 15) == 0) ? 2'd1 : 2'd2;
                pw_data[3:2] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                pw_data[21:20] = (($random(seed) & 7) == 0) ? 2'($random(seed)) : 2'd0;
                // ME op sizes small (NOUT [38:23], TILES [54:39], K [70:55]) so an ME op finishes within a token
                pw_data[38:23] = 16'(1 + ($random(seed) & 3)); pw_data[54:39] = 16'(1 + ($random(seed) & 3));
                pw_data[63:55] = 9'(1 + ($random(seed) & 3));
            end
            if (k % 16 == 1) pw_data[6:0] = 7'd0;            // K [70:64]
            if (k % 16 == 3) pw_data[44:27] = 18'd0;         // the ME DYN selectors D_* [236:219]: static sizes / bases
        end
        @(negedge clk); pw_v = 0;
        repeat (8) @(posedge clk);
        for (i = 0; i < NCYC; i = i + 1) begin
            @(negedge clk);
            rand_inputs;
            // status inputs follow the ICUT contract (readiness never falls without the unit's own go; the other
            // unit's accepted-op count, progress and landings only climb)
            kv_ok = 1; kv_write_drained = 1; me_mem_ok = 1; x_oidle = 1; x_rdy = 1;
            // the other unit's progress counters only climb within a token (chase compares never fall)
            if ((i % TW) == 0) begin xprog = 0; xrows = 0; xacc = 0; end
            else begin
                xprog = xprog + 16'(($random(seed) & 7) == 0); xrows = xrows + 16'(($random(seed) & 7) == 0);
                xacc = xacc + 24'(($random(seed) & 3) == 0);   // the other unit accepts its ops (count only climbs)
            end
            x_oacc = xacc;
            x_oprog = xprog; x_orows = xrows;
            land_cnt = lcnt; lcnt = ((i % TW) == 0) ? 16'd0 : lcnt + 16'd1;   // landings only climb (one a cycle: the memory keeps up)
            up_fault = 0; tr_fault = 0; p_fault = 0; fab_fault = 0;
            if ((i % TW) == 0) pbase = 12'($random(seed)) % 48;
            prog_base = pbase;   // held for the token (the die holds it); runs past word 63 read the out-of-store zeros
            rst_n = (i % TW) < TW - 8;                 // an 8-cycle reset every 400 cycles restarts the controller (store kept)
            h_start = (i % TW) == 12;
        end
        @(negedge clk); h_start = 0;
        repeat (20) @(posedge clk);
        if (bad == 0 && nrd >= MINRD) $display("PASS tt_ctlm_i_psram cycles=%0d program_reads=%0d loads=%0d icut_stim=%0d", cyc, nrd, nld, nicut);
        else $display("FAIL tt_ctlm_i_psram mismatches=%0d program_reads=%0d (min %0d) loads=%0d", bad, nrd, MINRD, nld);
        $finish;
    end
    // coverage note: where the controller waits when each token's window closes (cycle 390 of 400)
    always @(posedge clk) if (rst_n && ((i % TW) == TW - 10) && (i < 5 * TW))
        $display("WAITSTATE i=%0d st=%0d nx_v=%b unit=%0d ur=%b mr=%b men=%b xdep=%b bar=%b ch=%b wu=%b wo=%b oi=%b od=%b",
            i, u0.u_ctrl_me.st, u0.u_ctrl_me.nx_v, u0.u_ctrl_me.d_unit, u0.u_ctrl_me.unit_ready, u0.u_ctrl_me.me_ready,
            u0.u_ctrl_me.me_en, u0.u_ctrl_me.xdep_ok, u0.u_ctrl_me.d_barrier, u0.u_ctrl_me.d_chase, u0.u_ctrl_me.wait_u,
            u0.u_ctrl_me.wait_o, u0.u_ctrl_me.own_idle, u0.u_ctrl_me.o_drained);
    always @(posedge clk) if (rst_n) begin
        cyc = cyc + 1;
        if (u0.prog_re_r) nrd = nrd + 1;
        if ($isunknown({u0.u_ctrl_me.st, u0.u_ctrl_me.fq_n, u0.u_ctrl_me.nx_v, u0.u_ctrl_me.issue, u0.u_ctrl_me.load, u1.u_ctrl_me.issue, u1.u_ctrl_me.load})) begin
            bad = bad + 1;
            if (bad <= 5) $display("XSTATE cyc=%0d", cyc);
        end
        if (u0.u_ctrl_me.load) nld = nld + 1;
        if (u0.u_ctrl_me.issue && !u0.u_ctrl_me.issue_live) nicut = nicut + 1;
        if (out_mismatch || pq_mismatch) begin
            bad = bad + 1;
            if (bad <= 5) $display("MISMATCH cyc=%0d outputs=%b prog_q=%b", cyc, out_mismatch, pq_mismatch);
        end
    end
endmodule
