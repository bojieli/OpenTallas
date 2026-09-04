`timescale 1ns/1ps

module tb_a3_qwen_gqa;
    localparam integer CASE_COUNT = 5;
    localparam integer CASE_WORDS = 32;
    localparam integer SOURCE_WORDS = 38912;
    localparam integer OUTPUT_WORDS = 4096;
    localparam integer QUERY_BASE = 0;
    localparam integer KEY_BASE = 4096;
    localparam integer VALUE_BASE = 21504;
    localparam integer LATE_VALUE_ADDR = SOURCE_WORDS - 1;
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
    reg [31:0] source_mem [0:SOURCE_WORDS-1];
    reg [31:0] expected_mem [0:OUTPUT_WORDS-1];
    reg [31:0] observed_mem [0:OUTPUT_WORDS-1];

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
    reg [1023:0] expected_path;

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

    wire mem_req_valid;
    wire mem_req_ready;
    wire [31:0] mem_req_addr;
    reg mem_rsp_valid;
    reg [31:0] mem_rsp_data;
    wire out_valid;
    wire out_ready;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    wire busy;
    wire done;
    wire failed;
    wire [15:0] trap_class;
    wire [7:0] refusal_reason;
    wire [31:0] records_checked;
    wire [31:0] memory_read_count;
    wire [31:0] write_count;
    wire [31:0] score_multiply_count;
    wire [31:0] exponential_count;
    wire [31:0] value_multiply_count;
    wire [31:0] saturation_count;
    wire gqa_executed;

    integer case_index;
    integer base;
    integer word_index;
    integer timeout_cycles;
    integer checks;
    integer observed_writes;
    integer cycle_count;
    integer response_delay;
    integer stall_mode;
    integer mutation;
    reg pending_response;
    reg [31:0] pending_address;
    reg read_oob;
    reg write_oob;
    reg write_after_done;
    reg completion_seen;
    reg held_output;
    reg [31:0] held_address;
    reg [31:0] held_data;
    reg output_stability_error;

    assign mem_req_ready = !pending_response &&
        ((stall_mode == 0) || ((cycle_count % 5) != 1));
    assign out_ready = (stall_mode == 0) ||
        ((cycle_count % 7) != 2 && (cycle_count % 7) != 3);

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

    ot_a3_qwen_gqa_adapter dut (
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
        .operator_record(operator_record), .view0_record(view0_record),
        .view1_record(view1_record), .view2_record(view2_record),
        .view3_record(view3_record), .output_record(output_record),
        .numeric_record(numeric_record), .cfg_position_start(32'd16),
        .cfg_context_length(32'd17), .cfg_query_base(QUERY_BASE),
        .cfg_key_base(KEY_BASE), .cfg_value_base(VALUE_BASE),
        .cfg_output_base(32'd0), .mem_req_valid(mem_req_valid),
        .mem_req_ready(mem_req_ready), .mem_req_addr(mem_req_addr),
        .mem_rsp_valid(mem_rsp_valid), .mem_rsp_data(mem_rsp_data),
        .out_valid(out_valid), .out_ready(out_ready),
        .out_addr(out_addr), .out_data(out_data), .busy(busy),
        .done(done), .failed(failed), .trap_class(trap_class),
        .refusal_reason(refusal_reason), .records_checked(records_checked),
        .memory_read_count(memory_read_count), .write_count(write_count),
        .score_multiply_count(score_multiply_count),
        .exponential_count(exponential_count),
        .value_multiply_count(value_multiply_count),
        .saturation_count(saturation_count), .gqa_executed(gqa_executed)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_rsp_valid <= 1'b0;
            mem_rsp_data <= 0;
            pending_response <= 1'b0;
            pending_address <= 0;
            response_delay <= 0;
            cycle_count <= 0;
            observed_writes <= 0;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            write_after_done <= 1'b0;
            completion_seen <= 1'b0;
            held_output <= 1'b0;
            held_address <= 0;
            held_data <= 0;
            output_stability_error <= 1'b0;
        end else begin
            cycle_count <= cycle_count + 1;
            mem_rsp_valid <= 1'b0;
            if (start) begin
                pending_response <= 1'b0;
                observed_writes <= 0;
                read_oob <= 1'b0;
                write_oob <= 1'b0;
                write_after_done <= 1'b0;
                completion_seen <= 1'b0;
                held_output <= 1'b0;
                output_stability_error <= 1'b0;
            end

            if (mem_req_valid && mem_req_ready) begin
                if (mem_req_addr >= SOURCE_WORDS) begin
                    read_oob <= 1'b1;
                end else begin
                    pending_response <= 1'b1;
                    pending_address <= mem_req_addr;
                    response_delay <= stall_mode == 0
                        ? 0 : ((mem_req_addr ^ cycle_count) % 4);
                end
            end
            if (pending_response) begin
                if (response_delay == 0) begin
                    mem_rsp_valid <= 1'b1;
                    if (mutation == 1 &&
                        pending_address == LATE_VALUE_ADDR &&
                        value_multiply_count == 32'd69631)
                        mem_rsp_data <= 32'h0000_7f80;
                    else
                        mem_rsp_data <= source_mem[pending_address];
                    pending_response <= 1'b0;
                end else begin
                    response_delay <= response_delay - 1;
                end
            end

            if (held_output) begin
                if (!out_valid || out_addr !== held_address ||
                    out_data !== held_data)
                    output_stability_error <= 1'b1;
                if (out_ready)
                    held_output <= 1'b0;
            end
            if (out_valid && !out_ready && !held_output) begin
                held_output <= 1'b1;
                held_address <= out_addr;
                held_data <= out_data;
            end
            if (out_valid && out_ready) begin
                observed_writes <= observed_writes + 1;
                if (completion_seen)
                    write_after_done <= 1'b1;
                if (out_addr >= OUTPUT_WORDS) begin
                    write_oob <= 1'b1;
                end else begin
                    observed_mem[out_addr] <= out_data;
                end
            end
            if (done)
                completion_seen <= 1'b1;
        end
    end

    initial begin
        checks = 0;
        stall_mode = 0;
        mutation = 0;
        instruction_record = 0;
        instruction_index = 0;
        instruction_count = 0;
        operator_descriptor_id = 0;
        view0_descriptor_id = 0;
        view1_descriptor_id = 0;
        view2_descriptor_id = 0;
        view3_descriptor_id = 0;
        output_descriptor_id = 0;
        numeric_descriptor_id = 0;
        expected_object0 = 0;
        expected_object1 = 0;
        expected_object2 = 0;
        expected_object3 = 0;
        expected_output_object = 0;
        operator_record = 0;
        view0_record = 0;
        view1_record = 0;
        view2_record = 0;
        view3_record = 0;
        output_record = 0;
        numeric_record = 0;

        if (!$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("INSTRUCTION=%s", instruction_path) ||
            !$value$plusargs("OPERATOR=%s", operator_path) ||
            !$value$plusargs("VIEW0=%s", view0_path) ||
            !$value$plusargs("VIEW1=%s", view1_path) ||
            !$value$plusargs("VIEW2=%s", view2_path) ||
            !$value$plusargs("VIEW3=%s", view3_path) ||
            !$value$plusargs("OUTPUT=%s", output_path) ||
            !$value$plusargs("NUMERIC=%s", numeric_path) ||
            !$value$plusargs("SOURCE=%s", source_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path)) begin
            $fatal(1, "missing ABI3 Qwen GQA vector plusargs");
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
        $readmemh(source_path, source_mem);
        $readmemh(expected_path, expected_mem);

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
            mutation = case_mem[base + 16];
            stall_mode = case_mem[base + 17];
            operator_record = operator_mem[case_index];
            view0_record = view0_mem[case_index];
            view1_record = view1_mem[case_index];
            view2_record = view2_mem[case_index];
            view3_record = view3_mem[case_index];
            output_record = output_record_mem[case_index];
            numeric_record = numeric_mem[case_index];
            for (word_index = 0; word_index < OUTPUT_WORDS;
                 word_index = word_index + 1)
                observed_mem[word_index] = SENTINEL;

            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            timeout_cycles = 0;
            while (!done && timeout_cycles < 1500000) begin
                @(posedge clk);
                #1;
                timeout_cycles = timeout_cycles + 1;
            end
            if (!done)
                $fatal(1, "case %0d timed out", case_index);

            check_equal("failed", failed, case_mem[base + 18]);
            check_equal("trap", trap_class, case_mem[base + 19]);
            check_equal("refusal", refusal_reason, case_mem[base + 20]);
            check_equal("records", records_checked, case_mem[base + 21]);
            check_equal("memory_reads", memory_read_count, case_mem[base + 22]);
            check_equal("writes", write_count, case_mem[base + 23]);
            check_equal("observed_writes", observed_writes, case_mem[base + 23]);
            check_equal("score_multiplies", score_multiply_count, case_mem[base + 24]);
            check_equal("exponentials", exponential_count, case_mem[base + 25]);
            check_equal("value_multiplies", value_multiply_count, case_mem[base + 26]);
            check_equal("gqa_executed", gqa_executed, case_mem[base + 27]);
            check_equal("saturations", saturation_count, 0);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("write_after_done", write_after_done, 0);
            check_equal("output_stability", output_stability_error, 0);
            check_equal("pending_response", pending_response, 0);
            for (word_index = 0; word_index < OUTPUT_WORDS;
                 word_index = word_index + 1) begin
                if (case_mem[base + 23] != 0)
                    check_equal(
                        "computed_output",
                        observed_mem[word_index], expected_mem[word_index]
                    );
                else
                    check_equal(
                        "atomic_zero_write", observed_mem[word_index], SENTINEL
                    );
            end
            $display(
                "CASE_SUMMARY index=%0d failed=%0d trap=%0d refusal=%0d records=%0d reads=%0d writes=%0d score=%0d exp=%0d value=%0d executed=%0d verification_cycles=%0d",
                case_index, failed, trap_class, refusal_reason,
                records_checked, memory_read_count, write_count,
                score_multiply_count, exponential_count,
                value_multiply_count, gqa_executed, timeout_cycles
            );
            repeat (3) @(posedge clk);
        end
        $display(
            "PASS a3_qwen_gqa cases=%0d positive=2 words=8192 checks=%0d",
            CASE_COUNT, checks
        );
        $finish;
    end
endmodule
