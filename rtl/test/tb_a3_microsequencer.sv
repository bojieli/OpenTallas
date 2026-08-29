`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus testbench for the ABI 3.0 RTL.
//
// Every vector is a real ABI 3.0 deployment built by
// tools/build_abi3_rtl_vectors.py and executed by runtime.sim.device.Device.
// This testbench replays each one through the RTL and requires exact agreement
// on: program-header admission and its trap class; retired, fetched,
// predicated-off, issued, loop-iteration, branch, wait and state counts; the
// engine-issue sequence (family, subopcode, descriptor ID) in order; the
// resolved operand tensor views (descriptor, operand slot, leading extent and
// element offset) in order, which is where amendments A4 and A13 are checked;
// whether the staged state commit was applied or discarded; and the trap class
// and first faulting instruction.
//
// The engine issue port is back-pressured from a free-running LFSR so the
// sequence is checked under stalls, not only under a permanently ready
// consumer.
// ---------------------------------------------------------------------------
module tb_a3_microsequencer;
    localparam integer CASE_MEM_WORDS  = 2048;
    localparam integer ISSUE_MEM_WORDS = 2048;
    localparam integer VIEW_MEM_WORDS  = 8192;
    localparam integer META_WORDS      = 8;
    localparam integer CASE_STRIDE     = 35;
    localparam integer VIEW_STRIDE     = 6;

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
    wire [31:0] view_dim0;
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
        .view_dim0(view_dim0),
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

    // -- engine issue consumer with pseudo-random back-pressure ----------
    reg [15:0] lfsr = 16'hace1;
    reg        capture = 1'b0;
    integer    issue_seen;
    integer    expect_issue_base;
    integer    expect_issue_count;
    integer    total_issues;
    integer    total_traps;
    integer    total_programs;
    integer    total_headers;
    integer    total_views;
    integer    checks;
    reg [31:0] expect_word0;
    reg [31:0] expect_word1;

    integer    view_seen;
    integer    expect_view_base;
    integer    expect_view_count;
    integer    view_slot_base;

    always @(posedge clk) begin
        if (rst_n) begin
            lfsr <= {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
            issue_ready <= lfsr[3] | lfsr[7];
        end
    end

    always @(posedge clk) begin
        if (rst_n && capture && issue_valid && issue_ready) begin
            if (issue_seen >= expect_issue_count) begin
                $display("FAIL: issue overflow, expected %0d", expect_issue_count);
                $fatal(1, "issue overflow");
            end
            expect_word0 = issue_mem[(expect_issue_base + issue_seen) * 2];
            expect_word1 = issue_mem[(expect_issue_base + issue_seen) * 2 + 1];
            if ({issue_family, issue_sub} !== expect_word0[15:0]) begin
                $display("FAIL: issue %0d opcode %02x.%02x expected %04x",
                         issue_seen, issue_family, issue_sub, expect_word0[15:0]);
                $fatal(1, "issue opcode mismatch");
            end
            if (issue_descriptor_id !== expect_word1) begin
                $display("FAIL: issue %0d descriptor %0d expected %0d",
                         issue_seen, issue_descriptor_id, expect_word1);
                $fatal(1, "issue descriptor mismatch");
            end
            issue_seen = issue_seen + 1;
            total_issues = total_issues + 1;
            checks = checks + 2;
        end
    end

    // -- resolved operand views (amendments A4 and A13) ------------------
    // The view port is an observation pulse, not a handshake, so every
    // assertion is one event.  Order is program order, then operand order.
    always @(posedge clk) begin
        if (rst_n && capture && view_valid) begin
            if (view_seen >= expect_view_count) begin
                $display("FAIL: view overflow, expected %0d", expect_view_count);
                $fatal(1, "view overflow");
            end
            view_slot_base = (expect_view_base + view_seen) * VIEW_STRIDE;
            if (view_descriptor_id !== view_mem[view_slot_base]) begin
                $display("FAIL: view %0d descriptor %0d expected %0d", view_seen,
                         view_descriptor_id, view_mem[view_slot_base]);
                $fatal(1, "view descriptor mismatch");
            end
            if ({29'd0, view_slot} !== view_mem[view_slot_base + 1]) begin
                $display("FAIL: view %0d operand slot %0d expected %0d", view_seen,
                         view_slot, view_mem[view_slot_base + 1]);
                $fatal(1, "view slot mismatch");
            end
            if (view_dim0 !== view_mem[view_slot_base + 2]) begin
                $display("FAIL: view %0d (descriptor %0d) leading extent %0d expected %0d",
                         view_seen, view_descriptor_id, view_dim0,
                         view_mem[view_slot_base + 2]);
                $fatal(1, "A13 leading extent mismatch");
            end
            if (view_element_offset !== {view_mem[view_slot_base + 4],
                                         view_mem[view_slot_base + 3]}) begin
                $display("FAIL: view %0d element offset %0d expected %0d", view_seen,
                         view_element_offset,
                         {view_mem[view_slot_base + 4], view_mem[view_slot_base + 3]});
                $fatal(1, "A4 element offset mismatch");
            end
            if ({24'd0, view_rank} !== view_mem[view_slot_base + 5]) begin
                $display("FAIL: view %0d rank %0d expected %0d", view_seen,
                         view_rank, view_mem[view_slot_base + 5]);
                $fatal(1, "view rank mismatch");
            end
            view_seen = view_seen + 1;
            total_views = total_views + 1;
            checks = checks + 5;
        end
    end

    integer case_index;
    integer base;
    integer guard;
    integer case_count;

    task check_equal;
        input [255:0] label;
        input [63:0] actual;
        input [63:0] expected;
        begin
            checks = checks + 1;
            if (actual !== expected) begin
                $display("FAIL: case %0d %0s: %0d expected %0d",
                         case_index, label, actual, expected);
                $fatal(1, "mismatch");
            end
        end
    endtask

    initial begin
        $readmemh("a3_case.hex", case_mem);
        $readmemh("a3_issue.hex", issue_mem);
        $readmemh("a3_view.hex", view_mem);
        $readmemh("a3_meta.hex", meta_mem);
        total_issues = 0;
        total_traps = 0;
        total_programs = 0;
        total_headers = 0;
        total_views = 0;
        checks = 0;
        issue_seen = 0;
        expect_issue_base = 0;
        expect_issue_count = 0;
        view_seen = 0;
        expect_view_base = 0;
        expect_view_count = 0;
        view_slot_base = 0;
        case_index = 0;
        case_count = meta_mem[0];

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        for (case_index = 0; case_index < case_count; case_index = case_index + 1) begin
            base = case_index * CASE_STRIDE;

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
            total_headers = total_headers + 1;
            check_equal("header legal", {63'd0, header_legal},
                        {63'd0, case_mem[base + 10][0]});
            check_equal("header trap class", {48'd0, header_trap_class},
                        {32'd0, case_mem[base + 11]});
            if (case_mem[base + 10][0]) begin
                check_equal("header instruction count",
                            {32'd0, header_instruction_count},
                            {32'd0, case_mem[base + 12]});
                check_equal("header entrypoint count",
                            {32'd0, header_entrypoint_count},
                            {32'd0, case_mem[base + 13]});
            end
            @(negedge clk);

            // -- transaction --------------------------------------------
            if (case_mem[base + 10][1]) begin
                total_programs = total_programs + 1;
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
                while (!done && guard < 200000) begin
                    @(negedge clk);
                    guard = guard + 1;
                end
                if (!done) $fatal(1, "transaction timeout");
                capture = 1'b0;

                check_equal("complete", {63'd0, complete},
                            {63'd0, case_mem[base + 10][2]});
                check_equal("trap class", {48'd0, trap_class},
                            {32'd0, case_mem[base + 14]});
                if (trapped) begin
                    total_traps = total_traps + 1;
                    check_equal("first fault", {32'd0, first_fault_instruction},
                                {32'd0, case_mem[base + 15]});
                end
                check_equal("fetched", {32'd0, count_fetched},
                            {32'd0, case_mem[base + 16]});
                check_equal("retired", {32'd0, count_retired},
                            {32'd0, case_mem[base + 17]});
                check_equal("predicated off", {32'd0, count_predicated_off},
                            {32'd0, case_mem[base + 18]});
                check_equal("issued", {32'd0, count_issued},
                            {32'd0, case_mem[base + 19]});
                check_equal("loop iterations", {32'd0, count_loop_iterations},
                            {32'd0, case_mem[base + 20]});
                check_equal("branches", {32'd0, count_branches},
                            {32'd0, case_mem[base + 21]});
                check_equal("wait events", {32'd0, count_wait_events},
                            {32'd0, case_mem[base + 22]});
                check_equal("state prepares", {32'd0, count_state_prepares},
                            {32'd0, case_mem[base + 23]});
                check_equal("state commits", {32'd0, count_state_commits},
                            {32'd0, case_mem[base + 24]});
                check_equal("state discards", {32'd0, count_state_discards},
                            {32'd0, case_mem[base + 25]});
                check_equal("state reads", {32'd0, count_state_reads},
                            {32'd0, case_mem[base + 26]});
                check_equal("state generation advances",
                            {32'd0, count_state_generation_advances},
                            {32'd0, case_mem[base + 27]});
                check_equal("state commits applied",
                            {32'd0, count_state_commits_applied},
                            {32'd0, case_mem[base + 28]});
                check_equal("state rows committed",
                            {32'd0, count_state_rows_committed},
                            {32'd0, case_mem[base + 29]});
                check_equal("issue count", {32'd0, issue_seen[31:0]},
                            {32'd0, case_mem[base + 31]});
                check_equal("resolved view count", {32'd0, view_seen[31:0]},
                            {32'd0, case_mem[base + 33]});
                check_equal("views resolved counter",
                            {32'd0, count_views_resolved},
                            {32'd0, case_mem[base + 33]});
                check_equal("event single assignment", {63'd0, event_signal_error},
                            64'd0);
                @(negedge clk);
            end
        end

        if (total_issues !== meta_mem[1]) begin
            $display("FAIL: issue total %0d expected %0d", total_issues, meta_mem[1]);
            $fatal(1, "issue total mismatch");
        end
        // A view comparison that compared nothing is a defect, not a pass.
        if (total_views !== meta_mem[4]) begin
            $display("FAIL: resolved view total %0d expected %0d",
                     total_views, meta_mem[4]);
            $fatal(1, "view total mismatch");
        end
        if (total_views === 0) begin
            $display("FAIL: no operand view was resolved; the A4/A13 comparison is vacuous");
            $fatal(1, "no views compared");
        end
        $display("PASS: ABI3 RTL microsequencer cases=%0d headers=%0d programs=%0d issues=%0d views=%0d traps=%0d checks=%0d",
                 case_count, total_headers, total_programs, total_issues,
                 total_views, total_traps, checks);
        $finish;
    end
endmodule
