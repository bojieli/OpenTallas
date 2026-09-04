`timescale 1ns/1ps

module tb_a3_qwen_output_projection;
    localparam integer CASE_COUNT = 6;
    localparam integer CASE_WORDS = 32;
    localparam integer WIDTH = 4096;
    localparam integer WEIGHT_WORDS = WIDTH * WIDTH;
    localparam integer WEIGHT_BYTES = 2 * WEIGHT_WORDS;
    localparam integer WEIGHT_BASE = WIDTH;
    localparam integer LAST_WEIGHT_ADDR = WEIGHT_BASE + WEIGHT_WORDS - 1;
    localparam integer CHUNK_BYTES = 65536;
    localparam integer CHUNK_WORDS = CHUNK_BYTES / 2;
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
    reg [1535:0] output_record_mem [0:CASE_COUNT-1];
    reg [1535:0] numeric_mem [0:CASE_COUNT-1];
    reg [31:0] input_mem [0:WIDTH-1];
    reg [31:0] expected_mem [0:WIDTH-1];
    reg [31:0] observed_mem [0:WIDTH-1];
    reg [7:0] weight_chunk [0:CHUNK_BYTES-1];

    reg [4095:0] cases_path;
    reg [4095:0] instruction_path;
    reg [4095:0] operator_path;
    reg [4095:0] view0_path;
    reg [4095:0] view1_path;
    reg [4095:0] output_path;
    reg [4095:0] numeric_path;
    reg [4095:0] input_path;
    reg [4095:0] expected_path;
    reg [4095:0] weight_path;

    reg [255:0] instruction_record;
    reg [31:0] instruction_index;
    reg [31:0] instruction_count;
    reg [31:0] operator_descriptor_id;
    reg [31:0] view0_descriptor_id;
    reg [31:0] view1_descriptor_id;
    reg [31:0] output_descriptor_id;
    reg [31:0] numeric_descriptor_id;
    reg [31:0] expected_object0;
    reg [31:0] expected_object1;
    reg [31:0] expected_output_object;
    reg [1535:0] operator_record;
    reg [1535:0] view0_record;
    reg [1535:0] view1_record;
    reg [1535:0] output_record;
    reg [1535:0] numeric_record;
    reg [31:0] cfg_position_start;
    reg [31:0] cfg_context_length;
    reg [31:0] cfg_input_base;
    reg [31:0] cfg_weight_base;
    reg [31:0] cfg_output_base;

    wire mem_req_valid;
    wire mem_req_ready;
    wire [31:0] mem_req_addr;
    wire mem_rsp_valid;
    wire [31:0] mem_rsp_data;
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
    wire [31:0] input_read_count;
    wire [31:0] weight_read_count;
    wire [31:0] mac_count;
    wire [31:0] write_count;
    wire [31:0] saturation_count;
    wire projection_executed;

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
    integer weight_file;
    integer weight_bytes_read;
    integer weight_bytes_loaded;
    integer loaded_chunk;
    integer requested_chunk;
    integer weight_word_offset;
    integer chunk_word_offset;
    reg pending_response;
    reg [31:0] pending_data;
    reg read_oob;
    reg write_oob;
    reg read_before_admission;
    reg read_after_done;
    reg write_after_done;
    reg completion_seen;
    reg held_request;
    reg [31:0] held_request_address;
    reg request_stability_error;
    reg held_output;
    reg [31:0] held_output_address;
    reg [31:0] held_output_data;
    reg output_stability_error;

    assign mem_rsp_valid = pending_response && response_delay == 0;
    assign mem_rsp_data = pending_data;
    assign mem_req_ready = (!pending_response || mem_rsp_valid) &&
        ((stall_mode == 0) || ((cycle_count % 257) != 31));
    assign out_ready = (stall_mode == 0) ||
        (((cycle_count % 19) != 5) && ((cycle_count % 19) != 6));

    task automatic check_equal;
        input [2047:0] label;
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

    ot_a3_qwen_output_projection_adapter dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .instruction_record(instruction_record),
        .instruction_index(instruction_index),
        .instruction_count(instruction_count),
        .operator_descriptor_id(operator_descriptor_id),
        .view0_descriptor_id(view0_descriptor_id),
        .view1_descriptor_id(view1_descriptor_id),
        .output_descriptor_id(output_descriptor_id),
        .numeric_descriptor_id(numeric_descriptor_id),
        .expected_object0(expected_object0),
        .expected_object1(expected_object1),
        .expected_output_object(expected_output_object),
        .operator_record(operator_record), .view0_record(view0_record),
        .view1_record(view1_record), .output_record(output_record),
        .numeric_record(numeric_record),
        .cfg_position_start(cfg_position_start),
        .cfg_context_length(cfg_context_length),
        .cfg_input_base(cfg_input_base),
        .cfg_weight_base(cfg_weight_base),
        .cfg_output_base(cfg_output_base),
        .mem_req_valid(mem_req_valid), .mem_req_ready(mem_req_ready),
        .mem_req_addr(mem_req_addr), .mem_rsp_valid(mem_rsp_valid),
        .mem_rsp_data(mem_rsp_data), .out_valid(out_valid),
        .out_ready(out_ready), .out_addr(out_addr), .out_data(out_data),
        .busy(busy), .done(done), .failed(failed),
        .trap_class(trap_class), .refusal_reason(refusal_reason),
        .records_checked(records_checked),
        .memory_read_count(memory_read_count),
        .input_read_count(input_read_count),
        .weight_read_count(weight_read_count), .mac_count(mac_count),
        .write_count(write_count), .saturation_count(saturation_count),
        .projection_executed(projection_executed)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pending_response <= 1'b0;
            pending_data <= 0;
            response_delay <= 0;
            cycle_count <= 0;
            observed_writes <= 0;
            weight_bytes_loaded <= 0;
            loaded_chunk <= -1;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            read_before_admission <= 1'b0;
            read_after_done <= 1'b0;
            write_after_done <= 1'b0;
            completion_seen <= 1'b0;
            held_request <= 1'b0;
            held_request_address <= 0;
            request_stability_error <= 1'b0;
            held_output <= 1'b0;
            held_output_address <= 0;
            held_output_data <= 0;
            output_stability_error <= 1'b0;
        end else if (start) begin
            pending_response <= 1'b0;
            pending_data <= 0;
            response_delay <= 0;
            cycle_count <= 0;
            observed_writes <= 0;
            weight_bytes_loaded <= 0;
            loaded_chunk <= -1;
            read_oob <= 1'b0;
            write_oob <= 1'b0;
            read_before_admission <= 1'b0;
            read_after_done <= 1'b0;
            write_after_done <= 1'b0;
            completion_seen <= 1'b0;
            held_request <= 1'b0;
            request_stability_error <= 1'b0;
            held_output <= 1'b0;
            output_stability_error <= 1'b0;
        end else begin
            cycle_count <= cycle_count + 1;

            if (pending_response && response_delay != 0)
                response_delay <= response_delay - 1;
            if (mem_rsp_valid)
                pending_response <= 1'b0;

            if (held_request) begin
                if (!mem_req_valid || mem_req_addr !== held_request_address)
                    request_stability_error <= 1'b1;
                if (mem_req_ready)
                    held_request <= 1'b0;
            end
            if (mem_req_valid && !mem_req_ready && !held_request) begin
                held_request <= 1'b1;
                held_request_address <= mem_req_addr;
            end

            if (mem_req_valid && records_checked != 32'd5)
                read_before_admission <= 1'b1;
            if (mem_req_valid && completion_seen)
                read_after_done <= 1'b1;

            if (mem_req_valid && mem_req_ready) begin
                pending_response <= 1'b1;
                if (stall_mode == 0)
                    response_delay <= 0;
                else if (((mem_req_addr ^ cycle_count) % 4093) == 127)
                    response_delay <= 2;
                else
                    response_delay <= 0;

                if (mem_req_addr < WIDTH) begin
                    pending_data <= input_mem[mem_req_addr];
                end else if (mem_req_addr <= LAST_WEIGHT_ADDR) begin
                    weight_word_offset = mem_req_addr - WEIGHT_BASE;
                    requested_chunk = weight_word_offset / CHUNK_WORDS;
                    chunk_word_offset = weight_word_offset % CHUNK_WORDS;
                    if (requested_chunk != loaded_chunk) begin
                        if (requested_chunk != loaded_chunk + 1)
                            $fatal(1, "nonsequential checkpoint chunk request");
                        weight_bytes_read = $fread(
                            weight_chunk, weight_file, 0, CHUNK_BYTES
                        );
                        if (weight_bytes_read != CHUNK_BYTES)
                            $fatal(
                                1,
                                "checkpoint chunk %0d has %0d bytes, expected %0d",
                                requested_chunk, weight_bytes_read, CHUNK_BYTES
                            );
                        loaded_chunk = requested_chunk;
                        weight_bytes_loaded <=
                            weight_bytes_loaded + weight_bytes_read;
                    end
                    if (mutation == 1 && mem_req_addr == LAST_WEIGHT_ADDR)
                        pending_data <= 32'h0000_7f80;
                    else
                        pending_data <= {
                            16'd0,
                            weight_chunk[2*chunk_word_offset + 1],
                            weight_chunk[2*chunk_word_offset]
                        };
                end else begin
                    read_oob <= 1'b1;
                    pending_data <= 0;
                end
            end

            if (held_output) begin
                if (!out_valid || out_addr !== held_output_address ||
                    out_data !== held_output_data)
                    output_stability_error <= 1'b1;
                if (out_ready)
                    held_output <= 1'b0;
            end
            if (out_valid && !out_ready && !held_output) begin
                held_output <= 1'b1;
                held_output_address <= out_addr;
                held_output_data <= out_data;
            end
            if (out_valid && completion_seen)
                write_after_done <= 1'b1;
            if (out_valid && out_ready) begin
                observed_writes <= observed_writes + 1;
                if (out_addr >= WIDTH) begin
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
        weight_file = 0;
        instruction_record = 0;
        instruction_index = 0;
        instruction_count = 0;
        operator_descriptor_id = 0;
        view0_descriptor_id = 0;
        view1_descriptor_id = 0;
        output_descriptor_id = 0;
        numeric_descriptor_id = 0;
        expected_object0 = 0;
        expected_object1 = 0;
        expected_output_object = 0;
        operator_record = 0;
        view0_record = 0;
        view1_record = 0;
        output_record = 0;
        numeric_record = 0;
        cfg_position_start = 0;
        cfg_context_length = 0;
        cfg_input_base = 0;
        cfg_weight_base = 0;
        cfg_output_base = 0;

        if (!$value$plusargs("CASES=%s", cases_path) ||
            !$value$plusargs("INSTRUCTION=%s", instruction_path) ||
            !$value$plusargs("OPERATOR=%s", operator_path) ||
            !$value$plusargs("VIEW0=%s", view0_path) ||
            !$value$plusargs("VIEW1=%s", view1_path) ||
            !$value$plusargs("OUTPUT=%s", output_path) ||
            !$value$plusargs("NUMERIC=%s", numeric_path) ||
            !$value$plusargs("INPUT=%s", input_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path) ||
            !$value$plusargs("WEIGHT=%s", weight_path)) begin
            $fatal(1, "missing ABI3 Qwen output-projection plusargs");
        end
        $readmemh(cases_path, case_mem);
        $readmemh(instruction_path, instruction_mem);
        $readmemh(operator_path, operator_mem);
        $readmemh(view0_path, view0_mem);
        $readmemh(view1_path, view1_mem);
        $readmemh(output_path, output_record_mem);
        $readmemh(numeric_path, numeric_mem);
        $readmemh(input_path, input_mem);
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
            output_descriptor_id = case_mem[base + 5];
            numeric_descriptor_id = case_mem[base + 6];
            expected_object0 = case_mem[base + 7];
            expected_object1 = case_mem[base + 8];
            expected_output_object = case_mem[base + 9];
            cfg_position_start = case_mem[base + 10];
            cfg_context_length = case_mem[base + 11];
            mutation = case_mem[base + 12];
            stall_mode = case_mem[base + 13];
            cfg_input_base = case_mem[base + 27];
            cfg_weight_base = case_mem[base + 28];
            cfg_output_base = case_mem[base + 29];
            operator_record = operator_mem[case_index];
            view0_record = view0_mem[case_index];
            view1_record = view1_mem[case_index];
            output_record = output_record_mem[case_index];
            numeric_record = numeric_mem[case_index];
            for (word_index = 0; word_index < WIDTH;
                 word_index = word_index + 1)
                observed_mem[word_index] = SENTINEL;

            if (weight_file != 0)
                $fclose(weight_file);
            weight_file = $fopen(weight_path, "rb");
            if (weight_file == 0)
                $fatal(1, "cannot open staged checkpoint weight");

            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            timeout_cycles = 0;
            while (!done && timeout_cycles < 25000000) begin
                @(posedge clk);
                #1;
                timeout_cycles = timeout_cycles + 1;
            end
            if (!done)
                $fatal(1, "case %0d timed out", case_index);
            repeat (3) begin
                @(posedge clk);
                #1;
            end

            $display(
                "CASE_OBSERVED index=%0d failed=%0d trap=%0d refusal=%0d records=%0d reads=%0d input=%0d weights=%0d macs=%0d writes=%0d executed=%0d verification_cycles=%0d",
                case_index, failed, trap_class, refusal_reason,
                records_checked, memory_read_count, input_read_count,
                weight_read_count, mac_count, write_count,
                projection_executed, timeout_cycles
            );
            check_equal("failed", failed, case_mem[base + 14]);
            check_equal("trap", trap_class, case_mem[base + 15]);
            check_equal("refusal", refusal_reason, case_mem[base + 16]);
            check_equal("records", records_checked, case_mem[base + 17]);
            check_equal("memory_reads", memory_read_count, case_mem[base + 18]);
            check_equal("input_reads", input_read_count, case_mem[base + 19]);
            check_equal("weight_reads", weight_read_count, case_mem[base + 20]);
            check_equal("macs", mac_count, case_mem[base + 21]);
            check_equal("writes", write_count, case_mem[base + 22]);
            check_equal("observed_writes", observed_writes, case_mem[base + 22]);
            check_equal("saturations", saturation_count, case_mem[base + 23]);
            check_equal("projection_executed", projection_executed,
                        case_mem[base + 24]);
            check_equal("read_oob", read_oob, 0);
            check_equal("write_oob", write_oob, 0);
            check_equal("read_before_admission", read_before_admission, 0);
            check_equal("read_after_done", read_after_done, 0);
            check_equal("write_after_done", write_after_done, 0);
            check_equal("request_stability", request_stability_error, 0);
            check_equal("output_stability", output_stability_error, 0);
            check_equal("pending_response", pending_response, 0);
            if (case_mem[base + 18] != 0)
                check_equal("checkpoint_bytes_loaded", weight_bytes_loaded,
                            WEIGHT_BYTES);
            else
                check_equal("checkpoint_bytes_loaded", weight_bytes_loaded, 0);

            for (word_index = 0; word_index < WIDTH;
                 word_index = word_index + 1) begin
                if (case_mem[base + 25] != 0)
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
                "CASE_SUMMARY index=%0d failed=%0d trap=%0d refusal=%0d records=%0d reads=%0d input=%0d weights=%0d macs=%0d writes=%0d executed=%0d verification_cycles=%0d",
                case_index, failed, trap_class, refusal_reason,
                records_checked, memory_read_count, input_read_count,
                weight_read_count, mac_count, write_count,
                projection_executed, timeout_cycles
            );
            repeat (2) @(posedge clk);
        end
        if (weight_file != 0)
            $fclose(weight_file);
        $display(
            "PASS a3_qwen_output_projection cases=%0d positive=2 words=8192 checks=%0d",
            CASE_COUNT, checks
        );
        $finish;
    end
endmodule
