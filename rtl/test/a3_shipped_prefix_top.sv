`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the exact shipped ABI 3.0 decode-prefix witness.
//
// Program, descriptor and symbol images are the same source-bound images used
// by the full shipped-deployment control-plane campaign.  Only the compact
// operand banks are new.  The sequencer resolves the deployed views, the
// issue bridge validates the deployed OPERATOR/TENSOR_VIEW/NUMERIC records,
// and the existing engine array performs the real DMA copies before replying.
//
// The control plane is the design's own top, rtl/abi3/ot_a3_device_top.sv
// (admission block, asynchronous sequencer, descriptor base/bound/fault
// logic, symbol file, host load path); this module wraps it with the
// control stores and the issue-record payload it presents as abstract
// boundaries, the engine bridge and array on its engine port through
// rtl/test/a3_engine_completion_adapter.sv (the two-phase port to the
// bridge's run-to-completion port, at depth 1), the bridge's own descriptor
// read port, and the exact multicast witness.
//
// The program store, the descriptor store and the symbol file hold no image
// and are loaded through the design's host path by the checker
// (docs/CHIP_ARCHITECTURE_DESIGN.md section 13 item 12); the operand banks
// and the multicast witness records below are engine verification memories,
// not control stores, and stay preloaded.
// ---------------------------------------------------------------------------
module ot_a3_shipped_prefix_top #(
    parameter integer PROGRAM_WORDS = 4096,
    parameter integer DESC_WORDS = 8192,
    parameter integer INDEX_WORDS = 64,
    parameter integer SOURCE_WORDS = 65536,
    parameter integer RESULT_WORDS = 98304,
    // The weight image is addressed, not held.  This is a 64-bit byte count
    // of the *image* the paged window is opened over: one operator's segment
    // (386 MB for a Qwen3-8B layer, 1.24 GB for the LM head) or the whole
    // 16.4 GB checkpoint.  It is a `longint unsigned` because a
    // `parameter integer` is 32-bit and caps at 2 GiB, and nothing of this
    // size is ever resident: see the DPI window below.
    parameter longint unsigned MATMUL_WEIGHT_BYTES = 64'd50331648,
    parameter integer ENABLE_EXACT_MULTICAST = 0,
    // G1e hybrid co-simulation.  0: the engine array computes (the shipped
    // witness).  1: the ENTIRE control path is still this RTL -- fetch,
    // decode, view resolution, predicates, the loop stack, the wait set and
    // issue -- and only the engine RESULT is supplied, at the engine result
    // boundary, by the golden model.  No engine is instantiated in that mode.
    parameter integer ENABLE_RESULT_INJECTION = 0
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- host load path: program store, descriptor store, symbol file -----
    input  wire        host_we,
    input  wire [1:0]  host_sel,
    input  wire [31:0] host_row,
    input  wire [5:0]  host_lane,
    input  wire [31:0] host_wdata,
    output wire        host_ready,
    output wire        host_write_refused,

    input  wire        start,
    input  wire [31:0] cfg_program_base,
    input  wire [31:0] cfg_instruction_count,
    input  wire [31:0] cfg_entry_pc,
    input  wire [31:0] cfg_desc_base,
    input  wire [31:0] cfg_desc_count,
    input  wire [63:0] cfg_max_retired_work,
    input  wire [31:0] cfg_state_count,
    input  wire [31:0] cfg_index_base,
    input  wire [31:0] cfg_source_base,
    input  wire [31:0] cfg_source_launch_stride,
    input  wire [31:0] cfg_embedding_source_base,
    input  wire [31:0] cfg_rms_input_base,
    input  wire [31:0] cfg_rms_weight_base,
    input  wire [31:0] cfg_transfer_index_base,
    input  wire [31:0] cfg_transfer_source_base,
    input  wire [31:0] cfg_matmul_input_base,
    input  wire [31:0] cfg_matmul_weight_object_0,
    input  wire [31:0] cfg_matmul_weight_base_0,
    input  wire [31:0] cfg_matmul_weight_object_1,
    input  wire [31:0] cfg_matmul_weight_base_1,
    input  wire [31:0] cfg_matmul_weight_object_2,
    input  wire [31:0] cfg_matmul_weight_base_2,
    input  wire [31:0] cfg_head_input_object_0,
    input  wire [31:0] cfg_head_input_base_0,
    input  wire [31:0] cfg_head_input_object_1,
    input  wire [31:0] cfg_head_input_base_1,
    input  wire [31:0] cfg_head_weight_object_0,
    input  wire [31:0] cfg_head_weight_base_0,
    input  wire [31:0] cfg_head_weight_object_1,
    input  wire [31:0] cfg_head_weight_base_1,
    input  wire [31:0] cfg_rope_input_object_0,
    input  wire [31:0] cfg_rope_input_base_0,
    input  wire [31:0] cfg_rope_input_object_1,
    input  wire [31:0] cfg_rope_input_base_1,
    input  wire [31:0] cfg_rope_coefficient_object,
    input  wire [31:0] cfg_rope_coefficient_base,
    input  wire [31:0] cfg_output_base,
    // -- mapped placement for the six admitted operator families ---------
    // The bridge places DMA.SCATTER, ATTENTION.GQA, VECTOR.ADD,
    // VECTOR.SILU_MUL, SELECTION.ARGMAX and SELECTION.TOKEN_APPEND by
    // *object*, not by the appending result cursor, because a scatter is a
    // read-modify-write into a KV plane that already exists and the second
    // residual add writes back over the trunk object it read.  This top
    // therefore has to hand the bridge the same object->bank table its own
    // banks were built from; there is no default base and an unnamed object
    // is refused.  ``cfg_extended_placement_valid`` is the statement that
    // *this run* supplied that table.  Driving it low is not a way of
    // switching a check off: with no bank bound to an object the six
    // families have no operand address at all, so the bridge answers the
    // TRAP_CAPABILITY it gave before they were implemented, and the campaign
    // records that refusal as the measurement it is.
    input  wire        cfg_extended_placement_valid,
    input  wire [31:0] cfg_map_object_0,
    input  wire [31:0] cfg_map_base_0,
    input  wire [31:0] cfg_map_object_1,
    input  wire [31:0] cfg_map_base_1,
    input  wire [31:0] cfg_map_object_2,
    input  wire [31:0] cfg_map_base_2,
    input  wire [31:0] cfg_map_object_3,
    input  wire [31:0] cfg_map_base_3,
    input  wire [31:0] cfg_map_object_4,
    input  wire [31:0] cfg_map_base_4,
    input  wire [31:0] cfg_map_object_5,
    input  wire [31:0] cfg_map_base_5,
    input  wire [31:0] cfg_map_object_6,
    input  wire [31:0] cfg_map_base_6,
    input  wire [31:0] cfg_map_object_7,
    input  wire [31:0] cfg_map_base_7,
    // The request's active context length, checked inside the bridge against
    // the position the scatter and attention index views actually resolve to
    // (cfg_context_length == index + 1); the compact KV bank's fixed K-to-V
    // plane stride in rows, which does not move as the context grows; and the
    // bound GENERATION_POLICY with the authenticated request bound and the
    // tokens already produced.
    input  wire [31:0] cfg_context_length,
    input  wire [31:0] cfg_kv_plane_rows,
    input  wire [31:0] cfg_generation_policy_id,
    input  wire [31:0] cfg_request_max_new_tokens,
    input  wire [31:0] cfg_generated_before,
    // Byte offset of this operator's weight window inside the model image.
    // The engine port carries a 32-bit halfword offset, which reaches only
    // 8 GiB; the window base is what lets a bounded 32-bit operator offset
    // address any row of a 16.4 GB checkpoint.  64-bit throughout.
    input  wire [63:0] cfg_matmul_weight_window_base,
    // The device's own predicate-read port, served from device memory (never
    // from the golden model): object id and the word base inside result_mem.
    input  wire [31:0] cfg_predicate_object,
    input  wire [31:0] cfg_predicate_base,

    output wire        busy,
    output wire        done,
    output wire        complete,
    output wire        trapped,
    output wire [15:0] trap_class,
    output wire [31:0] first_fault_instruction,
    output wire [31:0] count_fetched,
    output wire [31:0] count_retired,
    output wire [31:0] count_predicated_off,
    output wire [31:0] count_issued,
    output wire [31:0] count_branches,
    output wire [31:0] count_loop_iterations,
    output wire [31:0] count_wait_events,
    output wire [31:0] count_signals,
    output wire [31:0] count_views_resolved,
    output wire [31:0] count_state_prepares,
    output wire [31:0] count_state_commits,
    output wire [31:0] count_state_discards,
    output wire [31:0] count_state_reads,
    output wire [31:0] count_state_generation_advances,
    output wire [31:0] count_state_commits_applied,
    output wire [31:0] count_state_rows_committed,
    output wire [63:0] count_state_bytes_written,
    output wire        event_signal_error,
    output wire        state_apply_overflow,

    output wire [31:0] real_launch_count,
    output wire [31:0] dma_gather_launch_count,
    output wire [31:0] embedding_launch_count,
    output wire [31:0] rms_norm_launch_count,
    output wire [31:0] head_rms_norm_launch_count,
    output wire [31:0] rope_launch_count,
    output wire [31:0] dma_transfer_launch_count,
    output wire [31:0] matmul_launch_count,
    // The six families this top now reaches.  Each is observed separately so
    // "the bridge admitted it" is a measurement per family rather than one
    // aggregate that a single admission could satisfy.
    output wire [31:0] vector_add_launch_count,
    output wire [31:0] vector_silu_mul_launch_count,
    output wire [31:0] dma_scatter_launch_count,
    output wire [31:0] attention_gqa_launch_count,
    output wire [31:0] selection_argmax_launch_count,
    output wire [31:0] selection_token_append_launch_count,
    output wire [31:0] selected_token,
    output wire [31:0] selected_tie_multiplicity,
    output wire [7:0]  selected_eos_reason,
    output wire [31:0] multicast_launch_count,
    output wire [31:0] multicast_fault_count,
    output wire [31:0] capability_fault_count,
    output wire [31:0] descriptor_fault_count,
    output wire [31:0] engine_fault_count,
    output wire [31:0] last_response_index,
    output wire [7:0]  last_response_family,
    output wire [7:0]  last_response_sub,
    output wire [31:0] last_response_descriptor_id,
    output wire        response_valid,
    output wire        response_fault,
    output wire [15:0] response_trap_class,
    output wire [7:0]  response_family,
    output wire [7:0]  response_sub,
    output wire [31:0] response_descriptor_id,
    output wire [31:0] response_index,
    output wire [7:0]  engine_error_code,
    output wire [31:0] engine_result_count,
    output wire [31:0] engine_work_count,
    output reg  [31:0] output_write_count,
    output reg  [31:0] writes_after_fault,
    output reg         operand_read_oob,
    output reg         result_write_oob,

    output wire        multicast_remote_write_valid,
    output wire        multicast_remote_write_ready,
    output wire [31:0] multicast_remote_write_object_id,
    output wire [15:0] multicast_remote_write_participant,
    output wire [63:0] multicast_remote_write_offset,
    output wire [31:0] multicast_remote_write_data,
    output wire [7:0]  multicast_tree_source,
    output wire [31:0] multicast_source_read_count,
    output wire [31:0] multicast_source_stall_cycles,
    output wire [31:0] multicast_destination_stall_cycles,
    output wire [31:0] multicast_remote_write_count,
    output wire [31:0] multicast_messages_sent,
    output wire [31:0] multicast_messages_received,
    output wire [63:0] multicast_bytes_sent,
    output wire [63:0] multicast_bytes_received,
    output wire [31:0] multicast_payload_flits,
    output wire [31:0] multicast_wire_flits,
    output wire [31:0] multicast_replayed_flits,
    output wire [31:0] multicast_retry_events,
    output wire [31:0] multicast_credit_stall_cycles,
    output wire [31:0] multicast_crc_errors,
    output wire [31:0] multicast_sequence_errors,
    output wire [31:0] multicast_writes_after_completion,
    output wire        multicast_protocol_error,

    input  wire [31:0] result_read_addr,
    output wire [31:0] result_read_data,

    // -- G1e issue trace, emitted by the RTL control plane ---------------
    // One record per accepted engine issue, taken at the sequencer's own
    // issue handshake: opcode, descriptor id, program counter, the schedule
    // (queue) the SCHEDULE record selected, the issue serial and the IRS
    // slot.  The resolved-view substream below carries every view the RTL
    // resolver produced for it, with its descriptor id and its resolved
    // address (object id is in the descriptor; extent, extent axis and
    // element offset are the resolved address).
    output wire        trace_issue_valid,
    output wire [7:0]  trace_issue_family,
    output wire [7:0]  trace_issue_sub,
    output wire [31:0] trace_issue_descriptor_id,
    output wire [31:0] trace_issue_index,
    output wire [31:0] trace_issue_serial,
    output wire [4:0]  trace_issue_queue,
    output wire [4:0]  trace_issue_slot,
    output wire        trace_view_valid,
    output wire [31:0] trace_view_descriptor_id,
    output wire [2:0]  trace_view_slot,
    output wire [31:0] trace_view_extent,
    output wire [7:0]  trace_view_extent_axis,
    output wire [63:0] trace_view_element_offset,
    output wire [7:0]  trace_view_rank,
    output wire [4:0]  trace_view_irs_slot,
    output wire [31:0] trace_issue_count,
    output wire [31:0] trace_view_count,

    // -- G1e engine-result injection boundary ----------------------------
    // Visible only when ENABLE_RESULT_INJECTION != 0.  These reach exactly
    // two places: the engine port's completion handshake, and result memory.
    // No injection signal is an input to fetch, decode, view resolution,
    // predicate evaluation, the loop stack, the wait set or issue.
    output wire        inj_issue_valid,
    output wire [7:0]  inj_issue_family,
    output wire [7:0]  inj_issue_sub,
    output wire [31:0] inj_issue_descriptor_id,
    output wire [31:0] inj_issue_index,
    output wire [31:0] inj_issue_view_count,
    input  wire        inj_result_valid,
    input  wire        inj_result_fault,
    input  wire [15:0] inj_result_trap_class,
    input  wire        inj_write_en,
    input  wire [31:0] inj_write_addr,
    input  wire [31:0] inj_write_data,
    output reg  [31:0] inj_completion_count,
    output wire        injection_enabled,

    // -- predicate read service, from device memory ----------------------
    output reg  [31:0] predicate_read_count,
    output reg  [31:0] predicate_read_refused_count
);
    reg [255:0]  program_mem [0:PROGRAM_WORDS-1];
    reg [1535:0] desc_mem [0:DESC_WORDS-1];
    reg [511:0]  irs_payload_mem [0:ot_a3_pkg::A3_IRS_ENTRIES*8-1];
    reg [31:0]   index_mem [0:INDEX_WORDS-1];
    reg [31:0]   source_mem [0:SOURCE_WORDS-1];
    reg [31:0]   result_mem [0:RESULT_WORDS-1];

    // -- the weight image: addressed through a paged window, never held ---
    // The previous form declared `reg [7:0] matmul_weight_mem
    // [0:MATMUL_WEIGHT_BYTES-1]` and $fread the whole blob at time 0.  That
    // is one resident byte of simulator heap per checkpoint byte: 386 MB for
    // one Qwen3-8B layer, 1.24 GB for the LM head, 16.4 GB for the model --
    // and the declaration could not even be written, because a
    // `parameter integer` is 32 bits.  The window below serves the same
    // little-endian BF16 halfword from the real safetensors shards through a
    // bounded, hard-capped page cache in the checker, so the memory the
    // harness holds is the working set of one operator, not the model.
    import "DPI-C" function longint unsigned ot_a3_weight_window_open(
        input longint unsigned declared_bytes);
    import "DPI-C" function int unsigned ot_a3_weight_window_halfword(
        input longint unsigned halfword_index);
    import "DPI-C" function void ot_a3_geometry_declare(
        input int unsigned program_words,
        input int unsigned desc_words,
        input int unsigned index_words,
        input int unsigned source_words,
        input int unsigned result_words,
        input longint unsigned matmul_weight_bytes,
        input int unsigned result_injection,
        input int unsigned exact_multicast);

    // Complete exact records cannot all be reconstructed from the 192-byte
    // descriptor-prefix image: TOPOLOGY is 256 bytes.  These side images are
    // the first, admitted vector of the retained multicast qualification and
    // are hash-bound by the overlay manifest and campaign.
    reg [31:0] multicast_communication_mem [0:47];
    reg [31:0] multicast_topology_mem [0:63];
    reg [31:0] multicast_local_object_mem [0:31];
    reg [31:0] multicast_remote_object_mem [0:31];
    reg [31:0] multicast_counter_mem [0:31];
    reg [31:0] multicast_source_mem [0:16383];
    reg [1535:0] multicast_communication_record;
    reg [2047:0] multicast_topology_record;
    reg [1023:0] multicast_local_object_record;
    reg [1023:0] multicast_remote_object_record;
    reg [1023:0] multicast_counter_record;

    integer clear_word;
    integer multicast_record_word;
    longint unsigned weight_window_bytes;
    initial begin
        ot_a3_geometry_declare(PROGRAM_WORDS, DESC_WORDS, INDEX_WORDS,
                               SOURCE_WORDS, RESULT_WORDS,
                               MATMUL_WEIGHT_BYTES, ENABLE_RESULT_INJECTION,
                               ENABLE_EXACT_MULTICAST);
        $readmemh("p3_index.hex", index_mem);
        $readmemh("p3_source.hex", source_mem);
        multicast_communication_record = 1536'd0;
        multicast_topology_record = 2048'd0;
        multicast_local_object_record = 1024'd0;
        multicast_remote_object_record = 1024'd0;
        multicast_counter_record = 1024'd0;
        if (ENABLE_EXACT_MULTICAST != 0) begin
            $readmemh("p3_multicast_communication.hex",
                      multicast_communication_mem);
            $readmemh("p3_multicast_topology.hex", multicast_topology_mem);
            $readmemh("p3_multicast_local_object.hex",
                      multicast_local_object_mem);
            $readmemh("p3_multicast_remote_object.hex",
                      multicast_remote_object_mem);
            $readmemh("p3_multicast_counter.hex", multicast_counter_mem);
            $readmemh("p3_multicast_source.hex", multicast_source_mem);
            for (multicast_record_word = 0; multicast_record_word < 48;
                 multicast_record_word = multicast_record_word + 1)
                multicast_communication_record[
                    multicast_record_word*32 +: 32] =
                    multicast_communication_mem[multicast_record_word];
            for (multicast_record_word = 0; multicast_record_word < 64;
                 multicast_record_word = multicast_record_word + 1)
                multicast_topology_record[
                    multicast_record_word*32 +: 32] =
                    multicast_topology_mem[multicast_record_word];
            for (multicast_record_word = 0; multicast_record_word < 32;
                 multicast_record_word = multicast_record_word + 1) begin
                multicast_local_object_record[
                    multicast_record_word*32 +: 32] =
                    multicast_local_object_mem[multicast_record_word];
                multicast_remote_object_record[
                    multicast_record_word*32 +: 32] =
                    multicast_remote_object_mem[multicast_record_word];
                multicast_counter_record[multicast_record_word*32 +: 32] =
                    multicast_counter_mem[multicast_record_word];
            end
        end
        // Open, do not load.  The window reports the byte count it can
        // serve; a disagreement with the declared image is fatal, exactly as
        // the short-$fread check was.
        weight_window_bytes = ot_a3_weight_window_open(MATMUL_WEIGHT_BYTES);
        if (weight_window_bytes != MATMUL_WEIGHT_BYTES)
            $fatal(1, "weight window serves %0d bytes, expected %0d",
                   weight_window_bytes, MATMUL_WEIGHT_BYTES);
        for (clear_word = 0; clear_word < RESULT_WORDS;
             clear_word = clear_word + 1)
            result_mem[clear_word] = 32'hdead_beef;
    end

    // -- control stores behind the device top's store boundaries ---------
    // One synchronous port each, ganged from 32-bit lanes: a read presents
    // the row one cycle later and holds it, a write lands one lane.  The
    // base/bound/fault logic that used to sit here is the design's and lives
    // in ot_a3_device_top.
    wire         pstore_en;
    wire         pstore_we;
    wire [31:0]  pstore_addr;
    wire [2:0]   pstore_wlane;
    wire [31:0]  pstore_wdata;
    reg  [255:0] pstore_rdata;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pstore_rdata <= 256'd0;
        end else if (pstore_en) begin
            if (pstore_we)
                program_mem[pstore_addr[19:0]][pstore_wlane*32 +: 32]
                    <= pstore_wdata;
            else
                pstore_rdata <= program_mem[pstore_addr[19:0]];
        end
    end

    wire          dstore_en;
    wire          dstore_we;
    wire [31:0]   dstore_addr;
    wire [5:0]    dstore_wlane;
    wire [31:0]   dstore_wdata;
    reg  [1535:0] dstore_rdata;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dstore_rdata <= 1536'd0;
        end else if (dstore_en) begin
            if (dstore_we)
                desc_mem[dstore_addr[19:0]][dstore_wlane*32 +: 32]
                    <= dstore_wdata;
            else
                dstore_rdata <= desc_mem[dstore_addr[19:0]];
        end
    end

    // -- independent descriptor read port for the engine bridge --------
    wire bridge_desc_req;
    wire [31:0] bridge_desc_id;
    reg bridge_desc_valid;
    reg bridge_desc_fault;
    reg [1535:0] bridge_desc_data;
    wire [32:0] bridge_desc_absolute =
        {1'b0, cfg_desc_base} + {1'b0, bridge_desc_id};
    wire bridge_desc_oob = (bridge_desc_id >= cfg_desc_count) ||
                            (bridge_desc_absolute >= DESC_WORDS);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bridge_desc_valid <= 1'b0;
            bridge_desc_fault <= 1'b0;
            bridge_desc_data <= 1536'd0;
        end else begin
            bridge_desc_valid <= bridge_desc_req;
            if (bridge_desc_req) begin
                bridge_desc_fault <= bridge_desc_oob;
                bridge_desc_data <= bridge_desc_oob
                    ? 1536'd0 : desc_mem[bridge_desc_absolute[19:0]];
            end
        end
    end

    // -- issue record store payload behind the device top's boundary ------
    wire         irs_we;
    wire [4:0]   irs_wslot;
    wire [2:0]   irs_wlane;
    wire [511:0] irs_wdata;
    wire         irs_re;
    wire [4:0]   irs_rslot;
    wire [2:0]   irs_rlane;
    reg  [511:0] irs_rdata;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            irs_rdata <= 512'd0;
        end else begin
            if (irs_we)
                irs_payload_mem[{irs_wslot, irs_wlane}] <= irs_wdata;
            if (irs_re)
                irs_rdata <= irs_payload_mem[{irs_rslot, irs_rlane}];
        end
    end

    // -- the sequencer's two-phase engine port ---------------------------
    wire seq_issue_valid;
    wire seq_issue_ready;
    wire [7:0] seq_issue_family;
    wire [7:0] seq_issue_sub;
    wire [31:0] seq_issue_descriptor_id;
    wire [31:0] seq_issue_index;
    wire [4:0] seq_issue_slot;
    wire [31:0] seq_issue_serial;
    wire [4:0] seq_issue_queue;
    wire seq_view_valid;
    wire [31:0] seq_view_descriptor_id;
    wire [2:0] seq_view_slot;
    wire [31:0] seq_view_extent;
    wire [7:0] seq_view_extent_axis;
    wire [63:0] seq_view_element_offset;
    wire [7:0] seq_view_rank;
    wire [4:0] seq_view_irs_slot;
    wire complete_valid;
    wire [4:0] complete_slot;
    wire complete_fault;
    wire [15:0] complete_trap_class;

    // -- the engine-side run-to-completion port, from the adapter ---------
    wire issue_valid;
    wire issue_ready;
    wire issue_fault;
    wire [15:0] issue_trap_class;
    wire [7:0] issue_family;
    wire [7:0] issue_sub;
    wire [31:0] issue_descriptor_id;
    wire [31:0] issue_index;
    wire [31:0] issue_view_count;
    wire view_valid;
    wire [31:0] view_descriptor_id;
    wire [2:0] view_slot;
    wire [31:0] view_extent;
    wire [7:0] view_extent_axis;
    wire [63:0] view_element_offset;
    wire [7:0] view_rank;

    a3_engine_completion_adapter adapter (
        .clk(clk),
        .rst_n(rst_n),
        .clear(start),
        .issue_valid(seq_issue_valid),
        .issue_ready(seq_issue_ready),
        .issue_family(seq_issue_family),
        .issue_sub(seq_issue_sub),
        .issue_descriptor_id(seq_issue_descriptor_id),
        .issue_index(seq_issue_index),
        .issue_slot(seq_issue_slot),
        .view_valid(seq_view_valid),
        .view_descriptor_id(seq_view_descriptor_id),
        .view_slot(seq_view_slot),
        .view_extent(seq_view_extent),
        .view_extent_axis(seq_view_extent_axis),
        .view_element_offset(seq_view_element_offset),
        .view_rank(seq_view_rank),
        .view_irs_slot(seq_view_irs_slot),
        .complete_valid(complete_valid),
        .complete_slot(complete_slot),
        .complete_fault(complete_fault),
        .complete_trap_class(complete_trap_class),
        .eng_issue_valid(issue_valid),
        .eng_issue_ready(issue_ready),
        .eng_issue_fault(issue_fault),
        .eng_issue_trap_class(issue_trap_class),
        .eng_issue_family(issue_family),
        .eng_issue_sub(issue_sub),
        .eng_issue_descriptor_id(issue_descriptor_id),
        .eng_issue_index(issue_index),
        .eng_issue_view_count(issue_view_count),
        .eng_view_valid(view_valid),
        .eng_view_descriptor_id(view_descriptor_id),
        .eng_view_slot(view_slot),
        .eng_view_extent(view_extent),
        .eng_view_extent_axis(view_extent_axis),
        .eng_view_element_offset(view_element_offset),
        .eng_view_rank(view_rank)
    );

    wire bridge_issue_ready;
    wire bridge_issue_fault;
    wire [15:0] bridge_issue_trap_class;
    wire exact_multicast_issue = (ENABLE_EXACT_MULTICAST != 0) && issue_valid &&
        (issue_family == 8'h90) && (issue_sub == 8'd3);
    reg multicast_issue_active;
    reg multicast_start;
    reg multicast_inject_crc;
    reg [31:0] multicast_observed_views;
    reg [31:0] multicast_launch_count_q;
    reg [31:0] multicast_fault_count_q;
    wire multicast_busy;
    wire multicast_done;
    wire multicast_failed;
    wire [15:0] multicast_trap_class;
    wire [7:0] multicast_refusal_reason;

    // The completion the engine port returns: the multicast adapter's, the
    // engine bridge's, or -- in G1e hybrid co-simulation -- the golden
    // model's, at the engine RESULT boundary and nowhere else.
    wire injected_ready = (ENABLE_RESULT_INJECTION != 0) && inj_result_valid;
    wire engine_ready = (ENABLE_RESULT_INJECTION != 0)
        ? injected_ready : bridge_issue_ready;
    wire engine_fault = (ENABLE_RESULT_INJECTION != 0)
        ? (inj_result_valid && inj_result_fault) : bridge_issue_fault;
    wire [15:0] engine_trap_class = (ENABLE_RESULT_INJECTION != 0)
        ? inj_result_trap_class : bridge_issue_trap_class;
    assign issue_ready = exact_multicast_issue
        ? (multicast_issue_active && (multicast_done || multicast_failed))
        : engine_ready;
    assign issue_fault = exact_multicast_issue
        ? multicast_failed : engine_fault;
    assign issue_trap_class = exact_multicast_issue
        ? multicast_trap_class : engine_trap_class;

    assign response_valid = issue_valid && issue_ready;
    assign response_fault = issue_fault;
    assign response_trap_class = issue_trap_class;
    assign response_family = issue_family;
    assign response_sub = issue_sub;
    assign response_descriptor_id = issue_descriptor_id;
    assign response_index = issue_index;

    assign multicast_launch_count = multicast_launch_count_q;
    assign multicast_fault_count = multicast_fault_count_q;

    reg        predicate_read_valid;
    reg        predicate_read_value;
    reg [15:0] predicate_read_trap_class;
    wire        predicate_read_req;
    wire [31:0] predicate_read_object_id;
    wire [31:0] predicate_read_element_index;

    ot_a3_device_top #(
        .PROGRAM_WORDS(PROGRAM_WORDS),
        .DESC_WORDS(DESC_WORDS),
        .STATE_COMPAT(0)
    ) device (
        .clk(clk),
        .rst_n(rst_n),
        // This witness admits no program header and preloads its stores.
        .hdr_in_valid(1'b0),
        .hdr_in_start(1'b0),
        .hdr_in_word(32'd0),
        .header_done(),
        .header_legal(),
        .header_error(),
        .header_trap_class(),
        .header_instruction_count(),
        .header_entrypoint_count(),
        .header_max_retired_work(),
        .header_entrypoint_descriptor(),
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
        .irs_we(irs_we),
        .irs_wslot(irs_wslot),
        .irs_wlane(irs_wlane),
        .irs_wdata(irs_wdata),
        .irs_re(irs_re),
        .irs_rslot(irs_rslot),
        .irs_rlane(irs_rlane),
        .irs_rdata(irs_rdata),
        .predicate_read_req(predicate_read_req),
        .predicate_read_object_id(predicate_read_object_id),
        .predicate_read_element_index(predicate_read_element_index),
        .predicate_read_valid(predicate_read_valid),
        .predicate_read_value(predicate_read_value),
        .predicate_read_trap_class(predicate_read_trap_class),
        .issue_valid(seq_issue_valid),
        .issue_ready(seq_issue_ready),
        .issue_family(seq_issue_family),
        .issue_sub(seq_issue_sub),
        .issue_descriptor_id(seq_issue_descriptor_id),
        .issue_index(seq_issue_index),
        .issue_serial(seq_issue_serial),
        .issue_slot(seq_issue_slot),
        .issue_queue(seq_issue_queue),
        .complete_valid(complete_valid),
        .complete_slot(complete_slot),
        .complete_fault(complete_fault),
        .complete_trap_class(complete_trap_class),
        .view_valid(seq_view_valid),
        .view_descriptor_id(seq_view_descriptor_id),
        .view_slot(seq_view_slot),
        .view_extent(seq_view_extent),
        .view_extent_axis(seq_view_extent_axis),
        .view_element_offset(seq_view_element_offset),
        .view_rank(seq_view_rank),
        .view_irs_slot(seq_view_irs_slot),
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
        .loop_depth(),
        .event_signal_error(event_signal_error),
        .state_apply_overflow(state_apply_overflow),
        .dbg_decode_error(),
        .dbg_source_operation_id(),
        .dbg_wait_fault_event(),
        .dbg_loop_action(),
        .dbg_outstanding(),
        .dbg_max_outstanding(),
        .dbg_dep_stalls(),
        .dbg_wait_stalls(),
        .irs_protocol_error()
    );

    // -- G1e issue trace -------------------------------------------------
    // Taken at the sequencer's OWN issue handshake, not at the engine port:
    // this is the control plane's issue event, with the schedule the
    // SCHEDULE record selected and the serial the sequencer allocated.  The
    // view substream is the RTL resolver's output for that issue -- resolved
    // descriptor id, slot, extent, extent axis and element offset.
    reg [31:0] trace_issue_count_q;
    reg [31:0] trace_view_count_q;
    assign trace_issue_valid = seq_issue_valid && seq_issue_ready;
    assign trace_issue_family = seq_issue_family;
    assign trace_issue_sub = seq_issue_sub;
    assign trace_issue_descriptor_id = seq_issue_descriptor_id;
    assign trace_issue_index = seq_issue_index;
    assign trace_issue_serial = seq_issue_serial;
    assign trace_issue_queue = seq_issue_queue;
    assign trace_issue_slot = seq_issue_slot;
    assign trace_view_valid = seq_view_valid;
    assign trace_view_descriptor_id = seq_view_descriptor_id;
    assign trace_view_slot = seq_view_slot;
    assign trace_view_extent = seq_view_extent;
    assign trace_view_extent_axis = seq_view_extent_axis;
    assign trace_view_element_offset = seq_view_element_offset;
    assign trace_view_rank = seq_view_rank;
    assign trace_view_irs_slot = seq_view_irs_slot;
    assign trace_issue_count = trace_issue_count_q;
    assign trace_view_count = trace_view_count_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trace_issue_count_q <= 32'd0;
            trace_view_count_q <= 32'd0;
        end else if (start) begin
            trace_issue_count_q <= 32'd0;
            trace_view_count_q <= 32'd0;
        end else begin
            if (trace_issue_valid)
                trace_issue_count_q <= trace_issue_count_q + 32'd1;
            if (trace_view_valid)
                trace_view_count_q <= trace_view_count_q + 32'd1;
        end
    end

    // -- predicate reads, served from the device's own memory -------------
    // A predicate outcome may never come from the golden model (G1e property
    // 2).  The sequencer's predicate logic evaluates it; this port only
    // supplies the element the machine itself wrote into result memory.  An
    // unmapped object is refused with A3_TRAP_DESCRIPTOR, never guessed.
    wire [32:0] predicate_word_addr =
        {1'b0, cfg_predicate_base} + {1'b0, predicate_read_element_index};
    wire predicate_mapped =
        (predicate_read_object_id == cfg_predicate_object) &&
        (predicate_word_addr < RESULT_WORDS);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            predicate_read_valid <= 1'b0;
            predicate_read_value <= 1'b0;
            predicate_read_trap_class <= 16'd0;
            predicate_read_count <= 32'd0;
            predicate_read_refused_count <= 32'd0;
        end else begin
            predicate_read_valid <= 1'b0;
            predicate_read_trap_class <= 16'd0;
            predicate_read_value <= 1'b0;
            if (start) begin
                predicate_read_count <= 32'd0;
                predicate_read_refused_count <= 32'd0;
            end
            if (predicate_read_req && !predicate_read_valid) begin
                predicate_read_valid <= 1'b1;
                predicate_read_count <= predicate_read_count + 32'd1;
                if (predicate_mapped) begin
                    predicate_read_value <=
                        (result_mem[predicate_word_addr[31:0]] != 32'd0);
                end else begin
                    predicate_read_trap_class <=
                        ot_a3_pkg::A3_TRAP_DESCRIPTOR;
                    predicate_read_refused_count <=
                        predicate_read_refused_count + 32'd1;
                end
            end
        end
    end

    // The last response the engine port returned.  Under injection the
    // bridge is idle, so these are latched from the completion the RTL
    // itself issued -- the opcode, descriptor and PC the sequencer produced,
    // not anything the golden model supplied -- and they are therefore
    // checked against the very same expectations as the real-engine run.
    wire [31:0] bridge_last_response_index;
    wire [7:0]  bridge_last_response_family;
    wire [7:0]  bridge_last_response_sub;
    wire [31:0] bridge_last_response_descriptor_id;
    reg  [31:0] inj_last_response_index;
    reg  [7:0]  inj_last_response_family;
    reg  [7:0]  inj_last_response_sub;
    reg  [31:0] inj_last_response_descriptor_id;
    assign last_response_index = (ENABLE_RESULT_INJECTION != 0)
        ? inj_last_response_index : bridge_last_response_index;
    assign last_response_family = (ENABLE_RESULT_INJECTION != 0)
        ? inj_last_response_family : bridge_last_response_family;
    assign last_response_sub = (ENABLE_RESULT_INJECTION != 0)
        ? inj_last_response_sub : bridge_last_response_sub;
    assign last_response_descriptor_id = (ENABLE_RESULT_INJECTION != 0)
        ? inj_last_response_descriptor_id : bridge_last_response_descriptor_id;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            inj_last_response_index <= 32'hffff_ffff;
            inj_last_response_family <= 8'hff;
            inj_last_response_sub <= 8'hff;
            inj_last_response_descriptor_id <= 32'hffff_ffff;
        end else if (start) begin
            inj_last_response_index <= 32'hffff_ffff;
            inj_last_response_family <= 8'hff;
            inj_last_response_sub <= 8'hff;
            inj_last_response_descriptor_id <= 32'hffff_ffff;
        end else if (inj_issue_valid && issue_ready) begin
            inj_last_response_index <= issue_index;
            inj_last_response_family <= issue_family;
            inj_last_response_sub <= issue_sub;
            inj_last_response_descriptor_id <= issue_descriptor_id;
        end
    end

    // -- G1e engine-result injection --------------------------------------
    // The issue reaches the engine port exactly as it does in the shipped
    // witness -- through the sequencer, the completion adapter and the
    // resolved-view replay.  Only the RESULT is supplied here.  When
    // injection is enabled the engine array is never issued to, so
    // real_launch_count and engine_work_count read zero: the evidence that
    // nothing was computed.
    assign injection_enabled = (ENABLE_RESULT_INJECTION != 0);
    assign inj_issue_valid = injection_enabled && issue_valid &&
                             !exact_multicast_issue;
    assign inj_issue_family = issue_family;
    assign inj_issue_sub = issue_sub;
    assign inj_issue_descriptor_id = issue_descriptor_id;
    assign inj_issue_index = issue_index;
    assign inj_issue_view_count = issue_view_count;

    // -- exact DeepSeek ROM wafer multicast ----------------------------
    // LINK owns no tensor views.  Record the number the adapter replayed for
    // this very issue and make the multicast adapter admit zero rather than
    // assuming it.  Every other LINK shape remains routed to the ordinary
    // bridge and receives its existing fail-closed CAPABILITY response.
    wire multicast_response_fire = exact_multicast_issue && issue_ready;
    reg multicast_started_this_transaction;
    reg [31:0] multicast_service_cycle;
    reg [31:0] multicast_source_read_count_q;
    reg [31:0] multicast_source_stall_cycles_q;
    reg [31:0] multicast_destination_stall_cycles_q;
    reg [31:0] multicast_writes_after_completion_q;
    reg multicast_protocol_error_q;
    reg multicast_completed_seen;
    reg multicast_source_ready_phase;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            multicast_issue_active <= 1'b0;
            multicast_start <= 1'b0;
            multicast_inject_crc <= 1'b0;
            multicast_observed_views <= 32'd0;
            multicast_launch_count_q <= 32'd0;
            multicast_fault_count_q <= 32'd0;
            multicast_started_this_transaction <= 1'b0;
            multicast_service_cycle <= 32'd0;
            multicast_completed_seen <= 1'b0;
        end else begin
            multicast_start <= 1'b0;
            multicast_inject_crc <= 1'b0;
            if (start) begin
                multicast_issue_active <= 1'b0;
                multicast_observed_views <= 32'd0;
                multicast_launch_count_q <= 32'd0;
                multicast_fault_count_q <= 32'd0;
                multicast_started_this_transaction <= 1'b0;
                multicast_service_cycle <= 32'd0;
                multicast_completed_seen <= 1'b0;
            end else begin
                if (multicast_issue_active)
                    multicast_service_cycle <= multicast_service_cycle + 32'd1;
                if (!multicast_issue_active && exact_multicast_issue) begin
                    multicast_issue_active <= 1'b1;
                    multicast_started_this_transaction <= 1'b1;
                    multicast_observed_views <= issue_view_count;
                    // The endpoint is idle when this pulse is sampled.  One
                    // packet is corrupted and recovered through NAK/replay.
                    multicast_inject_crc <= 1'b1;
                    multicast_start <= 1'b1;
                end
                if (multicast_done)
                    multicast_completed_seen <= 1'b1;
                if (multicast_response_fire) begin
                    multicast_issue_active <= 1'b0;
                    if (multicast_failed)
                        multicast_fault_count_q <=
                            multicast_fault_count_q + 32'd1;
                    else
                        multicast_launch_count_q <=
                            multicast_launch_count_q + 32'd1;
                end
            end
        end
    end

    function automatic [31:0] multicast_expected_word;
        input [13:0] index;
        reg [31:0] widened;
        begin
            widened = {18'd0, index};
            multicast_expected_word = 32'h9e37_79b9 ^
                (widened * 32'h045d_9f3b) ^ {index, index, index[3:0]};
        end
    endfunction

    wire multicast_source_read_valid_int;
    wire multicast_source_read_ready_int = multicast_issue_active &&
        multicast_source_ready_phase;
    wire [31:0] multicast_source_read_object_id_int;
    wire [63:0] multicast_source_read_offset_int;
    reg multicast_source_response_valid;
    wire multicast_source_response_ready;
    reg [31:0] multicast_source_response_data;

    assign multicast_source_read_count = multicast_source_read_count_q;
    assign multicast_source_stall_cycles = multicast_source_stall_cycles_q;
    assign multicast_destination_stall_cycles =
        multicast_destination_stall_cycles_q;
    assign multicast_writes_after_completion =
        multicast_writes_after_completion_q;
    assign multicast_protocol_error = multicast_protocol_error_q;

    // One-outstanding-response scratch-memory service.  Its nonzero contents
    // represent live object 365; they are intentionally not aliased to the
    // preceding DMA result, which belongs to a different object.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            multicast_source_response_valid <= 1'b0;
            multicast_source_response_data <= 32'd0;
            multicast_source_read_count_q <= 32'd0;
            multicast_source_stall_cycles_q <= 32'd0;
            multicast_destination_stall_cycles_q <= 32'd0;
            multicast_writes_after_completion_q <= 32'd0;
            multicast_protocol_error_q <= 1'b0;
            multicast_source_ready_phase <= 1'b0;
        end else begin
            if (start) begin
                multicast_source_response_valid <= 1'b0;
                multicast_source_response_data <= 32'd0;
                multicast_source_read_count_q <= 32'd0;
                multicast_source_stall_cycles_q <= 32'd0;
                multicast_destination_stall_cycles_q <= 32'd0;
                multicast_writes_after_completion_q <= 32'd0;
                multicast_protocol_error_q <= 1'b0;
                multicast_source_ready_phase <= 1'b0;
            end else begin
                if (!multicast_source_read_valid_int)
                    multicast_source_ready_phase <= 1'b0;
                else if (!multicast_source_ready_phase)
                    multicast_source_ready_phase <= 1'b1;
                else if (multicast_source_read_ready_int)
                    multicast_source_ready_phase <= 1'b0;
                if (multicast_source_response_valid &&
                    multicast_source_response_ready)
                    multicast_source_response_valid <= 1'b0;
                if (multicast_source_read_valid_int &&
                    !multicast_source_read_ready_int)
                    multicast_source_stall_cycles_q <=
                        multicast_source_stall_cycles_q + 32'd1;
                if (multicast_source_read_valid_int &&
                    multicast_source_read_ready_int) begin
                    multicast_source_read_count_q <=
                        multicast_source_read_count_q + 32'd1;
                    if ((multicast_source_read_object_id_int != 32'd365) ||
                        (multicast_source_read_offset_int[1:0] != 2'd0) ||
                        (multicast_source_read_offset_int >= 64'd65536) ||
                        (multicast_source_read_offset_int[15:2] !=
                         multicast_source_read_count_q[13:0])) begin
                        multicast_source_response_data <= 32'd0;
                        multicast_protocol_error_q <= 1'b1;
                    end else begin
                        multicast_source_response_data <=
                            multicast_source_mem[
                                multicast_source_read_offset_int[15:2]];
                    end
                    multicast_source_response_valid <= 1'b1;
                end
                if (multicast_remote_write_valid &&
                    !multicast_remote_write_ready)
                    multicast_destination_stall_cycles_q <=
                        multicast_destination_stall_cycles_q + 32'd1;
                if (multicast_remote_write_valid &&
                    multicast_remote_write_ready) begin
                    if ((multicast_remote_write_object_id != 32'd366) ||
                        (multicast_remote_write_offset[1:0] != 2'd0) ||
                        (multicast_remote_write_offset >= 64'd16777216) ||
                        (multicast_remote_write_participant !=
                         {8'd0, multicast_remote_write_offset[23:16]}) ||
                        (multicast_remote_write_data !=
                         multicast_expected_word(
                             multicast_remote_write_offset[15:2])))
                        multicast_protocol_error_q <= 1'b1;
                    if (multicast_completed_seen)
                        multicast_writes_after_completion_q <=
                            multicast_writes_after_completion_q + 32'd1;
                end
            end
        end
    end

    // One-cycle deterministic ready gaps exercise integration-level source
    // and destination backpressure while remaining far below endpoint timeout.
    assign multicast_remote_write_ready = multicast_issue_active &&
        (multicast_service_cycle[1:0] != 2'b00);

    wire [31:0] multicast_messages_sent_int;
    wire [31:0] multicast_messages_received_int;
    wire [63:0] multicast_bytes_sent_int;
    wire [63:0] multicast_bytes_received_int;
    wire [31:0] multicast_remote_write_count_int;
    wire [31:0] multicast_payload_flits_int;
    wire [31:0] multicast_wire_flits_int;
    wire [31:0] multicast_replayed_flits_int;
    wire [31:0] multicast_retry_events_int;
    wire [31:0] multicast_credit_stall_cycles_int;
    wire [31:0] multicast_crc_errors_int;
    wire [31:0] multicast_sequence_errors_int;

    assign multicast_messages_sent = multicast_started_this_transaction
        ? multicast_messages_sent_int : 32'd0;
    assign multicast_messages_received = multicast_started_this_transaction
        ? multicast_messages_received_int : 32'd0;
    assign multicast_bytes_sent = multicast_started_this_transaction
        ? multicast_bytes_sent_int : 64'd0;
    assign multicast_bytes_received = multicast_started_this_transaction
        ? multicast_bytes_received_int : 64'd0;
    assign multicast_remote_write_count = multicast_started_this_transaction
        ? multicast_remote_write_count_int : 32'd0;
    assign multicast_payload_flits = multicast_started_this_transaction
        ? multicast_payload_flits_int : 32'd0;
    assign multicast_wire_flits = multicast_started_this_transaction
        ? multicast_wire_flits_int : 32'd0;
    assign multicast_replayed_flits = multicast_started_this_transaction
        ? multicast_replayed_flits_int : 32'd0;
    assign multicast_retry_events = multicast_started_this_transaction
        ? multicast_retry_events_int : 32'd0;
    assign multicast_credit_stall_cycles =
        multicast_started_this_transaction
        ? multicast_credit_stall_cycles_int : 32'd0;
    assign multicast_crc_errors = multicast_started_this_transaction
        ? multicast_crc_errors_int : 32'd0;
    assign multicast_sequence_errors = multicast_started_this_transaction
        ? multicast_sequence_errors_int : 32'd0;

    generate
        if (ENABLE_EXACT_MULTICAST != 0) begin : g_exact_multicast
            ot_a3_shipped_prefix_multicast_adapter_wrapper u_multicast (
                .clk(clk), .rst_n(rst_n), .start(multicast_start),
                .issue_pc(issue_index), .issue_major(issue_family),
                .issue_sub(issue_sub),
                .issue_descriptor_id(issue_descriptor_id),
                .observed_view_count(multicast_observed_views),
                .state_descriptor_count(cfg_state_count),
                .topology_descriptor_id(32'd0),
                .local_object_descriptor_id(32'd365),
                .remote_object_descriptor_id(32'd366),
                .counter_descriptor_id(32'd367),
                .communication_record(multicast_communication_record),
                .topology_record(multicast_topology_record),
                .local_object_record(multicast_local_object_record),
                .remote_object_record(multicast_remote_object_record),
                .counter_record(multicast_counter_record),
                .source_read_valid(multicast_source_read_valid_int),
                .source_read_ready(multicast_source_read_ready_int),
                .source_read_object_id(multicast_source_read_object_id_int),
                .source_read_offset(multicast_source_read_offset_int),
                .source_response_valid(multicast_source_response_valid),
                .source_response_ready(multicast_source_response_ready),
                .source_response_data(multicast_source_response_data),
                .source_response_error(1'b0),
                .remote_write_valid(multicast_remote_write_valid),
                .remote_write_ready(multicast_remote_write_ready),
                .remote_write_object_id(multicast_remote_write_object_id),
                .remote_write_participant(
                    multicast_remote_write_participant),
                .remote_write_offset(multicast_remote_write_offset),
                .remote_write_data(multicast_remote_write_data),
                .inject_crc_error(multicast_inject_crc),
                .busy(multicast_busy), .done(multicast_done),
                .failed(multicast_failed),
                .trap_class(multicast_trap_class),
                .refusal_reason(multicast_refusal_reason),
                .messages_sent(multicast_messages_sent_int),
                .messages_received(multicast_messages_received_int),
                .bytes_sent(multicast_bytes_sent_int),
                .bytes_received(multicast_bytes_received_int),
                .remote_write_count(multicast_remote_write_count_int),
                .payload_flits_delivered(multicast_payload_flits_int),
                .wire_flits_transmitted(multicast_wire_flits_int),
                .replayed_flits(multicast_replayed_flits_int),
                .retry_events(multicast_retry_events_int),
                .credit_stall_cycles(multicast_credit_stall_cycles_int),
                .crc_errors(multicast_crc_errors_int),
                .sequence_errors(multicast_sequence_errors_int),
                .tree_source(multicast_tree_source)
            );
        end else begin : g_no_exact_multicast
            assign multicast_source_read_valid_int = 1'b0;
            assign multicast_source_read_object_id_int = 32'd0;
            assign multicast_source_read_offset_int = 64'd0;
            assign multicast_source_response_ready = 1'b0;
            assign multicast_remote_write_valid = 1'b0;
            assign multicast_remote_write_object_id = 32'd0;
            assign multicast_remote_write_participant = 16'd0;
            assign multicast_remote_write_offset = 64'd0;
            assign multicast_remote_write_data = 32'd0;
            assign multicast_busy = 1'b0;
            assign multicast_done = 1'b0;
            assign multicast_failed = 1'b0;
            assign multicast_trap_class = 16'd0;
            assign multicast_refusal_reason = 8'd0;
            assign multicast_messages_sent_int = 32'd0;
            assign multicast_messages_received_int = 32'd0;
            assign multicast_bytes_sent_int = 64'd0;
            assign multicast_bytes_received_int = 64'd0;
            assign multicast_remote_write_count_int = 32'd0;
            assign multicast_payload_flits_int = 32'd0;
            assign multicast_wire_flits_int = 32'd0;
            assign multicast_replayed_flits_int = 32'd0;
            assign multicast_retry_events_int = 32'd0;
            assign multicast_credit_stall_cycles_int = 32'd0;
            assign multicast_crc_errors_int = 32'd0;
            assign multicast_sequence_errors_int = 32'd0;
            assign multicast_tree_source = 8'd0;
        end
    endgenerate

    // -- compact operand banks and result memory ------------------------
    wire m0_rd_en, m1_rd_en, m2_rd_en, m3_rd_en;
    wire [31:0] m0_rd_addr, m1_rd_addr, m2_rd_addr, m3_rd_addr;
    reg [31:0] m0_rd_data, m1_rd_data, m2_rd_data, m3_rd_data;
    wire out_we;
    wire [31:0] out_addr;
    wire [31:0] out_data;
    // The engine result boundary.  In injection mode the words come from the
    // golden model; every other signal in this module still comes from RTL.
    wire        res_we = (ENABLE_RESULT_INJECTION != 0) ? inj_write_en : out_we;
    wire [31:0] res_addr =
        (ENABLE_RESULT_INJECTION != 0) ? inj_write_addr : out_addr;
    wire [31:0] res_data =
        (ENABLE_RESULT_INJECTION != 0) ? inj_write_data : out_data;
    wire m0_reads_result;
    wire m1_reads_result;
    wire m1_reads_matmul_weight;
    reg fault_seen;

    // Halfword index into the model image: the operator's 64-bit window base
    // plus the engine port's 32-bit halfword offset, computed at 64 bits.
    wire [63:0] m1_weight_halfword =
        (cfg_matmul_weight_window_base >> 1) + {32'd0, m1_rd_addr};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            m0_rd_data <= 32'd0;
            m1_rd_data <= 32'd0;
            m2_rd_data <= 32'd0;
            m3_rd_data <= 32'd0;
            output_write_count <= 32'd0;
            writes_after_fault <= 32'd0;
            operand_read_oob <= 1'b0;
            result_write_oob <= 1'b0;
            fault_seen <= 1'b0;
            inj_completion_count <= 32'd0;
        end else begin
            if (inj_issue_valid && issue_ready)
                inj_completion_count <= inj_completion_count + 32'd1;
            if (start) begin
                inj_completion_count <= 32'd0;
                output_write_count <= 32'd0;
                writes_after_fault <= 32'd0;
                operand_read_oob <= 1'b0;
                result_write_oob <= 1'b0;
                fault_seen <= 1'b0;
            end
            if (m0_rd_en) begin
                if (m0_reads_result && (m0_rd_addr < RESULT_WORDS))
                    m0_rd_data <= result_mem[m0_rd_addr];
                else if (!m0_reads_result && (m0_rd_addr < INDEX_WORDS))
                    m0_rd_data <= index_mem[m0_rd_addr];
                else begin
                    m0_rd_data <= 32'd0;
                    operand_read_oob <= 1'b1;
                end
            end
            if (m1_rd_en) begin
                if (m1_reads_matmul_weight) begin
                    // 64-bit throughout.  The old form was
                    // `matmul_weight_mem[m1_rd_addr << 1]`, whose shift is
                    // evaluated at the 32-bit width of m1_rd_addr, so every
                    // byte index above 2^32 aliased back into the low 4 GiB
                    // -- silently, with no fault.  The window base is added
                    // in 64 bits so a bounded 32-bit operator offset can
                    // address any row of the checkpoint.
                    if (m1_weight_halfword < (MATMUL_WEIGHT_BYTES >> 1))
                        m1_rd_data <=
                            ot_a3_weight_window_halfword(m1_weight_halfword);
                    else begin
                        m1_rd_data <= 32'd0;
                        operand_read_oob <= 1'b1;
                    end
                end
                else if (m1_reads_result && (m1_rd_addr < RESULT_WORDS))
                    m1_rd_data <= result_mem[m1_rd_addr];
                else if (!m1_reads_result && (m1_rd_addr < SOURCE_WORDS))
                    m1_rd_data <= source_mem[m1_rd_addr];
                else begin
                    m1_rd_data <= 32'd0;
                    operand_read_oob <= 1'b1;
                end
            end
            if (m2_rd_en) begin
                m2_rd_data <= 32'd0;
                // ot_a3_mac_lane drives both scale ports for every reduction
                // step.  This exact Qwen descriptor declares both operands
                // unscaled, so zero is the architectural don't-care responder
                // and no scale-object access took place.
                if (!m1_reads_matmul_weight)
                    operand_read_oob <= 1'b1;
            end
            if (m3_rd_en) begin
                m3_rd_data <= 32'd0;
                if (!m1_reads_matmul_weight)
                    operand_read_oob <= 1'b1;
            end
            if (res_we) begin
                output_write_count <= output_write_count + 32'd1;
                if (res_addr < RESULT_WORDS)
                    result_mem[res_addr] <= res_data;
                else
                    result_write_oob <= 1'b1;
            end
            if (fault_seen &&
                (res_we || (multicast_remote_write_valid &&
                            multicast_remote_write_ready)))
                writes_after_fault <= writes_after_fault +
                    (res_we ? 32'd1 : 32'd0) +
                    ((multicast_remote_write_valid &&
                      multicast_remote_write_ready) ? 32'd1 : 32'd0);
            if (issue_valid && issue_ready && issue_fault)
                fault_seen <= 1'b1;
        end
    end

    assign result_read_data = (result_read_addr < RESULT_WORDS)
        ? result_mem[result_read_addr] : 32'd0;

    wire engine_busy;
    wire [31:0] bridge_real_launch_count;
    assign real_launch_count =
        bridge_real_launch_count + multicast_launch_count_q;
    ot_a3_engine_issue_bridge bridge (
        .clk(clk),
        .rst_n(rst_n),
        .clear(start),
        .issue_valid(issue_valid && !exact_multicast_issue &&
                     (ENABLE_RESULT_INJECTION == 0)),
        .issue_ready(bridge_issue_ready),
        .issue_fault(bridge_issue_fault),
        .issue_trap_class(bridge_issue_trap_class),
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
        .desc_req(bridge_desc_req),
        .desc_id(bridge_desc_id),
        .desc_valid(bridge_desc_valid),
        .desc_fault(bridge_desc_fault),
        .desc_data(bridge_desc_data),
        .cfg_index_base(cfg_index_base),
        .cfg_source_base(cfg_source_base),
        .cfg_source_launch_stride(cfg_source_launch_stride),
        .cfg_embedding_source_base(cfg_embedding_source_base),
        .cfg_rms_input_base(cfg_rms_input_base),
        .cfg_rms_weight_base(cfg_rms_weight_base),
        .cfg_transfer_index_base(cfg_transfer_index_base),
        .cfg_transfer_source_base(cfg_transfer_source_base),
        .cfg_matmul_input_base(cfg_matmul_input_base),
        .cfg_matmul_weight_object_0(cfg_matmul_weight_object_0),
        .cfg_matmul_weight_base_0(cfg_matmul_weight_base_0),
        .cfg_matmul_weight_object_1(cfg_matmul_weight_object_1),
        .cfg_matmul_weight_base_1(cfg_matmul_weight_base_1),
        .cfg_matmul_weight_object_2(cfg_matmul_weight_object_2),
        .cfg_matmul_weight_base_2(cfg_matmul_weight_base_2),
        .cfg_head_input_object_0(cfg_head_input_object_0),
        .cfg_head_input_base_0(cfg_head_input_base_0),
        .cfg_head_input_object_1(cfg_head_input_object_1),
        .cfg_head_input_base_1(cfg_head_input_base_1),
        .cfg_head_weight_object_0(cfg_head_weight_object_0),
        .cfg_head_weight_base_0(cfg_head_weight_base_0),
        .cfg_head_weight_object_1(cfg_head_weight_object_1),
        .cfg_head_weight_base_1(cfg_head_weight_base_1),
        .cfg_rope_input_object_0(cfg_rope_input_object_0),
        .cfg_rope_input_base_0(cfg_rope_input_base_0),
        .cfg_rope_input_object_1(cfg_rope_input_object_1),
        .cfg_rope_input_base_1(cfg_rope_input_base_1),
        .cfg_rope_coefficient_object(cfg_rope_coefficient_object),
        .cfg_rope_coefficient_base(cfg_rope_coefficient_base),
        .cfg_output_base(cfg_output_base),
        .cfg_extended_placement_valid(cfg_extended_placement_valid),
        .cfg_map_object_0(cfg_map_object_0),
        .cfg_map_base_0(cfg_map_base_0),
        .cfg_map_object_1(cfg_map_object_1),
        .cfg_map_base_1(cfg_map_base_1),
        .cfg_map_object_2(cfg_map_object_2),
        .cfg_map_base_2(cfg_map_base_2),
        .cfg_map_object_3(cfg_map_object_3),
        .cfg_map_base_3(cfg_map_base_3),
        .cfg_map_object_4(cfg_map_object_4),
        .cfg_map_base_4(cfg_map_base_4),
        .cfg_map_object_5(cfg_map_object_5),
        .cfg_map_base_5(cfg_map_base_5),
        .cfg_map_object_6(cfg_map_object_6),
        .cfg_map_base_6(cfg_map_base_6),
        .cfg_map_object_7(cfg_map_object_7),
        .cfg_map_base_7(cfg_map_base_7),
        .cfg_context_length(cfg_context_length),
        .cfg_kv_plane_rows(cfg_kv_plane_rows),
        .cfg_generation_policy_id(cfg_generation_policy_id),
        .cfg_request_max_new_tokens(cfg_request_max_new_tokens),
        .cfg_generated_before(cfg_generated_before),
        .m0_rd_en(m0_rd_en),
        .m0_rd_addr(m0_rd_addr),
        .m0_rd_data(m0_rd_data),
        .m1_rd_en(m1_rd_en),
        .m1_rd_addr(m1_rd_addr),
        .m1_rd_data(m1_rd_data),
        .m2_rd_en(m2_rd_en),
        .m2_rd_addr(m2_rd_addr),
        .m2_rd_data(m2_rd_data),
        .m3_rd_en(m3_rd_en),
        .m3_rd_addr(m3_rd_addr),
        .m3_rd_data(m3_rd_data),
        .out_we(out_we),
        .out_addr(out_addr),
        .out_data(out_data),
        .m0_reads_result(m0_reads_result),
        .m1_reads_result(m1_reads_result),
        .m1_reads_matmul_weight(m1_reads_matmul_weight),
        .engine_busy(engine_busy),
        .engine_error_code(engine_error_code),
        .engine_result_count(engine_result_count),
        .engine_work_count(engine_work_count),
        .real_launch_count(bridge_real_launch_count),
        .dma_gather_launch_count(dma_gather_launch_count),
        .embedding_launch_count(embedding_launch_count),
        .rms_norm_launch_count(rms_norm_launch_count),
        .head_rms_norm_launch_count(head_rms_norm_launch_count),
        .rope_launch_count(rope_launch_count),
        .dma_transfer_launch_count(dma_transfer_launch_count),
        .matmul_launch_count(matmul_launch_count),
        .vector_add_launch_count(vector_add_launch_count),
        .vector_silu_mul_launch_count(vector_silu_mul_launch_count),
        .dma_scatter_launch_count(dma_scatter_launch_count),
        .attention_gqa_launch_count(attention_gqa_launch_count),
        .selection_argmax_launch_count(selection_argmax_launch_count),
        .selection_token_append_launch_count(
            selection_token_append_launch_count),
        .selected_token(selected_token),
        .selected_tie_multiplicity(selected_tie_multiplicity),
        .selected_eos_reason(selected_eos_reason),
        .capability_fault_count(capability_fault_count),
        .descriptor_fault_count(descriptor_fault_count),
        .engine_fault_count(engine_fault_count),
        .last_response_index(bridge_last_response_index),
        .last_response_family(bridge_last_response_family),
        .last_response_sub(bridge_last_response_sub),
        .last_response_descriptor_id(bridge_last_response_descriptor_id)
    );
endmodule
