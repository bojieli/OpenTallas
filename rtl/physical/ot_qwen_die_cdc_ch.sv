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
    parameter integer AD = 8,
    // PIPE = 1 (qwen-blocks 2026-10-07; 0 = original): a kept pin relay before the input capture (+1 wclk), the wide
    // async FIFO (ot_qwen_async_fifo_w: registered write, per-slice read-pointer copies; +1 wclk before visibility),
    // an enable-free output capture (o_d is meaningful only with o_v) and a kept output pin station (+1 rclk).
    // Order, values, credits and faults unchanged.
    // PIPE = 2 (safe-qwen S-A2, 2026-10-08): PIPE = 1 plus the FIFO's 2-level REGISTERED read select
    // (ot_qwen_async_fifo_w RSEL2 = 1, <= 8:1 per stage): the popped word reaches od_q one rclk later, o_v is re-timed
    // with it (+1 rclk; +3 rclk total vs PIPE = 0 on the read face).  Order, values, credits and faults unchanged.
    parameter integer PIPE = 0,
    // AFW = 1 (safe-qwen S-A4 rx128, 2026-10-08): with PIPE = 0, use the wide FIFO's per-slice read-pointer copies
    // (ot_qwen_async_fifo_w, registered write: +1 wclk before visibility) and nothing else of PIPE = 1.
    parameter integer AFW = 0
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
    wire         i_v_p;
    wire [W-1:0] i_d_p;
    generate if (PIPE != 0) begin : g_ipr
        (* keep *) reg         pv;
        (* keep *) reg [W-1:0] pd;
        always @(posedge wclk or negedge wr_n) if (!wr_n) pv <= 1'b0; else pv <= i_v;
        always @(posedge wclk) pd <= i_d;
        assign i_v_p = pv; assign i_d_p = pd;
    end else begin : g_ipw
        assign i_v_p = i_v; assign i_d_p = i_d;
    end endgenerate
    always @(posedge wclk or negedge wr_n) if (!wr_n) iv_q <= 1'b0; else iv_q <= i_v_p;
    always @(posedge wclk) id_q <= i_d_p;
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
`ifndef SYNTHESIS
    wire         af_drained;              // bench view: both FIFO pointers equal (whichever FIFO is built)
`endif
    generate if (PIPE != 0 || AFW != 0) begin : g_afw
        ot_qwen_async_fifo_w #(.WIDTH(W), .DEPTH(AD), .RSEL2(PIPE >= 2 ? 1 : 0)) u_af (
            .wr_clk(wclk), .wr_rst_n(wr_n), .wr_valid(pop), .wr_ready(af_ready), .wr_data(ib[ir[IA-1:0]]), .wr_overflow(),
            .rd_clk(rclk), .rd_rst_n(rr_n), .rd_valid(af_v), .rd_ready(send), .rd_data(af_d), .rd_underflow());
`ifndef SYNTHESIS
        assign af_drained = (u_af.wr_bin == u_af.rd_bin);
`endif
    end else begin : g_af
        ot_async_fifo #(.WIDTH(W), .DEPTH(AD)) u_af (
            .wr_clk(wclk), .wr_rst_n(wr_n), .wr_valid(pop), .wr_ready(af_ready), .wr_data(ib[ir[IA-1:0]]), .wr_overflow(),
            .rd_clk(rclk), .rd_rst_n(rr_n), .rd_valid(af_v), .rd_ready(send), .rd_data(af_d), .rd_underflow());
`ifndef SYNTHESIS
        assign af_drained = (u_af.wr_bin == u_af.rd_bin);
`endif
    end endgenerate
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
    generate if (PIPE >= 2) begin : g_ops2
        // RSEL2: af_d is the word popped (send) at the previous edge; ovd re-times o_v with it
        reg ovd;
        always @(posedge rclk or negedge rr_n) if (!rr_n) ovd <= 1'b0; else ovd <= ov_q;
        always @(posedge rclk) od_q <= af_d;            // enable-free: o_d is meaningful only with o_v
        (* keep *) reg         ovp;
        (* keep *) reg [W-1:0] odp;
        always @(posedge rclk or negedge rr_n) if (!rr_n) ovp <= 1'b0; else ovp <= ovd;
        always @(posedge rclk) odp <= od_q;
        assign o_v = ovp; assign o_d = odp;
    end else if (PIPE != 0) begin : g_ops
        always @(posedge rclk) od_q <= af_d;            // enable-free: o_d is meaningful only with o_v
        (* keep *) reg         ovp;
        (* keep *) reg [W-1:0] odp;
        always @(posedge rclk or negedge rr_n) if (!rr_n) ovp <= 1'b0; else ovp <= ov_q;
        always @(posedge rclk) odp <= od_q;
        assign o_v = ovp; assign o_d = odp;
    end else begin : g_opw
        always @(posedge rclk) if (send) od_q <= af_d;
        assign o_v = ov_q; assign o_d = od_q;
    end endgenerate
    assign r_fault = rf_q;
endmodule
