`timescale 1ns/1ps
// DIE-QC-59Q 2026-11-01: QC compute face u_cseq (qfd_sysface_cseq_single) on the as-built die path vs the proven
// kvs_compute_end reference, same pair image (d2d_cal_image_qc_pair.svh, C half).
//   REF: ot_qwen_d2d_cal_seq (ADM 1, AUTO 1, EP_SKEW 0) -> qfd_d2d_static PR 1 TXDP_C, direct (= kvs_compute_end u_cseq/u_c)
//   DUT: fwd_epoch -> wrapper input capture (1) -> qfd_sysface_cseq_single (CTL_PAD / CS_EP_SKEW as in the core) ->
//        wrapper output register (1) -> glue ot_dp_dly at the as-built bindC depths -> qfd_d2d_static_ovl_sf7_obs1
//        #(HEAD_CONTEXT 1, TXDP_C) (= glue u_d2d_rom); both masters see the same fwd_epoch pin.
// Bench-only: both ends' link-abort / end-fault are forced 0 (no far end / producers here), so the two calendars play
// the whole programme; the far-end proof is kvs_compute_end vs the KV die (KV-FN-7) and TOK-QK-2's pair vehicle.
// Check every edge: TX slot/kind/beat, capture fire, RX slot/kind/beat of the two link ends identical; DUT tx/rx_user 0;
// no calendar / sequencer fault; event counts.  Plusargs: +PAD0 (mutant: CTL_PAD 0 = main's as-built skew), +SKEW0.
module tb_qc59q;
`ifdef MUT_PAD0
    localparam [63:0] PAD = 64'd0;
`else
    localparam [63:0] PAD = {8'd0, 8'd1, 8'd1, 8'd2, 8'd2, 8'd3, 8'd3, 8'd2};
`endif
`ifdef MUT_SKEW0
    localparam integer SKW = 0;
`else
    localparam integer SKW = -9;
