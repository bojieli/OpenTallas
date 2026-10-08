`timescale 1ns/1ps
// Qwen ROM die CDC channel with credit flow control on both die faces (die-wide interface rule 2026-10-07: no
// same-cycle cross-block handshake).  One W-bit stream from the wclk domain to the rclk domain (unrelated clocks):
//   upstream face (wclk):   i_v / i_d captured at the pin; i_cr = registered credit pulse, one per word accepted
//                           out of the IBUF-slot receive buffer (the sender starts with IBUF credits).
//   crossing:               ot_async_fifo (Gray pointers, AD slots).
//   downstream face (rclk): o_v / o_d launched from flops; o_cr (credit pulse from the downstream receiver, captured at
//                           the pin) restores one of OCRED credits; a word leaves only with a credit in hand.
// Faults (sticky, flop-launched): w_fault = a word arrived with the receive buffer full (sender ignored credits);
// r_fault = more credits returned than OCRED.  Order and values are preserved exactly; latency is not cycle-fixed.
module ot_qwen_die_cdc_ch #(
    parameter integer W = 1024,
    parameter integer IBUF = 4,
    parameter integer OCRED = 4,
    parameter integer AD = 8
) (
    input  wire         wclk,
    input  wire         wrst_n,
    input  wire         i_v,
    input  wire [W-1:0] i_d,
    output wire         i_cr,
    output wire         w_fault,
    input  wire         rclk,
    input  wire         rrst_n,
    output wire         o_v,
    output wire [W-1:0] o_d,
    input  wire         o_cr,
    output wire         r_fault
);
    localparam integer IA = (IBUF <= 2) ? 1 : $clog2(IBUF);
    localparam integer CB = $clog2(OCRED + 1) + 1;
    wire wr_n, rr_n;
    ot_reset_sync u_wrs (.clk(wclk), .async_rst_n(wrst_n), .sync_rst_n(wr_n));
    ot_reset_sync u_rrs (.clk(rclk), .async_rst_n(rrst_n), .sync_rst_n(rr_n));
    // ---- write face ------------------------------------------------------------------------------------------------
    reg         iv_q;
    reg [W-1:0] id_q;
    always @(posedge wclk or negedge wr_n) if (!wr_n) iv_q <= 1'b0; else iv_q <= i_v;
    always @(posedge wclk) id_q <= i_d;
    reg [W-1:0] ib [0:IBUF-1];
    reg [IA:0]  iw, ir;
    wire        ib_empty = (iw == ir);
    wire        ib_full  = (iw[IA-1:0] == ir[IA-1:0]) && (iw[IA] != ir[IA]);
    wire        af_ready;
    wire        pop = !ib_empty && af_ready;
    reg         cr_q, wf_q;
    always @(posedge wclk) if (iv_q && !ib_full) ib[iw[IA-1:0]] <= id_q;
    always @(posedge wclk or negedge wr_n)
        if (!wr_n) begin iw <= 0; ir <= 0; cr_q <= 1'b0; wf_q <= 1'b0; end
        else begin
            if (iv_q && !ib_full) iw <= iw + 1'b1;
            if (pop) ir <= ir + 1'b1;
            cr_q <= pop;
            wf_q <= wf_q | (iv_q && ib_full);
        end
    assign i_cr = cr_q;
    assign w_fault = wf_q;
    // ---- crossing --------------------------------------------------------------------------------------------------
    wire         af_v;
    wire [W-1:0] af_d;
    wire         send;
    ot_async_fifo #(.WIDTH(W), .DEPTH(AD)) u_af (
        .wr_clk(wclk), .wr_rst_n(wr_n), .wr_valid(pop), .wr_ready(af_ready), .wr_data(ib[ir[IA-1:0]]), .wr_overflow(),
        .rd_clk(rclk), .rd_rst_n(rr_n), .rd_valid(af_v), .rd_ready(send), .rd_data(af_d), .rd_underflow());
    // ---- read face -------------------------------------------------------------------------------------------------
    reg          ocr_q, ov_q, rf_q;
    reg [W-1:0]  od_q;
    reg [CB-1:0] cred;
    assign send = af_v && (cred != 0);
    always @(posedge rclk or negedge rr_n)
        if (!rr_n) begin ocr_q <= 1'b0; ov_q <= 1'b0; cred <= OCRED[CB-1:0]; rf_q <= 1'b0; end
        else begin
            ocr_q <= o_cr;
            ov_q <= send;
            cred <= cred - {{(CB-1){1'b0}}, send} + {{(CB-1){1'b0}}, ocr_q};
            rf_q <= rf_q | (cred - {{(CB-1){1'b0}}, send} + {{(CB-1){1'b0}}, ocr_q} > OCRED[CB-1:0]);
        end
    always @(posedge rclk) if (send) od_q <= af_d;
    assign o_v = ov_q;
    assign o_d = od_q;
    assign r_fault = rf_q;
endmodule
