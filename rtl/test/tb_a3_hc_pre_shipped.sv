`timescale 1ns/1ps
// Focused dual-simulator checker for shipped ABI 3.0 -> HC_PRE integration.
//
// The two positive cases execute the real DeepSeek ROM/HBM instruction and
// descriptor images from PC6 through the first HC_PRE.  Earlier issues are a
// recording completion service; HC_PRE alone uses real raw descriptor reads,
// the sequencer's six resolved views, delayed/backpressured tensor-memory
// responses, exact arithmetic and backpressured output commits.  The retained
// checkpoint contents are preloaded at that operator boundary, so this is not
// a full-prefix live-buffer provenance claim and not a token/TPOT result.
module tb_a3_hc_pre_shipped;
    localparam integer PROGRAM_WORDS = 4096;
    localparam integer DESC_WORDS = 8192;
    localparam integer SYMBOL_WORDS = 2048;
    localparam integer CASE_WORDS = 320;
    localparam integer CASE_STRIDE = 40;
    localparam integer WIDTH = 16384;
    localparam integer FIELDS = 24;
    localparam integer EXPECTED_WORDS = 74;
    localparam integer RUN_GUARD = 1800000;

    reg [255:0] program_mem [0:PROGRAM_WORDS-1];
    reg [1535:0] descriptor_mem [0:DESC_WORDS-1];
    reg [31:0] symbol_mem [0:SYMBOL_WORDS-1];
    reg [31:0] case_mem [0:CASE_WORDS-1];
    reg [15:0] hidden_mem [0:WIDTH-1];
    reg [31:0] projection_mem [0:FIELDS*WIDTH-1];
    reg [31:0] base_mem [0:FIELDS-1];
    reg [31:0] scale_mem [0:2];
    reg [31:0] expected_mem [0:EXPECTED_WORDS-1];

    reg [2047:0] program_path;
    reg [2047:0] descriptor_path;
    reg [2047:0] symbol_path;
    reg [2047:0] case_path;
    reg [2047:0] hidden_path;
    reg [2047:0] projection_path;
    reg [2047:0] base_path;
    reg [2047:0] scale_path;
    reg [2047:0] expected_path;
    initial begin
        if (!$value$plusargs("PROGRAM=%s", program_path) ||
            !$value$plusargs("DESCRIPTOR=%s", descriptor_path) ||
            !$value$plusargs("SYMBOL=%s", symbol_path) ||
            !$value$plusargs("CASE=%s", case_path) ||
            !$value$plusargs("HIDDEN=%s", hidden_path) ||
            !$value$plusargs("PROJECTION=%s", projection_path) ||
            !$value$plusargs("BASE=%s", base_path) ||
            !$value$plusargs("SCALE=%s", scale_path) ||
            !$value$plusargs("EXPECTED=%s", expected_path))
            $fatal(1, "missing shipped HC_PRE vector path");
        $readmemh(program_path, program_mem);
        $readmemh(descriptor_path, descriptor_mem);
        $readmemh(symbol_path, symbol_mem);
        $readmemh(case_path, case_mem);
        $readmemh(hidden_path, hidden_mem);
        $readmemh(projection_path, projection_mem);
        $readmemh(base_path, base_mem);
        $readmemh(scale_path, scale_mem);
        $readmemh(expected_path, expected_mem);
    end

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg start = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] cfg_program_base = 0;
    reg [31:0] cfg_instruction_count = 0;
    reg [31:0] cfg_entry_pc = 0;
    reg [31:0] cfg_desc_base = 0;
    reg [31:0] cfg_desc_count = 0;
    reg [31:0] cfg_symbol_base = 0;
    reg [31:0] cfg_symbol_mask = 0;
    reg [63:0] cfg_max_retired_work = 0;
    reg [31:0] cfg_state_count = 0;

    wire imem_req;
    wire [31:0] imem_index;
    reg imem_valid = 0;
    reg [255:0] imem_data = 0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            imem_valid <= 1'b0;
            imem_data <= 0;
        end else begin
            imem_valid <= imem_req;
            if (imem_req)
                imem_data <= imem_index < PROGRAM_WORDS
                    ? program_mem[imem_index] : 0;
        end
    end

    wire seq_desc_req;
    wire [31:0] seq_desc_id;
    reg seq_desc_valid = 0;
    reg seq_desc_fault = 0;
    reg [1535:0] seq_desc_data = 0;
    wire [32:0] seq_desc_absolute =
        {1'b0, cfg_desc_base} + {1'b0, seq_desc_id};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            seq_desc_valid <= 1'b0;
            seq_desc_fault <= 1'b0;
            seq_desc_data <= 0;
        end else begin
            seq_desc_valid <= seq_desc_req;
            if (seq_desc_req) begin
                seq_desc_fault <= (seq_desc_id >= cfg_desc_count) ||
                    (seq_desc_absolute >= DESC_WORDS);
                seq_desc_data <= ((seq_desc_id < cfg_desc_count) &&
                                  (seq_desc_absolute < DESC_WORDS))
                    ? descriptor_mem[seq_desc_absolute[12:0]] : 0;
            end
        end
    end

    reg inject_descriptor_corruption = 0;
    wire hc_desc_req;
    wire [31:0] hc_desc_id;
    reg hc_desc_valid = 0;
    reg hc_desc_fault = 0;
    reg [1535:0] hc_desc_data = 0;
    wire [32:0] hc_desc_absolute =
        {1'b0, cfg_desc_base} + {1'b0, hc_desc_id};
    wire [31:0] selected_numeric_descriptor =
        current_profile == 0 ? 32'd378 : 32'd543;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hc_desc_valid <= 1'b0;
            hc_desc_fault <= 1'b0;
            hc_desc_data <= 0;
        end else begin
            hc_desc_valid <= hc_desc_req;
            if (hc_desc_req) begin
                hc_desc_fault <= (hc_desc_id >= cfg_desc_count) ||
                    (hc_desc_absolute >= DESC_WORDS);
                if ((hc_desc_id < cfg_desc_count) &&
                    (hc_desc_absolute < DESC_WORDS)) begin
                    hc_desc_data <= descriptor_mem[hc_desc_absolute[12:0]];
                    if (inject_descriptor_corruption &&
                        hc_desc_id == selected_numeric_descriptor)
                        hc_desc_data[512] <=
                            ~descriptor_mem[hc_desc_absolute[12:0]][512];
                end else begin
                    hc_desc_data <= 0;
                end
            end
        end
    end

    wire [3:0] sym_index;
    wire [31:0] symbol_absolute = cfg_symbol_base + {28'd0, sym_index};
    wire [31:0] sym_value = symbol_absolute < SYMBOL_WORDS
        ? symbol_mem[symbol_absolute] : 0;
    wire sym_bound = cfg_symbol_mask[sym_index];

    wire predicate_read_req;
    wire [31:0] predicate_read_object_id;
    wire [31:0] predicate_read_element_index;

    wire fallback_issue_valid;
    wire [7:0] fallback_issue_family;
    wire [7:0] fallback_issue_sub;
    wire [31:0] fallback_issue_descriptor_id;
    wire [31:0] fallback_issue_index;
    reg hc_succeeded = 0;
    wire fallback_issue_ready = 1'b1;
    wire fallback_issue_fault = hc_succeeded;
    wire [15:0] fallback_issue_trap_class = hc_succeeded ? 16'd4 : 16'd0;

    wire mem_read_valid;
    wire mem_read_ready;
    wire [31:0] mem_read_object_id;
    wire [63:0] mem_read_element_offset;
    wire [7:0] mem_read_dtype;
    wire [4:0] mem_read_element_count;
    wire [31:0] mem_read_element_stride;
    reg mem_response_valid = 0;
    wire mem_response_ready;
    reg [255:0] mem_response_data = 0;
    reg mem_response_error = 0;
    wire mem_write_valid;
    wire mem_write_ready;
    wire [31:0] mem_write_object_id;
    wire [63:0] mem_write_element_offset;
    wire [31:0] mem_write_data;

    wire busy;
    wire done;
    wire complete;
    wire trapped;
    wire [15:0] trap_class;
    wire [31:0] first_fault_instruction;
    wire [31:0] count_fetched;
    wire [31:0] count_retired;
    wire [31:0] count_predicated_off;
    wire [31:0] count_issued;
    wire [31:0] count_branches;
    wire [31:0] count_loop_iterations;
    wire [31:0] count_wait_events;
    wire [31:0] count_signals;
    wire [31:0] count_views_resolved;
    wire event_signal_error;
    wire state_apply_overflow;
    wire hc_issue_response;
    wire hc_issue_fault;
    wire [15:0] hc_issue_trap_class;
    wire [31:0] hc_descriptor_records_checked;
    wire [31:0] hc_resolved_views_captured;
    wire [31:0] hc_memory_read_count;
    wire [31:0] hc_memory_request_stall_cycles;
    wire [31:0] hc_memory_response_stall_cycles;
    wire [31:0] hc_output_write_count;
    wire [31:0] hc_output_write_stall_cycles;
    wire hc_arithmetic_executed;
    wire [7:0] hc_last_error_code;
    wire [31:0] hc_arithmetic_square_count;
    wire [31:0] hc_arithmetic_reduction_add_count;
    wire [31:0] hc_arithmetic_fma_count;

    ot_a3_hc_pre_sequencer_bridge dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .imem_req(imem_req), .imem_index(imem_index),
        .imem_valid(imem_valid), .imem_data(imem_data),
        .seq_desc_req(seq_desc_req), .seq_desc_id(seq_desc_id),
        .seq_desc_valid(seq_desc_valid), .seq_desc_fault(seq_desc_fault),
        .seq_desc_data(seq_desc_data), .hc_desc_req(hc_desc_req),
        .hc_desc_id(hc_desc_id), .hc_desc_valid(hc_desc_valid),
        .hc_desc_fault(hc_desc_fault), .hc_desc_data(hc_desc_data),
        .sym_index(sym_index), .sym_value(sym_value), .sym_bound(sym_bound),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(1'b0), .predicate_read_value(1'b0),
        .predicate_read_trap_class(16'd0),
        .fallback_issue_valid(fallback_issue_valid),
        .fallback_issue_ready(fallback_issue_ready),
        .fallback_issue_fault(fallback_issue_fault),
        .fallback_issue_trap_class(fallback_issue_trap_class),
        .fallback_issue_family(fallback_issue_family),
        .fallback_issue_sub(fallback_issue_sub),
        .fallback_issue_descriptor_id(fallback_issue_descriptor_id),
        .fallback_issue_index(fallback_issue_index),
        .mem_read_valid(mem_read_valid), .mem_read_ready(mem_read_ready),
        .mem_read_object_id(mem_read_object_id),
        .mem_read_element_offset(mem_read_element_offset),
        .mem_read_dtype(mem_read_dtype),
        .mem_read_element_count(mem_read_element_count),
        .mem_read_element_stride(mem_read_element_stride),
        .mem_response_valid(mem_response_valid),
        .mem_response_ready(mem_response_ready),
        .mem_response_data(mem_response_data),
        .mem_response_error(mem_response_error),
        .mem_write_valid(mem_write_valid),
        .mem_write_ready(mem_write_ready),
        .mem_write_object_id(mem_write_object_id),
        .mem_write_element_offset(mem_write_element_offset),
        .mem_write_data(mem_write_data), .busy(busy), .done(done),
        .complete(complete), .trapped(trapped), .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .count_fetched(count_fetched), .count_retired(count_retired),
        .count_predicated_off(count_predicated_off),
        .count_issued(count_issued), .count_branches(count_branches),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events), .count_signals(count_signals),
        .count_views_resolved(count_views_resolved),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .hc_issue_response(hc_issue_response),
        .hc_issue_fault(hc_issue_fault),
        .hc_issue_trap_class(hc_issue_trap_class),
        .hc_descriptor_records_checked(hc_descriptor_records_checked),
        .hc_resolved_views_captured(hc_resolved_views_captured),
        .hc_memory_read_count(hc_memory_read_count),
        .hc_memory_request_stall_cycles(
            hc_memory_request_stall_cycles),
        .hc_memory_response_stall_cycles(
            hc_memory_response_stall_cycles),
        .hc_output_write_count(hc_output_write_count),
        .hc_output_write_stall_cycles(hc_output_write_stall_cycles),
        .hc_arithmetic_executed(hc_arithmetic_executed),
        .hc_last_error_code(hc_last_error_code),
        .hc_arithmetic_square_count(hc_arithmetic_square_count),
        .hc_arithmetic_reduction_add_count(
            hc_arithmetic_reduction_add_count),
        .hc_arithmetic_fma_count(hc_arithmetic_fma_count)
    );

    integer current_profile = 0;
    reg inject_memory_error = 0;
    reg inject_arithmetic_error = 0;
    reg [31:0] service_cycle = 0;
    integer response_delay = 0;
    reg [255:0] pending_response_data = 0;
    reg pending_response_error = 0;
    integer memory_protocol_errors = 0;
    integer write_protocol_errors = 0;
    integer observed_writes = 0;
    integer hc_responses = 0;
    integer hc_fault_responses = 0;
    integer fallback_before_hc = 0;
    integer fallback_after_hc = 0;
    integer lane;
    integer projection_address;

    wire memory_service_idle = !mem_response_valid && response_delay == 0;
    assign mem_read_ready = memory_service_idle &&
        (service_cycle[1:0] != 2'b00);
    assign mem_write_ready = service_cycle[1:0] != 2'b00;

    wire [31:0] hidden_object = current_profile == 0 ? 32'd359 : 32'd239;
    wire [31:0] projection_object = current_profile == 0 ? 32'd9 : 32'd1;
    wire [31:0] base_object = current_profile == 0 ? 32'd12 : 32'd3;
    wire [31:0] scale_object = current_profile == 0 ? 32'd10 : 32'd2;
    wire [31:0] weight_output_object =
        current_profile == 0 ? 32'd374 : 32'd240;
    wire [31:0] combination_output_object =
        current_profile == 0 ? 32'd376 : 32'd241;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            service_cycle <= 0;
            response_delay <= 0;
            pending_response_data <= 0;
            pending_response_error <= 0;
            mem_response_valid <= 0;
            mem_response_data <= 0;
            mem_response_error <= 0;
            memory_protocol_errors <= 0;
            write_protocol_errors <= 0;
            observed_writes <= 0;
            hc_responses <= 0;
            hc_fault_responses <= 0;
            fallback_before_hc <= 0;
            fallback_after_hc <= 0;
            hc_succeeded <= 0;
        end else begin
            service_cycle <= service_cycle + 1'b1;
            if (start) begin
                response_delay <= 0;
                pending_response_data <= 0;
                pending_response_error <= 0;
                mem_response_valid <= 0;
                mem_response_data <= 0;
                mem_response_error <= 0;
                memory_protocol_errors <= 0;
                write_protocol_errors <= 0;
                observed_writes <= 0;
                hc_responses <= 0;
                hc_fault_responses <= 0;
                fallback_before_hc <= 0;
                fallback_after_hc <= 0;
                hc_succeeded <= 0;
            end else begin
                if (mem_response_valid && mem_response_ready) begin
                    mem_response_valid <= 1'b0;
                    mem_response_error <= 1'b0;
                end
                if (!mem_response_valid && response_delay > 0) begin
                    if (response_delay == 1) begin
                        mem_response_valid <= 1'b1;
                        mem_response_data <= pending_response_data;
                        mem_response_error <= pending_response_error;
                        response_delay <= 0;
                    end else begin
                        response_delay <= response_delay - 1;
                    end
                end

                if (mem_read_valid && mem_read_ready) begin
                    pending_response_data <= 0;
                    pending_response_error <= 0;
                    response_delay <= service_cycle[2] ? 2 : 1;
                    if (mem_read_object_id == hidden_object) begin
                        if ((mem_read_dtype != 8'h10) ||
                            (mem_read_element_count != 1) ||
                            (mem_read_element_stride != 1) ||
                            (mem_read_element_offset >= WIDTH)) begin
                            memory_protocol_errors <=
                                memory_protocol_errors + 1;
                        end else begin
                            pending_response_data[15:0] <=
                                hidden_mem[mem_read_element_offset[13:0]];
                            if (inject_arithmetic_error &&
                                mem_read_element_offset == 0)
                                pending_response_data[15:0] <= 16'h7fc1;
                            if (inject_memory_error &&
                                mem_read_element_offset == 0)
                                pending_response_error <= 1'b1;
                        end
                    end else if (mem_read_object_id == projection_object) begin
                        if ((mem_read_dtype != 8'h12) ||
                            (mem_read_element_count != 8) ||
                            (mem_read_element_stride != WIDTH) ||
                            (mem_read_element_offset +
                             7*mem_read_element_stride >= FIELDS*WIDTH)) begin
                            memory_protocol_errors <=
                                memory_protocol_errors + 1;
                        end else begin
                            for (lane = 0; lane < 8; lane = lane + 1) begin
                                projection_address = mem_read_element_offset +
                                    lane * mem_read_element_stride;
                                pending_response_data[lane*32 +: 32] <=
                                    projection_mem[projection_address];
                            end
                        end
                    end else if (mem_read_object_id == base_object) begin
                        if ((mem_read_dtype != 8'h12) ||
                            (mem_read_element_count != 1) ||
                            (mem_read_element_stride != 1) ||
                            (mem_read_element_offset >= FIELDS)) begin
                            memory_protocol_errors <=
                                memory_protocol_errors + 1;
                        end else begin
                            pending_response_data[31:0] <=
                                base_mem[mem_read_element_offset[4:0]];
                        end
                    end else if (mem_read_object_id == scale_object) begin
                        if ((mem_read_dtype != 8'h12) ||
                            (mem_read_element_count != 1) ||
                            (mem_read_element_stride != 1) ||
                            (mem_read_element_offset >= 3)) begin
                            memory_protocol_errors <=
                                memory_protocol_errors + 1;
                        end else begin
                            pending_response_data[31:0] <=
                                scale_mem[mem_read_element_offset[1:0]];
                        end
                    end else begin
                        memory_protocol_errors <= memory_protocol_errors + 1;
                        pending_response_error <= 1'b1;
                    end
                end

                if (mem_write_valid && mem_write_ready) begin
                    if ((observed_writes < 8 &&
                         ((mem_write_object_id != weight_output_object) ||
                          (mem_write_element_offset != observed_writes))) ||
                        (observed_writes >= 8 &&
                         ((mem_write_object_id != combination_output_object) ||
                          (mem_write_element_offset != observed_writes-8))) ||
                        (observed_writes >= 24) ||
                        (mem_write_data != expected_mem[50+observed_writes]))
                        write_protocol_errors <= write_protocol_errors + 1;
                    observed_writes <= observed_writes + 1;
                end

                if (hc_issue_response) begin
                    hc_responses <= hc_responses + 1;
                    if (hc_issue_fault)
                        hc_fault_responses <= hc_fault_responses + 1;
                    else
                        hc_succeeded <= 1'b1;
                end
                if (fallback_issue_valid && fallback_issue_ready) begin
                    if (hc_succeeded)
                        fallback_after_hc <= fallback_after_hc + 1;
                    else
                        fallback_before_hc <= fallback_before_hc + 1;
                end
            end
        end
    end

    integer failures = 0;
    integer checks = 0;
    integer case_number = 0;
    integer guard;
    integer base_word;
    reg [31:0] saved_span_symbol;
    integer rom_cycles = 0;
    integer hbm_cycles = 0;
    integer total_request_stalls = 0;
    integer total_write_stalls = 0;
    integer refusal_cases = 0;

    task automatic check_equal;
        input [1023:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case=%0d %0s got=%0d (0x%0x) wanted=%0d (0x%0x)",
                             case_number, label, got, got, wanted, wanted);
            end
        end
    endtask

    task automatic check_positive;
        input [1023:0] label;
        input [63:0] got;
        begin
            checks = checks + 1;
            if (got == 0) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case=%0d %0s got zero", case_number, label);
            end
        end
    endtask

    task automatic configure_deployment_case;
        input integer deployment_case;
        input integer profile;
        begin
            base_word = deployment_case * CASE_STRIDE;
            current_profile = profile;
            cfg_program_base = case_mem[base_word + 0];
            cfg_instruction_count = case_mem[base_word + 1];
            cfg_desc_base = case_mem[base_word + 2];
            cfg_desc_count = case_mem[base_word + 3];
            cfg_symbol_base = case_mem[base_word + 4];
            cfg_symbol_mask = case_mem[base_word + 5];
            // PC6 opens the embedding loop whose PC7 producer supplies event
            // 2; PC9/10 then supplies event 3 consumed by HC_PRE.  Starting at
            // PC9 would correctly fail its shipped wait set rather than create
            // a synthetic predecessor event.
            cfg_entry_pc = 32'd6;
            cfg_max_retired_work =
                {case_mem[base_word + 9], case_mem[base_word + 8]};
            cfg_state_count = case_mem[base_word + 34];
        end
    endtask

    task automatic begin_case;
        input integer deployment_case;
        input integer profile;
        input integer descriptor_corruption;
        input integer span_mismatch;
        input integer memory_error_case;
        input integer arithmetic_error_case;
        begin
            rst_n = 1'b0;
            start = 1'b0;
            inject_descriptor_corruption = descriptor_corruption != 0;
            inject_memory_error = memory_error_case != 0;
            inject_arithmetic_error = arithmetic_error_case != 0;
            repeat (4) @(negedge clk);
            configure_deployment_case(deployment_case, profile);
            saved_span_symbol = symbol_mem[cfg_symbol_base];
            if (span_mismatch != 0)
                symbol_mem[cfg_symbol_base] = 32'd2;
            rst_n = 1'b1;
            repeat (3) @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            guard = 0;
            while (!done && guard < RUN_GUARD) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (span_mismatch != 0)
                symbol_mem[cfg_symbol_base] = saved_span_symbol;
            check_equal("bounded completion", done, 1);
            check_equal("transaction trapped", trapped, 1);
            check_equal("not complete", complete, 0);
            check_equal("event signal in range", event_signal_error, 0);
            check_equal("state compatibility remains absent",
                        state_apply_overflow, 0);
            check_equal("one HC_PRE response", hc_responses, 1);
            check_equal("memory request protocol", memory_protocol_errors, 0);
            repeat (5) @(negedge clk);
            check_equal("no duplicate HC_PRE response", hc_responses, 1);
        end
    endtask

    task automatic check_success;
        input integer expected_next_fault_pc;
        begin
            check_equal("HC_PRE response success", hc_fault_responses, 0);
            check_equal("post-HC capability trap", trap_class, 16'd4);
            check_equal("next unsupported PC", first_fault_instruction,
                        expected_next_fault_pc);
            check_equal("all raw descriptors checked",
                        hc_descriptor_records_checked, 11);
            check_equal("all resolved views captured",
                        hc_resolved_views_captured, 6);
            check_equal("arithmetic launched", hc_arithmetic_executed, 1);
            check_equal("adapter error clear", hc_last_error_code, 0);
            check_equal("exact square count", hc_arithmetic_square_count,
                        16384);
            check_equal("exact balanced-add count",
                        hc_arithmetic_reduction_add_count, 16383);
            check_equal("exact fused-accumulation count",
                        hc_arithmetic_fma_count, 393216);
            check_equal("all memory reads completed", hc_memory_read_count,
                        114715);
            check_positive("request backpressure observed",
                           hc_memory_request_stall_cycles);
            check_equal("all output words committed", hc_output_write_count,
                        24);
            check_equal("all output words observed", observed_writes, 24);
            check_positive("write backpressure observed",
                           hc_output_write_stall_cycles);
            check_equal("output protocol and exact words",
                        write_protocol_errors, 0);
            check_equal("one post-HC refusal", fallback_after_hc, 1);
            total_request_stalls = total_request_stalls +
                hc_memory_request_stall_cycles;
            total_write_stalls = total_write_stalls +
                hc_output_write_stall_cycles;
        end
    endtask

    task automatic check_refusal;
        input [15:0] wanted_trap;
        input [31:0] wanted_pc;
        input [7:0] wanted_error;
        input [31:0] wanted_records;
        input [31:0] wanted_reads;
        input integer wanted_arithmetic;
        begin
            refusal_cases = refusal_cases + 1;
            check_equal("HC_PRE response fault", hc_fault_responses, 1);
            check_equal("precise refusal trap", trap_class, wanted_trap);
            check_equal("precise refusal PC", first_fault_instruction,
                        wanted_pc);
            check_equal("adapter refusal reason", hc_last_error_code,
                        wanted_error);
            check_equal("descriptor prefix checked",
                        hc_descriptor_records_checked, wanted_records);
            check_equal("memory reads before refusal", hc_memory_read_count,
                        wanted_reads);
            check_equal("arithmetic admission", hc_arithmetic_executed,
                        wanted_arithmetic);
            check_equal("no output word committed", hc_output_write_count, 0);
            check_equal("no output word observed", observed_writes, 0);
            check_equal("no post-HC fallback", fallback_after_hc, 0);
        end
    endtask

    initial begin
        repeat (2) @(negedge clk);

        case_number = 0;
        begin_case(5, 0, 0, 0, 0, 0);
        rom_cycles = guard;
        check_success(18);

        case_number = 1;
        begin_case(7, 1, 0, 0, 0, 0);
        hbm_cycles = guard;
        check_success(17);

        case_number = 2;
        begin_case(5, 0, 1, 0, 0, 0);
        check_refusal(16'd3, 32'd15, 8'd4, 3, 0, 0);

        case_number = 3;
        begin_case(7, 1, 0, 1, 0, 0);
        check_refusal(16'd3, 32'd14, 8'd2, 11, 0, 0);

        case_number = 4;
        begin_case(5, 0, 0, 0, 1, 0);
        check_refusal(16'd8, 32'd15, 8'd6, 11, 28, 1);

        case_number = 5;
        begin_case(7, 1, 0, 0, 0, 1);
        check_refusal(16'd6, 32'd14, 8'd7, 11, 28, 1);

        $display("HC_PRE_SHIPPED_SUMMARY checks=%0d rom_cycles=%0d hbm_cycles=%0d request_stalls=%0d write_stalls=%0d refusal_cases=%0d",
                 checks, rom_cycles, hbm_cycles, total_request_stalls,
                 total_write_stalls, refusal_cases);
        if (failures != 0)
            $fatal(1, "shipped HC_PRE integration failures=%0d checks=%0d",
                   failures, checks);
        $display("PASS a3_hc_pre_shipped checks=%0d", checks);
        $finish;
    end
endmodule
