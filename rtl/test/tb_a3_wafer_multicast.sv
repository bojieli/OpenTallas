`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Source-bound, two-simulator testbench for DeepSeek ROM PC-13 multicast.
//
// One admitted case executes the entire 256 x 65,536-byte destination image
// with a deliberate packet CRC corruption.  A streaming scoreboard checks all
// 4,194,304 writes without allocating a second 16-MiB image.  The remaining
// cases are fail-closed admission mutations generated and CRC-resealed by
// tools/build_a3_wafer_multicast_vectors.py.
// ---------------------------------------------------------------------------
module tb_a3_wafer_multicast;
    parameter integer CASES = 38;
    parameter integer META_WORDS = 16;
    parameter integer COMM_WORDS = 48;
    parameter integer TOPOLOGY_WORDS = 64;
    parameter integer OBJECT_WORDS = 32;
    parameter integer COUNTER_WORDS = 32;
    parameter integer PAYLOAD_WORDS = 16384;
    parameter integer TIMEOUT_CYCLES = 6000000;

    reg [31:0] meta_mem [0:CASES*META_WORDS-1];
    reg [31:0] communication_mem [0:CASES*COMM_WORDS-1];
    reg [31:0] topology_mem [0:CASES*TOPOLOGY_WORDS-1];
    reg [31:0] local_mem [0:CASES*OBJECT_WORDS-1];
    reg [31:0] remote_mem [0:CASES*OBJECT_WORDS-1];
    reg [31:0] counter_mem [0:CASES*COUNTER_WORDS-1];

    reg [1023:0] meta_path;
    reg [1023:0] communication_path;
    reg [1023:0] topology_path;
    reg [1023:0] local_path;
    reg [1023:0] remote_path;
    reg [1023:0] counter_path;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg start = 1'b0;
    reg [31:0] issue_pc = 32'd0;
    reg [7:0] issue_major = 8'd0;
    reg [7:0] issue_sub = 8'd0;
    reg [31:0] issue_descriptor_id = 32'd0;
    reg [31:0] observed_view_count = 32'd0;
    reg [31:0] state_descriptor_count = 32'd0;
    reg [31:0] topology_descriptor_id = 32'd0;
    reg [31:0] local_object_descriptor_id = 32'd0;
    reg [31:0] remote_object_descriptor_id = 32'd0;
    reg [31:0] counter_descriptor_id = 32'd0;
    reg [1535:0] communication_record = 1536'd0;
    reg [2047:0] topology_record = 2048'd0;
    reg [1023:0] local_object_record = 1024'd0;
    reg [1023:0] remote_object_record = 1024'd0;
    reg [1023:0] counter_record = 1024'd0;

    wire source_read_valid;
    reg source_read_ready = 1'b1;
    wire [31:0] source_read_object_id;
    wire [63:0] source_read_offset;
    reg source_response_valid = 1'b0;
    wire source_response_ready;
    reg [31:0] source_response_data = 32'd0;
    reg source_response_error = 1'b0;

    wire remote_write_valid;
    reg remote_write_ready = 1'b1;
    wire [31:0] remote_write_object_id;
    wire [15:0] remote_write_participant;
    wire [63:0] remote_write_offset;
    wire [31:0] remote_write_data;
    reg inject_crc_error = 1'b0;

    wire busy;
    wire done;
    wire failed;
    wire [15:0] trap_class;
    wire [7:0] refusal_reason;
    wire [31:0] messages_sent;
    wire [31:0] messages_received;
    wire [63:0] bytes_sent;
    wire [63:0] bytes_received;
    wire [31:0] remote_write_count;
    wire [31:0] payload_flits_delivered;
    wire [31:0] wire_flits_transmitted;
    wire [31:0] replayed_flits;
    wire [31:0] retry_events;
    wire [31:0] credit_stall_cycles;
    wire [31:0] crc_errors;
    wire [31:0] sequence_errors;

    ot_a3_wafer_multicast_adapter dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .issue_pc(issue_pc), .issue_major(issue_major),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .observed_view_count(observed_view_count),
        .state_descriptor_count(state_descriptor_count),
        .topology_descriptor_id(topology_descriptor_id),
        .local_object_descriptor_id(local_object_descriptor_id),
        .remote_object_descriptor_id(remote_object_descriptor_id),
        .counter_descriptor_id(counter_descriptor_id),
        .communication_record(communication_record),
        .topology_record(topology_record),
        .local_object_record(local_object_record),
        .remote_object_record(remote_object_record),
        .counter_record(counter_record),
        .source_read_valid(source_read_valid),
        .source_read_ready(source_read_ready),
        .source_read_object_id(source_read_object_id),
        .source_read_offset(source_read_offset),
        .source_response_valid(source_response_valid),
        .source_response_ready(source_response_ready),
        .source_response_data(source_response_data),
        .source_response_error(source_response_error),
        .remote_write_valid(remote_write_valid),
        .remote_write_ready(remote_write_ready),
        .remote_write_object_id(remote_write_object_id),
        .remote_write_participant(remote_write_participant),
        .remote_write_offset(remote_write_offset),
        .remote_write_data(remote_write_data),
        .inject_crc_error(inject_crc_error),
        .busy(busy), .done(done), .failed(failed),
        .trap_class(trap_class), .refusal_reason(refusal_reason),
        .messages_sent(messages_sent),
        .messages_received(messages_received),
        .bytes_sent(bytes_sent), .bytes_received(bytes_received),
        .remote_write_count(remote_write_count),
        .payload_flits_delivered(payload_flits_delivered),
        .wire_flits_transmitted(wire_flits_transmitted),
        .replayed_flits(replayed_flits),
        .retry_events(retry_events),
        .credit_stall_cycles(credit_stall_cycles),
        .crc_errors(crc_errors), .sequence_errors(sequence_errors)
    );

    function automatic [31:0] payload_word;
        input [13:0] index;
        reg [31:0] widened;
        begin
            widened = {18'd0, index};
            payload_word = 32'h9e37_79b9 ^
                           (widened * 32'h045d_9f3b) ^
                           {index, index, index[3:0]};
        end
    endfunction

    function automatic [7:0] expected_tree_source;
        input [7:0] destination;
        integer power;
        begin
            power = 1;
            while ((power << 1) <= destination)
                power = power << 1;
            expected_tree_source = destination - power;
        end
    endfunction

    integer failures;
    integer checks;
    integer ci;
    integer j;
    integer guard;
    integer meta_base;
    integer source_requests;
    integer source_responses;
    integer observed_writes;
    integer post_fault_reads;
    integer post_fault_writes;
    integer next_word [0:255];
    integer participant_writes [0:255];
    reg case_active;
    reg case_fault_seen;

    task expect32;
        input [255:0] label;
        input [31:0] got;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d %0s: got %0d (%h), wanted %0d (%h)",
                             ci, label, got, got, wanted, wanted);
            end
        end
    endtask

    task expect64;
        input [255:0] label;
        input [63:0] got;
        input [63:0] wanted;
        begin
            checks = checks + 1;
            if (got !== wanted) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d %0s: got %0d, wanted %0d",
                             ci, label, got, wanted);
            end
        end
    endtask

    // One-cycle source-memory response.  Addresses are checked independently
    // before the deterministic nonzero word is returned.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            source_response_valid <= 1'b0;
            source_response_data <= 32'd0;
            source_response_error <= 1'b0;
        end else begin
            source_response_valid <= 1'b0;
            source_response_error <= 1'b0;
            if (source_read_valid && source_read_ready) begin
                if (case_fault_seen)
                    post_fault_reads = post_fault_reads + 1;
                source_requests = source_requests + 1;
                checks = checks + 1;
                if ((source_read_object_id !== 32'd365) ||
                    (source_read_offset !== ((source_requests-1) * 4))) begin
                    failures = failures + 1;
                    if (failures < 40)
                        $display("FAIL case %0d source request %0d object=%0d offset=%0d",
                                 ci, source_requests-1, source_read_object_id,
                                 source_read_offset);
                end
                source_response_data <=
                    payload_word(source_read_offset[15:2]);
                source_response_valid <= 1'b1;
            end
            if (source_response_valid && source_response_ready)
                source_responses = source_responses + 1;
        end
    end

    // Streaming destination scoreboard.  Slot geometry makes participant and
    // word index directly observable from the address, so an address/data pair
    // cannot validate itself accidentally.
    always @(posedge clk) begin
        if (rst_n && remote_write_valid && remote_write_ready) begin
            if (case_fault_seen)
                post_fault_writes = post_fault_writes + 1;
            observed_writes = observed_writes + 1;
            checks = checks + 1;
            if ((remote_write_object_id !== 32'd366) ||
                (remote_write_offset[1:0] !== 2'd0) ||
                (remote_write_offset >= 64'd16777216) ||
                (remote_write_participant !==
                 {8'd0, remote_write_offset[23:16]}) ||
                (remote_write_data !==
                 payload_word(remote_write_offset[15:2]))) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d write %0d obj=%0d participant=%0d offset=%0d data=%h expected=%h",
                             ci, observed_writes-1, remote_write_object_id,
                             remote_write_participant, remote_write_offset,
                             remote_write_data,
                             payload_word(remote_write_offset[15:2]));
            end
            checks = checks + 1;
            if (next_word[remote_write_participant[7:0]] !==
                remote_write_offset[15:2]) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL case %0d participant %0d wrote word %0d, expected next %0d",
                             ci, remote_write_participant,
                             remote_write_offset[15:2],
                             next_word[remote_write_participant[7:0]]);
            end
            next_word[remote_write_participant[7:0]] =
                next_word[remote_write_participant[7:0]] + 1;
            participant_writes[remote_write_participant[7:0]] =
                participant_writes[remote_write_participant[7:0]] + 1;

            if (remote_write_participant != 0) begin
                checks = checks + 1;
                if (dut.tree_source !==
                    expected_tree_source(remote_write_participant[7:0])) begin
                    failures = failures + 1;
                    if (failures < 40)
                        $display("FAIL case %0d tree destination %0d source %0d expected %0d",
                                 ci, remote_write_participant, dut.tree_source,
                                 expected_tree_source(remote_write_participant[7:0]));
                end
            end
        end
        if (rst_n && failed)
            case_fault_seen = 1'b1;
    end

    initial begin
        if (!$value$plusargs("META=%s", meta_path))
            meta_path = "case_meta.hex";
        if (!$value$plusargs("COMMUNICATION=%s", communication_path))
            communication_path = "communication.hex";
        if (!$value$plusargs("TOPOLOGY=%s", topology_path))
            topology_path = "topology.hex";
        if (!$value$plusargs("LOCAL=%s", local_path))
            local_path = "local_object.hex";
        if (!$value$plusargs("REMOTE=%s", remote_path))
            remote_path = "remote_object.hex";
        if (!$value$plusargs("COUNTER=%s", counter_path))
            counter_path = "counter.hex";

        $readmemh(meta_path, meta_mem);
        $readmemh(communication_path, communication_mem);
        $readmemh(topology_path, topology_mem);
        $readmemh(local_path, local_mem);
        $readmemh(remote_path, remote_mem);
        $readmemh(counter_path, counter_mem);

        failures = 0;
        checks = 0;
        case_active = 1'b0;
        case_fault_seen = 1'b0;
        source_requests = 0;
        source_responses = 0;
        observed_writes = 0;
        post_fault_reads = 0;
        post_fault_writes = 0;

        for (ci = 0; ci < CASES; ci = ci + 1) begin
            rst_n = 1'b0;
            start = 1'b0;
            inject_crc_error = 1'b0;
            source_requests = 0;
            source_responses = 0;
            observed_writes = 0;
            post_fault_reads = 0;
            post_fault_writes = 0;
            case_fault_seen = 1'b0;
            for (j = 0; j < 256; j = j + 1) begin
                next_word[j] = 0;
                participant_writes[j] = 0;
            end

            meta_base = ci * META_WORDS;
            issue_pc = meta_mem[meta_base + 0];
            issue_major = meta_mem[meta_base + 1][7:0];
            issue_sub = meta_mem[meta_base + 2][7:0];
            issue_descriptor_id = meta_mem[meta_base + 3];
            observed_view_count = meta_mem[meta_base + 4];
            state_descriptor_count = meta_mem[meta_base + 5];
            topology_descriptor_id = meta_mem[meta_base + 6];
            local_object_descriptor_id = meta_mem[meta_base + 7];
            remote_object_descriptor_id = meta_mem[meta_base + 8];
            counter_descriptor_id = meta_mem[meta_base + 9];
            for (j = 0; j < COMM_WORDS; j = j + 1)
                communication_record[j*32 +: 32] =
                    communication_mem[ci*COMM_WORDS+j];
            for (j = 0; j < TOPOLOGY_WORDS; j = j + 1)
                topology_record[j*32 +: 32] =
                    topology_mem[ci*TOPOLOGY_WORDS+j];
            for (j = 0; j < OBJECT_WORDS; j = j + 1) begin
                local_object_record[j*32 +: 32] =
                    local_mem[ci*OBJECT_WORDS+j];
                remote_object_record[j*32 +: 32] =
                    remote_mem[ci*OBJECT_WORDS+j];
            end
            for (j = 0; j < COUNTER_WORDS; j = j + 1)
                counter_record[j*32 +: 32] =
                    counter_mem[ci*COUNTER_WORDS+j];

            repeat (4) @(posedge clk);
            rst_n = 1'b1;
            repeat (2) @(posedge clk);
            // Arm the endpoint while it is idle.  The endpoint contract spends
            // an armed fault on the next transmitted flit; pulsing during an
            // active send would make the level-sensitive hook ambiguous.
            if (meta_mem[meta_base + 12]) begin
                @(negedge clk);
                inject_crc_error = 1'b1;
                @(negedge clk);
                inject_crc_error = 1'b0;
            end
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;

            if (meta_mem[meta_base + 10]) begin
                guard = 0;
                while (!done && !failed && guard < TIMEOUT_CYCLES) begin
                    @(posedge clk);
                    guard = guard + 1;
                end
                if (!done || failed) begin
                    failures = failures + 1;
                    $display("FAIL case %0d did not complete: done=%0d failed=%0d reason=%0d guard=%0d",
                             ci, done, failed, refusal_reason, guard);
                end

                expect32("source requests", source_requests, PAYLOAD_WORDS);
                expect32("source responses", source_responses, PAYLOAD_WORDS);
                expect32("messages sent", messages_sent, 255);
                expect32("messages received", messages_received, 255);
                expect64("bytes sent", bytes_sent, 64'd16711680);
                expect64("bytes received", bytes_received, 64'd16711680);
                expect32("payload flits", payload_flits_delivered, 4177920);
                expect32("remote writes", remote_write_count, 4194304);
                expect32("scoreboard writes", observed_writes, 4194304);
                expect32("trap class", {16'd0, trap_class}, 0);
                expect32("refusal reason", {24'd0, refusal_reason}, 0);
                expect32("CRC errors", crc_errors, 1);
                checks = checks + 1;
                if ((retry_events < 1) || (replayed_flits < 1) ||
                    (wire_flits_transmitted !==
                     payload_flits_delivered + crc_errors +
                     sequence_errors)) begin
                    failures = failures + 1;
                    $display("FAIL case %0d replay relation tx=%0d delivered=%0d replayed=%0d retries=%0d",
                             ci, wire_flits_transmitted,
                             payload_flits_delivered, replayed_flits,
                             retry_events);
                end
                for (j = 0; j < 256; j = j + 1)
                    expect32("participant write count",
                             participant_writes[j], PAYLOAD_WORDS);
                expect32("post-fault reads", post_fault_reads, 0);
                expect32("post-fault writes", post_fault_writes, 0);
                $display("CASE %0d admitted=1 reason=%0d messages=%0d bytes=%0d payload_flits=%0d writes=%0d tx_flits=%0d replayed=%0d retries=%0d crc_errors=%0d sequence_errors=%0d credit_stalls=%0d cycles=%0d",
                         ci, refusal_reason, messages_sent, bytes_sent,
                         payload_flits_delivered, remote_write_count,
                         wire_flits_transmitted, replayed_flits,
                         retry_events, crc_errors, sequence_errors,
                         credit_stall_cycles, guard);
            end else begin
                repeat (4) @(posedge clk);
                expect32("failed", {31'd0, failed}, 1);
                expect32("busy", {31'd0, busy}, 0);
                expect32("done", {31'd0, done}, 0);
                expect32("trap class", {16'd0, trap_class}, 11);
                expect32("refusal reason", {24'd0, refusal_reason},
                         meta_mem[meta_base + 11]);
                expect32("source requests", source_requests, 0);
                expect32("remote writes", observed_writes, 0);
                // Prove the sticky state does not resume on a second start.
                @(negedge clk);
                start = 1'b1;
                @(negedge clk);
                start = 1'b0;
                repeat (3) @(posedge clk);
                expect32("post-fault reads", post_fault_reads, 0);
                expect32("post-fault writes", post_fault_writes, 0);
                expect32("sticky refusal", {24'd0, refusal_reason},
                         meta_mem[meta_base + 11]);
                $display("CASE %0d admitted=0 reason=%0d reads=%0d writes=%0d",
                         ci, refusal_reason, source_requests, observed_writes);
            end
        end

        if (failures == 0)
            $display("PASS a3_wafer_multicast checks=%0d", checks);
        else
            $display("FAIL a3_wafer_multicast failures=%0d checks=%0d",
                     failures, checks);
        $finish;
    end
endmodule
