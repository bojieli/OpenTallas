`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Wide unsigned multiply, BITS_PER_STEP bits of the multiplier per clock, with a
// CARRY-SAVE accumulator so no cycle ever contains a wide carry chain.
//
// WHY THIS EXISTS. ot_a3_fp32_exp_pos_cr_rne spells three 161-by-163 products as
// the ``*`` operator -- ``term_lower * reduced``, ``term_upper * reduced`` and
// ``x_fixed * LOG2E`` -- and each elaborates to a full multiplier tree ending in
// a 324-bit carry-propagate adder. The routed evidence: 373,426 cells and
// 35,845 um2 for a block that computes one exponential, which is also why the
// route took 7.2 hours.
// (results/physical_abi3/asap7/a3_fp32_exp_pos_cr_rne/pnr_4p0ns_not_met.json)
//
// THE ACCUMULATOR NEVER CARRIES. A cycle adds BITS_PER_STEP partial products to
// a redundant pair ``(s, c)`` standing for ``s + 2*c``; each addition is one
// carry-save level -- an XOR3 and a MAJ3 per bit, no propagation. The ONLY
// carry-propagate adder in the design is BITS_PER_STEP+1 bits wide, and it is
// there to emit the low BITS_PER_STEP product bits, which are final: their
// carries have already been absorbed, and the carry OUT of them is folded back
// into the shifted accumulator as a third CSA input. So the critical path is
// BITS_PER_STEP+1 carry-save levels plus a small adder, and the cycle count is
// (WA+WB)/BITS_PER_STEP.
//
// PRODUCT BITS LEAVE FROM THE BOTTOM, WHICH IS WHAT THE CALLERS WANT. Both
// consumers need the top of the product exactly and the bottom only as "was
// anything discarded": exp_pos takes ``scaled[2*FRAC_BITS+2:FRAC_BITS]`` and
// ``|scaled[FRAC_BITS-1:0]``, and the range reduction takes nine bits at
// ``2*FRAC_BITS`` and none below. So the low LOW_BITS bits are OR-reduced as they
// are emitted and never stored, and only the rest is kept.
//
// THE ACCUMULATOR IS OVERSIZED ON PURPOSE. A carry-save level can push a set bit
// one position up (``c`` is shifted left when it re-enters as an addend), so a
// chain of BITS_PER_STEP of them can creep BITS_PER_STEP positions above the true
// magnitude before the next shift brings it back. ACC carries twice
// BITS_PER_STEP of headroom over WA for that reason; losing the top bit would be
// a silent wrong product, and rtl/test/tb_wide_mul_seq_equiv.sv checks against
// ``*`` itself rather than trusting the bound.
//
// LOW_BITS MUST BE A MULTIPLE OF BITS_PER_STEP. The split between "OR-reduced"
// and "kept" happens at a chunk boundary, so a split inside a chunk is refused at
// elaboration rather than silently mis-binned.
// ---------------------------------------------------------------------------
module ot_wide_mul_seq #(
    parameter integer WA = 163,
    parameter integer WB = 161,
    parameter integer BITS_PER_STEP = 16,
    //: Product bits below this are OR-reduced into ``low_nonzero``; the rest are
    //: kept in ``product_high``.
    parameter integer LOW_BITS = 160
) (
    input  wire            clk,
    input  wire            rst_n,
    //: Accepted only while ``busy`` is low.
    input  wire            start,
    input  wire [WA-1:0]   a,
    input  wire [WB-1:0]   b,
    output wire            busy,
    //: One cycle, with both results valid alongside it.
    output reg             done,
    output reg  [WA+WB-LOW_BITS-1:0] product_high,
    output reg             low_nonzero
);
    localparam integer TOTAL = WA + WB;
    localparam integer STEPS = (TOTAL + BITS_PER_STEP - 1) / BITS_PER_STEP;
    localparam integer LOW_STEPS = LOW_BITS / BITS_PER_STEP;
    localparam integer HIGH_PAD = STEPS * BITS_PER_STEP - LOW_BITS;
    localparam integer ACC = WA + 2 * BITS_PER_STEP + 4;
    localparam integer COUNT_BITS = (STEPS < 2) ? 1 : $clog2(STEPS + 1);
    localparam [31:0] STEPS_CODE = STEPS;
    localparam [31:0] LOW_STEPS_CODE = LOW_STEPS;
    localparam [COUNT_BITS-1:0] ONE_STEP = {{(COUNT_BITS-1){1'b0}}, 1'b1};

    //: Elaboration-time refusal, not a comment: a split inside a chunk would
    //: mis-bin product bits and the OR would be silently short.
    initial begin
        if (LOW_BITS % BITS_PER_STEP != 0) begin
            $display("FATAL ot_wide_mul_seq: LOW_BITS %0d is not a multiple of BITS_PER_STEP %0d",
                     LOW_BITS, BITS_PER_STEP);
            $finish;
        end
        //: BITS_PER_STEP of one would make the emission adder a single bit and
        //: ``fin_c[BITS_PER_STEP-2:0]`` an empty select, which neither elaborator
        //: accepts. Two is the narrowest chunk, and one bit per cycle is not a
        //: design point any caller wants.
        if (BITS_PER_STEP < 2) begin
            $display("FATAL ot_wide_mul_seq: BITS_PER_STEP %0d is below two",
                     BITS_PER_STEP);
            $finish;
        end
    end

    reg [ACC-1:0]          acc_s, acc_c;
    reg [WB-1:0]           b_work;      //: multiplier bits not yet consumed
    reg [HIGH_PAD-1:0]     high_pad;
    reg                    low_or;
    reg [COUNT_BITS-1:0]   steps_left;
    reg                    running;
    reg [COUNT_BITS-1:0]   emitted;

    assign busy = running;

    wire [BITS_PER_STEP-1:0] chunk = b_work[BITS_PER_STEP-1:0];
    wire [ACC-1:0]           a_ext = {{(ACC-WA){1'b0}}, a};

    //: One carry-save level per partial product. The pair (x, y) enters as
    //: ``s`` and ``c<<1`` so that the running value is exactly ``s + 2*c``
    //: before and after.
    wire [ACC-1:0] cs_s [0:BITS_PER_STEP];
    wire [ACC-1:0] cs_c [0:BITS_PER_STEP];
    assign cs_s[0] = acc_s;
    assign cs_c[0] = acc_c;
    genvar g;
    generate
        for (g = 0; g < BITS_PER_STEP; g = g + 1) begin : partial_product
            wire [ACC-1:0] x = cs_s[g];
            wire [ACC-1:0] y = {cs_c[g][ACC-2:0], 1'b0};
            wire [ACC-1:0] z = chunk[g] ? (a_ext << g) : {ACC{1'b0}};
            assign cs_s[g+1] = x ^ y ^ z;
            assign cs_c[g+1] = (x & y) | (x & z) | (y & z);
        end
    endgenerate

    //: The only carry-propagate adder here. The low BITS_PER_STEP bits of
    //: ``s + 2*c`` are final product bits; bit BITS_PER_STEP is their carry out.
    wire [ACC-1:0] fin_s = cs_s[BITS_PER_STEP];
    wire [ACC-1:0] fin_c = cs_c[BITS_PER_STEP];
    wire [BITS_PER_STEP:0] emit_sum =
        {1'b0, fin_s[BITS_PER_STEP-1:0]} +
        {1'b0, fin_c[BITS_PER_STEP-2:0], 1'b0};
    wire [BITS_PER_STEP-1:0] emit = emit_sum[BITS_PER_STEP-1:0];
    wire                     emit_carry = emit_sum[BITS_PER_STEP];

    //: ``(s + 2c) >> BITS_PER_STEP`` is ``(s >> B) + (c >> (B-1)) + carry``, and
    //: those three fold to a redundant pair with one more carry-save level.
    wire [ACC-1:0] shift_x = fin_s >> BITS_PER_STEP;
    wire [ACC-1:0] shift_y = fin_c >> (BITS_PER_STEP - 1);
    wire [ACC-1:0] shift_z = {{(ACC-1){1'b0}}, emit_carry};
    wire [ACC-1:0] next_s = shift_x ^ shift_y ^ shift_z;
    wire [ACC-1:0] next_c = (shift_x & shift_y) | (shift_x & shift_z) |
                            (shift_y & shift_z);

    wire in_low_half = (emitted < LOW_STEPS_CODE[COUNT_BITS-1:0]);
    wire last_step = (steps_left == ONE_STEP);
    //: The kept chunks arrive lowest-first and are inserted at the TOP of a
    //: register shifted right by one chunk each time, so after HIGH_PAD/
    //: BITS_PER_STEP insertions the first one has reached bit zero. With exactly
    //: one kept chunk there is nothing to shift and the part-select below would
    //: be empty, which is a generate-if rather than a ternary because both
    //: elaborators evaluate the select in a ternary.
    wire [HIGH_PAD-1:0] high_next;
    generate
        if (HIGH_PAD <= BITS_PER_STEP) begin : one_kept_chunk
            assign high_next = emit[HIGH_PAD-1:0];
        end else begin : many_kept_chunks
            assign high_next = {emit, high_pad[HIGH_PAD-1:BITS_PER_STEP]};
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; done <= 1'b0;
            product_high <= {(TOTAL-LOW_BITS){1'b0}};
            low_nonzero <= 1'b0;
            acc_s <= {ACC{1'b0}}; acc_c <= {ACC{1'b0}};
            b_work <= {WB{1'b0}}; high_pad <= {HIGH_PAD{1'b0}};
            low_or <= 1'b0; steps_left <= {COUNT_BITS{1'b0}};
            emitted <= {COUNT_BITS{1'b0}};
        end else begin
            done <= 1'b0;
            if (!running) begin
                if (start) begin
                    acc_s <= {ACC{1'b0}}; acc_c <= {ACC{1'b0}};
                    b_work <= b;
                    high_pad <= {HIGH_PAD{1'b0}};
                    low_or <= 1'b0;
                    steps_left <= STEPS_CODE[COUNT_BITS-1:0];
                    emitted <= {COUNT_BITS{1'b0}};
                    running <= 1'b1;
                end
            end else begin
                acc_s <= next_s;
                acc_c <= next_c;
                b_work <= b_work >> BITS_PER_STEP;
                emitted <= emitted + ONE_STEP;
                steps_left <= steps_left - ONE_STEP;
                if (in_low_half) low_or <= low_or | (|emit);
                else high_pad <= high_next;
                if (last_step) begin
                    running <= 1'b0;
                    done <= 1'b1;
                    //: The final chunk is high by construction -- LOW_STEPS is
                    //: strictly below STEPS for every caller here -- so the
                    //: emitted word is already folded in by ``high_next``.
                    product_high <= high_next[TOTAL-LOW_BITS-1:0];
                    low_nonzero <= low_or | (in_low_half ? (|emit) : 1'b0);
                end
            end
        end
    end
endmodule
