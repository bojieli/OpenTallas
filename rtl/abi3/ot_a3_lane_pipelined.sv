`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The format-scaled, pipelined TENSOR contraction lane
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 4.2 and 11.6).
//
// rtl/abi3/ot_a3_mac_lane.sv is this module's reference and is untouched.
// That lane retires one multiply-accumulate every five cycles by construction;
// this one retires one lane-op per cycle by interleaving ADDER_STAGES output
// columns through one pipelined binary32 adder, and it consumes g = 1, 2 or 4
// products per lane-op according to the operand formats:
//
//   g = 1  BF16 x BF16 (and any 8-bit-or-narrower pair): one 8 x 8 product,
//          acc <- RNE32(acc + RNE32(a * w)), the product canonicalised to +0.0
//          when exactly zero.  This is bf16_bf16_fp32_sequential_rne_v1 with
//          K_BLOCK = K, and gate D1 proves it bit-identical to the sequential
//          lane by running both on one operand set.
//   g = 2  E4M3FN x E4M3FN (or E2M1): two exact 4 x 4 products, summed exactly,
//          acc <- RNE32(acc + p0 + p1)  -- one rounding per group (AM-E1).
//   g = 4  E2M1 x E4M3FN (either side E2M1): four exact 2 x 4 products,
//          acc <- RNE32(acc + p0 + p1 + p2 + p3).
//
// Ascending-k order is a property of one output element's accumulator chain.
// Interleaving *different* output elements through the adder reorders nothing
// inside any chain, which is why a pipelined lane can be bit-identical to the
// sequential one; the interleave depth equals the adder latency so that a
// chain's next add always sees its previous result (a same-slot bypass covers
// the exact-latency case).
//
// Pipeline (P = 8 front-end stages, then L = ADDER_STAGES adder stages):
//
//   issue    address generation for (row, column, k-group); one token per cycle
//   read     the operand memories answer one cycle after the address
//   unpack   storage code -> (sign, significand, power); E8M0 scale folded as
//            an exponent add with np.float32 subnormal rounding; nonfinite
//            BF16, reserved E4M3FN / E8M0 and scale range faults raised here
//   multiply the reconfigurable 8 x 8 partial-product field; exponent adds
//   group    the exact group sum, in four stages -- encode (msb16, the
//            four-way exponent minimum, the align distances; at g = 1 the
//            product rounded to binary32 on the subnormal grid instead),
//            align (the four variable shifts, the add tree's first level),
//            sum (its second level and the magnitude), normalise -- with the
//            product and aligner range checks raised on the way.  It was one
//            combinational stage until it became the design's critical path;
//            splitting it cost three cycles of latency and no throughput
//            (see the block's own comment for why neither the accumulator
//            recurrence nor the issue rate moves with P)
//   adder    align | add + normalise | round + pack, cut into L register
//            stages; accumulator read at entry (with bypass), written at exit
//
// Faults travel with their token and commit in issue order at the adder's
// exit, so a refused operation is deterministic: every pass that completed
// before the faulting pass has been written, the faulting pass and everything
// after it write nothing, and the lane stops with a distinct error detail
// (gate D5) whose class equals the sequential lane's error code.
//
// Address generation (section 13 item 11): no divider and no multiplier on
// the per-cycle path.  Every operand and scale address the lane issues is an
// adder over registered walk state:
//
//   a_rd_addr = a_row_base + kg            a_row_base += depth_words per row
//   b_rd_addr = b_col_base[col] + kg       the column's base word, sampled
//                                          from a cursor that advances by
//                                          depth_words each time a column is
//                                          opened (its first k-group) and
//                                          returns to cfg_b_base at the end
//                                          of a row
//   s_rd_addr = cfg_scale_a_base + row_scale_a + k_scale_a
//   t_rd_addr = cfg_scale_b_base + col_scale_b[col] + k_scale_b
//   out_addr  = out_row_base + column      out_row_base += cols per row
//
// For amendment A15's E8M0 code index
//     (row / rows_per_block) * (depth / block) + (k / block)
// none of the three quotients is divided per element.  depth / block is
// computed once per operation by the admission unit and held as a registered
// stride (cpr_x, codes per row of blocks); row / rows_per_block and
// column / rows_per_block are counters that wrap at rows_per_block and add
// the stride on the wrap (row_scale_a; and the column cursor col_cur_scale_b,
// sampled into col_scale_b[col] when the column is opened); k / block is a
// counter that wraps every block / g k-groups (bw_x, a shift of the block
// size, since g divides it) and increments on the wrap.  For every admitted
// configuration the address sequence equals the sequential lane's
// scale_index() element by element; for a side whose scale is disabled the
// scale address is the base (the code read there is not used).
//
// Admission (state S_ADMIT, once per operation): a restoring divider computes
// depth / block for both sides one quotient bit per cycle -- a 17-bit
// subtract per cycle, never on the issue path -- and the operation is
// admitted only if both remainders are zero, each enabled block is a
// multiple of g (its low log2 g bits are zero) and every format and shape
// rule of shape_ok holds; otherwise the lane stops with ERR_SHAPE /
// DETAIL_SHAPE and writes nothing, the same class and detail as before.
// The first lane-op issues 18 cycles after start (it was 1); the steady-state
// rate is unchanged.  Configuration inputs are sampled at start and held in
// registers for the operation, so they must be stable from start to done --
// the benches and the LQ8 block hold them so.
//
// Package constants are re-declared as local parameters and package functions
// called through their scope -- never a wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_lane_pipelined #(
    parameter integer ADDER_STAGES = 3,     // L: adder latency = interleaved columns
    parameter integer ACC_SLOTS    = 8      // accumulator file slots (>= ADDER_STAGES)
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [15:0] cfg_rows,           // M
    input  wire [15:0] cfg_cols,           // N
    input  wire [15:0] cfg_depth,          // K
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [7:0]  cfg_group,          // g: 1, 2 or 4 products per lane-op
    input  wire [31:0] cfg_a_base,         // word addresses; a word holds g elements
    input  wire [31:0] cfg_b_base,
    input  wire        cfg_scale_a,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_a,        // scale_block_elements
    input  wire [15:0] cfg_block_b,
    input  wire [15:0] cfg_block_rows_a,   // scale_block_rows (amendment A15)
    input  wire [15:0] cfg_block_rows_b,
    input  wire [31:0] cfg_scale_a_base,
    input  wire [31:0] cfg_scale_b_base,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_out_fp32,       // 1: binary32 partials; 0: BF16 with saturation

    output reg         a_rd_en,
    output reg  [31:0] a_rd_addr,
    input  wire [63:0] a_rd_data,
    output reg         b_rd_en,
    output reg  [31:0] b_rd_addr,
    input  wire [63:0] b_rd_data,
    output reg         s_rd_en,
    output reg  [31:0] s_rd_addr,
    input  wire [31:0] s_rd_data,
    output reg         t_rd_en,
    output reg  [31:0] t_rd_addr,
    input  wire [31:0] t_rd_data,

    output reg         out_we,
    output reg  [31:0] out_addr,
    output reg  [31:0] out_data,           // BF16 (low half) or binary32 per cfg_out_fp32
    output reg  [31:0] out_acc,            // the binary32 accumulator, always

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,         // ot_a3_engine_pkg class, as the reference
    output reg  [7:0]  error_detail,       // ot_a3_lane_pkg detail, one per failure mode
    output reg  [31:0] out_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] mac_count,          // lane-ops retired (g products each)
    output reg  [31:0] product_count,      // products retired
    output reg         op_retire           // one-cycle pulse per retired lane-op
);
    localparam integer L = ADDER_STAGES;
    localparam [15:0]  L16 = ADDER_STAGES;
    localparam [2:0]   L3 = ADDER_STAGES;
    localparam [3:0]   L_WAIT = ADDER_STAGES - 1;

    localparam [7:0] ERR_NONE  = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_SHAPE = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] DETAIL_NONE             = ot_a3_lane_pkg::DETAIL_NONE;
    localparam [7:0] DETAIL_A_NONFINITE      = ot_a3_lane_pkg::DETAIL_A_NONFINITE;
    localparam [7:0] DETAIL_B_NONFINITE      = ot_a3_lane_pkg::DETAIL_B_NONFINITE;
    localparam [7:0] DETAIL_A_RESERVED       = ot_a3_lane_pkg::DETAIL_A_RESERVED;
    localparam [7:0] DETAIL_B_RESERVED       = ot_a3_lane_pkg::DETAIL_B_RESERVED;
    localparam [7:0] DETAIL_SCALE_A_RESERVED = ot_a3_lane_pkg::DETAIL_SCALE_A_RESERVED;
    localparam [7:0] DETAIL_SCALE_B_RESERVED = ot_a3_lane_pkg::DETAIL_SCALE_B_RESERVED;
    localparam [7:0] DETAIL_SCALE_A_RANGE    = ot_a3_lane_pkg::DETAIL_SCALE_A_RANGE;
    localparam [7:0] DETAIL_SCALE_B_RANGE    = ot_a3_lane_pkg::DETAIL_SCALE_B_RANGE;
    localparam [7:0] DETAIL_PRODUCT_RANGE    = ot_a3_lane_pkg::DETAIL_PRODUCT_RANGE;
    localparam [7:0] DETAIL_ACCUMULATE_RANGE = ot_a3_lane_pkg::DETAIL_ACCUMULATE_RANGE;
    localparam [7:0] DETAIL_SHAPE            = ot_a3_lane_pkg::DETAIL_SHAPE;
    localparam [7:0] DETAIL_ALIGNER          = ot_a3_lane_pkg::DETAIL_ALIGNER;
    localparam [7:0] FMT_BF16       = ot_a3_lane_pkg::FMT_BF16;
    localparam [7:0] FMT_FP8_E4M3FN = ot_a3_lane_pkg::FMT_FP8_E4M3FN;
    localparam [7:0] FMT_MXFP4_E2M1 = ot_a3_lane_pkg::FMT_MXFP4_E2M1;

    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_RUN   = 2'd1;
    localparam [1:0] S_DONE  = 2'd2;
    localparam [1:0] S_ADMIT = 2'd3;

    // Column-indexed walk state is sized to the next power of two above L so
    // that col_i (< n_active <= L) never leaves the array.
    localparam integer COL_BITS = (ADDER_STAGES > 4) ? 3 : ((ADDER_STAGES > 2) ? 2 : 1);
    localparam integer COL_SLOTS = 1 << COL_BITS;

    // -- latched configuration ---------------------------------------------------
    reg [1:0]  state;
    reg [1:0]  mode;            // 0: g = 1, 1: g = 2, 2: g = 4
    reg [2:0]  group;           // 1, 2, 4
    reg [1:0]  group_shift;     // log2(group)
    reg        swap_ab;         // E2M1 operand is B: it takes the narrow side
    reg [15:0] depth_words;     // ceil(depth / group)
    reg [15:0] kg_count;        // k-groups per column
    reg [2:0]  tail_valid;      // elements valid in the last k-group
    reg        faulted;
    reg [7:0]  dtype_a_r, dtype_b_r;
    reg        scale_a_r, scale_b_r, out_fp32_r;
    reg [15:0] rows_r, cols_r;
    reg [31:0] b_base_r, scale_a_base_r, scale_b_base_r;

    // -- scale geometry, from the admission unit ---------------------------------
    reg [15:0] rpb_a, rpb_b;    // rows (columns) per scale block, >= 1
    reg [15:0] cpr_a, cpr_b;    // codes per row of blocks: depth / block (0 when unscaled)
    reg [15:0] bw_a, bw_b;      // k-groups per scale block: block / g (0 when unscaled)

    // -- admission divider: depth / block, restoring, one bit per cycle ----------
    reg [4:0]  div_step;
    reg [15:0] div_n;           // the numerator, shifted out MSB first
    reg [15:0] div_r_a, div_r_b;
    reg [15:0] div_q_a, div_q_b;

    // -- issue counters ----------------------------------------------------------
    reg [15:0] row;
    reg [15:0] pass_col0;
    reg [15:0] kg;
    reg [2:0]  col_i;
    reg        issue_active;
    reg [3:0]  slot_wait [0:ACC_SLOTS-1];
    reg [31:0] inflight;

    // -- address walk (adders only) ----------------------------------------------
    reg [31:0] a_row_base;                  // cfg_a_base + row * depth_words
    reg [31:0] out_row_base;                // cfg_out_base + row * cols
    reg [31:0] b_col_cursor;                // cfg_b_base + (next column to open) * depth_words
    reg [31:0] b_col_base   [0:COL_SLOTS-1];
    reg [15:0] row_in_block_a;              // row mod rpb_a
    reg [31:0] row_scale_a;                 // (row / rpb_a) * cpr_a
    reg [15:0] kg_in_block_a, kg_in_block_b; // kg mod bw_x
    reg [15:0] k_scale_a, k_scale_b;        // kg / bw_x
    reg [15:0] col_cur_in_block_b;          // (next column to open) mod rpb_b
    reg [31:0] col_cur_scale_b;             // ((next column to open) / rpb_b) * cpr_b
    reg [31:0] col_scale_b  [0:COL_SLOTS-1];

    // -- accumulator file --------------------------------------------------------
    reg [31:0] acc_file [0:ACC_SLOTS-1];

    // -- token fields shared by every stage --------------------------------------
    // {valid, slot[2:0], first, last, nvalid[2:0], out_addr[31:0], detail[7:0]}
    localparam integer TOKEN_BITS = 1 + 3 + 1 + 1 + 3 + 32 + 8;
    function automatic [TOKEN_BITS-1:0] make_token;
        input        valid;
        input [2:0]  slot;
        input        first;
        input        last;
        input [2:0]  nvalid;
        input [31:0] address;
        input [7:0]  detail;
        begin
            make_token = {valid, slot, first, last, nvalid, address, detail};
        end
    endfunction
    function automatic token_valid;
        input [TOKEN_BITS-1:0] token;
        begin token_valid = token[TOKEN_BITS-1]; end
    endfunction
    function automatic [2:0] token_slot;
        input [TOKEN_BITS-1:0] token;
        begin token_slot = token[TOKEN_BITS-2:TOKEN_BITS-4]; end
    endfunction
    function automatic token_first;
        input [TOKEN_BITS-1:0] token;
        begin token_first = token[TOKEN_BITS-5]; end
    endfunction
    function automatic token_last;
        input [TOKEN_BITS-1:0] token;
        begin token_last = token[TOKEN_BITS-6]; end
    endfunction
    function automatic [2:0] token_nvalid;
        input [TOKEN_BITS-1:0] token;
        begin token_nvalid = token[TOKEN_BITS-7:TOKEN_BITS-9]; end
    endfunction
    function automatic [31:0] token_address;
        input [TOKEN_BITS-1:0] token;
        begin token_address = token[39:8]; end
    endfunction
    function automatic [7:0] token_detail;
        input [TOKEN_BITS-1:0] token;
        begin token_detail = token[7:0]; end
    endfunction
    function automatic [TOKEN_BITS-1:0] token_with_detail;
        input [TOKEN_BITS-1:0] token;
        input [7:0] detail;
        begin
            token_with_detail = token;
            if (token[7:0] == DETAIL_NONE)
                token_with_detail[7:0] = detail;
        end
    endfunction

    // One 16-bit storage code out of a packed 64-bit operand word.
    function automatic [15:0] element_code;
        input [63:0] word;
        input [7:0]  format;
        input integer index;
        reg [63:0] shifted;
        begin
            shifted = word >> (index * ot_a3_lane_pkg::element_width(format));
            element_code = shifted[15:0];
        end
    endfunction

    function automatic [7:0] element_detail;
        input [29:0] element;
        begin element_detail = element[29:22]; end
    endfunction
    function automatic element_sign;
        input [29:0] element;
        begin element_sign = element[21]; end
    endfunction
    function automatic element_zero;
        input [29:0] element;
        begin element_zero = element[20]; end
    endfunction
    function automatic [7:0] element_mag;
        input [29:0] element;
        begin element_mag = element[19:12]; end
    endfunction
    function automatic [11:0] element_pow;
        input [29:0] element;
        begin element_pow = element[11:0]; end
    endfunction

    function automatic [15:0] min16;
        input [15:0] left;
        input [15:0] right;
        begin min16 = (left < right) ? left : right; end
    endfunction

    // ---------------------------------------------------------------------------
    // Issue
    // ---------------------------------------------------------------------------
    wire [15:0] cols_left = cols_r - pass_col0;
    wire [2:0]  n_active  = (cols_left >= L16) ? L3 : cols_left[2:0];
    wire        last_kg   = (kg + 16'd1 == kg_count);
    wire [15:0] column    = pass_col0 + {13'b0, col_i};
    wire        open_col  = (kg == 16'd0);   // first k-group: the column is opened from the cursor
    wire        can_issue = (state == S_RUN) && issue_active && !faulted &&
                            (slot_wait[col_i] == 4'd0);
    wire [COL_BITS-1:0] col_idx = col_i[COL_BITS-1:0];
    wire [31:0] b_col_now     = open_col ? b_col_cursor    : b_col_base[col_idx];
    wire [31:0] col_scale_now = open_col ? col_cur_scale_b : col_scale_b[col_idx];
    // Counter wraps, compared one bit wider so that a zero bound never wraps.
    wire        row_wrap_a = ({1'b0, row_in_block_a} + 17'd1) == {1'b0, rpb_a};
    wire        col_wrap_b = ({1'b0, col_cur_in_block_b} + 17'd1) == {1'b0, rpb_b};
    wire        kg_wrap_a  = ({1'b0, kg_in_block_a} + 17'd1) == {1'b0, bw_a};
    wire        kg_wrap_b  = ({1'b0, kg_in_block_b} + 17'd1) == {1'b0, bw_b};

    // tok_ge, tok_ga and tok_gs are the group block's three internal stages;
    // tok_g is still the token at the group registers the adder reads.
    reg [TOKEN_BITS-1:0] tok_i, tok_r, tok_u, tok_m, tok_ge, tok_ga, tok_gs, tok_g;
    reg [TOKEN_BITS-1:0] tok_a [0:L-1];

    // ---------------------------------------------------------------------------
    // Unpack (combinational on the read stage)
    // ---------------------------------------------------------------------------
    reg [29:0]  u_a [0:3];
    reg [29:0]  u_b [0:3];
    reg [7:0]   u_detail;
    reg [29:0]  raw_a, raw_b;
    reg         seen_operand, seen_scale_reserved, seen_scale_range;
    reg [7:0]   operand_detail, scale_reserved_detail, scale_range_detail;
    integer     uj;
    always @* begin
        u_detail = DETAIL_NONE;
        seen_operand = 1'b0;
        seen_scale_reserved = 1'b0;
        seen_scale_range = 1'b0;
        operand_detail = DETAIL_NONE;
        scale_reserved_detail = DETAIL_NONE;
        scale_range_detail = DETAIL_NONE;
        for (uj = 0; uj < 4; uj = uj + 1) begin
            raw_a = ot_a3_lane_pkg::unpack_element(
                dtype_a_r, element_code(a_rd_data, dtype_a_r, uj), 1'b0);
            raw_b = ot_a3_lane_pkg::unpack_element(
                dtype_b_r, element_code(b_rd_data, dtype_b_r, uj), 1'b1);
            if (uj < token_nvalid(tok_r)) begin
                u_a[uj] = ot_a3_lane_pkg::fold_scale(raw_a, s_rd_data[7:0], scale_a_r, 1'b0);
                u_b[uj] = ot_a3_lane_pkg::fold_scale(raw_b, t_rd_data[7:0], scale_b_r, 1'b1);
            end else begin
                u_a[uj] = ot_a3_lane_pkg::pack_element(DETAIL_NONE, 1'b0, 1'b1, 8'b0, 12'b0);
                u_b[uj] = ot_a3_lane_pkg::pack_element(DETAIL_NONE, 1'b0, 1'b1, 8'b0, 12'b0);
            end
        end
        // The sequential lane's priority: a nonfinite or reserved operand,
        // then a reserved scale, then a scale application leaving binary32.
        for (uj = 0; uj < 4; uj = uj + 1) begin
            if (!seen_operand &&
                ((element_detail(u_a[uj]) == DETAIL_A_NONFINITE) ||
                 (element_detail(u_a[uj]) == DETAIL_A_RESERVED) ||
                 (element_detail(u_a[uj]) == DETAIL_SHAPE))) begin
                seen_operand = 1'b1;
                operand_detail = element_detail(u_a[uj]);
            end
            if (!seen_operand &&
                ((element_detail(u_b[uj]) == DETAIL_B_NONFINITE) ||
                 (element_detail(u_b[uj]) == DETAIL_B_RESERVED) ||
                 (element_detail(u_b[uj]) == DETAIL_SHAPE))) begin
                seen_operand = 1'b1;
                operand_detail = element_detail(u_b[uj]);
            end
        end
        for (uj = 0; uj < 4; uj = uj + 1) begin
            if (!seen_scale_reserved &&
                (element_detail(u_a[uj]) == DETAIL_SCALE_A_RESERVED)) begin
                seen_scale_reserved = 1'b1;
                scale_reserved_detail = DETAIL_SCALE_A_RESERVED;
            end
            if (!seen_scale_reserved &&
                (element_detail(u_b[uj]) == DETAIL_SCALE_B_RESERVED)) begin
                seen_scale_reserved = 1'b1;
                scale_reserved_detail = DETAIL_SCALE_B_RESERVED;
            end
        end
        for (uj = 0; uj < 4; uj = uj + 1) begin
            if (!seen_scale_range &&
                (element_detail(u_a[uj]) == DETAIL_SCALE_A_RANGE)) begin
                seen_scale_range = 1'b1;
                scale_range_detail = DETAIL_SCALE_A_RANGE;
            end
            if (!seen_scale_range &&
                (element_detail(u_b[uj]) == DETAIL_SCALE_B_RANGE)) begin
                seen_scale_range = 1'b1;
                scale_range_detail = DETAIL_SCALE_B_RANGE;
            end
        end
        if (seen_operand)
            u_detail = operand_detail;
        else if (seen_scale_reserved)
            u_detail = scale_reserved_detail;
        else if (seen_scale_range)
            u_detail = scale_range_detail;
    end

    // Unpack stage registers
    reg [29:0] r_a [0:3];
    reg [29:0] r_b [0:3];

    // ---------------------------------------------------------------------------
    // Multiply (combinational on the unpack stage)
    // ---------------------------------------------------------------------------
    reg [31:0] narrow_mags, wide_mags;
    wire [63:0] field_products;
    reg [3:0]  m_sign, m_zero;
    reg [63:0] m_mag;
    reg [47:0] m_pow;
    integer    mj;
    integer    pow_sum;
    always @* begin
        for (mj = 0; mj < 4; mj = mj + 1) begin
            narrow_mags[mj*8 +: 8] = swap_ab ? element_mag(r_b[mj]) : element_mag(r_a[mj]);
            wide_mags[mj*8 +: 8]   = swap_ab ? element_mag(r_a[mj]) : element_mag(r_b[mj]);
        end
    end
    assign field_products = ot_a3_lane_pkg::multiplier_field(mode, narrow_mags, wide_mags);
    always @* begin
        for (mj = 0; mj < 4; mj = mj + 1) begin
            m_sign[mj] = element_sign(r_a[mj]) ^ element_sign(r_b[mj]);
            m_zero[mj] = element_zero(r_a[mj]) | element_zero(r_b[mj]);
            m_mag[mj*16 +: 16] = field_products[mj*16 +: 16];
            pow_sum = {{20{r_a[mj][11]}}, element_pow(r_a[mj])} +
                      {{20{r_b[mj][11]}}, element_pow(r_b[mj])};
            m_pow[mj*12 +: 12] = pow_sum[11:0];
        end
    end

    // Multiply stage registers
    reg [3:0]  p_sign, p_zero;
    reg [63:0] p_mag;
    reg [47:0] p_pow;

    // ---------------------------------------------------------------------------
    // Group sum and normalise: four register stages on the multiply stage
    // ---------------------------------------------------------------------------
    // This was one combinational block from the multiply registers to the group
    // registers, and it was the worst setup path of both routed views of the
    // lane: `p_mag[0] -> g_pow[11]` on asap7 and `p_mag[1] -> g_mag[32]` on
    // sky130hd, around 146 data-path cells of group alignment each, and the
    // period-independent search put the lane at 4.32 ns (232 MHz) at asap7 TT
    // (results/physical_abi3/*/a3_lane_pipelined/pnr.json, the records this
    // change was written against).  In one cycle the block encoded four
    // significands, took a four-way exponent minimum, ran four 48-bit variable
    // align shifts, a serial chain of four 50-bit signed adds, a 50-bit negate,
    // a 48-bit leading-zero count and a 48-bit normalise shift.  It is cut into
    // four stages, each carrying its own copy of the two operand shapes the
    // block serves (g = 1's rounded product and g > 1's exact aligned sum):
    //
    //   G1 encode     msb16 per product, the product range check, the four-way
    //                 minimum of the counting powers and each product's align
    //                 distance; at g = 1, round_product instead
    //   G2 align      the four 48-bit variable shifts and the first level of the
    //                 add tree (two 50-bit signed adds side by side)
    //   G3 sum        the tree's second level and the magnitude of the sum; the
    //                 group's failure detail is resolved here
    //   G4 normalise  msb48, the normalise shift and the power adjust, into the
    //                 g_* registers the adder's first piece reads
    //
    // The deepest of the four is G1's round_product (a 17-bit subnormal shift,
    // its sticky and its increment in series).  After the cut this block is no
    // longer the lane's longest path at all: a generic elaboration's longest
    // topological path (yosys `synth -flatten; abc -g ...; ltp -noff`) falls
    // from 267 cells starting at p_mag to 115 starting at the adder's first
    // register, at a cost of about 5 % more cells, so the next path to answer
    // for is the adder's own middle piece, acc_sum_normalise.  That is a
    // proxy on a generic gate set, not a setup number: only a route measures
    // this lane, and this change has not had one.
    //
    // Throughput is unchanged at one lane-op per cycle, and that is structural,
    // not a measurement: the only cyclic dependence in this lane is the
    // accumulator recurrence, which runs from the accumulator read at the group
    // registers, through the L adder stages, to the writeback -- L cycles, and
    // entirely downstream of here.  Everything above the group registers is
    // feed-forward, so three more registers in it delay every token equally and
    // change no distance the issue logic enforces: a slot still may not reissue
    // for L cycles (slot_wait = L_WAIT), and a chain's next add still meets its
    // predecessor's result exactly at the writeback bypass.  What grows is
    // latency: the first lane-op retires three cycles later than before (the
    // front end is P = 8 stages, was 5) and the whole run is three cycles
    // longer, while the steady-state window between the first and the last
    // retirement is the same length.
    //
    // Three restructurings inside the block are what let the stages be shallow;
    // each is an identity, not an approximation, which is why gate D1 still
    // holds bit for bit:
    //
    //   * the serial four-way minimum becomes a two-level tree.  A product that
    //     does not count carries POW_NEUTRAL, which no real power can beat, so
    //     the tree's minimum equals the serial minimum over the counting
    //     products; when none counts the tree returns POW_NEUTRAL and it is
    //     never read (the sum is then zero, and G4 forces a zero group's power
    //     to 0 exactly as the serial form did).
    //   * the serial chain of four 50-bit signed adds becomes a balanced tree.
    //     Every add in the chain was a wrapping 50-bit two's complement add, and
    //     addition modulo 2**50 is associative and commutative, so any grouping
    //     of the same four terms yields the same 50 bits.  The one place the
    //     chain's width mattered -- the 48-bit window check -- reads the final
    //     sum, never an intermediate, and is unchanged.
    //   * the magnitude of the sum no longer puts a negate in series with the
    //     final add: -(p0 + p1) = ~p0 + ~p1 + 2 modulo 2**50, so the negated sum
    //     is formed from the inverted summands by an adder that runs beside the
    //     sum's own, and only the select waits for the sign bit.
    //
    // The failure detail is resolved once, in G3, in the order the single block
    // resolved it: within that block later assignments overwrote earlier ones,
    // so an aligner exit (a clamped align distance, or a sum outside the 48-bit
    // window) beat a product range exit, which beat none.  G1 and G3 therefore
    // raise flags rather than details, and G3 turns the flags into the one
    // detail token_with_detail applies -- so gate D5's modes stay distinct and
    // an unpack detail still wins over both, as before.
    // ---------------------------------------------------------------------------

    // An exponent that never wins the four-way minimum: a real product power is
    // a sign-extended 12-bit code, so it is at most 2047.
    localparam integer POW_NEUTRAL = 4095;

    // -- G1: encode, the exponent minimum and the align distances ---------------
    reg [38:0] rounded;
    reg [15:0] ge_mag_c   [0:3];
    reg [5:0]  ge_shift_c [0:3];
    reg [3:0]  ge_sign_c, ge_use_c;
    reg [12:0] ge_pow_c;
    reg        ge_range_c, ge_clamp_c;
    reg [16:0] ge_s_mag_c;
    reg        ge_s_sign_c, ge_s_zero_c;
    reg [7:0]  ge_s_detail_c;
    integer    pow_of  [0:3];       // each product's power, sign extended
    integer    pow_key [0:3];       // ... or POW_NEUTRAL when it does not count
    integer    pow_lo01, pow_lo23, pow_min;
    integer    gj, msb_j, shift_j;
    always @* begin
        rounded = 39'b0;
        ge_sign_c = 4'b0;
        ge_use_c = 4'b0;
        ge_pow_c = 13'b0;
        ge_range_c = 1'b0;
        ge_clamp_c = 1'b0;
        ge_s_mag_c = 17'b0;
        ge_s_sign_c = 1'b0;
        ge_s_zero_c = 1'b1;
        ge_s_detail_c = DETAIL_NONE;
        pow_lo01 = POW_NEUTRAL;
        pow_lo23 = POW_NEUTRAL;
        pow_min = POW_NEUTRAL;
        msb_j = 0;
        shift_j = 0;
        for (gj = 0; gj < 4; gj = gj + 1) begin
            ge_mag_c[gj] = 16'b0;
            ge_shift_c[gj] = 6'b0;
            pow_of[gj] = {{20{p_pow[gj*12 + 11]}}, p_pow[gj*12 +: 12]};
            pow_key[gj] = POW_NEUTRAL;
        end
        if (mode == 2'd0) begin
            // g = 1: one product, rounded to binary32 (subnormal grid) here.
            // Its 17-bit significand, sign, zero and detail travel beside the
            // group path -- G2 and G3 carry them untouched -- and G3 selects
            // them, so the shifters and the sum tree stay quiet at g = 1.
            rounded = ot_a3_lane_pkg::round_product(
                p_sign[0], p_zero[0], p_mag[15:0], p_pow[11:0]);
            ge_s_detail_c = rounded[38:31];
            ge_s_sign_c = rounded[30];
            ge_s_zero_c = rounded[29];
            ge_s_mag_c = rounded[28:12];
            pow_min = {{20{rounded[11]}}, rounded[11:0]};
        end else begin
            // Exact products; the minimum power of the nonzero ones is the
            // fixed-point unit of the group sum.
            for (gj = 0; gj < 4; gj = gj + 1) begin
                ge_mag_c[gj] = p_mag[gj*16 +: 16];
                ge_sign_c[gj] = p_sign[gj];
                ge_use_c[gj] = !p_zero[gj] && (p_mag[gj*16 +: 16] != 16'b0);
                msb_j = ot_a3_lane_pkg::msb16(p_mag[gj*16 +: 16]);
                if (ge_use_c[gj]) begin
                    pow_key[gj] = pow_of[gj];
                    if (pow_of[gj] + msb_j > 127)
                        ge_range_c = 1'b1;
                end
            end
            pow_lo01 = (pow_key[1] < pow_key[0]) ? pow_key[1] : pow_key[0];
            pow_lo23 = (pow_key[3] < pow_key[2]) ? pow_key[3] : pow_key[2];
            pow_min  = (pow_lo23 < pow_lo01) ? pow_lo23 : pow_lo01;
            // A product that does not count may compute a negative or wrapped
            // distance here; it is never shifted in and never raises the clamp,
            // exactly as the serial loop only aligned the counting products.
            for (gj = 0; gj < 4; gj = gj + 1) begin
                shift_j = pow_of[gj] - pow_min;
                if (ge_use_c[gj] && (shift_j > 32)) begin
                    ge_clamp_c = 1'b1;
                    shift_j = 32;
                end
                ge_shift_c[gj] = shift_j[5:0];
            end
        end
        ge_pow_c = pow_min[12:0];
    end

    // G1 (encode) stage registers
    reg [15:0] ge_mag   [0:3];
    reg [5:0]  ge_shift [0:3];
    reg [3:0]  ge_sign, ge_use;
    reg [12:0] ge_pow;
    reg        ge_range, ge_clamp;
    reg [16:0] ge_s_mag;
    reg        ge_s_sign, ge_s_zero;
    reg [7:0]  ge_s_detail;

    // -- G2: the four align shifts and the first level of the add tree ----------
    reg [47:0] aligned   [0:3];
    reg [49:0] term      [0:3];
    reg [49:0] ga_part_c [0:1];
    integer    aj;
    always @* begin
        for (aj = 0; aj < 4; aj = aj + 1) begin
            aligned[aj] = {32'b0, ge_mag[aj]} << ge_shift[aj];
            // The sign is applied without a negate per product: (x ^ -s) + s is
            // x for s = 0 and ~x + 1 for s = 1, and the two carry bits of a pair
            // fold into that pair's own adder below.  A product that does not
            // count contributes exactly zero, and so does its carry.
            term[aj] = ge_use[aj] ? ({50{ge_sign[aj]}} ^ {2'b0, aligned[aj]})
                                  : 50'b0;
        end
        ga_part_c[0] = term[0] + term[1]
                     + {49'b0, (ge_use[0] & ge_sign[0])}
                     + {49'b0, (ge_use[1] & ge_sign[1])};
        ga_part_c[1] = term[2] + term[3]
                     + {49'b0, (ge_use[2] & ge_sign[2])}
                     + {49'b0, (ge_use[3] & ge_sign[3])};
    end

    // G2 (align) stage registers
    reg [49:0] ga_part [0:1];
    reg [12:0] ga_pow;
    reg        ga_range, ga_clamp;
    reg [16:0] ga_s_mag;
    reg        ga_s_sign, ga_s_zero;
    reg [7:0]  ga_s_detail;

    // -- G3: the tree's second level, the magnitude, and the detail -------------
    reg [49:0] group_sum, group_neg, group_abs;
    reg        gs_sign_c, gs_zero_c;
    reg [47:0] gs_mag_c;
    reg [7:0]  gs_detail_c;
    always @* begin
        group_sum = ga_part[0] + ga_part[1];
        group_neg = (~ga_part[0]) + (~ga_part[1]) + 50'd2;
        gs_sign_c = group_sum[49];
        group_abs = gs_sign_c ? group_neg : group_sum;
        gs_mag_c = group_abs[47:0];
        gs_zero_c = (gs_mag_c == 48'b0);
        if (gs_zero_c)
            gs_sign_c = 1'b0;
        gs_detail_c = (ga_clamp || (group_abs[49:48] != 2'b00)) ? DETAIL_ALIGNER :
                      (ga_range ? DETAIL_PRODUCT_RANGE : DETAIL_NONE);
        if (mode == 2'd0) begin
            gs_mag_c = {31'b0, ga_s_mag};
            gs_sign_c = ga_s_sign;
            gs_zero_c = ga_s_zero;
            gs_detail_c = ga_s_detail;
        end
    end

    // G3 (sum) stage registers
    reg [47:0] gs_mag;
    reg        gs_sign, gs_zero;
    reg [12:0] gs_pow;

    // -- G4: normalise ----------------------------------------------------------
    reg        g_zero_c, g_sign_c;
    reg [47:0] g_mag_c;
    reg [11:0] g_pow_c;
    integer    lz, pow_res;
    always @* begin
        g_zero_c = gs_zero;
        g_sign_c = gs_sign;
        g_mag_c = gs_mag;
        lz = 0;
        pow_res = {{19{gs_pow[12]}}, gs_pow};
        // Normalise: leading one to bit 47, power adjusted.
        if (!g_zero_c) begin
            lz = 47 - ot_a3_lane_pkg::msb48(gs_mag);
            g_mag_c = gs_mag << lz;
            pow_res = pow_res - lz;
        end else begin
            pow_res = 0;
        end
        g_pow_c = pow_res[11:0];
    end

    // G4 (normalise) stage registers: what the adder's first piece reads
    reg        g_zero, g_sign;
    reg [47:0] g_mag;
    reg [11:0] g_pow;

    // ---------------------------------------------------------------------------
    // Adder: L register stages over three combinational pieces
    // ---------------------------------------------------------------------------
    wire        g_valid = token_valid(tok_g);
    wire [2:0]  g_slot  = token_slot(tok_g);
    wire        g_first = token_first(tok_g);

    // Writeback comes from the last adder stage.
    wire [TOKEN_BITS-1:0] wb_token = tok_a[L-1];
    wire        wb_valid = token_valid(wb_token);
    wire [2:0]  wb_slot  = token_slot(wb_token);
    wire [31:0] wb_code;
    wire [1:0]  wb_error;

    // Accumulator read with same-slot bypass; a chain's first add starts
    // from +0.0 whatever the slot holds.
    wire [31:0] acc_in = g_first ? 32'b0 :
                         ((wb_valid && (wb_slot == g_slot)) ? wb_code : acc_file[g_slot]);

    wire [118:0] piece1 = ot_a3_lane_pkg::acc_align(acc_in, g_zero, g_sign, g_mag, g_pow);

    generate
        if (L >= 3) begin : gen_l3
            reg [118:0] r1;
            reg [65:0]  r2;
            reg [33:0]  r3;
            always @(posedge clk) begin
                r1 <= piece1;
                r2 <= ot_a3_lane_pkg::acc_sum_normalise(r1);
                r3 <= ot_a3_lane_pkg::acc_round_pack(r2);
            end
            assign wb_code = r3[31:0];
            assign wb_error = r3[33:32];
        end else if (L == 2) begin : gen_l2
            reg [118:0] r1;
            reg [33:0]  r2;
            always @(posedge clk) begin
                r1 <= piece1;
                r2 <= ot_a3_lane_pkg::acc_round_pack(
                          ot_a3_lane_pkg::acc_sum_normalise(r1));
            end
            assign wb_code = r2[31:0];
            assign wb_error = r2[33:32];
        end else begin : gen_l1
            reg [33:0] r1;
            always @(posedge clk) begin
                r1 <= ot_a3_lane_pkg::acc_round_pack(
                          ot_a3_lane_pkg::acc_sum_normalise(piece1));
            end
            assign wb_code = r1[31:0];
            assign wb_error = r1[33:32];
        end
    endgenerate

    wire [7:0] wb_detail = (token_detail(wb_token) != DETAIL_NONE)
                           ? token_detail(wb_token)
                           : ((wb_error != 2'd0) ? DETAIL_ACCUMULATE_RANGE : DETAIL_NONE);
    wire [18:0] narrowed = ot_fp32_rne_pkg::fp32_to_bf16_rne(wb_code);

    // ---------------------------------------------------------------------------
    // Sequential logic
    // ---------------------------------------------------------------------------
    // Admission: fail closed on any shape or format this lane does not
    // implement.  shape_ok is the combinational part; the divisibility rules
    // (block a multiple of g, block dividing K) come from the admission
    // divider below and are decided in S_ADMIT, never on the issue path.
    reg shape_ok;
    always @* begin
        shape_ok = (cfg_rows != 16'd0) && (cfg_cols != 16'd0) && (cfg_depth != 16'd0);
        // Supported storage formats and group sizes.
        if ((cfg_dtype_a != FMT_BF16) && (cfg_dtype_a != FMT_FP8_E4M3FN) &&
            (cfg_dtype_a != FMT_MXFP4_E2M1))
            shape_ok = 1'b0;
        if ((cfg_dtype_b != FMT_BF16) && (cfg_dtype_b != FMT_FP8_E4M3FN) &&
            (cfg_dtype_b != FMT_MXFP4_E2M1))
            shape_ok = 1'b0;
        if ((cfg_group != 8'd1) && (cfg_group != 8'd2) && (cfg_group != 8'd4))
            shape_ok = 1'b0;
        // A group mode needs block formats on both sides: the exact aligner is
        // sized for their exponent ranges, and a BF16 operand's range would
        // exceed it, so it is refused rather than approximated.
        if ((cfg_group != 8'd1) &&
            ((cfg_dtype_a == FMT_BF16) || (cfg_dtype_b == FMT_BF16)))
            shape_ok = 1'b0;
        // g = 4 puts an E2M1 operand on the narrow side of the field.
        if ((cfg_group == 8'd4) &&
            (cfg_dtype_a != FMT_MXFP4_E2M1) && (cfg_dtype_b != FMT_MXFP4_E2M1))
            shape_ok = 1'b0;
        // A block-scaled operand needs a block; that it is a multiple of g and
        // divides K is checked from the divider's remainder in S_ADMIT.
        if (cfg_scale_a && (cfg_block_a == 16'd0))
            shape_ok = 1'b0;
        if (cfg_scale_b && (cfg_block_b == 16'd0))
            shape_ok = 1'b0;
    end

    // One restoring step of depth / block on each side: shift the next
    // numerator bit into the partial remainder and subtract the block if it
    // fits.  Only S_ADMIT advances it.
    // (The partial remainder is below the block, so a fitting difference is
    // below 2^16 and the 16-bit subtraction is exact.)
    wire [16:0] div_sh_a   = {div_r_a, div_n[15]};
    wire [16:0] div_sh_b   = {div_r_b, div_n[15]};
    wire        div_fit_a  = (div_sh_a >= {1'b0, cfg_block_a});
    wire        div_fit_b  = (div_sh_b >= {1'b0, cfg_block_b});
    wire [15:0] div_diff_a = div_sh_a[15:0] - cfg_block_a;
    wire [15:0] div_diff_b = div_sh_b[15:0] - cfg_block_b;
    // block mod g: the low log2(g) bits of the block, g latched as group_shift.
    wire        block_mod_g_a = (group_shift == 2'd1) ? cfg_block_a[0] :
                                (group_shift == 2'd2) ? (|cfg_block_a[1:0]) : 1'b0;
    wire        block_mod_g_b = (group_shift == 2'd1) ? cfg_block_b[0] :
                                (group_shift == 2'd2) ? (|cfg_block_b[1:0]) : 1'b0;
    wire        admit_ok = shape_ok &&
                           !(cfg_scale_a && (block_mod_g_a || (div_r_a != 16'd0))) &&
                           !(cfg_scale_b && (block_mod_g_b || (div_r_b != 16'd0)));

    integer si;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            out_count <= 32'b0;
            saturation_count <= 32'b0;
            mac_count <= 32'b0;
            product_count <= 32'b0;
            op_retire <= 1'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            s_rd_en <= 1'b0;
            t_rd_en <= 1'b0;
            a_rd_addr <= 32'b0;
            b_rd_addr <= 32'b0;
            s_rd_addr <= 32'b0;
            t_rd_addr <= 32'b0;
            out_we <= 1'b0;
            out_addr <= 32'b0;
            out_data <= 32'b0;
            out_acc <= 32'b0;
            mode <= 2'd0;
            group <= 3'd1;
            group_shift <= 2'd0;
            swap_ab <= 1'b0;
            depth_words <= 16'b0;
            kg_count <= 16'b0;
            tail_valid <= 3'd1;
            faulted <= 1'b0;
            dtype_a_r <= 8'b0;
            dtype_b_r <= 8'b0;
            scale_a_r <= 1'b0;
            scale_b_r <= 1'b0;
            out_fp32_r <= 1'b0;
            rows_r <= 16'b0;
            cols_r <= 16'b0;
            b_base_r <= 32'b0;
            scale_a_base_r <= 32'b0;
            scale_b_base_r <= 32'b0;
            rpb_a <= 16'd1;
            rpb_b <= 16'd1;
            cpr_a <= 16'b0;
            cpr_b <= 16'b0;
            bw_a <= 16'b0;
            bw_b <= 16'b0;
            div_step <= 5'b0;
            div_n <= 16'b0;
            div_r_a <= 16'b0;
            div_r_b <= 16'b0;
            div_q_a <= 16'b0;
            div_q_b <= 16'b0;
            row <= 16'b0;
            pass_col0 <= 16'b0;
            kg <= 16'b0;
            col_i <= 3'b0;
            issue_active <= 1'b0;
            inflight <= 32'b0;
            a_row_base <= 32'b0;
            out_row_base <= 32'b0;
            b_col_cursor <= 32'b0;
            row_in_block_a <= 16'b0;
            row_scale_a <= 32'b0;
            kg_in_block_a <= 16'b0;
            kg_in_block_b <= 16'b0;
            k_scale_a <= 16'b0;
            k_scale_b <= 16'b0;
            col_cur_in_block_b <= 16'b0;
            col_cur_scale_b <= 32'b0;
            for (si = 0; si < COL_SLOTS; si = si + 1) begin
                b_col_base[si] <= 32'b0;
                col_scale_b[si] <= 32'b0;
            end
            tok_i <= {TOKEN_BITS{1'b0}};
            tok_r <= {TOKEN_BITS{1'b0}};
            tok_u <= {TOKEN_BITS{1'b0}};
            tok_m <= {TOKEN_BITS{1'b0}};
            tok_ge <= {TOKEN_BITS{1'b0}};
            tok_ga <= {TOKEN_BITS{1'b0}};
            tok_gs <= {TOKEN_BITS{1'b0}};
            tok_g <= {TOKEN_BITS{1'b0}};
            for (si = 0; si < L; si = si + 1)
                tok_a[si] <= {TOKEN_BITS{1'b0}};
            for (si = 0; si < ACC_SLOTS; si = si + 1) begin
                slot_wait[si] <= 4'd0;
                acc_file[si] <= 32'b0;
            end
            for (si = 0; si < 4; si = si + 1) begin
                r_a[si] <= 30'b0;
                r_b[si] <= 30'b0;
            end
            p_sign <= 4'b0;
            p_zero <= 4'b0;
            p_mag <= 64'b0;
            p_pow <= 48'b0;
            for (si = 0; si < 4; si = si + 1) begin
                ge_mag[si] <= 16'b0;
                ge_shift[si] <= 6'b0;
            end
            ge_sign <= 4'b0;
            ge_use <= 4'b0;
            ge_pow <= 13'b0;
            ge_range <= 1'b0;
            ge_clamp <= 1'b0;
            ge_s_mag <= 17'b0;
            ge_s_sign <= 1'b0;
            ge_s_zero <= 1'b1;
            ge_s_detail <= DETAIL_NONE;
            ga_part[0] <= 50'b0;
            ga_part[1] <= 50'b0;
            ga_pow <= 13'b0;
            ga_range <= 1'b0;
            ga_clamp <= 1'b0;
            ga_s_mag <= 17'b0;
            ga_s_sign <= 1'b0;
            ga_s_zero <= 1'b1;
            ga_s_detail <= DETAIL_NONE;
            gs_mag <= 48'b0;
            gs_sign <= 1'b0;
            gs_zero <= 1'b1;
            gs_pow <= 13'b0;
            g_zero <= 1'b1;
            g_sign <= 1'b0;
            g_mag <= 48'b0;
            g_pow <= 12'b0;
        end else begin
            done <= 1'b0;
            out_we <= 1'b0;
            op_retire <= 1'b0;
            a_rd_en <= 1'b0;
            b_rd_en <= 1'b0;
            s_rd_en <= 1'b0;
            t_rd_en <= 1'b0;

            // -- pipeline advance ------------------------------------------------
            tok_r <= tok_i;
            tok_u <= token_with_detail(tok_r, u_detail);
            for (si = 0; si < 4; si = si + 1) begin
                r_a[si] <= u_a[si];
                r_b[si] <= u_b[si];
            end
            tok_m <= tok_u;
            p_sign <= m_sign;
            p_zero <= m_zero;
            p_mag <= m_mag;
            p_pow <= m_pow;
            // The group block's four stages.  Only G3 contributes a detail, and
            // it contributes the one the single-stage block resolved (aligner
            // over product range over none), so the token still meets exactly
            // one group detail on its way to the adder.
            tok_ge <= tok_m;
            for (si = 0; si < 4; si = si + 1) begin
                ge_mag[si] <= ge_mag_c[si];
                ge_shift[si] <= ge_shift_c[si];
            end
            ge_sign <= ge_sign_c;
            ge_use <= ge_use_c;
            ge_pow <= ge_pow_c;
            ge_range <= ge_range_c;
            ge_clamp <= ge_clamp_c;
            ge_s_mag <= ge_s_mag_c;
            ge_s_sign <= ge_s_sign_c;
            ge_s_zero <= ge_s_zero_c;
            ge_s_detail <= ge_s_detail_c;
            tok_ga <= tok_ge;
            ga_part[0] <= ga_part_c[0];
            ga_part[1] <= ga_part_c[1];
            ga_pow <= ge_pow;
            ga_range <= ge_range;
            ga_clamp <= ge_clamp;
            ga_s_mag <= ge_s_mag;
            ga_s_sign <= ge_s_sign;
            ga_s_zero <= ge_s_zero;
            ga_s_detail <= ge_s_detail;
            tok_gs <= token_with_detail(tok_ga, gs_detail_c);
            gs_mag <= gs_mag_c;
            gs_sign <= gs_sign_c;
            gs_zero <= gs_zero_c;
            gs_pow <= ga_pow;
            tok_g <= tok_gs;
            g_zero <= g_zero_c;
            g_sign <= g_sign_c;
            g_mag <= g_mag_c;
            g_pow <= g_pow_c;
            tok_a[0] <= tok_g;
            for (si = 1; si < L; si = si + 1)
                tok_a[si] <= tok_a[si-1];
            for (si = 0; si < ACC_SLOTS; si = si + 1)
                if (slot_wait[si] != 4'd0)
                    slot_wait[si] <= slot_wait[si] - 4'd1;

            // -- issue -----------------------------------------------------------
            tok_i <= {TOKEN_BITS{1'b0}};
            if (can_issue) begin
                a_rd_en <= 1'b1;
                a_rd_addr <= a_row_base + {16'b0, kg};
                b_rd_en <= 1'b1;
                b_rd_addr <= b_col_now + {16'b0, kg};
                s_rd_en <= 1'b1;
                s_rd_addr <= scale_a_base_r + row_scale_a + {16'b0, k_scale_a};
                t_rd_en <= 1'b1;
                t_rd_addr <= scale_b_base_r + col_scale_now + {16'b0, k_scale_b};
                tok_i <= make_token(1'b1, col_i, open_col, last_kg,
                                    last_kg ? tail_valid : group,
                                    out_row_base + {16'b0, column},
                                    DETAIL_NONE);
                slot_wait[col_i] <= L_WAIT;
                inflight <= inflight + 32'd1;
                if (open_col) begin
                    // The column is opened: keep its bases for the later
                    // k-groups and step the cursor to the next column.
                    b_col_base[col_idx] <= b_col_cursor;
                    col_scale_b[col_idx] <= col_cur_scale_b;
                    b_col_cursor <= b_col_cursor + {16'b0, depth_words};
                    if (col_wrap_b) begin
                        col_cur_in_block_b <= 16'd0;
                        col_cur_scale_b <= col_cur_scale_b + {16'b0, cpr_b};
                    end else begin
                        col_cur_in_block_b <= col_cur_in_block_b + 16'd1;
                    end
                end
                if (col_i + 3'd1 == n_active) begin
                    col_i <= 3'd0;
                    if (last_kg) begin
                        kg <= 16'd0;
                        kg_in_block_a <= 16'd0;
                        kg_in_block_b <= 16'd0;
                        k_scale_a <= 16'd0;
                        k_scale_b <= 16'd0;
                        if (pass_col0 + {13'b0, n_active} >= cols_r) begin
                            // End of the row: the column cursor returns to
                            // column 0 (this overrides the step above).
                            pass_col0 <= 16'd0;
                            b_col_cursor <= b_base_r;
                            col_cur_in_block_b <= 16'd0;
                            col_cur_scale_b <= 32'b0;
                            if (row + 16'd1 == rows_r) begin
                                issue_active <= 1'b0;
                            end else begin
                                row <= row + 16'd1;
                                a_row_base <= a_row_base + {16'b0, depth_words};
                                out_row_base <= out_row_base + {16'b0, cols_r};
                                if (row_wrap_a) begin
                                    row_in_block_a <= 16'd0;
                                    row_scale_a <= row_scale_a + {16'b0, cpr_a};
                                end else begin
                                    row_in_block_a <= row_in_block_a + 16'd1;
                                end
                            end
                        end else begin
                            pass_col0 <= pass_col0 + {13'b0, n_active};
                        end
                    end else begin
                        kg <= kg + 16'd1;
                        if (kg_wrap_a) begin
                            kg_in_block_a <= 16'd0;
                            k_scale_a <= k_scale_a + 16'd1;
                        end else begin
                            kg_in_block_a <= kg_in_block_a + 16'd1;
                        end
                        if (kg_wrap_b) begin
                            kg_in_block_b <= 16'd0;
                            k_scale_b <= k_scale_b + 16'd1;
                        end else begin
                            kg_in_block_b <= kg_in_block_b + 16'd1;
                        end
                    end
                end else begin
                    col_i <= col_i + 3'd1;
                end
            end

            // -- writeback, in issue order ---------------------------------------
            if (wb_valid && !faulted) begin
                if (wb_detail != DETAIL_NONE) begin
                    faulted <= 1'b1;
                    error_code <= ot_a3_lane_pkg::error_code_of_detail(wb_detail);
                    error_detail <= wb_detail;
                    issue_active <= 1'b0;
                    inflight <= 32'b0;
                    tok_i <= {TOKEN_BITS{1'b0}};
                    tok_r <= {TOKEN_BITS{1'b0}};
                    tok_u <= {TOKEN_BITS{1'b0}};
                    tok_m <= {TOKEN_BITS{1'b0}};
                    tok_ge <= {TOKEN_BITS{1'b0}};
                    tok_ga <= {TOKEN_BITS{1'b0}};
                    tok_gs <= {TOKEN_BITS{1'b0}};
                    tok_g <= {TOKEN_BITS{1'b0}};
                    for (si = 0; si < L; si = si + 1)
                        tok_a[si] <= {TOKEN_BITS{1'b0}};
                    a_rd_en <= 1'b0;
                    b_rd_en <= 1'b0;
                    s_rd_en <= 1'b0;
                    t_rd_en <= 1'b0;
                    state <= S_DONE;
                end else begin
                    acc_file[wb_slot] <= wb_code;
                    mac_count <= mac_count + 32'd1;
                    product_count <= product_count + {29'b0, token_nvalid(wb_token)};
                    op_retire <= 1'b1;
                    inflight <= inflight - 32'd1 + (can_issue ? 32'd1 : 32'd0);
                    if (token_last(wb_token)) begin
                        out_we <= 1'b1;
                        out_addr <= token_address(wb_token);
                        out_acc <= wb_code;
                        out_data <= out_fp32_r ? wb_code : {16'b0, narrowed[15:0]};
                        out_count <= out_count + 32'd1;
                        if (!out_fp32_r && narrowed[16])
                            saturation_count <= saturation_count + 32'd1;
                    end
                end
            end

            // -- control ---------------------------------------------------------
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        error_detail <= DETAIL_NONE;
                        out_count <= 32'b0;
                        saturation_count <= 32'b0;
                        mac_count <= 32'b0;
                        product_count <= 32'b0;
                        faulted <= 1'b0;
                        row <= 16'b0;
                        pass_col0 <= 16'b0;
                        kg <= 16'b0;
                        col_i <= 3'b0;
                        inflight <= 32'b0;
                        for (si = 0; si < ACC_SLOTS; si = si + 1)
                            slot_wait[si] <= 4'd0;
                        // Sample the configuration; the divisibility rules
                        // are decided in S_ADMIT once the divider has run.
                        dtype_a_r <= cfg_dtype_a;
                        dtype_b_r <= cfg_dtype_b;
                        scale_a_r <= cfg_scale_a;
                        scale_b_r <= cfg_scale_b;
                        out_fp32_r <= cfg_out_fp32;
                        rows_r <= cfg_rows;
                        cols_r <= cfg_cols;
                        b_base_r <= cfg_b_base;
                        scale_a_base_r <= cfg_scale_a_base;
                        scale_b_base_r <= cfg_scale_b_base;
                        case (cfg_group)
                            8'd2: begin
                                mode <= 2'd1; group <= 3'd2; group_shift <= 2'd1;
                                depth_words <= (cfg_depth + 16'd1) >> 1;
                                kg_count <= (cfg_depth + 16'd1) >> 1;
                                tail_valid <= (cfg_depth[0] == 1'b0) ? 3'd2 : 3'd1;
                            end
                            8'd4: begin
                                mode <= 2'd2; group <= 3'd4; group_shift <= 2'd2;
                                depth_words <= (cfg_depth + 16'd3) >> 2;
                                kg_count <= (cfg_depth + 16'd3) >> 2;
                                tail_valid <= (cfg_depth[1:0] == 2'b00) ? 3'd4 : {1'b0, cfg_depth[1:0]};
                            end
                            default: begin
                                mode <= 2'd0; group <= 3'd1; group_shift <= 2'd0;
                                depth_words <= cfg_depth;
                                kg_count <= cfg_depth;
                                tail_valid <= 3'd1;
                            end
                        endcase
                        swap_ab <= (cfg_dtype_b == FMT_MXFP4_E2M1) &&
                                   (cfg_dtype_a != FMT_MXFP4_E2M1);
                        div_step <= 5'd0;
                        div_n <= cfg_depth;
                        div_r_a <= 16'b0;
                        div_r_b <= 16'b0;
                        div_q_a <= 16'b0;
                        div_q_b <= 16'b0;
                        issue_active <= 1'b0;
                        state <= S_ADMIT;
                    end
                end

                S_ADMIT: begin
                    if (div_step != 5'd16) begin
                        // One quotient bit per cycle, both sides together.
                        div_r_a <= div_fit_a ? div_diff_a : div_sh_a[15:0];
                        div_r_b <= div_fit_b ? div_diff_b : div_sh_b[15:0];
                        div_q_a <= {div_q_a[14:0], div_fit_a};
                        div_q_b <= {div_q_b[14:0], div_fit_b};
                        div_n <= {div_n[14:0], 1'b0};
                        div_step <= div_step + 5'd1;
                    end else if (!admit_ok) begin
                        error_code <= ERR_SHAPE;
                        error_detail <= DETAIL_SHAPE;
                        issue_active <= 1'b0;
                        state <= S_DONE;
                    end else begin
                        // Registered geometry for the walk; an unscaled side
                        // holds its scale address at the base.
                        rpb_a <= (cfg_block_rows_a == 16'd0) ? 16'd1 : cfg_block_rows_a;
                        rpb_b <= (cfg_block_rows_b == 16'd0) ? 16'd1 : cfg_block_rows_b;
                        cpr_a <= cfg_scale_a ? div_q_a : 16'd0;
                        cpr_b <= cfg_scale_b ? div_q_b : 16'd0;
                        bw_a <= cfg_scale_a ? (cfg_block_a >> group_shift) : 16'd0;
                        bw_b <= cfg_scale_b ? (cfg_block_b >> group_shift) : 16'd0;
                        a_row_base <= cfg_a_base;
                        out_row_base <= cfg_out_base;
                        b_col_cursor <= cfg_b_base;
                        row_in_block_a <= 16'd0;
                        row_scale_a <= 32'b0;
                        kg_in_block_a <= 16'd0;
                        kg_in_block_b <= 16'd0;
                        k_scale_a <= 16'd0;
                        k_scale_b <= 16'd0;
                        col_cur_in_block_b <= 16'd0;
                        col_cur_scale_b <= 32'b0;
                        issue_active <= 1'b1;
                        state <= S_RUN;
                    end
                end

                S_RUN: begin
                    if (!issue_active && (inflight == 32'd0) && !faulted &&
                        !wb_valid && !can_issue)
                        state <= S_DONE;
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
