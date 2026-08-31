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
    parameter integer HOP_CYCLES  = 1;
    parameter integer ACK_TIMEOUT = 4096;
    parameter integer MAX_CASES   = 10;
    parameter integer CASE_STRIDE = 16;
    parameter integer TIMEOUT_CYCLES = 2000000;

    localparam integer NODES = MESH_X * MESH_Y;
    localparam integer VECWORDS = MAX_CASES * NODES * VEC_LEN;

    reg [31:0] meta_mem    [0:7];
    reg [31:0] case_mem    [0:MAX_CASES*CASE_STRIDE-1];
    reg [31:0] contrib_mem [0:VECWORDS-1];
    reg [31:0] expect_mem  [0:VECWORDS-1];

    reg [1023:0] path_meta;
    reg [1023:0] path_case;
    reg [1023:0] path_contrib;
    reg [1023:0] path_expect;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        start = 1'b0;
    reg [7:0]  op = 8'd0;
    reg [1:0]  alg = 2'd0;
    reg [7:0]  rorder = 8'd1;
    reg [3:0]  root_x = 4'd0;
    reg [3:0]  root_y = 4'd0;
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
        .ACK_TIMEOUT(ACK_TIMEOUT), .HOP_CYCLES(HOP_CYCLES)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .start(start), .op(op), .alg(alg), .reduction_order(rorder),
        .root_x(root_x), .root_y(root_y),
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

    initial begin
        if (!$value$plusargs("META=%s", path_meta))    path_meta = "meta.hex";
        if (!$value$plusargs("CASE=%s", path_case))    path_case = "case.hex";
        if (!$value$plusargs("CONTRIB=%s", path_contrib)) path_contrib = "contrib.hex";
        if (!$value$plusargs("EXPECT=%s", path_expect)) path_expect = "expect.hex";
        $readmemh(path_meta, meta_mem);
        $readmemh(path_case, case_mem);
        $readmemh(path_contrib, contrib_mem);
        $readmemh(path_expect, expect_mem);

        checks = 0;
        failures = 0;

        // The vector set states the geometry it was generated for.  An
        // elaboration that does not match it is refused, not tolerated.
        if (meta_mem[0] !== MESH_X || meta_mem[1] !== MESH_Y ||
            meta_mem[2] !== VEC_LEN || meta_mem[3] !== CREDITS ||
            meta_mem[4] !== RETRY_MAX || meta_mem[5] !== HOP_CYCLES ||
            meta_mem[6] !== MAX_CASES || meta_mem[7] !== NODES) begin
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
            op = case_mem[ci*CASE_STRIDE + 0][7:0];
            alg = case_mem[ci*CASE_STRIDE + 1][1:0];
            rorder = case_mem[ci*CASE_STRIDE + 2][7:0];
            root_x = case_mem[ci*CASE_STRIDE + 3][3:0];
            root_y = case_mem[ci*CASE_STRIDE + 4][3:0];
            inject_node = case_mem[ci*CASE_STRIDE + 5][7:0];
            inject_dir = case_mem[ci*CASE_STRIDE + 6][1:0];
            expect_trap = case_mem[ci*CASE_STRIDE + 7][0];
            do_inject = case_mem[ci*CASE_STRIDE + 7][1];

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
            if (expect_trap && any_trap)
                if (first_trap_class !== 16'd11) begin
                    failures = failures + 1;
                    $display("FAIL case %0d: trap class %0d, expected 11 (LINK_OR_NOC)",
                             ci, first_trap_class);
                end

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
                        case_mem[ci*CASE_STRIDE + 8]);
            // 4. the flits the engine offered
            expect_eq32("engine_flits", total_engine_flits_sent,
                        case_mem[ci*CASE_STRIDE + 9]);
            // 5. the steps the schedule ran
            expect_eq32("steps", total_steps, case_mem[ci*CASE_STRIDE + 11]);

            // 6. the fabric's own link crossings against the schedule's
            //    Manhattan distance, and the replay relation
            checks = checks + 1;
            if (!do_inject) begin
                if ((wire_delta !== total_hop_distance) ||
                    (total_hop_distance !== case_mem[ci*CASE_STRIDE + 10]) ||
                    (crc_delta !== 0) || (retry_delta !== 0) ||
                    any_link_error || any_misroute) begin
                    failures = failures + 1;
                    $display("FAIL case %0d: crossings %0d hop_distance %0d expected %0d crc %0d retry %0d link_error %0d misroute %0d",
                             ci, wire_delta, total_hop_distance,
                             case_mem[ci*CASE_STRIDE + 10], crc_delta,
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

            $display("CASE %0d op=%0d alg=%0d order=%0d cycles=%0d traversals=%0d engine_flits=%0d crossings=%0d retries=%0d crc_errors=%0d credit_stalls=%0d replayed=%0d trap=%0d",
                     ci, op, alg, rorder, cycles_used, max_serial_traversals,
                     total_engine_flits_sent, wire_delta, retry_delta, crc_delta,
                     stall_delta, replay_delta, any_trap);
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
