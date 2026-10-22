`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LEAD2-S81/TOK (2026-10-19): ot_s81sl_cap_ed = static E-column delay of the capture root (TOK.DS.BENCH.1 calendar fix).
//
// Why: the first coupled QF diagnostic (757a340ff, unit 627409) proved the CAP root takes ONE word per edge and the six
// frames' rows never merge, so all frame partials need distinct root edges.  The shared XS stream gives every frame the
// same segment dates; the root's possible exit window is 37 edges (9 pairs) / 39 edges (12 pairs) against >= 44 real
// partials.  An EXACT uncapped packing (root_pack.py, results/rtl/s81_qf_producer_1019/cap_ed_calendar) finds NO legal
// six-frame calendar for 9 or 12 pairs with shared-stream gaps 0/8/16/24/32, but finds one per column (3 frames, 12
// pairs, gap 0: 22 words, edges 1773..1802), and a six-frame one with the E column delayed by D = 23 edges.
// So the E tree's output word (u_te nc RST flop) is delayed by exactly D edges before n6's E port: W and E columns
// interleave on n6 at disjoint edges, no arbitration, no queue, no backpressure (static calendar; the compiler owns D).
//
// Structure: ot_hdc_delay_rf (pin input reg -> (D-2)-row circular RF -> pin output reg; no flop->flop hold chain).
// 66 bits x (D-2) = 1,386 bits at D = 23 (< 2 kb: register file, SAFE item 5).  The RF holds no reset; the valid bit
// leaving the line is masked for the first D edges after reset (primed counter) so no stale/X word is ever valid.
// The E fault bit is sticky and phase-end checked: it bypasses the line (plus one pin flop).
// Cost: +D edges on every E-column return word (latency only; throughput unchanged: epoch period 600 >> D).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_ed #(
    parameter integer D = 23
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    input  wire        i_f,
    output wire        o_v,
    output wire [31:0] o_t,
    output wire [31:0] o_d,
    output wire        o_e,
    output reg         o_f
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire [65:0] q;
    ot_hdc_delay_rf #(.W(66), .D(D)) u_dl (.clk(clk), .rst_n(rsv[0]), .d({i_e, i_d, i_t, i_v}), .q(q));
    localparam integer CW = $clog2(D + 2);
    reg [CW-1:0] cnt; reg primed;
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin cnt <= {CW{1'b0}}; primed <= 1'b0; end
        else if (!primed) begin cnt <= cnt + 1'b1; primed <= (cnt == D[CW-1:0]); end
    assign o_v = q[0] && primed;
    assign o_t = q[32:1];
    assign o_d = q[64:33];
    assign o_e = q[65];
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) o_f <= 1'b0; else if (i_f) o_f <= 1'b1;
endmodule
`default_nettype wire
