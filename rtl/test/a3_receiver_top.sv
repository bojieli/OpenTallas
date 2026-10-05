`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for OR64, the operand receiver
// (rtl/abi3/ot_a3_operand_receiver.sv; results/rtl/abi3_operand_receiver.json).
//
// Both checkers -- rtl/test/tb_a3_receiver.sv on Icarus and
// rtl/test/a3_receiver_harness.cpp on Verilator -- instantiate this module and
// read the same generated images.  The stimulus is inside the top and is a
// deterministic function of the case table, so the two simulators must report
// the same cycles as well as the same values.
//
// It holds the receiver, a root driver that presents one binary32 root per
// cycle (or with a gap the case names) with the tag the collector would have
// given it, and an activation array with the same shape and the same write
// semantics as ot_a3_tile64's activation FIFO -- act_wr_en / act_wr_addr /
// act_wr_data, one 64-bit word, written on the clock edge.  It also stamps,
// per slice, the cycles from the slice's LAST root to the cycle
// act_ready_kblocks names that slice, which is the operand-readiness term of
// section 3.6 measured on the block that owns it.
//
// Images (tools/build_abi3_receiver_vectors.py):
//   or_root.hex    binary32 roots, in the order the endpoint retires them
//   or_case.hex    one 24-word record per case
//   or_expect.hex  per case, the final contents of the activation window
//   or_meta.hex    case count and the campaign totals
// ---------------------------------------------------------------------------
module ot_a3_receiver_top #(
    parameter integer ACT_WORDS       = 2048,
    parameter integer ACT_SCALE_WORDS = 64,
    parameter integer ROOT_WORDS      = 8192,
    parameter integer CASE_WORDS      = 2048,
    parameter integer EXPECT_WORDS    = 8192,
    parameter integer META_WORDS      = 8,
    parameter integer TRACE_SLICES    = 16,
    parameter integer CASE_STRIDE     = 24
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        run,
    input  wire [31:0] run_case,
    output reg         busy,
    output reg         done,

    output reg  [31:0] obs_timeout,
    output reg  [31:0] obs_done_pulses,
    output wire [7:0]  obs_error_code,
    output wire [7:0]  obs_error_detail,
    output wire [15:0] obs_error_tag,
    output wire [31:0] obs_roots_count,
    output wire [31:0] obs_words_written,
    output wire [15:0] obs_slices_ready,
    output wire [31:0] obs_saturation_count,
    output wire [15:0] obs_act_ready_kblocks,
    output wire        obs_busy,
    output reg  [31:0] obs_scale_writes,

    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] root_rd_addr,
    output wire [31:0] root_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] act_rd_addr,          // 2 words per 64-bit activation word
    output wire [31:0] act_rd_data,
    input  wire [31:0] trace_rd_addr,
    output wire [31:0] trace_rd_data,
    output wire [31:0] act_words_param
);
    reg [31:0] case_mem   [0:CASE_WORDS-1];
    reg [31:0] root_mem   [0:ROOT_WORDS-1];
    reg [31:0] expect_mem [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem   [0:META_WORDS-1];
    reg [63:0] act_mem    [0:ACT_WORDS-1];
    reg [31:0] trace_mem  [0:TRACE_SLICES-1];

    integer init_i;
    initial begin
        $readmemh("or_case.hex", case_mem);
        $readmemh("or_root.hex", root_mem);
        $readmemh("or_expect.hex", expect_mem);
        $readmemh("or_meta.hex", meta_mem);
        for (init_i = 0; init_i < ACT_WORDS; init_i = init_i + 1) act_mem[init_i] = 64'hdeadbeefdeadbeef;
        for (init_i = 0; init_i < TRACE_SLICES; init_i = init_i + 1) trace_mem[init_i] = 32'hffffffff;
    end

    assign case_rd_data   = (case_rd_addr   < CASE_WORDS)   ? case_mem[case_rd_addr]     : 32'b0;
    assign root_rd_data   = (root_rd_addr   < ROOT_WORDS)   ? root_mem[root_rd_addr]     : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr   < META_WORDS)   ? meta_mem[meta_rd_addr]     : 32'b0;
    assign trace_rd_data  = (trace_rd_addr  < TRACE_SLICES) ? trace_mem[trace_rd_addr]   : 32'b0;
    assign act_rd_data    = ((act_rd_addr >> 1) < ACT_WORDS)
                            ? (act_rd_addr[0] ? act_mem[act_rd_addr >> 1][63:32]
                                              : act_mem[act_rd_addr >> 1][31:0])
                            : 32'b0;
    assign act_words_param = ACT_WORDS;

    // -- the case, read combinationally out of the image -----------------------------------
    reg [31:0] base;
    wire [31:0] f_blocks      = case_mem[base + 0];
    wire [31:0] f_slice_words = case_mem[base + 1];
    wire [31:0] f_group       = case_mem[base + 2];
    wire [31:0] f_dtype       = case_mem[base + 3];
    wire [31:0] f_scaled      = case_mem[base + 4];
    wire [31:0] f_base        = case_mem[base + 5];
    wire [31:0] f_stride      = case_mem[base + 6];
    wire [31:0] f_root_base   = case_mem[base + 7];
    wire [31:0] f_roots       = case_mem[base + 8];
    wire [31:0] f_inject      = case_mem[base + 9];
    wire [31:0] f_gap         = case_mem[base + 20];
    wire [31:0] f_bad_tag_at  = case_mem[base + 21];
    wire [31:0] f_bad_tag     = case_mem[base + 22];

    // -- receiver ports -----------------------------------------------------------------------
    reg         cfg_start;
    reg  [15:0] cfg_blocks, cfg_slice_words, cfg_stride;
    reg  [7:0]  cfg_group, cfg_dtype;
    reg         cfg_scaled;
    reg  [31:0] cfg_base;
    reg         clear;
    reg         in_valid;
    reg  [31:0] in_data;
    reg  [15:0] in_tag;
    reg         in_last;

    wire                        act_wr_en;
    wire [$clog2(ACT_WORDS)-1:0] act_wr_addr;
    wire [63:0]                 act_wr_data;
    wire                        act_scale_wr_en;
    /* verilator lint_off UNUSEDSIGNAL */
    wire [$clog2(ACT_SCALE_WORDS)-1:0] act_scale_wr_addr;
    wire [7:0]                  act_scale_wr_data;
    /* verilator lint_on UNUSEDSIGNAL */
    wire                        recv_done;

    ot_a3_operand_receiver #(
        .ACT_WORDS(ACT_WORDS), .ACT_SCALE_WORDS(ACT_SCALE_WORDS), .TAG_W(16)
    ) u_recv (
        .clk(clk), .rst_n(rst_n),
        .cfg_start(cfg_start), .cfg_blocks(cfg_blocks), .cfg_slice_words(cfg_slice_words),
        .cfg_group(cfg_group), .cfg_dtype(cfg_dtype), .cfg_scaled(cfg_scaled),
        .cfg_base(cfg_base), .cfg_stride(cfg_stride), .clear(clear),
        .in_valid(in_valid), .in_data(in_data), .in_tag(in_tag), .in_last(in_last),
        .act_wr_en(act_wr_en), .act_wr_addr(act_wr_addr), .act_wr_data(act_wr_data),
        .act_scale_wr_en(act_scale_wr_en), .act_scale_wr_addr(act_scale_wr_addr),
        .act_scale_wr_data(act_scale_wr_data),
        .act_ready_kblocks(obs_act_ready_kblocks),
        .busy(obs_busy), .done(recv_done),
        .error_code(obs_error_code), .error_detail(obs_error_detail),
        .error_tag(obs_error_tag), .roots_count(obs_roots_count),
        .words_written(obs_words_written), .slices_ready(obs_slices_ready),
        .saturation_count(obs_saturation_count)
    );

    // -- the activation array, with ot_a3_tile64's own write semantics -------------------------
    // Wiped between cases, so that a word this case did not deliver reads as
    // unwritten rather than as the previous case's data.
    reg        wipe_active;
    reg [31:0] wipe_ptr;
    always @(posedge clk) begin
        if (wipe_active) begin
            act_mem[wipe_ptr[$clog2(ACT_WORDS)-1:0]] <= 64'hdeadbeefdeadbeef;
            if (wipe_ptr < TRACE_SLICES) trace_mem[wipe_ptr[3:0]] <= 32'hffffffff;
        end else if (act_wr_en) begin
            act_mem[act_wr_addr] <= act_wr_data;
        end
    end

    // -- the readiness stamp: cycles from a slice's last root to its readiness ------------------
    reg [31:0] cycle;
    reg [31:0] last_root_cycle;   // the cycle of the most recent root
    reg [31:0] wr_source_cycle;   // the cycle of the root that produced the word being written
    reg [15:0] ready_seen;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle <= 32'b0;
            last_root_cycle <= 32'b0;
            wr_source_cycle <= 32'b0;
            ready_seen <= 16'b0;
            obs_scale_writes <= 32'b0;
        end else begin
            cycle <= cycle + 32'd1;
            if (act_scale_wr_en) obs_scale_writes <= obs_scale_writes + 32'd1;
            if (cfg_start) begin
                ready_seen <= 16'b0;
                obs_scale_writes <= 32'b0;
            end
            if (in_valid) last_root_cycle <= cycle;
            // act_wr_en is asserted the cycle after the root that completed its
            // word, so last_root_cycle still names that root here: the stamp is
            // the cycle of the SLICE'S last root, not of the most recent one.
            if (act_wr_en) wr_source_cycle <= last_root_cycle;
            if (!wipe_active && (obs_act_ready_kblocks != ready_seen)) begin
                if (ready_seen < TRACE_SLICES)
                    trace_mem[ready_seen[3:0]] <= cycle - wr_source_cycle;
                ready_seen <= obs_act_ready_kblocks;
            end
        end
    end

    // -- the root driver ----------------------------------------------------------------------------
    localparam [2:0] R_IDLE = 3'd0, R_START = 3'd1, R_SETTLE = 3'd2, R_SEND = 3'd3,
                     R_GAP = 3'd4, R_DRAIN = 3'd5, R_FINISH = 3'd6, R_WIPE = 3'd7;
    reg [2:0]  rstate;
    reg [31:0] sent, roots_r, root_base_r, gap_r, gap_ctr, bad_tag_at_r, bad_tag_r;
    reg [31:0] settle;
    reg        refused;

    wire [31:0] root_word = root_mem[(root_base_r + sent) % ROOT_WORDS];
    wire [15:0] send_tag = (sent == bad_tag_at_r) ? bad_tag_r[15:0] : sent[15:0];

    always @* begin
        in_valid = (rstate == R_SEND);
        in_data  = root_word;
        in_tag   = send_tag;
        in_last  = (rstate == R_SEND) && (sent + 32'd1 >= roots_r);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rstate <= R_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            cfg_start <= 1'b0;
            clear <= 1'b0;
            cfg_blocks <= 16'b0; cfg_slice_words <= 16'b0; cfg_stride <= 16'b0;
            cfg_group <= 8'b0; cfg_dtype <= 8'b0; cfg_scaled <= 1'b0; cfg_base <= 32'b0;
            base <= 32'b0;
            sent <= 32'b0; roots_r <= 32'b0; root_base_r <= 32'b0;
            gap_r <= 32'b0; gap_ctr <= 32'b0;
            bad_tag_at_r <= 32'hffffffff; bad_tag_r <= 32'b0;
            wipe_active <= 1'b0; wipe_ptr <= 32'b0;
            settle <= 32'b0;
            obs_timeout <= 32'b0;
            obs_done_pulses <= 32'b0;
            refused <= 1'b0;
        end else begin
            done <= 1'b0;
            cfg_start <= 1'b0;
            clear <= 1'b0;
            if (recv_done) obs_done_pulses <= obs_done_pulses + 32'd1;

            case (rstate)
                R_IDLE: begin
                    if (run) begin
                        base <= run_case * CASE_STRIDE;
                        busy <= 1'b1;
                        clear <= 1'b1;          // the previous case's fault, before cfg_start
                        obs_timeout <= 32'b0;
                        obs_done_pulses <= 32'b0;
                        wipe_active <= 1'b1;
                        wipe_ptr <= 32'b0;
                        rstate <= R_WIPE;
                    end
                end
                R_WIPE: begin
                    if (wipe_ptr + 32'd1 >= ACT_WORDS) begin
                        wipe_active <= 1'b0;
                        rstate <= R_START;
                    end else begin
                        wipe_ptr <= wipe_ptr + 32'd1;
                    end
                end
                R_START: begin
                    cfg_blocks <= f_blocks[15:0];
                    cfg_slice_words <= f_slice_words[15:0];
                    cfg_group <= f_group[7:0];
                    cfg_dtype <= f_dtype[7:0];
                    cfg_scaled <= f_scaled[0];
                    cfg_base <= f_base;
                    cfg_stride <= f_stride[15:0];
                    cfg_start <= 1'b1;
                    sent <= 32'b0;
                    roots_r <= f_roots;
                    root_base_r <= f_root_base;
                    gap_r <= f_gap;
                    gap_ctr <= 32'b0;
                    bad_tag_at_r <= (f_inject == 32'd6) ? f_bad_tag_at : 32'hffffffff;
                    bad_tag_r <= f_bad_tag;
                    refused <= (f_inject >= 32'd1) && (f_inject <= 32'd5);
                    settle <= 32'b0;
                    rstate <= R_SETTLE;
                end
                R_SETTLE: begin
                    rstate <= refused ? R_FINISH : ((roots_r != 32'b0) ? R_SEND : R_DRAIN);
                end
                R_SEND: begin
                    sent <= sent + 32'd1;
                    if (sent + 32'd1 >= roots_r) begin
                        rstate <= R_DRAIN;
                        settle <= 32'b0;
                    end else if (gap_r != 32'b0) begin
                        gap_ctr <= 32'b0;
                        rstate <= R_GAP;
                    end
                    if (obs_error_code != 8'b0) begin
                        rstate <= R_DRAIN;
                        settle <= 32'b0;
                    end
                end
                R_GAP: begin
                    gap_ctr <= gap_ctr + 32'd1;
                    if (gap_ctr + 32'd1 >= gap_r) rstate <= R_SEND;
                end
                R_DRAIN: begin
                    settle <= settle + 32'd1;
                    if ((!obs_busy) || (settle > 32'd2000)) begin
                        if (settle > 32'd2000) obs_timeout <= 32'd1;
                        settle <= 32'b0;
                        rstate <= R_FINISH;
                    end
                end
                R_FINISH: begin
                    settle <= settle + 32'd1;
                    if (settle > 32'd8) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        rstate <= R_IDLE;
                    end
                end
                default: rstate <= R_IDLE;
            endcase
        end
    end
endmodule
