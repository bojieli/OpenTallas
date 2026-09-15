`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The row-shard vehicle: one operator, one contiguous range of output rows.
//
// A TENSOR.MATMUL output row is a dot product over the whole reduction axis K
// and is independent of every other output row -- ot_a3_mac_lane walks K in
// ascending order for one output row and carries no state across a row
// boundary -- so running rows [first, first+count) is the SAME arithmetic the
// whole operator would do for those rows, not an approximation of it.  This
// bench runs one such range and publishes every word the engine wrote, by
// address and by value, so a composer outside can reassemble the operator and
// refuse anything that is not an exact partition.
//
// The design under test is rtl/abi3/ot_a3_engine_issue_bridge.sv, unmodified
// and instantiated whole, exactly as rtl/test/tb_a3_operator_admission.sv
// instantiates it.  Everything the bridge decides -- admission, the operator,
// view and numeric contract, where each operand lives, how many result words
// and how much work -- is still the bridge's own.  What this bench supplies is
// what the device supplies around it: the sequencer's resolved-view stream, a
// descriptor store, the activation bank, and the projection matrix.
//
// The projection matrix is NOT held.  It is addressed through the same paged
// DPI window rtl/test/a3_shipped_prefix_top.sv opens over the checkpoint's own
// safetensors shards, so a 1.24 GB LM head costs the window's resident cap and
// not 1.24 GB of simulator heap.  cfg_matmul_weight_window_base is the byte
// offset of THIS SHARD's first row inside that image; the bridge's own 32-bit
// operand offset then addresses only the shard.
//
// This vehicle runs under Verilator alone, for the same reason the
// integrated shipped-prefix vehicle does: the window is DPI-C.
// ---------------------------------------------------------------------------
module tb_a3_row_shard;
    parameter integer CASE_COUNT = 1;
    localparam integer CASE_WORDS = 128;
    localparam integer VIEW_SLOTS = 5;
    localparam integer VIEW_WORDS = 8;
    localparam integer MAP_ENTRIES = 32;
    localparam integer MAP_BASE = 64;
    parameter integer DESC_RECORDS = 320;
    parameter integer BANK_WORDS = 32768;
    parameter integer SOURCE_WORDS = 16;
    parameter integer INDEX_WORDS = 64;
    //: 12,288 because that is the widest operator the bridge now admits: the
    //: MLP gate and up projections are [12288, 4096], and they were refused
    //: while the weight predicate pinned the reduction length to the embedding
    //: width.  At 4,096 this array was large enough only because those legs
    //: never ran -- $readmemh aborted on "file address beyond bounds of array"
    //: the first time one was admitted.
    parameter integer EXPECTED_WORDS = 12288;
    parameter integer PRELOAD_WORDS = 12288;
    // A guard against a case that never retires, not a budget.  The largest
    // shard this vehicle issues is 12,288 output rows over K = 4,096, which is
    // 50,331,648 multiply-accumulates and about 252 x 10^6 cycles at the
    // sequential lane's measured 5.008 cycles per MAC.
    localparam integer CASE_TIMEOUT = 400000000;

    import "DPI-C" function longint unsigned ot_a3_shard_window_open();
    import "DPI-C" function int unsigned ot_a3_shard_window_halfword(
        input longint unsigned halfword_index);
    import "DPI-C" function void ot_a3_shard_stream_open(input string path);
    import "DPI-C" function void ot_a3_shard_stream_write(
        input int unsigned address, input int unsigned data);
    import "DPI-C" function void ot_a3_shard_stream_close();

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg [31:0]   case_mem [0:CASE_COUNT*CASE_WORDS-1];
    reg [31:0]   view_mem [0:CASE_COUNT*VIEW_SLOTS*VIEW_WORDS-1];
    reg [1535:0] desc_mem [0:DESC_RECORDS-1];
    reg [31:0]   bank_mem [0:BANK_WORDS-1];
    reg [31:0]   index_mem [0:INDEX_WORDS-1];
    reg [31:0]   source_mem [0:SOURCE_WORDS-1];
    reg [31:0]   expected_mem [0:EXPECTED_WORDS-1];
    reg [31:0]   preload_mem [0:PRELOAD_WORDS-1];

    reg [4095:0] cases_path;
    reg [4095:0] views_path;
    reg [4095:0] descriptors_path;
    reg [4095:0] index_path;
    reg [4095:0] source_path;
    reg [4095:0] expected_path;
    reg [4095:0] preload_path;
    reg [4095:0] stream_path;

    longint unsigned window_bytes;
    longint unsigned window_base;
    longint unsigned weight_halfword;

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
    integer mismatched_words;
    integer timeout_cycles;
    integer observed_writes;
    integer stream_writes;
    reg     read_oob;
    reg     write_oob;
    reg     stream_open;
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
                $display("FAIL case=%0d %0s actual=%0d expected=%0d",
                         case_index, label, actual, expected);
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
        .issue_eos_reason(),
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
        .desc_rd_valid(desc_valid),
        .desc_rd_fault(desc_fault),
        .desc_rd_data(desc_data),
        .cfg_index_base(32'd0),
        .cfg_source_base(32'd0),
        .cfg_source_launch_stride(32'd0),
        .cfg_embedding_source_base(32'd0),
        .cfg_transfer_index_base(32'd0),
        .cfg_transfer_source_base(32'd0),
        .cfg_extended_placement_valid(cfg_extended_placement_valid),
        .cfg_place_object_0(cfg_map_object[0]),   .cfg_place_base_0(cfg_map_base[0]),
        .cfg_place_object_1(cfg_map_object[1]),   .cfg_place_base_1(cfg_map_base[1]),
        .cfg_place_object_2(cfg_map_object[2]),   .cfg_place_base_2(cfg_map_base[2]),
        .cfg_place_object_3(cfg_map_object[3]),   .cfg_place_base_3(cfg_map_base[3]),
        .cfg_place_object_4(cfg_map_object[4]),   .cfg_place_base_4(cfg_map_base[4]),
        .cfg_place_object_5(cfg_map_object[5]),   .cfg_place_base_5(cfg_map_base[5]),
        .cfg_place_object_6(cfg_map_object[6]),   .cfg_place_base_6(cfg_map_base[6]),
        .cfg_place_object_7(cfg_map_object[7]),   .cfg_place_base_7(cfg_map_base[7]),
        .cfg_place_object_8(cfg_map_object[8]),   .cfg_place_base_8(cfg_map_base[8]),
        .cfg_place_object_9(cfg_map_object[9]),   .cfg_place_base_9(cfg_map_base[9]),
        .cfg_place_object_10(cfg_map_object[10]), .cfg_place_base_10(cfg_map_base[10]),
        .cfg_place_object_11(cfg_map_object[11]), .cfg_place_base_11(cfg_map_base[11]),
        .cfg_place_object_12(cfg_map_object[12]), .cfg_place_base_12(cfg_map_base[12]),
        .cfg_place_object_13(cfg_map_object[13]), .cfg_place_base_13(cfg_map_base[13]),
        .cfg_place_object_14(cfg_map_object[14]), .cfg_place_base_14(cfg_map_base[14]),
        .cfg_place_object_15(cfg_map_object[15]), .cfg_place_base_15(cfg_map_base[15]),
        .cfg_place_object_16(cfg_map_object[16]), .cfg_place_base_16(cfg_map_base[16]),
        .cfg_place_object_17(cfg_map_object[17]), .cfg_place_base_17(cfg_map_base[17]),
        .cfg_place_object_18(cfg_map_object[18]), .cfg_place_base_18(cfg_map_base[18]),
        .cfg_place_object_19(cfg_map_object[19]), .cfg_place_base_19(cfg_map_base[19]),
        .cfg_place_object_20(cfg_map_object[20]), .cfg_place_base_20(cfg_map_base[20]),
        .cfg_place_object_21(cfg_map_object[21]), .cfg_place_base_21(cfg_map_base[21]),
        .cfg_place_object_22(cfg_map_object[22]), .cfg_place_base_22(cfg_map_base[22]),
        .cfg_place_object_23(cfg_map_object[23]), .cfg_place_base_23(cfg_map_base[23]),
        .cfg_place_object_24(cfg_map_object[24]), .cfg_place_base_24(cfg_map_base[24]),
        .cfg_place_object_25(cfg_map_object[25]), .cfg_place_base_25(cfg_map_base[25]),
        .cfg_place_object_26(cfg_map_object[26]), .cfg_place_base_26(cfg_map_base[26]),
        .cfg_place_object_27(cfg_map_object[27]), .cfg_place_base_27(cfg_map_base[27]),
        .cfg_place_object_28(cfg_map_object[28]), .cfg_place_base_28(cfg_map_base[28]),
        .cfg_place_object_29(cfg_map_object[29]), .cfg_place_base_29(cfg_map_base[29]),
        .cfg_place_object_30(cfg_map_object[30]), .cfg_place_base_30(cfg_map_base[30]),
        .cfg_place_object_31(cfg_map_object[31]), .cfg_place_base_31(cfg_map_base[31]),
        // Placement is stated through the 32-port surface, which the bridge
        // seeds into its table on every ``clear``; the load path is unused.
        .place_ld_en(1'b0),
        .place_ld_object(32'hffff_ffff),
        .place_ld_base(32'd0),
        .cfg_context_length(32'd0),
        .cfg_kv_plane_rows(32'd0),
        .cfg_generation_policy_id(32'hffff_ffff),
        .cfg_request_max_new_tokens(32'd0),
        .cfg_generated_before(32'd0),
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
        .selected_token(),
        .selected_tie_multiplicity(),
        .selected_eos_reason(),
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

    // -- operand banks; the weight is addressed, never held ---------------
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
                    if (m0_rd_addr < BANK_WORDS) m0_rd_data <= bank_mem[m0_rd_addr];
                    else begin m0_rd_data <= 32'd0; read_oob <= 1'b1; end
                end else begin
                    if (m0_rd_addr < INDEX_WORDS) m0_rd_data <= index_mem[m0_rd_addr];
                    else begin m0_rd_data <= 32'd0; read_oob <= 1'b1; end
                end
            end
            if (m1_rd_en) begin
                if (m1_reads_matmul_weight) begin
                    // 64-bit throughout: this shard's window base plus the
                    // bridge's bounded 32-bit operand offset.  A read past
                    // the declared image is a refusal, never a silent zero.
                    weight_halfword = (window_base >> 1) + {32'd0, m1_rd_addr};
                    if (weight_halfword < (window_bytes >> 1))
                        m1_rd_data <= ot_a3_shard_window_halfword(weight_halfword);
                    else begin m1_rd_data <= 32'd0; read_oob <= 1'b1; end
                end else if (m1_reads_result) begin
                    if (m1_rd_addr < BANK_WORDS) m1_rd_data <= bank_mem[m1_rd_addr];
                    else begin m1_rd_data <= 32'd0; read_oob <= 1'b1; end
                end else begin
                    if (m1_rd_addr < SOURCE_WORDS) m1_rd_data <= source_mem[m1_rd_addr];
                    else begin m1_rd_data <= 32'd0; read_oob <= 1'b1; end
                end
            end
            // Both scale ports are driven on every reduction step and this
            // MATMUL declares both operands unscaled, so zero is the
            // architectural don't-care while a matmul is in flight.  Any
            // other family touching them is still a refusal.
            if ((m2_rd_en || m3_rd_en) && !m1_reads_matmul_weight)
                read_oob <= 1'b1;
            if (out_we) begin
                observed_writes <= observed_writes + 1;
                if (out_addr < BANK_WORDS) bank_mem[out_addr] <= out_data;
                else write_oob <= 1'b1;
            end
        end
    end

    // The write stream, observed at the commit edge: one record per word the
    // engine wrote, in launch order, address AND value.  Nothing inside the
    // design reads it.
    always @(posedge clk) begin
        if (rst_n && out_we && stream_open) begin
            ot_a3_shard_stream_write(out_addr, out_data);
            stream_writes <= stream_writes + 1;
        end
    end

    initial begin
        checks = 0;
        positive_cases = 0;
        compared_words = 0;
        mismatched_words = 0;
        stream_writes = 0;
        stream_open = 1'b0;
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
        window_base = 64'd0;
        for (slot_index = 0; slot_index < MAP_ENTRIES; slot_index = slot_index + 1)
        begin
            cfg_map_object[slot_index] = 32'hffff_ffff;
            cfg_map_base[slot_index] = 32'd0;
        end

        if (!$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("VIEWS=%s", views_path) ||
            !$value$plusargs("DESCRIPTORS=%s", descriptors_path) ||
            !$value$plusargs("INDEX=%s", index_path) ||
            !$value$plusargs("SOURCE=%s", source_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path) ||
            !$value$plusargs("PRELOAD=%s", preload_path) ||
            !$value$plusargs("STREAM=%s", stream_path)) begin
            $fatal(1, "missing ABI3 row-shard vector plusargs");
        end
        $readmemh(cases_path, case_mem);
        $readmemh(views_path, view_mem);
        $readmemh(descriptors_path, desc_mem);
        $readmemh(index_path, index_mem);
        $readmemh(source_path, source_mem);
        $readmemh(expected_path, expected_mem);
        $readmemh(preload_path, preload_mem);

        window_bytes = ot_a3_shard_window_open();
        if (window_bytes == 0) $fatal(1, "the weight window declares no bytes");
        ot_a3_shard_stream_open(stream_path);
        stream_open = 1'b1;

        $display("GEOMETRY cases=%0d case_words=%0d view_slots=%0d view_words=%0d map_entries=%0d descriptor_records=%0d bank_words=%0d expected_words=%0d preload_words=%0d window_bytes=%0d",
                 CASE_COUNT, CASE_WORDS, VIEW_SLOTS, VIEW_WORDS, MAP_ENTRIES,
                 DESC_RECORDS, BANK_WORDS, EXPECTED_WORDS, PRELOAD_WORDS,
                 window_bytes);

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (case_index = 0; case_index < CASE_COUNT;
             case_index = case_index + 1) begin
            base = case_index * CASE_WORDS;
            view_base = case_index * VIEW_SLOTS * VIEW_WORDS;

            cfg_extended_placement_valid = case_mem[base + 24][0];
            window_base = {case_mem[base + 12], case_mem[base + 11]};
            for (slot_index = 0; slot_index < MAP_ENTRIES;
                 slot_index = slot_index + 1) begin
                cfg_map_object[slot_index] = case_mem[base + MAP_BASE + 2*slot_index];
                cfg_map_base[slot_index] = case_mem[base + MAP_BASE + 1 + 2*slot_index];
            end

            @(negedge clk);
            clear = 1'b1;
            @(negedge clk);
            clear = 1'b0;

            // The activation this operator reads.  It is the testbench
            // standing in for the operator that produced it in a longer
            // program; the golden this case is checked against is computed
            // from these same words by the independent scalar reference.
            for (word_index = 0; word_index < case_mem[base + 21];
                 word_index = word_index + 1)
                bank_mem[case_mem[base + 13] + word_index] =
                    preload_mem[case_mem[base + 22] + word_index];

            for (slot_index = 0; slot_index < VIEW_SLOTS;
                 slot_index = slot_index + 1) begin
                if (view_mem[view_base + slot_index*VIEW_WORDS + 0] != 0) begin
                    @(negedge clk);
                    view_valid = 1'b1;
                    view_descriptor_id = view_mem[view_base + slot_index*VIEW_WORDS + 1];
                    view_slot = view_mem[view_base + slot_index*VIEW_WORDS + 2][2:0];
                    view_extent = view_mem[view_base + slot_index*VIEW_WORDS + 3];
                    view_extent_axis = view_mem[view_base + slot_index*VIEW_WORDS + 4][7:0];
                    view_element_offset = {
                        view_mem[view_base + slot_index*VIEW_WORDS + 6],
                        view_mem[view_base + slot_index*VIEW_WORDS + 5]
                    };
                    view_rank = view_mem[view_base + slot_index*VIEW_WORDS + 7][7:0];
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
            if (!issue_ready) $fatal(1, "case %0d timed out", case_index);
            observed_fault = {31'd0, issue_fault};
            observed_trap = issue_trap_class;
            observed_result_count = engine_result_count;
            observed_work_count = engine_work_count;
            @(negedge clk);
            issue_valid = 1'b0;
            @(negedge clk);

            check_equal("fault", observed_fault, case_mem[base + 3]);
            check_equal("trap", observed_trap, case_mem[base + 4]);
            check_equal("response_family", last_response_family, case_mem[base + 0]);
            check_equal("response_sub", last_response_sub, case_mem[base + 1]);
            check_equal("response_descriptor", last_response_descriptor_id,
                        case_mem[base + 2]);
            check_equal("response_index", last_response_index, case_index);
            check_equal("write_beats", observed_writes, case_mem[base + 7]);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("engine_busy", engine_busy, 0);
            if (case_mem[base + 3] == 0) begin
                check_equal("result_count", observed_result_count, case_mem[base + 5]);
                check_equal("work_count", observed_work_count, case_mem[base + 6]);
                check_equal("engine_error", engine_error_code, 0);
                check_equal("real_launches", real_launch_count, 1);
                check_equal("launch_matmul", matmul_launch_count, 1);
                positive_cases = positive_cases + 1;
            end else begin
                check_equal("real_launches", real_launch_count, 0);
                check_equal("launch_matmul", matmul_launch_count, 0);
                check_equal("capability_faults", capability_fault_count,
                            (case_mem[base + 4] == 4) ? 1 : 0);
                check_equal("descriptor_faults", descriptor_fault_count,
                            (case_mem[base + 4] == 3) ? 1 : 0);
            end

            // Every word of this shard's own range, against the independent
            // reference's golden for THAT range.
            for (word_index = 0; word_index < case_mem[base + 9];
                 word_index = word_index + 1) begin
                if (bank_mem[case_mem[base + 8] + word_index] !==
                    expected_mem[case_mem[base + 10] + word_index]) begin
                    mismatched_words = mismatched_words + 1;
                    if (mismatched_words <= 8)
                        $display("MISMATCH case=%0d row=%0d actual=%08x expected=%08x",
                                 case_index,
                                 case_mem[base + 15] + word_index,
                                 bank_mem[case_mem[base + 8] + word_index],
                                 expected_mem[case_mem[base + 10] + word_index]);
                end
                checks = checks + 1;
            end
            compared_words = compared_words + case_mem[base + 9];

            $display("SHARD index=%0d pc=%0d shipped_operator=%0d shard_operator=%0d first_row=%0d row_count=%0d declared_extent=%0d fault=%0d trap=%0d result=%0d work=%0d writes=%0d compared=%0d verification_cycles=%0d",
                     case_index, case_mem[base + 17], case_mem[base + 18],
                     case_mem[base + 2], case_mem[base + 15],
                     case_mem[base + 19], case_mem[base + 14],
                     observed_fault, observed_trap,
                     observed_result_count, observed_work_count,
                     observed_writes, case_mem[base + 9], timeout_cycles);
            repeat (3) @(posedge clk);
        end

        ot_a3_shard_stream_close();
        if (mismatched_words != 0) begin
            $display("FAIL a3_row_shard mismatched=%0d", mismatched_words);
            $fatal(1);
        end
        $display("PASS a3_row_shard cases=%0d positive=%0d words=%0d mismatched=%0d checks=%0d stream_writes=%0d",
                 CASE_COUNT, positive_cases, compared_words, mismatched_words,
                 checks, stream_writes);
        $finish;
    end
endmodule
