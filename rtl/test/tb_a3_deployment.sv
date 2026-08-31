`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus testbench: the three deployments this program ships, co-simulated.
//
// rtl/test/tb_a3_microsequencer.sv replays 64 vectors that are real ABI 3.0
// programs *written for the campaign*.  This one replays the programs the
// project claims to run -- Qwen3-8B on ROM, Qwen3-8B on HBM, DeepSeek-V4-Flash
// on the wafer -- from their own deployment images, on both entrypoints.
//
// It instantiates the same verification top, unmodified and with the same
// parameters, that the microsequencer campaign drives, so no bespoke wrapper
// stands between the real program and the RTL.  Only the memory images differ:
// tools/build_abi3_deployment_rtl_vectors.py writes the real 256-byte program
// headers, the real 32-byte instruction records, the real descriptor records
// and the request-bound runtime symbols into exactly the four files that top
// reads.
//
// What has to agree, per case, with runtime.sim.device.Device:
//   * program-header admission, its trap class, the instruction and entrypoint
//     counts it publishes, and the retired-work bound it publishes;
//   * every engine issue, in program order: family, subopcode, descriptor ID
//     *and the instruction index that issued it*, which is what ties the
//     comparison to the program counter rather than only to a sequence;
//   * every resolved operand tensor view, in program order then operand order:
//     descriptor, slot, resolved extent, the axis that extent belongs to,
//     element offset and rank;
//   * the fourteen transaction counters plus the views-resolved counter, the
//     completion decision, the trap class and the first faulting instruction.
//
// A divergence does not stop the run.  The first disagreement in a case is
// recorded with a numeric site code (the table below, transcribed identically
// in rtl/test/a3_deployment_harness.cpp), further comparison for that case is
// abandoned because everything after a divergence is downstream of it, and the
// next case starts clean.  A campaign that stopped at the first divergence
// would report one defect where there may be several, and would say nothing
// about the deployments after it.
//
// Engine datapaths are out of scope here exactly as in the sibling campaign:
// the golden model runs with recording no-op engines, so what is compared is
// the instruction stream and not the arithmetic.
// ---------------------------------------------------------------------------
module tb_a3_deployment;
    localparam integer CASE_MEM_WORDS  = 512;
    localparam integer ISSUE_MEM_WORDS = 65536;
    localparam integer VIEW_MEM_WORDS  = 524288;
    localparam integer META_WORDS      = 8;
    localparam integer CASE_STRIDE     = 38;
    localparam integer ISSUE_STRIDE    = 3;
    localparam integer VIEW_STRIDE     = 7;
    // A whole DeepSeek prefill is 29,595 fetched instructions and 39,849
    // resolved views; the guard is generous enough that a real hang is still
    // caught but a long real program is not mistaken for one.
    localparam integer RUN_GUARD       = 40000000;

    // -- divergence site codes -------------------------------------------
    // Numbers, not strings, so the two independently written checkers report
    // the same site the same way with no shared code.
    localparam integer D_NONE                = 0;
    localparam integer D_ISSUE_OPCODE        = 1;
    localparam integer D_ISSUE_DESCRIPTOR    = 2;
    localparam integer D_ISSUE_INDEX         = 3;
    localparam integer D_ISSUE_OVERFLOW      = 4;
    localparam integer D_ISSUE_COUNT         = 5;
    localparam integer D_VIEW_DESCRIPTOR     = 6;
    localparam integer D_VIEW_SLOT           = 7;
    localparam integer D_VIEW_EXTENT         = 8;
    localparam integer D_VIEW_OFFSET         = 9;
    localparam integer D_VIEW_RANK           = 10;
    localparam integer D_VIEW_AXIS           = 11;
    localparam integer D_VIEW_OVERFLOW       = 12;
    localparam integer D_VIEW_COUNT          = 13;
    localparam integer D_VIEW_COUNTER        = 14;
    localparam integer D_HEADER_LEGAL        = 20;
    localparam integer D_HEADER_TRAP         = 21;
    localparam integer D_HEADER_INSTRUCTIONS = 22;
    localparam integer D_HEADER_ENTRYPOINTS  = 23;
    localparam integer D_HEADER_WORK         = 24;
    localparam integer D_COMPLETE            = 30;
    localparam integer D_TRAP_CLASS          = 31;
    localparam integer D_FIRST_FAULT         = 32;
    localparam integer D_FETCHED             = 33;
    localparam integer D_RETIRED             = 34;
    localparam integer D_PREDICATED_OFF      = 35;
    localparam integer D_ISSUED              = 36;
    localparam integer D_LOOP_ITERATIONS     = 37;
    localparam integer D_BRANCHES            = 38;
    localparam integer D_WAIT_EVENTS         = 39;
    localparam integer D_STATE_PREPARES      = 40;
    localparam integer D_STATE_COMMITS       = 41;
    localparam integer D_STATE_DISCARDS      = 42;
    localparam integer D_STATE_READS         = 43;
    localparam integer D_STATE_ADVANCES      = 44;
    localparam integer D_STATE_APPLIED       = 45;
    localparam integer D_STATE_ROWS          = 46;
    localparam integer D_SIGNAL_ERROR        = 47;

    reg [31:0] case_mem  [0:CASE_MEM_WORDS-1];
    reg [31:0] issue_mem [0:ISSUE_MEM_WORDS-1];
    reg [31:0] view_mem  [0:VIEW_MEM_WORDS-1];
    reg [31:0] meta_mem  [0:META_WORDS-1];

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        header_start = 1'b0;
    reg [31:0] cfg_header_base = 32'd0;
    wire       header_done;
    wire       header_legal;
    wire [3:0] header_error;
    wire [15:0] header_trap_class;
    wire [31:0] header_instruction_count;
    wire [31:0] header_entrypoint_count;
    wire [63:0] header_max_retired_work;
    wire [31:0] header_entrypoint_descriptor;

    reg        start = 1'b0;
    reg [31:0] cfg_program_base = 32'd0;
    reg [31:0] cfg_instruction_count = 32'd0;
    reg [31:0] cfg_entry_pc = 32'd0;
    reg [31:0] cfg_desc_base = 32'd0;
    reg [31:0] cfg_desc_count = 32'd0;
    reg [31:0] cfg_symbol_base = 32'd0;
    reg [31:0] cfg_symbol_mask = 32'd0;
    reg [63:0] cfg_max_retired_work = 64'd0;
    reg [31:0] cfg_state_count = 32'd0;

    wire        busy;
    wire        done;
    wire        complete;
    wire        trapped;
    wire [15:0] trap_class;
    wire [31:0] first_fault_instruction;

    reg         issue_ready = 1'b1;
    wire        issue_valid;
    wire [7:0]  issue_family;
    wire [7:0]  issue_sub;
    wire [31:0] issue_descriptor_id;
    wire [31:0] issue_index;

    wire        view_valid;
    wire [31:0] view_descriptor_id;
    wire [2:0]  view_slot;
    wire [31:0] view_extent;
    wire [7:0]  view_extent_axis;
    wire [63:0] view_element_offset;
    wire [7:0]  view_rank;
    wire [31:0] count_views_resolved;

    wire [31:0] count_fetched;
    wire [31:0] count_retired;
    wire [31:0] count_predicated_off;
    wire [31:0] count_issued;
    wire [31:0] count_branches;
    wire [31:0] count_loop_iterations;
    wire [31:0] count_wait_events;
    wire [31:0] count_signals;
    wire [31:0] count_state_prepares;
    wire [31:0] count_state_commits;
    wire [31:0] count_state_discards;
    wire [31:0] count_state_reads;
    wire [31:0] count_state_generation_advances;
    wire [31:0] count_state_commits_applied;
    wire [31:0] count_state_rows_committed;
    wire [63:0] count_state_bytes_written;
    wire [3:0]  loop_depth;
    wire        event_signal_error;
    wire        state_apply_overflow;

    ot_a3_microsequencer_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .header_start(header_start),
        .cfg_header_base(cfg_header_base),
        .header_done(header_done),
        .header_legal(header_legal),
        .header_error(header_error),
        .header_trap_class(header_trap_class),
        .header_instruction_count(header_instruction_count),
        .header_entrypoint_count(header_entrypoint_count),
        .header_max_retired_work(header_max_retired_work),
        .header_entrypoint_descriptor(header_entrypoint_descriptor),
        .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_desc_base(cfg_desc_base),
        .cfg_desc_count(cfg_desc_count),
        .cfg_symbol_base(cfg_symbol_base),
        .cfg_symbol_mask(cfg_symbol_mask),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(busy),
        .done(done),
        .complete(complete),
        .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .issue_ready(issue_ready),
        .issue_valid(issue_valid),
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
        .count_views_resolved(count_views_resolved),
        .count_fetched(count_fetched),
        .count_retired(count_retired),
        .count_predicated_off(count_predicated_off),
        .count_issued(count_issued),
        .count_branches(count_branches),
        .count_loop_iterations(count_loop_iterations),
        .count_wait_events(count_wait_events),
        .count_signals(count_signals),
        .count_state_prepares(count_state_prepares),
        .count_state_commits(count_state_commits),
        .count_state_discards(count_state_discards),
        .count_state_reads(count_state_reads),
        .count_state_generation_advances(count_state_generation_advances),
        .count_state_commits_applied(count_state_commits_applied),
        .count_state_rows_committed(count_state_rows_committed),
        .count_state_bytes_written(count_state_bytes_written),
        .loop_depth(loop_depth),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow)
    );

    // -- per-case bookkeeping ---------------------------------------------
    reg [15:0] lfsr = 16'hbeef;
    reg        capture = 1'b0;
    integer    issue_seen;
    integer    expect_issue_base;
    integer    expect_issue_count;
    integer    issue_word_base;
    integer    view_seen;
    integer    expect_view_base;
    integer    expect_view_count;
    integer    view_word_base;

    integer    case_code;          // divergence site, D_NONE while agreeing
    reg [63:0] case_rtl;
    reg [63:0] case_golden;

    integer    total_issues;
    integer    total_views;
    integer    total_completions;
    integer    diverged_cases;
    integer    signal_flag_cases;
    integer    apply_overflow_cases;
    integer    checks;

    integer    deploy_index;
    integer    deploy_cases;
    integer    deploy_issues;
    integer    deploy_views;
    integer    deploy_diverged;

    // -- engine issue consumer with pseudo-random back-pressure ----------
    // A real program is a long stream of issues; accepting on every cycle would
    // check the order but never the hold.
    always @(posedge clk) begin
        if (rst_n) begin
            lfsr <= {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
            issue_ready <= lfsr[2] | lfsr[9];
        end
    end

    task record;
        input integer code;
        input [63:0] actual;
        input [63:0] expected;
        begin
            if (case_code == D_NONE) begin
                case_code = code;
                case_rtl = actual;
                case_golden = expected;
            end
        end
    endtask

    task check_equal;
        input integer code;
        input [63:0] actual;
        input [63:0] expected;
        begin
            checks = checks + 1;
            if (actual !== expected) record(code, actual, expected);
        end
    endtask

    always @(posedge clk) begin
        if (rst_n && capture && (case_code == D_NONE) &&
            issue_valid && issue_ready) begin
            if (issue_seen >= expect_issue_count) begin
                record(D_ISSUE_OVERFLOW, issue_seen, expect_issue_count);
            end else begin
                issue_word_base = (expect_issue_base + issue_seen) * ISSUE_STRIDE;
                checks = checks + 3;
                if ({issue_family, issue_sub} !== issue_mem[issue_word_base][15:0])
                    record(D_ISSUE_OPCODE, {48'd0, issue_family, issue_sub},
                           {48'd0, issue_mem[issue_word_base][15:0]});
                else if (issue_descriptor_id !== issue_mem[issue_word_base + 1])
                    record(D_ISSUE_DESCRIPTOR, {32'd0, issue_descriptor_id},
                           {32'd0, issue_mem[issue_word_base + 1]});
                // The program counter that issued it.  This is what makes the
                // comparison per-instruction: a branch or a loop trip that came
                // out differently shows up on the very next issue.
                else if (issue_index !== issue_mem[issue_word_base + 2])
                    record(D_ISSUE_INDEX, {32'd0, issue_index},
                           {32'd0, issue_mem[issue_word_base + 2]});
                issue_seen = issue_seen + 1;
                total_issues = total_issues + 1;
                deploy_issues = deploy_issues + 1;
            end
        end
    end

    // -- resolved operand views (amendments A4, A13 and A18) -------------
    always @(posedge clk) begin
        if (rst_n && capture && (case_code == D_NONE) && view_valid) begin
            if (view_seen >= expect_view_count) begin
                record(D_VIEW_OVERFLOW, view_seen, expect_view_count);
            end else begin
                view_word_base = (expect_view_base + view_seen) * VIEW_STRIDE;
                checks = checks + 6;
                if (view_descriptor_id !== view_mem[view_word_base])
                    record(D_VIEW_DESCRIPTOR, {32'd0, view_descriptor_id},
                           {32'd0, view_mem[view_word_base]});
                else if ({29'd0, view_slot} !== view_mem[view_word_base + 1])
                    record(D_VIEW_SLOT, {61'd0, view_slot},
                           {32'd0, view_mem[view_word_base + 1]});
                else if (view_extent !== view_mem[view_word_base + 2])
                    record(D_VIEW_EXTENT, {32'd0, view_extent},
                           {32'd0, view_mem[view_word_base + 2]});
                else if (view_element_offset !== {view_mem[view_word_base + 4],
                                                  view_mem[view_word_base + 3]})
                    record(D_VIEW_OFFSET, view_element_offset,
                           {view_mem[view_word_base + 4],
                            view_mem[view_word_base + 3]});
                else if ({24'd0, view_rank} !== view_mem[view_word_base + 5])
                    record(D_VIEW_RANK, {56'd0, view_rank},
                           {32'd0, view_mem[view_word_base + 5]});
                else if ({24'd0, view_extent_axis} !== view_mem[view_word_base + 6])
                    record(D_VIEW_AXIS, {56'd0, view_extent_axis},
                           {32'd0, view_mem[view_word_base + 6]});
                view_seen = view_seen + 1;
                total_views = total_views + 1;
                deploy_views = deploy_views + 1;
            end
        end
    end

    integer case_index;
    integer base;
    integer guard;
    integer case_count;
    integer deployment_count;
    integer this_deploy;

    task close_deployment;
        begin
            if (deploy_cases > 0)
                $display("DEPLOY %0d cases=%0d diverged=%0d issues=%0d views=%0d",
                         deploy_index, deploy_cases, deploy_diverged,
                         deploy_issues, deploy_views);
        end
    endtask

    initial begin
        $readmemh("a3_deployment_case.hex", case_mem);
        $readmemh("a3_deployment_issue.hex", issue_mem);
        $readmemh("a3_deployment_view.hex", view_mem);
        $readmemh("a3_deployment_meta.hex", meta_mem);
        total_issues = 0;
        total_views = 0;
        total_completions = 0;
        diverged_cases = 0;
        signal_flag_cases = 0;
        apply_overflow_cases = 0;
        checks = 0;
        issue_seen = 0;
        expect_issue_base = 0;
        expect_issue_count = 0;
        issue_word_base = 0;
        view_seen = 0;
        expect_view_base = 0;
        expect_view_count = 0;
        view_word_base = 0;
        case_code = D_NONE;
        case_rtl = 64'd0;
        case_golden = 64'd0;
        case_index = 0;
        base = 0;
        deploy_index = -1;
        deploy_cases = 0;
        deploy_issues = 0;
        deploy_views = 0;
        deploy_diverged = 0;
        case_count = meta_mem[0];
        deployment_count = meta_mem[4];

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        for (case_index = 0; case_index < case_count; case_index = case_index + 1) begin
            base = case_index * CASE_STRIDE;
            case_code = D_NONE;
            case_rtl = 64'd0;
            case_golden = 64'd0;
            this_deploy = case_mem[base + 35] >> 8;
            if (this_deploy !== deploy_index) begin
                close_deployment;
                deploy_index = this_deploy;
                deploy_cases = 0;
                deploy_issues = 0;
                deploy_views = 0;
                deploy_diverged = 0;
            end
            deploy_cases = deploy_cases + 1;

            // -- program header admission ------------------------------
            cfg_header_base = case_mem[base + 6];
            @(negedge clk);
            header_start = 1'b1;
            @(negedge clk);
            header_start = 1'b0;
            guard = 0;
            while (!header_done && guard < 400) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!header_done) $fatal(1, "header admission timeout");
            check_equal(D_HEADER_LEGAL, {63'd0, header_legal},
                        {63'd0, case_mem[base + 10][0]});
            check_equal(D_HEADER_TRAP, {48'd0, header_trap_class},
                        {32'd0, case_mem[base + 11]});
            check_equal(D_HEADER_INSTRUCTIONS, {32'd0, header_instruction_count},
                        {32'd0, case_mem[base + 12]});
            check_equal(D_HEADER_ENTRYPOINTS, {32'd0, header_entrypoint_count},
                        {32'd0, case_mem[base + 13]});
            // The bound the header itself declares.  Words 8/9 are the bound
            // the transaction is *configured* with, which is the same number
            // unless the vector set lowered it to bound the co-simulated
            // prefix; the header must publish what the program says either way.
            check_equal(D_HEADER_WORK, header_max_retired_work,
                        {case_mem[base + 37], case_mem[base + 36]});
            @(negedge clk);

            // -- transaction --------------------------------------------
            cfg_program_base = case_mem[base + 0];
            cfg_instruction_count = case_mem[base + 1];
            cfg_desc_base = case_mem[base + 2];
            cfg_desc_count = case_mem[base + 3];
            cfg_symbol_base = case_mem[base + 4];
            cfg_symbol_mask = case_mem[base + 5];
            cfg_entry_pc = case_mem[base + 7];
            cfg_max_retired_work = {case_mem[base + 9], case_mem[base + 8]};
            cfg_state_count = case_mem[base + 34];
            expect_issue_base = case_mem[base + 30];
            expect_issue_count = case_mem[base + 31];
            expect_view_base = case_mem[base + 32];
            expect_view_count = case_mem[base + 33];
            issue_seen = 0;
            view_seen = 0;
            capture = 1'b1;
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            guard = 0;
            while (!done && guard < RUN_GUARD) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) $fatal(1, "transaction timeout");
            capture = 1'b0;

            // Trap class first: when the RTL stops a program the golden model
            // runs to completion, "trap class 4 where 0 was expected" names the
            // divergence and "complete 0 where 1 was expected" only restates it.
            check_equal(D_TRAP_CLASS, {48'd0, trap_class},
                        {32'd0, case_mem[base + 14]});
            if (trapped)
                check_equal(D_FIRST_FAULT, {32'd0, first_fault_instruction},
                            {32'd0, case_mem[base + 15]});
            check_equal(D_COMPLETE, {63'd0, complete},
                        {63'd0, case_mem[base + 10][2]});
            if (complete) total_completions = total_completions + 1;
            check_equal(D_FETCHED, {32'd0, count_fetched},
                        {32'd0, case_mem[base + 16]});
            check_equal(D_RETIRED, {32'd0, count_retired},
                        {32'd0, case_mem[base + 17]});
            check_equal(D_PREDICATED_OFF, {32'd0, count_predicated_off},
                        {32'd0, case_mem[base + 18]});
            check_equal(D_ISSUED, {32'd0, count_issued},
                        {32'd0, case_mem[base + 19]});
            check_equal(D_LOOP_ITERATIONS, {32'd0, count_loop_iterations},
                        {32'd0, case_mem[base + 20]});
            check_equal(D_BRANCHES, {32'd0, count_branches},
                        {32'd0, case_mem[base + 21]});
            check_equal(D_WAIT_EVENTS, {32'd0, count_wait_events},
                        {32'd0, case_mem[base + 22]});
            check_equal(D_STATE_PREPARES, {32'd0, count_state_prepares},
                        {32'd0, case_mem[base + 23]});
            check_equal(D_STATE_COMMITS, {32'd0, count_state_commits},
                        {32'd0, case_mem[base + 24]});
            check_equal(D_STATE_DISCARDS, {32'd0, count_state_discards},
                        {32'd0, case_mem[base + 25]});
            check_equal(D_STATE_READS, {32'd0, count_state_reads},
                        {32'd0, case_mem[base + 26]});
            check_equal(D_STATE_ADVANCES, {32'd0, count_state_generation_advances},
                        {32'd0, case_mem[base + 27]});
            check_equal(D_STATE_APPLIED, {32'd0, count_state_commits_applied},
                        {32'd0, case_mem[base + 28]});
            check_equal(D_STATE_ROWS, {32'd0, count_state_rows_committed},
                        {32'd0, case_mem[base + 29]});
            check_equal(D_ISSUE_COUNT, {32'd0, issue_seen[31:0]},
                        {32'd0, case_mem[base + 31]});
            check_equal(D_VIEW_COUNT, {32'd0, view_seen[31:0]},
                        {32'd0, case_mem[base + 33]});
            check_equal(D_VIEW_COUNTER, {32'd0, count_views_resolved},
                        {32'd0, case_mem[base + 33]});

            // -- RTL status bits ------------------------------------------
            // event_signal_error is asserted rather than counted, and zero is
            // not a hand-written expectation: after amendment A24 the bit
            // reports exactly one condition -- a signal naming an event ID
            // outside the scoreboard's space -- and amendment A23 makes that
            // condition a refusal at admission (verifier check
            // ``event_id_bound``).  A program that reached this point was
            // admitted, so the ABI says the bit is zero, and a one here is a
            // divergence from the ABI rather than an unexplained status.
            //
            // Before A24 the bit also fired on the second *dynamic* signal of
            // an event ID, which every loop-compressed program does: it was
            // set on all four Qwen cases, 691 signals against 26 IDs.
            //
            // state_apply_overflow still has no golden counterpart --
            // runtime.sim.device.Device publishes nothing to compare it
            // against -- so it stays counted, printed, and required by
            // tools/rtl_abi3_deployment_campaign.py to agree between the two
            // simulators.
            check_equal(D_SIGNAL_ERROR, {63'd0, event_signal_error}, 64'd0);
            if (event_signal_error) signal_flag_cases = signal_flag_cases + 1;
            if (state_apply_overflow)
                apply_overflow_cases = apply_overflow_cases + 1;

            if (case_code != D_NONE) begin
                diverged_cases = diverged_cases + 1;
                deploy_diverged = deploy_diverged + 1;
            end
            $display("CASE %0d tag=%04x %0s code=%0d rtl=%0d golden=%0d issues=%0d/%0d views=%0d/%0d fetched=%0d retired=%0d trap=%0d fault=%0d sigerr=%0d applyovf=%0d",
                     case_index, case_mem[base + 35][15:0],
                     (case_code == D_NONE) ? "OK" : "DIVERGE",
                     case_code, case_rtl, case_golden,
                     issue_seen, case_mem[base + 31],
                     view_seen, case_mem[base + 33],
                     count_fetched, count_retired, trap_class,
                     first_fault_instruction, event_signal_error,
                     state_apply_overflow);
            @(negedge clk);
        end
        close_deployment;

        if (diverged_cases == 0) begin
            if (total_issues !== meta_mem[1]) begin
                $display("FAIL: issue total %0d expected %0d",
                         total_issues, meta_mem[1]);
                $fatal(1, "issue total mismatch");
            end
            if (total_views !== meta_mem[2]) begin
                $display("FAIL: resolved view total %0d expected %0d",
                         total_views, meta_mem[2]);
                $fatal(1, "view total mismatch");
            end
            if (total_completions !== meta_mem[3]) begin
                $display("FAIL: completion total %0d expected %0d",
                         total_completions, meta_mem[3]);
                $fatal(1, "completion total mismatch");
            end
            // A comparison that compared nothing is a defect, not a pass.
            if (total_views === 0) begin
                $display("FAIL: no operand view was resolved; the comparison is vacuous");
                $fatal(1, "no views compared");
            end
            $display("PASS: ABI3 RTL deployment co-simulation deployments=%0d cases=%0d completions=%0d issues=%0d views=%0d signal_flag_cases=%0d apply_overflow_cases=%0d checks=%0d",
                     deployment_count, case_count, total_completions,
                     total_issues, total_views, signal_flag_cases,
                     apply_overflow_cases, checks);
            $finish;
        end else begin
            $display("FAIL: ABI3 RTL deployment co-simulation diverged_cases=%0d of %0d deployments=%0d issues=%0d views=%0d signal_flag_cases=%0d apply_overflow_cases=%0d checks=%0d",
                     diverged_cases, case_count, deployment_count, total_issues,
                     total_views, signal_flag_cases, apply_overflow_cases,
                     checks);
            $fatal(1, "the RTL and runtime.sim.device.Device disagree on a shipped program");
        end
    end
endmodule
