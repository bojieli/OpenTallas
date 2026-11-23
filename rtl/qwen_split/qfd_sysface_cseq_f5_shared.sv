`timescale 1ns/1ps
module qfd_sysface_cseq_f5_shared #(
    parameter [8*8-1:0] CTL_PAD = {8'd0, 8'd1, 8'd1, 8'd2, 8'd2, 8'd3, 8'd3, 8'd2},
    parameter integer   CS_EP_SKEW = -9,
    parameter integer   FRESH_WARM_OWNER = 0
) (
    input  wire        ck, rst_n, reload, epoch_go, halt,
    input  wire        media_hold,
    input  wire [31:0] shared_tape_word,
    output wire [8:0]  shared_tape_addr,
    output wire        cfg_tx_we, cfg_rx_we,
    output wire [5:0]  cfg_addr,
    output wire [31:0] cfg_data,
    output wire        cal_start, cal_seg, cal_start_rx, cal_seg_rx,
    output wire [1:0]  cal_user_tx, cal_user_rx,
    output wire        cal_ready, running,
    output wire [5:0]  layer,
    output wire        adm_done, seq_start, fault
);
    `include "qfd_sysface_f5_shared_calendar.svh"

    wire s_tx, s_rx, s_cs, s_sg, r_cs, r_sg;
    wire [1:0] tx_user, rx_user;
    wire [5:0] s_a;
    wire [31:0] s_d;
    wire [8:0] addr_tx, addr_rx;
    reg addr_fault;
    wire seq_fault;

    // Identical C TX/RX start, segment and user fields let both readers share
    // one mask. Verify the unpadded requests remain equal throughout replay.
    assign shared_tape_addr = addr_tx;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) addr_fault <= 1'b0;
        else if (addr_tx != addr_rx || s_cs != r_cs || (s_cs && {s_sg,tx_user} != {r_sg,rx_user}))
            addr_fault <= 1'b1;

    ot_qwen_d2d_ovl_seq_shared #(.AW(9),.COLD_PREFIX(1),.ADM(1),.FRESH_WARM_OWNER(FRESH_WARM_OWNER),
        .TX_IMG(CAL0),.RX_IMG(CAL1),.TX_SEG1(BASE0),.RX_SEG1(BASE1),
        .TX_SEG2(ADM_BASE0),.RX_SEG2(ADM_BASE1),
        .ADM_OFS(ADM_OFS),.ADM_LEN(ADM_LEN),.FIRST_OFS(FIRST_TOKEN-LIST_LEAD),
        .EP_SKEW(CS_EP_SKEW)) u_seq (
        .ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),.media_hold(media_hold),
        .cfg_tx_we(s_tx),.cfg_rx_we(s_rx),.cfg_addr(s_a),.cfg_data(s_d),
        .cal_start(s_cs),.cal_seg(s_sg),.cal_start_rx(r_cs),.cal_seg_rx(r_sg),
        .cal_user_tx(tx_user),.cal_user_rx(rx_user),
        .tx_rom_addr(addr_tx),.tx_rom_q(shared_tape_word),.rx_rom_addr(addr_rx),.rx_rom_q(shared_tape_word),
        .cal_ready(cal_ready),.adm_done(adm_done),.running(running),.fault(seq_fault));
    assign seq_start = s_cs;
    // The face uses layer only to distinguish the single admission start.
    assign layer = s_cs && !adm_done ? 6'd63 : 6'd0;
    assign fault = seq_fault || addr_fault;
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[0*8 +: 8]), .R(1)) u_lp_txwe (.ck(ck), .rst_n(rst_n), .d(s_tx), .q(cfg_tx_we));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[1*8 +: 8]), .R(1)) u_lp_rxwe (.ck(ck), .rst_n(rst_n), .d(s_rx), .q(cfg_rx_we));
    qfd_sysface_land_pad #(.W(6),  .D(CTL_PAD[2*8 +: 8]), .R(0)) u_lp_addr (.ck(ck), .rst_n(rst_n), .d(s_a),  .q(cfg_addr));
    qfd_sysface_land_pad #(.W(32), .D(CTL_PAD[3*8 +: 8]), .R(0)) u_lp_data (.ck(ck), .rst_n(rst_n), .d(s_d),  .q(cfg_data));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[4*8 +: 8]), .R(1)) u_lp_cs   (.ck(ck), .rst_n(rst_n), .d(s_cs), .q(cal_start));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[5*8 +: 8]), .R(1)) u_lp_sg   (.ck(ck), .rst_n(rst_n), .d(s_sg), .q(cal_seg));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[6*8 +: 8]), .R(1)) u_lp_csrx (.ck(ck), .rst_n(rst_n), .d(s_cs), .q(cal_start_rx));
    qfd_sysface_land_pad #(.W(1),  .D(CTL_PAD[7*8 +: 8]), .R(1)) u_lp_sgrx (.ck(ck), .rst_n(rst_n), .d(s_sg), .q(cal_seg_rx));
    assign cal_user_tx = tx_user;
    assign cal_user_rx = rx_user;
endmodule
