`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The design's host load path, exercised end to end on the vehicle geometry.
//
// rtl/abi3/ot_a3_device_top.sv presents its program and descriptor stores as
// abstract macro boundaries and writes them only through host_* -- the
// management processor's path of docs/CHIP_ARCHITECTURE_DESIGN.md section
// 3.4.  The control-plane campaigns preload those stores from the vector
// images because their checkers own reset and start timing; this bench is
// the test that the load path itself works, and it is deliberately run at
// the vehicle defaults (PROGRAM_WORDS = 128, DESC_WORDS = 256: the 4 KiB
// program store and 64 KiB descriptor store of section 11.2), which the
// Qwen3-8B ROM deployment fits -- 74 instructions, 227 descriptor records.
//
//   1. With both stores empty (every row zero) the first Qwen3-8B ROM case
//      must trap, not complete: the load path is load-bearing.
//   2. The program body and descriptor records of that deployment are then
//      written one 32-bit lane at a time through host_*, from the same
//      source-bound images the campaigns read, relocated to row 0 of each
//      store.  No write may be refused.
//   3. The program header is streamed through the admission port; then both
//      entrypoints of the deployment run against the loaded stores and every
//      compared counter (fetched, retired, predicated off, issued, loop
//      iterations, branches, wait-set evaluations), the issue and view pulse
//      counts, the trap class and the completion decision must equal the
//      golden record of testdata/compiler/abi3_deployment.
//   4. A write offered while the transaction is busy, and one aimed past the
//      end of a store, must be refused, reported, and leave the store intact.
//
// The bench is one checker run under two simulators (Icarus, and Verilator
// with --timing); the marker it prints is compared across both by
// tools/rtl_abi3_device_top_host_load.py.
// ---------------------------------------------------------------------------
module tb_a3_device_top_host_load;
    localparam integer PROGRAM_WORDS = 128;
    localparam integer DESC_WORDS    = 256;
    localparam integer IMAGE_PROGRAM_WORDS = 4096;
    localparam integer IMAGE_HEADER_WORDS  = 8192;
    localparam integer IMAGE_DESC_WORDS    = 8192;
    localparam integer IMAGE_SYMBOL_WORDS  = 2048;
    localparam integer CASE_MEM_WORDS = 512;
    localparam integer CASE_STRIDE    = 40;
    localparam integer CASES_TO_RUN   = 2;   // both Qwen3-8B ROM entrypoints

    // -- source-bound images, held host-side -------------------------------
    reg [255:0]  image_program [0:IMAGE_PROGRAM_WORDS-1];
    reg [31:0]   image_header  [0:IMAGE_HEADER_WORDS-1];
    reg [1535:0] image_desc    [0:IMAGE_DESC_WORDS-1];
    reg [31:0]   image_symbol  [0:IMAGE_SYMBOL_WORDS-1];
    reg [31:0]   case_mem      [0:CASE_MEM_WORDS-1];

    // -- the device's stores, empty until the host writes them --------------
    reg [255:0]  program_store [0:PROGRAM_WORDS-1];
    reg [1535:0] desc_store    [0:DESC_WORDS-1];

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg         hdr_in_valid = 1'b0;
    reg         hdr_in_start = 1'b0;
    reg [31:0]  hdr_in_word = 32'd0;
    wire        header_done;
    wire        header_legal;
    wire [3:0]  header_error;
    wire [15:0] header_trap_class;
    wire [31:0] header_instruction_count;
    wire [31:0] header_entrypoint_count;
    wire [63:0] header_max_retired_work;
    wire [31:0] header_entrypoint_descriptor;

    reg         host_we = 1'b0;
    reg         host_sel = 1'b0;
    reg [31:0]  host_row = 32'd0;
    reg [5:0]   host_lane = 6'd0;
    reg [31:0]  host_wdata = 32'd0;
    wire        host_ready;
    wire        host_write_refused;

    reg         start = 1'b0;
    reg [31:0]  cfg_program_base = 32'd0;
    reg [31:0]  cfg_instruction_count = 32'd0;
    reg [31:0]  cfg_entry_pc = 32'd0;
    reg [31:0]  cfg_desc_base = 32'd0;
    reg [31:0]  cfg_desc_count = 32'd0;
    reg [31:0]  cfg_symbol_base = 32'd0;
    reg [31:0]  cfg_symbol_mask = 32'd0;
    reg [63:0]  cfg_max_retired_work = 64'd0;
    reg [31:0]  cfg_state_count = 32'd0;

    wire        busy;
    wire        done;
    wire        complete;
    wire        trapped;
    wire [15:0] trap_class;
    wire [31:0] first_fault_instruction;

    wire         pstore_en;
    wire         pstore_we;
    wire [31:0]  pstore_addr;
    wire [2:0]   pstore_wlane;
    wire [31:0]  pstore_wdata;
    reg  [255:0] pstore_rdata;
    wire          dstore_en;
    wire          dstore_we;
    wire [31:0]   dstore_addr;
    wire [5:0]    dstore_wlane;
    wire [31:0]   dstore_wdata;
    reg  [1535:0] dstore_rdata;
    wire [31:0]  sym_addr;
    wire [31:0]  sym_value = image_symbol[sym_addr[10:0]];

    wire        predicate_read_req;
    wire [31:0] predicate_read_object_id;
    wire [31:0] predicate_read_element_index;

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

    // -- store macros: one synchronous port, 32-bit lanes ------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pstore_rdata <= 256'd0;
        end else if (pstore_en) begin
            if (pstore_we)
                program_store[pstore_addr[6:0]][pstore_wlane*32 +: 32]
                    <= pstore_wdata;
            else
                pstore_rdata <= program_store[pstore_addr[6:0]];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dstore_rdata <= 1536'd0;
        end else if (dstore_en) begin
            if (dstore_we)
                desc_store[dstore_addr[7:0]][dstore_wlane*32 +: 32]
                    <= dstore_wdata;
            else
                dstore_rdata <= desc_store[dstore_addr[7:0]];
        end
    end

    ot_a3_device_top #(
        .PROGRAM_WORDS(PROGRAM_WORDS),
        .DESC_WORDS(DESC_WORDS),
        .STATE_COMPAT(0)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .hdr_in_valid(hdr_in_valid),
        .hdr_in_start(hdr_in_start),
        .hdr_in_word(hdr_in_word),
        .header_done(header_done),
        .header_legal(header_legal),
        .header_error(header_error),
        .header_trap_class(header_trap_class),
        .header_instruction_count(header_instruction_count),
        .header_entrypoint_count(header_entrypoint_count),
        .header_max_retired_work(header_max_retired_work),
        .header_entrypoint_descriptor(header_entrypoint_descriptor),
        .host_we(host_we),
        .host_sel(host_sel),
        .host_row(host_row),
        .host_lane(host_lane),
        .host_wdata(host_wdata),
        .host_ready(host_ready),
        .host_write_refused(host_write_refused),
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
        .pstore_en(pstore_en),
        .pstore_we(pstore_we),
        .pstore_addr(pstore_addr),
        .pstore_wlane(pstore_wlane),
        .pstore_wdata(pstore_wdata),
        .pstore_rdata(pstore_rdata),
        .dstore_en(dstore_en),
        .dstore_we(dstore_we),
        .dstore_addr(dstore_addr),
        .dstore_wlane(dstore_wlane),
        .dstore_wdata(dstore_wdata),
        .dstore_rdata(dstore_rdata),
        .sym_addr(sym_addr),
        .sym_value(sym_value),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        // Qwen3-8B issues no data-dependent predicate; a request here is a
        // failure the timeout below reports.
        .predicate_read_valid(1'b0),
        .predicate_read_value(1'b0),
        .predicate_read_trap_class(16'd0),
        .issue_valid(issue_valid),
        .issue_ready(1'b1),
        .issue_fault(1'b0),
        .issue_trap_class(16'd0),
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
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(),
        .dbg_source_operation_id(),
        .dbg_wait_fault_event(),
        .dbg_loop_action()
    );

    // -- issue / view pulse counters and a predicate-request watchdog -------
    integer issue_seen;
    integer view_seen;
    integer predicate_requests;
    always @(posedge clk) begin
        if (view_valid) view_seen <= view_seen + 1;
        if (predicate_read_req) predicate_requests <= predicate_requests + 1;
    end
    // issue_valid is held until issue_ready; with ready tied high each issue
    // is exactly one cycle wide.
    always @(posedge clk) if (issue_valid) issue_seen <= issue_seen + 1;

    // -- checking ----------------------------------------------------------
    integer checks;
    integer failures;
    task check_equal(input [255:0] what, input [63:0] got, input [63:0] want);
        begin
            checks = checks + 1;
            if (got !== want) begin
                failures = failures + 1;
                $display("FAIL %0s: got %0d want %0d", what, got, want);
            end
        end
    endtask

    integer image_program_base;
    integer image_desc_base;
    integer row;
    integer lane;
    integer guard;
    integer case_index;
    integer base;
    integer host_writes;
    reg [31:0] lane_before;

    task host_write(input sel, input [31:0] r, input [5:0] l, input [31:0] d);
        begin
            host_sel = sel;
            host_row = r;
            host_lane = l;
            host_wdata = d;
            host_we = 1'b1;
            @(negedge clk);
            host_we = 1'b0;
            host_writes = host_writes + 1;
        end
    endtask

    task run_case(input integer index, input expect_loaded);
        begin
            base = index * CASE_STRIDE;
            // Relocate to row 0 of each store; symbols stay at their image
            // address because the symbol file is not behind the load path.
            cfg_program_base = 32'd0;
            cfg_instruction_count = case_mem[base + 1];
            cfg_desc_base = 32'd0;
            cfg_desc_count = case_mem[base + 3];
            cfg_symbol_base = case_mem[base + 4];
            cfg_symbol_mask = case_mem[base + 5];
            cfg_entry_pc = case_mem[base + 7];
            cfg_max_retired_work = {case_mem[base + 9], case_mem[base + 8]};
            cfg_state_count = case_mem[base + 34];
            issue_seen = 0;
            view_seen = 0;
            predicate_requests = 0;
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
            guard = 0;
            while (!done && guard < 4000000) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (!done) begin
                failures = failures + 1;
                $display("FAIL case %0d: transaction timeout", index);
            end
            check_equal("predicate requests", predicate_requests, 64'd0);
            if (expect_loaded) begin
                check_equal("trap class", {48'd0, trap_class},
                            {32'd0, case_mem[base + 14]});
                check_equal("complete", {63'd0, complete},
                            {63'd0, case_mem[base + 10][2]});
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
                check_equal("issue pulses", issue_seen,
                            {32'd0, case_mem[base + 31]});
                check_equal("view pulses", view_seen,
                            {32'd0, case_mem[base + 33]});
                check_equal("views resolved", {32'd0, count_views_resolved},
                            {32'd0, case_mem[base + 33]});
                check_equal("event signal error", {63'd0, event_signal_error},
                            64'd0);
            end else begin
                // Empty stores: the transaction must stop at a trap and
                // retire nothing.
                check_equal("empty-store trapped", {63'd0, trapped}, 64'd1);
                check_equal("empty-store complete", {63'd0, complete}, 64'd0);
                check_equal("empty-store retired", {32'd0, count_retired},
                            64'd0);
                check_equal("empty-store issued", {32'd0, count_issued},
                            64'd0);
            end
            $display("CASE %0d loaded=%0d complete=%0d trap=%0d fetched=%0d retired=%0d issued=%0d views=%0d",
                     index, expect_loaded, complete, trap_class,
                     count_fetched, count_retired, count_issued, view_seen);
        end
    endtask

    initial begin
        $readmemh("a3_program.hex", image_program);
        $readmemh("a3_header.hex", image_header);
        $readmemh("a3_descriptor.hex", image_desc);
        $readmemh("a3_symbol.hex", image_symbol);
        $readmemh("a3_deployment_case.hex", case_mem);
        for (row = 0; row < PROGRAM_WORDS; row = row + 1)
            program_store[row] = 256'd0;
        for (row = 0; row < DESC_WORDS; row = row + 1)
            desc_store[row] = 1536'd0;
        checks = 0;
        failures = 0;
        host_writes = 0;
        issue_seen = 0;
        view_seen = 0;
        predicate_requests = 0;

        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // The first Qwen3-8B ROM case names the image rows to load.
        image_program_base = case_mem[0];
        image_desc_base = case_mem[2];
        if (case_mem[1] > PROGRAM_WORDS || case_mem[3] > DESC_WORDS)
            $fatal(1, "the Qwen3-8B ROM deployment does not fit the vehicle stores");

        // 1. Empty stores: the program must not run.
        run_case(0, 1'b0);

        // 2. Load the program body and the descriptor records, one lane at a
        //    time, exactly as the management processor would.
        check_equal("host ready before load", {63'd0, host_ready}, 64'd1);
        for (row = 0; row < case_mem[1]; row = row + 1)
            for (lane = 0; lane < 8; lane = lane + 1)
                host_write(1'b0, row, lane[5:0],
                           image_program[image_program_base + row][lane*32 +: 32]);
        for (row = 0; row < case_mem[3]; row = row + 1)
            for (lane = 0; lane < 48; lane = lane + 1)
                host_write(1'b1, row, lane[5:0],
                           image_desc[image_desc_base + row][lane*32 +: 32]);
        @(negedge clk);
        check_equal("no write refused during load", {63'd0, host_write_refused},
                    64'd0);
        for (row = 0; row < case_mem[1]; row = row + 1)
            check_equal("program row landed", program_store[row][63:0],
                        image_program[image_program_base + row][63:0]);
        for (row = 0; row < case_mem[3]; row = row + 1)
            check_equal("descriptor row landed", desc_store[row][1535:1472],
                        image_desc[image_desc_base + row][1535:1472]);

        // 3. Header admission through the beat port, then both entrypoints.
        for (case_index = 0; case_index < CASES_TO_RUN; case_index = case_index + 1) begin
            base = case_index * CASE_STRIDE;
            for (row = 0; row < 64; row = row + 1) begin
                hdr_in_valid = 1'b1;
                hdr_in_start = (row == 0);
                hdr_in_word = image_header[case_mem[base + 6] + row];
                @(negedge clk);
            end
            hdr_in_valid = 1'b0;
            hdr_in_start = 1'b0;
            guard = 0;
            while (!header_done && guard < 400) begin
                @(negedge clk);
                guard = guard + 1;
            end
            check_equal("header done", {63'd0, header_done}, 64'd1);
            check_equal("header legal", {63'd0, header_legal},
                        {63'd0, case_mem[base + 10][0]});
            check_equal("header trap class", {48'd0, header_trap_class},
                        {32'd0, case_mem[base + 11]});
            check_equal("header instruction count",
                        {32'd0, header_instruction_count},
                        {32'd0, case_mem[base + 12]});
            check_equal("header entrypoint count",
                        {32'd0, header_entrypoint_count},
                        {32'd0, case_mem[base + 13]});
            check_equal("header max retired work", header_max_retired_work,
                        {case_mem[base + 37], case_mem[base + 36]});
            @(negedge clk);
            run_case(case_index, 1'b1);
        end

        // 4. Refusals: while busy, and past the end of a store.  Neither may
        //    touch the store; both must be reported.
        base = 0;
        cfg_program_base = 32'd0;
        cfg_instruction_count = case_mem[1];
        cfg_desc_base = 32'd0;
        cfg_desc_count = case_mem[3];
        cfg_symbol_base = case_mem[4];
        cfg_symbol_mask = case_mem[5];
        cfg_entry_pc = case_mem[7];
        cfg_max_retired_work = {case_mem[9], case_mem[8]};
        cfg_state_count = case_mem[34];
        lane_before = program_store[0][31:0];
        @(negedge clk);
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;
        @(negedge clk);
        check_equal("busy after start", {63'd0, busy}, 64'd1);
        check_equal("host not ready while busy", {63'd0, host_ready}, 64'd0);
        host_write(1'b0, 32'd0, 6'd0, ~lane_before);
        @(negedge clk);
        check_equal("busy write refused", {63'd0, host_write_refused}, 64'd1);
        check_equal("busy write dropped", {32'd0, program_store[0][31:0]},
                    {32'd0, lane_before});
        guard = 0;
        while (!done && guard < 4000000) begin
            @(negedge clk);
            guard = guard + 1;
        end
        check_equal("transaction after refused write still completes",
                    {63'd0, complete}, {63'd0, case_mem[10][2]});
        // Past the end of each store, and past the last lane, with the
        // transaction idle: refused too.
        rst_n = 1'b0;
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        check_equal("refusal flag clears on reset", {63'd0, host_write_refused},
                    64'd0);
        host_write(1'b0, PROGRAM_WORDS, 6'd0, 32'hdead_beef);
        @(negedge clk);
        check_equal("program row past end refused", {63'd0, host_write_refused},
                    64'd1);
        rst_n = 1'b0;
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        host_write(1'b1, DESC_WORDS, 6'd0, 32'hdead_beef);
        @(negedge clk);
        check_equal("descriptor row past end refused",
                    {63'd0, host_write_refused}, 64'd1);
        rst_n = 1'b0;
        repeat (2) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        host_write(1'b0, 32'd0, 6'd8, 32'hdead_beef);
        @(negedge clk);
        check_equal("program lane past end refused", {63'd0, host_write_refused},
                    64'd1);
        check_equal("program lane past end dropped", {32'd0, program_store[0][31:0]},
                    {32'd0, lane_before});

        if (failures == 0)
            $display("PASS: ABI3 device top host load vehicle_program_words=%0d vehicle_desc_words=%0d host_writes=%0d cases=%0d checks=%0d",
                     PROGRAM_WORDS, DESC_WORDS, host_writes, CASES_TO_RUN, checks);
        else
            $display("FAIL: ABI3 device top host load failures=%0d checks=%0d",
                     failures, checks);
        $finish;
    end
endmodule
