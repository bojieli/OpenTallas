`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The six operator families the ABI 3.0 issue bridge used to refuse.
//
// The bridge is the design under test, unmodified and instantiated whole.  The
// testbench supplies the three things the device supplies around it: the
// sequencer's resolved-view stream, an immutable descriptor store answering
// one cycle after a request, and the compact operand bank.  Everything the
// bridge decides -- whether the opcode is admitted, whether the operator,
// view and numeric records prove the family's frozen contract, where each
// operand lives, how many result words and how much work to expect -- is the
// bridge's own.
//
// The bank is loaded once and the cases run in order, so a scatter's write is
// the attention's read.  Every case also checks that the words outside its own
// result region are untouched by checking its region against an independently
// computed expectation, and every refusal checks that the region it would have
// written is byte-identical to what it was before.
// ---------------------------------------------------------------------------
module tb_a3_operator_admission;
    localparam integer CASE_COUNT = 19;
    localparam integer CASE_WORDS = 64;
    localparam integer VIEW_SLOTS = 5;
    localparam integer VIEW_WORDS = 8;
    localparam integer MAP_ENTRIES = 8;
    localparam integer DESC_RECORDS = 218;
    localparam integer BANK_WORDS = 242050;
    localparam integer INDEX_WORDS = 64;
    localparam integer EXPECTED_WORDS = 33093;
    localparam integer PRELOAD_WORDS = 12291;
    localparam integer CASE_TIMEOUT = 4000000;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [31:0]   case_mem [0:CASE_COUNT*CASE_WORDS-1];
    reg [31:0]   view_mem [0:CASE_COUNT*VIEW_SLOTS*VIEW_WORDS-1];
    reg [1535:0] desc_mem [0:DESC_RECORDS-1];
    reg [31:0]   bank_mem [0:BANK_WORDS-1];
    reg [31:0]   index_mem [0:INDEX_WORDS-1];
    reg [31:0]   expected_mem [0:EXPECTED_WORDS-1];
    reg [31:0]   preload_mem [0:PRELOAD_WORDS-1];

    reg [1023:0] cases_path;
    reg [1023:0] views_path;
    reg [1023:0] descriptors_path;
    reg [1023:0] bank_path;
    reg [1023:0] index_path;
    reg [1023:0] expected_path;
    reg [1023:0] preload_path;

    // -- bridge interface ------------------------------------------------
    reg          clear;
    reg          issue_valid;
    wire         issue_ready;
    wire         issue_fault;
    wire [15:0]  issue_trap_class;
    reg  [7:0]   issue_family;
    reg  [7:0]   issue_sub;
    reg  [31:0]  issue_descriptor_id;
    reg  [31:0]  issue_index;

    reg          view_valid;
    reg  [31:0]  view_descriptor_id;
    reg  [2:0]   view_slot;
    reg  [31:0]  view_extent;
    reg  [7:0]   view_extent_axis;
    reg  [63:0]  view_element_offset;
    reg  [7:0]   view_rank;

    wire         desc_req;
    wire [31:0]  desc_id;
    reg          desc_valid;
    reg          desc_fault;
    reg  [1535:0] desc_data;

    reg          cfg_extended_placement_valid;
    reg  [31:0]  cfg_map_object [0:MAP_ENTRIES-1];
    reg  [31:0]  cfg_map_base [0:MAP_ENTRIES-1];
    reg  [31:0]  cfg_context_length;
    reg  [31:0]  cfg_kv_plane_rows;
    reg  [31:0]  cfg_generation_policy_id;
    reg  [31:0]  cfg_request_max_new_tokens;
    reg  [31:0]  cfg_generated_before;

    wire         m0_rd_en;
    wire [31:0]  m0_rd_addr;
    reg  [31:0]  m0_rd_data;
    wire         m1_rd_en;
    wire [31:0]  m1_rd_addr;
    reg  [31:0]  m1_rd_data;
    wire         m2_rd_en;
    wire [31:0]  m2_rd_addr;
    wire         m3_rd_en;
    wire [31:0]  m3_rd_addr;
    wire         out_we;
    wire [31:0]  out_addr;
    wire [31:0]  out_data;
    wire         m0_reads_result;
    wire         m1_reads_result;
    wire         m1_reads_matmul_weight;

    wire         engine_busy;
    wire [7:0]   engine_error_code;
    wire [31:0]  engine_result_count;
    wire [31:0]  engine_work_count;
    wire [31:0]  real_launch_count;
    wire [31:0]  dma_gather_launch_count;
    wire [31:0]  embedding_launch_count;
    wire [31:0]  rms_norm_launch_count;
    wire [31:0]  head_rms_norm_launch_count;
    wire [31:0]  rope_launch_count;
    wire [31:0]  dma_transfer_launch_count;
    wire [31:0]  matmul_launch_count;
    wire [31:0]  vector_add_launch_count;
    wire [31:0]  vector_silu_mul_launch_count;
    wire [31:0]  dma_scatter_launch_count;
    wire [31:0]  attention_gqa_launch_count;
    wire [31:0]  selection_argmax_launch_count;
    wire [31:0]  selection_token_append_launch_count;
    wire [31:0]  selected_token;
    wire [31:0]  selected_tie_multiplicity;
    wire [7:0]   selected_eos_reason;
    wire [31:0]  capability_fault_count;
    wire [31:0]  descriptor_fault_count;
    wire [31:0]  engine_fault_count;
    wire [31:0]  last_response_index;
    wire [7:0]   last_response_family;
    wire [7:0]   last_response_sub;
    wire [31:0]  last_response_descriptor_id;

    integer case_index;
    integer slot_index;
    integer word_index;
    integer base;
    integer view_base;
    integer checks;
    integer positive_cases;
    integer compared_words;
    integer timeout_cycles;
    integer observed_writes;
    reg     read_oob;
    reg     write_oob;
    reg [31:0] observed_fault;
    reg [15:0] observed_trap;
    reg [31:0] observed_result_count;
    reg [31:0] observed_work_count;

    task automatic check_equal;
        input [1023:0] label;
        input [63:0] actual;
        input [63:0] expected;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                $display(
                    "FAIL case=%0d %0s actual=%0d expected=%0d",
                    case_index, label, actual, expected
                );
                $fatal(1);
            end
        end
    endtask

    ot_a3_engine_issue_bridge dut (
        .clk(clk),
        .rst_n(rst_n),
        .clear(clear),
        .issue_valid(issue_valid),
        .issue_ready(issue_ready),
        .issue_fault(issue_fault),
        .issue_trap_class(issue_trap_class),
        .issue_family(issue_family),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset),
        .view_rank(view_rank),
        .desc_req(desc_req),
        .desc_id(desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .cfg_index_base(32'd0),
        .cfg_source_base(32'd0),
        .cfg_source_launch_stride(32'd0),
        .cfg_embedding_source_base(32'd0),
        .cfg_rms_input_base(32'd0),
        .cfg_rms_weight_base(32'd0),
        .cfg_transfer_index_base(32'd0),
        .cfg_transfer_source_base(32'd0),
        .cfg_matmul_input_base(32'd0),
        .cfg_matmul_weight_object_0(32'hffff_ffff),
        .cfg_matmul_weight_base_0(32'd0),
        .cfg_matmul_weight_object_1(32'hffff_ffff),
        .cfg_matmul_weight_base_1(32'd0),
        .cfg_matmul_weight_object_2(32'hffff_ffff),
        .cfg_matmul_weight_base_2(32'd0),
        .cfg_head_input_object_0(32'hffff_ffff),
        .cfg_head_input_base_0(32'd0),
        .cfg_head_input_object_1(32'hffff_ffff),
        .cfg_head_input_base_1(32'd0),
        .cfg_head_weight_object_0(32'hffff_ffff),
        .cfg_head_weight_base_0(32'd0),
        .cfg_head_weight_object_1(32'hffff_ffff),
        .cfg_head_weight_base_1(32'd0),
        .cfg_rope_input_object_0(32'hffff_ffff),
        .cfg_rope_input_base_0(32'd0),
        .cfg_rope_input_object_1(32'hffff_ffff),
        .cfg_rope_input_base_1(32'd0),
        .cfg_rope_coefficient_object(32'hffff_ffff),
        .cfg_rope_coefficient_base(32'd0),
        .cfg_output_base(32'd0),
        .cfg_extended_placement_valid(cfg_extended_placement_valid),
        .cfg_map_object_0(cfg_map_object[0]),
        .cfg_map_base_0(cfg_map_base[0]),
        .cfg_map_object_1(cfg_map_object[1]),
        .cfg_map_base_1(cfg_map_base[1]),
        .cfg_map_object_2(cfg_map_object[2]),
        .cfg_map_base_2(cfg_map_base[2]),
        .cfg_map_object_3(cfg_map_object[3]),
        .cfg_map_base_3(cfg_map_base[3]),
        .cfg_map_object_4(cfg_map_object[4]),
        .cfg_map_base_4(cfg_map_base[4]),
        .cfg_map_object_5(cfg_map_object[5]),
        .cfg_map_base_5(cfg_map_base[5]),
        .cfg_map_object_6(cfg_map_object[6]),
        .cfg_map_base_6(cfg_map_base[6]),
        .cfg_map_object_7(cfg_map_object[7]),
        .cfg_map_base_7(cfg_map_base[7]),
        .cfg_context_length(cfg_context_length),
        .cfg_kv_plane_rows(cfg_kv_plane_rows),
        .cfg_generation_policy_id(cfg_generation_policy_id),
        .cfg_request_max_new_tokens(cfg_request_max_new_tokens),
        .cfg_generated_before(cfg_generated_before),
        .m0_rd_en(m0_rd_en),
        .m0_rd_addr(m0_rd_addr),
        .m0_rd_data(m0_rd_data),
        .m1_rd_en(m1_rd_en),
        .m1_rd_addr(m1_rd_addr),
        .m1_rd_data(m1_rd_data),
        .m2_rd_en(m2_rd_en),
        .m2_rd_addr(m2_rd_addr),
        .m2_rd_data(32'd0),
        .m3_rd_en(m3_rd_en),
        .m3_rd_addr(m3_rd_addr),
        .m3_rd_data(32'd0),
        .out_we(out_we),
        .out_addr(out_addr),
        .out_data(out_data),
        .m0_reads_result(m0_reads_result),
        .m1_reads_result(m1_reads_result),
        .m1_reads_matmul_weight(m1_reads_matmul_weight),
        .engine_busy(engine_busy),
        .engine_error_code(engine_error_code),
        .engine_result_count(engine_result_count),
        .engine_work_count(engine_work_count),
        .real_launch_count(real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .rms_norm_launch_count(rms_norm_launch_count),
        .head_rms_norm_launch_count(head_rms_norm_launch_count),
        .rope_launch_count(rope_launch_count),
        .dma_transfer_launch_count(dma_transfer_launch_count),
        .matmul_launch_count(matmul_launch_count),
        .vector_add_launch_count(vector_add_launch_count),
        .vector_silu_mul_launch_count(vector_silu_mul_launch_count),
        .dma_scatter_launch_count(dma_scatter_launch_count),
        .attention_gqa_launch_count(attention_gqa_launch_count),
        .selection_argmax_launch_count(selection_argmax_launch_count),
        .selection_token_append_launch_count(selection_token_append_launch_count),
        .selected_token(selected_token),
        .selected_tie_multiplicity(selected_tie_multiplicity),
        .selected_eos_reason(selected_eos_reason),
        .capability_fault_count(capability_fault_count),
        .descriptor_fault_count(descriptor_fault_count),
        .engine_fault_count(engine_fault_count),
        .last_response_index(last_response_index),
        .last_response_family(last_response_family),
        .last_response_sub(last_response_sub),
        .last_response_descriptor_id(last_response_descriptor_id)
    );

    // -- immutable descriptor store, one-cycle response ------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            desc_valid <= 1'b0;
            desc_fault <= 1'b0;
            desc_data <= 1536'd0;
        end else begin
            desc_valid <= desc_req;
            if (desc_req) begin
                if (desc_id < DESC_RECORDS) begin
                    desc_data <= desc_mem[desc_id];
                    desc_fault <= 1'b0;
                end else begin
                    desc_data <= 1536'd0;
                    desc_fault <= 1'b1;
                end
            end
        end
    end

    // -- compact operand bank and index bank -----------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            m0_rd_data <= 32'd0;
            m1_rd_data <= 32'd0;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            observed_writes <= 0;
        end else begin
            if (clear) begin
                read_oob <= 1'b0;
                write_oob <= 1'b0;
                observed_writes <= 0;
            end
            if (m0_rd_en) begin
                if (m0_reads_result) begin
                    if (m0_rd_addr < BANK_WORDS)
                        m0_rd_data <= bank_mem[m0_rd_addr];
                    else begin
                        m0_rd_data <= 32'd0;
                        read_oob <= 1'b1;
                    end
                end else begin
                    if (m0_rd_addr < INDEX_WORDS)
                        m0_rd_data <= index_mem[m0_rd_addr];
                    else begin
                        m0_rd_data <= 32'd0;
                        read_oob <= 1'b1;
                    end
                end
            end
            if (m1_rd_en) begin
                if (m1_reads_matmul_weight) begin
                    m1_rd_data <= 32'd0;
                    read_oob <= 1'b1;
                end else if (m1_reads_result) begin
                    if (m1_rd_addr < BANK_WORDS)
                        m1_rd_data <= bank_mem[m1_rd_addr];
                    else begin
                        m1_rd_data <= 32'd0;
                        read_oob <= 1'b1;
                    end
                end else begin
                    if (m1_rd_addr < INDEX_WORDS)
                        m1_rd_data <= index_mem[m1_rd_addr];
                    else begin
                        m1_rd_data <= 32'd0;
                        read_oob <= 1'b1;
                    end
                end
            end
            if (m2_rd_en || m3_rd_en)
                read_oob <= 1'b1;
            if (out_we) begin
                observed_writes <= observed_writes + 1;
                if (out_addr < BANK_WORDS)
                    bank_mem[out_addr] <= out_data;
                else
                    write_oob <= 1'b1;
            end
        end
    end

    initial begin
        checks = 0;
        positive_cases = 0;
        compared_words = 0;
        clear = 1'b0;
        issue_valid = 1'b0;
        issue_family = 8'd0;
        issue_sub = 8'd0;
        issue_descriptor_id = 32'hffff_ffff;
        issue_index = 32'd0;
        view_valid = 1'b0;
        view_descriptor_id = 32'hffff_ffff;
        view_slot = 3'd0;
        view_extent = 32'd0;
        view_extent_axis = 8'd0;
        view_element_offset = 64'd0;
        view_rank = 8'd0;
        cfg_extended_placement_valid = 1'b0;
        cfg_context_length = 32'd0;
        cfg_kv_plane_rows = 32'd0;
        cfg_generation_policy_id = 32'hffff_ffff;
        cfg_request_max_new_tokens = 32'd0;
        cfg_generated_before = 32'd0;
        for (slot_index = 0; slot_index < MAP_ENTRIES; slot_index = slot_index + 1)
        begin
            cfg_map_object[slot_index] = 32'hffff_ffff;
            cfg_map_base[slot_index] = 32'd0;
        end

        if (!$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("VIEWS=%s", views_path) ||
            !$value$plusargs("DESCRIPTORS=%s", descriptors_path) ||
            !$value$plusargs("BANK=%s", bank_path) ||
            !$value$plusargs("INDEX=%s", index_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path) ||
            !$value$plusargs("PRELOAD=%s", preload_path)) begin
            $fatal(1, "missing ABI3 operator-admission vector plusargs");
        end
        $readmemh(cases_path, case_mem);
        $readmemh(views_path, view_mem);
        $readmemh(descriptors_path, desc_mem);
        $readmemh(bank_path, bank_mem);
        $readmemh(index_path, index_mem);
        $readmemh(expected_path, expected_mem);
        $readmemh(preload_path, preload_mem);

        $display(
            "GEOMETRY cases=%0d case_words=%0d view_slots=%0d view_words=%0d map_entries=%0d descriptor_records=%0d bank_words=%0d index_words=%0d expected_words=%0d preload_words=%0d",
            CASE_COUNT, CASE_WORDS, VIEW_SLOTS, VIEW_WORDS, MAP_ENTRIES,
            DESC_RECORDS, BANK_WORDS, INDEX_WORDS, EXPECTED_WORDS,
            PRELOAD_WORDS
        );

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (case_index = 0; case_index < CASE_COUNT;
             case_index = case_index + 1) begin
            base = case_index * CASE_WORDS;
            view_base = case_index * VIEW_SLOTS * VIEW_WORDS;

            cfg_extended_placement_valid = case_mem[base + 40][0];
            cfg_context_length = case_mem[base + 4];
            cfg_kv_plane_rows = case_mem[base + 5];
            cfg_generation_policy_id = case_mem[base + 6];
            cfg_request_max_new_tokens = case_mem[base + 7];
            cfg_generated_before = case_mem[base + 8];
            for (slot_index = 0; slot_index < MAP_ENTRIES;
                 slot_index = slot_index + 1) begin
                cfg_map_object[slot_index] = case_mem[base + 24 + 2*slot_index];
                cfg_map_base[slot_index] = case_mem[base + 25 + 2*slot_index];
            end

            @(negedge clk);
            clear = 1'b1;
            @(negedge clk);
            clear = 1'b0;

            // The preload is the testbench standing in for the operator that
            // would have produced this operand in a longer program -- the
            // attention projection and the MLP down projection are both
            // TENSOR.MATMUL, which this campaign does not run.
            for (word_index = 0; word_index < case_mem[base + 21];
                 word_index = word_index + 1)
                bank_mem[case_mem[base + 22] + word_index] =
                    preload_mem[case_mem[base + 23] + word_index];

            // The sequencer's resolved-view stream, in slot order.
            for (slot_index = 0; slot_index < VIEW_SLOTS;
                 slot_index = slot_index + 1) begin
                if (view_mem[view_base + slot_index*VIEW_WORDS + 0] != 0) begin
                    @(negedge clk);
                    view_valid = 1'b1;
                    view_descriptor_id =
                        view_mem[view_base + slot_index*VIEW_WORDS + 1];
                    view_slot =
                        view_mem[view_base + slot_index*VIEW_WORDS + 2][2:0];
                    view_extent =
                        view_mem[view_base + slot_index*VIEW_WORDS + 3];
                    view_extent_axis =
                        view_mem[view_base + slot_index*VIEW_WORDS + 4][7:0];
                    view_element_offset = {
                        view_mem[view_base + slot_index*VIEW_WORDS + 6],
                        view_mem[view_base + slot_index*VIEW_WORDS + 5]
                    };
                    view_rank =
                        view_mem[view_base + slot_index*VIEW_WORDS + 7][7:0];
                    @(negedge clk);
                    view_valid = 1'b0;
                end
            end

            issue_family = case_mem[base + 0][7:0];
            issue_sub = case_mem[base + 1][7:0];
            issue_descriptor_id = case_mem[base + 2];
            issue_index = case_index;
            @(negedge clk);
            issue_valid = 1'b1;
            timeout_cycles = 0;
            while (!issue_ready && timeout_cycles < CASE_TIMEOUT) begin
                @(negedge clk);
                timeout_cycles = timeout_cycles + 1;
            end
            if (!issue_ready)
                $fatal(1, "case %0d timed out", case_index);
            observed_fault = {31'd0, issue_fault};
            observed_trap = issue_trap_class;
            observed_result_count = engine_result_count;
            observed_work_count = engine_work_count;
            @(negedge clk);
            issue_valid = 1'b0;
            @(negedge clk);

            check_equal("fault", observed_fault, case_mem[base + 9]);
            check_equal("trap", observed_trap, case_mem[base + 10]);
            check_equal("response_family", last_response_family,
                        case_mem[base + 0]);
            check_equal("response_sub", last_response_sub, case_mem[base + 1]);
            check_equal("response_descriptor", last_response_descriptor_id,
                        case_mem[base + 2]);
            check_equal("response_index", last_response_index, case_index);
            check_equal("write_beats", observed_writes, case_mem[base + 13]);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("engine_busy", engine_busy, 0);
            if (case_mem[base + 9] == 0) begin
                check_equal("result_count", observed_result_count,
                            case_mem[base + 11]);
                check_equal("work_count", observed_work_count,
                            case_mem[base + 12]);
                check_equal("engine_error", engine_error_code, 0);
                check_equal("real_launches", real_launch_count, 1);
                positive_cases = positive_cases + 1;
            end else begin
                check_equal("real_launches", real_launch_count, 0);
                check_equal("capability_faults", capability_fault_count,
                            (case_mem[base + 10] == 4) ? 1 : 0);
                check_equal("descriptor_faults", descriptor_fault_count,
                            (case_mem[base + 10] == 3) ? 1 : 0);
                check_equal("engine_faults", engine_fault_count,
                            (case_mem[base + 10] == 8) ? 1 : 0);
            end
            check_equal("launch_add", vector_add_launch_count,
                        (case_mem[base + 18] == 0) ? 1 : 0);
            check_equal("launch_silu", vector_silu_mul_launch_count,
                        (case_mem[base + 18] == 1) ? 1 : 0);
            check_equal("launch_scatter", dma_scatter_launch_count,
                        (case_mem[base + 18] == 2) ? 1 : 0);
            check_equal("launch_gqa", attention_gqa_launch_count,
                        (case_mem[base + 18] == 3) ? 1 : 0);
            check_equal("launch_argmax", selection_argmax_launch_count,
                        (case_mem[base + 18] == 4) ? 1 : 0);
            check_equal("launch_token_append",
                        selection_token_append_launch_count,
                        (case_mem[base + 18] == 5) ? 1 : 0);
            check_equal("launch_legacy_gather", dma_gather_launch_count, 0);
            check_equal("launch_legacy_matmul", matmul_launch_count, 0);
            check_equal("launch_legacy_rms", rms_norm_launch_count, 0);
            check_equal("launch_legacy_rope", rope_launch_count, 0);
            check_equal("launch_legacy_embed", embedding_launch_count, 0);
            check_equal("launch_legacy_transfer", dma_transfer_launch_count, 0);
            if (case_mem[base + 18] == 4) begin
                check_equal("token", selected_token, case_mem[base + 14]);
                check_equal("tie_multiplicity", selected_tie_multiplicity,
                            case_mem[base + 19]);
            end
            if (case_mem[base + 18] == 5) begin
                check_equal("token", selected_token, case_mem[base + 14]);
                check_equal("eos_reason", selected_eos_reason,
                            case_mem[base + 15]);
            end

            for (word_index = 0; word_index < case_mem[base + 17];
                 word_index = word_index + 1) begin
                check_equal(
                    "bank_word",
                    bank_mem[case_mem[base + 16] + word_index],
                    expected_mem[case_mem[base + 20] + word_index]
                );
            end
            compared_words = compared_words + case_mem[base + 17];

            $display(
                "CASE_SUMMARY index=%0d fault=%0d trap=%0d result=%0d work=%0d writes=%0d token=%0d ties=%0d eos=%0d verification_cycles=%0d",
                case_index, observed_fault, observed_trap,
                observed_result_count, observed_work_count, observed_writes,
                selected_token, selected_tie_multiplicity, selected_eos_reason,
                timeout_cycles
            );
            repeat (3) @(posedge clk);
        end

        $display(
            "PASS a3_operator_admission cases=%0d positive=%0d words=%0d checks=%0d",
            CASE_COUNT, positive_cases, compared_words, checks
        );
        $finish;
    end
endmodule
