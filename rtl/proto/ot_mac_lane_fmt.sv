`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One MAC lane, as a SEPARATE MODULE so it can be synthesised once and
// replicated.
//
// This is not a style preference, it is the measured difference between a design
// that reaches GHz and one that does not. The flow runs `synth -flatten` and then
// a single `abc -D` pass over the whole netlist, and ABC's mapping quality
// collapses as that netlist grows: the same lane logic written as a flattened
// generate loop measured
//
//     LANES=4    926 MHz      179 violating paths
//     LANES=64    74 MHz    8,393 violating paths
//
// on parallel, independent lanes that share no timing path at all. Four
// independent module INSTANCES of the same arithmetic measured 1,150 MHz.
// Replicating a hardened leaf is how GPUs and every large accelerator are built,
// and here it is also the only way the tool produces a usable netlist.
//
// Arithmetic (block floating point, exact):
//   1  exact 8x8 significand multiply, exponent add
//   2  align into the shared fixed-point window
//   3  carry-save accumulate -- 3:2 compressor, no carry chain in the loop
//   4a/4b  resolve the (sum, carry) pair, split, once per dot product
//
// Numerically qualified against runtime.reference.mac_tile (which takes the same
// act_format/wgt_format pair) by rtl/test/tb_mac_lane_fmt.sv, for each of BF16,
// FP8 E4M3 and MXFP4 weights against BF16 activations.
// ---------------------------------------------------------------------------
module ot_mac_lane_fmt #(
    parameter integer ACC_W      = 40,
    parameter integer EXP_WINDOW = 16,
    //: The weight format, as exponent and stored-fraction widths.  BF16 is
    //: (8,7), FP8 E4M3 is (4,3), MXFP4 E2M1 is (2,1).  Measured multiplier cost
    //: at this node: MXFP4 7.4 um2, FP8 13.3 um2, BF16 46.4 um2 -- so a fixed
    //: area budget buys about six MXFP4 lanes per BF16 lane, which is where the
    //: mask-ROM density argument has to be cashed in if it is real.
    parameter integer W_EXP_BITS  = 8,
    parameter integer W_FRAC_BITS = 7
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              clear,
    input  wire              accept,      // this lane's term is valid this cycle

    // operands arrive already registered by the tile's broadcast stage
    input  wire              a_sign,
    input  wire [7:0]        a_exp,
    input  wire [7:0]        a_man,
    input  wire              a_zero,
    input  wire [W_EXP_BITS+W_FRAC_BITS:0] b,   // this lane's weight, W_FMT_W bits
    input  wire [7:0]        scale_exp,

    output reg  [ACC_W-1:0]  result,
    output reg               dropped
);
    localparam integer HALF = ACC_W/2;

    reg              s1_sign, s2_neg, s2_drop;
    reg [9:0]        s1_exp;
    localparam integer PROD_W = 8 + 1 + W_FRAC_BITS;   // 8-bit activation sig x W_SIG_W
    reg [PROD_W-1:0] s1_prod;
    reg [ACC_W-1:0]  s2_term, acc_sum, acc_car;
    reg [HALF:0]     r_lo;
    reg [HALF-1:0]   r_hi_a, r_hi_b;

    localparam integer W_FMT_W = 1 + W_EXP_BITS + W_FRAC_BITS;
    localparam integer W_SIG_W = 1 + W_FRAC_BITS;

    wire                    b_sign = b[W_FMT_W-1];
    wire [W_EXP_BITS-1:0]   b_exp  = b[W_EXP_BITS+W_FRAC_BITS-1:W_FRAC_BITS];
    wire                    b_zero = (b[W_FMT_W-2:0] == {(W_FMT_W-1){1'b0}});
    wire [W_SIG_W-1:0]      b_man  = {1'b1, b[W_FRAC_BITS-1:0]};

    // ---- stage 1: exact significand multiply -------------------------------
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s1_sign <= 1'b0; s1_exp <= 10'b0; s1_prod <= 16'b0;
        end else begin
            s1_sign <= a_sign ^ b_sign;
            s1_exp  <= {2'b0, a_exp} + {{(10-W_EXP_BITS){1'b0}}, b_exp};
            s1_prod <= (a_zero || b_zero) ? {PROD_W{1'b0}} : (a_man * b_man);
        end

    // ---- stage 2: align into the window; sign by XOR, +1 deferred ----------
    wire [9:0]       rel    = s1_exp - {2'b0, scale_exp};
    wire             in_win = (rel[9] == 1'b0) && (rel <= EXP_WINDOW[9:0]);
    wire [4:0]       sh     = in_win ? rel[4:0] : 5'd0;
    wire [ACC_W-1:0] mag    = in_win
        ? ({{(ACC_W-PROD_W){1'b0}}, s1_prod} << sh) : {ACC_W{1'b0}};
    wire             drops  = !in_win && (s1_prod != {PROD_W{1'b0}});

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s2_neg <= 1'b0; s2_term <= {ACC_W{1'b0}}; s2_drop <= 1'b0;
        end else begin
            s2_neg  <= s1_sign;
            s2_term <= s1_sign ? ~mag : mag;
            s2_drop <= drops;
        end

    // ---- stage 3: 3:2 compressor ------------------------------------------
    wire [ACC_W-1:0] cs_sum = acc_sum ^ acc_car ^ s2_term;
    wire [ACC_W-1:0] cs_car =
        ((acc_sum & acc_car) | (acc_sum & s2_term) | (acc_car & s2_term)) << 1;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}}; dropped <= 1'b0;
        end else if (clear) begin
            acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}}; dropped <= 1'b0;
        end else if (accept) begin
            acc_sum <= cs_sum ^ {{(ACC_W-1){1'b0}}, s2_neg};
            acc_car <= cs_car | ({{(ACC_W-1){1'b0}}, (cs_sum[0] & s2_neg)} << 1);
            dropped <= dropped | s2_drop;
        end

    // ---- stages 4a/4b: resolve, split, once per dot product ----------------
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
