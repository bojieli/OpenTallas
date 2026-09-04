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
// Pipeline (P = 5 front-end stages, then L = ADDER_STAGES adder stages):
//
//   issue    address generation for (row, column, k-group); one token per cycle
//   read     the operand memories answer one cycle after the address
//   unpack   storage code -> (sign, significand, power); E8M0 scale folded as
//            an exponent add with np.float32 subnormal rounding; nonfinite
//            BF16, reserved E4M3FN / E8M0 and scale range faults raised here
//   multiply the reconfigurable 8 x 8 partial-product field; exponent adds
//   group    g = 1: round the product to binary32 (subnormal grid), range
//            check; g > 1: exact aligned fixed-point group sum, range check;
//            then normalise for the adder
//   adder    align | add + normalise | round + pack, cut into L register
//            stages; accumulator read at entry (with bypass), written at exit
//
// Faults travel with their token and commit in issue order at the adder's
// exit, so a refused operation is deterministic: every pass that completed
// before the faulting pass has been written, the faulting pass and everything
// after it write nothing, and the lane stops with a distinct error detail
// (gate D5) whose class equals the sequential lane's error code.
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

    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_RUN  = 2'd1;
    localparam [1:0] S_DONE = 2'd2;

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

    // -- issue counters ----------------------------------------------------------
    reg [15:0] row;
    reg [15:0] pass_col0;
    reg [15:0] kg;
    reg [2:0]  col_i;
    reg        issue_active;
    reg [3:0]  slot_wait [0:ACC_SLOTS-1];
    reg [31:0] inflight;

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

    // Amendment A15: the E8M0 code for element (row, column) of a view over
    // ``depth`` columns is (row / block_rows) * (depth / block) + column / block.
    // Identical to the sequential lane's function.
    function automatic [31:0] scale_index;
        input [15:0] element_row;
        input [15:0] element_column;
        input [15:0] depth;
        input [15:0] block;
        input [15:0] block_rows;
        reg [15:0] rows_per_block;
        reg [15:0] elements_per_block;
        begin
            rows_per_block = (block_rows == 16'd0) ? 16'd1 : block_rows;
            elements_per_block = (block == 16'd0) ? 16'd1 : block;
            scale_index = ({16'b0, element_row} / {16'b0, rows_per_block}) *
                          ({16'b0, depth} / {16'b0, elements_per_block}) +
                          ({16'b0, element_column} / {16'b0, elements_per_block});
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
    wire [15:0] cols_left = cfg_cols - pass_col0;
    wire [2:0]  n_active  = (cols_left >= L16) ? L3 : cols_left[2:0];
    wire        last_kg   = (kg + 16'd1 == kg_count);
    wire [15:0] column    = pass_col0 + {13'b0, col_i};
    wire [15:0] k_first   = kg << group_shift;
    wire        can_issue = (state == S_RUN) && issue_active && !faulted &&
                            (slot_wait[col_i] == 4'd0);

    reg [TOKEN_BITS-1:0] tok_i, tok_r, tok_u, tok_m, tok_g;
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
                cfg_dtype_a, element_code(a_rd_data, cfg_dtype_a, uj), 1'b0);
            raw_b = ot_a3_lane_pkg::unpack_element(
                cfg_dtype_b, element_code(b_rd_data, cfg_dtype_b, uj), 1'b1);
            if (uj < token_nvalid(tok_r)) begin
                u_a[uj] = ot_a3_lane_pkg::fold_scale(raw_a, s_rd_data[7:0], cfg_scale_a, 1'b0);
                u_b[uj] = ot_a3_lane_pkg::fold_scale(raw_b, t_rd_data[7:0], cfg_scale_b, 1'b1);
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
    // Group sum and normalise (combinational on the multiply stage)
    // ---------------------------------------------------------------------------
    reg [38:0] rounded;
    reg        g_zero_c, g_sign_c;
    reg [47:0] g_mag_c;
    reg [11:0] g_pow_c;
    reg [7:0]  g_detail_c;
    reg [47:0] aligned;
    reg signed [49:0] group_sum;
    reg [49:0] group_abs;
    integer    gj;
    integer    pow_j, pow_min, shift_j, msb_j;
    reg        any_nonzero;
    integer    lz;
    always @* begin
        g_zero_c = 1'b1;
        g_sign_c = 1'b0;
        g_mag_c = 48'b0;
        g_pow_c = 12'b0;
        g_detail_c = DETAIL_NONE;
        rounded = 39'b0;
        aligned = 48'b0;
        group_sum = 50'sd0;
        group_abs = 50'd0;
        pow_min = 0;
        pow_j = 0;
        shift_j = 0;
        msb_j = 0;
        any_nonzero = 1'b0;
        lz = 0;
        gj = 0;
        if (mode == 2'd0) begin
            rounded = ot_a3_lane_pkg::round_product(
                p_sign[0], p_zero[0], p_mag[15:0], p_pow[11:0]);
            g_detail_c = rounded[38:31];
            g_sign_c = rounded[30];
            g_zero_c = rounded[29];
            g_mag_c = {31'b0, rounded[28:12]};
            pow_min = {{20{rounded[11]}}, rounded[11:0]};
        end else begin
            // Exact products; the minimum power of the nonzero ones is the
            // fixed-point unit of the group sum.
            for (gj = 0; gj < 4; gj = gj + 1) begin
                if (!p_zero[gj] && (p_mag[gj*16 +: 16] != 16'b0)) begin
                    pow_j = {{20{p_pow[gj*12 + 11]}}, p_pow[gj*12 +: 12]};
                    msb_j = ot_a3_lane_pkg::msb16(p_mag[gj*16 +: 16]);
                    if (pow_j + msb_j > 127)
                        g_detail_c = DETAIL_PRODUCT_RANGE;
                    if (!any_nonzero || (pow_j < pow_min))
                        pow_min = pow_j;
                    any_nonzero = 1'b1;
                end
            end
            for (gj = 0; gj < 4; gj = gj + 1) begin
                if (!p_zero[gj] && (p_mag[gj*16 +: 16] != 16'b0)) begin
                    pow_j = {{20{p_pow[gj*12 + 11]}}, p_pow[gj*12 +: 12]};
                    shift_j = pow_j - pow_min;
                    if (shift_j > 32) begin
                        g_detail_c = DETAIL_ALIGNER;
                        shift_j = 32;
                    end
                    aligned = {32'b0, p_mag[gj*16 +: 16]} << shift_j;
                    if (p_sign[gj])
                        group_sum = group_sum - $signed({2'b0, aligned});
                    else
                        group_sum = group_sum + $signed({2'b0, aligned});
                end
            end
            g_sign_c = group_sum[49];
            group_abs = g_sign_c ? (~group_sum + 50'd1) : group_sum;
            if (group_abs[49:48] != 2'b00)
                g_detail_c = DETAIL_ALIGNER;
            g_mag_c = group_abs[47:0];
            g_zero_c = (g_mag_c == 48'b0);
            if (g_zero_c)
                g_sign_c = 1'b0;
        end
        // Normalise: leading one to bit 47, power adjusted.
        if (!g_zero_c) begin
            lz = 47 - ot_a3_lane_pkg::msb48(g_mag_c);
            g_mag_c = g_mag_c << lz;
            pow_min = pow_min - lz;
        end else begin
            pow_min = 0;
        end
        g_pow_c = pow_min[11:0];
    end

    // Group stage registers
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
    // Start-time admission: fail closed on any shape or format this lane does
    // not implement.
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
        // A block-scaled operand: a block, a multiple of g, dividing K.
        if (cfg_scale_a) begin
            if (cfg_block_a == 16'd0)
                shape_ok = 1'b0;
            else if (((cfg_block_a % {8'b0, cfg_group}) != 16'd0) ||
                     ((cfg_depth % cfg_block_a) != 16'd0))
                shape_ok = 1'b0;
        end
        if (cfg_scale_b) begin
            if (cfg_block_b == 16'd0)
                shape_ok = 1'b0;
            else if (((cfg_block_b % {8'b0, cfg_group}) != 16'd0) ||
                     ((cfg_depth % cfg_block_b) != 16'd0))
                shape_ok = 1'b0;
        end
    end

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
            row <= 16'b0;
            pass_col0 <= 16'b0;
            kg <= 16'b0;
            col_i <= 3'b0;
            issue_active <= 1'b0;
            inflight <= 32'b0;
            tok_i <= {TOKEN_BITS{1'b0}};
            tok_r <= {TOKEN_BITS{1'b0}};
            tok_u <= {TOKEN_BITS{1'b0}};
            tok_m <= {TOKEN_BITS{1'b0}};
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
            tok_g <= token_with_detail(tok_m, g_detail_c);
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
                a_rd_addr <= cfg_a_base + ({16'b0, row} * {16'b0, depth_words}) + {16'b0, kg};
                b_rd_en <= 1'b1;
                b_rd_addr <= cfg_b_base + ({16'b0, column} * {16'b0, depth_words}) + {16'b0, kg};
                s_rd_en <= 1'b1;
                s_rd_addr <= cfg_scale_a_base +
                             scale_index(row, k_first, cfg_depth, cfg_block_a, cfg_block_rows_a);
                t_rd_en <= 1'b1;
                t_rd_addr <= cfg_scale_b_base +
                             scale_index(column, k_first, cfg_depth, cfg_block_b, cfg_block_rows_b);
                tok_i <= make_token(1'b1, col_i, (kg == 16'd0), last_kg,
                                    last_kg ? tail_valid : group,
                                    cfg_out_base + ({16'b0, row} * {16'b0, cfg_cols}) + {16'b0, column},
                                    DETAIL_NONE);
                slot_wait[col_i] <= L_WAIT;
                inflight <= inflight + 32'd1;
                if (col_i + 3'd1 == n_active) begin
                    col_i <= 3'd0;
                    if (last_kg) begin
                        kg <= 16'd0;
                        if (pass_col0 + {13'b0, n_active} >= cfg_cols) begin
                            pass_col0 <= 16'd0;
                            if (row + 16'd1 == cfg_rows)
                                issue_active <= 1'b0;
                            else
                                row <= row + 16'd1;
                        end else begin
                            pass_col0 <= pass_col0 + {13'b0, n_active};
                        end
                    end else begin
                        kg <= kg + 16'd1;
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
                        out_data <= cfg_out_fp32 ? wb_code : {16'b0, narrowed[15:0]};
                        out_count <= out_count + 32'd1;
                        if (!cfg_out_fp32 && narrowed[16])
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
                        if (!shape_ok) begin
                            error_code <= ERR_SHAPE;
                            error_detail <= DETAIL_SHAPE;
                            issue_active <= 1'b0;
                            state <= S_DONE;
                        end else begin
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
                            issue_active <= 1'b1;
                            state <= S_RUN;
                        end
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
