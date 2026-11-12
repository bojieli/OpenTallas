`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// BUS-GEAR-1 (2026-11-12): static-schedule bus gearbox, BEATS:1 (2 or 4), for wide low-duty partition crossings.
//
// A W-bit word that is valid in cycle t (v_i) is sent as BEATS registered beats of BW = ceil(W / BEATS) bits on
// cycles t+1 .. t+BEATS (beat 0 = d_i[BW-1:0] first), with a 1-bit first-beat flag f_o beside beat 0.  The receiver
// presents the whole word on the cycle its last beat arrives, so the word lands BEATS - 1 cycles later than an
// unserialised registered crossing (plan DEC12: word_cycles = cycles + beats - 1; beat_index_bits = 1 for f).
// Bits that ride beside the word (commands, strobes) go through ot_bus_gear_rx's side-band delay so every bit of the
// original bundle keeps the same relative cycle (one uniform +BEATS-1 on the whole crossing).
//
// Static schedule, no flow control: the producer must not raise v_i again within BEATS - 1 cycles of a word (word
// spacing >= BEATS).  A violation is a sticky fault (fault_o), never arbitrated or silently stretched (METHODOLOGY 1.1).
// Cycles without a word carry zero beats and f = 0 (bubbles), so an idle crossing does not toggle.
//
// Equivalence (transaction level): for every input word stream with spacing >= BEATS, the receiver's (v_o, d_o, s_o)
// stream equals the transmitter's (v_i, d_i, s_i) stream delayed by exactly LAT = 1 (tx reg) + H (stations between) +
// BEATS - 1 cycles on valid words; d_o is zero on non-word cycles.  Bench: tb_ot_bus_gear.sv.
// MUT (bench only, 0 in every kit): 1 = TX sends the beats in reverse order, 2 = RX side-band delay one cycle short,
//   3 = TX never raises the spacing fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_bus_gear_tx #(
    parameter integer W = 288,
    parameter integer BEATS = 2,
    parameter integer MUT = 0,
    localparam integer BW = (W + BEATS - 1) / BEATS
) (
    input  wire clk,
    input  wire rst_n,
    input  wire v_i,
    input  wire [W-1:0] d_i,
    output reg  [BW-1:0] b_o,
    output reg  f_o,
    output reg  fault_o
);
    localparam integer WP = BW * BEATS;
    localparam integer CW = $clog2(BEATS);
    wire [WP-1:0] dp = {{(WP - W){1'b0}}, d_i};
    reg  [WP-1:0] wq;                // the word being sent (datapath: no reset, METHODOLOGY 2.6)
    reg  [CW-1:0] left;              // beats still to send after the current one
    wire busy = (left != {CW{1'b0}});
    wire [CW-1:0] idx = CW'(BEATS) - left;                       // next beat index while busy
    wire [CW-1:0] sel = (MUT == 1) ? CW'(BEATS - 1) - idx : idx;
    always @(posedge clk) begin
        if (v_i) begin
            wq  <= dp;
            b_o <= (MUT == 1) ? dp[WP-1 -: BW] : dp[BW-1:0];
        end else if (busy) begin
            b_o <= wq[BW*sel +: BW];
        end else begin
            b_o <= {BW{1'b0}};
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            left <= {CW{1'b0}}; f_o <= 1'b0; fault_o <= 1'b0;
        end else begin
            f_o <= v_i;
            if (v_i) left <= CW'(BEATS - 1);
            else if (busy) left <= left - 1'b1;
            if (v_i && busy && MUT != 3) fault_o <= 1'b1;
        end
    end
endmodule

module ot_bus_gear_rx #(
    parameter integer W = 288,
    parameter integer BEATS = 2,
    parameter integer SW = 1,           // side-band bits (delayed BEATS - 1 cycles to stay aligned with the word)
    parameter integer MUT = 0,
    localparam integer BW = (W + BEATS - 1) / BEATS
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [BW-1:0] b_i,
    input  wire f_i,
    input  wire [SW-1:0] s_i,
    output wire v_o,
    output wire [W-1:0] d_o,
    output wire [SW-1:0] s_o
);
    localparam integer WP = BW * BEATS;
    localparam integer D = BEATS - 1;
    localparam integer DS = (MUT == 2) ? D - 1 : D;
    // beats 0 .. BEATS-2 held (oldest at the bottom); the last beat is the live input
    reg [BW*D-1:0] held;
    reg [D-1:0] fpipe;               // fpipe[k] = f_i delayed k+1 cycles
    generate
        if (D == 1) begin : g_h1
            always @(posedge clk) held <= b_i;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) fpipe <= 1'b0; else fpipe <= f_i;
        end else begin : g_hn
            always @(posedge clk) held <= {b_i, held[BW*D-1:BW]};
            always @(posedge clk or negedge rst_n)
                if (!rst_n) fpipe <= {D{1'b0}}; else fpipe <= {fpipe[D-2:0], f_i};
        end
    endgenerate
    /* verilator lint_off UNUSEDSIGNAL */   // word[WP-1:W] = zero pad of the last beat when W % BEATS != 0
    wire [WP-1:0] word = {b_i, held};
    /* verilator lint_on UNUSEDSIGNAL */
    assign v_o = fpipe[D-1];
    assign d_o = v_o ? word[W-1:0] : {W{1'b0}};
    generate
        if (DS == 0) begin : g_s0
            assign s_o = s_i;
        end else begin : g_s
            reg [SW*DS-1:0] sp;
            if (DS == 1) begin : g_s1
                always @(posedge clk) sp <= s_i;
            end else begin : g_sn
                always @(posedge clk) sp <= {sp[SW*(DS-1)-1:0], s_i};
            end
            assign s_o = sp[SW*DS-1 -: SW];
        end
    endgenerate
endmodule
`default_nettype wire
