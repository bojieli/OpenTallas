`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Output-stationary MAC tile -- the inner array of a modern accelerator.
//
// LANES independent dot products advance together.  One activation is broadcast
// to every lane each cycle; each lane holds its own weight and its own
// carry-save accumulator.  After K cycles every lane has one output element.
// This is the standard GEMV/GEMM inner tile: operands are read once and reused
// LANES times, which is the whole point of an array rather than a single MAC.
//
// Arithmetic per lane, matching ot_mac_bf16_csa_pipe:
//   1  unpack, exponent add, exact 8x8 significand multiply
//   2  align the product into a shared fixed-point window (block floating point)
//   3  carry-save accumulate -- a 3:2 compressor, no carry chain in the loop
//   4  resolve the (sum, carry) pair, split across two cycles, ONCE per dot
//      product so it costs 1/K of throughput
//
// The shared window exponent makes the accumulation EXACT: every term that lands
// in the window is summed in fixed point with no intermediate rounding, so the
// result is independent of accumulation order.  A per-step floating-point add is
// neither exact nor order-independent.
//
// Terms outside the window are dropped, and dropped_mask reports it per lane
// rather than silently losing them.  A caller that sees a set bit must widen
// ACC_W or re-centre scale_exp; it is never correct to ignore.
// ---------------------------------------------------------------------------
module ot_mac_tile #(
    parameter integer LANES      = 16,
    parameter integer ACC_W      = 40,
    parameter integer EXP_WINDOW = 16
) (
    input  wire                    clk,
    input  wire                    rst_n,

    input  wire                    clear,        // begin a new set of dot products
    input  wire                    valid_in,
    input  wire [15:0]             act,          // BF16 activation, broadcast
    input  wire [16*LANES-1:0]     wgt,          // BF16 weight, one per lane
    input  wire [7:0]              scale_exp,    // shared window exponent

    output wire [ACC_W*LANES-1:0]  result,       // resolved fixed-point per lane
    output wire [LANES-1:0]        dropped_mask, // a term fell outside the window
    output reg                     result_valid
);
    localparam integer HALF = ACC_W/2;

    //: Per-lane state lives INSIDE the generate scope, not in module-level
    //: `reg [W-1:0] name [0:LANES-1]` arrays.  Declared as arrays and written
    //: from a generate block, Yosys infers an address-decoded MEMORY and builds
    //: muxes across the lanes: measured at 4 lanes, 596 MHz for the array form
    //: against 1,150 MHz for four genuinely independent MACs.  The lanes never
    //: index each other, so the arrays bought nothing and cost 2x the clock.
    reg s0_v, s1_v, s2_v, s3_v, s4_v;

    //: OPERAND BROADCAST TREE.  One activation feeds every lane, so at LANES=64
    //: a single unpacked wire drove 64 multiplier inputs and the array collapsed
    //: to 14 MHz (72 ns) -- fanout delay, not logic depth, and synth-only runs
    //: insert no buffers.  Real arrays distribute operands through a registered
    //: tree for exactly this reason.  GROUP lanes share one replica, and the
    //: replicas are registered, so fanout per driver is bounded by GROUP however
    //: wide the tile gets.
    localparam integer GROUP   = 4;
    localparam integer GROUPS  = (LANES + GROUP - 1) / GROUP;

    wire       act_zero_c = (act[14:0] == 15'b0);
    wire [7:0] act_man_c  = {1'b1, act[6:0]};
    wire       act_sign_c = act[15];
    wire [7:0] act_exp_c  = act[14:7];

    reg        b_zero [0:GROUPS-1];
    reg [7:0]  b_man  [0:GROUPS-1];
    reg        b_sign [0:GROUPS-1];
    reg [7:0]  b_exp  [0:GROUPS-1];
    reg [7:0]  b_scale[0:GROUPS-1];

    integer bg;
    always @(posedge clk or negedge rst_n)
        if (!rst_n)
            for (bg = 0; bg < GROUPS; bg = bg + 1) begin
                b_zero[bg] <= 1'b0; b_man[bg] <= 8'b0; b_sign[bg] <= 1'b0;
                b_exp[bg] <= 8'b0; b_scale[bg] <= 8'b0;
            end
        else
            for (bg = 0; bg < GROUPS; bg = bg + 1) begin
                b_zero[bg]  <= act_zero_c;
                b_man[bg]   <= act_man_c;
                b_sign[bg]  <= act_sign_c;
                b_exp[bg]   <= act_exp_c;
                b_scale[bg] <= scale_exp;
            end

    genvar g;
    generate
        for (g = 0; g < LANES; g = g + 1) begin : lane
            reg             s1_sign, s2_neg, s2_drop, dropped;
            reg [9:0]       s1_exp;
            reg [15:0]      s1_prod;
            reg [ACC_W-1:0] s2_term, acc_sum, acc_car, r_out;
            reg [HALF:0]    r_lo;
            reg [HALF-1:0]  r_hi_a, r_hi_b;

            localparam integer MYG = g / GROUP;

            // the weight is registered alongside the broadcast replica so both
            // multiplier operands arrive from flops in the same stage
            reg [15:0] w_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) w_q <= 16'b0; else w_q <= wgt[16*g +: 16];

            wire        w_zero   = (w_q[14:0] == 15'b0);
            wire [7:0]  w_man    = {1'b1, w_q[6:0]};

            // ---- stage 1 ----
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    s1_sign <= 1'b0; s1_exp <= 10'b0; s1_prod <= 16'b0;
                end else begin
                    s1_sign <= b_sign[MYG] ^ w_q[15];
                    s1_exp  <= {2'b0, b_exp[MYG]} + {2'b0, w_q[14:7]};
                    s1_prod <= (b_zero[MYG] || w_zero) ? 16'b0
                                                      : (b_man[MYG] * w_man);
                end

            // ---- stage 2 ----
            wire [9:0]       rel    = s1_exp - {2'b0, b_scale[MYG]};
            wire             in_win = (rel[9] == 1'b0) && (rel <= EXP_WINDOW[9:0]);
            wire [4:0]       sh     = in_win ? rel[4:0] : 5'd0;
            wire [ACC_W-1:0] mag    = in_win
                ? ({{(ACC_W-16){1'b0}}, s1_prod} << sh) : {ACC_W{1'b0}};
            // a zero product is not a dropped term
            wire             drops  = !in_win && (s1_prod != 16'b0);

            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    s2_neg <= 1'b0; s2_term <= {ACC_W{1'b0}};
                    s2_drop <= 1'b0;
                end else begin
                    s2_neg  <= s1_sign;
                    s2_term <= s1_sign ? ~mag : mag;   // XOR only
                    s2_drop <= drops;
                end

            // ---- stage 3: 3:2 compressor, no carry chain ----
            wire [ACC_W-1:0] cs_sum = acc_sum ^ acc_car ^ s2_term;
            wire [ACC_W-1:0] cs_car =
                ((acc_sum & acc_car) | (acc_sum & s2_term) |
                 (acc_car & s2_term)) << 1;

            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}};
                    dropped <= 1'b0;
                end else if (clear) begin
                    acc_sum <= {ACC_W{1'b0}}; acc_car <= {ACC_W{1'b0}};
                    dropped <= 1'b0;
                end else if (s2_v) begin
                    // the deferred +1 for a negated term rides in on bit 0
                    acc_sum <= cs_sum ^ {{(ACC_W-1){1'b0}}, s2_neg};
                    acc_car <= cs_car |
                        ({{(ACC_W-1){1'b0}}, (cs_sum[0] & s2_neg)} << 1);
                    dropped <= dropped | s2_drop;
                end

            // ---- stages 4a/4b ----
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    r_lo <= {(HALF+1){1'b0}};
                    r_hi_a <= {HALF{1'b0}}; r_hi_b <= {HALF{1'b0}};
                end else begin
                    r_lo   <= {1'b0, acc_sum[HALF-1:0]} +
                                 {1'b0, acc_car[HALF-1:0]};
                    r_hi_a <= acc_sum[ACC_W-1:HALF];
                    r_hi_b <= acc_car[ACC_W-1:HALF];
                end

            always @(posedge clk or negedge rst_n)
                if (!rst_n) r_out <= {ACC_W{1'b0}};
                else r_out <= {(r_hi_a + r_hi_b +
                                   {{(HALF-1){1'b0}}, r_lo[HALF]}),
                                  r_lo[HALF-1:0]};

            assign result[ACC_W*g +: ACC_W] = r_out;
            assign dropped_mask[g] = dropped;
        end
    endgenerate

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s0_v <= 1'b0; s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; s4_v <= 1'b0;
            result_valid <= 1'b0;
        end else begin
            s0_v <= valid_in;   // broadcast register stage
            s1_v <= s0_v;
            s2_v <= s1_v;
            s3_v <= s2_v;
            s4_v <= s3_v;
            result_valid <= s4_v;
        end
endmodule
