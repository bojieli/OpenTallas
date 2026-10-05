`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// BF16 add, restructured for speed. Bit-identical to ot_bf16_add_rne.
//
// The original normalises with a ten-iteration loop, each iteration a
// conditional one-bit shift guarded by a comparison. Unrolled that is a serial
// chain of ten muxes and ten comparators, and it is why the vector engine
// place-and-routes at 239 MHz while a bare flop-to-flop path on this node
// reaches 8,691 MHz.
//
// This version does what every hardware float adder does: count the leading
// zeros once, then shift once by that amount. The ten-deep cascade becomes a
// priority encoder plus one barrel shifter, both logarithmic.
//
// NOT a new arithmetic contract. Every semantic of ot_bf16_add_rne is preserved
// deliberately, including the ones that are narrowings of IEEE 754:
//   * nonfinite input fails closed with ERR_NONFINITE
//   * a subnormal input is read with exponent 1 and no implicit leading one
//   * exponent_work >= 255 before rounding is ERR_OVERFLOW, after rounding is
//     saturation to 0x?e7f with result_saturated
//   * every zero result is canonical positive zero
// Equivalence is not argued from this comment. It is PROVEN over all 2**32
// input pairs by a Yosys SAT miter; see tools/prove_bf16_add_equivalence.sh.
// ---------------------------------------------------------------------------
module ot_bf16_add_flat (
    input  wire [15:0] left_code,
    input  wire [15:0] right_code,
    output wire [15:0] result_code,
    output wire        result_saturated,
    output wire [1:0]  result_error
);
    localparam [1:0] ERR_NONE = 2'd0, ERR_NONFINITE = 2'd1, ERR_OVERFLOW = 2'd2;

    wire l_nf = (left_code[14:7]  == 8'hff);
    wire r_nf = (right_code[14:7] == 8'hff);
    wire [7:0] l_man = (left_code[14:7]  == 0) ? {1'b0, left_code[6:0]}  : {1'b1, left_code[6:0]};
    wire [7:0] r_man = (right_code[14:7] == 0) ? {1'b0, right_code[6:0]} : {1'b1, right_code[6:0]};
    wire [7:0] l_exp = (left_code[14:7]  == 0) ? 8'd1 : left_code[14:7];
    wire [7:0] r_exp = (right_code[14:7] == 0) ? 8'd1 : right_code[14:7];

    // ---- compare / swap ----------------------------------------------------
    wire swap = (r_exp > l_exp) || ((r_exp == l_exp) && (r_man > l_man));
    wire        big_sign  = swap ? right_code[15] : left_code[15];
    wire        sml_sign  = swap ? left_code[15]  : right_code[15];
    wire [7:0]  big_exp   = swap ? r_exp : l_exp;
    wire [7:0]  sml_exp   = swap ? l_exp : r_exp;
    wire [7:0]  big_man   = swap ? r_man : l_man;
    wire [7:0]  sml_man   = swap ? l_man : r_man;

    // ---- align, with the sticky ("jam") bit the original computes ----------
    wire [8:0]  ediff = {1'b0, big_exp} - {1'b0, sml_exp};
    wire [11:0] sml_ext = {1'b0, sml_man, 3'b000};
    wire [11:0] big_ext = {1'b0, big_man, 3'b000};

    //: shift_right_jam, unrolled. distance >= 12 collapses the whole operand
    //: into the sticky bit, which is what the original's `distance >= 12`
    //: branch does.
    wire        far   = (ediff >= 9'd12);
    wire [3:0]  adist  = far ? 4'd12 : ediff[3:0];
    wire [11:0] shr   = far ? 12'b0 : (sml_ext >> adist);
    reg         jam;
    integer     j;
    always @* begin
        jam = 1'b0;
        for (j = 0; j < 12; j = j + 1)
            if (j < adist) jam = jam | sml_ext[j];
    end
    wire [11:0] sml_aligned = (ediff == 0) ? sml_ext : (shr | {11'b0, jam});

    // ---- add or subtract ---------------------------------------------------
    wire same_sign = (big_sign == sml_sign);
    wire [11:0] arith = same_sign ? (big_ext + sml_aligned) : (big_ext - sml_aligned);

    // ---- normalise: count once, shift once --------------------------------
    //: The ten-deep cascade the original builds, replaced by a priority encoder
    //: and one barrel shift. `lz` is how many left shifts bring the highest set
    //: bit to position 10; the original's loop guard `exponent_work > 1` caps
    //: the shift at exp-1, which is the subnormal boundary, so the distance is
    //: min(lz, exp-1) and nothing else.
    reg [3:0] lz;
    always @* casez (arith[10:0])
        11'b1??????????: lz = 4'd0;
        11'b01?????????: lz = 4'd1;
        11'b001????????: lz = 4'd2;
        11'b0001???????: lz = 4'd3;
        11'b00001??????: lz = 4'd4;
        11'b000001?????: lz = 4'd5;
        11'b0000001????: lz = 4'd6;
        11'b00000001???: lz = 4'd7;
        11'b000000001??: lz = 4'd8;
        11'b0000000001?: lz = 4'd9;
        default:         lz = 4'd10;
    endcase

    wire [8:0] exp_in   = {1'b0, big_exp};
    wire [8:0] room     = exp_in - 9'd1;                 // exp is >= 1 always
    wire [3:0] shl      = ({5'b0, lz} <= room) ? lz : room[3:0];
    wire [11:0] norm_l  = arith << shl;
    wire [8:0]  exp_l   = exp_in - {5'b0, shl};

    //: arith[11] set means the magnitudes summed into the carry position; the
    //: original shifts right by one THROUGH shift_right_jam, so bit 0 of the
    //: pre-shift value survives as sticky.
    wire [11:0] norm_r  = (arith >> 1) | {11'b0, arith[0]};
    wire [8:0]  exp_r   = exp_in + 9'd1;

    wire        up      = arith[11];
    wire [11:0] norm    = up ? norm_r : norm_l;
    wire [8:0]  exp_n   = up ? exp_r  : exp_l;

    // ---- round to nearest, ties to even -----------------------------------
    wire        inc     = norm[2] && ((|norm[1:0]) || norm[3]);
    wire [8:0]  rnd     = {1'b0, norm[10:3]} + {8'b0, inc};
    wire        carry   = rnd[8];
    wire [8:0]  rnd_f   = carry ? 9'd128 : rnd;
    wire [8:0]  exp_f   = exp_n + {8'b0, carry};

    // ---- assemble, in the original's precedence ---------------------------
    wire both_zero = (l_man == 0) && (r_man == 0);
    wire sum_zero  = (arith == 12'b0);
    wire pre_ovf   = (exp_n >= 9'd255);
    wire post_ovf  = (exp_f >= 9'd255);
    wire subnormal = (exp_f == 9'd1) && !rnd_f[7];

    wire [15:0] packed_code =
        post_ovf  ? {big_sign, 8'hfe, 7'h7f} :
        subnormal ? {big_sign, 8'h00, rnd_f[6:0]} :
                    {big_sign, exp_f[7:0], rnd_f[6:0]};
    wire [15:0] packed_z = (packed_code[14:0] == 15'b0) ? 16'b0 : packed_code;

    wire nf  = l_nf || r_nf;
    wire z   = !nf && both_zero;
    wire sz  = !nf && !both_zero && sum_zero;
    wire ovf = !nf && !both_zero && !sum_zero && pre_ovf;

    assign result_error      = nf  ? ERR_NONFINITE : ovf ? ERR_OVERFLOW : ERR_NONE;
    assign result_code       = (nf || z || sz || ovf) ? 16'b0 : packed_z;
    assign result_saturated  = !nf && !both_zero && !sum_zero && !pre_ovf && post_ovf;
endmodule
