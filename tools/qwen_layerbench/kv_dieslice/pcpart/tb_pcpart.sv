`timescale 1ns/1ps
// KV-TOK 10-24: flat sub-bench of ONE bound pc partition (kv3_pc_part = pc_EN_0, the chain head: 4 HOST slices +
// 4 kvpc PC paths) with the HBM PHY bench model on its 4 PCs.  Purpose: see INSIDE the cold-boot scratch check that the
// whole-die bench (protect-lib blocks, opaque) shows timing out (all 128 slices done/ok 0/fault at core cycle ~20590).
// Drives: core clk / hbm clk as tb_kvslice; arst_n; HOST host_rst_n / hbm_rst_n lanes; one bgi pulse; the kvpc reset
// spine ri_kvpc0_rst_n either = die_rst_n (held low, as the HOST does until every slice reports boot done; default) or
// = hbm_rst_n (+KVPC_RST_HBM).  Every other input 0 (embgw est 0 = boot window).  Prints the boot-check state, the
// slice word at each stage (slice ctrl_es -> es_merge hq/es -> PHY po) and the slice status.
module tb_pcpart;
    // +HCK_IS_CLK (diagnostic, KV-TOK B): the HBM clock IS the core clock, so the partition's PHY po/pi boundary lanes
    // (ot_dp_st on the core clock clk although po/pi live in the HBM domain -- a bind clock-domain finding) carry each
    // HBM-domain beat exactly once; default = the real 0.977 GHz HBM clock.
    // TOK-QK/D: +DFI_CORE (owner decision 14, apply_D dfi-core) = the same single clock as +HCK_IS_CLK.  Phase / rate sweep
    // of the real HBM clock: +HCK_HALF_PS=<half period ps, default 512> +HCK_PHASE_PS=<first-edge offset ps, default 0>.
    reg clk = 0, hck_r = 0; always #0.416667 clk = ~clk;
    real hck_half = 0.512, hck_ph = 0.0;
    initial begin : hgen
        integer v;
        if ($value$plusargs("HCK_HALF_PS=%d", v)) hck_half = v / 1000.0;
        if ($value$plusargs("HCK_PHASE_PS=%d", v)) hck_ph = v / 1000.0;
        $display("PCB HCK half %0.3f ns phase %0.3f ns%s", hck_half, hck_ph,
                 ($test$plusargs("HCK_IS_CLK") || $test$plusargs("DFI_CORE")) ? " (unused: single clock)" : "");
        #(hck_ph);
        forever #(hck_half) hck_r = ~hck_r;
    end
    wire hck = ($test$plusargs("HCK_IS_CLK") || $test$plusargs("DFI_CORE")) ? clk : hck_r;
    reg arst_n = 0, hbm_rn = 0, host_rn = 0, die_rn = 0, bg = 0;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    wire [328:0] po0, po1, po2, po3; wire [288:0] pi0, pi1, pi2, pi3; wire [3:0] fh0, fh1, fh2, fh3, rh0, rh1, rh2, rh3;
    wire [32:0] sdo, soo, sfo; wire kvrst = $test$plusargs("KVPC_RST_HBM") ? hbm_rn : die_rn;
    kv3_pc_part dut(.clk(clk), .arst_n(arst_n), .clk_clk_hbm(hck),
        .i_ectl_Q_N_kf(2'd0), .i_ectl_Q_N_rq(39'd0), .i_embgw_est(14'd0), .i_fch_pc_Q_N_q(2'd0),
        .i_host_hbm_rst_n({arst_n, hbm_rn}), .i_host_host_rst_n({arst_n, host_rn}), .i_hsl_Q_N_bgo({arst_n, bg}),
        .i_hsl_Q_N_fo(292'd0), .i_idhr_Q_y(3'd0), .i_kvpc_Q_N_o_prev(781'd0), .i_kvpc_Q_N_pc__ko(34'd0),
        .i_kvs_emb_px_tep(17'd0), .i_kvs_emb_px_tok(19'd0),
        .i_phy_Q__sN_fhN({1'b1, fh3, fh2, fh1, fh0}), .i_phy_Q__sN_rhN({1'b1, rh3, rh2, rh1, rh0}),
        .i_phy_Q__sN_piN({1'b1, pi0}), .i_phy_Q__sN_piN_d1({1'b1, pi1}), .i_phy_Q__sN_piN_d2({1'b1, pi2}),
        .i_phy_Q__sN_piN_d3({1'b1, pi3}), .i_slg_Q_N_o_dn(272'd0), .i_vport_Q_N_f(2'd0), .i_vport_Q_N_vqN(16'd0),
        .o_fch_pc_Q_N_q(), .o_hsl_Q_N_ao(), .o_hsl_Q_N_co(), .o_hsl_Q_N_fault_o(), .o_hsl_Q_N_sdo(sdo), .o_hsl_Q_N_sfo(sfo),
        .o_hsl_Q_N_sko(), .o_hsl_Q_N_soo(soo), .o_idpc_Q_N_y(), .o_kvpc_Q_N_o_next(), .o_kvpc_Q_N_pc__fo(),
        .o_kvpc_Q_N_pc__po(po0), .o_kvpc_Q_N_pc__po_d1(po1), .o_kvpc_Q_N_pc__po_d2(po2), .o_kvpc_Q_N_pc__po_d3(po3),
        .o_slg_Q_N_af__fault(), .o_slg_Q_N_krsp(), .o_slg_Q_N_o_ctl(), .o_slg_Q_N_rsp(), .ri_kvpc0_rst_n(kvrst));
    qkd_hbm3e_phy_pc4 #(.PRELOAD_ID(0)) u_phy(.clk(hck), .rst_n(hbm_rn), .pi0(pi0), .pi1(pi1), .pi2(pi2), .pi3(pi3),
        .po0(po0[327:0]), .po1(po1[327:0]), .po2(po2[327:0]), .po3(po3[327:0]),
        .fh0(fh0), .fh1(fh1), .fh2(fh2), .fh3(fh3), .rh0(rh0), .rh1(rh1), .rh2(rh2), .rh3(rh3));
    // stage observation, PC 0 (u_hsl0 -> u_kvpc0)
    wire [2:0] st = dut.u_hsl0.u_slice.u_boot.u_boot.u_test.state;
    wire       s_es = dut.u_hsl0.ctrl_es[0];
    wire       m_own = dut.u_kvpc0.u_pc.u_pce.u_esm.own, m_hq = dut.u_kvpc0.u_pc.u_pce.u_esm.hq[0],
               m_es = dut.u_kvpc0.u_pc.u_pce.u_esm.es[0], m_f = dut.u_kvpc0.u_pc.u_pce.u_esm.m_fault,
               m_rs = dut.u_kvpc0.u_pc.u_pce.u_esm.rs_q;
    wire [260:0] her = dut.u_kvpc0.u_pc.u_pce.u_esm.her;
    reg [2:0] st_q = 7; reg [7:0] ev_q = 0;
    wire [7:0] ev = {s_es, m_hq, m_es, po0[28], her[259], her[0], her[260], m_f};
    always @(posedge clk) begin
        st_q <= st; ev_q <= ev;
        if (st != st_q) $display("PCB cyc %0d boot_pc state %0d (own %b merge_rs %b) done %b ok %b cause %0d", cyc, st, m_own, m_rs,
                                 dut.u_hsl0.u_slice.u_boot.u_boot.u_test.done, dut.u_hsl0.u_slice.u_boot.u_boot.u_test.ok,
                                 dut.u_hsl0.u_slice.u_boot.u_boot.u_test.cause);
        if (ev != ev_q && ev != 0) $display("PCB cyc %0d slice_es %b merge_hq %b merge_es %b po0_col %b her_credit %b her_rd %b her_fault %b merge_fault %b",
                                            cyc, ev[7], ev[6], ev[5], ev[4], ev[3], ev[2], ev[1], ev[0]);
    end
    // controller face (u_path = qkd_static_kv_pc_path_nc): es into the controller, calendar reservations (hbm clock)
    wire c_es = dut.u_kvpc0.u_pc.u_pce.u_path.es[0];
    wire c_rsc = dut.u_kvpc0.u_pc.u_pce.u_path.reserved_static_col, c_rwc = dut.u_kvpc0.u_pc.u_pce.u_path.reserved_write_col,
         c_rrd = dut.u_kvpc0.u_pc.u_pce.u_path.reserved_rd, c_go = dut.u_kvpc0.u_pc.u_pce.u_path.cal_go,
         c_seal = dut.u_kvpc0.u_pc.u_pce.u_path.cal_seal;
    integer n_ces = 0, n_rsc = 0, n_rwc = 0, n_rrd = 0, n_go = 0;
    always @(posedge clk) if (c_es) begin n_ces <= n_ces + 1; $display("PCB cyc %0d controller es[0] (static word in)", cyc); end
    always @(posedge hck) begin n_rsc <= n_rsc + c_rsc; n_rwc <= n_rwc + c_rwc; n_rrd <= n_rrd + c_rrd; n_go <= n_go + c_go; end
    final $display("PCB CAL controller_es %0d reserved_static_col %0d reserved_write_col %0d reserved_rd %0d cal_go %0d cal_seal %b",
                   n_ces, n_rsc, n_rwc, n_rrd, n_go, c_seal);
`ifndef PCB_ORIG
    // KV-TOK B: controller boot window (qkd_ctrl_pc_sched_nc boot_win / col_boot), PC 0 path; HBM-clock PHY columns
    wire b_win = dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.boot_win, b_col = dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.col_boot;
    integer n_bcol = 0;
    always @(posedge hck) if (b_col) begin n_bcol <= n_bcol + 1; $display("PCB cyc %0d boot column (no reservation) we %b", cyc,
                                                  dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.col_we); end
    final $display("PCB BOOTWIN boot_win %b boot_columns %0d", b_win, n_bcol);
    // every PC of the partition (u_kvpc0 head + u_kvpc1..3): controller static words in, boot columns, faults
