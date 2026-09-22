`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_a3_g2_cluster -- the ASAP7 cluster top gate G2 asks for: one datapath
// array, the memory system as placed macros, and the microsequencer, in one
// module.
//
// docs/OPENTALLAS_REDESIGN_PLAN.md G2: "A routed netlist exists containing the
// datapath array, the memory system AND the microsequencer, at one named PDK,
// with DRC 0 and antenna 0."  Its evaluator
// (configs/gates/redesign_gates.json, type routed_netlist_contains) passes on
// ONE results/physical_abi3/*/*/pnr.json record whose sources cover a
// *microsequencer* and an *lq8* or *tile64*, whose macro_count is at least 1,
// and whose route is clean.  This module is the thing to synthesise for that
// record.  It is NOT routed by this file, and nothing here claims it closes.
//
// ---------------------------------------------------------------------------
// WHY LQ8 AND NOT T64
// ---------------------------------------------------------------------------
// Section 11.1 of docs/CHIP_ARCHITECTURE_DESIGN.md sets the flat-flow budget
// at T1 (<= ~65,000 cells; local evidence 65,476 routed at asap7) and T2
// (<= ~200,000, the published ORFS capacity, behind a hardening gate), and
// says "nothing >= 250k is planned flat".
//
//   ot_a3_lq8   239,868 cells routed flat at asap7, 16 ns, closed 2026-09-05
//               (results/physical_abi3/asap7/a3_lq8_array/pnr.json)
//   ot_a3_tile64  8 x LQ8 plus the tile stream sequencer and staging.  Its own
//               row in section 11.1 reads "not measured; lane hierarchy
//               exceeds flat-flow budget", class "hierarchical only, pilot
//               required".  Eight LQ8s is about 1.92 M cells before the
//               sequencer: roughly TEN TIMES the T2 ceiling and EIGHT TIMES
//               the largest route this repository has ever closed.
//
// LQ8 + the microsequencer is 239,868 + 66,100 = 305,968 cells of measured
// blocks, plus this file's glue.  That is already above T2 and above anything
// closed here, so the cluster is a stretch and the campaign that routes it
// must report its own number rather than inherit either block's.  It is a
// stretch of about 1.28x on the largest closed route.  T64 would be a stretch
// of about 8x, and section 11.1 forbids it flat.  G2's evaluator accepts an
// *lq8* source as the datapath array precisely because the vehicle's array is
// T64 = 8 x LQ8, so one LQ8 satisfies the gate's array clause with the block
// that has physical evidence behind it.  T64 belongs to the BLOCKS pilot
// (G2a-P), not to this cluster.
//
// Note also that the 66,100-cell microsequencer figure is the block as routed
// on 2026-09-05 at STATE_COMPAT = 0 with the narrow front end.  The working
// tree's ot_a3_microsequencer has since grown the resolver bank, the
// dependence table, the issue-record store control, the symbol file and the
// shared divider, so this cluster's synthesised count will exceed 305,968 and
// the campaign, not this comment, is the source of the real number.
//
// ---------------------------------------------------------------------------
// THE MEMORY SYSTEM: TWELVE ASAP7 MACROS
// ---------------------------------------------------------------------------
// Every store below is a compiled part of the pinned openroad/orfs:latest
// image, declared in rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv from the
// image's own LEF and NLDM liberty.  Section 11.2's decisions are followed
// where they fit and named where they do not.
//
//   store               part                    n   capacity   area (um^2)
//   program store       fakeram_256x128         1     4 KiB      1,375.9
//   descriptor store    fakeram_2048x128        2    64 KiB     22,015.1
//   issue-record store  fakeram_256x128         4    16 KiB      5,503.8
//   weight staging      fakeram_512x128         2    16 KiB      5,503.8
//   activation window   fakeram_256x64          1     2 KiB        688.0
//   activation scales   fakeram7_256x32         1     1 KiB        344.0
//   weight scales       fakeram_256x64          1     2 KiB        688.0
//   TOTAL                                      12   105 KiB     36,118.6
//
// against 28,037 um^2 of standard cell in the routed LQ8 and 8,440 um^2 in
// the routed microsequencer.  The macros are therefore comparable in area to
// the logic, and macro placement -- never exercised in this flow, every
// pnr.json to date at macro_count 0 -- is the risk this cluster carries.
//
// Three departures from section 11.2, each argued in the wrapper that makes
// it, and each restated here because a reader of the gate record should not
// have to open four files:
//
//   1. The 4 KiB program store IS one fakeram_256x128, as decided.  But the
//      part is 128 b wide and the sequencer's instruction record is 256 b, so
//      a fetch is two macro beats and about four cycles instead of the one
//      cycle rtl/abi3/ot_a3_device_top.sv models.  Front-end cycle figures
//      measured against that model do not carry over to this cluster.
//   2. The 64 KiB descriptor store IS two fakeram_2048x128, as decided, ganged
//      to 256 b x 2,048 rows.  A 192-byte record is six rows, so the store
//      holds 341 descriptors and a read is about ten cycles rather than one.
//      Same warning about inherited cycle figures.
//   3. The issue-record store is NOT the eight fakeram_512x8 that section
//      11.2 decision (a) names.  That mapping is 4 KiB behind a 64-bit port;
//      the microsequencer's IRS payload port is 32 slots x 8 lanes x 512 b =
//      16 KiB behind a 512-bit port with one cycle of latency.  Four
//      fakeram_256x128 ganged in width are exactly 16 KiB at exactly 512 b
//      with exactly one cycle, so they are used instead, at 5,503.8 um^2
//      against the 1,375.9 um^2 the section-11.2 row prices.  The reason is
//      in rtl/abi3/ot_a3_g2_issue_record_ram.sv and in the report.
//
// Section 11.2 does not price the array's activation window or its two E8M0
// scale tables at all; they are mapped here onto the parts whose word width
// is exactly the LQ8's port width, so no read-path adapter exists for any of
// the four staging arrays.
//
// ---------------------------------------------------------------------------
// WHAT IS WIRED, AND WHAT IS NOT
// ---------------------------------------------------------------------------
// Wired for real, no tie-off:
//   * imem_req/index/valid/data          -> the program-store macro
//   * desc_req/id/valid/fault/data       -> the descriptor-store macros
//   * irs_we/re/slot/lane/wdata/rdata    -> the issue-record macros
//   * the LQ8's four read ports          -> the staging macros
//   * issue_valid/ready/family/slot and complete_valid/slot/fault/trap_class
//     -> ot_a3_g2_array_issue_adapter -> the LQ8's start and geometry, with
//     the geometry read out of the operand TENSOR_VIEW descriptors over a
//     second descriptor-store port.  The array runs what the sequencer issues.
//   * every macro is loaded through the host write port, so the weights,
//     activations, program and descriptors all enter from outside the cluster.
//   * the LQ8's partial port (out_we/out_addr/out_data/out_acc) and every
//     counter of both blocks reach primary outputs, so nothing is optimised
//     away and the routed netlist contains the blocks the gate names.
//
// Adapters, each argued where it lives:
//   * the program store's two-beat fetch and the descriptor store's six-beat
//     burst (width mismatch against the macros);
//   * the descriptor store's two-master arbitration (the sequencer and the
//     issue adapter), which is the arrangement
//     rtl/abi3/ot_a3_engine_issue_bridge.sv already assumes;
//   * the issue adapter itself, which has no counterpart in either block.
//
// Refused, precisely, rather than faked:
//   * predicate_read_*.  The cluster has no predicate value cache and no data
//     path to a predicate object, so predicate_read_valid is returned one
//     cycle later with A3_TRAP_CAPABILITY.  A data-dependent predicate
//     therefore traps here, which is the truthful answer for a machine that
//     cannot evaluate one; it is not a tie-off, and it is counted.
//   * every issue family except TENSOR, for the same reason: this cluster
//     holds one contraction array, so the rest return A3_TRAP_CAPABILITY,
//     exactly as ot_a3_engine_issue_bridge does for the opcodes it does not
//     serve.
//
// Not represented at all, and named so no one reads more into the gate record
// than it holds: the reduction endpoint (RE8), the vector, attention, route
// and selection tiles, the DMA mover, the NoC routers, the link endpoints and
// the management processor -- section 11.3's "G2 top" lists all of them.
// This cluster is the three things the G2 STATEMENT names, not the whole
// vehicle top.
// ---------------------------------------------------------------------------
module ot_a3_g2_cluster #(
    parameter integer STATE_COMPAT  = 0,     // as routed: a3_microsequencer
    parameter integer LANES         = 8,     // as routed: a3_lq8_array
    parameter integer ADDER_STAGES  = 3,
    parameter integer ACC_SLOTS     = 8,
    parameter integer RUNTIME_OPERANDS = 0,
    parameter bit RUNTIME_WEIGHT_ROW_REUSE = 1,
    parameter integer OUTPUT_DEPTH = 4,
    // The control-plane performance knobs, forwarded to the sequencer.  They
    // are declared here so a route can select a configuration with --param
    // instead of editing a default in a scratch worktree: a record produced
    // that way carries worktree_dirty true and is inadmissible under the rule
    // 49c5c55 added, which is exactly how the first shipping-configuration
    // route was wasted.  Every one defaults to 0, so a build that names none
    // of them is the design as routed.
    parameter integer CRC_CACHE      = 0,
    parameter integer CRC_PERIOD     = 0,
    parameter integer FAST_FRONT_END = 0,
    parameter integer FAST_SCAN      = 0,
    parameter integer FAST_WALK      = 0
) (
    input  wire          clk,
    input  wire          rst_n,

    // -- transaction control (the sequencer's own) -----------------------
    input  wire          start,
    input  wire [31:0]   cfg_program_base,
    input  wire [31:0]   cfg_instruction_count,
    input  wire [31:0]   cfg_entry_pc,
    input  wire [63:0]   cfg_max_retired_work,
    input  wire [31:0]   cfg_state_count,

    // -- per-transaction numeric configuration for the array -------------
    // The ABI carries these in the NUMERIC descriptor and the schedule; the
    // resolved-view stream does not publish them, so the host writes them
    // beside the program base.  See ot_a3_g2_array_issue_adapter's header.
    input  wire [7:0]    cfg_array_group,
    input  wire [15:0]   cfg_array_block_a,
    input  wire [15:0]   cfg_array_block_rows_a,
    input  wire [15:0]   cfg_array_block_b,
    input  wire [31:0]   cfg_array_scale_a_base,
    input  wire [31:0]   cfg_array_ws_base,
    input  wire          cfg_array_out_fp32,

    // Runtime mode keeps the program loader idle-only. Transport acknowledgements
    // promise that this generation cannot return more data; writes_drained covers
    // every accepted partial write. Global reset must reset transport as well.
    input wire runtime_transport_ack,runtime_writes_drained,runtime_abort,
    // Sticky external transport/auxiliary failure; cleared after cancellation.
    input wire runtime_service_fault,
    output wire runtime_transport_cancel,
    output wire [31:0] runtime_generation,
    output wire weight_request_valid,
    input wire weight_request_ready,
    output wire [63:0] weight_request_tag,
    output wire [31:0] weight_request_address,
    output wire [9:0] weight_request_words,
    input wire weight_response_valid,
    output wire weight_response_ready,
    input wire [63:0] weight_response_tag,
    input wire [9:0] weight_response_index,
    input wire [127:0] weight_response_data,
    output wire auxiliary_request_valid,
    input wire auxiliary_request_ready,
    output wire [31:0] auxiliary_request_generation,auxiliary_request_a,
                       auxiliary_request_s,auxiliary_request_ws,auxiliary_request_w,
    output wire auxiliary_scale_a,auxiliary_scale_b,
    input wire auxiliary_response_valid,
    output wire auxiliary_response_ready,
    input wire [31:0] auxiliary_response_generation,auxiliary_response_w,
    input wire [63:0] auxiliary_response_a_data,auxiliary_response_ws_data,
    input wire [31:0] auxiliary_response_s_data,

    // -- host load port --------------------------------------------------
    // One 128-bit write port over every store, in the spirit of
    // ot_a3_device_top's host_we / host_sel / host_row / host_lane / host_wdata.
    //   sel 0 program store      row[7:0]
    //   sel 1 descriptor store   row[10:0], lane[0] selects the 128-bit half
    //   sel 2 weight staging     row[9:0]
    //   sel 3 activation window  row[7:0]
    //   sel 4 activation scales  row[7:0]
    //   sel 5 weight scales      row[7:0]
    //   sel 6 symbol file        row[3:0] index, lane[1:0] lane, wdata[31:0]
    input  wire          host_we,
    input  wire [2:0]    host_sel,
    // host_row and host_lane keep ot_a3_device_top's widths; the deepest
    // store here is 2,048 rows and the widest needs one lane bit, so the
    // upper bits of both are deliberately unread.
    /* verilator lint_off UNUSEDSIGNAL */
    input  wire [31:0]   host_row,
    input  wire [5:0]    host_lane,
    /* verilator lint_on UNUSEDSIGNAL */
    input  wire [127:0]  host_wdata,
    output wire          host_ready,
    output reg           host_write_refused,

    // -- sequencer status and accounting ---------------------------------
    output wire          busy,
    output wire          done,
    output wire          complete,
    output wire          trapped,
    output wire [15:0]   trap_class,
    output wire [31:0]   first_fault_instruction,
    output wire [31:0]   count_fetched,
    output wire [31:0]   count_retired,
    output wire [31:0]   count_predicated_off,
    output wire [31:0]   count_issued,
    output wire [31:0]   count_branches,
    output wire [31:0]   count_views_resolved,
    output wire [31:0]   count_loop_iterations,
    output wire [31:0]   count_wait_events,
    output wire [31:0]   count_signals,
    output wire [31:0]   count_state_prepares,
    output wire [31:0]   count_state_commits,
    output wire [31:0]   count_state_discards,
    output wire [31:0]   count_state_reads,
    output wire [31:0]   count_state_generation_advances,
    output wire [31:0]   count_state_commits_applied,
    output wire [31:0]   count_state_rows_committed,
    output wire [63:0]   count_state_bytes_written,
    output wire [3:0]    loop_depth,
    output wire          event_signal_error,
    output wire          state_apply_overflow,
    output wire [3:0]    dbg_decode_error,
    output wire [31:0]   dbg_source_operation_id,
    output wire [31:0]   dbg_wait_fault_event,
    output wire [1:0]    dbg_loop_action,
    output wire [5:0]    dbg_outstanding,
    output wire [5:0]    dbg_max_outstanding,
    output wire [31:0]   dbg_dep_stalls,
    output wire [31:0]   dbg_wait_stalls,
    output wire          irs_protocol_error,

    // -- the issue stream and the resolved views, observed at the boundary
    output wire          issue_valid,
    output wire [7:0]    issue_family,
    output wire [7:0]    issue_sub,
    output wire [31:0]   issue_descriptor_id,
    output wire [31:0]   issue_index,
    output wire [31:0]   issue_serial,
    output wire [4:0]    issue_slot,
    output wire [4:0]    issue_queue,
    output wire          view_valid,
    output wire [31:0]   view_descriptor_id,
    output wire [2:0]    view_slot,
    output wire [31:0]   view_extent,
    output wire [7:0]    view_extent_axis,
    output wire [63:0]   view_element_offset,
    output wire [7:0]    view_rank,
    output wire [4:0]    view_irs_slot,

    // Runtime mode: part_valid holds mask/address/data/acc until part_ready.
    // A beat atomically transfers all masked lanes. Queued pre-abort results
    // still drain; runtime_generation remains stable until completion.
    // Legacy mode: fixed-throughput pulses; part_ready is ignored.
    input wire part_ready,
    output wire part_valid,
    // -- the array's partial port and status -----------------------------
    output wire [LANES-1:0]    part_we,
    output wire [32*LANES-1:0] part_addr,
    output wire [32*LANES-1:0] part_data,
    output wire [32*LANES-1:0] part_acc,
    output wire                array_busy,
    output wire                array_done,
    output wire [7:0]          array_error_code,
    output wire [7:0]          array_error_detail,
    output wire [7:0]          array_error_lane,
    output wire [8*LANES-1:0]  lane_error_code,
    output wire [8*LANES-1:0]  lane_error_detail,
    output wire [LANES-1:0]    lane_busy,
    output wire [LANES-1:0]    lane_done,
    output wire [LANES-1:0]    op_retire,
    output wire [$clog2(LANES+1)-1:0] retire_count,
    output wire [31:0]         out_count,
    output wire [31:0]         saturation_count,
    output wire [31:0]         mac_count,
    output wire [31:0]         product_count,

    // -- memory-system and adapter observation ---------------------------
    output wire [31:0]   prog_out_of_range,
    output wire [31:0]   prog_fetch_count,
    output wire [31:0]   desc_read_count,
    output wire [31:0]   desc_fault_count,
    output wire [31:0]   desc_dropped_requests,
    output wire [31:0]   irs_conflict_count,
    output wire [31:0]   staging_window_faults,
    output wire [31:0]   staging_write_refusals,
    output wire [31:0]   staging_weight_words_read,
    output wire [31:0]   adapter_launch_count,
    output wire [31:0]   adapter_capability_refusals,
    output wire [31:0]   adapter_descriptor_refusals,
    output wire [31:0]   adapter_engine_faults,
    output wire [31:0]   adapter_views_captured,
    output reg  [31:0]   predicate_refusals,
    output wire [31:0]   predicate_read_object_id,
    output wire [31:0]   predicate_read_element_index,
    output wire          predicate_read_req
);
    // -- host decode ------------------------------------------------------
    assign host_ready = !busy;

    wire host_en    = host_we && host_ready;
    wire host_prog  = host_en && (host_sel == 3'd0);
    wire host_desc  = host_en && (host_sel == 3'd1);
    wire host_stage = host_en && (host_sel >= 3'd2) && (host_sel <= 3'd5);
    wire host_sym   = host_en && (host_sel == 3'd6);

    wire host_prog_accept;
    wire host_desc_accept;
    wire host_stage_accept;
    wire host_accept = host_prog_accept | host_desc_accept | host_stage_accept |
                       host_sym;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            host_write_refused <= 1'b0;
        else if (host_we && !host_accept)
            host_write_refused <= 1'b1;
    end

    // -- program store -----------------------------------------------------
    wire         imem_req;
    wire [31:0]  imem_index;
    wire         imem_valid;
    wire [255:0] imem_data;

    ot_a3_g2_program_store program_store (
        .clk(clk),
        .rst_n(rst_n),
        .imem_req(imem_req),
        .imem_index(imem_index),
        .imem_valid(imem_valid),
        .imem_data(imem_data),
        .host_we(host_prog),
        .host_row(host_row[7:0]),
        .host_wdata(host_wdata),
        .host_accept(host_prog_accept),
        .out_of_range_count(prog_out_of_range),
        .fetch_count(prog_fetch_count)
    );

    // -- descriptor store, two masters -------------------------------------
    wire          desc_req;
    wire [31:0]   desc_id;
    wire          desc_valid;
    wire          desc_fault;
    wire [1535:0] desc_data;
    wire          aux_desc_req;
    wire [31:0]   aux_desc_id;
    wire          aux_desc_valid;
    wire          aux_desc_fault;
    wire [1535:0] aux_desc_data;

    ot_a3_g2_descriptor_store descriptor_store (
        .clk(clk),
        .rst_n(rst_n),
        .desc_req(desc_req),
        .desc_id(desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .aux_req(aux_desc_req),
        .aux_id(aux_desc_id),
        .aux_valid(aux_desc_valid),
        .aux_fault(aux_desc_fault),
        .aux_data(aux_desc_data),
        .host_we(host_desc),
        .host_row(host_row[10:0]),
        .host_lane(host_lane[0]),
        .host_wdata(host_wdata),
        .host_accept(host_desc_accept),
        .read_count(desc_read_count),
        .fault_count(desc_fault_count),
        .dropped_requests(desc_dropped_requests)
    );

    // -- issue-record payload store ----------------------------------------
    wire         irs_we;
    wire [4:0]   irs_wslot;
    wire [2:0]   irs_wlane;
    wire [511:0] irs_wdata;
    wire         irs_re;
    wire [4:0]   irs_rslot;
    wire [2:0]   irs_rlane;
    wire [511:0] irs_rdata;

    ot_a3_g2_issue_record_ram issue_record_ram (
        .clk(clk),
        .rst_n(rst_n),
        .irs_we(irs_we),
        .irs_wslot(irs_wslot),
        .irs_wlane(irs_wlane),
        .irs_wdata(irs_wdata),
        .irs_re(irs_re),
        .irs_rslot(irs_rslot),
        .irs_rlane(irs_rlane),
        .irs_rdata(irs_rdata),
        .conflict_count(irs_conflict_count)
    );

    // -- the microsequencer -------------------------------------------------
    // Data-dependent predicates are refused precisely: the cluster has no
    // predicate value path, so the read answers one cycle later with a
    // CAPABILITY trap class rather than a fabricated value.
    reg         predicate_read_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            predicate_read_valid <= 1'b0;
            predicate_refusals   <= 32'd0;
        end else begin
            predicate_read_valid <= predicate_read_req;
            if (predicate_read_req)
                predicate_refusals <= predicate_refusals + 32'd1;
        end
    end

    wire        seq_issue_ready;
    wire        seq_complete_valid;
    wire [4:0]  seq_complete_slot;
    wire        seq_complete_fault;
    wire [15:0] seq_complete_trap_class;

    ot_a3_microsequencer #(
        .STATE_COMPAT(STATE_COMPAT),
        .CRC_CACHE(CRC_CACHE),
        .CRC_PERIOD(CRC_PERIOD),
        .FAST_FRONT_END(FAST_FRONT_END),
        .FAST_SCAN(FAST_SCAN),
        .FAST_WALK(FAST_WALK)
    ) sequencer (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_program_base(cfg_program_base),
        .cfg_instruction_count(cfg_instruction_count),
        .cfg_entry_pc(cfg_entry_pc),
        .cfg_max_retired_work(cfg_max_retired_work),
        .cfg_state_count(cfg_state_count),
        .busy(busy),
        .done(done),
        .complete(complete),
        .trapped(trapped),
        .trap_class(trap_class),
        .first_fault_instruction(first_fault_instruction),
        .imem_req(imem_req),
        .imem_index(imem_index),
        .imem_valid(imem_valid),
        .imem_data(imem_data),
        .desc_req(desc_req),
        .desc_id(desc_id),
        .desc_valid(desc_valid),
        .desc_fault(desc_fault),
        .desc_data(desc_data),
        .host_sym_we(host_sym),
        .host_sym_index(host_row[3:0]),
        .host_sym_lane(host_lane[1:0]),
        .host_sym_wdata(host_wdata[31:0]),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(predicate_read_valid),
        .predicate_read_value(1'b0),
        .predicate_read_trap_class(ot_a3_pkg::A3_TRAP_CAPABILITY),
        .issue_valid(issue_valid),
        .issue_ready(seq_issue_ready),
        .issue_family(issue_family),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_index(issue_index),
        .issue_serial(issue_serial),
        .issue_slot(issue_slot),
        .issue_queue(issue_queue),
        .complete_valid(seq_complete_valid),
        .complete_slot(seq_complete_slot),
        .complete_fault(seq_complete_fault),
        .complete_trap_class(seq_complete_trap_class),
        .irs_we(irs_we),
        .irs_wslot(irs_wslot),
        .irs_wlane(irs_wlane),
        .irs_wdata(irs_wdata),
        .irs_re(irs_re),
        .irs_rslot(irs_rslot),
        .irs_rlane(irs_rlane),
        .irs_rdata(irs_rdata),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_extent(view_extent),
        .view_extent_axis(view_extent_axis),
        .view_element_offset(view_element_offset),
        .view_rank(view_rank),
        .view_irs_slot(view_irs_slot),
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
        .dbg_decode_error(dbg_decode_error),
        .dbg_source_operation_id(dbg_source_operation_id),
        .dbg_wait_fault_event(dbg_wait_fault_event),
        .dbg_loop_action(dbg_loop_action),
        .dbg_outstanding(dbg_outstanding),
        .dbg_max_outstanding(dbg_max_outstanding),
        .dbg_dep_stalls(dbg_dep_stalls),
        .dbg_wait_stalls(dbg_wait_stalls),
        .irs_protocol_error(irs_protocol_error)
    );

    // -- the issue adapter --------------------------------------------------
    wire        arr_start;
    wire [15:0] arr_rows;
    wire [15:0] arr_cols;
    wire [15:0] arr_depth;
    wire [7:0]  arr_dtype_a;
    wire [7:0]  arr_dtype_b;
    wire [7:0]  arr_group;
    wire [31:0] arr_a_base;
    wire        arr_scale_a;
    wire [15:0] arr_block_a;
    wire [15:0] arr_block_rows_a;
    wire [31:0] arr_scale_a_base;
    wire [31:0] arr_w_base;
    wire        arr_scale_b;
    wire [15:0] arr_block_b;
    wire [31:0] arr_ws_base;
    wire [31:0] arr_out_base;
    wire        arr_out_fp32;

    ot_a3_g2_array_issue_adapter #(
        .LANES(LANES)
    ) issue_adapter (
        .clk(clk),
        .rst_n(rst_n),
        .clear(start),
        .issue_valid(issue_valid),
        .issue_ready(seq_issue_ready),
        .issue_family(issue_family),
        .issue_sub(issue_sub),
        .issue_descriptor_id(issue_descriptor_id),
        .issue_slot(issue_slot),
        .view_valid(view_valid),
        .view_descriptor_id(view_descriptor_id),
        .view_slot(view_slot),
        .view_element_offset(view_element_offset),
        .view_irs_slot(view_irs_slot),
        .complete_valid(seq_complete_valid),
        .complete_slot(seq_complete_slot),
        .complete_fault(seq_complete_fault),
        .complete_trap_class(seq_complete_trap_class),
        .desc_req(aux_desc_req),
        .desc_id(aux_desc_id),
        .desc_valid(aux_desc_valid),
        .desc_fault(aux_desc_fault),
        .desc_data(aux_desc_data),
        .cfg_group(cfg_array_group),
        .cfg_block_a(cfg_array_block_a),
        .cfg_block_rows_a(cfg_array_block_rows_a),
        .cfg_block_b(cfg_array_block_b),
        .cfg_scale_a_base(cfg_array_scale_a_base),
        .cfg_ws_base(cfg_array_ws_base),
        .cfg_out_fp32(cfg_array_out_fp32),
        .array_start(arr_start),
        .array_rows(arr_rows),
        .array_cols(arr_cols),
        .array_depth(arr_depth),
        .array_dtype_a(arr_dtype_a),
        .array_dtype_b(arr_dtype_b),
        .array_group(arr_group),
        .array_a_base(arr_a_base),
        .array_scale_a(arr_scale_a),
        .array_block_a(arr_block_a),
        .array_block_rows_a(arr_block_rows_a),
        .array_scale_a_base(arr_scale_a_base),
        .array_w_base(arr_w_base),
        .array_scale_b(arr_scale_b),
        .array_block_b(arr_block_b),
        .array_ws_base(arr_ws_base),
        .array_out_base(arr_out_base),
        .array_out_fp32(arr_out_fp32),
        .array_done(array_done),
        .array_error_code(array_error_code),
        .launch_count(adapter_launch_count),
        .capability_refusals(adapter_capability_refusals),
        .descriptor_refusals(adapter_descriptor_refusals),
        .engine_faults(adapter_engine_faults),
        .views_captured(adapter_views_captured)
    );

    // -- the datapath array and its staging ---------------------------------
    // host_sel 2..5 select the four staging arrays in the staging block's own
    // order (weight ring, activation window, activation scales, weight scales).
    /* verilator lint_off UNUSEDSIGNAL */
    wire [2:0]   host_stage_sel3 = host_sel - 3'd2;
    /* verilator lint_on UNUSEDSIGNAL */
    wire [1:0]   host_stage_sel  = host_stage_sel3[1:0];

    wire         w_rd_en;
    wire [31:0]  w_rd_addr;
    wire [16*LANES-1:0] w_rd_data;
    wire         a_rd_en;
    wire [31:0]  a_rd_addr;
    wire [63:0]  a_rd_data;
    wire         s_rd_en;
    wire [31:0]  s_rd_addr;
    wire [31:0]  s_rd_data;
    wire         ws_rd_en;
    wire [31:0]  ws_rd_addr;
    wire [8*LANES-1:0] ws_rd_data;

    wire core_busy,core_done,core_rst_n;
    wire [7:0] core_error,core_detail,core_error_lane;
    wire [LANES-1:0] core_part_we;
    wire [32*LANES-1:0] core_part_addr,core_part_data,core_part_acc;
    wire operand_request,operand_issue,operand_credit,operand_last;
    wire [31:0] operand_a,operand_s,operand_ws,operand_w;
    generate if(RUNTIME_OPERANDS==0)begin : legacy_operands
    ot_a3_g2_array_staging staging (
        .clk(clk),
        .rst_n(rst_n),
        .w_rd_en(w_rd_en),
        .w_rd_addr(w_rd_addr),
        .w_rd_data(w_rd_data),
        .a_rd_en(a_rd_en),
        .a_rd_addr(a_rd_addr),
        .a_rd_data(a_rd_data),
        .s_rd_en(s_rd_en),
        .s_rd_addr(s_rd_addr),
        .s_rd_data(s_rd_data),
        .ws_rd_en(ws_rd_en),
        .ws_rd_addr(ws_rd_addr),
        .ws_rd_data(ws_rd_data),
        .host_we(host_stage),
        .host_sel(host_stage_sel),
        .host_row(host_row[9:0]),
        .host_wdata(host_wdata),
        .host_accept(host_stage_accept),
        .window_faults(staging_window_faults),
        .write_refusals(staging_write_refusals),
        .weight_words_read(staging_weight_words_read)
    );

        assign core_rst_n=rst_n;
        assign operand_credit=1'b1;
        assign array_busy=core_busy;assign array_done=core_done;
        assign array_error_code=core_error;assign array_error_detail=core_detail;assign array_error_lane=core_error_lane;
        assign part_we=core_part_we;assign part_valid=|core_part_we;
        assign part_addr=core_part_addr;assign part_data=core_part_data;assign part_acc=core_part_acc;
        assign runtime_transport_cancel=0;assign runtime_generation=0;
        assign weight_request_valid=0;assign weight_request_tag=0;assign weight_request_address=0;assign weight_request_words=0;
        assign weight_response_ready=0;assign auxiliary_request_valid=0;
        assign auxiliary_request_generation=0;assign auxiliary_request_a=0;assign auxiliary_request_s=0;
        assign auxiliary_request_ws=0;assign auxiliary_request_w=0;
        assign auxiliary_scale_a=0;assign auxiliary_scale_b=0;assign auxiliary_response_ready=0;
    end else begin : runtime_operands
        if(LANES!=8)begin : unsupported_width
            initial $error("G2 runtime service requires eight lanes");
        end
        reg [31:0] next_generation;
        reg command_pending;
        wire command_ready,service_busy,geometry_error,protocol_error,lifetime_clear,compute_abort,lifetime_ready;
        wire [31:0] completed_generation;
        wire [7:0] completed_error;
        wire output_error,output_empty,output_credit,service_credit;
        wire runtime_fault=runtime_service_fault || protocol_error || output_error || (geometry_error && operand_request);
        wire service_clear=lifetime_clear;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin next_generation<=0;command_pending<=0;end
            else begin
                if(arr_start)begin next_generation<=next_generation+1'b1;command_pending<=1;end
                if(command_pending && command_ready)command_pending<=0;
                if(lifetime_clear)command_pending<=0;
            end
        end
        ot_a3_runtime_operation_lifetime lifetime(
            .clk(clk),.rst_n(rst_n),.start(arr_start),.start_ready(lifetime_ready),
            .command_generation(next_generation+1'b1),.compute_done(core_done),.compute_error(core_error),
            .service_fault(runtime_fault),.abort_valid(runtime_abort),
            .transport_ack(runtime_transport_ack),.writes_drained(runtime_writes_drained && output_empty),
            .transport_cancel(runtime_transport_cancel),.transport_generation(runtime_generation),
            .service_clear(lifetime_clear),.compute_abort(compute_abort),.busy(array_busy),
            .completion_valid(array_done),.completion_ready(1'b1),
            .completion_generation(completed_generation),.completion_error(completed_error));
        assign core_rst_n=rst_n && !compute_abort;
        // No new results enter storage after an abort is observed. Previously
        // queued beats retain ready/valid stability and drain before completion.
        wire push_output=(|core_part_we) && !compute_abort && !runtime_fault && !runtime_abort;
        wire [LANES-1:0] queued_mask;
        assign part_we=part_valid?queued_mask:{LANES{1'b0}};
        assign operand_credit=service_credit && (!operand_last || output_credit);
        ot_a3_reserved_output_queue #(.WIDTH(97*LANES),.DEPTH(OUTPUT_DEPTH)) output_queue(
            .clk(clk),.rst_n(rst_n),
            .reserve_valid(operand_issue && operand_last),.reserve_ready(output_credit),
            .stop_producer(core_done || compute_abort),
            .push_valid(push_output),.push_data({core_part_we,core_part_addr,core_part_data,core_part_acc}),
            .out_valid(part_valid),.out_ready(part_ready),
            .out_data({queued_mask,part_addr,part_data,part_acc}),
            .empty(output_empty),.protocol_error(output_error));
        assign array_error_code=array_done?completed_error:core_error;
        assign array_error_detail=compute_abort?completed_error:core_detail;
        assign array_error_lane=compute_abort?8'b0:core_error_lane;
        assign host_stage_accept=0;
        assign staging_window_faults=0;assign staging_write_refusals=0;
        reg [31:0] words_read;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)words_read<=0;
            else if(operand_issue)words_read<=words_read+1'b1;
        end
        assign staging_weight_words_read=words_read;
        ot_a3_lq8_runtime_operands #(.INTERLEAVE(ADDER_STAGES),.REUSE_WEIGHT_ROWS(RUNTIME_WEIGHT_ROW_REUSE)) service(
            .clk(clk),.rst_n(rst_n),.clear(service_clear),
            .command_valid(command_pending),.command_ready(command_ready),
            .cfg_generation(next_generation),.cfg_rows(arr_rows),.cfg_cols(arr_cols),.cfg_depth(arr_depth),
            .cfg_group(arr_group),.cfg_scale_a(arr_scale_a),.cfg_scale_b(arr_scale_b),
            .cfg_block_a(arr_block_a),.cfg_block_b(arr_block_b),.cfg_block_rows_a(arr_block_rows_a),
            .cfg_a_base(arr_a_base),.cfg_s_base(arr_scale_a_base),.cfg_ws_base(arr_ws_base),.cfg_w_base(arr_w_base),
            .compute_admitted(operand_request),.operand_request(operand_request),.operand_issue(operand_issue),
            .operand_a(operand_a),.operand_s(operand_s),.operand_ws(operand_ws),.operand_w(operand_w),
            .operand_credit(service_credit),.a_data(a_rd_data),.s_data(s_rd_data),.w_data(w_rd_data),.ws_data(ws_rd_data),
            .busy(service_busy),.geometry_error(geometry_error),.protocol_error(protocol_error),
            .weight_request_valid(weight_request_valid),
            .weight_request_ready(weight_request_ready),
            .weight_request_tag(weight_request_tag),
            .weight_request_address(weight_request_address),
            .weight_request_words(weight_request_words),
            .weight_response_valid(weight_response_valid),
            .weight_response_ready(weight_response_ready),
            .weight_response_tag(weight_response_tag),
            .weight_response_index(weight_response_index),
            .weight_response_data(weight_response_data),
            .auxiliary_request_valid(auxiliary_request_valid),
            .auxiliary_request_ready(auxiliary_request_ready),
            .auxiliary_request_generation(auxiliary_request_generation),
            .auxiliary_request_a(auxiliary_request_a),
            .auxiliary_request_s(auxiliary_request_s),
            .auxiliary_request_ws(auxiliary_request_ws),
            .auxiliary_request_w(auxiliary_request_w),
            .auxiliary_scale_a(auxiliary_scale_a),
            .auxiliary_scale_b(auxiliary_scale_b),
            .auxiliary_response_valid(auxiliary_response_valid),
            .auxiliary_response_ready(auxiliary_response_ready),
            .auxiliary_response_generation(auxiliary_response_generation),
            .auxiliary_response_w(auxiliary_response_w),
            .auxiliary_response_a_data(auxiliary_response_a_data),
            .auxiliary_response_ws_data(auxiliary_response_ws_data),
            .auxiliary_response_s_data(auxiliary_response_s_data)
        );
    end endgenerate

    ot_a3_lq8 #(
        .LANES(LANES),
        .ADDER_STAGES(ADDER_STAGES),
        .ACC_SLOTS(ACC_SLOTS),.OPERAND_CREDITS(RUNTIME_OPERANDS)
    ) array (
        .clk(clk),
        .rst_n(core_rst_n),
        .start(arr_start),.operand_credit(operand_credit),
        .operand_request(operand_request),.operand_issue(operand_issue),.operand_last(operand_last),
        .operand_a_addr(operand_a),.operand_s_addr(operand_s),.operand_ws_addr(operand_ws),.operand_w_addr(operand_w),
        .cfg_rows(arr_rows),
        .cfg_cols(arr_cols),
        .cfg_depth(arr_depth),
        .cfg_dtype_a(arr_dtype_a),
        .cfg_dtype_b(arr_dtype_b),
        .cfg_group(arr_group),
        .cfg_a_base(arr_a_base),
        .cfg_scale_a(arr_scale_a),
        .cfg_block_a(arr_block_a),
        .cfg_block_rows_a(arr_block_rows_a),
        .cfg_scale_a_base(arr_scale_a_base),
        .cfg_w_base(arr_w_base),
        .cfg_scale_b(arr_scale_b),
        .cfg_block_b(arr_block_b),
        .cfg_ws_base(arr_ws_base),
        .cfg_out_base(arr_out_base),
        .cfg_out_fp32(arr_out_fp32),
        .a_rd_en(a_rd_en),
        .a_rd_addr(a_rd_addr),
        .a_rd_data(a_rd_data),
        .s_rd_en(s_rd_en),
        .s_rd_addr(s_rd_addr),
        .s_rd_data(s_rd_data),
        .w_rd_en(w_rd_en),
        .w_rd_addr(w_rd_addr),
        .w_rd_data(w_rd_data),
        .ws_rd_en(ws_rd_en),
        .ws_rd_addr(ws_rd_addr),
        .ws_rd_data(ws_rd_data),
        .out_we(core_part_we),
        .out_addr(core_part_addr),
        .out_data(core_part_data),
        .out_acc(core_part_acc),
        .busy(core_busy),
        .done(core_done),
        .error_code(core_error),
        .error_detail(core_detail),
        .error_lane(core_error_lane),
        .lane_error_code(lane_error_code),
        .lane_error_detail(lane_error_detail),
        .lane_busy(lane_busy),
        .lane_done(lane_done),
        .op_retire(op_retire),
        .retire_count(retire_count),
        .out_count(out_count),
        .saturation_count(saturation_count),
        .mac_count(mac_count),
        .product_count(product_count)
    );
endmodule
