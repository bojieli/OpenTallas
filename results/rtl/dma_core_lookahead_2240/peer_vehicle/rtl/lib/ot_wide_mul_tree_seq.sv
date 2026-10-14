`timescale 1ns/1ps
// Wide sequential unsigned multiplier with a balanced carry-save reduction.
// The transaction interface, bit emission and cycle count match ot_wide_mul_seq.
// Reduce BITS_PER_STEP partial products and the accumulator pair together using
// 3:2 compressors: the default 18 inputs take six levels rather than sixteen.
// No rounding occurs in the tree. The two outputs represent the same integer
// modulo 2**ACC; the existing accumulator headroom and low-bit emission retain
// the exact product. Inputs a and b follow the original unit's hold contract.
// This candidate stays separate until routed area/timing justify integration.
module ot_wide_mul_tree_seq #(
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

    // Reduce the independent partial products and the redundant accumulator
    // together. Each level compresses groups of three to two, so depth grows
    // logarithmically instead of one dependent compressor per multiplier bit.
    function automatic integer row_count(input integer level);
        integer n, k;
        begin
            n = BITS_PER_STEP + 2;
            for (k = 0; k < level; k = k + 1)
                n = (n / 3) * 2 + n % 3;
            row_count = n;
        end
    endfunction
    function automatic integer tree_depth(input integer n_in);
        integer n;
        begin
            n = n_in;
            tree_depth = 0;
            while (n > 2) begin
                n = (n / 3) * 2 + n % 3;
                tree_depth = tree_depth + 1;
            end
        end
    endfunction
    localparam integer LEVELS = tree_depth(BITS_PER_STEP + 2);
    localparam integer ROWS = BITS_PER_STEP + 2;
    wire [ACC-1:0] rows [0:(LEVELS+1)*ROWS-1];
    assign rows[(0)*ROWS+(0)] = acc_s;
    assign rows[(0)*ROWS+(1)] = acc_c << 1;
    genvar g, level, group, tail;
    generate
        for (g = 0; g < BITS_PER_STEP; g = g + 1) begin : partial_product
            assign rows[(0)*ROWS+(g+2)] = chunk[g] ? (a_ext << g) : {ACC{1'b0}};
        end
        for (level = 0; level < LEVELS; level = level + 1) begin : compress_level
            for (group = 0; group < row_count(level)/3; group = group + 1) begin : triple
                wire [ACC-1:0] x = rows[(level)*ROWS+(3*group)];
                wire [ACC-1:0] y = rows[(level)*ROWS+(3*group+1)];
                wire [ACC-1:0] z = rows[(level)*ROWS+(3*group+2)];
                assign rows[(level+1)*ROWS+(2*group)] = x ^ y ^ z;
                assign rows[(level+1)*ROWS+(2*group+1)] =
                    ((x & y) | (x & z) | (y & z)) << 1;
            end
            for (tail = 0; tail < row_count(level)%3; tail = tail + 1) begin : remainder
                assign rows[(level+1)*ROWS+(2*(row_count(level)/3)+tail)] =
                    rows[(level)*ROWS+(3*(row_count(level)/3)+tail)];
            end
        end
    endgenerate
    // The final level always compresses three rows to a sum and shifted carry.
    // Restore the existing s + 2*c representation for emission and feedback.
    wire [ACC-1:0] fin_s = rows[(LEVELS)*ROWS+(0)];
    wire [ACC-1:0] fin_c = rows[(LEVELS)*ROWS+(1)] >> 1;
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