`define PCB_PC(i, P) \
    integer n_cv``i = 0, n_bc``i = 0; \
    always @(posedge hck) begin if (P.u_ctrl.u_sched.c_v) n_cv``i <= n_cv``i + 1; if (P.u_ctrl.u_sched.col_boot) n_bc``i <= n_bc``i + 1; end \
    final $display("PCB PC%0d c_v %0d boot_columns %0d boot_win %b hgo %b fo %b f_raw %b obs %b ctl %b f_cmd %b f_early %b f_ecdc %b", i, n_cv``i, n_bc``i, \
        P.u_ctrl.u_sched.boot_win, P.u_ctrl.u_sched.hgo, P.u_ctrl.u_sched.fo, P.u_ctrl.u_sched.f_raw, P.u_ctrl.u_sched.native_observer_fault, \
        P.u_ctrl.u_sched.ctl_fault, P.u_ctrl.u_sched.f_cmd, P.u_ctrl.u_sched.f_early, P.u_ctrl.u_sched.f_ecdc);
    // raw PHY return valid at the PHY model (pi<k>[0], hck) vs at each controller's pin flop (rv_q): a return must
    // arrive exactly once per RD (the partition po/pi lanes are bound to the core clock clk -- see KV-TOK B report)
`define PCB_RV(i, P, PI) \
    integer n_pi``i = 0, n_rv``i = 0; \
    always @(posedge hck) begin if (PI[0]) n_pi``i <= n_pi``i + 1; if (P.u_ctrl.u_sched.rv_q) begin n_rv``i <= n_rv``i + 1; \
        $display("PCB cyc %0d PC%0d rv_q raw_out %0d raw_nom %b", cyc, i, P.u_ctrl.u_sched.raw_out, P.u_ctrl.u_sched.raw_nom); end end \
    final $display("PCB PC%0d phy_pi_valid %0d controller_rv %0d", i, n_pi``i, n_rv``i);
    `PCB_RV(0, dut.u_kvpc0.u_pc.u_pce.u_path, pi0)
    `PCB_RV(1, dut.u_kvpc1.u_pc.u_pce.u_path, pi1)
    `PCB_RV(2, dut.u_kvpc2.u_pc.u_pce.u_path, pi2)
    `PCB_RV(3, dut.u_kvpc3.u_pc.u_pce.u_path, pi3)
    `PCB_PC(0, dut.u_kvpc0.u_pc.u_pce.u_path)
    `PCB_PC(1, dut.u_kvpc1.u_pc.u_pce.u_path)
    `PCB_PC(2, dut.u_kvpc2.u_pc.u_pce.u_path)
    `PCB_PC(3, dut.u_kvpc3.u_pc.u_pce.u_path)
