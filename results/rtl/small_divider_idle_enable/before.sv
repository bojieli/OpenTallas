`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Restoring division of a WIDE dividend by a SMALL divisor, BITS_PER_STEP bits
// of quotient per clock.
//
// WHY THIS EXISTS. ot_a3_fp32_exp_pos_cr_rne and
// ot_a3_fp32_transcendental_cr_rne both advance a Taylor term by
// ``term * r / (k+1)``, and both spelled the division as a FUNCTION -- a
// restoring loop over every bit of the dividend, which elaborates to one
// compare-subtract stage per bit in a single cycle. At FRAC_BITS = 160 that is
// 163 stages of a ten-bit subtract chained end to end, and the routed evidence
// says exactly what that costs: ot_a3_fp32_exp_pos_cr_rne's worst setup path
// runs reduced[40] -> interval_upper[162] through 2,135 cell delays for 57.2 ns,
// against a 4 ns target -- 17.5 MHz, the slowest block in the design by 15x.
// (results/physical_abi3/asap7/a3_fp32_exp_pos_cr_rne/pnr_4p0ns_not_met.json)
//
// THE TRANSFORMATION IS TIMING ONLY. This module runs the SAME restoring loop
// over the same bits in the same order; it only stops after BITS_PER_STEP of
// them and keeps the partial remainder in a register. Every intermediate
// remainder and every quotient bit is the one the unrolled loop produced, so the
// quotient and the inexact flag are bit-identical for every input -- not
// approximately, by construction. rtl/test/tb_wide_div_small_seq_equiv.sv checks
// that against the unrolled function itself over the full argument corpus rather
// than asserting it.
//
// THE DIVIDEND IS PADDED AT THE TOP, NOT THE BOTTOM. STEPS*BITS_PER_STEP can
// exceed WIDTH, and the padding has to be leading zeros: those produce quotient
// bits of zero and leave the remainder at zero, so the answer is unchanged.
// Padding at the bottom would compute ``dividend * 2**pad / divisor`` instead.
//
// BITS_PER_STEP IS THE TIMING KNOB. The combinational path is BITS_PER_STEP
// chained compare-subtracts of DIVISOR_BITS+1 bits, so the delay is linear in it
// and the cycle count is WIDTH/BITS_PER_STEP. Nothing here picks the value; the
// caller does, against measurement.
// ---------------------------------------------------------------------------
module ot_wide_div_small_seq #(
    parameter integer WIDTH = 163,
    parameter integer DIVISOR_BITS = 9,
    parameter integer BITS_PER_STEP = 8
) (
    input  wire                    clk,
    input  wire                    rst_n,
    //: Accepted only while ``busy`` is low.
    input  wire                    start,
    input  wire [WIDTH-1:0]        dividend,
    input  wire [DIVISOR_BITS-1:0] divisor,
    output wire                    busy,
    //: One cycle, with ``quotient`` and ``inexact`` valid alongside it.
    output reg                     done,
    output reg  [WIDTH-1:0]        quotient,
    output reg                     inexact
);
    localparam integer STEPS = (WIDTH + BITS_PER_STEP - 1) / BITS_PER_STEP;
    localparam integer PADDED = STEPS * BITS_PER_STEP;
    localparam integer COUNT_BITS = (STEPS < 2) ? 1 : $clog2(STEPS + 1);
    //: Sized, because indexing a bare integer localparam is not portable
    //: across the two elaborators this repository runs.
    localparam [31:0] STEPS_CODE = STEPS;
    localparam [COUNT_BITS-1:0] ONE_STEP = {{(COUNT_BITS-1){1'b0}}, 1'b1};

    reg [PADDED-1:0]       work;        //: unconsumed dividend above produced quotient
    // Each step consumes the high chunk and inserts quotient bits below.
    // Produced bits cannot reach the high chunk before the final step, so a
    // separate quotient shift register would duplicate PADDED storage bits.
    reg [DIVISOR_BITS:0]   rem;         //: partial remainder, always < divisor
    reg [COUNT_BITS-1:0]   steps_left;
    reg                    running;

    // Capture both operands at acceptance. The small divisor register breaks
    // the external-input path into the entire restoring chain, without an
    // added cycle: the first chunk is evaluated after the start edge.
    reg [DIVISOR_BITS-1:0] divisor_q;
    always @(posedge clk) begin
        if (!running && start) divisor_q <= divisor;
    end

    assign busy = running;

    //: One cycle: BITS_PER_STEP steps of the unrolled loop, MSB of the chunk
    //: first, over a remainder that never reaches DIVISOR_BITS+1 bits because a
    //: restoring step leaves it below the divisor.
    wire [BITS_PER_STEP-1:0] chunk = work[PADDED-1 -: BITS_PER_STEP];
    reg [DIVISOR_BITS:0]     walk;
    reg [DIVISOR_BITS:0]     next_rem;
    reg [BITS_PER_STEP-1:0]  step_digit;
    integer j;
    always @* begin
        walk = rem;
        step_digit = {BITS_PER_STEP{1'b0}};
        for (j = BITS_PER_STEP - 1; j >= 0; j = j - 1) begin
            walk = {walk[DIVISOR_BITS-1:0], chunk[j]};
            if (walk >= {1'b0, divisor_q}) begin
                walk = walk - {1'b0, divisor_q};
                step_digit[j] = 1'b1;
            end
        end
        next_rem = walk;
    end

    //: Named rather than indexed in place: indexing an EXPRESSION is rejected
    //: by both elaborators, which is the same shape that has cost this
    //: repository several compile failures.
    wire [PADDED-1:0] quot_next = (work << BITS_PER_STEP) |
                                 {{(PADDED-BITS_PER_STEP){1'b0}}, step_digit};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0;
            done <= 1'b0;
            quotient <= {WIDTH{1'b0}};
            inexact <= 1'b0;
            work <= {PADDED{1'b0}};
            rem <= {(DIVISOR_BITS+1){1'b0}};
            steps_left <= {COUNT_BITS{1'b0}};
        end else begin
            done <= 1'b0;
            if (!running) begin
                if (start) begin
                    work <= {{(PADDED-WIDTH){1'b0}}, dividend};
                    rem <= {(DIVISOR_BITS+1){1'b0}};
                    steps_left <= STEPS_CODE[COUNT_BITS-1:0];
                    running <= 1'b1;
                end
            end else begin
                work <= quot_next;
                rem <= next_rem;
                if (steps_left == ONE_STEP) begin
                    running <= 1'b0;
                    done <= 1'b1;
                    quotient <= quot_next[WIDTH-1:0];
                    inexact <= |next_rem;
                end
                steps_left <= steps_left - ONE_STEP;
            end
        end
    end
endmodule
