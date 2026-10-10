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
    parameter integer AFW = 0,
    // RXP = 1 (sys-takeover 2026-10-09, opt-in; qfd_emb_far92 IBUF 128 x 523: ir -> 128:1 receive-buffer mux -> FIFO
    // write, -620 ps at 770 / PREROUTE -941): the receive buffer is written and read through replicated ONE-HOT pointers
    // (one 128-bit copy per 32-bit slice: select fanout 32, no binary decode), and the read is a registered 2-stage
    // AND-OR (stage 1: 8 region partial ORs of 16 entries, stage 2: their OR) into a 4-entry staging FIFO ahead of the
    // async FIFO.  A word is issued (credit returned) when the staging FIFO has room for it including the 2 in flight.
    // Cost: +2 wclk latency per word; full rate; order, values, credits and faults unchanged.
    parameter integer RXP = 0
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
    wire        x_issue;                  // RXP: a word leaves the receive buffer into the read pipeline
    wire        pop = (RXP != 0) ? x_issue : (!ib_empty && af_ready);
    reg         cr_q, wf_q;
    // RXP >= 2 (sys-takeover 2026-10-10; qfd_emb_far92_rxp_a TT -385.7: iw -> ib_full / ib_empty compares -> x_wr / x_issue ->
    // 128 x 523 write enables / one-hot read shifts, 17-20 lv): the write takes every pin-flop valid (the sender's credits
    // make a full buffer illegal; that stays a sticky fault, wf_q) and issue uses a registered non-empty flag.
    reg         ne_q;
    wire        x_wr = (RXP >= 2) ? iv_q : (iv_q && !ib_full);
    wire [W-1:0] x_af_d;                  // RXP: staging-FIFO head -> async FIFO
    wire         x_af_v, x_af_pop;
    generate if (RXP == 0) begin : g_ibw
        always @(posedge wclk) if (x_wr) ib[iw[IA-1:0]] <= id_q;
        assign x_issue = 1'b0; assign x_af_v = 1'b0; assign x_af_d = {W{1'b0}}; assign x_af_pop = 1'b0;
    end else begin : g_rxp
        localparam integer G  = 32;
        localparam integer NS = (W + G - 1) / G;
        localparam integer NR = 8;                        // stage-1 regions
        localparam integer RE = (IBUF + NR - 1) / NR;     // entries a region
        localparam integer SD = 4;                        // staging FIFO depth (>= 2 in flight + 1, full rate)
        reg [IBUF-1:0] woh [0:NS-1];
        reg [IBUF-1:0] roh [0:NS-1];
        integer s, k, r;
        genvar gs, gk;
        // one-hot pointer copies (one per slice) and one-hot writes (counters iw / ir still give empty / full / faults)
        for (gs = 0; gs < NS; gs = gs + 1) begin : g_sl
            always @(posedge wclk or negedge wr_n)
                if (!wr_n) begin woh[gs] <= {{(IBUF-1){1'b0}}, 1'b1}; roh[gs] <= {{(IBUF-1){1'b0}}, 1'b1}; end
                else begin
                    if (x_wr)    woh[gs] <= {woh[gs][IBUF-2:0], woh[gs][IBUF-1]};
                    if (x_issue) roh[gs] <= {roh[gs][IBUF-2:0], roh[gs][IBUF-1]};
                end
            for (gk = 0; gk < IBUF; gk = gk + 1) begin : g_e
                localparam integer HI = ((gs + 1) * G > W) ? W : (gs + 1) * G;
                always @(posedge wclk) if (x_wr && woh[gs][gk]) ib[gk][HI-1:gs*G] <= id_q[HI-1:gs*G];
            end
        end
        // issue: buffer non-empty and staging room for this word plus the ones in flight
        reg        v1, v2;
        reg [2:0]  sn;                                    // staging occupancy
`ifdef OT_CDC_RXP_MUT_NOINFLIGHT
        wire room = (sn < SD);                            // mutant: the 2 words in flight are not counted
`else
        wire room = ({1'b0, sn} + v1 + v2) < SD;
`endif
        assign x_issue = ((RXP >= 2) ? ne_q : !ib_empty) && room;
        // per-entry W-bit select mask from the slice copies (bit b of entry k = roh[b / G][k])
        wire [W-1:0] ohm [0:IBUF-1];
        genvar gb, gm;
        for (gm = 0; gm < IBUF; gm = gm + 1) begin : g_m
            for (gb = 0; gb < W; gb = gb + 1) begin : g_b
                assign ohm[gm][gb] = roh[gb / G][gm];
            end
        end
        // stage 1: region partial AND-OR (the issued entry's one-hot); stage 2: OR of the regions
        reg [W-1:0] p1 [0:NR-1];
        reg [W-1:0] d2;
        reg [W-1:0] t1;
        always @(posedge wclk) begin
            for (r = 0; r < NR; r = r + 1) begin
                t1 = {W{1'b0}};
                for (k = r * RE; k < (r + 1) * RE && k < IBUF; k = k + 1)
                    t1 = t1 | (ib[k] & ohm[k]);
                p1[r] <= t1;
            end
            t1 = {W{1'b0}};
            for (r = 0; r < NR; r = r + 1) t1 = t1 | p1[r];
            d2 <= t1;
        end
        // staging FIFO (SD entries) -> async FIFO
        reg [W-1:0] st [0:SD-1];
        reg [1:0]   sw, sr;
        assign x_af_v = (sn != 0);
        assign x_af_d = st[sr];
        assign x_af_pop = x_af_v && af_ready;
        always @(posedge wclk) if (v2) st[sw] <= d2;
        always @(posedge wclk or negedge wr_n)
            if (!wr_n) begin v1 <= 1'b0; v2 <= 1'b0; sn <= 3'd0; sw <= 2'd0; sr <= 2'd0; end
            else begin
                v1 <= x_issue; v2 <= v1;
                if (v2) sw <= sw + 1'b1;
                if (x_af_pop) sr <= sr + 1'b1;
                sn <= sn + v2 - x_af_pop;
            end
    end endgenerate
    always @(posedge wclk or negedge wr_n)
        if (!wr_n) begin iw <= 0; ir <= 0; cr_q <= 1'b0; wf_q <= 1'b0; ne_q <= 1'b0; end
        else begin
            if (x_wr) iw <= iw + 1'b1;
            // the occupancy after this edge, non-zero (iw - ir next): exact, not conservative
`ifdef OT_CDC_RXP_MUT_NESTALE
            ne_q <= (iw != ir);                            // mutant: the flag lags the edge's own write / issue
`else
            ne_q <= ((iw + (x_wr ? 1'b1 : 1'b0)) != (ir + (pop ? 1'b1 : 1'b0)));
`endif
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
            .wr_clk(wclk), .wr_rst_n(wr_n), .wr_valid((RXP != 0) ? x_af_pop : pop), .wr_ready(af_ready), .wr_data((RXP != 0) ? x_af_d : ib[ir[IA-1:0]]), .wr_overflow(),
            .rd_clk(rclk), .rd_rst_n(rr_n), .rd_valid(af_v), .rd_ready(send), .rd_data(af_d), .rd_underflow());
`ifndef SYNTHESIS
        assign af_drained = (u_af.wr_bin == u_af.rd_bin);
`endif
    end else begin : g_af
        ot_async_fifo #(.WIDTH(W), .DEPTH(AD)) u_af (
            .wr_clk(wclk), .wr_rst_n(wr_n), .wr_valid((RXP != 0) ? x_af_pop : pop), .wr_ready(af_ready), .wr_data((RXP != 0) ? x_af_d : ib[ir[IA-1:0]]), .wr_overflow(),
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
