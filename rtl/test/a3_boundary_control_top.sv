`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The control half of a dependent boundary, measured on the design's own
// front-end modules (docs/CHIP_ARCHITECTURE_DESIGN.md sections 3.6 and 13
// item 13).
//
// Section 3.6 names five terms of the exposed dependent chain: "the last
// result, mesh transfer, operand readiness, queue admission, and acknowledged
// completion".  Three of them are control-path terms and every one of them
// has design RTL today:
//
//   acknowledged completion  rtl/abi3/ot_a3_issue_record_store.sv, whose
//                            retirement carries the producer's event to
//                            rtl/abi3/ot_a3_event_scoreboard.sv, which sets
//                            `signalled` (and `published` under release);
//   mesh transfer            rtl/abi3/ot_a3_mesh_router.sv, one real hop
//                            between node (0,0) and node (dest_x, 0);
//   queue admission          the issue record store's `alloc_ready` under the
//                            per-queue depth and the per-die outstanding
//                            bound, plus the scoreboard's wait-set evaluation
//                            (twelve producers looked up four at a time over
//                            three chunks, rescanned while any is pending).
//
// The two terms this top does NOT measure are named in the artifact and are
// not modelled here at all: the producer tile's own last-result path, and the
// operand broadcast into the consumer tile's activation FIFO (no design RTL
// exists for the broadcast; the T64 bench models an H-tree and its record
// already declares that a `does_not_establish`).  A boundary composed from
// this top alone would be a control-path lower bound, and the campaign says
// so rather than calling it the boundary section 13 item 13 asks for.
//
// One case is one dependent boundary:
//
//   t0  the producer's LAST completion is acknowledged at the issue record
//       store (`complete_valid`), which is where a real engine's completion
//       enters the front end;
//   ..  the store retires it and the scoreboard signals the event;
//   ..  one flit carrying the retired event travels dest_x hops through the
//       mesh to the consumer's node;
//   ..  the consumer starts its wait set over the producer events;
//   ..  the wait passes and the consumer is admitted to its engine queue;
//   t1  the cycle that admission is accepted.
//
//   boundary_cycles = t1 - t0, and the four spans between them are recorded
//   separately so the total is attributable rather than a single number.
//
// The environment this top provides is a driver and nothing else: it presents
// handshakes and counts clocks.  Every latency it reports is produced inside
// one of the four instantiated design modules.
//
// Case table (`bc_case.hex`, CASE_STRIDE 32-bit words per case; the layout is
// transcribed identically in rtl/test/tb_a3_boundary_control.sv and
// rtl/test/a3_boundary_control_harness.cpp):
//   0 producer_count (1..12)      6 pending_delay
//   1 ordering byte               7 queue index
//   2 acquire flag                8 preload (operations already in the store)
//   3 release flag                9 dest_x (mesh hops)
//   4 first event id             10 expect_trap_class
//   5 leave_one_pending          11 expect_wait_ok
//                                12 unsignalled_producer (provokes trap 13)
//                                13 tag
// ---------------------------------------------------------------------------
module ot_a3_boundary_control_top #(
    parameter integer EVENTS      = ot_a3_pkg::A3_EVENT_COUNT,
    parameter integer IRS_ENTRIES = ot_a3_pkg::A3_IRS_ENTRIES,
    parameter integer QUEUES      = ot_a3_pkg::A3_QUEUE_COUNT,
    parameter integer CASE_WORDS  = 4096,
    parameter integer META_WORDS  = 8,
    parameter integer CASE_STRIDE = 16,
    parameter integer MESH_X      = 4
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        run,
    input  wire [31:0] run_case,
    output reg         busy,
    output reg         done,

    // -- the measurement, valid while done ---------------------------------
    output reg  [31:0] boundary_cycles,
    output reg  [31:0] boundary_control_cycles,
    output reg  [31:0] span_retire,
    output reg  [31:0] span_mesh,
    output reg  [31:0] span_wait,
    output reg  [31:0] span_admit,
    output reg  [15:0] obs_trap_class,
    output reg         obs_wait_ok,
    output reg         obs_stalled,
    output reg  [31:0] obs_mesh_local_deliveries,
    output reg  [31:0] obs_wait_count,
    output reg  [31:0] obs_signal_count,
    output reg  [5:0]  obs_max_outstanding,
    output reg         obs_protocol_error,
    output reg         obs_signal_error,
    output reg         obs_misroute,
    output reg  [31:0] obs_timeout,

    // -- case table read-back ----------------------------------------------
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data
);
    localparam integer FLIT_W = ot_a3_link_pkg::FLIT_W;
    localparam integer GUARD  = 100000;

    reg [31:0] case_mem [0:CASE_WORDS-1];
    reg [31:0] meta_mem [0:META_WORDS-1];
    initial begin
        $readmemh("bc_case.hex", case_mem);
        $readmemh("bc_meta.hex", meta_mem);
    end
    assign case_rd_data = (case_rd_addr < CASE_WORDS) ? case_mem[case_rd_addr] : 32'd0;
    assign meta_rd_data = (meta_rd_addr < META_WORDS) ? meta_mem[meta_rd_addr] : 32'd0;

    // -- the free-running clock counter every span is measured against -----
    reg [31:0] tick;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tick <= 32'd0;
        else        tick <= tick + 32'd1;
    end

    // -- the issue record store: queue admission and acknowledged completion
    reg        irs_clear;
    reg [4:0]  alloc_queue;
    wire       alloc_ready;
    wire [4:0] free_slot;
    reg        alloc_valid;
    reg [4:0]  alloc_slot;
    reg [31:0] alloc_serial;
    reg [31:0] alloc_pc;
    reg [31:0] alloc_event_id;
    reg        alloc_release;
    reg        irs_complete_valid;
    reg [4:0]  irs_complete_slot;
    wire       retire_valid;
    wire [4:0] retire_slot;
    wire [31:0] retire_serial;
    wire [31:0] retire_event_id;
    wire       retire_release;
    wire       retire_event_last;
    wire       retire_fault;
    wire       fault_valid;
    wire [4:0] fault_slot;
    wire [31:0] fault_serial;
    wire [31:0] fault_pc;
    wire [15:0] fault_trap_class;
    wire [5:0] outstanding;
    wire [5:0] outstanding_with_event;
    wire       any_outstanding;
    wire [5:0] max_outstanding;
    wire       irs_protocol_error;

    ot_a3_issue_record_store #(.ENTRIES(IRS_ENTRIES), .QUEUES(QUEUES)) u_irs (
        .clk(clk), .rst_n(rst_n), .clear(irs_clear),
        .alloc_queue(alloc_queue), .alloc_ready(alloc_ready), .free_slot(free_slot),
        .alloc_valid(alloc_valid), .alloc_slot(alloc_slot), .alloc_serial(alloc_serial),
        .alloc_pc(alloc_pc), .alloc_event_id(alloc_event_id), .alloc_release(alloc_release),
        .complete_valid(irs_complete_valid), .complete_slot(irs_complete_slot),
        .complete_fault(1'b0), .complete_trap_class(16'd0),
        .retire_valid(retire_valid), .retire_slot(retire_slot),
        .retire_serial(retire_serial), .retire_event_id(retire_event_id),
        .retire_release(retire_release), .retire_event_last(retire_event_last),
        .retire_fault(retire_fault),
        .fault_valid(fault_valid), .fault_slot(fault_slot), .fault_serial(fault_serial),
        .fault_pc(fault_pc), .fault_trap_class(fault_trap_class),
        .outstanding(outstanding), .outstanding_with_event(outstanding_with_event),
        .any_outstanding(any_outstanding), .max_outstanding(max_outstanding),
        .irs_protocol_error(irs_protocol_error)
    );

    // -- the event scoreboard: the wait check --------------------------------
    reg         sb_clear;
    reg         sb_issue_valid;
    reg  [31:0] sb_issue_event;
    reg         wait_start;
    reg  [511:0] wait_payload;
    reg         wait_acquire;
    wire        wait_busy;
    wire        wait_done;
    wire        sb_wait_ok;
    wire [15:0] sb_trap_class;
    wire [31:0] sb_fault_event;
    wire        sb_wait_stalled;
    wire        sb_signal_error;
    wire [31:0] sb_signal_count;
    wire [31:0] sb_wait_count;

    ot_a3_event_scoreboard #(.EVENTS(EVENTS)) u_sb (
        .clk(clk), .rst_n(rst_n), .clear(sb_clear),
        .issue_valid(sb_issue_valid), .issue_event_id(sb_issue_event),
        // the acknowledged-completion path: the store's retirement, not the
        // checker, is what signals an event here
        .complete_valid(retire_valid && !retire_fault &&
                        (retire_event_id != ot_a3_pkg::A3_NO_ID)),
        .complete_event_id(retire_event_id),
        .complete_release(retire_release),
        .complete_last(retire_event_last),
        .control_signal_valid(1'b0), .control_signal_event_id(32'd0),
        .control_signal_release(1'b0),
        .signal_error(sb_signal_error),
        .wait_start(wait_start), .wait_payload(wait_payload),
        .wait_acquire(wait_acquire),
        .wait_busy(wait_busy), .wait_done(wait_done), .wait_ok(sb_wait_ok),
        .wait_trap_class(sb_trap_class), .wait_fault_event(sb_fault_event),
        .wait_stalled(sb_wait_stalled),
        .signal_count(sb_signal_count), .wait_count(sb_wait_count)
    );

    // -- the mesh: MESH_X routers in a row, one real hop per column ----------
    reg  [4:0]            local_in_valid  [0:MESH_X-1];
    reg  [FLIT_W-1:0]     local_in_flit   [0:MESH_X-1];
    wire [4:0]            r_in_valid      [0:MESH_X-1];
    wire [5*FLIT_W-1:0]   r_in_flit       [0:MESH_X-1];
    wire [4:0]            r_in_ready      [0:MESH_X-1];
    wire [4:0]            r_out_valid     [0:MESH_X-1];
    wire [5*FLIT_W-1:0]   r_out_flit      [0:MESH_X-1];
    wire [4:0]            r_out_ready     [0:MESH_X-1];
    wire [31:0]           r_forwarded     [0:MESH_X-1];
    wire [31:0]           r_local         [0:MESH_X-1];
    wire                  r_misroute      [0:MESH_X-1];

    genvar gx;
    generate
        for (gx = 0; gx < MESH_X; gx = gx + 1) begin : g_router
            // Port order in the router: 0 EAST, 1 WEST, 2 SOUTH, 3 NORTH,
            // 4 LOCAL.  Only the forward direction is wired.  The routers'
            // crossbars are combinational by design ("every cycle of a
            // traversal is spent in the link channel, not in the router"), so
            // wiring both directions between two adjacent routers closes a
            // combinational loop -- Verilator reports it as UNOPTFLAT, which
            // is the tool saying what the module header already says: two
            // routers may not be placed back to back without the link channel
            // between them.  This probe carries one flit one way and wires one
            // way; it is not a fabric.
            assign r_in_valid[gx][0] = 1'b0;
            assign r_in_valid[gx][1] = (gx > 0) ? r_out_valid[gx-1][0] : 1'b0;
            assign r_in_valid[gx][2] = 1'b0;
            assign r_in_valid[gx][3] = 1'b0;
            assign r_in_valid[gx][4] = local_in_valid[gx][4];
            assign r_in_flit[gx][0*FLIT_W +: FLIT_W] = {FLIT_W{1'b0}};
            assign r_in_flit[gx][1*FLIT_W +: FLIT_W] =
                (gx > 0) ? r_out_flit[gx-1][0*FLIT_W +: FLIT_W] : {FLIT_W{1'b0}};
            assign r_in_flit[gx][2*FLIT_W +: FLIT_W] = {FLIT_W{1'b0}};
            assign r_in_flit[gx][3*FLIT_W +: FLIT_W] = {FLIT_W{1'b0}};
            assign r_in_flit[gx][4*FLIT_W +: FLIT_W] = local_in_flit[gx];
            // every downstream port accepts on the cycle it is offered: this
            // top measures the router's own traversal, not a credit scheme
            assign r_out_ready[gx] = 5'b11111;

            ot_a3_mesh_router #(.FLIT_W(FLIT_W), .MY_X(gx), .MY_Y(0)) u_router (
                .clk(clk), .rst_n(rst_n),
                .in_valid(r_in_valid[gx]), .in_flit(r_in_flit[gx]),
                .in_ready(r_in_ready[gx]),
                .out_valid(r_out_valid[gx]), .out_flit(r_out_flit[gx]),
                .out_ready(r_out_ready[gx]),
                .flits_forwarded(r_forwarded[gx]),
                .flits_delivered_local(r_local[gx]),
                .misroute_error(r_misroute[gx])
            );
        end
    endgenerate

    /* verilator lint_off UNUSEDSIGNAL */
    wire unused_ready = |{r_in_ready[0], retire_slot, retire_serial, fault_valid,
                          fault_slot, fault_serial, fault_pc, fault_trap_class,
                          outstanding_with_event, any_outstanding, wait_busy,
                          sb_fault_event, retire_fault};
    /* verilator lint_on UNUSEDSIGNAL */

    // -- the case under test ------------------------------------------------
    reg [31:0] c_producers, c_ordering, c_acquire, c_release, c_first_event;
    reg [31:0] c_leave_pending, c_pending_delay, c_queue, c_preload, c_dest_x;
    reg [31:0] c_unsignalled;
    reg [31:0] c_admit_release;
    wire [31:0] case_base = run_case * CASE_STRIDE;

    localparam [3:0] S_IDLE     = 4'd0;
    localparam [3:0] S_CLEAR    = 4'd1;
    localparam [3:0] S_PRELOAD  = 4'd2;
    localparam [3:0] S_ISSUE    = 4'd3;
    localparam [3:0] S_SETTLE   = 4'd4;
    localparam [3:0] S_COMPLETE = 4'd5;
    localparam [3:0] S_RETIRE   = 4'd6;
    localparam [3:0] S_MESH     = 4'd7;
    localparam [3:0] S_WAIT     = 4'd8;
    localparam [3:0] S_ADMIT    = 4'd9;
    localparam [3:0] S_FINISH   = 4'd10;

    reg [3:0]  state;
    reg [31:0] step;
    reg [31:0] guard;
    reg [31:0] t0, t_retire, t_mesh, t_wait, t_admit;
    reg [4:0]  producer_slot [0:15];
    reg [4:0]  preload_slot  [0:31];
    // The store's free_slot is combinational on `valid`, and `valid` is set a
    // cycle after the allocation handshake, so a second allocation presented
    // on the very next cycle would be handed the same slot.  The design's
    // sequencer holds its reservation across the handshake ("the sequencer
    // reserves free_slot ahead of the issue handshake and presents it back as
    // alloc_slot"); this driver has nothing to hold with, so it leaves one
    // cycle between allocations.  Every allocation here happens BEFORE t0, so
    // the pacing is outside every measured span.
    reg        alloc_gap;
    reg [31:0] late_slot;
    reg        late_pending;
    reg [31:0] late_countdown;
    reg        stalled_latch;

    // The producer sits on node (0,0) and the consumer on node (dest_x, 0), so
    // dest_x is the hop count of the boundary's mesh leg.  A flit addressed to
    // node d leaves router 0's EAST port and appears at router d's LOCAL
    // output; the span is measured to that output.  Sweeping dest_x over
    // 0..MESH_X-1 separates the router's per-hop cost from the rest.
    wire [3:0] dest_x4 = c_dest_x[3:0];
    wire [MESH_X-1:0] local_out_valid;
    genvar gv;
    generate
        for (gv = 0; gv < MESH_X; gv = gv + 1) begin : g_local
            assign local_out_valid[gv] = r_out_valid[gv][4];
        end
    endgenerate
    reg        mesh_delivered;
    reg [31:0] mesh_local_count;
    integer    mx;
    always @* begin
        mesh_delivered = 1'b0;
        mesh_local_count = 32'd0;
        for (mx = 0; mx < MESH_X; mx = mx + 1) begin
            if ({28'd0, dest_x4} == mx[31:0]) begin
                mesh_delivered = local_out_valid[mx];
                mesh_local_count = r_local[mx];
            end
        end
    end

    integer p;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            irs_clear <= 1'b0;
            sb_clear <= 1'b0;
            alloc_valid <= 1'b0;
            alloc_queue <= 5'd0;
            alloc_slot <= 5'd0;
            alloc_serial <= 32'd0;
            alloc_pc <= 32'd0;
            alloc_event_id <= ot_a3_pkg::A3_NO_ID;
            alloc_release <= 1'b0;
            irs_complete_valid <= 1'b0;
            irs_complete_slot <= 5'd0;
            sb_issue_valid <= 1'b0;
            sb_issue_event <= 32'd0;
            wait_start <= 1'b0;
            wait_acquire <= 1'b0;
            wait_payload <= 512'd0;
            for (p = 0; p < MESH_X; p = p + 1) begin
                local_in_valid[p] <= 5'd0;
                local_in_flit[p] <= {FLIT_W{1'b0}};
            end
            boundary_cycles <= 32'd0;
            boundary_control_cycles <= 32'd0;
            span_retire <= 32'd0;
            span_mesh <= 32'd0;
            span_wait <= 32'd0;
            span_admit <= 32'd0;
            obs_trap_class <= 16'd0;
            obs_wait_ok <= 1'b0;
            obs_stalled <= 1'b0;
            obs_mesh_local_deliveries <= 32'd0;
            obs_wait_count <= 32'd0;
            obs_signal_count <= 32'd0;
            obs_max_outstanding <= 6'd0;
            obs_protocol_error <= 1'b0;
            obs_signal_error <= 1'b0;
            obs_misroute <= 1'b0;
            obs_timeout <= 32'd0;
            step <= 32'd0;
            guard <= 32'd0;
            alloc_gap <= 1'b0;
            late_pending <= 1'b0;
            late_countdown <= 32'd0;
            late_slot <= 32'd0;
            stalled_latch <= 1'b0;
            t0 <= 32'd0; t_retire <= 32'd0; t_mesh <= 32'd0;
            t_wait <= 32'd0; t_admit <= 32'd0;
        end else begin
            irs_clear <= 1'b0;
            sb_clear <= 1'b0;
            alloc_valid <= 1'b0;
            irs_complete_valid <= 1'b0;
            sb_issue_valid <= 1'b0;
            wait_start <= 1'b0;
            for (p = 0; p < MESH_X; p = p + 1) local_in_valid[p] <= 5'd0;
            if (sb_wait_stalled) stalled_latch <= 1'b1;
            if (irs_protocol_error) obs_protocol_error <= 1'b1;
            if (sb_signal_error) obs_signal_error <= 1'b1;
            for (p = 0; p < MESH_X; p = p + 1)
                if (r_misroute[p]) obs_misroute <= 1'b1;
            if (late_pending && late_countdown != 32'd0)
                late_countdown <= late_countdown - 32'd1;

            case (state)
                S_IDLE: begin
                    if (run) begin
                        c_producers     <= case_mem[case_base + 0];
                        c_ordering      <= case_mem[case_base + 1];
                        c_acquire       <= case_mem[case_base + 2];
                        c_release       <= case_mem[case_base + 3];
                        c_first_event   <= case_mem[case_base + 4];
                        c_leave_pending <= case_mem[case_base + 5];
                        c_pending_delay <= case_mem[case_base + 6];
                        c_queue         <= case_mem[case_base + 7];
                        c_preload       <= case_mem[case_base + 8];
                        c_dest_x        <= case_mem[case_base + 9];
                        c_unsignalled   <= case_mem[case_base + 12];
                        c_admit_release <= case_mem[case_base + 14];
                        busy <= 1'b1;
                        done <= 1'b0;
                        irs_clear <= 1'b1;
                        sb_clear <= 1'b1;
                        stalled_latch <= 1'b0;
                        late_pending <= 1'b0;
                        step <= 32'd0;
                        guard <= 32'd0;
                        obs_timeout <= 32'd0;
                        boundary_cycles <= 32'd0;
                        boundary_control_cycles <= 32'd0;
                        span_retire <= 32'd0;
                        span_mesh <= 32'd0;
                        span_wait <= 32'd0;
                        span_admit <= 32'd0;
                        obs_trap_class <= 16'd0;
                        obs_wait_ok <= 1'b0;
                        obs_stalled <= 1'b0;
                        state <= S_CLEAR;
                    end
                end
                S_CLEAR: begin
                    step <= 32'd0;
                    state <= S_PRELOAD;
                end
                // Operations already resident in the store and in the queue
                // the consumer will ask for: admission is measured under
                // occupancy, not on an empty machine.
                S_PRELOAD: begin
                    if (step >= c_preload) begin
                        step <= 32'd0;
                        alloc_gap <= 1'b0;
                        // alloc_ready is a function of alloc_queue, so the
                        // queue is presented a cycle before it is read.
                        alloc_queue <= 5'd0;
                        state <= S_ISSUE;
                    end else if (alloc_gap) begin
                        alloc_gap <= 1'b0;
                    end else if (alloc_ready) begin
                        alloc_gap <= 1'b1;
                        alloc_valid <= 1'b1;
                        alloc_slot <= free_slot;
                        alloc_queue <= c_queue[4:0];
                        alloc_serial <= step;
                        alloc_pc <= step;
                        alloc_event_id <= ot_a3_pkg::A3_NO_ID;
                        alloc_release <= 1'b0;
                        preload_slot[step[4:0]] <= free_slot;
                        step <= step + 32'd1;
                    end
                end
                // The producers: one allocation each, and the scoreboard is
                // told the event goes pending exactly as the front end tells
                // it at issue.
                S_ISSUE: begin
                    if (step >= c_producers) begin
                        step <= 32'd0;
                        alloc_gap <= 1'b0;
                        state <= S_SETTLE;
                    end else if (alloc_gap) begin
                        alloc_gap <= 1'b0;
                    end else if (alloc_ready) begin
                        alloc_gap <= 1'b1;
                        alloc_valid <= 1'b1;
                        alloc_slot <= free_slot;
                        // The producers occupy queue 0; the preloaded
                        // operations and the consumer occupy c_queue, so a
                        // deliberately full consumer queue cannot deadlock the
                        // producers' own admission.
                        alloc_queue <= 5'd0;
                        alloc_serial <= 32'd1000 + step;
                        alloc_pc <= 32'd1000 + step;
                        alloc_event_id <= c_first_event + step;
                        alloc_release <= c_release[0];
                        producer_slot[step[3:0]] <= free_slot;
                        // An "unsignalled" case allocates the producer but
                        // never tells the scoreboard it is pending, which is
                        // the state section 3.6 says traps 13.
                        if (!c_unsignalled[0]) begin
                            sb_issue_valid <= 1'b1;
                            sb_issue_event <= c_first_event + step;
                        end
                        step <= step + 32'd1;
                    end
                end
                S_SETTLE: begin
                    if (step >= 32'd2) begin
                        step <= 32'd0;
                        guard <= 32'd0;
                        if (c_unsignalled[0]) begin
                            // Neither pending (never issued to the scoreboard)
                            // nor signalled (never completed): section 3.6's
                            // trap-13 case.  There is no completion to
                            // acknowledge, so t0 is the cycle the consumer's
                            // boundary begins and span_retire is zero.
                            t0 <= tick;
                            t_retire <= tick;
                            span_retire <= 32'd0;
                            state <= S_MESH;
                        end else begin
                            state <= S_COMPLETE;
                        end
                    end else step <= step + 32'd1;
                end
                // t0: the producers' completions are acknowledged, one per
                // cycle.  With leave_one_pending the last producer is held
                // back for pending_delay cycles so the wait stalls behind it,
                // which is the case the design says must stall rather than
                // trap.
                S_COMPLETE: begin
                    if (step >= c_producers) begin
                        t0 <= tick;
                        step <= 32'd0;
                        guard <= 32'd0;
                        state <= S_RETIRE;
                    end else if (c_leave_pending[0] &&
                                 (step + 32'd1 == c_producers)) begin
                        // One producer stays outstanding: the consumer's wait
                        // must STALL behind it and pass when it completes,
                        // which is the case section 3.6 says is not a trap.
                        late_pending <= 1'b1;
                        late_countdown <= c_pending_delay;
                        late_slot <= {27'd0, producer_slot[step[3:0]]};
                        step <= 32'd0;
                        guard <= 32'd0;
                        state <= S_RETIRE;
                    end else begin
                        irs_complete_valid <= 1'b1;
                        irs_complete_slot <= producer_slot[step[3:0]];
                        // t0 is the LAST acknowledged completion; every
                        // completion writes it and the last one stands.
                        t0 <= tick;
                        step <= step + 32'd1;
                    end
                end
                // The store retires one cycle after each completion and the
                // scoreboard signals on that retirement.  The span ends on
                // the last retirement before the mesh leg starts.
                S_RETIRE: begin
                    guard <= guard + 32'd1;
                    if (retire_valid) begin
                        t_retire <= tick;
                        span_retire <= tick - t0;
                        guard <= 32'd0;
                        state <= S_MESH;
                    end else if (guard > GUARD) begin
                        obs_timeout <= 32'd1;
                        state <= S_FINISH;
                    end
                end
                // One flit carrying the retired event travels dest_x hops.
                S_MESH: begin
                    guard <= guard + 32'd1;
                    if (c_dest_x == 32'd0) begin
                        // Producer and consumer on one node: no traversal, and
                        // the span is zero by construction rather than by
                        // measurement.  These cases exist as the control.
                        t_mesh <= tick;
                        span_mesh <= tick - t_retire;
                        obs_mesh_local_deliveries <= mesh_local_count;
                        guard <= 32'd0;
                        state <= S_WAIT;
                    end else if (guard == 32'd0) begin
                        local_in_valid[0] <= 5'b10000;
                        local_in_flit[0] <= ot_a3_link_pkg::flit_pack(
                            retire_event_id, dest_x4, 4'd0, 4'd0, 4'd0,
                            4'd1, 8'd0);
                    end else if (mesh_delivered) begin
                        t_mesh <= tick;
                        span_mesh <= tick - t_retire;
                        obs_mesh_local_deliveries <= r_local[MESH_X-1];
                        guard <= 32'd0;
                        state <= S_WAIT;
                    end else if (guard > GUARD) begin
                        obs_timeout <= 32'd2;
                        state <= S_FINISH;
                    end
                end
                // The consumer's wait set over the producer events.
                S_WAIT: begin
                    guard <= guard + 32'd1;
                    if (late_pending && (late_countdown == 32'd0)) begin
                        irs_complete_valid <= 1'b1;
                        irs_complete_slot <= late_slot[4:0];
                        late_pending <= 1'b0;
                    end
                    if (guard == 32'd0) begin
                        wait_start <= 1'b1;
                        wait_acquire <= c_acquire[0];
                        wait_payload <= 512'd0;
                        wait_payload[15:8] <= c_ordering[7:0];
                        wait_payload[31:24] <= c_producers[7:0];
                        for (p = 0; p < 12; p = p + 1)
                            if (p < c_producers)
                                wait_payload[64 + 32*p +: 32] <= c_first_event + p;
                    end else if (wait_done) begin
                        t_wait <= tick;
                        span_wait <= tick - t_mesh;
                        obs_wait_ok <= sb_wait_ok;
                        obs_trap_class <= sb_trap_class;
                        obs_stalled <= stalled_latch;
                        guard <= 32'd0;
                        if (sb_wait_ok) begin
                            alloc_queue <= c_queue[4:0];
                            state <= S_ADMIT;
                        end
                        else begin
                            // A refused wait ends the boundary at the trap.
                            boundary_cycles <= tick - t0;
                            boundary_control_cycles <= (tick - t0) - span_mesh;
                            state <= S_FINISH;
                        end
                    end else if (guard > GUARD) begin
                        obs_timeout <= 32'd3;
                        state <= S_FINISH;
                    end
                end
                // Queue admission: the consumer asks its engine queue for a
                // slot under the store's occupancy and per-queue depth.  With
                // admit_release the queue is FULL when the consumer arrives
                // and one preloaded operation is completed admit_release
                // cycles later, so what is measured is admission behind the
                // per-queue bound rather than into an empty queue.
                S_ADMIT: begin
                    guard <= guard + 32'd1;
                    if ((c_admit_release != 32'd0) && (guard == c_admit_release)) begin
                        irs_complete_valid <= 1'b1;
                        irs_complete_slot <= preload_slot[0];
                    end
                    if (alloc_ready) begin
                        alloc_valid <= 1'b1;
                        alloc_slot <= free_slot;
                        alloc_serial <= 32'd9999;
                        alloc_pc <= 32'd9999;
                        alloc_event_id <= ot_a3_pkg::A3_NO_ID;
                        alloc_release <= 1'b0;
                        t_admit <= tick;
                        span_admit <= tick - t_wait;
                        boundary_cycles <= tick - t0;
                        // The mesh leg is excluded from the control figure:
                        // ot_a3_mesh_router's crossbar is combinational by
                        // design ("every cycle of a traversal is spent in the
                        // link channel, not in the router"), so the cycles
                        // span_mesh reports are this driver's injection
                        // register and its observation cycle, not a
                        // traversal.  boundary_control_cycles is the span
                        // with a design module behind every cycle of it.
                        boundary_control_cycles <= (tick - t0) - span_mesh;
                        state <= S_FINISH;
                    end else if (guard > GUARD) begin
                        obs_timeout <= 32'd4;
                        state <= S_FINISH;
                    end
                end
                S_FINISH: begin
                    obs_wait_count <= sb_wait_count;
                    obs_signal_count <= sb_signal_count;
                    obs_max_outstanding <= max_outstanding;
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
