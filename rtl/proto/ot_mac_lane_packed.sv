`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Packed MAC lane: PACK multipliers share ONE accumulator.
//
// WHY THIS EXISTS. Measured on ASAP7, the multiplier is a small minority of a
// lane's area:
//
//     format   multiplier   whole lane   multiplier share
//     bf16        46.4 um2    649.6 um2        7.1 %
//     fp8         13.3 um2    571.0 um2        2.3 %
//     mxfp4        7.4 um2    530.4 um2        1.4 %
//
// So the 6.3x multiplier saving from BF16 to MXFP4 becomes an 18 % saving at lane
// level, because the 40-bit accumulator, the align shifter and the split resolve
// dominate and none of them shrink with the weight format. Any claim that low
// precision buys order-of-magnitude arithmetic density is measuring the
// multiplier and quietly charging the accumulator to nobody.
//
// The fix is the one every tensor core uses: amortise the accumulator. PACK
// products are aligned into the shared fixed-point window, summed in an adder
// tree, and accumulated ONCE. The tree is exact -- these are fixed-point integers
// in a common window, so summing them introduces no rounding and the result does
// not depend on tree shape.
//
// MEASURED, AND NOT YET GOOD ENOUGH.  Place-and-routed at PACK=8 with MXFP4
// weights this lane reaches 717 MHz with setup WNS -0.394 ns -- it does NOT close
// -- in 1,975 um2, against the unpacked lane's 1,388 MHz closed in 530 um2.  That
// is 8 MAC/cycle for 3.7x the area: a 2.1x density gain, not the 8x the idea
// promises.
//
// The cause is the adder tree below: summing eight 40-bit aligned terms with `+`
// builds a chain of carry-propagate adders, which is the same carry-chain mistake
// already fixed once in the accumulator loop.  The tree must be carry-save --
// 3:2 compressors reducing eight terms to a (sum, carry) pair, then a 4:2
// compression against the accumulator pair, with no carry propagation anywhere in
// the recurring path.  Until that is done this module is a demonstration that
// sharing the accumulator is the right direction, not a usable lane.
//
// Qualified against runtime.reference.mac_tile: the reference sums the same terms
// in the same window, so a packed lane must agree bit-for-bit with an unpacked one
// over the same operand stream.
// ---------------------------------------------------------------------------
module ot_mac_lane_packed #(
    parameter integer ACC_W       = 40,
    parameter integer EXP_WINDOW  = 16,
    parameter integer PACK        = 8,    // multipliers sharing one accumulator
    parameter integer W_EXP_BITS  = 2,    // MXFP4 E2M1 by default
    parameter integer W_FRAC_BITS = 1
) (
    input  wire                        clk,
    input  wire                        rst_n,
    input  wire                        clear,
    input  wire                        accept,

    // PACK activation/weight pairs arrive together, already registered
    input  wire [16*PACK-1:0]          a,          // BF16 activations
    input  wire [(1+W_EXP_BITS+W_FRAC_BITS)*PACK-1:0] b,
    input  wire [7:0]                  scale_exp,

    output reg  [ACC_W-1:0]            result,
    output reg                         dropped
);
    localparam integer HALF    = ACC_W/2;
    localparam integer W_FMT_W = 1 + W_EXP_BITS + W_FRAC_BITS;
    localparam integer W_SIG_W = 1 + W_FRAC_BITS;
    localparam integer PROD_W  = 8 + W_SIG_W;

    // ---- stage 1: PACK exact significand multiplies ------------------------
    reg                s1_sign [0:PACK-1];
    reg [9:0]          s1_exp  [0:PACK-1];
    reg [PROD_W-1:0]   s1_prod [0:PACK-1];

    // ---- stage 2: align each product, then sum the tree --------------------
    reg [ACC_W-1:0]    s2_sum;
    reg                s2_drop;

    // signed aligned terms, summed exactly in the window
    wire signed [ACC_W-1:0] term [0:PACK-1];
    wire                    drops [0:PACK-1];

    genvar i;
    generate
        for (i = 0; i < PACK; i = i + 1) begin : mul
            wire [15:0]          ai = a[16*i +: 16];
            wire [W_FMT_W-1:0]   bi = b[W_FMT_W*i +: W_FMT_W];

            wire        a_zero = (ai[14:0] == 15'b0);
            wire [7:0]  a_man  = {1'b1, ai[6:0]};
            wire        b_zero = (bi[W_FMT_W-2:0] == {(W_FMT_W-1){1'b0}});
            wire [W_SIG_W-1:0] b_man = {1'b1, bi[W_FRAC_BITS-1:0]};

            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    s1_sign[i] <= 1'b0; s1_exp[i] <= 10'b0;
                    s1_prod[i] <= {PROD_W{1'b0}};
                end else begin
                    s1_sign[i] <= ai[15] ^ bi[W_FMT_W-1];
                    s1_exp[i]  <= {2'b0, ai[14:7]} +
                                  {{(10-W_EXP_BITS){1'b0}},
                                   bi[W_EXP_BITS+W_FRAC_BITS-1:W_FRAC_BITS]};
                    s1_prod[i] <= (a_zero || b_zero) ? {PROD_W{1'b0}}
                                                     : (a_man * b_man);
                end

            wire [9:0]       rel    = s1_exp[i] - {2'b0, scale_exp};
            wire             in_win = (rel[9] == 1'b0) && (rel <= EXP_WINDOW[9:0]);
            wire [4:0]       sh     = in_win ? rel[4:0] : 5'd0;
            wire [ACC_W-1:0] mag    = in_win
                ? ({{(ACC_W-PROD_W){1'b0}}, s1_prod[i]} << sh) : {ACC_W{1'b0}};

            assign term[i]  = s1_sign[i] ? -$signed(mag) : $signed(mag);
            assign drops[i] = !in_win && (s1_prod[i] != {PROD_W{1'b0}});
        end
    endgenerate

    // The tree is exact: fixed-point integers in one window, so no rounding and
    // no dependence on association order.
    integer t;
    reg signed [ACC_W-1:0] tree;
    reg                    any_drop;
    always @* begin
        tree = {ACC_W{1'b0}};
        any_drop = 1'b0;
        for (t = 0; t < PACK; t = t + 1) begin
            tree = tree + term[t];
            any_drop = any_drop | drops[t];
        end
    end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s2_sum <= {ACC_W{1'b0}}; s2_drop <= 1'b0; end
        else begin s2_sum <= tree; s2_drop <= any_drop; end

    // ---- stage 3: one carry-save accumulate for all PACK products ----------
    reg [ACC_W-1:0] acc_sum, acc_car;
    wire [ACC_W-1:0] cs_sum = acc_sum ^ acc_car ^ s2_sum;
    wire [ACC_W-1:0] cs_car =
        ((acc_sum & acc_car) | (acc_sum & s2_sum) | (acc_car & s2_sum)) << 1;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}}; dropped <= 1'b0;
        end else if (clear) begin
            acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}}; dropped <= 1'b0;
        end else if (accept) begin
            acc_sum <= cs_sum;
            acc_car <= cs_car;
            dropped <= dropped | s2_drop;
        end

    // ---- stages 4a/4b: split resolve, once per dot product -----------------
    reg [HALF:0]   r_lo;
    reg [HALF-1:0] r_hi_a, r_hi_b;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            r_lo <= {(HALF+1){1'b0}};
            r_hi_a <= {HALF{1'b0}}; r_hi_b <= {HALF{1'b0}};
        end else begin
            r_lo   <= {1'b0, acc_sum[HALF-1:0]} + {1'b0, acc_car[HALF-1:0]};
            r_hi_a <= acc_sum[ACC_W-1:HALF];
            r_hi_b <= acc_car[ACC_W-1:HALF];
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) result <= {ACC_W{1'b0}};
        else result <= {(r_hi_a + r_hi_b + {{(HALF-1){1'b0}}, r_lo[HALF]}),
                        r_lo[HALF-1:0]};
endmodule
