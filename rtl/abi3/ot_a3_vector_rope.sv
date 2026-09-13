`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 bank-port adapter for the qualified Qwen BF16 RoPE datapath.
//
// The released ABI presents query and key rotation as two independent
// VECTOR.ROPE operations, while ot_ta_rope_bf16_sram_engine implements the
// earlier qualified fused 32-query-head plus 8-key-head command.  This adapter
// executes one declared ABI operand at a time through that unchanged datapath.
// The inactive side receives internal positive-zero data and its writes are
// discarded; no undeclared external operand is read or destination written.
//
// ABI 3.0 coefficient rows are FP32.  They are narrowed to BF16 RNE at the
// adapter boundary, exactly as qwen3_rope_fp32_bf16_v1 requires, before the
// qualified core performs its two BF16-rounded products and BF16-rounded sum.
// One BF16 code occupies the low half of each 32-bit verification-bank word.
//
// MULTI-POSITION LAUNCHES (prefill).  A decode launch rotates ONE position; the
// golden device reports the same 83 launches for prefill, each covering a span
// of 16 positions.  The qualified core cannot retire that: its coefficient row
// is loaded once per command and on the last coefficient index falls through to
// the input stage, so nothing in it iterates positions.  So a span of two or
// more is retired by ot_a3_rope_lane_pipe instead -- six registered stages, one
// element per cycle, the same six ot_fp32_rne_pkg calls in the same order -- and
// a span of exactly one still goes to the unchanged qualified core, which is
// what makes every decode launch bit-identical rather than argued.
//
// WHERE THE SPAN COMES FROM, and it is not a new port.  cfg_count is the
// launch's resolved result count.  For a span-S launch the bridge derives it as
// S * cfg_rows * cfg_cols, because that is what the resolved view extent means,
// so cfg_count already carries S and no descriptor field is invented.  The span
// is recovered by repeated subtraction of one position block -- S cycles, once
// per launch, off the datapath -- rather than by a divider.  When cfg_count is
// exactly one block the check is the identity this engine has always applied
// and the legacy path is entered on the same cycle as before.
//
// WHAT THE BRIDGE MUST PASS for a span-S VECTOR.ROPE launch.  Three things, all
// of them already implied by the RoPE view predicates it enforces today:
//
//   1. cfg_count = S * cfg_rows * cfg_cols.  Today the bridge's rope leg of
//      expected_result_count and expected_work_count is source_rows *
//      source_trailing with no extent factor; both need the resolved extent.
//   2. captured_extent[0] for the RoPE input view must be allowed to be that
//      extent.  rope_input_source_ok pins it to the literal 1, and that single
//      comparison is the bridge-side refusal of prefill.  The coefficient and
//      output views already tie their extents to it.
//   3. Nothing else.  The three operand regions are contiguous position-major
//      sweeps -- input and output stride S blocks of cfg_rows*cfg_cols words, the
//      coefficient table S rows of 2*cfg_cols FP32 words -- which is exactly
//      what rope_input_source_ok, rope_coefficient_source_ok and rope_output_ok
//      already require of stride0.  No base, no stride and no rank changes.
//
// WHY THE SPAN IS NOT IN THE CORE COMMAND RECORD.  The record is ABI 2.2,
// private to this adapter, and its reflected CRC32 over the first fifteen words
// is retained evidence for the qualified fused single-position profile
// (results/tensor_accelerator/qwen3_rtl_rope_campaign.json pins the core's
// source digest).  A span belongs outside it for three reasons.  It is per
// launch, and the record is an elaboration constant, so a span in the record
// would freeze the span exactly as size0/size1/size2 froze the geometry.  The
// qualified datapath cannot execute S > 1 whatever the record says, so the
// field would describe a command the decoder admits and the engine cannot run.
// And the span already reaches this engine as the resolved view extent, which is
// launch state, not profile state.  The retarget function below therefore still
// rewrites exactly three words and recomputes the CRC, and the record for a
// prefill launch is the record for a decode launch.
// ---------------------------------------------------------------------------
module ot_a3_vector_rope #(
    //: MODEL GEOMETRY.  These three were localparams frozen to Qwen3-8B, and
    //: through them so was every expected count in the completion check below
    //: and the 512-bit core command literal.  A RoPE rotation is the same
    //: arithmetic at any head width; nothing in the datapath required 128.
    //: Defaults reproduce the shipped values bit-for-bit, including the
    //: command record's CRC.
    parameter [31:0] QUERY_HEADS = 32'd32,
    parameter [31:0] KEY_HEADS   = 32'd8,
    parameter [31:0] HEAD_WIDTH  = 32'd128,
    //: POSITIONS PER LAUNCH, a bound and not geometry.  It sizes the span
    //: counters in this wrapper and in the lane and nothing else -- no array is
    //: sized by it, because the lane streams positions -- so the cost of the
    //: default is $clog2 flip-flops rather than storage, and it is large enough
    //: that a prefill chunk is never refused for being long.
    parameter [31:0] MAX_POSITION_SPAN = 32'd65536,
    //: Route a span-1 launch through the pipelined lane too.  Default 0 keeps
    //: every decode launch on the unchanged qualified core; setting it to 1 is
    //: how rtl/test/tb_a3_rope_span.sv proves the two agree word for word.
    parameter integer LANE_AT_SPAN1 = 0,
    //: Forwarded to the lane, which documents each trade at its own
    //: declaration.  They are here so a deployment can spend storage on the
    //: last per-position bubble instead of inheriting a default.
    parameter integer ROW_BUFFERS = 4,
    parameter integer COEF_BUFFERS = 2,
    parameter integer OUT_BUFFERS = 2
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] cfg_count,
    input  wire [31:0] cfg_rows,
    input  wire [31:0] cfg_cols,
    input  wire [31:0] cfg_input_base,
    input  wire [31:0] cfg_coefficient_base,
    input  wire [31:0] cfg_output_base,

    output wire        input_rd_en,
    output wire [31:0] input_rd_addr,
    input  wire [31:0] input_rd_data,
    output wire        coefficient_rd_en,
    output wire [31:0] coefficient_rd_addr,
    input  wire [31:0] coefficient_rd_data,
    output wire        out_we,
    output wire [31:0] out_addr,
    output wire [31:0] out_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg  [31:0] result_count,
    output reg  [31:0] saturation_count,
    output reg  [31:0] work_count
);
    //: Set +OT_ROPE_TRACE=1 to report which shape check rejected.
    reg trace_rope = 1'b0;
    initial if ($test$plusargs("OT_ROPE_TRACE")) trace_rope = 1'b1;

    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE =
        ot_a3_engine_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE =
        ot_a3_engine_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    //: One cosine and one sine per column.
    localparam [31:0] COEFFICIENT_COUNT = 32'd2 * HEAD_WIDTH;
    //: Every rotated element, queries and keys together.
    localparam [31:0] QUERY_ELEMENTS = QUERY_HEADS * HEAD_WIDTH;
    localparam [31:0] KEY_ELEMENTS = KEY_HEADS * HEAD_WIDTH;
    localparam [31:0] TOTAL_ELEMENTS = QUERY_ELEMENTS + KEY_ELEMENTS;

    // The internal byte-address spaces are deliberately disjoint.  They are
    // decoded here and never escape onto an ABI-visible memory port.
    localparam [63:0] CORE_QUERY_BASE = 64'h0000_0000_0001_0000;
    localparam [63:0] CORE_KEY_BASE = 64'h0000_0000_0002_0000;
    localparam [63:0] CORE_QUERY_OUTPUT_BASE = 64'h0000_0000_0003_0000;
    localparam [63:0] CORE_KEY_OUTPUT_BASE = 64'h0000_0000_0004_0000;
    localparam [63:0] CORE_COEFFICIENT_BASE = 64'h0000_0000_0005_0000;
    //: Two bytes per BF16 element.
    localparam [63:0] CORE_QUERY_BYTES = 64'd2 * {32'd0, QUERY_ELEMENTS};
    localparam [63:0] CORE_KEY_BYTES = 64'd2 * {32'd0, KEY_ELEMENTS};
    localparam [63:0] CORE_COEFFICIENT_BYTES = 64'd2 * {32'd0, COEFFICIENT_COUNT};

    // ABI 2.2 is private to this adapter.  The record contains ROPE_BF16,
    // vector engine 3, index/kernel 0, the five internal bases above,
    // 32/8/128 geometry, and reflected IEEE CRC32 0xdb8405f0.
    localparam [511:0] CORE_COMMAND_SHIPPED =
        512'hdb8405f0000500000000008000000008000000200000000000040000000000000003000000000000000200000000000000010000000000000000000000000321;

    //: The record above carries its own geometry in size0/size1/size2 and a
    //: reflected IEEE CRC32 over its first fifteen words.  Retargeting it to a
    //: different head count therefore means rewriting three words and
    //: RECOMPUTING that CRC -- which is why the literal had frozen the model.
    //: Doing both at elaboration keeps the shipped record as the witness: at
    //: the default parameters the three words are already 32/8/128, so the
    //: recomputed CRC is the literal's own and CORE_COMMAND is bit-identical.
    function automatic [31:0] crc32_ieee_word;
        input [31:0] crc_in;
        input [31:0] payload_word;
        integer bit_index;
        reg [31:0] crc;
        reg        feedback;
        begin
            crc = crc_in;
            for (bit_index = 0; bit_index < 32; bit_index = bit_index + 1) begin
                feedback = crc[0] ^ payload_word[bit_index];
                crc = crc >> 1;
                if (feedback) crc = crc ^ 32'hedb8_8320;
            end
            crc32_ieee_word = crc;
        end
    endfunction

    function automatic [511:0] retarget_command;
        input [511:0] base;
        input [31:0]  query_heads;
        input [31:0]  key_heads;
        input [31:0]  head_width;
        reg [511:0] record;
        reg [31:0]  crc;
        integer     word_index;
        begin
            record = base;
            record[383:352] = query_heads;   // size0
            record[415:384] = key_heads;     // size1
            record[447:416] = head_width;    // size2
            crc = 32'hffff_ffff;
            for (word_index = 0; word_index < 15; word_index = word_index + 1)
                crc = crc32_ieee_word(crc, record[word_index * 32 +: 32]);
            record[511:480] = ~crc;
            retarget_command = record;
        end
    endfunction

    localparam [511:0] CORE_COMMAND =
        retarget_command(CORE_COMMAND_SHIPPED, QUERY_HEADS, KEY_HEADS, HEAD_WIDTH);

    localparam [2:0] S_IDLE = 3'd0;
    localparam [2:0] S_DISPATCH = 3'd1;
    localparam [2:0] S_RUN = 3'd2;
    localparam [2:0] S_DONE = 3'd3;
    //: Span recovery and the pipelined-lane launch.  A span-1 launch never
    //: enters either, so its cycle count is the shipped one.
    localparam [2:0] S_SPAN = 3'd4;
    localparam [2:0] S_LANE_START = 3'd5;
    localparam [2:0] S_LANE_RUN = 3'd6;
    localparam [1:0] READ_DUMMY = 2'd0;
    localparam [1:0] READ_INPUT = 2'd1;
    localparam [1:0] READ_COEFFICIENT = 2'd2;
    localparam [1:0] READ_INVALID = 2'd3;

    reg [2:0] state;
    reg active_query;
    reg [31:0] input_base_q;
    reg [31:0] coefficient_base_q;
    reg [31:0] output_base_q;
    reg [31:0] count_q;
    reg [31:0] rows_q;
    reg [31:0] cols_q;
    reg [31:0] block_q;
    reg [31:0] span_q;
    reg [31:0] span_remaining;
    reg        lane_mode;
    reg        lane_start;
    reg read_pending;
    reg [1:0] read_kind;
    reg address_fault;
    reg [31:0] selected_write_count;

    wire core_cmd_valid = state == S_DISPATCH;
    wire core_cmd_ready;
    wire core_read_valid;
    wire core_read_ready;
    wire [63:0] core_read_address;
    wire core_response_valid;
    wire core_response_ready;
    wire [15:0] core_response_data;
    wire core_write_valid;
    wire core_write_ready;
    wire [63:0] core_write_address;
    wire [15:0] core_write_data;
    wire [1:0] core_write_byte_enable;
    wire core_done_valid;
    wire core_done_ready = state == S_RUN;
    wire [7:0] core_done_error;
    wire [31:0] core_done_command_index;
    wire [31:0] core_done_coefficient_reads;
    wire [31:0] core_done_query_reads;
    wire [31:0] core_done_key_reads;
    wire [31:0] core_done_writes;
    wire [31:0] core_done_elements;
    wire [31:0] core_done_multiplications;
    wire [31:0] core_done_additions;
    wire [31:0] core_done_multiplication_saturations;
    wire [31:0] core_done_addition_saturations;

    wire read_is_query =
        (core_read_address >= CORE_QUERY_BASE) &&
        (core_read_address < CORE_QUERY_BASE + CORE_QUERY_BYTES);
    wire read_is_key =
        (core_read_address >= CORE_KEY_BASE) &&
        (core_read_address < CORE_KEY_BASE + CORE_KEY_BYTES);
    wire read_is_coefficient =
        (core_read_address >= CORE_COEFFICIENT_BASE) &&
        (core_read_address <
         CORE_COEFFICIENT_BASE + CORE_COEFFICIENT_BYTES);
    wire read_is_selected_input =
        (active_query && read_is_query) || (!active_query && read_is_key);
    wire read_is_dummy_input =
        (active_query && read_is_key) || (!active_query && read_is_query);
    wire [63:0] selected_input_offset = active_query
        ? core_read_address - CORE_QUERY_BASE
        : core_read_address - CORE_KEY_BASE;
    wire [63:0] coefficient_offset =
        core_read_address - CORE_COEFFICIENT_BASE;

    assign core_read_ready = (state == S_RUN) && !read_pending;
    wire        adapter_input_rd_en = core_read_valid && core_read_ready &&
                                      read_is_selected_input;
    wire [31:0] adapter_input_rd_addr =
        input_base_q + selected_input_offset[32:1];
    wire        adapter_coefficient_rd_en = core_read_valid && core_read_ready &&
                                            read_is_coefficient;
    wire [31:0] adapter_coefficient_rd_addr =
        coefficient_base_q + coefficient_offset[32:1];

    wire [18:0] narrowed_coefficient =
        ot_fp32_rne_pkg::fp32_to_bf16_rne(coefficient_rd_data);
    wire coefficient_conversion_error =
        narrowed_coefficient[18:17] != 2'd0;
    assign core_response_valid = read_pending;
    assign core_response_data = read_kind == READ_INPUT
        ? input_rd_data[15:0]
        : read_kind == READ_COEFFICIENT
        ? (coefficient_conversion_error
           ? 16'h7f80 : narrowed_coefficient[15:0])
        : read_kind == READ_DUMMY ? 16'd0 : 16'h7f80;

    wire write_is_query =
        (core_write_address >= CORE_QUERY_OUTPUT_BASE) &&
        (core_write_address < CORE_QUERY_OUTPUT_BASE + CORE_QUERY_BYTES);
    wire write_is_key =
        (core_write_address >= CORE_KEY_OUTPUT_BASE) &&
        (core_write_address < CORE_KEY_OUTPUT_BASE + CORE_KEY_BYTES);
    wire write_is_selected =
        (active_query && write_is_query) || (!active_query && write_is_key);
    wire write_is_dummy =
        (active_query && write_is_key) || (!active_query && write_is_query);
    wire [63:0] selected_output_offset = active_query
        ? core_write_address - CORE_QUERY_OUTPUT_BASE
        : core_write_address - CORE_KEY_OUTPUT_BASE;
    assign core_write_ready = state == S_RUN;
    wire        adapter_out_we =
        core_write_valid && core_write_ready && write_is_selected;
    wire [31:0] adapter_out_addr =
        output_base_q + selected_output_offset[32:1];
    wire [31:0] adapter_out_data = {16'd0, core_write_data};

    // ---- the pipelined multi-position lane ---------------------------------
    //: A VECTOR.ROPE launch declares ONE operand, so the lane only ever needs
    //: the larger of the two head counts.  Derived, so it cannot disagree with
    //: the geometry the shape check admits.
    localparam [31:0] LANE_MAX_HEADS =
        (QUERY_HEADS > KEY_HEADS) ? QUERY_HEADS : KEY_HEADS;

    wire        lane_input_rd_en;
    wire [31:0] lane_input_rd_addr;
    wire        lane_coefficient_rd_en;
    wire [31:0] lane_coefficient_rd_addr;
    wire        lane_out_we;
    wire [31:0] lane_out_addr;
    wire [31:0] lane_out_data;
    wire        lane_busy;
    wire        lane_done;
    wire [7:0]  lane_error_code;
    wire [31:0] lane_result_count;
    wire [31:0] lane_saturation_count;
    wire [31:0] lane_work_count;

    ot_a3_rope_lane_pipe #(
        .MAX_HEADS(LANE_MAX_HEADS),
        .MAX_HEAD_WIDTH(HEAD_WIDTH),
        .MAX_POSITION_SPAN(MAX_POSITION_SPAN),
        .ROW_BUFFERS(ROW_BUFFERS),
        .COEF_BUFFERS(COEF_BUFFERS),
        .OUT_BUFFERS(OUT_BUFFERS)
    ) span_lane (
        .clk(clk),
        .rst_n(rst_n),
        .start(lane_start),
        .cfg_heads(rows_q),
        .cfg_cols(cols_q),
        .cfg_span(span_q),
        .cfg_input_base(input_base_q),
        .cfg_coefficient_base(coefficient_base_q),
        .cfg_output_base(output_base_q),
        .input_rd_en(lane_input_rd_en),
        .input_rd_addr(lane_input_rd_addr),
        .input_rd_data(input_rd_data),
        .coefficient_rd_en(lane_coefficient_rd_en),
        .coefficient_rd_addr(lane_coefficient_rd_addr),
        .coefficient_rd_data(coefficient_rd_data),
        .out_we(lane_out_we),
        .out_addr(lane_out_addr),
        .out_data(lane_out_data),
        .busy(lane_busy),
        .done(lane_done),
        .error_code(lane_error_code),
        .result_count(lane_result_count),
        .saturation_count(lane_saturation_count),
        .work_count(lane_work_count)
    );

    //: The two paths never drive the banks at once: the core is dispatched only
    //: from S_DISPATCH and the lane started only from S_LANE_START, and
    //: lane_mode is latched before either runs.
    assign input_rd_en = lane_mode ? lane_input_rd_en : adapter_input_rd_en;
    assign input_rd_addr = lane_mode ? lane_input_rd_addr
                                     : adapter_input_rd_addr;
    assign coefficient_rd_en = lane_mode ? lane_coefficient_rd_en
                                         : adapter_coefficient_rd_en;
    assign coefficient_rd_addr = lane_mode ? lane_coefficient_rd_addr
                                           : adapter_coefficient_rd_addr;
    assign out_we = lane_mode ? lane_out_we : adapter_out_we;
    assign out_addr = lane_mode ? lane_out_addr : adapter_out_addr;
    assign out_data = lane_mode ? lane_out_data : adapter_out_data;

    ot_ta_rope_bf16_sram_engine #(
        .PROFILE_COMMAND_INDEX(32'd0),
        .PROFILE_KERNEL_INDEX(32'd0),
        //: The core was already parameterised; only this wrapper was not, so
        //: the geometry stopped here and the core never heard about it.
        .PROFILE_QUERY_HEADS(QUERY_HEADS),
        .PROFILE_KEY_HEADS(KEY_HEADS),
        .PROFILE_HEAD_WIDTH(HEAD_WIDTH)
    ) qualified_rope (
        .clk(clk),
        .rst_n(rst_n),
        .cmd_valid(core_cmd_valid),
        .cmd_ready(core_cmd_ready),
        .abi_major(16'd2),
        .abi_minor(16'd2),
        .expected_command_index(32'd0),
        .command_record(CORE_COMMAND),
        .sram_read_valid(core_read_valid),
        .sram_read_ready(core_read_ready),
        .sram_read_address(core_read_address),
        .sram_response_valid(core_response_valid),
        .sram_response_ready(core_response_ready),
        .sram_response_data(core_response_data),
        .sram_write_valid(core_write_valid),
        .sram_write_ready(core_write_ready),
        .sram_write_address(core_write_address),
        .sram_write_data(core_write_data),
        .sram_write_byte_enable(core_write_byte_enable),
        .done_valid(core_done_valid),
        .done_ready(core_done_ready),
        .done_error(core_done_error),
        .done_command_index(core_done_command_index),
        .done_coefficient_read_count(core_done_coefficient_reads),
        .done_query_read_count(core_done_query_reads),
        .done_key_read_count(core_done_key_reads),
        .done_output_write_count(core_done_writes),
        .done_element_count(core_done_elements),
        .done_multiplication_count(core_done_multiplications),
        .done_addition_count(core_done_additions),
        .done_multiplication_saturation_count(
            core_done_multiplication_saturations
        ),
        .done_addition_saturation_count(core_done_addition_saturations)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            active_query <= 1'b0;
            input_base_q <= 0;
            coefficient_base_q <= 0;
            output_base_q <= 0;
            count_q <= 0;
            rows_q <= 0;
            cols_q <= 0;
            block_q <= 0;
            span_q <= 0;
            span_remaining <= 0;
            lane_mode <= 1'b0;
            lane_start <= 1'b0;
            read_pending <= 1'b0;
            read_kind <= READ_DUMMY;
            address_fault <= 1'b0;
            selected_write_count <= 0;
            busy <= 1'b0;
            done <= 1'b0;
            error_code <= ERR_NONE;
            result_count <= 0;
            saturation_count <= 0;
            work_count <= 0;
        end else begin
            done <= 1'b0;

            if (core_read_valid && core_read_ready) begin
                read_pending <= 1'b1;
                if (read_is_selected_input)
                    read_kind <= READ_INPUT;
                else if (read_is_coefficient)
                    read_kind <= READ_COEFFICIENT;
                else if (read_is_dummy_input)
                    read_kind <= READ_DUMMY;
                else begin
                    read_kind <= READ_INVALID;
                    address_fault <= 1'b1;
                end
            end else if (core_response_valid && core_response_ready) begin
                read_pending <= 1'b0;
                if ((read_kind == READ_COEFFICIENT) &&
                    narrowed_coefficient[16])
                    saturation_count <= saturation_count + 1'b1;
            end

            if (core_write_valid && core_write_ready) begin
                if (write_is_selected)
                    selected_write_count <= selected_write_count + 1'b1;
                else if (!write_is_dummy)
                    address_fault <= 1'b1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        busy <= 1'b1;
                        error_code <= ERR_NONE;
                        result_count <= 0;
                        saturation_count <= 0;
                        work_count <= 0;
                        read_pending <= 1'b0;
                        read_kind <= READ_DUMMY;
                        address_fault <= 1'b0;
                        selected_write_count <= 0;
                        input_base_q <= cfg_input_base;
                        coefficient_base_q <= cfg_coefficient_base;
                        output_base_q <= cfg_output_base;
                        count_q <= cfg_count;
                        rows_q <= cfg_rows;
                        cols_q <= cfg_cols;
                        block_q <= cfg_rows * cfg_cols;
                        span_q <= 32'd0;
                        span_remaining <= cfg_count;
                        lane_mode <= 1'b0;
                        active_query <= cfg_rows == QUERY_HEADS;
                        if ((cfg_cols != HEAD_WIDTH) ||
                            !((cfg_rows == QUERY_HEADS) ||
                              (cfg_rows == KEY_HEADS)) ||
                            //: Below one position block there is no span to
                            //: recover, so refuse here rather than in the scan.
                            //: One comparator, and it keeps the refusal on the
                            //: cycle this engine has always refused on.
                            (cfg_count < cfg_rows * cfg_cols)) begin
                            if (trace_rope)
                                $display("OT_ROPE_CFG_SHAPE rows=%0d cols=%0d count=%0d (want cols=%0d rows in {%0d,%0d} count=span*rows*cols)",
                                         cfg_rows, cfg_cols, cfg_count,
                                         HEAD_WIDTH, QUERY_HEADS, KEY_HEADS);
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        //: ONE POSITION.  Byte for byte the check this engine
                        //: has always applied, entered on the same cycle, so a
                        //: decode launch still runs on the qualified core with
                        //: the cycle count it has always had.
                        end else if (cfg_count == cfg_rows * cfg_cols) begin
                            span_q <= 32'd1;
                            lane_mode <= (LANE_AT_SPAN1 != 0);
                            state <= (LANE_AT_SPAN1 != 0) ? S_LANE_START
                                                          : S_DISPATCH;
                        //: MORE THAN ONE.  Recover the span by subtracting one
                        //: position block at a time: S cycles once per launch,
                        //: which buys a divider's answer without a divider and
                        //: without the count check becoming a remainder test the
                        //: engine could not perform.
                        end else begin
                            state <= S_SPAN;
                        end
                    end
                end

                S_DISPATCH: begin
                    if (core_cmd_valid && core_cmd_ready)
                        state <= S_RUN;
                end

                S_RUN: begin
                    if (core_done_valid) begin
                        if (core_done_error == 8'd9)
                            error_code <= ERR_OPERAND_NONFINITE;
                        else if (core_done_error == 8'd10)
                            error_code <= ERR_ACCUMULATE_RANGE;
                        else if ((core_done_error != 0) || address_fault ||
                                 (core_done_command_index != 0) ||
                                 (core_done_coefficient_reads !=
                                  COEFFICIENT_COUNT) ||
                                 //: Each of these was a Qwen3-8B constant:
                                 //: 4096 = 32x128, 1024 = 8x128, 5120 their
                                 //: sum, 10240 two multiplies per element.
                                 //: They are the same identities at any
                                 //: geometry, so state them that way.
                                 (core_done_query_reads != QUERY_ELEMENTS) ||
                                 (core_done_key_reads != KEY_ELEMENTS) ||
                                 (core_done_writes != TOTAL_ELEMENTS) ||
                                 (core_done_elements != TOTAL_ELEMENTS) ||
                                 (core_done_multiplications !=
                                  (32'd2 * TOTAL_ELEMENTS)) ||
                                 (core_done_additions != TOTAL_ELEMENTS) ||
                                 (selected_write_count != count_q))
                        begin
                            if (trace_rope)
                                $display("OT_ROPE_DONE_SHAPE err=%0d fault=%0b cmdidx=%0d coef=%0d/%0d q=%0d/%0d k=%0d/%0d w=%0d/%0d el=%0d/%0d mul=%0d/%0d add=%0d/%0d sel=%0d/%0d",
                                         core_done_error, address_fault,
                                         core_done_command_index,
                                         core_done_coefficient_reads, COEFFICIENT_COUNT,
                                         core_done_query_reads, QUERY_ELEMENTS,
                                         core_done_key_reads, KEY_ELEMENTS,
                                         core_done_writes, TOTAL_ELEMENTS,
                                         core_done_elements, TOTAL_ELEMENTS,
                                         core_done_multiplications, 32'd2 * TOTAL_ELEMENTS,
                                         core_done_additions, TOTAL_ELEMENTS,
                                         selected_write_count, count_q);
                            error_code <= ERR_SHAPE;
                        end
                        else begin
                            error_code <= ERR_NONE;
                            result_count <= count_q;
                            work_count <= count_q;
                        end
                        state <= S_DONE;
                    end
                end

                S_SPAN: begin
                    if (span_remaining >= block_q) begin
                        if (span_q == MAX_POSITION_SPAN) begin
                            if (trace_rope)
                                $display("OT_ROPE_SPAN_BOUND count=%0d block=%0d bound=%0d",
                                         count_q, block_q, MAX_POSITION_SPAN);
                            error_code <= ERR_SHAPE;
                            state <= S_DONE;
                        end else begin
                            span_remaining <= span_remaining - block_q;
                            span_q <= span_q + 32'd1;
                        end
                    //: A count that is not a whole number of position blocks is
                    //: refused BEFORE anything is read or written, which is the
                    //: fail-closed point the single-position check had.
                    end else if (span_remaining != 32'd0) begin
                        if (trace_rope)
                            $display("OT_ROPE_SPAN_SHAPE count=%0d block=%0d remainder=%0d",
                                     count_q, block_q, span_remaining);
                        error_code <= ERR_SHAPE;
                        state <= S_DONE;
                    end else begin
                        lane_mode <= 1'b1;
                        state <= S_LANE_START;
                    end
                end

                S_LANE_START: begin
                    lane_start <= 1'b1;
                    state <= S_LANE_RUN;
                end

                S_LANE_RUN: begin
                    lane_start <= 1'b0;
                    if (lane_done) begin
                        saturation_count <= lane_saturation_count;
                        //: The written-word count is checked against the
                        //: declared count, as the legacy path checks
                        //: selected_write_count: a lane that retired the wrong
                        //: number of positions fails closed rather than
                        //: reporting success over a short destination.
                        if ((lane_error_code != ERR_NONE) ||
                            (lane_result_count != count_q)) begin
                            if (trace_rope)
                                $display("OT_ROPE_LANE_DONE err=%0d wrote=%0d/%0d span=%0d rows=%0d cols=%0d",
                                         lane_error_code, lane_result_count,
                                         count_q, span_q, rows_q, cols_q);
                            error_code <= (lane_error_code != ERR_NONE)
                                ? lane_error_code : ERR_SHAPE;
                        end else begin
                            error_code <= ERR_NONE;
                            result_count <= count_q;
                            work_count <= count_q;
                        end
                        state <= S_DONE;
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: begin
                    error_code <= ERR_SHAPE;
                    state <= S_DONE;
                end
            endcase
        end
    end

    wire _unused_core = &{1'b0, core_write_byte_enable,
        core_done_multiplication_saturations,
        core_done_addition_saturations,
        lane_busy, lane_work_count};
endmodule
