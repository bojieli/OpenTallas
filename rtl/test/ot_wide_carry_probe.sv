`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// A characterisation vehicle: ONE wide primitive per MODE, registered in and
// registered out, so static timing reports the primitive and nothing else.
//
// WHY. ot_a3_fp32_exp_pos_cr_rne is 17.5 MHz and the routed worst path is 2,135
// cell delays, which the unrolled restoring divide explains. But the block is
// full of OTHER 163- and 170-bit operations -- adds, a subtract, two
// comparators, an increment, a 163-bit priority encode written as a loop -- and
// each of those is a carry or mux chain of its own. Guessing which ones matter
// is how a rewrite lands on the wrong thing, so each is measured alone, at
// synthesis and pre-layout timing, which costs seconds rather than the seven
// hours a full route of that block takes.
//
// This lives under rtl/test because it is not part of any design: it is
// instantiated by nothing and the coverage audit excludes the directory.
// ---------------------------------------------------------------------------
module ot_wide_carry_probe #(
    parameter integer MODE = 0,
    parameter integer FRAC_BITS = 160,
    parameter integer INT_BITS = 9
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [255:0] operand_a,
    input  wire [255:0] operand_b,
    output reg  [255:0] result
);
    localparam integer W = FRAC_BITS + 3;    //: 163, the enclosure endpoint width
    localparam integer WIDE = FRAC_BITS + INT_BITS;

    reg [255:0] a_q, b_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_q <= 256'd0; b_q <= 256'd0; end
        else begin a_q <= operand_a; b_q <= operand_b; end
    end

    wire [W-1:0]    aw = a_q[W-1:0];
    wire [W-1:0]    bw = b_q[W-1:0];
    wire [WIDE:0]   ax = a_q[WIDE:0];
    wire [WIDE:0]   bx = b_q[WIDE:0];

    localparam [FRAC_BITS:0] LN2 =
        161'h0b17217f7d1cf79abc9e3b39803f2f6af40f34326;

    //: MODE 4 and 5 are the same function, written the two ways the rewrite
    //: chooses between: a linear scan for the top set bit, and a two-level
    //: group-then-bit encode. Both must return the same index.
    function automatic [8:0] top_set_scan;
        input [W-1:0] value;
        integer bit_index, found;
        begin
            found = 0;
            for (bit_index = 0; bit_index < W; bit_index = bit_index + 1)
                if (value[bit_index]) found = bit_index;
            top_set_scan = found[8:0];
        end
    endfunction

    localparam integer GROUPS = (W + 7) / 8;
    function automatic [8:0] top_set_tree;
        input [W-1:0] value;
        reg [GROUPS-1:0] any;
        reg [7:0] word;
        integer gi, bi, group, within;
        begin
            any = {GROUPS{1'b0}};
            for (gi = 0; gi < GROUPS; gi = gi + 1)
                for (bi = 0; bi < 8; bi = bi + 1)
                    if (gi * 8 + bi < W)
                        any[gi] = any[gi] | value[gi*8 + bi];
            group = 0;
            for (gi = 0; gi < GROUPS; gi = gi + 1) if (any[gi]) group = gi;
            word = 8'd0;
            for (bi = 0; bi < 8; bi = bi + 1)
                if (group * 8 + bi < W) word[bi] = value[group*8 + bi];
            within = 0;
            for (bi = 0; bi < 8; bi = bi + 1) if (word[bi]) within = bi;
            top_set_tree = (group * 8 + within);
        end
    endfunction

    //: MODE 6 and 7: the sticky-bit reduction the rounding function needs, as a
    //: chained OR over a loop and as a masked reduction.
    function automatic sticky_scan;
        input [W-1:0] value;
        input [8:0] below;
        integer bit_index;
        reg s;
        begin
            s = 1'b0;
            for (bit_index = 0; bit_index < W; bit_index = bit_index + 1)
                if (bit_index < below) s = s | value[bit_index];
            sticky_scan = s;
        end
    endfunction

    wire [W-1:0] sticky_mask = ({W{1'b1}} >> (W - b_q[7:0])) &
                               {W{|b_q[7:0]}};

    localparam [FRAC_BITS+1:0] LOG2E =
        162'h171547652b82fe1777d0ffda0d23a7d11d6aef551;

    //: ``term * reduced`` keeps bits [2*FRAC_BITS+2:FRAC_BITS] and the OR of the
    //: rest; the OR is free (measured at MODE 7) so the product is what is
    //: measured here.
    function automatic [W-1:0] full_product_high;
        input [W-1:0] term;
        input [W-1:0] reduced;
        reg [2*W-1:0] wide;
        begin
            wide = term * reduced;
            full_product_high = wide[2*FRAC_BITS+2:FRAC_BITS];
        end
    endfunction

    function automatic [11:0] reduce_product_high;
        input [WIDE:0] value;
        reg [2*FRAC_BITS+INT_BITS+2:0] wide;
        begin
            wide = value * LOG2E;
            reduce_product_high = {3'd0, wide[2*FRAC_BITS+8:2*FRAC_BITS]};
        end
    endfunction

    //: ot_a3_fp32_exp_pos_cr_rne's fixed_to_fp32_scaled, verbatim apart from the
    //: parameter names.
    function automatic [32:0] fixed_to_fp32_scaled;
        input [W-1:0]        fixed_code;
        input signed [8:0]   power;
        reg [23:0] main_mantissa;
        reg [24:0] rounded_mantissa;
        reg round_bit, sticky;
        integer most_significant, bit_index, shift_distance;
        integer floor_exponent;
        begin
            main_mantissa = 0; rounded_mantissa = 0;
            round_bit = 0; sticky = 0;
            most_significant = -1; shift_distance = 0;
            fixed_to_fp32_scaled = 33'd0;
            for (bit_index = 0; bit_index < W; bit_index = bit_index + 1)
                if (fixed_code[bit_index]) most_significant = bit_index;
            if (most_significant >= 0) begin
                floor_exponent = most_significant - FRAC_BITS + power;
                shift_distance = most_significant - 23;
                for (bit_index = 0; bit_index < 24; bit_index = bit_index + 1)
                    if ((bit_index + shift_distance >= 0) &&
                        (bit_index + shift_distance < W))
                        main_mantissa[bit_index] =
                            fixed_code[bit_index + shift_distance];
                if (shift_distance > 0)
                    round_bit = fixed_code[shift_distance-1];
                for (bit_index = 0; bit_index < W; bit_index = bit_index + 1)
                    if (bit_index < shift_distance-1)
                        sticky = sticky | fixed_code[bit_index];
                rounded_mantissa = {1'b0, main_mantissa};
                if (round_bit && (sticky || main_mantissa[0]))
                    rounded_mantissa = rounded_mantissa + 1'b1;
                if (rounded_mantissa[24]) begin
                    rounded_mantissa = rounded_mantissa >> 1;
                    floor_exponent = floor_exponent + 1;
                end
                if (floor_exponent > 127)
                    fixed_to_fp32_scaled = {1'b1, 32'd0};
                else
                    fixed_to_fp32_scaled = {1'b0, 1'b0,
                        floor_exponent[7:0] + 8'd127, rounded_mantissa[22:0]};
            end
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) result <= 256'd0;
        else begin
            result <= 256'd0;
            case (MODE)
                0: result <= {{(256-W-1){1'b0}}, aw + bw};                  // 163-bit add
                1: result <= {{(256-W-1){1'b0}}, aw + {{(W-1){1'b0}}, 1'b1}}; // 163-bit increment
                2: result <= {{(256-WIDE-2){1'b0}}, ax - bx};               // 170-bit subtract
                3: result <= {255'd0, (ax < bx)};                           // 170-bit compare
                4: result <= {247'd0, top_set_scan(aw)};                    // top set bit, linear
                5: result <= {247'd0, top_set_tree(aw)};                    // top set bit, two level
                6: result <= {255'd0, sticky_scan(aw, b_q[8:0])};           // sticky, chained
                7: result <= {255'd0, |(aw & sticky_mask)};                 // sticky, masked
                8: result <= {{(256-W-16){1'b0}},                           // 161x16 constant product
                              LN2 * b_q[15:0]};
                9: result <= {{(256-W){1'b0}}, aw >> b_q[7:0]};             // 163-bit barrel shift
                10: result <= {255'd0, (ax >= {{(INT_BITS){1'b0}}, LN2})};  // compare against LN2
                //: The two products exp_pos spells with ``*``: the series
                //: recurrence's term-by-reduced-argument, and the range
                //: reduction's argument-by-log2(e). Only the high half of each
                //: is kept, exactly as the block keeps it, so the probe measures
                //: what the block asks for rather than a wider product.
                11: result <= {{(256-W-1){1'b0}},
                               full_product_high(aw, bw)};
                12: result <= {{(256-12){1'b0}}, reduce_product_high(ax)};
                //: The rounding function whole: find the top set bit, shift the
                //: mantissa down by that much, collect the sticky, round to
                //: nearest-even, re-normalise and check for overflow. Its parts
                //: measure fast individually; this is whether the chain does.
                13: result <= {223'd0, fixed_to_fp32_scaled(aw, 9'sd0)};
                14: result <= {223'd0, fixed_to_fp32_scaled(aw, b_q[8:0])};
                default: result <= 256'd0;
            endcase
        end
    end
endmodule
