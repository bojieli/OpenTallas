`timescale 1ns/1ps
// Qwen ROM die IO-band CDC slot (r21 master qfd_io_xfifo, 400.008 x 1563.816, beside the collective): the five clock
// crossings between the core / collective clock (ck), the UCIe PHY digital clock (cku), the SerDes PHY digital clock
// (cks) and the sequencer clock (ckd), each an ot_qwen_die_cdc_ch (credit flow control on both faces, async FIFO):
//   ut: collective -> UCIe TX   (ck  -> cku, 1,024 b)      ur: UCIe RX  -> collective (cku -> ck, 1,024 b)
//   st: collective -> SerDes TX (ck  -> cks, 1,024 b)      sr: SerDes RX -> collective (cks -> ck, 1,024 b)
//   sq: sequencer -> collective (ckd -> ck, 66 b)
// Port naming follows the r21 abstract (i_<ch> / o_<ch>), plus the per-channel valid and credit bits the abstract's
// bit counts omit (_v, _cr).  Faults are sticky, flop-launched, one per clock domain.
module ot_qwen_die_io_xfifo #(
    parameter integer WIO = 1024,
    parameter integer WSQ = 66,
    parameter integer PIPE = 0,         // ot_qwen_die_cdc_ch PIPE (qwen-blocks 2026-10-07; 2 = safe-qwen S-A2)
    // NCOLL = 1 (sys-takeover 2026-10-09, opt-in; registry qfd_native_collective_binding): the production collective
    // local port.  sq carries the full engine input word (instantiate WSQ = 546: {tag32, mode, last, data512}, mode at
    // bit MB) and a new return channel cq (ck -> ckd, WCQ = 516: {err, rank2, last, data512}) carries the engine's push
    // output back to the sequencer.  The engine output has no back-pressure, so the ckd-side credit gate hands a
    // forward credit to the sequencer only while the return path (cq receive buffer + async FIFO, RRES words) can hold
    // every result that word can produce (N for an all-gather word, 1 for an all-reduce word: N - 1 refunded when the
    // accepted word is a reduce).  The sequencer keeps its 4 initial forward credits (pre-reserved at reset) and
    // returns one o_coll_seq_cr per returned word it consumes.  No ready crosses a block face.
    parameter integer NCOLL = 0,
    parameter integer WCQ = 516,
    parameter integer N = 4,
    parameter integer MB = 513,
    parameter integer CQ_AD = 64
) (
    input  wire ck, input wire cku, input wire cks, input wire ckd, input wire rst_n,
    input  wire i_ucie_tx_v,   input  wire [WIO-1:0] i_ucie_tx,   output wire i_ucie_tx_cr,
    output wire o_ucie_tx_v,   output wire [WIO-1:0] o_ucie_tx,   input  wire o_ucie_tx_cr,
    input  wire i_ucie_rx_v,   input  wire [WIO-1:0] i_ucie_rx,   output wire i_ucie_rx_cr,
    output wire o_ucie_rx_v,   output wire [WIO-1:0] o_ucie_rx,   input  wire o_ucie_rx_cr,
    input  wire i_serdes_tx_v, input  wire [WIO-1:0] i_serdes_tx, output wire i_serdes_tx_cr,
    output wire o_serdes_tx_v, output wire [WIO-1:0] o_serdes_tx, input  wire o_serdes_tx_cr,
    input  wire i_serdes_rx_v, input  wire [WIO-1:0] i_serdes_rx, output wire i_serdes_rx_cr,
    output wire o_serdes_rx_v, output wire [WIO-1:0] o_serdes_rx, input  wire o_serdes_rx_cr,
    input  wire i_seq_coll_v,  input  wire [WSQ-1:0] i_seq_coll,  output wire i_seq_coll_cr,
    output wire o_seq_coll_v,  output wire [WSQ-1:0] o_seq_coll,  input  wire o_seq_coll_cr,
    // NCOLL return channel (unused when NCOLL = 0)
    input  wire i_coll_seq_v,  input  wire [WCQ-1:0] i_coll_seq,
    output wire o_coll_seq_v,  output wire [WCQ-1:0] o_coll_seq,  input  wire o_coll_seq_cr,
    output wire fault_ck, output wire fault_cku, output wire fault_cks, output wire fault_ckd
);
    wire wf_ut, rf_ut, wf_ur, rf_ur, wf_st, rf_st, wf_sr, rf_sr, wf_sq, rf_sq;
    ot_qwen_die_cdc_ch #(.W(WIO), .PIPE(PIPE)) u_ut (.wclk(ck), .wrst_n(rst_n), .i_v(i_ucie_tx_v), .i_d(i_ucie_tx), .i_cr(i_ucie_tx_cr),
        .w_fault(wf_ut), .rclk(cku), .rrst_n(rst_n), .o_v(o_ucie_tx_v), .o_d(o_ucie_tx), .o_cr(o_ucie_tx_cr), .r_fault(rf_ut));
    ot_qwen_die_cdc_ch #(.W(WIO), .PIPE(PIPE)) u_ur (.wclk(cku), .wrst_n(rst_n), .i_v(i_ucie_rx_v), .i_d(i_ucie_rx), .i_cr(i_ucie_rx_cr),
        .w_fault(wf_ur), .rclk(ck), .rrst_n(rst_n), .o_v(o_ucie_rx_v), .o_d(o_ucie_rx), .o_cr(o_ucie_rx_cr), .r_fault(rf_ur));
    ot_qwen_die_cdc_ch #(.W(WIO), .PIPE(PIPE)) u_st (.wclk(ck), .wrst_n(rst_n), .i_v(i_serdes_tx_v), .i_d(i_serdes_tx), .i_cr(i_serdes_tx_cr),
        .w_fault(wf_st), .rclk(cks), .rrst_n(rst_n), .o_v(o_serdes_tx_v), .o_d(o_serdes_tx), .o_cr(o_serdes_tx_cr), .r_fault(rf_st));
    ot_qwen_die_cdc_ch #(.W(WIO), .PIPE(PIPE)) u_sr (.wclk(cks), .wrst_n(rst_n), .i_v(i_serdes_rx_v), .i_d(i_serdes_rx), .i_cr(i_serdes_rx_cr),
        .w_fault(wf_sr), .rclk(ck), .rrst_n(rst_n), .o_v(o_serdes_rx_v), .o_d(o_serdes_rx), .o_cr(o_serdes_rx_cr), .r_fault(rf_sr));
    wire wf_cq, rf_cq, gf_cq;   // NCOLL: the coll_xfifo's per-domain sticky faults (wf_cq: ck, rf_cq: ckd)
    generate if (NCOLL != 0) begin : g_coll
        ot_qwen_die_coll_xfifo #(.WSQ(WSQ), .WCQ(WCQ), .N(N), .MB(MB), .CQ_AD(CQ_AD), .PIPE(PIPE)) u_coll (
            .ck(ck), .ckd(ckd), .rst_n(rst_n),
            .i_seq_coll_v(i_seq_coll_v), .i_seq_coll(i_seq_coll), .i_seq_coll_cr(i_seq_coll_cr),
            .o_seq_coll_v(o_seq_coll_v), .o_seq_coll(o_seq_coll), .o_seq_coll_cr(o_seq_coll_cr),
            .i_coll_seq_v(i_coll_seq_v), .i_coll_seq(i_coll_seq),
            .o_coll_seq_v(o_coll_seq_v), .o_coll_seq(o_coll_seq), .o_coll_seq_cr(o_coll_seq_cr),
            .fault_ck(wf_cq), .fault_ckd(rf_cq));
        assign wf_sq = 1'b0; assign rf_sq = 1'b0; assign gf_cq = 1'b0;
    end else begin : g_nocoll
        ot_qwen_die_cdc_ch #(.W(WSQ), .PIPE(PIPE)) u_sq (.wclk(ckd), .wrst_n(rst_n), .i_v(i_seq_coll_v), .i_d(i_seq_coll),
            .i_cr(i_seq_coll_cr), .w_fault(wf_sq), .rclk(ck), .rrst_n(rst_n), .o_v(o_seq_coll_v), .o_d(o_seq_coll),
            .o_cr(o_seq_coll_cr), .r_fault(rf_sq));
        assign o_coll_seq_v = 1'b0; assign o_coll_seq = {WCQ{1'b0}};
        assign wf_cq = 1'b0; assign rf_cq = 1'b0; assign gf_cq = 1'b0;
    end endgenerate
    reg f_ck, f_cku, f_cks, f_ckd;   // per-domain OR of flop-launched sticky faults, registered at the pin
    always @(posedge ck)  f_ck  <= wf_ut | wf_st | rf_ur | rf_sr | rf_sq | wf_cq;
    always @(posedge cku) f_cku <= rf_ut | wf_ur;
    always @(posedge cks) f_cks <= rf_st | wf_sr;
    always @(posedge ckd) f_ckd <= wf_sq | rf_cq | gf_cq;
    assign fault_ck = f_ck; assign fault_cku = f_cku; assign fault_cks = f_cks; assign fault_ckd = f_ckd;
endmodule
