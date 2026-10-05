`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// BF16 add, five-stage pipeline. One result per cycle, five cycles of latency.
//
// THIS IS THE ANSWER TO "HOW DOES A GPU RUN AT 1 GHz IF AN FP ADD IS 300 MHz".
// It does not make the add faster. It cuts the add into pieces short enough that
// each piece fits in a 1 GHz cycle, and keeps five adds in flight at once. The
// LATENCY is five cycles and gets slightly worse; the THROUGHPUT is one add per
// cycle. Every high-frequency float unit in every CPU and GPU is built this way,
// and the unpipelined combinational adder this replaces is the reason the vector
// engine place-and-routed at 239 MHz.
//
//   stage 1   unpack, compare/swap, exponent difference
//   stage 2   align the smaller operand (barrel shift + sticky)
//   stage 3   add or subtract
//   stage 4   leading-zero count, normalising shift
//   stage 5   round to nearest-even, overflow, pack
//
// The arithmetic is ot_bf16_add_flat's, which is PROVEN bit-identical to
// ot_bf16_add_rne over all 2**32 input pairs by SAT miter
// (tools/prove_bf16_add_equivalence.sh). Registers do not change a function, so
// this pipeline computes that same function; what has to be checked here is that
// the staging is right -- every value a later stage reads is carried forward and
// not read one cycle stale. That is what rtl/test/tb_bf16_add_pipe.sv checks, by
// running the same operand stream through this and through the combinational
// module and requiring agreement cycle by cycle.
// ---------------------------------------------------------------------------
module ot_bf16_add_pipe (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        in_valid,
    input  wire [15:0] left_code,
    input  wire [15:0] right_code,
    output reg         out_valid,
    output reg  [15:0] result_code,
    output reg         result_saturated,
    output reg  [1:0]  result_error
);
    localparam [1:0] ERR_NONE = 2'd0, ERR_NONFINITE = 2'd1, ERR_OVERFLOW = 2'd2;

    // ================= stage 1: unpack, compare/swap ========================
    wire l_nf = (left_code[14:7]  == 8'hff);
    wire r_nf = (right_code[14:7] == 8'hff);
    wire [7:0] l_man = (left_code[14:7]  == 0) ? {1'b0, left_code[6:0]}  : {1'b1, left_code[6:0]};
    wire [7:0] r_man = (right_code[14:7] == 0) ? {1'b0, right_code[6:0]} : {1'b1, right_code[6:0]};
    wire [7:0] l_exp = (left_code[14:7]  == 0) ? 8'd1 : left_code[14:7];
    wire [7:0] r_exp = (right_code[14:7] == 0) ? 8'd1 : right_code[14:7];
    wire swap = (r_exp > l_exp) || ((r_exp == l_exp) && (r_man > l_man));

    reg        s1_v, s1_nf, s1_bothz, s1_bsign, s1_same;
    reg [7:0]  s1_bexp;
    reg [11:0] s1_bext, s1_sext;
    reg [8:0]  s1_ediff;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s1_nf <= 1'b0; s1_bothz <= 1'b0;
            s1_bsign <= 1'b0; s1_same <= 1'b0; s1_bexp <= 8'b0;
            s1_bext <= 12'b0; s1_sext <= 12'b0; s1_ediff <= 9'b0;
        end else begin
            s1_v     <= in_valid;
            s1_nf    <= l_nf || r_nf;
            s1_bothz <= (l_man == 0) && (r_man == 0);
            s1_bsign <= swap ? right_code[15] : left_code[15];
            s1_same  <= (left_code[15] == right_code[15]);
            s1_bexp  <= swap ? r_exp : l_exp;
            s1_bext  <= {1'b0, (swap ? r_man : l_man), 3'b000};
            s1_sext  <= {1'b0, (swap ? l_man : r_man), 3'b000};
            s1_ediff <= {1'b0, (swap ? r_exp : l_exp)} - {1'b0, (swap ? l_exp : r_exp)};
        end

    // ================= stage 2: align =======================================
    wire       far  = (s1_ediff >= 9'd12);
    wire [3:0] adist = far ? 4'd12 : s1_ediff[3:0];
    wire [11:0] shr = far ? 12'b0 : (s1_sext >> adist);
    reg        jam;
    integer    j;
    always @* begin
        jam = 1'b0;
        for (j = 0; j < 12; j = j + 1) if (j < adist) jam = jam | s1_sext[j];
    end
    wire [11:0] aligned = (s1_ediff == 0) ? s1_sext : (shr | {11'b0, jam});

    reg        s2_v, s2_nf, s2_bothz, s2_bsign, s2_same;
    reg [7:0]  s2_bexp;
    reg [11:0] s2_bext, s2_sal;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s2_v <= 1'b0; s2_nf <= 1'b0; s2_bothz <= 1'b0;
            s2_bsign <= 1'b0; s2_same <= 1'b0; s2_bexp <= 8'b0;
            s2_bext <= 12'b0; s2_sal <= 12'b0;
        end else begin
            s2_v <= s1_v; s2_nf <= s1_nf; s2_bothz <= s1_bothz;
            s2_bsign <= s1_bsign; s2_same <= s1_same; s2_bexp <= s1_bexp;
            s2_bext <= s1_bext; s2_sal <= aligned;
        end

    // ================= stage 3: add or subtract =============================
    wire [11:0] arith = s2_same ? (s2_bext + s2_sal) : (s2_bext - s2_sal);

    reg        s3_v, s3_nf, s3_bothz, s3_bsign;
    reg [7:0]  s3_bexp;
    reg [11:0] s3_arith;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s3_v <= 1'b0; s3_nf <= 1'b0; s3_bothz <= 1'b0;
            s3_bsign <= 1'b0; s3_bexp <= 8'b0; s3_arith <= 12'b0;
        end else begin
            s3_v <= s2_v; s3_nf <= s2_nf; s3_bothz <= s2_bothz;
            s3_bsign <= s2_bsign; s3_bexp <= s2_bexp; s3_arith <= arith;
        end

    // ================= stage 4: leading-zero count, normalise ===============
    //: The ten-deep conditional-shift cascade, replaced by a priority encoder
    //: and one barrel shift.  The original loop's guard `exponent_work > 1` caps
    //: the distance at exp-1, the subnormal boundary, so the shift is
    //: min(lz, exp-1) and nothing more.
    reg [3:0] lz;
    always @* casez (s3_arith[10:0])
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

    wire [8:0] exp_in = {1'b0, s3_bexp};
    wire [8:0] room   = exp_in - 9'd1;
    wire [3:0] shl    = ({5'b0, lz} <= room) ? lz : room[3:0];
    wire        up    = s3_arith[11];
    wire [11:0] norm  = up ? ((s3_arith >> 1) | {11'b0, s3_arith[0]})
                           : (s3_arith << shl);
    wire [8:0]  exp_n = up ? (exp_in + 9'd1) : (exp_in - {5'b0, shl});

    reg        s4_v, s4_nf, s4_bothz, s4_sumz, s4_bsign;
    reg [11:0] s4_norm;
    reg [8:0]  s4_exp;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s4_v <= 1'b0; s4_nf <= 1'b0; s4_bothz <= 1'b0;
            s4_sumz <= 1'b0; s4_bsign <= 1'b0; s4_norm <= 12'b0; s4_exp <= 9'b0;
        end else begin
            s4_v <= s3_v; s4_nf <= s3_nf; s4_bothz <= s3_bothz;
            s4_sumz <= (s3_arith == 12'b0); s4_bsign <= s3_bsign;
            s4_norm <= norm; s4_exp <= exp_n;
        end

    // ================= stage 5: round, pack =================================
    wire       inc   = s4_norm[2] && ((|s4_norm[1:0]) || s4_norm[3]);
    wire [8:0] rnd   = {1'b0, s4_norm[10:3]} + {8'b0, inc};
    wire       carry = rnd[8];
    wire [8:0] rnd_f = carry ? 9'd128 : rnd;
    wire [8:0] exp_f = s4_exp + {8'b0, carry};

    wire pre_ovf  = (s4_exp >= 9'd255);
    wire post_ovf = (exp_f  >= 9'd255);
    wire subn     = (exp_f == 9'd1) && !rnd_f[7];

    wire [15:0] packed_code =
        post_ovf ? {s4_bsign, 8'hfe, 7'h7f} :
        subn     ? {s4_bsign, 8'h00, rnd_f[6:0]} :
                   {s4_bsign, exp_f[7:0], rnd_f[6:0]};
    wire [15:0] packed_z = (packed_code[14:0] == 15'b0) ? 16'b0 : packed_code;

    wire z   = !s4_nf && s4_bothz;
    wire sz  = !s4_nf && !s4_bothz && s4_sumz;
    wire ovf = !s4_nf && !s4_bothz && !s4_sumz && pre_ovf;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            out_valid <= 1'b0; result_code <= 16'b0;
            result_saturated <= 1'b0; result_error <= ERR_NONE;
        end else begin
            out_valid        <= s4_v;
            result_error     <= s4_nf ? ERR_NONFINITE : ovf ? ERR_OVERFLOW : ERR_NONE;
            result_code      <= (s4_nf || z || sz || ovf) ? 16'b0 : packed_z;
            result_saturated <= !s4_nf && !s4_bothz && !s4_sumz && !pre_ovf && post_ovf;
        end
endmodule
