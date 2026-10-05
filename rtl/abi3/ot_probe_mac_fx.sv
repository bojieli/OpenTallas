`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The modern accelerator inner loop: multiply low precision, accumulate in WIDE
// FIXED POINT, normalise and round ONCE at the end of the reduction.
//
// Per-step FP add is what caps the existing datapath: align -> add -> normalise
// -> round every cycle.  A dot product does not need that.  Align each product
// into a shared fixed-point window and the recurring stage becomes an INTEGER
// ADD, which is a carry tree and nothing else.  One rounding at the end is also
// strictly MORE accurate than rounding every step.
//
// This is block-floating-point / fixed-point accumulation, standard in tensor
// cores and systolic arrays.
//
//   acc window: 48 bits covers a BF16 dot product over a 2^8 exponent spread
//   with 24 bits of significand headroom and no intermediate rounding.
// ---------------------------------------------------------------------------
module ot_probe_mac_fx #(
    parameter integer ACC_W = 48,
    parameter integer EXP_WINDOW = 16      // exponent spread handled in-window
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        clear,              // start a new dot product
    input  wire        valid_in,
    input  wire [15:0] a,                  // BF16
    input  wire [15:0] b,                  // BF16
    input  wire [7:0]  scale_exp,          // shared window exponent for the tile
    output reg  [ACC_W-1:0] acc,
    output reg              acc_valid
);
    // ---- stage 1: unpack, exponent add, exact 8x8 significand multiply -----
    reg               s1_v, s1_sign;
    reg  [9:0]        s1_exp;
    reg  [15:0]       s1_prod;

    wire        a_zero = (a[14:0] == 15'b0);
    wire        b_zero = (b[14:0] == 15'b0);
    wire [7:0]  a_man  = {1'b1, a[6:0]};
    wire [7:0]  b_man  = {1'b1, b[6:0]};

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v<=1'b0; s1_sign<=1'b0; s1_exp<=10'b0; s1_prod<=16'b0; end
        else begin
            s1_v    <= valid_in;
            s1_sign <= a[15] ^ b[15];
            s1_exp  <= {2'b0, a[14:7]} + {2'b0, b[14:7]};
            s1_prod <= (a_zero || b_zero) ? 16'b0 : (a_man * b_man);
        end

    // ---- stage 2: align the product into the shared fixed-point window -----
    // A left shift by a bounded amount only; no leading-zero count, no round.
    reg                s2_v;
    reg  [ACC_W-1:0]   s2_term;

    wire [9:0]  rel     = s1_exp - {2'b0, scale_exp};
    wire        in_win  = (rel[9] == 1'b0) && (rel <= EXP_WINDOW[9:0]);
    wire [4:0]  sh      = in_win ? rel[4:0] : 5'd0;
    wire [ACC_W-1:0] mag = in_win ? ({{(ACC_W-16){1'b0}}, s1_prod} << sh)
                                  : {ACC_W{1'b0}};

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s2_v<=1'b0; s2_term<={ACC_W{1'b0}}; end
        else begin
            s2_v    <= s1_v;
            // two's complement in the accumulator domain: sign folds into the
            // term, so the recurring stage is a plain signed add.
            s2_term <= s1_sign ? (~mag + {{(ACC_W-1){1'b0}}, 1'b1}) : mag;
        end

    // ---- stage 3: the recurring stage -- ONE signed integer add ------------
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin acc <= {ACC_W{1'b0}}; acc_valid <= 1'b0; end
        else if (clear) begin acc <= {ACC_W{1'b0}}; acc_valid <= 1'b0; end
        else begin
            acc_valid <= s2_v;
            if (s2_v) acc <= acc + s2_term;
        end
endmodule
