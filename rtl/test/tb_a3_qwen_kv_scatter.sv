`timescale 1ns/1ps

module tb_a3_qwen_kv_scatter;
    localparam integer CASE_COUNT = 12;
    localparam integer CASE_WORDS = 32;
    localparam integer ACTIVE_ROWS = 17;
    localparam integer TRAILING = 1024;
    localparam integer ACTIVE_WORDS = ACTIVE_ROWS * TRAILING;
    localparam integer SOURCE_WORDS = 2 * TRAILING;
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [31:0] SENTINEL = 32'hdead_beef;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] case_mem [0:CASE_COUNT*CASE_WORDS-1];
    reg [255:0] instruction_mem [0:CASE_COUNT-1];
    reg [1535:0] operator_mem [0:CASE_COUNT-1];
    reg [1535:0] view0_mem [0:CASE_COUNT-1];
    reg [1535:0] view1_mem [0:CASE_COUNT-1];
    reg [1535:0] view2_mem [0:CASE_COUNT-1];
    reg [1535:0] view3_mem [0:CASE_COUNT-1];
    reg [1535:0] output_record_mem [0:CASE_COUNT-1];
    reg [1535:0] numeric_mem [0:CASE_COUNT-1];
    reg [31:0] exact_source_mem [0:SOURCE_WORDS-1];
    reg [31:0] prior_mem [0:ACTIVE_WORDS-1];
    reg [31:0] output_mem [0:ACTIVE_WORDS-1];

    reg [1023:0] cases_path;
    reg [1023:0] instruction_path;
    reg [1023:0] operator_path;
    reg [1023:0] view0_path;
    reg [1023:0] view1_path;
    reg [1023:0] view2_path;
    reg [1023:0] view3_path;
    reg [1023:0] output_path;
    reg [1023:0] numeric_path;
    reg [1023:0] source_path;

    reg [255:0] instruction_record;
    reg [31:0] instruction_index;
    reg [31:0] instruction_count;
    reg [31:0] operator_descriptor_id;
    reg [31:0] view0_descriptor_id;
    reg [31:0] view1_descriptor_id;
    reg [31:0] view2_descriptor_id;
    reg [31:0] view3_descriptor_id;
    reg [31:0] output_descriptor_id;
    reg [31:0] numeric_descriptor_id;
    reg [31:0] expected_object0;
    reg [31:0] expected_object1;
    reg [31:0] expected_object2;
    reg [31:0] expected_object3;
    reg [31:0] expected_output_object;
    reg [1535:0] operator_record;
    reg [1535:0] view0_record;
    reg [1535:0] view1_record;
    reg [1535:0] view2_record;
    reg [1535:0] view3_record;
    reg [1535:0] output_record;
    reg [1535:0] numeric_record;
    reg [31:0] cfg_position_start;
    reg [31:0] cfg_context_length;
    reg [31:0] cfg_index_base;
    reg [31:0] cfg_source_base;
    reg [31:0] cfg_prior_base;
    reg [31:0] cfg_output_base;

    wire idx_rd_en;
    wire [31:0] idx_rd_addr;
    reg [31:0] idx_rd_data;
    wire src_rd_en;
    wire [31:0] src_rd_addr;
    reg [31:0] src_rd_data;
    wire out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire busy;
    wire done;
    wire failed;
    wire [15:0] trap_class;
    wire [7:0] refusal_reason;
    wire [31:0] records_checked;
    wire [31:0] moved_elements;
    wire [31:0] indices_checked;
    wire [31:0] write_count;
    wire gqa_boundary;

    integer case_index;
    integer base;
    integer word_index;
    integer timeout_cycles;
    integer verification_cycles;
    integer checks;
    integer observed_writes;
    integer current_plane;
    reg [31:0] current_index;
    reg read_oob;
    reg write_oob;
    reg write_after_done;
    reg completion_seen;
    reg [31:0] expected_word;

    function automatic [31:0] deterministic_prior;
        input integer index;
        input integer plane;
        integer seed;
        begin
            seed = (plane == 0) ? 16'h1357 : 16'h2468;
            deterministic_prior = ((index * 251 + seed) % 16'h7f7e) + 1;
        end
    endfunction

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

    ot_a3_qwen_kv_scatter_adapter dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .instruction_record(instruction_record),
        .instruction_index(instruction_index),
        .instruction_count(instruction_count),
        .operator_descriptor_id(operator_descriptor_id),
        .view0_descriptor_id(view0_descriptor_id),
        .view1_descriptor_id(view1_descriptor_id),
        .view2_descriptor_id(view2_descriptor_id),
        .view3_descriptor_id(view3_descriptor_id),
        .output_descriptor_id(output_descriptor_id),
        .numeric_descriptor_id(numeric_descriptor_id),
        .expected_object0(expected_object0),
        .expected_object1(expected_object1),
        .expected_object2(expected_object2),
        .expected_object3(expected_object3),
        .expected_output_object(expected_output_object),
        .operator_record(operator_record),
        .view0_record(view0_record), .view1_record(view1_record),
        .view2_record(view2_record), .view3_record(view3_record),
        .output_record(output_record), .numeric_record(numeric_record),
        .cfg_position_start(cfg_position_start),
        .cfg_context_length(cfg_context_length),
        .cfg_index_base(cfg_index_base),
        .cfg_source_base(cfg_source_base),
        .cfg_prior_base(cfg_prior_base),
        .cfg_output_base(cfg_output_base),
        .idx_rd_en(idx_rd_en), .idx_rd_addr(idx_rd_addr),
        .idx_rd_data(idx_rd_data),
        .src_rd_en(src_rd_en), .src_rd_addr(src_rd_addr),
        .src_rd_data(src_rd_data),
        .out_we(out_we), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .failed(failed),
        .trap_class(trap_class), .refusal_reason(refusal_reason),
        .records_checked(records_checked),
        .moved_elements(moved_elements),
        .indices_checked(indices_checked), .write_count(write_count),
        .gqa_boundary(gqa_boundary)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            idx_rd_data <= 32'd0;
            src_rd_data <= 32'd0;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            observed_writes <= 0;
            write_after_done <= 1'b0;
            completion_seen <= 1'b0;
        end else begin
            if (start) begin
                read_oob <= 1'b0;
                write_oob <= 1'b0;
                observed_writes <= 0;
                write_after_done <= 1'b0;
                completion_seen <= 1'b0;
            end
            if (idx_rd_en) begin
                if (idx_rd_addr != 0) begin
                    idx_rd_data <= 32'd0;
                    read_oob <= 1'b1;
                end else begin
                    idx_rd_data <= current_index;
                end
            end
            if (src_rd_en) begin
                if (src_rd_addr < ACTIVE_WORDS) begin
                    src_rd_data <= prior_mem[src_rd_addr];
                end else if (
                    (src_rd_addr >= ACTIVE_WORDS) &&
                    (src_rd_addr < ACTIVE_WORDS + SOURCE_WORDS)
                ) begin
                    src_rd_data <= exact_source_mem[src_rd_addr - ACTIVE_WORDS];
                end else begin
                    src_rd_data <= 32'd0;
                    read_oob <= 1'b1;
                end
            end
            if (out_we) begin
                observed_writes <= observed_writes + 1;
                if (completion_seen)
                    write_after_done <= 1'b1;
                if (out_addr >= ACTIVE_WORDS) begin
                    write_oob <= 1'b1;
                end else begin
                    output_mem[out_addr] <= out_data;
                end
            end
            if (done)
                completion_seen <= 1'b1;
        end
    end

    initial begin
        checks = 0;
        instruction_record = 256'd0;
        instruction_index = 32'd0;
        instruction_count = 32'd0;
        operator_descriptor_id = NO_ID;
        view0_descriptor_id = NO_ID;
        view1_descriptor_id = NO_ID;
        view2_descriptor_id = NO_ID;
        view3_descriptor_id = NO_ID;
        output_descriptor_id = NO_ID;
        numeric_descriptor_id = NO_ID;
        expected_object0 = NO_ID;
        expected_object1 = NO_ID;
        expected_object2 = NO_ID;
        expected_object3 = NO_ID;
        expected_output_object = NO_ID;
        operator_record = 1536'd0;
        view0_record = 1536'd0;
        view1_record = 1536'd0;
        view2_record = 1536'd0;
        view3_record = 1536'd0;
        output_record = 1536'd0;
        numeric_record = 1536'd0;
        cfg_position_start = 32'd0;
        cfg_context_length = 32'd0;
        cfg_index_base = 32'd0;
        cfg_source_base = 32'd0;
        cfg_prior_base = 32'd0;
        cfg_output_base = 32'd0;
        current_index = 32'd0;
        current_plane = 0;

        if (!$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("INSTRUCTION=%s", instruction_path) ||
            !$value$plusargs("OPERATOR=%s", operator_path) ||
            !$value$plusargs("VIEW0=%s", view0_path) ||
            !$value$plusargs("VIEW1=%s", view1_path) ||
            !$value$plusargs("VIEW2=%s", view2_path) ||
            !$value$plusargs("VIEW3=%s", view3_path) ||
            !$value$plusargs("OUTPUT=%s", output_path) ||
            !$value$plusargs("NUMERIC=%s", numeric_path) ||
            !$value$plusargs("SOURCE=%s", source_path)) begin
            $fatal(1, "missing ABI3 Qwen KV-scatter vector plusargs");
        end
        $readmemh(cases_path, case_mem);
        $readmemh(instruction_path, instruction_mem);
        $readmemh(operator_path, operator_mem);
        $readmemh(view0_path, view0_mem);
        $readmemh(view1_path, view1_mem);
        $readmemh(view2_path, view2_mem);
        $readmemh(view3_path, view3_mem);
        $readmemh(output_path, output_record_mem);
        $readmemh(numeric_path, numeric_mem);
        $readmemh(source_path, exact_source_mem);

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        for (case_index = 0; case_index < CASE_COUNT;
             case_index = case_index + 1) begin
            base = case_index * CASE_WORDS;
            instruction_record = instruction_mem[case_index];
            instruction_index = case_mem[base + 0];
            instruction_count = case_mem[base + 1];
            operator_descriptor_id = case_mem[base + 2];
            view0_descriptor_id = case_mem[base + 3];
            view1_descriptor_id = case_mem[base + 4];
            view2_descriptor_id = case_mem[base + 5];
            view3_descriptor_id = case_mem[base + 6];
            output_descriptor_id = case_mem[base + 7];
            numeric_descriptor_id = case_mem[base + 8];
            expected_object0 = case_mem[base + 9];
            expected_object1 = case_mem[base + 10];
            expected_object2 = case_mem[base + 11];
            expected_object3 = case_mem[base + 12];
            expected_output_object = case_mem[base + 13];
            cfg_position_start = case_mem[base + 14];
            cfg_context_length = case_mem[base + 15];
            current_index = case_mem[base + 16];
            current_plane = case_mem[base + 17];
            operator_record = operator_mem[case_index];
            view0_record = view0_mem[case_index];
            view1_record = view1_mem[case_index];
            view2_record = view2_mem[case_index];
            view3_record = view3_mem[case_index];
            output_record = output_record_mem[case_index];
            numeric_record = numeric_mem[case_index];
            cfg_index_base = 0;
            cfg_source_base = ACTIVE_WORDS + current_plane * TRAILING;
            cfg_prior_base = 0;
            cfg_output_base = 0;

            for (word_index = 0; word_index < ACTIVE_WORDS;
                 word_index = word_index + 1) begin
                prior_mem[word_index] = deterministic_prior(
                    word_index, current_plane
                );
                output_mem[word_index] = SENTINEL;
            end

            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            timeout_cycles = 0;
            while (!done && timeout_cycles < 200000) begin
                @(posedge clk);
                #1;
                timeout_cycles = timeout_cycles + 1;
            end
            if (!done)
                $fatal(1, "case %0d timed out", case_index);
            verification_cycles = timeout_cycles;

            check_equal("failed", failed, case_mem[base + 18]);
            check_equal("trap_class", trap_class, case_mem[base + 19]);
            check_equal(
                "refusal_reason", refusal_reason, case_mem[base + 20]
            );
            check_equal(
                "records_checked", records_checked, case_mem[base + 21]
            );
            check_equal(
                "moved_elements", moved_elements, case_mem[base + 22]
            );
            check_equal(
                "indices_checked", indices_checked, case_mem[base + 23]
            );
            check_equal("write_count", write_count, case_mem[base + 24]);
            check_equal("observed_writes", observed_writes, case_mem[base + 24]);
            check_equal("gqa_boundary", gqa_boundary, case_mem[base + 25]);
            check_equal("busy_at_done", busy, 0);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("write_after_done", write_after_done, 0);

            for (word_index = 0; word_index < ACTIVE_WORDS;
                 word_index = word_index + 1) begin
                if (case_mem[base + 26]) begin
                    if ((word_index / TRAILING) == 16)
                        expected_word = exact_source_mem[
                            current_plane * TRAILING +
                            (word_index % TRAILING)
                        ];
                    else
                        expected_word = deterministic_prior(
                            word_index, current_plane
                        );
                end else begin
                    expected_word = SENTINEL;
                end
                check_equal("output_word", output_mem[word_index], expected_word);
            end

            $display(
                "CASE_SUMMARY index=%0d failed=%0d trap=%0d refusal=%0d records=%0d moved=%0d checked=%0d writes=%0d gqa=%0d verification_cycles=%0d",
                case_index, failed, trap_class, refusal_reason,
                records_checked, moved_elements, indices_checked,
                write_count, gqa_boundary, verification_cycles
            );
            @(posedge clk);
            #1;
            check_equal("done_pulse", done, 0);
            check_equal("post_done_write", out_we, 0);
        end

        $display(
            "PASS a3_qwen_kv_scatter cases=%0d scatters=4 next_pc=38 checks=%0d",
            CASE_COUNT, checks
        );
        $finish;
    end
endmodule