`endif
    `include "d2d_cal_image_qc_pair.svh"
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst_n = 0, F = 0;
    integer cyc = 0;
    always @(posedge ck) cyc <= cyc + 1;
    // ---------------- REF
    wire r_tx, r_rx, r_cs, r_sg, r_rdy, r_run, r_ad, r_ts, r_f; wire [5:0] r_a, r_l; wire [31:0] r_d;
    ot_qwen_d2d_cal_seq #(.TX_IMG(D2D_CAL_C_TX_IMG), .RX_IMG(D2D_CAL_C_RX_IMG), .TX_SEG1(D2D_CAL_C_TX_SEG1),
        .RX_SEG1(D2D_CAL_C_RX_SEG1), .START(D2D_CAL_START), .ADM(1), .TX_SEG2(D2D_CAL_C_TX_SEG2), .RX_SEG2(D2D_CAL_C_RX_SEG2),
        .ADM_OFS(D2D_ADM_OFS), .ADM_LEN(D2D_ADM_LEN), .AUTO(1), .FIRST_OFS(D2D_FIRST_TOKEN), .PERIOD(D2D_TOKEN_PERIOD),
        .EP_SKEW(0)) r_seq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .tok_go(1'b0), .epoch_go(F), .halt(1'b0),
        .cfg_tx_we(r_tx), .cfg_rx_we(r_rx), .cfg_addr(r_a), .cfg_data(r_d), .cal_start(r_cs), .cal_seg(r_sg),
        .cal_ready(r_rdy), .running(r_run), .layer(r_l), .adm_done(r_ad), .tok_start(r_ts), .fault(r_f));
    qfd_d2d_static #(.MUT(0), .PR(1), .TXDP(D2D_TXDP_C)) r_m (.ck(ck), .por_n(rst_n), .rst_n(rst_n),
        .cfg_tx_we(r_tx), .cfg_rx_we(r_rx), .cfg_addr(r_a), .cfg_data(r_d), .cal_start(r_cs), .cal_seg(r_sg),
        .fwd_epoch(F), .fwd_link_rst_n(1'b1), .native_tx_slot(), .native_tx_slot_kind(), .native_tx_slot_beat(),
        .native_tx_v(1'b0), .native_tx_payload(548'd0), .rx_payload(), .native_rx_v(), .native_rx_slot(),
        .native_rx_slot_kind(), .native_rx_slot_beat(), .prog_witness_slot(), .prog_auth_slot(), .prog_context_slot(),
        .prog_tx_observed_v(1'b0), .prog_tx_record(548'd0), .prog_rx_v(), .emb_rx_v(), .emb_rx_slot(),
        .kv_x3_slot(), .x3(524'd0), .x3_identity(59'd0), .x3_generation(2'd0),
        .status_epoch16(16'd0), .vm_drained(1'b1), .collective_drained(1'b1), .collective_busy(1'b0),
        .crom_fault(1'b0), .execution_active(1'b0), .admit_ready(1'b1), .result_v(1'b0), .result_done(1'b0),
        .result_fault(1'b0), .result_cause(4'd0), .result_tag(59'd0), .result_gen(2'd0), .result_token(18'd0),
        .result_value(32'd0), .result_cycles(32'd0), .fdi_tx_up(1'b1), .fdi_tx_v(), .fdi_tx_flit(), .fdi_rx_v(1'b0),
        .fdi_rx_flit(583'd0), .phy_rst_n(), .epoch_abort(), .transport_fault(), .fault());
    // ---------------- DUT
    reg Fq = 0; always @(posedge ck) Fq <= F;                       // wrapper input capture
    wire d_tx, d_rx, d_cs, d_sg, d_csr, d_sgr, d_rdy, d_run, d_ad, d_ss, d_f; wire [1:0] d_ut, d_ur;
    wire [5:0] d_a, d_l; wire [31:0] d_d;
    qfd_sysface_cseq_single #(.CTL_PAD(PAD), .CS_EP_SKEW(SKW)) u_cseq (.ck(ck), .rst_n(rst_n), .reload(1'b0),
        .epoch_go(Fq), .halt(1'b0), .cfg_tx_we(d_tx), .cfg_rx_we(d_rx), .cfg_addr(d_a), .cfg_data(d_d),
        .cal_start(d_cs), .cal_seg(d_sg), .cal_start_rx(d_csr), .cal_seg_rx(d_sgr), .cal_user_tx(d_ut),
        .cal_user_rx(d_ur), .cal_ready(d_rdy), .running(d_run), .layer(d_l), .adm_done(d_ad), .seq_start(d_ss),
        .fault(d_f));
    // wrapper output registers
    reg w_tx, w_rx, w_cs, w_sg, w_csr, w_sgr; reg [1:0] w_ut, w_ur; reg [5:0] w_a; reg [31:0] w_d;
    always @(posedge ck) begin w_tx <= d_tx; w_rx <= d_rx; w_cs <= d_cs; w_sg <= d_sg; w_csr <= d_csr; w_sgr <= d_sgr;
        w_ut <= d_ut; w_ur <= d_ur; w_a <= d_a; w_d <= d_d; end
    // glue relays at the as-built (bindC qfd_qc_glue_part.sv:1844-1853) depths
    wire g_tx, g_rx, g_cs, g_sg, g_csr, g_sgr; wire [1:0] g_ut, g_ur; wire [5:0] g_a; wire [31:0] g_d;
    ot_dp_dly #(.W(1), .D(6)) u_d6_cal_seg (.clk(ck), .d(w_sg), .q(g_sg));
    ot_dp_dly #(.W(1), .D(7)) u_d7_cal_seg_rx (.clk(ck), .d(w_sgr), .q(g_sgr));
    ot_dp_dly #(.W(1), .D(5)) u_d5_cal_start (.clk(ck), .d(w_cs), .q(g_cs));
    ot_dp_dly #(.W(1), .D(6)) u_d6_cal_start_rx (.clk(ck), .d(w_csr), .q(g_csr));
    ot_dp_dly #(.W(2), .D(7)) u_d7_cal_user_rx (.clk(ck), .d(w_ur), .q(g_ur));
    ot_dp_dly #(.W(2), .D(7)) u_d7_cal_user_tx (.clk(ck), .d(w_ut), .q(g_ut));
    ot_dp_dly #(.W(6), .D(4)) u_d4_cfg_addr (.clk(ck), .d(w_a), .q(g_a));
    ot_dp_dly #(.W(32), .D(5)) u_d5_cfg_data (.clk(ck), .d(w_d), .q(g_d));
    ot_dp_dly #(.W(1), .D(4)) u_d4_cfg_rx_we (.clk(ck), .d(w_rx), .q(g_rx));
    ot_dp_dly #(.W(1), .D(5)) u_d5_cfg_tx_we (.clk(ck), .d(w_tx), .q(g_tx));
    wire [1:0] m_tu, m_ru;
    qfd_d2d_static_ovl_sf7_obs1 #(.HEAD_CONTEXT(1), .TXDP(D2D_TXDP_C)) d_m (.obs_ctx(62'd0), .obs_res(47'd0),
        .obs_native(60'd0), .ck(ck), .por_n(rst_n), .rst_n(rst_n),
        .cfg_tx_we(g_tx), .cfg_rx_we(g_rx), .cfg_addr(g_a), .cfg_data(g_d), .cal_start(g_cs), .cal_seg(g_sg),
        .cal_start_rx(g_csr), .cal_seg_rx(g_sgr), .cal_user_tx(g_ut), .cal_user_rx(g_ur), .tx_user(m_tu), .rx_user(m_ru),
        .fwd_epoch(F), .fwd_link_rst_n(1'b1), .native_tx_slot(), .native_tx_slot_kind(), .native_tx_slot_beat(),
        .native_tx_v(1'b0), .native_tx_payload(548'd0), .rx_payload(), .native_rx_v(), .native_rx_slot(),
        .native_rx_slot_kind(), .native_rx_slot_beat(), .prog_witness_slot(), .prog_head_context_slot(),
        .prog_auth_slot(), .prog_context_slot(), .prog_tx_observed_v(1'b0), .prog_tx_record(548'd0), .prog_rx_v(),
        .emb_rx_v(), .emb_rx_slot(), .kv_x3_slot(), .x3(524'd0), .x3_identity(59'd0), .x3_generation(2'd0),
        .status_epoch16(16'd0), .vm_drained(1'b1), .collective_drained(1'b1), .collective_busy(1'b0),
        .crom_fault(1'b0), .execution_active(1'b0), .admit_ready(1'b1), .result_v(1'b0), .result_done(1'b0),
        .result_fault(1'b0), .result_cause(4'd0), .result_tag(59'd0), .result_gen(2'd0), .result_token(18'd0),
        .result_value(32'd0), .result_cycles(32'd0), .fdi_tx_up(1'b1), .fdi_tx_v(), .fdi_tx_flit(), .fdi_rx_v(1'b0),
        .fdi_rx_flit(583'd0), .phy_rst_n(), .epoch_abort(), .transport_fault(), .fault());
    // bench-only: no far end / producers -> keep both link ends out of abort so the calendars play the whole programme
    initial begin
        force r_m.u_core.u_end.epoch_abort = 1'b0; force r_m.u_core.u_end.end_fault = 1'b0;
        force d_m.u_core.u_end.epoch_abort = 1'b0; force d_m.u_core.u_end.end_fault = 1'b0;
    end
    // ---------------- compare
    wire [3:0] rts = r_m.u_core.u_end.tx_slot, dts = d_m.u_core.u_end.tx_slot;
    wire [3:0] rtk = r_m.u_core.u_end.tx_kind, dtk = d_m.u_core.u_end.tx_kind;
    wire [4:0] rtb = r_m.u_core.u_end.tx_beat, dtb = d_m.u_core.u_end.tx_beat;
    wire [3:0] rfi = r_m.u_core.u_end.fire, dfi = d_m.u_core.u_end.fire;
    wire [3:0] rrs = r_m.u_core.u_end.rx_slot, drs = d_m.u_core.u_end.rx_slot;
    wire [3:0] rrk = r_m.u_core.u_end.rx_kind, drk = d_m.u_core.u_end.rx_kind;
    wire [4:0] rrb = r_m.u_core.u_end.rx_beat, drb = d_m.u_core.u_end.rx_beat;
    // calendar event streams (the RX calendar plays without a far end; rx_slot needs received frames)
    wire [12:0] rce = {r_m.u_core.u_end.rv, r_m.u_core.u_end.rp, r_m.u_core.u_end.rk, r_m.u_core.u_end.rb};
    wire [12:0] dce = {d_m.u_core.u_end.rv, d_m.u_core.u_end.rp, d_m.u_core.u_end.rk, d_m.u_core.u_end.rb};
    wire [12:0] rte = {r_m.u_core.u_end.tv, r_m.u_core.u_end.tp, r_m.u_core.u_end.tk, r_m.u_core.u_end.tb};
    wire [12:0] dte = {d_m.u_core.u_end.tv, d_m.u_core.u_end.tp, d_m.u_core.u_end.tk, d_m.u_core.u_end.tb};
    integer nrxc = 0, ntxc = 0, cmism = 0;
    always @(posedge ck) if (rst_n) begin
        if ((rce[12] ? rce : 13'd0) !== (dce[12] ? dce : 13'd0) || (rte[12] ? rte : 13'd0) !== (dte[12] ? dte : 13'd0)) begin
            if (cmism < 10) $display("CALMIS cyc %0d ref rx %h tx %h | dut rx %h tx %h", cyc, rce, rte, dce, dte);
            cmism = cmism + 1;
        end
        if (rce[12]) nrxc = nrxc + 1;
        if (rte[12]) ntxc = ntxc + 1;
    end
    wire r_cf = r_m.u_core.u_end.tf | r_m.u_core.u_end.rf, d_cf = d_m.u_core.u_end.tf | d_m.u_core.u_end.rf;
    integer mism = 0, ntx = 0, nrx = 0, nfire = 0, nst = 0, nst_d = 0, nuser = 0, first_mis = -1;
    integer r_cff = -1, d_cff = -1, r_sf = -1, d_sf = -1, ntok = 0, nadm = 0;
    always @(posedge ck) if (rst_n) begin
        if ({rts, rtk & {4{|rts}}, rtb & {5{|rts}}, rfi, rrs, rrk & {4{|rrs}}, rrb & {5{|rrs}}} !==
            {dts, dtk & {4{|dts}}, dtb & {5{|dts}}, dfi, drs, drk & {4{|drs}}, drb & {5{|drs}}}) begin
            if (mism < 10) $display("MISMATCH cyc %0d ref ts %b k %0d b %0d fire %b rs %b k %0d b %0d | dut ts %b k %0d b %0d fire %b rs %b k %0d b %0d",
                cyc, rts, rtk, rtb, rfi, rrs, rrk, rrb, dts, dtk, dtb, dfi, drs, drk, drb);
            if (first_mis < 0) first_mis = cyc;
            mism = mism + 1;
        end
        if (|rts) ntx = ntx + 1;
        if (|rrs) nrx = nrx + 1;
        if (|rfi) nfire = nfire + 1;
        if (r_cs) nst = nst + 1;
        if (r_cs && r_l == 6'h3f) nadm = nadm + 1;
        if (r_ts) ntok = ntok + 1;
        if (d_ss) nst_d = nst_d + 1;
        if (m_tu != 0 || m_ru != 0 || d_ut != 0 || d_ur != 0) nuser = nuser + 1;
        if (r_cf && r_cff < 0) r_cff = cyc;
        if (d_cf && d_cff < 0) d_cff = cyc;
        if (r_f && r_sf < 0) r_sf = cyc;
        if (d_f && d_sf < 0) d_sf = cyc;
    end
    integer NC, E2;
    initial begin
        if (!$value$plusargs("NC=%d", NC)) NC = 640000;
        if (!$value$plusargs("E2=%d", E2)) E2 = 0;     // optional second epoch (re-anchor) at this cycle
        repeat (20) @(posedge ck); rst_n = 1;
        repeat (180) @(posedge ck); F = 1;
        $display("EPOCH1 cyc %0d", cyc);
        if (E2 > 0) begin
            wait (cyc == E2); F = 0; repeat (20) @(posedge ck); F = 1; $display("EPOCH2 cyc %0d", cyc);
        end
        wait (cyc == NC);
        $display("RESULT pad %h skew %0d mism %0d first_mis %0d | ref tx_ev %0d rx_ev %0d fire %0d cal_starts %0d adm %0d tok_starts %0d | dut seq_starts %0d user_nonzero %0d | cal_fault ref %0d dut %0d | seq_fault ref %0d dut %0d",
            PAD, SKW, mism, first_mis, ntx, nrx, nfire, nst, nadm, ntok, nst_d, nuser, r_cff, d_cff, r_sf, d_sf);
        $display("CAL rx_cal_ev %0d tx_cal_ev %0d cal_mism %0d", nrxc, ntxc, cmism);
        // E2 (re-epoch while running): both halves must behave identically, seq faults included (DUT 1 edge later = wrapper input reg)
        if (mism == 0 && cmism == 0 && nuser == 0 && r_cff < 0 && d_cff < 0 && ntx > 0 && nrxc > 0 && ntok >= 2 &&
            ((E2 == 0 && r_sf < 0 && d_sf < 0) || (E2 > 0 && r_sf > 0 && d_sf == r_sf + 1)))
            $display("VERDICT PASS");
        else $display("VERDICT FAIL");
        $finish;
    end
endmodule
