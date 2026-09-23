`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Restoring division of a WIDE numerator by a WIDE denominator, BITS_PER_STEP
// quotient bits per clock, keeping only the low QUOT_BITS of the quotient.
//
// WHY THIS EXISTS. ot_a3_fp32_transcendental_cr_rne's sigmoid transform spells an
// exact rational division as a function -- ``divide_fixed_ratio`` -- whose loop
// runs over all 328 bits of the numerator with a 165-bit compare-and-subtract at
// every step. Unrolled into one cycle that is some 54,000 levels of carry logic,
// and it is not merely slow: YOSYS NEVER FINISHED IT. A synthesis of that block
// ran 8 hours inside the pinned container and timed out in 1_2_yosys, so the
// module has no ASAP7 record at all, and twelve of the design's forty-five
// uncovered modules sit behind it and its siblings.
//
// ONE SUBTRACT PER STEP, WHICH IS WHY BITS_PER_STEP IS USUALLY ONE. The compare
// and the difference come from the same subtraction -- its borrow IS the
// comparison -- so a step costs one DEN_BITS+1 subtract. That measures 296.5 MHz
// alone on ASAP7 at these widths, so a second step in the same cycle would halve
// the clock; a wide-denominator divide is the one place in this design where
// bits-per-cycle is not a free knob.
//
// THE QUOTIENT WINDOW IS THE CALLER'S, NOT AN OPTIMISATION. divide_fixed_ratio
// records a quotient bit only for ``divide_bit <= FRAC_BITS+2`` and discards the
// rest, because the true quotient is bounded by one in Q0.FRAC_BITS. Digits are
// shifted into a QUOT_BITS-wide register here, so the early ones fall off the top
// exactly as they were dropped there.
//
// THE TRANSFORMATION IS TIMING ONLY: the same restoring steps in the same order
// over the same bits, with the partial remainder in a register.
// rtl/test/tb_wide_div_seq_equiv.sv checks the quotient and the remainder-nonzero
// flag against the unrolled function over its own corpus.
// ---------------------------------------------------------------------------
module ot_wide_div_seq #(
    parameter integer NUM_BITS = 328,
    parameter integer DEN_BITS = 164,
    parameter integer QUOT_BITS = 163,
    parameter integer BITS_PER_STEP = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [NUM_BITS-1:0]  numerator,
    input  wire [DEN_BITS-1:0]  denominator,
    output wire                 busy,
    output reg                  done,
    output reg [QUOT_BITS-1:0]  quotient,
    output reg                  inexact
);
    localparam integer STEPS = (NUM_BITS + BITS_PER_STEP - 1) / BITS_PER_STEP;
    localparam integer PADDED = STEPS * BITS_PER_STEP;
    localparam integer COUNT_BITS = (STEPS < 2) ? 1 : $clog2(STEPS + 1);
    localparam [31:0] STEPS_CODE = STEPS;
    localparam [COUNT_BITS-1:0] ONE_STEP = {{(COUNT_BITS-1){1'b0}}, 1'b1};

    reg [PADDED-1:0]     work;      //: numerator bits not yet consumed, MSB first
    reg [QUOT_BITS-1:0]  quot;
    reg [DEN_BITS-1:0]   rem;
    reg [COUNT_BITS-1:0] steps_left;
    reg                  running;

    assign busy = running;

    wire [BITS_PER_STEP-1:0] chunk = work[PADDED-1 -: BITS_PER_STEP];

    //: The unrolled loop's body, BITS_PER_STEP times. The shifted remainder is
    //: DEN_BITS+1 wide and the difference is truncated back to DEN_BITS, which
    //: loses nothing: a restoring step leaves the remainder below the divisor.
    reg [DEN_BITS:0]        shifted;
    reg [DEN_BITS:0]        difference;
    reg [DEN_BITS-1:0]      walk;
    reg [DEN_BITS-1:0]      next_rem;
    reg [BITS_PER_STEP-1:0] step_digit;
    integer j;
    always @* begin
        walk = rem;
        step_digit = {BITS_PER_STEP{1'b0}};
        for (j = BITS_PER_STEP - 1; j >= 0; j = j - 1) begin
            shifted = {walk, chunk[j]};
            if (shifted >= {1'b0, denominator}) begin
                difference = shifted - {1'b0, denominator};
                walk = difference[DEN_BITS-1:0];
                step_digit[j] = 1'b1;
            end else begin
                walk = shifted[DEN_BITS-1:0];
            end
        end
        next_rem = walk;
    end

    wire [QUOT_BITS-1:0] quot_next = (quot << BITS_PER_STEP) |
                                     {{(QUOT_BITS-BITS_PER_STEP){1'b0}}, step_digit};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; done <= 1'b0;
            quotient <= {QUOT_BITS{1'b0}};
            inexact <= 1'b0;
            work <= {PADDED{1'b0}};
            quot <= {QUOT_BITS{1'b0}};
            rem <= {DEN_BITS{1'b0}};
            steps_left <= {COUNT_BITS{1'b0}};
        end else begin
            done <= 1'b0;
            if (!running) begin
                if (start) begin
                    work <= {{(PADDED-NUM_BITS){1'b0}}, numerator};
                    quot <= {QUOT_BITS{1'b0}};
                    rem <= {DEN_BITS{1'b0}};
                    steps_left <= STEPS_CODE[COUNT_BITS-1:0];
                    running <= 1'b1;
                end
            end else begin
                work <= work << BITS_PER_STEP;
                quot <= quot_next;
                rem <= next_rem;
                if (steps_left == ONE_STEP) begin
                    running <= 1'b0;
                    done <= 1'b1;
                    quotient <= quot_next;
                    inexact <= |next_rem;
                end
                steps_left <= steps_left - ONE_STEP;
            end
        end
    end
endmodule
