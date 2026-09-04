`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Exact ABI 3.0 VECTOR.MHC / HYPER_CONNECT_PRE tile scheduler.
//
// This block is the descriptor-admission and work-coordinate front end for the
// two released DeepSeek-V4-Flash HC_PRE sites:
//
//   * ROM wafer decode PC 15, OPERATOR descriptor 381; and
//   * HBM/SRAM cluster PC 14, OPERATOR descriptor 546.
//
// The 128-word semantic configuration is supplied only after the ordinary ABI
// record decoder, CRC checker, permission checker, wait scoreboard and view
// resolver have run.  The word layout is frozen alongside the vector builder
// in tools/build_a3_mhc_pre_tile_vectors.py.  This block independently checks
// the instruction identity, every OPERATOR reference, the complete numeric
// policy and digest, all six resolved view geometries, and the selected target
// SCHEDULE profile before exposing work.
//
// Projection tiles enumerate the exact logical contraction
//
//   [active_tokens, 16384] x [24, 16384]^T
//
// in increasing (token, parameter, K) tile-origin order.  K never splits or
// reorders one accumulator: a consumer must keep the accumulator live between
// consecutive depth tiles.  Weight and combination commit tiles then cover
// [active_tokens, 2, 4] and [active_tokens, 4, 4] exactly once.  Backpressure
// freezes every emitted field and advances no counter.
//
// This module deliberately contains no RMS, projection MAC, correctly rounded
// sigmoid/exponential, stable-softmax or Sinkhorn arithmetic.  Consequently a
// successful schedule is not full HC_PRE execution and its cycle count is not
// architectural latency or TPOT.  The retained campaign binds the complete
// authenticated functional-output digest without injecting those outputs here.
// ---------------------------------------------------------------------------
module ot_a3_vector_mhc_pre_tile_scheduler #(
    parameter integer CONFIG_WORDS = 128
) (
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          start,
    input  wire [CONFIG_WORDS*32-1:0]    config_words,

    output wire                          tile_valid,
    input  wire                          tile_ready,
    output wire [1:0]                    tile_kind,
    output wire [31:0]                   tile_token_base,
    output wire [31:0]                   tile_field_base,
    output wire [31:0]                   tile_k_base,
    output wire [31:0]                   tile_active_tokens,
    output wire [31:0]                   tile_active_fields,
    output wire [31:0]                   tile_active_k,
    output wire [63:0]                   tile_logical_work,
    output wire [63:0]                   tile_output_base,
    output wire [31:0]                   tile_output_row_stride,
    output wire                          tile_last,

    output reg                           busy,
    output reg                           done,
    output reg  [7:0]                    error_code,
    output reg  [63:0]                   projection_tile_count,
    output reg  [63:0]                   commit_tile_count,
    output reg  [63:0]                   logical_fma_count,
    output reg  [63:0]                   logical_output_count
);
    localparam [7:0] ERR_NONE        = 8'd0;
    localparam [7:0] ERR_INSTRUCTION = 8'd16;
    localparam [7:0] ERR_OPERATOR    = 8'd17;
    localparam [7:0] ERR_NUMERIC     = 8'd18;
    localparam [7:0] ERR_VIEW        = 8'd19;
    localparam [7:0] ERR_SCHEDULE    = 8'd20;

    localparam [1:0] PROFILE_ROM = 2'd0;
    localparam [1:0] PROFILE_HBM = 2'd1;

    localparam [1:0] TILE_PROJECTION  = 2'd0;
    localparam [1:0] TILE_WEIGHTS     = 2'd1;
    localparam [1:0] TILE_COMBINATION = 2'd2;

    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_EMIT = 2'd1;

    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [31:0] FAMILY_VECTOR = 32'h0000_0030;
    localparam [31:0] SUB_MHC = 32'h0000_0009;
    localparam [31:0] FMT_BF16 = 32'h0000_0010;
    localparam [31:0] FMT_FP32 = 32'h0000_0012;
    localparam [31:0] HC_EPSILON = 32'h3586_37bd;
    localparam [31:0] COUNTER_0 = 32'h0500_0001;
    localparam [31:0] COUNTER_1 = 32'h0500_0002;
    localparam [31:0] COUNTER_2 = 32'h0500_0003;

    function automatic [31:0] cfg;
        input [CONFIG_WORDS*32-1:0] words;
        input integer index;
        begin
            cfg = words[index*32 +: 32];
        end
    endfunction

    function automatic [31:0] view_cfg;
        input [CONFIG_WORDS*32-1:0] words;
        input integer slot;
        input integer field;
        begin
            view_cfg = cfg(words, 64 + slot*10 + field);
        end
    endfunction

    // The packed configuration is an explicit argument of both accessors so
    // that every simulator and synthesis front end discovers the complete
    // combinational sensitivity.  The top-level profile slices remain direct
    // for clarity.
    wire [31:0] profile_word = config_words[0 +: 32];
    wire [1:0] profile = profile_word[1:0];
    wire [31:0] active_tokens = config_words[32 +: 32];

    wire profile_known =
        (profile_word == PROFILE_ROM) || (profile_word == PROFILE_HBM);

    // Instruction words 2..9.  The wait-set record itself is upstream; word 6
    // is the independently decoded sole producer event.
    reg instruction_common;
    always @* instruction_common =
        (cfg(config_words, 3) == 32'd12) &&
        (cfg(config_words, 6) == 32'd3) &&
        (cfg(config_words, 8) == NO_ID) &&
        (cfg(config_words, 9) == 32'd4);
    reg instruction_rom;
    always @* instruction_rom =
        (cfg(config_words, 2) == 32'd15) &&
        (cfg(config_words, 4) == 32'd381) &&
        (cfg(config_words, 5) == 32'd382) &&
        (cfg(config_words, 7) == 32'd5);
    reg instruction_hbm;
    always @* instruction_hbm =
        (cfg(config_words, 2) == 32'd14) &&
        (cfg(config_words, 4) == 32'd546) &&
        (cfg(config_words, 5) == 32'd547) &&
        (cfg(config_words, 7) == 32'd4);
    wire instruction_supported =
        profile_known && instruction_common &&
        ((profile == PROFILE_ROM && instruction_rom) ||
         (profile == PROFILE_HBM && instruction_hbm));

    // OPERATOR, COUNTER_CLASS and reference identity, words 10..32.
    reg operator_common;
    always @* operator_common =
        (cfg(config_words, 10) == FAMILY_VECTOR) &&
        (cfg(config_words, 11) == SUB_MHC) &&
        (cfg(config_words, 12) == 0) &&
        (cfg(config_words, 13) == NO_ID) &&
        (cfg(config_words, 14) == 32'd4) &&
        (cfg(config_words, 24) == 0) &&
        (cfg(config_words, 25) == 32'd20) &&
        (cfg(config_words, 26) == 32'd4) &&
        (cfg(config_words, 27) == NO_ID) &&
        (cfg(config_words, 28) == 32'd5) &&
        (cfg(config_words, 29) == 32'd3) &&
        (cfg(config_words, 30) == COUNTER_0) &&
        (cfg(config_words, 31) == COUNTER_1) &&
        (cfg(config_words, 32) == COUNTER_2);
    reg operator_rom;
    always @* operator_rom =
        (cfg(config_words, 15) == 32'd380) &&
        (cfg(config_words, 16) == 32'd378) &&
        (cfg(config_words, 17) == 32'd379) &&
        (cfg(config_words, 18) == 32'd370) &&
        (cfg(config_words, 19) == 32'd371) &&
        (cfg(config_words, 20) == 32'd372) &&
        (cfg(config_words, 21) == 32'd373) &&
        (cfg(config_words, 22) == 32'd375) &&
        (cfg(config_words, 23) == 32'd377);
    reg operator_hbm;
    always @* operator_hbm =
        (cfg(config_words, 15) == 32'd536) &&
        (cfg(config_words, 16) == 32'd544) &&
        (cfg(config_words, 17) == 32'd545) &&
        (cfg(config_words, 18) == 32'd538) &&
        (cfg(config_words, 19) == 32'd539) &&
        (cfg(config_words, 20) == 32'd540) &&
        (cfg(config_words, 21) == 32'd541) &&
        (cfg(config_words, 22) == 32'd542) &&
        (cfg(config_words, 23) == 32'd543);
    wire operator_supported =
        operator_common &&
        ((profile == PROFILE_ROM && operator_rom) ||
         (profile == PROFILE_HBM && operator_hbm));

    // Complete NUMERIC payload, including the 256-bit named-contract digest.
    reg numeric_supported;
    always @* numeric_supported =
        (cfg(config_words, 33) == FMT_BF16) &&
        (cfg(config_words, 34) == FMT_FP32) &&
        (cfg(config_words, 35) == FMT_FP32) &&
        (cfg(config_words, 36) == FMT_FP32) &&
        (cfg(config_words, 37) == 0) &&
        (cfg(config_words, 38) == 1) &&
        (cfg(config_words, 39) == 0) &&
        (cfg(config_words, 40) == 0) &&
        (cfg(config_words, 41) == HC_EPSILON) &&
        (cfg(config_words, 42) == 0) &&
        (cfg(config_words, 43) == 0) &&
        (cfg(config_words, 44) == 32'he68b_2e20) &&
        (cfg(config_words, 45) == 32'h69cf_a935) &&
        (cfg(config_words, 46) == 32'hf381_3d0f) &&
        (cfg(config_words, 47) == 32'h6881_6922) &&
        (cfg(config_words, 48) == 32'hfa12_29c7) &&
        (cfg(config_words, 49) == 32'h5bbd_35f7) &&
        (cfg(config_words, 50) == 32'hfd29_fd76) &&
        (cfg(config_words, 51) == 32'h86d5_2c46);

    // Complete SCHEDULE payload, words 52..63.
    reg schedule_common;
    always @* schedule_common =
        (cfg(config_words, 52) == FAMILY_VECTOR) &&
        (cfg(config_words, 53) == 0) &&
        (cfg(config_words, 58) != 0) &&
        (cfg(config_words, 59) != 0) &&
        (cfg(config_words, 60) == 0) &&
        (cfg(config_words, 63) == 0);
    reg schedule_rom;
    always @* schedule_rom =
        (cfg(config_words, 54) == 32'd32) &&
        (cfg(config_words, 55) == 32'd128) &&
        (cfg(config_words, 56) == 32'd4096) &&
        (cfg(config_words, 57) == 32'd1024) &&
        (cfg(config_words, 58) == 32'h4000_0000) &&
        (cfg(config_words, 59) == 32'd56) &&
        (cfg(config_words, 61) == 32'd3) &&
        (cfg(config_words, 62) == 32'd32);
    reg schedule_hbm;
    always @* schedule_hbm =
        (cfg(config_words, 54) == 32'd2) &&
        (cfg(config_words, 55) == 32'd64) &&
        (cfg(config_words, 56) == 32'd8) &&
        (cfg(config_words, 57) == 32'd1) &&
        (cfg(config_words, 58) == 32'd8) &&
        (cfg(config_words, 59) == 32'd3) &&
        (cfg(config_words, 61) == 32'd128) &&
        (cfg(config_words, 62) == 32'd64);
    wire schedule_supported =
        schedule_common &&
        ((profile == PROFILE_ROM && schedule_rom) ||
         (profile == PROFILE_HBM && schedule_hbm));

    // Six view records begin at word 64.  Each record is:
    // object, permissions, dtype, rank, dim0..2, stride0..2.
    reg view_common;
    always @* view_common =
        // hidden [capacity,4,4096] BF16, contiguous token-major
        (view_cfg(config_words, 0, 1) == 1) &&
        (view_cfg(config_words, 0, 2) == FMT_BF16) &&
        (view_cfg(config_words, 0, 3) == 3) &&
        (view_cfg(config_words, 0, 5) == 4) &&
        (view_cfg(config_words, 0, 6) == 4096) &&
        (view_cfg(config_words, 0, 7) == 16384) &&
        (view_cfg(config_words, 0, 8) == 4096) &&
        (view_cfg(config_words, 0, 9) == 1) &&
        // fn [24,16384] FP32
        (view_cfg(config_words, 1, 1) == 1) &&
        (view_cfg(config_words, 1, 2) == FMT_FP32) &&
        (view_cfg(config_words, 1, 3) == 2) &&
        (view_cfg(config_words, 1, 4) == 24) &&
        (view_cfg(config_words, 1, 5) == 16384) &&
        (view_cfg(config_words, 1, 6) == 0) &&
        (view_cfg(config_words, 1, 7) == 16384) &&
        (view_cfg(config_words, 1, 8) == 1) &&
        (view_cfg(config_words, 1, 9) == 0) &&
        // base [24] FP32
        (view_cfg(config_words, 2, 1) == 1) &&
        (view_cfg(config_words, 2, 2) == FMT_FP32) &&
        (view_cfg(config_words, 2, 3) == 1) &&
        (view_cfg(config_words, 2, 4) == 24) &&
        (view_cfg(config_words, 2, 5) == 0) &&
        (view_cfg(config_words, 2, 6) == 0) &&
        (view_cfg(config_words, 2, 7) == 1) &&
        (view_cfg(config_words, 2, 8) == 0) &&
        (view_cfg(config_words, 2, 9) == 0) &&
        // scale [3] FP32
        (view_cfg(config_words, 3, 1) == 1) &&
        (view_cfg(config_words, 3, 2) == FMT_FP32) &&
        (view_cfg(config_words, 3, 3) == 1) &&
        (view_cfg(config_words, 3, 4) == 3) &&
        (view_cfg(config_words, 3, 5) == 0) &&
        (view_cfg(config_words, 3, 6) == 0) &&
        (view_cfg(config_words, 3, 7) == 1) &&
        (view_cfg(config_words, 3, 8) == 0) &&
        (view_cfg(config_words, 3, 9) == 0) &&
        // weights [capacity,2,4] FP32
        (view_cfg(config_words, 4, 1) == 3) &&
        (view_cfg(config_words, 4, 2) == FMT_FP32) &&
        (view_cfg(config_words, 4, 3) == 3) &&
        (view_cfg(config_words, 4, 4) == view_cfg(config_words, 0, 4)) &&
        (view_cfg(config_words, 4, 5) == 2) &&
        (view_cfg(config_words, 4, 6) == 4) &&
        (view_cfg(config_words, 4, 7) == 8) &&
        (view_cfg(config_words, 4, 8) == 4) &&
        (view_cfg(config_words, 4, 9) == 1) &&
        // combination [capacity,4,4] FP32, source-major
        (view_cfg(config_words, 5, 1) == 3) &&
        (view_cfg(config_words, 5, 2) == FMT_FP32) &&
        (view_cfg(config_words, 5, 3) == 3) &&
        (view_cfg(config_words, 5, 4) == view_cfg(config_words, 0, 4)) &&
        (view_cfg(config_words, 5, 5) == 4) &&
        (view_cfg(config_words, 5, 6) == 4) &&
        (view_cfg(config_words, 5, 7) == 16) &&
        (view_cfg(config_words, 5, 8) == 4) &&
        (view_cfg(config_words, 5, 9) == 1) &&
        (cfg(config_words, 1) != 0) &&
        (cfg(config_words, 1) <= view_cfg(config_words, 0, 4));
    reg view_rom;
    always @* view_rom =
        (view_cfg(config_words, 0, 4) == 32'd131072) &&
        (view_cfg(config_words, 0, 0) == 32'd359) &&
        (view_cfg(config_words, 1, 0) == 32'd9) &&
        (view_cfg(config_words, 2, 0) == 32'd12) &&
        (view_cfg(config_words, 3, 0) == 32'd10) &&
        (view_cfg(config_words, 4, 0) == 32'd374) &&
        (view_cfg(config_words, 5, 0) == 32'd376);
    reg view_hbm;
    always @* view_hbm =
        (view_cfg(config_words, 0, 4) == 32'd512) &&
        (view_cfg(config_words, 0, 0) == 32'd239) &&
        (view_cfg(config_words, 1, 0) == 32'd1) &&
        (view_cfg(config_words, 2, 0) == 32'd3) &&
        (view_cfg(config_words, 3, 0) == 32'd2) &&
        (view_cfg(config_words, 4, 0) == 32'd240) &&
        (view_cfg(config_words, 5, 0) == 32'd241);
    wire view_supported =
        view_common &&
        ((profile == PROFILE_ROM && view_rom) ||
         (profile == PROFILE_HBM && view_hbm));

    reg [1:0] state;
    reg [1:0] kind_q;
    reg [31:0] tokens_q;
    reg [31:0] tile_rows_q;
    reg [31:0] tile_cols_q;
    reg [31:0] tile_depth_q;
    reg [31:0] token_base_q;
    reg [31:0] field_base_q;
    reg [31:0] k_base_q;

    reg [31:0] fields_total;
    reg [31:0] k_total;
    reg [31:0] active_token_count;
    reg [31:0] active_field_count;
    reg [31:0] active_k_count;
    reg [63:0] logical_work;
    reg [63:0] output_base;
    reg [31:0] output_stride;
    reg last_comb;

    always @* begin
        fields_total = (kind_q == TILE_PROJECTION) ? 32'd24 :
                       (kind_q == TILE_WEIGHTS) ? 32'd8 : 32'd16;
        k_total = (kind_q == TILE_PROJECTION) ? 32'd16384 : 32'd1;

        if (tokens_q - token_base_q > tile_rows_q)
            active_token_count = tile_rows_q;
        else
            active_token_count = tokens_q - token_base_q;
        if (fields_total - field_base_q > tile_cols_q)
            active_field_count = tile_cols_q;
        else
            active_field_count = fields_total - field_base_q;
        if (k_total - k_base_q > tile_depth_q)
            active_k_count = tile_depth_q;
        else
            active_k_count = k_total - k_base_q;

        logical_work = (kind_q == TILE_PROJECTION) ?
            {32'd0, active_token_count} *
            {32'd0, active_field_count} *
            {32'd0, active_k_count} : 64'd0;
        output_stride = (kind_q == TILE_WEIGHTS) ? 32'd8 :
                        (kind_q == TILE_COMBINATION) ? 32'd16 : 32'd0;
        output_base = (kind_q == TILE_PROJECTION) ? 64'd0 :
            ({32'd0, token_base_q} * {32'd0, output_stride}) +
            {32'd0, field_base_q};
        last_comb =
            (kind_q == TILE_COMBINATION) &&
            (token_base_q + active_token_count == tokens_q) &&
            (field_base_q + active_field_count == fields_total);
    end

    assign tile_valid = state == S_EMIT;
    assign tile_kind = kind_q;
    assign tile_token_base = token_base_q;
    assign tile_field_base = field_base_q;
    assign tile_k_base = k_base_q;
    assign tile_active_tokens = active_token_count;
    assign tile_active_fields = active_field_count;
    assign tile_active_k = active_k_count;
    assign tile_logical_work = logical_work;
    assign tile_output_base = output_base;
    assign tile_output_row_stride = output_stride;
    assign tile_last = last_comb;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            kind_q <= TILE_PROJECTION;
            tokens_q <= 0;
            tile_rows_q <= 0;
            tile_cols_q <= 0;
            tile_depth_q <= 0;
            token_base_q <= 0;
            field_base_q <= 0;
            k_base_q <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            projection_tile_count <= 0;
            commit_tile_count <= 0;
            logical_fma_count <= 0;
            logical_output_count <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b0;
                        error_code <= ERR_NONE;
                        projection_tile_count <= 0;
                        commit_tile_count <= 0;
                        logical_fma_count <= 0;
                        logical_output_count <= 0;
                        kind_q <= TILE_PROJECTION;
                        token_base_q <= 0;
                        field_base_q <= 0;
                        k_base_q <= 0;
                        if (!instruction_supported) begin
                            error_code <= ERR_INSTRUCTION;
                            done <= 1'b1;
                        end else if (!operator_supported) begin
                            error_code <= ERR_OPERATOR;
                            done <= 1'b1;
                        end else if (!numeric_supported) begin
                            error_code <= ERR_NUMERIC;
                            done <= 1'b1;
                        end else if (!view_supported) begin
                            error_code <= ERR_VIEW;
                            done <= 1'b1;
                        end else if (!schedule_supported) begin
                            error_code <= ERR_SCHEDULE;
                            done <= 1'b1;
                        end else begin
                            tokens_q <= active_tokens;
                            tile_rows_q <= cfg(config_words, 55);
                            tile_cols_q <= cfg(config_words, 56);
                            tile_depth_q <= cfg(config_words, 57);
                            busy <= 1'b1;
                            state <= S_EMIT;
                        end
                    end
                end

                S_EMIT: begin
                    if (tile_valid && tile_ready) begin
                        if (kind_q == TILE_PROJECTION) begin
                            projection_tile_count <= projection_tile_count + 1;
                            logical_fma_count <= logical_fma_count + logical_work;
                        end else begin
                            commit_tile_count <= commit_tile_count + 1;
                            logical_output_count <= logical_output_count +
                                ({32'd0, active_token_count} *
                                 {32'd0, active_field_count});
                        end

                        if (k_base_q + active_k_count < k_total) begin
                            k_base_q <= k_base_q + active_k_count;
                        end else if (field_base_q + active_field_count <
                                     fields_total) begin
                            k_base_q <= 0;
                            field_base_q <= field_base_q + active_field_count;
                        end else if (token_base_q + active_token_count < tokens_q) begin
                            k_base_q <= 0;
                            field_base_q <= 0;
                            token_base_q <= token_base_q + active_token_count;
                        end else if (kind_q == TILE_PROJECTION) begin
                            kind_q <= TILE_WEIGHTS;
                            k_base_q <= 0;
                            field_base_q <= 0;
                            token_base_q <= 0;
                        end else if (kind_q == TILE_WEIGHTS) begin
                            kind_q <= TILE_COMBINATION;
                            k_base_q <= 0;
                            field_base_q <= 0;
                            token_base_q <= 0;
                        end else begin
                            busy <= 1'b0;
                            done <= 1'b1;
                            state <= S_IDLE;
                        end
                    end
                end

                default: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    error_code <= ERR_INSTRUCTION;
                    state <= S_IDLE;
                end
            endcase
        end
    end
endmodule
