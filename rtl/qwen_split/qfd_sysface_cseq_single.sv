`timescale 1ns/1ps
// =====================================================================================================================
// qfd_sysface_cseq_single -- DIE-QC-59Q 2026-11-01 (COORD 05:0x ruling: MU single-seq calendar form on BOTH dies).
// The QC compute face's D2D calendar producer (qfd_sys_face_lctx3_core u_cseq): the image-driven ot_qwen_d2d_cal_seq on
// the QC+KV pair image the KV die boots (d2d_cal_image_qc_pair.svh, C half: TX/RX images, segment bases, START table,
// ADM 1 / ADM_OFS / ADM_LEN, AUTO 1 / FIRST_OFS / PERIOD), exactly as tools/qwen_layerbench/kv_dieslice/kvs_compute_end.sv
// proves against the KV die.  It replaces the 10-21 OVL two-list producer (qfd_d2d_cal_seq_ovl_rope + ovl_release_rope
// ROMs) and keeps that producer's port set, so the bound die's OVL master (qfd_d2d_static_ovl_sf7_obs1) and the plan are
// unchanged:
//   cal_start_rx / cal_seg_rx = the single start / segment (both directions start on one edge, as the non-OVL end and
//   as the OVL sequencer's own admission start); cal_user_tx / cal_user_rx = declared constant 0 (no per-direction
//   user in the single-seq form; the master's tx_user / rx_user then stay 0).
// LANDING (CTL_PAD): the as-built die relays u_sys_face -> u_d2d_rom (glue ot_dp_dly, die_r56 rly_sf_*) land the tuple
//   on different edges: cfg_addr / cfg_rx_we D4, cfg_data / cfg_tx_we / cal_start D5, cal_seg / cal_start_rx D6,
//   cal_seg_rx / cal_user_* D7, while the master's pin flops are uniform.  CTL_PAD (edges, byte k: 0 cfg_tx_we
//   1 cfg_rx_we 2 cfg_addr 3 cfg_data 4 cal_start 5 cal_seg 6 cal_start_rx 7 cal_seg_rx) pads each output so the whole
//   tuple lands on one edge (D7).  Strobes are reset flops (rst_n), cfg payload is reset-less.
// ANCHOR (CS_EP_SKEW): kvs_compute_end feeds the sequencer and the master the same fwd_epoch edge and the tuple straight
//   to the master pins.  On the die the face sees fwd_epoch 1 edge after the master (wrapper input capture) and the tuple
//   reaches the master 1 (wrapper output register) + 7 (landing) edges after the sequencer: EP_SKEW -9 starts every
//   compiled event 9 edges earlier, so the master plays the pair image on the same edges as in kvs_compute_end
//   (ADM_OFS / FIRST_OFS of the image unchanged; the 2 NE + 2 = 66-edge image load runs from reset, before the strobe).
// seq_start = the sequencer's own cal_start (same edge as layer), for the face's admission / token checks.
// No valid / ready / credit selects a cycle; every fault stays sticky (ot_qwen_d2d_cal_seq).
// =====================================================================================================================
module qfd_sysface_cseq_single #(
    parameter [8*8-1:0] CTL_PAD = {8'd0, 8'd1, 8'd1, 8'd2, 8'd2, 8'd3, 8'd3, 8'd2},
    parameter integer   CS_EP_SKEW = -9
) (
    input  wire        ck, rst_n, reload, epoch_go, halt,
    output wire        cfg_tx_we, cfg_rx_we,
    output wire [5:0]  cfg_addr,
    output wire [31:0] cfg_data,
    output wire        cal_start, cal_seg, cal_start_rx, cal_seg_rx,
    output wire [1:0]  cal_user_tx, cal_user_rx,
    output wire        cal_ready, running,
    output wire [5:0]  layer,
    output wire        adm_done, seq_start, fault
);
    `include "d2d_cal_image_qc_pair.svh"
    wire s_tx, s_rx, s_cs, s_sg, s_ts; wire [5:0] s_a; wire [31:0] s_d;
    ot_qwen_d2d_cal_seq #(.TX_IMG(D2D_CAL_C_TX_IMG), .RX_IMG(D2D_CAL_C_RX_IMG), .TX_SEG1(D2D_CAL_C_TX_SEG1),
        .RX_SEG1(D2D_CAL_C_RX_SEG1), .START(D2D_CAL_START), .ADM(1), .TX_SEG2(D2D_CAL_C_TX_SEG2), .RX_SEG2(D2D_CAL_C_RX_SEG2),
        .ADM_OFS(D2D_ADM_OFS), .ADM_LEN(D2D_ADM_LEN), .AUTO(1), .FIRST_OFS(D2D_FIRST_TOKEN), .PERIOD(D2D_TOKEN_PERIOD),
        .EP_SKEW(CS_EP_SKEW)) u_seq (.ck(ck), .rst_n(rst_n), .reload(reload), .tok_go(1'b0), .epoch_go(epoch_go),
        .halt(halt), .cfg_tx_we(s_tx), .cfg_rx_we(s_rx), .cfg_addr(s_a), .cfg_data(s_d), .cal_start(s_cs), .cal_seg(s_sg),
        .cal_ready(cal_ready), .running(running), .layer(layer), .adm_done(adm_done), .tok_start(s_ts), .fault(fault));
    assign seq_start = s_cs;
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[0*8 +: 8]), .R(1)) u_lp_txwe (.ck(ck), .rst_n(rst_n), .d(s_tx), .q(cfg_tx_we));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[1*8 +: 8]), .R(1)) u_lp_rxwe (.ck(ck), .rst_n(rst_n), .d(s_rx), .q(cfg_rx_we));
    qfd_sysface_land_pad #(.W(6),  .D(CTL_PAD[2*8 +: 8]), .R(0)) u_lp_addr (.ck(ck), .rst_n(rst_n), .d(s_a),  .q(cfg_addr));
    qfd_sysface_land_pad #(.W(32), .D(CTL_PAD[3*8 +: 8]), .R(0)) u_lp_data (.ck(ck), .rst_n(rst_n), .d(s_d),  .q(cfg_data));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[4*8 +: 8]), .R(1)) u_lp_cs   (.ck(ck), .rst_n(rst_n), .d(s_cs), .q(cal_start));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[5*8 +: 8]), .R(1)) u_lp_sg   (.ck(ck), .rst_n(rst_n), .d(s_sg), .q(cal_seg));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[6*8 +: 8]), .R(1)) u_lp_csrx (.ck(ck), .rst_n(rst_n), .d(s_cs), .q(cal_start_rx));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[7*8 +: 8]), .R(1)) u_lp_sgrx (.ck(ck), .rst_n(rst_n), .d(s_sg), .q(cal_seg_rx));
    assign cal_user_tx = 2'd0;
    assign cal_user_rx = 2'd0;
endmodule

// D register stages (D = 0: wire); R = 1 resets to 0 on rst_n (strobes), R = 0 reset-less (cfg payload).
module qfd_sysface_land_pad #(parameter integer W = 1, parameter integer D = 0, parameter integer R = 0) (
    input wire ck, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    if (D == 0) begin : g_w
        assign q = d;
    end else begin : g_r
        reg [W-1:0] sr [0:D-1];
        integer i;
        if (R != 0) begin : g_rs
            always @(posedge ck or negedge rst_n)
                if (!rst_n) for (i = 0; i < D; i = i + 1) sr[i] <= {W{1'b0}};
                else begin sr[0] <= d; for (i = 1; i < D; i = i + 1) sr[i] <= sr[i-1]; end
        end else begin : g_nr
            always @(posedge ck) begin sr[0] <= d; for (i = 1; i < D; i = i + 1) sr[i] <= sr[i-1]; end
        end
        assign q = sr[D-1];
    end
endmodule
