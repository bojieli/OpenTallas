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
    // S81-CORE-LAT-R20 10-27 (RAW face_guard 'unregistered' on the valid output): the valid bit leaves through its OWN
    // pin flop, masked BEFORE that flop instead of after the line's output register.  The valid bit runs a (D-1)-edge
    // register-file line, its output flop takes it AND the primed flag's next state -> o_v(t) = i_v(t-D) & primed(t),
    // edge for edge the old q[0] && primed (0 cycles).  The other bits keep the D-edge line.
    wire [65:0] q;
    ot_hdc_delay_rf #(.W(65), .D(D)) u_dl (.clk(clk), .rst_n(rsv[0]), .d({i_e, i_d, i_t}), .q(q[65:1]));
    wire v1;
    ot_hdc_delay_rf #(.W(1), .D(D - 1)) u_dv (.clk(clk), .rst_n(rsv[0]), .d(i_v), .q(v1));
    localparam integer CW = $clog2(D + 2);
    reg [CW-1:0] cnt; reg primed;
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin cnt <= {CW{1'b0}}; primed <= 1'b0; end
        else if (!primed) begin cnt <= cnt + 1'b1; primed <= (cnt == D[CW-1:0]); end
    wire primed_n = primed || (cnt == D[CW-1:0]);              // next state of primed (out of reset)
    reg o_v_q;
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) o_v_q <= 1'b0; else o_v_q <= v1 && primed_n;
    assign o_v = o_v_q;
    assign q[0] = 1'b0;                                         // unused (valid: o_v_q)
    assign o_t = q[32:1];
    assign o_d = q[64:33];
    assign o_e = q[65];
    // S81-CORE-LAT-R20 10-27 (RAW face_guard: i_f unregistered, o_f shared by its own sticky loop): i_f gets a pin
    // flop (+1 edge on fault visibility ONLY: the sticky fault is phase-end checked, OWNERS-S81/CAP2 fault_p
    // precedent), the sticky lives in f_s and the pin o_f is a copy flop (f_s kept: no merge) with the SAME next state (0 extra edges).
    reg i_f_q;
    (* keep = "true" *) reg f_s;
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) i_f_q <= 1'b0; else i_f_q <= i_f;
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) f_s <= 1'b0; else if (i_f_q) f_s <= 1'b1;
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) o_f <= 1'b0; else o_f <= f_s || i_f_q;
endmodule
`default_nettype wire
