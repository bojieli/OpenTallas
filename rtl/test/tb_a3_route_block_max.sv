`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus Verilog checker for ROUTE.BLOCK_MAX
// (rtl/abi3/ot_a3_route_block_max.sv, record
// results/rtl/a3_v41_block_max_campaign.json).
//
// The first of the two independently written checkers over the same RTL and the
// same generated images.  It shares no code with
// rtl/test/a3_route_block_max_harness.cpp: each loads the images itself,
// sequences the block itself, counts what it actually checked, and prints the
// marker only if its own tallies equal the totals the image declares.  The two
// agree on the image layout, the sequencing protocol, the check accounting and
// the marker, and on nothing else.
//
// ----- IMAGE LAYOUT (tools/build_a3_v41_block_max_vectors.py) ---------------
// bm_meta.hex, 32 words:
//   0 magic 0x424d4158   1 layout version   2 BLOCK        3 SCORE_W
//   4 EXP_W              5 MANT_W           6 CMP_STAGES   7 MAX_BLOCKS
//   8 pipeline depth     9 case count      10 vector count 11 expect count
//  12 blocks retired    13 positions reduced 14 rows       15 refusal cases
//  16 VEC_STRIDE        17 CASE_STRIDE     18 EXP_STRIDE   19 LANES_MAX
//  20 rate cases       21 output latency in cycles (the stage count less one)
// bm_case.hex, CASE_STRIDE = 10 words per case:
//   0 id  1 flags (bit0 rate, bit1 refusal)  2 vec_base  3 vec_count
//   4 exp_base  5 exp_count  6 expected error_code  7 expected error_detail
//   8 expected error_block_id  9 expected error_tag
// bm_vec.hex, VEC_STRIDE = 4 + LANES_MAX words per driven block:
//   0 in_valid_count as driven (may be illegal on purpose)
//   1 flags (bit0 in_row_last)   2 in_tag   3 idle cycles before this block
//   4 + k  score code of lane k, in the low SCORE_W bits
// bm_expect.hex, EXP_STRIDE = 4 words per expected output, in output order:
//   0 out_score  1 out_block_id  2 out_row_last  3 out_tag
//
// ----- SEQUENCING PROTOCOL, which both checkers implement -------------------
// A tick applies the inputs, drives the rising edge that samples them, and then
// reads the outputs, which are the registered values of that edge.  Cycles are
// counted per case, the case's clear tick being cycle 0.
//   reset:       4 ticks with rst_n low and in_valid low, then rst_n high
//   per case:    1 tick with clear high and in_valid low;
//                then each of the case's blocks: its idle_before ticks with
//                in_valid low, then 1 tick with in_valid high and its fields;
//                then pipeline_depth + 4 drain ticks with in_valid low.
//   outputs are collected after every tick of the case, in order.
// Latency of output i is its tick minus the tick that accepted block i (blocks
// are accepted in order, and every block accepted before a refusal retires),
// and must equal the declared output latency -- meta word 21, one less than the
// stage count, because the accepting edge is the input stage's own edge -- for
// EVERY output.  That, with the rate case's window, is the II = 1 claim.
//
// ----- CHECK ACCOUNTING, so both checkers report the same count -------------
//   per case:     1 (output count) + 5 per output (score, block id, row last,
//                 tag, latency) + 4 (error_code, error_detail, error_block_id,
//                 error_tag) + 1 (busy low), + 1 more for a rate case (the
//                 output window equals the output count)
//   at the end:  15 (magic, layout version, the seven elaborated parameters
//                against the image, pipeline depth, the three retired counters,
//                total outputs, refusals observed)
// ---------------------------------------------------------------------------
module tb_a3_route_block_max #(
    parameter integer BLOCK      = 8,
    parameter integer SCORE_W    = 32,
    parameter integer EXP_W      = 8,
    parameter integer MANT_W     = 23,
    parameter integer MAX_BLOCKS = 2048,
    parameter integer CMP_STAGES = 1,
    parameter integer LANES_MAX  = 16,
    //: exactly the word counts of the four images, passed at elaboration by
    //: tools/run_a3_v41_block_max_rtl_campaign.py from the vector manifest.
    parameter integer VEC_WORDS  = 48960,
    parameter integer CASE_WORDS = 170,
    parameter integer EXP_WORDS  = 9732,
    parameter integer META_WORDS = 32
);
    localparam integer CASE_STRIDE = 10;
    localparam integer EXP_STRIDE  = 4;
    localparam integer VEC_STRIDE  = 4 + LANES_MAX;
    localparam integer QUEUE       = 256;

    reg                     clk;
    reg                     rst_n;
    reg                     in_valid;
    reg  [31:0]             in_valid_count_w;
    reg  [32*LANES_MAX-1:0] in_score_words;
    reg                     in_row_last;
    reg  [31:0]             in_tag_w;
    reg                     clear;

    wire                    out_valid;
    wire [31:0]             out_score_w;
    wire [31:0]             out_block_id_w;
    wire                    out_row_last;
    wire [31:0]             out_tag_w;
    wire [7:0]              error_code;
    wire [7:0]              error_detail;
    wire [31:0]             error_block_id_w;
    wire [31:0]             error_tag_w;
    wire                    busy;
    wire [31:0]             pipeline_depth;
    wire [31:0]             blocks_count_w;
    wire [31:0]             positions_count_w;
    wire [31:0]             rows_count_w;
    wire [31:0]             param_block, param_score_w, param_exp_w, param_mant_w;
    wire [31:0]             param_max_blocks, param_cmp_stages, param_lanes_max;

    //: this checker reads the images itself; the verification top holds no
    //: image memory, only the block and its elaborated parameter values.
    ot_a3_route_block_max_top #(
        .BLOCK(BLOCK), .SCORE_W(SCORE_W), .EXP_W(EXP_W), .MANT_W(MANT_W),
        .MAX_BLOCKS(MAX_BLOCKS), .CMP_STAGES(CMP_STAGES), .LANES_MAX(LANES_MAX)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .in_valid(in_valid), .in_valid_count_w(in_valid_count_w),
        .in_score_words(in_score_words), .in_row_last(in_row_last),
        .in_tag_w(in_tag_w), .clear(clear),
        .out_valid(out_valid), .out_score_w(out_score_w), .out_block_id_w(out_block_id_w),
        .out_row_last(out_row_last), .out_tag_w(out_tag_w),
        .error_code(error_code), .error_detail(error_detail),
        .error_block_id_w(error_block_id_w), .error_tag_w(error_tag_w),
        .busy(busy), .pipeline_depth(pipeline_depth),
        .blocks_count_w(blocks_count_w), .positions_count_w(positions_count_w),
        .rows_count_w(rows_count_w),
        .param_block(param_block), .param_score_w(param_score_w),
        .param_exp_w(param_exp_w), .param_mant_w(param_mant_w),
        .param_max_blocks(param_max_blocks), .param_cmp_stages(param_cmp_stages),
        .param_lanes_max(param_lanes_max)
    );

    reg [31:0] meta_mem [0:META_WORDS-1];
    reg [31:0] case_mem [0:CASE_WORDS-1];
    reg [31:0] vec_mem  [0:VEC_WORDS-1];
    reg [31:0] exp_mem  [0:EXP_WORDS-1];

    integer checks, failures, reported, current_case, outputs_seen, faults_seen;

    task report(input [255:0] label, input integer got, input integer want);
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                if (reported < 40) begin
                    reported = reported + 1;
                    $display("FAIL: case %0d %0s got %0d want %0d", current_case, label,
                             got, want);
                end
            end
        end
    endtask

    function integer case_word(input integer index, input integer field);
        case_word = case_mem[index * CASE_STRIDE + field];
    endfunction

    function integer vec_word(input integer index, input integer field);
        vec_word = vec_mem[index * VEC_STRIDE + field];
    endfunction

    function integer exp_word(input integer index, input integer field);
        exp_word = exp_mem[index * EXP_STRIDE + field];
    endfunction

    integer cycle;
    integer accept_q [0:QUEUE-1];
    integer accept_wr, accept_rd, exp_ptr, case_outputs;
    integer first_out_cycle, last_out_cycle, case_exp_base;

    task collect;
        begin
            if (out_valid === 1'b1) begin
                report("out_score",    out_score_w,          exp_word(case_exp_base + exp_ptr, 0));
                report("out_block_id", out_block_id_w,       exp_word(case_exp_base + exp_ptr, 1));
                report("out_row_last", {31'b0, out_row_last}, exp_word(case_exp_base + exp_ptr, 2));
                report("out_tag",      out_tag_w,            exp_word(case_exp_base + exp_ptr, 3));
                report("latency",      cycle - accept_q[accept_rd], m_latency);
                accept_rd    = (accept_rd + 1) % QUEUE;
                exp_ptr      = exp_ptr + 1;
                case_outputs = case_outputs + 1;
                outputs_seen = outputs_seen + 1;
                if (first_out_cycle < 0) first_out_cycle = cycle;
                last_out_cycle = cycle;
            end
        end
    endtask

    task tick;
        begin
            clk = 1'b0;
            #5;
            clk = 1'b1;
            #5;
            cycle = cycle + 1;
            collect;
        end
    endtask

    task idle_tick;
        begin
            in_valid = 1'b0;
            clear    = 1'b0;
            tick;
        end
    endtask

    integer m_magic, m_version, m_block, m_score_w, m_exp_w, m_mant_w;
    integer m_cmp_stages, m_max_blocks, m_depth, m_cases, m_expects;
    integer m_blocks, m_positions, m_rows, m_faults, m_lanes_max, m_latency;
    integer c, v, k, lane, drain, window;
    integer vec_base, vec_count, exp_count, flags, err_code, err_detail;
    integer err_block_id, err_tag, idle_before;

    initial begin
        $readmemh("bm_meta.hex", meta_mem);
        $readmemh("bm_case.hex", case_mem);
        $readmemh("bm_vec.hex", vec_mem);
        $readmemh("bm_expect.hex", exp_mem);

        checks = 0; failures = 0; reported = 0; current_case = -1;
        outputs_seen = 0; faults_seen = 0;
        clk = 1'b0; rst_n = 1'b0; in_valid = 1'b0; clear = 1'b0;
        in_valid_count_w = 32'b0; in_score_words = {32*LANES_MAX{1'b0}};
        in_row_last = 1'b0; in_tag_w = 32'b0;
        cycle = 0; accept_wr = 0; accept_rd = 0; exp_ptr = 0;
        case_exp_base = 0; case_outputs = 0;
        first_out_cycle = -1; last_out_cycle = -1;

        m_magic      = meta_mem[0];
        m_version    = meta_mem[1];
        m_block      = meta_mem[2];
        m_score_w    = meta_mem[3];
        m_exp_w      = meta_mem[4];
        m_mant_w     = meta_mem[5];
        m_cmp_stages = meta_mem[6];
        m_max_blocks = meta_mem[7];
        m_depth      = meta_mem[8];
        m_cases      = meta_mem[9];
        m_expects    = meta_mem[11];
        m_blocks     = meta_mem[12];
        m_positions  = meta_mem[13];
        m_rows       = meta_mem[14];
        m_faults     = meta_mem[15];
        m_lanes_max  = meta_mem[19];
        m_latency    = meta_mem[21];

        for (k = 0; k < 4; k = k + 1) begin
            clk = 1'b0; #5; clk = 1'b1; #5;
        end
        rst_n = 1'b1;

        for (c = 0; c < m_cases; c = c + 1) begin
            current_case  = c;
            flags         = case_word(c, 1);
            vec_base      = case_word(c, 2);
            vec_count     = case_word(c, 3);
            case_exp_base = case_word(c, 4);
            exp_count     = case_word(c, 5);
            err_code      = case_word(c, 6);
            err_detail    = case_word(c, 7);
            err_block_id  = case_word(c, 8);
            err_tag       = case_word(c, 9);
            exp_ptr = 0; case_outputs = 0; cycle = 0;
            accept_wr = 0; accept_rd = 0;
            first_out_cycle = -1; last_out_cycle = -1;

            in_valid = 1'b0; clear = 1'b1; tick; clear = 1'b0;

            for (v = 0; v < vec_count; v = v + 1) begin
                idle_before = vec_word(vec_base + v, 3);
                for (k = 0; k < idle_before; k = k + 1) idle_tick;
                in_valid_count_w = vec_word(vec_base + v, 0);
                in_row_last      = vec_word(vec_base + v, 1) & 1;
                in_tag_w         = vec_word(vec_base + v, 2);
                for (lane = 0; lane < LANES_MAX; lane = lane + 1)
                    in_score_words[32*lane +: 32] = vec_word(vec_base + v, 4 + lane);
                in_valid            = 1'b1;
                accept_q[accept_wr] = cycle + 1;
                accept_wr           = (accept_wr + 1) % QUEUE;
                tick;
                in_valid = 1'b0;
            end

            drain = pipeline_depth + 4;
            for (k = 0; k < drain; k = k + 1) idle_tick;

            report("case_outputs", case_outputs, exp_count);
            report("error_code",   error_code,   err_code);
            report("error_detail", error_detail, err_detail);
            report("error_block_id", error_block_id_w, err_block_id);
            report("error_tag",      error_tag_w,      err_tag);
            report("busy", {31'b0, busy}, 0);
            if (flags & 2) faults_seen = faults_seen + 1;
            if (flags & 1) begin
                window = (first_out_cycle < 0) ? 0 : (last_out_cycle - first_out_cycle + 1);
                $display("RATE: case=%0d outputs=%0d window=%0d first=%0d last=%0d",
                         c, case_outputs, window, first_out_cycle, last_out_cycle);
                report("rate_window", window, case_outputs);
            end
        end

        current_case = -1;
        report("magic",            m_magic,   32'h424d4158);
        report("layout_version",   m_version, 1);
        report("param_block",      param_block,      m_block);
        report("param_score_w",    param_score_w,    m_score_w);
        report("param_exp_w",      param_exp_w,      m_exp_w);
        report("param_mant_w",     param_mant_w,     m_mant_w);
        report("param_max_blocks", param_max_blocks, m_max_blocks);
        report("param_cmp_stages", param_cmp_stages, m_cmp_stages);
        report("param_lanes_max",  param_lanes_max,  m_lanes_max);
        report("pipeline_depth",   pipeline_depth,   m_depth);
        report("blocks_count",     blocks_count_w,   m_blocks);
        report("positions_count",  positions_count_w, m_positions);
        report("rows_count",       rows_count_w,     m_rows);
        report("total_outputs",    outputs_seen,     m_expects);
        report("refusal_cases",    faults_seen,      m_faults);

        if (failures == 0 && outputs_seen == m_blocks && faults_seen == m_faults) begin
            $display("PASS: A3 V41 BLOCK_MAX block=%0d cmp_stages=%0d cases=%0d outputs=%0d faults=%0d checks=%0d",
                     m_block, m_cmp_stages, m_cases, outputs_seen, faults_seen, checks);
        end else begin
            $display("FAILURES: %0d of %0d checks (outputs=%0d expected=%0d)",
                     failures, checks, outputs_seen, m_blocks);
        end
        $finish;
    end
endmodule