`endif
    wire [2:0] st1 = dut.u_hsl1.u_slice.u_boot.u_boot.u_test.state, st3 = dut.u_hsl3.u_slice.u_boot.u_boot.u_test.state;
    reg [2:0] st1_q = 7, st3_q = 7;
    always @(posedge clk) begin st1_q <= st1; st3_q <= st3;
        if (st1 != st1_q) $display("PCB cyc %0d slice1 boot_pc state %0d", cyc, st1);
        if (st3 != st3_q) $display("PCB cyc %0d slice3 boot_pc state %0d", cyc, st3); end
    always @(posedge hck) if (po0[28]) $display("PCB cyc %0d PHY col pc0 we %b bank %0d col %0d", cyc, po0[29], po0[34:30], po0[39:35]);
    final $display("PCB FAULTS pc0 fo %b f_raw %b obs %b ctl %b f_cmd %b f_early %b",
                   dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.fo, dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.f_raw,
                   dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.native_observer_fault, dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.ctl_fault,
                   dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.f_cmd, dut.u_kvpc0.u_pc.u_pce.u_path.u_ctrl.u_sched.f_early);
    reg [32:0] sd_q = 0;
    always @(posedge clk) begin sd_q <= sdo; if (sdo != sd_q) $display("PCB cyc %0d sdo %b soo %b sfo %b", cyc, sdo[3:0], soo[3:0], sfo[3:0]); end
    integer maxc = 25000;
    initial begin
        void'($value$plusargs("MAXCYC=%d", maxc));
        repeat (20) @(posedge clk); arst_n = 1;
        repeat (20) @(posedge clk); host_rn = 1;
        repeat (100) @(posedge clk); hbm_rn = 1;
        repeat (40) @(posedge clk); bg = 1; @(posedge clk); bg = 0;
        $display("PCB cyc %0d boot_go pulse (kvpc reset = %s)", cyc, $test$plusargs("KVPC_RST_HBM") ? "hbm_rst_n" : "die_rst_n (held)");
        while (cyc < maxc) @(posedge clk);
        $display("PCB END cyc %0d sdo %b soo %b sfo %b", cyc, sdo[3:0], soo[3:0], sfo[3:0]);
        $finish;
    end
endmodule
