`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the dependent-boundary control probe.
//
// The top (rtl/test/a3_boundary_control_top.sv) drives one dependent boundary
// per case across ot_a3_issue_record_store, ot_a3_event_scoreboard and
// ot_a3_mesh_router, and reports the span and its parts.  This checker runs
// every case, compares the protocol outcome with the case table's prediction,
// requires the structural invariants to hold, and prints one line per case for
// the campaign to parse.  It predicts no cycle count: the cycles are the
// measurement.
//
// A divergence does not stop the run -- the same rule the deployment
// co-simulation follows -- so one wrong case does not hide the state of the
// others.  A second checker (rtl/test/a3_boundary_control_harness.cpp) is
// written independently against the same top.
// ---------------------------------------------------------------------------
module tb_a3_boundary_control;
    localparam integer CASE_STRIDE = 16;
    localparam integer GUARD       = 400000;

    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;

    reg        run = 1'b0;
    reg [31:0] run_case = 32'd0;
    wire       busy, done;
    wire [31:0] boundary_cycles, boundary_control_cycles;
    wire [31:0] span_retire, span_mesh, span_wait, span_admit;
    wire [15:0] obs_trap_class;
    wire       obs_wait_ok, obs_stalled;
    wire [31:0] obs_mesh_local_deliveries, obs_wait_count, obs_signal_count;
    wire [5:0] obs_max_outstanding;
    wire       obs_protocol_error, obs_signal_error, obs_misroute;
    wire [31:0] obs_timeout;
    reg [31:0] case_rd_addr = 32'd0;
    wire [31:0] case_rd_data;
    reg [31:0] meta_rd_addr = 32'd0;
    wire [31:0] meta_rd_data;

    ot_a3_boundary_control_top dut (
        .clk(clk), .rst_n(rst_n), .run(run), .run_case(run_case),
        .busy(busy), .done(done),
        .boundary_cycles(boundary_cycles),
        .boundary_control_cycles(boundary_control_cycles),
        .span_retire(span_retire), .span_mesh(span_mesh),
        .span_wait(span_wait), .span_admit(span_admit),
        .obs_trap_class(obs_trap_class), .obs_wait_ok(obs_wait_ok),
        .obs_stalled(obs_stalled),
        .obs_mesh_local_deliveries(obs_mesh_local_deliveries),
        .obs_wait_count(obs_wait_count), .obs_signal_count(obs_signal_count),
        .obs_max_outstanding(obs_max_outstanding),
        .obs_protocol_error(obs_protocol_error),
        .obs_signal_error(obs_signal_error), .obs_misroute(obs_misroute),
        .obs_timeout(obs_timeout),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data)
    );

    integer case_count;
    integer index;
    integer guard;
    integer checks;
    integer failures;
    integer base;
    integer producers, expect_trap, expect_ok, expect_stalled, tag, dest_x;
    integer leave_pending, unsignalled;
    integer code;

    task read_case;
        input integer word;
        output integer value;
        begin
            case_rd_addr = base + word;
            @(negedge clk);
            value = case_rd_data;
        end
    endtask

    task check_eq;
        input integer site;
        input integer actual;
        input integer expected;
        begin
            checks = checks + 1;
            if (actual !== expected && code == 0) code = site;
        end
    endtask

    initial begin
        checks = 0;
        failures = 0;
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (4) @(negedge clk);
        meta_rd_addr = 32'd0;
        @(negedge clk);
        case_count = meta_rd_data;
        if (case_count <= 0) $fatal(1, "the case table is empty");

        for (index = 0; index < case_count; index = index + 1) begin
            base = index * CASE_STRIDE;
            read_case(0,  producers);
            read_case(5,  leave_pending);
            read_case(9,  dest_x);
            read_case(10, expect_trap);
            read_case(11, expect_ok);
            read_case(12, unsignalled);
            read_case(13, tag);
            expect_stalled = leave_pending;
            code = 0;

            run_case = index;
            run = 1'b1;
            @(negedge clk);
            run = 1'b0;
            guard = 0;
            while (!done && guard < GUARD) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) $fatal(1, "case %0d did not finish", index);

            // -- the protocol outcome, against the case table --------------
            check_eq(1, {16'd0, obs_trap_class}, expect_trap);
            check_eq(2, obs_wait_ok ? 1 : 0, expect_ok);
            check_eq(3, obs_stalled ? 1 : 0, expect_stalled);
            // -- structural invariants -------------------------------------
            check_eq(4, obs_timeout, 0);
            check_eq(5, obs_protocol_error ? 1 : 0, 0);
            check_eq(6, obs_signal_error ? 1 : 0, 0);
            check_eq(7, obs_misroute ? 1 : 0, 0);
            check_eq(8, obs_wait_count, 1);
            // every producer of a non-unsignalled case signals exactly once
            check_eq(9, obs_signal_count,
                     unsignalled ? 0 : (leave_pending ? producers : producers));
            // a boundary that measured nothing is a defect, not a measurement
            checks = checks + 1;
            if (boundary_cycles == 0 && code == 0) code = 10;
            // the parts must account for the whole
            check_eq(11, span_retire + span_mesh + span_wait + span_admit,
                     boundary_cycles);
            check_eq(12, boundary_cycles - span_mesh, boundary_control_cycles);

            if (code != 0) failures = failures + 1;
            $display("BCASE %0d tag=%0d %0s site=%0d boundary=%0d control=%0d retire=%0d mesh=%0d wait=%0d admit=%0d trap=%0d ok=%0d stalled=%0d producers=%0d hops=%0d waits=%0d signals=%0d maxout=%0d local=%0d",
                     index, tag, (code == 0) ? "OK" : "DIVERGE", code,
                     boundary_cycles, boundary_control_cycles,
                     span_retire, span_mesh, span_wait, span_admit,
                     obs_trap_class, obs_wait_ok, obs_stalled,
                     producers, dest_x, obs_wait_count, obs_signal_count,
                     obs_max_outstanding, obs_mesh_local_deliveries);
            @(negedge clk);
        end

        if (failures == 0)
            $display("PASS: ABI3 dependent-boundary control probe cases=%0d checks=%0d",
                     case_count, checks);
        else begin
            $display("FAIL: ABI3 dependent-boundary control probe cases=%0d checks=%0d failures=%0d",
                     case_count, checks, failures);
            $fatal(1, "the probe disagreed with the case table");
        end
        $finish;
    end
endmodule
