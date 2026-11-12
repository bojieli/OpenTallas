`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-HALFWIDTH-1 (2026-11-12): default-off 2-beat (half-width) transit lane endpoints for a registered bundle crossing
// (HBM structural event, plan delta halfwidth_b10x_1112 and the qq set: lane.beats = BEATS (2 or 4), lane.word_bits = W,
// lane port = ceil(W/BEATS) + 1).
//
//   producer partition:  d[W-1:0] -> ot_hbm_hw_lane_tx -> {b_o[BW-1:0], f_o}  (BW = ceil(W/2); the plan port width BW + 1)
//                        ... the lane's boundary flops and ft stations, unchanged except for the width ...
//   consumer partition:  {b_i, f_i} -> ot_hbm_hw_lane_rx -> q[W-1:0]
//
// The beat engine is rtl/common/ot_bus_gear.sv (BUS-GEAR-1, merged): beat 0 first, f = first-beat flag.  This file adds
// what a bundle lane needs and the BUS-GEAR PC write lane does not have: the bundles carried here are cut sets of
// scheduled registers (pulses, held levels and payload); they have NO word-valid pin.  The word clock is therefore a free-
// running period-BEATS slot generated in the TX and locked to the producer's schedule on the first activity:
//   slot0 = the cycle of the first nonzero non-payload bit, then every second cycle.  One word (the whole bundle, W bits) is
//   sampled at each slot0; ot_bus_gear sends it as beat 0 (cycle +1, with f) and beat 1 (cycle +2).
//
// Three bit classes (parameters, per lane, from the lane's leaf list):
//   CONTROL_MASK : pulses / valids / events.  Must be 0 on every slot 1..BEATS-1 cycle (premise P1).  RX shows a pulse for ONE cycle,
//                  the cycle the word completes (zero in between), exactly like the 1-beat lane shows it.
//   PAYLOAD_MASK : data bits only meaningful beside a control bit; may change on slot1 (garbage); RX holds the slot0 value.
//   all others   : LEVELS (state, fills, counters, done / fault levels).  Must be stable over a BEATS-cycle group
//                  (premise P2: a level changes only on a slot0 cycle).  RX holds the sampled value.
// Under P1 and P2 the RX output is EXACTLY the 1-beat lane output delayed by BEATS - 1 cycles (word_cycles = cycles + BEATS - 1) on all
// CONTROL and LEVEL bits, and on PAYLOAD bits on every cycle where the beside-control is set.  P1 is checked in the TX
// (sticky fault_o, never arbitrated); P2 is checked when GUARD_LEVELS = 1 (one extra W-bit register: a sim / bring-up
// guard, 0 in the physical kit).  No ready, no credit, no queue: the lane is a static-schedule crossing (METHODOLOGY 1.1).
//
// HW = 0: both modules are wires (b_o = d, q = b_i, no flop, no fault) and the lane keeps its plan width W; the generator
// emits the ordinary u_bout / u_bin only for such a lane, so the bind output is byte-identical to today.
// BEATS = 4: same structure, the RX holds each word 4 cycles, spacing fault is the TX guard.
// MUT (bench only, 0 in every kit): TX 1 = beats reversed, 2 / 3 = ot_bus_gear mutants, 4 = P1 guard off;
//                                   RX 5 = beat 0 dropped, 6 = control bits held between words, 7 = hold not driven.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_hw_lane_tx #(
    parameter integer W = 601,
    parameter integer HW = 1,
    parameter integer BEATS = 2,           // 2 or 4 (word_bits W, port ceil(W/BEATS) + 1)
    parameter [W-1:0] CONTROL_MASK = {W{1'b0}},
    parameter [W-1:0] PAYLOAD_MASK = {W{1'b0}},
    parameter integer GUARD_LEVELS = 0,
    parameter integer MUT = 0,
    localparam integer BW = (W + BEATS - 1) / BEATS,
    localparam integer OW = (HW != 0) ? BW : W
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [W-1:0] d,
    output wire [OW-1:0] b_o,
    output wire f_o,
    output wire fault_o
);
    generate
        if (HW == 0) begin : g_off
            assign b_o = d;
            assign f_o = 1'b0;
            assign fault_o = 1'b0;
            /* verilator lint_off UNUSEDSIGNAL */
            wire unused_off = clk ^ rst_n;
            /* verilator lint_on UNUSEDSIGNAL */
        end else begin : g_on
            localparam [W-1:0] LEVEL_MASK = ~(CONTROL_MASK | PAYLOAD_MASK);
            reg lock;             // slot generator locked to the producer
            localparam integer PB = $clog2(BEATS);
            reg [PB-1:0] ph;      // slot index 0 .. BEATS-1 (valid when lock); slot 0 samples the word
            reg pf;               // sticky: premise P1 / P2 violated
            wire act = |(d & ~PAYLOAD_MASK);
            wire s0 = lock ? (ph == {PB{1'b0}}) : act;                       // this cycle is a slot0: sample the bundle
            wire nz = lock && (ph != {PB{1'b0}});          // a slot 1 .. BEATS-1 cycle
            wire bad1 = nz && (|(d & CONTROL_MASK));
            wire badl;
            if (GUARD_LEVELS != 0) begin : g_lv
                reg [W-1:0] dp;
                always @(posedge clk) dp <= d;
                assign badl = nz && (|((d ^ dp) & LEVEL_MASK));
            end else begin : g_nolv
                assign badl = 1'b0;
            end
            always @(posedge clk) begin           // synchronous reset (METHODOLOGY 4.5)
                if (!rst_n) begin
                    lock <= 1'b0; ph <= {PB{1'b0}}; pf <= 1'b0;
                end else begin
                    if (!lock) begin
                        if (act) begin lock <= 1'b1; ph <= PB'(1); end
                    end else begin
                        ph <= (ph == PB'(BEATS - 1)) ? {PB{1'b0}} : ph + 1'b1;
                    end
                    if ((bad1 && MUT != 4) || badl) pf <= 1'b1;
                end
            end
            wire gf;
            ot_bus_gear_tx #(.W(W), .BEATS(BEATS), .MUT((MUT >= 1 && MUT <= 3) ? MUT : 0)) u_gear (
                .clk(clk), .rst_n(rst_n), .v_i(s0), .d_i(d), .b_o(b_o), .f_o(f_o), .fault_o(gf));
            assign fault_o = gf | pf;
        end
    endgenerate
endmodule

module ot_hbm_hw_lane_rx #(
    parameter integer W = 601,
    parameter integer HW = 1,
    parameter integer BEATS = 2,
    parameter [W-1:0] CONTROL_MASK = {W{1'b0}},
    parameter integer MUT = 0,
    localparam integer BW = (W + BEATS - 1) / BEATS,
    localparam integer IW = (HW != 0) ? BW : W
) (
    input  wire clk,
    input  wire rst_n,
    input  wire [IW-1:0] b_i,
    input  wire f_i,
    output wire [W-1:0] q
);
    generate
        if (HW == 0) begin : g_off
            assign q = b_i;
            /* verilator lint_off UNUSEDSIGNAL */
            wire unused_off = clk ^ rst_n ^ f_i;
            /* verilator lint_on UNUSEDSIGNAL */
        end else begin : g_on
            wire v_o;
            wire [W-1:0] d_o;
            wire [BW-1:0] bm = (MUT == 5 && f_i) ? {BW{1'b0}} : b_i;
            /* verilator lint_off PINCONNECTEMPTY */
            ot_bus_gear_rx #(.W(W), .BEATS(BEATS), .SW(1)) u_gear (
                .clk(clk), .rst_n(rst_n), .b_i(bm), .f_i(f_i), .s_i(1'b0), .v_o(v_o), .d_o(d_o), .s_o());
            /* verilator lint_on PINCONNECTEMPTY */
            reg seen;                       // hold register content valid (no reset on the W-bit datapath, METHODOLOGY 2.6)
            reg [W-1:0] hold;
            wire [W-1:0] hq = (MUT == 6) ? hold : (hold & ~CONTROL_MASK);
            assign q = v_o ? d_o : ((seen && MUT != 7) ? hq : {W{1'b0}});
            always @(posedge clk) begin
                if (!rst_n) seen <= 1'b0; else if (v_o) seen <= 1'b1;
                if (v_o) hold <= d_o;
            end
        end
    endgenerate
endmodule
`default_nettype wire
