`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Two-simulator testbench for the ABI 3.0 inter-chip endpoint.
//
// Every expected value comes from `tools/build_a3_link_vectors.py`, which takes
// the reduced result from the executed functional model
// (`runtime.sim.engines.reduction.ordered_sum`) and the traversal charge from
// the rule `src/opentallas/roofline.py` applies.  This file checks, per case:
//
//   * the reduced binary32 codes at EVERY participant, element by element --
//     an all-reduce that is right at one node and wrong at another is the
//     failure mode a single-node check cannot see;
//   * the trap expectation, including the arithmetic collective the engine must
//     REFUSE because the mesh cannot produce the declared reduction order;
//   * the serial traversal count, which is the quantity the analytical model
//     charges and has never been measured;
//   * the flits the engine offered and the link crossings the fabric actually
//     performed, which must agree exactly when nothing is replayed;
//   * that a deliberately corrupted CRC is detected, replayed within the retry
//     bound, and leaves the arithmetic result bit-identical.
//
// The testbench refuses to run if the vector set's geometry disagrees with the
// parameters this elaboration was built with.  A campaign that silently ran a
// 4x4 vector set against an 8x8 elaboration would pass most of its checks.
// ---------------------------------------------------------------------------
module tb_a3_link;
    parameter integer MESH_X      = 4;
    parameter integer MESH_Y      = 4;
    parameter integer VEC_LEN     = 16;
    parameter integer CREDITS     = 8;
    parameter integer RETRY_MAX   = 3;
    parameter integer TIMEOUT_CLASS = 1;
    parameter integer HOP_CYCLES  = 1;
    parameter integer ACK_TIMEOUT = 4096;
    parameter integer MAX_CASES   = 10;
    parameter integer CASE_STRIDE = 80;
    parameter integer DESCRIPTOR_WORDS = 48;
    parameter integer NUMERIC_WORDS = 32;
    parameter integer TIMEOUT_CYCLES = 2000000;

    localparam integer NODES = MESH_X * MESH_Y;
    localparam integer VECWORDS = MAX_CASES * NODES * VEC_LEN;

    reg [31:0] meta_mem    [0:11];
    reg [31:0] case_mem    [0:MAX_CASES*CASE_STRIDE-1];
    reg [31:0] communication_mem [0:MAX_CASES*DESCRIPTOR_WORDS-1];
    reg [31:0] numeric_mem [0:MAX_CASES*NUMERIC_WORDS-1];
    reg [31:0] contrib_mem [0:VECWORDS-1];
    reg [31:0] expect_mem  [0:VECWORDS-1];

    reg [1023:0] path_meta;
    reg [1023:0] path_case;
    reg [1023:0] path_communication;
    reg [1023:0] path_numeric;
    reg [1023:0] path_contrib;
    reg [1023:0] path_expect;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        start = 1'b0;
    reg [1535:0] communication_descriptor = 1536'd0;
    reg [1023:0] numeric_descriptor = 1024'd0;
    reg [7:0]  instruction_subopcode = 8'd0;
    reg [1:0]  alg = 2'd0;
    reg [7:0]  rorder = 8'd1;
    reg [31:0] numeric_descriptor_id = 32'hffff_ffff;
    wire       descriptor_valid;
    wire       numeric_descriptor_valid;
    wire       numeric_semantics_supported;
    wire [7:0] numeric_refusal_reason;
    wire       command_admitted;
    wire [7:0] refusal_reason;
    wire [31:0] decoded_magic;
    wire [15:0] decoded_descriptor_type;
    wire [7:0] decoded_type_major;
    wire [7:0] decoded_type_minor;
    wire [31:0] decoded_total_bytes;
    wire [31:0] decoded_flags;
    wire [31:0] decoded_primary_object_id;
    wire [31:0] decoded_secondary_object_id;
    wire [31:0] decoded_numeric_profile_id;
    wire [31:0] decoded_schedule_id;
    wire [31:0] decoded_permissions;
    wire [31:0] decoded_owner_scope_id;
    wire [31:0] decoded_payload_offset;
    wire [31:0] decoded_payload_bytes;
    wire [31:0] decoded_supplied_crc;
    wire [31:0] decoded_calculated_crc;
    wire [7:0] decoded_collective_op;
    wire [7:0] decoded_ordering;
    wire [7:0] decoded_integrity_mode;
    wire [7:0] decoded_virtual_channel;
    wire [15:0] decoded_source_node;
    wire [15:0] decoded_destination_node;
    wire [31:0] decoded_group_id;
    wire [31:0] decoded_route_class;
    wire [31:0] decoded_local_object_id;
    wire [31:0] decoded_remote_object_id;
    wire [63:0] decoded_local_offset;
    wire [63:0] decoded_remote_offset;
    wire [63:0] decoded_byte_extent;
    wire [31:0] decoded_credit_bound;
    wire [31:0] decoded_retry_bound;
    wire [31:0] decoded_timeout_class;
    wire [31:0] decoded_completion_event_id;
    wire [31:0] decoded_reduction_numeric_id;
    wire [31:0] decoded_counter_class_id;
    wire [31:0] decoded_participant_count;
    wire [31:0] decoded_chunk_bytes;
    wire [7:0] decoded_participant_scope;
    wire [15:0] decoded_numeric_descriptor_type;
    wire [31:0] decoded_numeric_total_bytes;
    wire [31:0] decoded_numeric_payload_bytes;
    wire [31:0] decoded_numeric_supplied_crc;
    wire [31:0] decoded_numeric_calculated_crc;
    wire [7:0] decoded_numeric_input_dtype;
    wire [7:0] decoded_numeric_second_input_dtype;
    wire [7:0] decoded_numeric_accumulator_dtype;
    wire [7:0] decoded_numeric_output_dtype;
    wire [7:0] decoded_numeric_rounding_mode;
    wire [7:0] decoded_numeric_reduction_order;
    wire [7:0] decoded_numeric_saturate;
    wire [7:0] decoded_numeric_nan_policy;
    wire [31:0] decoded_numeric_epsilon_bits;
    wire [31:0] decoded_numeric_scale_bits;
    wire [31:0] decoded_numeric_flags;
    wire decoded_numeric_contract_digest_zero;
    wire [7:0] decoded_engine_op;
    wire [3:0] decoded_root_x;
    wire [3:0] decoded_root_y;
    wire       all_done;
    wire       any_busy;
    wire       any_trap;
    wire [15:0] first_trap_class;

    reg        load_valid = 1'b0;
    reg [7:0]  load_node = 8'd0;
    reg [7:0]  load_index = 8'd0;
    reg [31:0] load_data = 32'd0;
    reg [7:0]  read_node = 8'd0;
    reg [7:0]  read_index = 8'd0;
    wire [31:0] read_data;

    reg        inject_valid = 1'b0;
    reg [7:0]  inject_node = 8'd0;
    reg [1:0]  inject_dir = 2'd0;

    wire [31:0] total_wire_flits;
    wire [31:0] total_hop_distance;
    wire [31:0] total_engine_flits_sent;
    wire [31:0] total_replayed_flits;
    wire [31:0] total_retry_events;
    wire [31:0] total_credit_stall_cycles;
    wire [31:0] total_crc_errors;
    wire [31:0] total_sequence_errors;
    wire [31:0] total_steps;
    wire [31:0] max_serial_traversals;
    wire [31:0] max_busy_cycles;
    wire        any_link_error;
    wire        any_misroute;

    a3_link_mesh_top #(
        .MESH_X(MESH_X), .MESH_Y(MESH_Y), .VEC_LEN(VEC_LEN),
        .CREDITS(CREDITS), .RETRY_MAX(RETRY_MAX),
        .TIMEOUT_CLASS(TIMEOUT_CLASS),
        .ACK_TIMEOUT(ACK_TIMEOUT), .HOP_CYCLES(HOP_CYCLES)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .start(start), .communication_descriptor(communication_descriptor),
        .numeric_descriptor(numeric_descriptor),
        .instruction_subopcode(instruction_subopcode), .alg(alg),
        .numeric_descriptor_id(numeric_descriptor_id),
        .numeric_reduction_order(rorder),
        .descriptor_valid(descriptor_valid),
        .numeric_descriptor_valid(numeric_descriptor_valid),
        .numeric_semantics_supported(numeric_semantics_supported),
        .numeric_refusal_reason(numeric_refusal_reason),
        .command_admitted(command_admitted),
        .refusal_reason(refusal_reason),
        .decoded_magic(decoded_magic),
        .decoded_descriptor_type(decoded_descriptor_type),
        .decoded_type_major(decoded_type_major),
        .decoded_type_minor(decoded_type_minor),
        .decoded_total_bytes(decoded_total_bytes),
        .decoded_flags(decoded_flags),
        .decoded_primary_object_id(decoded_primary_object_id),
        .decoded_secondary_object_id(decoded_secondary_object_id),
        .decoded_numeric_profile_id(decoded_numeric_profile_id),
        .decoded_schedule_id(decoded_schedule_id),
        .decoded_permissions(decoded_permissions),
        .decoded_owner_scope_id(decoded_owner_scope_id),
        .decoded_payload_offset(decoded_payload_offset),
        .decoded_payload_bytes(decoded_payload_bytes),
        .decoded_supplied_crc(decoded_supplied_crc),
        .decoded_calculated_crc(decoded_calculated_crc),
        .decoded_collective_op(decoded_collective_op),
        .decoded_ordering(decoded_ordering),
        .decoded_integrity_mode(decoded_integrity_mode),
        .decoded_virtual_channel(decoded_virtual_channel),
        .decoded_source_node(decoded_source_node),
        .decoded_destination_node(decoded_destination_node),
        .decoded_group_id(decoded_group_id),
        .decoded_route_class(decoded_route_class),
        .decoded_local_object_id(decoded_local_object_id),
        .decoded_remote_object_id(decoded_remote_object_id),
        .decoded_local_offset(decoded_local_offset),
        .decoded_remote_offset(decoded_remote_offset),
        .decoded_byte_extent(decoded_byte_extent),
        .decoded_credit_bound(decoded_credit_bound),
        .decoded_retry_bound(decoded_retry_bound),
        .decoded_timeout_class(decoded_timeout_class),
        .decoded_completion_event_id(decoded_completion_event_id),
        .decoded_reduction_numeric_id(decoded_reduction_numeric_id),
        .decoded_counter_class_id(decoded_counter_class_id),
        .decoded_participant_count(decoded_participant_count),
        .decoded_chunk_bytes(decoded_chunk_bytes),
        .decoded_participant_scope(decoded_participant_scope),
        .decoded_numeric_descriptor_type(decoded_numeric_descriptor_type),
        .decoded_numeric_total_bytes(decoded_numeric_total_bytes),
        .decoded_numeric_payload_bytes(decoded_numeric_payload_bytes),
        .decoded_numeric_supplied_crc(decoded_numeric_supplied_crc),
        .decoded_numeric_calculated_crc(decoded_numeric_calculated_crc),
        .decoded_numeric_input_dtype(decoded_numeric_input_dtype),
        .decoded_numeric_second_input_dtype(
            decoded_numeric_second_input_dtype),
        .decoded_numeric_accumulator_dtype(
            decoded_numeric_accumulator_dtype),
        .decoded_numeric_output_dtype(decoded_numeric_output_dtype),
        .decoded_numeric_rounding_mode(decoded_numeric_rounding_mode),
        .decoded_numeric_reduction_order(decoded_numeric_reduction_order),
        .decoded_numeric_saturate(decoded_numeric_saturate),
        .decoded_numeric_nan_policy(decoded_numeric_nan_policy),
        .decoded_numeric_epsilon_bits(decoded_numeric_epsilon_bits),
        .decoded_numeric_scale_bits(decoded_numeric_scale_bits),
        .decoded_numeric_flags(decoded_numeric_flags),
        .decoded_numeric_contract_digest_zero(
            decoded_numeric_contract_digest_zero),
        .decoded_engine_op(decoded_engine_op),
        .decoded_root_x(decoded_root_x), .decoded_root_y(decoded_root_y),
        .all_done(all_done), .any_busy(any_busy), .any_trap(any_trap),
        .first_trap_class(first_trap_class),
        .load_valid(load_valid), .load_node(load_node),
        .load_index(load_index), .load_data(load_data),
        .read_node(read_node), .read_index(read_index), .read_data(read_data),
        .inject_valid(inject_valid), .inject_node(inject_node),
        .inject_dir(inject_dir),
        .total_wire_flits(total_wire_flits),
        .total_hop_distance(total_hop_distance),
        .total_engine_flits_sent(total_engine_flits_sent),
        .total_replayed_flits(total_replayed_flits),
        .total_retry_events(total_retry_events),
        .total_credit_stall_cycles(total_credit_stall_cycles),
        .total_crc_errors(total_crc_errors),
        .total_sequence_errors(total_sequence_errors),
        .total_steps(total_steps),
        .max_serial_traversals(max_serial_traversals),
        .max_busy_cycles(max_busy_cycles),
        .any_link_error(any_link_error),
        .any_misroute(any_misroute)
    );

    integer checks;
    integer failures;
    integer case_count;
    integer ci;
    integer n;
    integer j;
    integer guard;
    integer base;
    integer case_base;
    integer wire_before;
    integer crc_before;
    integer retry_before;
    integer replay_before;
    integer stall_before;
    integer wire_delta;
    integer crc_delta;
    integer retry_delta;
    integer replay_delta;
    integer stall_delta;
    integer cycles_used;
    reg [31:0] want;
    reg [31:0] got;
    reg expect_trap;
    reg do_inject;

    task expect_eq32;
        input [255:0] what;
        input [31:0] observed;
        input [31:0] wanted;
        begin
            checks = checks + 1;
            if (observed !== wanted) begin
                failures = failures + 1;
                $display("FAIL case %0d %0s: observed %0d (%h) wanted %0d (%h)",
                         ci, what, observed, observed, wanted, wanted);
            end
        end
    endtask

    task check_descriptor_decode;
        input integer cb;
        begin
            expect_eq32("descriptor_valid", {31'd0, descriptor_valid},
                        {31'd0, case_mem[cb + 6][2]});
            expect_eq32("command_admitted", {31'd0, command_admitted},
                        {31'd0, case_mem[cb + 6][3]});
            expect_eq32("refusal_reason", {24'd0, refusal_reason},
                        case_mem[cb + 7]);
            expect_eq32("engine_op", {24'd0, decoded_engine_op},
                        case_mem[cb + 12]);
            expect_eq32("root_x", {28'd0, decoded_root_x}, case_mem[cb + 13]);
            expect_eq32("root_y", {28'd0, decoded_root_y}, case_mem[cb + 14]);
            expect_eq32("magic", decoded_magic, case_mem[cb + 15]);
            expect_eq32("descriptor_type", {16'd0, decoded_descriptor_type},
                        case_mem[cb + 16]);
            expect_eq32("type_major", {24'd0, decoded_type_major},
                        case_mem[cb + 17]);
            expect_eq32("type_minor", {24'd0, decoded_type_minor},
                        case_mem[cb + 18]);
            expect_eq32("total_bytes", decoded_total_bytes, case_mem[cb + 19]);
            expect_eq32("header_flags", decoded_flags, case_mem[cb + 20]);
            expect_eq32("primary_object_id", decoded_primary_object_id,
                        case_mem[cb + 21]);
            expect_eq32("secondary_object_id", decoded_secondary_object_id,
                        case_mem[cb + 22]);
            expect_eq32("numeric_profile_id", decoded_numeric_profile_id,
                        case_mem[cb + 23]);
            expect_eq32("schedule_id", decoded_schedule_id, case_mem[cb + 24]);
            expect_eq32("permissions", decoded_permissions, case_mem[cb + 25]);
            expect_eq32("owner_scope_id", decoded_owner_scope_id,
                        case_mem[cb + 26]);
            expect_eq32("payload_offset", decoded_payload_offset,
                        case_mem[cb + 27]);
            expect_eq32("payload_bytes", decoded_payload_bytes,
                        case_mem[cb + 28]);
            expect_eq32("supplied_crc", decoded_supplied_crc, case_mem[cb + 29]);
            expect_eq32("calculated_crc", decoded_calculated_crc,
                        case_mem[cb + 30]);
            expect_eq32("collective_op", {24'd0, decoded_collective_op},
                        case_mem[cb + 31]);
            expect_eq32("ordering", {24'd0, decoded_ordering},
                        case_mem[cb + 32]);
            expect_eq32("integrity_mode", {24'd0, decoded_integrity_mode},
                        case_mem[cb + 33]);
            expect_eq32("virtual_channel", {24'd0, decoded_virtual_channel},
                        case_mem[cb + 34]);
            expect_eq32("source_node", {16'd0, decoded_source_node},
                        case_mem[cb + 35]);
            expect_eq32("destination_node", {16'd0, decoded_destination_node},
                        case_mem[cb + 36]);
            expect_eq32("group_id", decoded_group_id, case_mem[cb + 37]);
            expect_eq32("route_class", decoded_route_class, case_mem[cb + 38]);
            expect_eq32("local_object_id", decoded_local_object_id,
                        case_mem[cb + 39]);
            expect_eq32("remote_object_id", decoded_remote_object_id,
                        case_mem[cb + 40]);
            expect_eq32("local_offset_lo", decoded_local_offset[31:0],
                        case_mem[cb + 41]);
            expect_eq32("local_offset_hi", decoded_local_offset[63:32],
                        case_mem[cb + 42]);
            expect_eq32("remote_offset_lo", decoded_remote_offset[31:0],
                        case_mem[cb + 43]);
            expect_eq32("remote_offset_hi", decoded_remote_offset[63:32],
                        case_mem[cb + 44]);
            expect_eq32("byte_extent_lo", decoded_byte_extent[31:0],
                        case_mem[cb + 45]);
            expect_eq32("byte_extent_hi", decoded_byte_extent[63:32],
                        case_mem[cb + 46]);
            expect_eq32("credit_bound", decoded_credit_bound, case_mem[cb + 47]);
            expect_eq32("retry_bound", decoded_retry_bound, case_mem[cb + 48]);
            expect_eq32("timeout_class", decoded_timeout_class,
                        case_mem[cb + 49]);
            expect_eq32("completion_event_id", decoded_completion_event_id,
                        case_mem[cb + 50]);
            expect_eq32("reduction_numeric_id", decoded_reduction_numeric_id,
                        case_mem[cb + 51]);
            expect_eq32("counter_class_id", decoded_counter_class_id,
                        case_mem[cb + 52]);
            expect_eq32("participant_count", decoded_participant_count,
                        case_mem[cb + 53]);
            expect_eq32("chunk_bytes", decoded_chunk_bytes, case_mem[cb + 54]);
            expect_eq32("participant_scope", {24'd0, decoded_participant_scope},
                        case_mem[cb + 55]);
            expect_eq32("numeric_record_valid",
                        {31'd0, numeric_descriptor_valid},
                        case_mem[cb + 57]);
            expect_eq32("numeric_semantics_supported",
                        {31'd0, numeric_semantics_supported},
                        case_mem[cb + 58]);
            expect_eq32("numeric_refusal_reason",
                        {24'd0, numeric_refusal_reason},
                        case_mem[cb + 59]);
            expect_eq32("numeric_descriptor_type",
                        {16'd0, decoded_numeric_descriptor_type},
                        case_mem[cb + 60]);
            expect_eq32("numeric_total_bytes", decoded_numeric_total_bytes,
                        case_mem[cb + 61]);
            expect_eq32("numeric_payload_bytes", decoded_numeric_payload_bytes,
                        case_mem[cb + 62]);
            expect_eq32("numeric_supplied_crc", decoded_numeric_supplied_crc,
                        case_mem[cb + 63]);
            expect_eq32("numeric_calculated_crc", decoded_numeric_calculated_crc,
                        case_mem[cb + 64]);
            expect_eq32("numeric_input_dtype",
                        {24'd0, decoded_numeric_input_dtype},
                        case_mem[cb + 65]);
            expect_eq32("numeric_second_input_dtype",
                        {24'd0, decoded_numeric_second_input_dtype},
                        case_mem[cb + 66]);
            expect_eq32("numeric_accumulator_dtype",
                        {24'd0, decoded_numeric_accumulator_dtype},
                        case_mem[cb + 67]);
            expect_eq32("numeric_output_dtype",
                        {24'd0, decoded_numeric_output_dtype},
                        case_mem[cb + 68]);
            expect_eq32("numeric_rounding_mode",
                        {24'd0, decoded_numeric_rounding_mode},
                        case_mem[cb + 69]);
            expect_eq32("numeric_reduction_order",
                        {24'd0, decoded_numeric_reduction_order},
                        case_mem[cb + 70]);
            expect_eq32("numeric_saturate",
                        {24'd0, decoded_numeric_saturate},
                        case_mem[cb + 71]);
            expect_eq32("numeric_nan_policy",
                        {24'd0, decoded_numeric_nan_policy},
                        case_mem[cb + 72]);
            expect_eq32("numeric_epsilon_bits", decoded_numeric_epsilon_bits,
                        case_mem[cb + 73]);
            expect_eq32("numeric_scale_bits", decoded_numeric_scale_bits,
                        case_mem[cb + 74]);
            expect_eq32("numeric_flags", decoded_numeric_flags,
                        case_mem[cb + 75]);
            expect_eq32("numeric_contract_digest_zero",
                        {31'd0, decoded_numeric_contract_digest_zero},
                        case_mem[cb + 76]);
        end
    endtask

    initial begin
        if (!$value$plusargs("META=%s", path_meta))    path_meta = "meta.hex";
        if (!$value$plusargs("CASE=%s", path_case))    path_case = "case.hex";
        if (!$value$plusargs("COMMUNICATION=%s", path_communication))
            path_communication = "communication.hex";
        if (!$value$plusargs("NUMERIC=%s", path_numeric))
            path_numeric = "numeric.hex";
        if (!$value$plusargs("CONTRIB=%s", path_contrib)) path_contrib = "contrib.hex";
        if (!$value$plusargs("EXPECT=%s", path_expect)) path_expect = "expect.hex";
        $readmemh(path_meta, meta_mem);
        $readmemh(path_case, case_mem);
        $readmemh(path_communication, communication_mem);
        $readmemh(path_numeric, numeric_mem);
        $readmemh(path_contrib, contrib_mem);
        $readmemh(path_expect, expect_mem);

        checks = 0;
        failures = 0;

        // The vector set states the geometry it was generated for.  An
        // elaboration that does not match it is refused, not tolerated.
        if (meta_mem[0] !== MESH_X || meta_mem[1] !== MESH_Y ||
            meta_mem[2] !== VEC_LEN || meta_mem[3] !== CREDITS ||
            meta_mem[4] !== RETRY_MAX || meta_mem[5] !== HOP_CYCLES ||
            meta_mem[6] !== MAX_CASES || meta_mem[7] !== NODES ||
            meta_mem[8] !== TIMEOUT_CLASS || meta_mem[9] !== CASE_STRIDE ||
            meta_mem[10] !== DESCRIPTOR_WORDS ||
            meta_mem[11] !== NUMERIC_WORDS) begin
            $display("FAIL: vector geometry %0dx%0d vec=%0d credits=%0d retry=%0d hop=%0d nodes=%0d does not match this elaboration %0dx%0d vec=%0d credits=%0d retry=%0d hop=%0d nodes=%0d",
                     meta_mem[0], meta_mem[1], meta_mem[2], meta_mem[3],
                     meta_mem[4], meta_mem[5], meta_mem[7],
                     MESH_X, MESH_Y, VEC_LEN, CREDITS, RETRY_MAX, HOP_CYCLES, NODES);
            $display("FAIL: vector case count %0d, elaboration %0d", meta_mem[6], MAX_CASES);
            $finish;
        end
        case_count = meta_mem[6];

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        for (ci = 0; ci < case_count; ci = ci + 1) begin
            base = ci * NODES * VEC_LEN;
            case_base = ci * CASE_STRIDE;
            alg = case_mem[case_base + 0][1:0];
            rorder = case_mem[case_base + 1][7:0];
            numeric_descriptor_id = case_mem[case_base + 2];
            instruction_subopcode = case_mem[case_base + 3][7:0];
            inject_node = case_mem[case_base + 4][7:0];
            inject_dir = case_mem[case_base + 5][1:0];
            expect_trap = case_mem[case_base + 6][0];
            do_inject = case_mem[case_base + 6][1];
            for (j = 0; j < DESCRIPTOR_WORDS; j = j + 1)
                communication_descriptor[j*32 +: 32] =
                    communication_mem[ci*DESCRIPTOR_WORDS + j];
            for (j = 0; j < NUMERIC_WORDS; j = j + 1)
                numeric_descriptor[j*32 +: 32] =
                    numeric_mem[ci*NUMERIC_WORDS + j];
            #1;
            check_descriptor_decode(case_base);

            // load the contributions of this case into every participant
            for (n = 0; n < NODES; n = n + 1)
                for (j = 0; j < VEC_LEN; j = j + 1) begin
                    @(posedge clk);
                    load_valid <= 1'b1;
                    load_node <= n[7:0];
                    load_index <= j[7:0];
                    load_data <= contrib_mem[base + n*VEC_LEN + j];
                end
            @(posedge clk);
            load_valid <= 1'b0;
            @(posedge clk);

            wire_before = total_wire_flits;
            crc_before = total_crc_errors;
            retry_before = total_retry_events;
            replay_before = total_replayed_flits;
            stall_before = total_credit_stall_cycles;

            @(posedge clk);
            start <= 1'b1;
            @(posedge clk);
            start <= 1'b0;
            if (do_inject) begin
                inject_valid <= 1'b1;
                @(posedge clk);
                inject_valid <= 1'b0;
            end
            @(posedge clk);
            @(posedge clk);

            guard = 0;
            while (!all_done && guard < TIMEOUT_CYCLES) begin
                @(posedge clk);
                guard = guard + 1;
            end
            cycles_used = guard;
            if (!all_done) begin
                failures = failures + 1;
                $display("FAIL case %0d: the fabric did not converge in %0d cycles",
                         ci, TIMEOUT_CYCLES);
            end

            wire_delta = total_wire_flits - wire_before;
            crc_delta = total_crc_errors - crc_before;
            retry_delta = total_retry_events - retry_before;
            replay_delta = total_replayed_flits - replay_before;
            stall_delta = total_credit_stall_cycles - stall_before;

            // 1. the trap expectation
            expect_eq32("trap", {31'd0, any_trap}, {31'd0, expect_trap});
            expect_eq32("trap_class", {16'd0, first_trap_class},
                        case_mem[case_base + 56]);

            // 2. the result at every participant
            for (n = 0; n < NODES; n = n + 1) begin
                read_node = n[7:0];
                for (j = 0; j < VEC_LEN; j = j + 1) begin
                    read_index = j[7:0];
                    #1;
                    got = read_data;
                    want = expect_mem[base + n*VEC_LEN + j];
                    checks = checks + 1;
                    if (got !== want) begin
                        failures = failures + 1;
                        if (failures < 40)
                            $display("FAIL case %0d node %0d element %0d: got %h wanted %h",
                                     ci, n, j, got, want);
                    end
                end
            end

            // 3. the traversal count the analytical model charges
            expect_eq32("serial_traversals", max_serial_traversals,
                        case_mem[case_base + 8]);
            // 4. the flits the engine offered
            expect_eq32("engine_flits", total_engine_flits_sent,
                        case_mem[case_base + 9]);
            // 5. the steps the schedule ran
            expect_eq32("steps", total_steps, case_mem[case_base + 11]);

            // 6. the fabric's own link crossings against the schedule's
            //    Manhattan distance, and the replay relation
            checks = checks + 1;
            if (!do_inject) begin
                if ((wire_delta !== total_hop_distance) ||
                    (total_hop_distance !== case_mem[case_base + 10]) ||
                    (crc_delta !== 0) || (retry_delta !== 0) ||
                    any_link_error || any_misroute) begin
                    failures = failures + 1;
                    $display("FAIL case %0d: crossings %0d hop_distance %0d expected %0d crc %0d retry %0d link_error %0d misroute %0d",
                             ci, wire_delta, total_hop_distance,
                             case_mem[case_base + 10], crc_delta,
                             retry_delta, any_link_error, any_misroute);
                end
            end else begin
                if ((crc_delta < 1) || (retry_delta < 1) ||
                    (wire_delta <= total_hop_distance) ||
                    any_link_error || any_misroute) begin
                    failures = failures + 1;
                    $display("FAIL case %0d: a corrupted flit did not produce a detected, replayed and recovered traversal (crc %0d retry %0d crossings %0d hop_distance %0d link_error %0d)",
                             ci, crc_delta, retry_delta, wire_delta,
                             total_hop_distance, any_link_error);
                end
            end

            $display("CASE %0d op=%0d alg=%0d order=%0d cycles=%0d traversals=%0d engine_flits=%0d crossings=%0d retries=%0d crc_errors=%0d credit_stalls=%0d replayed=%0d trap=%0d trap_class=%0d record_valid=%0d numeric_valid=%0d numeric_supported=%0d admitted=%0d reason=%0d",
                     ci, decoded_collective_op, alg, rorder, cycles_used,
                     max_serial_traversals,
                     total_engine_flits_sent, wire_delta, retry_delta, crc_delta,
                     stall_delta, replay_delta, any_trap, first_trap_class,
                     descriptor_valid, numeric_descriptor_valid,
                     numeric_semantics_supported, command_admitted,
                     refusal_reason);
        end

        if (failures == 0)
            $display("PASS: A3 LINK mesh=%0dx%0d vec=%0d hop=%0d cases=%0d checks=%0d",
                     MESH_X, MESH_Y, VEC_LEN, HOP_CYCLES, case_count, checks);
        else
            $display("FAILED: A3 LINK mesh=%0dx%0d vec=%0d hop=%0d cases=%0d checks=%0d failures=%0d",
                     MESH_X, MESH_Y, VEC_LEN, HOP_CYCLES, case_count, checks, failures);
        $finish;
    end
endmodule
