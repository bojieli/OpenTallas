`timescale 1ns/1ps
// Compute face's overlapping calendar producer. Lists are mask ROMs; only the next list word is held in flops.
module qfd_d2d_cal_seq_ovl #(parameter ROM_DIR = "", parameter integer AW=11, parameter integer TX_WRAP_BASE=0, parameter integer RX_WRAP_BASE=0, parameter integer MUT_HALT_REWIND = 0) (
    input wire ck, rst_n, reload, epoch_go, halt,
    output wire cfg_tx_we, cfg_rx_we, output wire [5:0] cfg_addr, output wire [31:0] cfg_data,
    output wire cal_start, cal_seg, cal_start_rx, cal_seg_rx,
    output wire [1:0] cal_user_tx, cal_user_rx,
    output wire cal_ready, adm_done, running, fault
);
    `include "ovl_release/ovl_release_img.svh"
    wire [AW-1:0] ta, ra;
    wire [71:0] tq, rq;
    reg [31:0] tq_cap, rq_cap;
    // The ROM's slow output drives plain capture flops only; list decoding starts at the capture register.
    always @(posedge ck) begin tq_cap <= tq[31:0]; rq_cap <= rq[31:0]; end
`ifdef SYNTHESIS
    ot_rom_4096x72_m8 u_tx_rom (.clk(ck), .ce_in(1'b1), .addr_in({{(12-AW){1'b0}},ta}), .rd_out(tq));
    ot_rom_4096x72_m8 u_rx_rom (.clk(ck), .ce_in(1'b1), .addr_in({{(12-AW){1'b0}},ra}), .rd_out(rq));
`else
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_c_tx.viamap.hex"}), .INSTANCE("ovl_c_tx")) u_tx_rom
        (.clk(ck), .ce_in(1'b1), .addr_in({{(12-AW){1'b0}},ta}), .rd_out(tq));
    ot_rom_4096x72_m8 #(.VIAMAP({ROM_DIR,"/ovl_c_rx.viamap.hex"}), .INSTANCE("ovl_c_rx")) u_rx_rom
        (.clk(ck), .ce_in(1'b1), .addr_in({{(12-AW){1'b0}},ra}), .rd_out(rq));
`endif
    ot_qwen_d2d_ovl_seq #(.AW(AW),.TX_WRAP_BASE(TX_WRAP_BASE),.RX_WRAP_BASE(RX_WRAP_BASE),.MUT_HALT_REWIND(MUT_HALT_REWIND), .TX_IMG(OVL_C_TX_IMG), .RX_IMG(OVL_C_RX_IMG),
        .TX_SEG1(OVL_C_TX_SEG1), .RX_SEG1(OVL_C_RX_SEG1), .ADM(1), .TX_SEG2(32'd16), .RX_SEG2(32'd16),
        .ADM_OFS(72), .ADM_LEN(1100), .FIRST_OFS(1176), .EP_SKEW(0)) u_seq (
        .ck(ck), .rst_n(rst_n), .reload(reload), .epoch_go(epoch_go), .halt(halt),
        .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .cal_start(cal_start), .cal_seg(cal_seg), .cal_start_rx(cal_start_rx), .cal_seg_rx(cal_seg_rx),
        .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx), .tx_rom_addr(ta), .tx_rom_q(tq_cap),
        .rx_rom_addr(ra), .rx_rom_q(rq_cap), .cal_ready(cal_ready), .adm_done(adm_done), .running(running), .fault(fault));
endmodule
