`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DeepSeek-V4-Flash ROM, ABI 3.0 PC 13: exact wafer LINK.MULTICAST adapter.
//
// This block is intentionally narrower than a general LINK implementation.  It
// admits the shipped descriptor 368 only after checking the complete
// COMMUNICATION, TOPOLOGY, two MEMORY_OBJECT, and COUNTER_CLASS records and the
// issue metadata that binds them.  LINK has no tensor-view operands, so zero
// resolved views is an explicit part of admission.  The shipped deployment has
// no STATE descriptors; a nonzero state count is therefore also refused.
//
// Once admitted, one 64-KiB source is read into a local link buffer, copied to
// participant zero, and broadcast over the exact eight-round binomial tree for
// route group zero (256 tiles).  Tree edges are time-multiplexed over the same
// production link endpoint.  The endpoint, wire, and return path provide the
// real packet-local CRC32C, credit, sequence, NAK, and bounded replay behavior.
// There is no operation-level retry and every fault is fail-stop until reset.
//
// This adapter proves descriptor admission, the tree schedule, byte movement,
// packet replay, and architectural counters.  Time multiplexing 255 logical
// edges over one endpoint is a verification construction: its simulator wall
// time and cycle count are NOT wafer timing and MUST NOT be reported as TPOT.
// ---------------------------------------------------------------------------
module ot_a3_wafer_multicast_adapter #(
    parameter integer WIRE_CYCLES = 1,
    parameter integer ACK_TIMEOUT = 512
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,

    // Already-authenticated issue metadata supplied by the program sequencer.
    input  wire [31:0]   issue_pc,
    input  wire [7:0]    issue_major,
    input  wire [7:0]    issue_sub,
    input  wire [31:0]   issue_descriptor_id,
    input  wire [31:0]   observed_view_count,
    input  wire [31:0]   state_descriptor_count,

    // Table indices are sidebands: descriptor IDs are table positions and are
    // not encoded inside descriptor records.
    input  wire [31:0]   topology_descriptor_id,
    input  wire [31:0]   local_object_descriptor_id,
    input  wire [31:0]   remote_object_descriptor_id,
    input  wire [31:0]   counter_descriptor_id,

    input  wire [1535:0] communication_record,
    input  wire [2047:0] topology_record,
    input  wire [1023:0] local_object_record,
    input  wire [1023:0] remote_object_record,
    input  wire [1023:0] counter_record,

    // One-outstanding-read source interface.  A response error is fail-stop.
    output wire          source_read_valid,
    input  wire          source_read_ready,
    output wire [31:0]   source_read_object_id,
    output wire [63:0]   source_read_offset,
    input  wire          source_response_valid,
    output wire          source_response_ready,
    input  wire [31:0]   source_response_data,
    input  wire          source_response_error,

    // Destination writes are committed only on valid && ready.  participant
    // identifies the logical tile whose 64-KiB slot the offset addresses.
    output wire          remote_write_valid,
    input  wire          remote_write_ready,
    output wire [31:0]   remote_write_object_id,
    output wire [15:0]   remote_write_participant,
    output wire [63:0]   remote_write_offset,
    output wire [31:0]   remote_write_data,

    // Arms one corruption in the reused link endpoint.  It is strictly a
    // verification hook and exercises packet-local recovery only.
    input  wire          inject_crc_error,

    output reg           busy,
    output reg           done,
    output reg           failed,
    output reg  [15:0]   trap_class,
    output reg  [7:0]    refusal_reason,

    output reg  [31:0]   messages_sent,
    output reg  [31:0]   messages_received,
    output reg  [63:0]   bytes_sent,
    output reg  [63:0]   bytes_received,
    output reg  [31:0]   remote_write_count,
    output wire [31:0]   payload_flits_delivered,
    output wire [31:0]   wire_flits_transmitted,
    output wire [31:0]   replayed_flits,
    output wire [31:0]   retry_events,
    output wire [31:0]   credit_stall_cycles,
    output wire [31:0]   crc_errors,
    output wire [31:0]   sequence_errors
);
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [15:0] NO_NODE = 16'hffff;
    localparam [15:0] LINK_TRAP = 16'd11;

    localparam [31:0] EXPECTED_PC = 32'd13;
    localparam [7:0]  EXPECTED_MAJOR = 8'h90;
    localparam [7:0]  EXPECTED_SUB = 8'd3;
    localparam [31:0] COMMUNICATION_ID = 32'd368;
    localparam [31:0] TOPOLOGY_ID = 32'd0;
    localparam [31:0] LOCAL_OBJECT_ID = 32'd365;
    localparam [31:0] REMOTE_OBJECT_ID = 32'd366;
    localparam [31:0] COUNTER_ID = 32'd367;

    localparam integer PARTICIPANTS = 256;
    localparam integer PAYLOAD_BYTES = 65536;
    localparam integer PAYLOAD_WORDS = PAYLOAD_BYTES / 4;
    localparam integer TREE_ROUNDS = 8;

    // Refusal reasons are adapter observability, not ABI registry values.
    localparam [7:0] REFUSE_NONE             = 8'd0;
    localparam [7:0] REFUSE_ISSUE_METADATA   = 8'd1;
    localparam [7:0] REFUSE_VIEW_CONTRACT    = 8'd2;
    localparam [7:0] REFUSE_STATE_CONTRACT   = 8'd3;
    localparam [7:0] REFUSE_COMM_RECORD      = 8'd4;
    localparam [7:0] REFUSE_COMM_SEMANTICS   = 8'd5;
    localparam [7:0] REFUSE_TOPOLOGY_RECORD  = 8'd6;
    localparam [7:0] REFUSE_TOPOLOGY         = 8'd7;
    localparam [7:0] REFUSE_LOCAL_RECORD     = 8'd8;
    localparam [7:0] REFUSE_REMOTE_RECORD    = 8'd9;
    localparam [7:0] REFUSE_MEMORY_BINDING   = 8'd10;
    localparam [7:0] REFUSE_COUNTER_RECORD   = 8'd11;
    localparam [7:0] REFUSE_COUNTER_BINDING  = 8'd12;
    localparam [7:0] REFUSE_SOURCE_MEMORY    = 8'd13;
    localparam [7:0] REFUSE_LINK_ENDPOINT    = 8'd14;
    localparam [7:0] REFUSE_FLIT_METADATA    = 8'd15;
    localparam [7:0] REFUSE_REENTRY          = 8'd16;

    // The existing decoder owns the complete 192-byte COMMUNICATION structural
    // contract and CRC.  Its standalone mesh command_admitted output is not
    // used: that output deliberately supports NODE scope only, while this
    // adapter resolves the admitted wafer TOPOLOGY and TILE scope below.
    wire comm_record_valid;
    wire [31:0] comm_flags;
    wire [31:0] comm_primary_object_id;
    wire [31:0] comm_secondary_object_id;
    wire [31:0] comm_numeric_profile_id;
    wire [31:0] comm_schedule_id;
    wire [31:0] comm_permissions;
    wire [31:0] comm_owner_scope_id;
    wire [7:0]  comm_collective_op;
    wire [7:0]  comm_ordering;
    wire [7:0]  comm_integrity_mode;
    wire [7:0]  comm_virtual_channel;
    wire [15:0] comm_source_node;
    wire [15:0] comm_destination_node;
    wire [31:0] comm_group_id;
    wire [31:0] comm_route_class;
    wire [31:0] comm_local_object_id;
    wire [31:0] comm_remote_object_id;
    wire [63:0] comm_local_offset;
    wire [63:0] comm_remote_offset;
    wire [63:0] comm_byte_extent;
    wire [31:0] comm_credit_bound;
    wire [31:0] comm_retry_bound;
    wire [31:0] comm_timeout_class;
    wire [31:0] comm_completion_event_id;
    wire [31:0] comm_reduction_numeric_id;
    wire [31:0] comm_counter_class_id;
    wire [31:0] comm_participant_count;
    wire [31:0] comm_chunk_bytes;
    wire [7:0]  comm_participant_scope;

    ot_a3_communication_decoder #(
        .MESH_X(16), .MESH_Y(16), .VEC_LEN(256),
        .CREDITS(8), .RETRY_MAX(3), .TIMEOUT_CLASS(1)
    ) u_communication_decoder (
        .descriptor_record(communication_record),
        .numeric_descriptor_record(1024'd0),
        .instruction_subopcode(issue_sub),
        .algorithm(2'd0),
        .numeric_descriptor_id(NO_ID),
        .numeric_reduction_order(8'd0),
        .record_valid(comm_record_valid),
        .flags(comm_flags),
        .primary_object_id(comm_primary_object_id),
        .secondary_object_id(comm_secondary_object_id),
        .numeric_profile_id(comm_numeric_profile_id),
        .schedule_id(comm_schedule_id),
        .permissions(comm_permissions),
        .owner_scope_id(comm_owner_scope_id),
        .collective_op(comm_collective_op),
        .ordering(comm_ordering),
        .integrity_mode(comm_integrity_mode),
        .virtual_channel(comm_virtual_channel),
        .source_node(comm_source_node),
        .destination_node(comm_destination_node),
        .group_id(comm_group_id),
        .route_class(comm_route_class),
        .local_object_id(comm_local_object_id),
        .remote_object_id(comm_remote_object_id),
        .local_offset(comm_local_offset),
        .remote_offset(comm_remote_offset),
        .byte_extent(comm_byte_extent),
        .credit_bound(comm_credit_bound),
        .retry_bound(comm_retry_bound),
        .timeout_class(comm_timeout_class),
        .completion_event_id(comm_completion_event_id),
        .reduction_numeric_id(comm_reduction_numeric_id),
        .counter_class_id(comm_counter_class_id),
        .participant_count(comm_participant_count),
        .chunk_bytes(comm_chunk_bytes),
        .participant_scope(comm_participant_scope)
    );

    // Complete-record CRCs.  CRC is transport integrity; the upstream
    // deployment admission remains responsible for signature/authentication.
    wire [2047:0] topology_crc_image = {
        topology_record[2047:416], 32'd0, topology_record[383:0]
    };
    wire [1023:0] local_crc_image = {
        local_object_record[1023:416], 32'd0, local_object_record[383:0]
    };
    wire [1023:0] remote_crc_image = {
        remote_object_record[1023:416], 32'd0, remote_object_record[383:0]
    };
    wire [1023:0] counter_crc_image = {
        counter_record[1023:416], 32'd0, counter_record[383:0]
    };
    //: FOUR CRCs IN A TREE, not four chains.  ot_crc_pkg::crc32c states the
    //: reflected Castagnoli algorithm one bit at a time, so these four calls unroll
    //: into 2,048 + 1,024 + 1,024 + 1,024 = 5,120 sequential steps in one module.
    //: That is why this block has never been routed: its yosys step ran three hours
    //: in EXTRACT_FA at 101% CPU and 37.8 GB without writing a line of log, and was
    //: killed rather than finished.  ot_crc32c_tree_pkg computes the same function
    //: as 32 balanced XOR reductions per CRC -- eleven levels for 2,048 bits, ten
    //: for 1,024 -- and rtl/test/tb_crc32c_tree_equiv.sv proves the two forms equal
    //: over 512 comparisons at exactly these widths.
    wire [31:0] topology_crc = ot_crc32c_tree_pkg::crc32c_2048(topology_crc_image);
    wire [31:0] local_crc    = ot_crc32c_tree_pkg::crc32c_1024(local_crc_image);
    wire [31:0] remote_crc   = ot_crc32c_tree_pkg::crc32c_1024(remote_crc_image);
    wire [31:0] counter_crc  = ot_crc32c_tree_pkg::crc32c_1024(counter_crc_image);

    wire topology_record_valid =
        (topology_record[31:0] == 32'h4433_4154) &&
        (topology_record[47:32] == 16'h0005) &&
        (topology_record[55:48] == 8'd1) &&
        (topology_record[63:56] == 8'd0) &&
        (topology_record[95:64] == 32'd256) &&
        (topology_record[127:96] == 32'd0) &&
        (topology_record[255:128] == {4{NO_ID}}) &&
        (topology_record[287:256] == 32'd129) &&
        (topology_record[319:288] == 32'd0) &&
        (topology_record[351:320] == 32'd64) &&
        (topology_record[383:352] == 32'd192) &&
        (topology_record[415:384] == topology_crc) &&
        (topology_record[511:416] == 96'd0) &&
        (topology_record[527:520] == 8'd0) &&
        (topology_record[1023:960] == 64'd0);

    wire topology_semantics_valid =
        (topology_descriptor_id == TOPOLOGY_ID) &&
        (topology_record[519:512] ==
         ot_a3_link_pkg::TOPOLOGY_WAFER_LOGICAL_DEVICE) &&
        (topology_record[543:528] == 16'd1) &&
        (topology_record[559:544] == 16'd37) &&
        (topology_record[575:560] == 16'd256) &&
        (topology_record[591:576] == 16'd0) &&
        (topology_record[607:592] == 16'd0) &&
        (topology_record[623:608] == 16'd0) &&
        (topology_record[639:624] == 16'd3) &&
        (topology_record[671:640] == 32'd9300) &&
        (topology_record[703:672] == 32'd0) &&
        (topology_record[767:704] == 64'd1649267441664) &&
        (topology_record[831:768] == 64'd8589934592) &&
        (topology_record[863:832] == 32'd19072) &&
        (topology_record[895:864] == 32'd37) &&
        (topology_record[927:896] == 32'd1) &&
        (topology_record[959:928] == 32'd96) &&
        (topology_record[1279:1024] != 256'd0) &&
        (topology_record[1535:1280] != 256'd0) &&
        (topology_record[1791:1536] != 256'd0) &&
        (topology_record[2047:1792] != 256'd0);

    function automatic memory_record_valid;
        input [1023:0] record;
        input [31:0] calculated_crc;
        begin
            memory_record_valid =
                (record[31:0] == 32'h4433_4154) &&
                (record[47:32] == 16'h0001) &&
                (record[55:48] == 8'd1) &&
                (record[63:56] == 8'd0) &&
                (record[95:64] == 32'd128) &&
                (record[127:96] == 32'd0) &&
                (record[255:128] == {4{NO_ID}}) &&
                (record[319:288] == 32'd0) &&
                (record[351:320] == 32'd64) &&
                (record[383:352] == 32'd64) &&
                (record[415:384] == calculated_crc) &&
                (record[511:416] == 96'd0) &&
                (record[543:536] == 8'd0) &&
                (record[767:736] == 32'd0);
        end
    endfunction

    wire local_record_valid = memory_record_valid(local_object_record, local_crc);
    wire remote_record_valid = memory_record_valid(remote_object_record, remote_crc);

    wire memory_semantics_valid =
        (local_object_descriptor_id == LOCAL_OBJECT_ID) &&
        (remote_object_descriptor_id == REMOTE_OBJECT_ID) &&
        (local_object_record[287:256] == 32'd3) &&
        (remote_object_record[287:256] == 32'd35) &&
        (local_object_record[519:512] == 8'd1) &&
        (remote_object_record[519:512] == 8'd1) &&
        (local_object_record[527:520] == 8'd1) &&
        (remote_object_record[527:520] == 8'd1) &&
        (local_object_record[535:528] == 8'd6) &&
        (remote_object_record[535:528] == 8'd6) &&
        (local_object_record[559:544] == NO_NODE) &&
        (remote_object_record[559:544] == NO_NODE) &&
        (local_object_record[575:560] == NO_NODE) &&
        (remote_object_record[575:560] == NO_NODE) &&
        (local_object_record[639:576] == 64'd0) &&
        (remote_object_record[639:576] == 64'd0) &&
        (local_object_record[703:640] == 64'd16777216) &&
        (remote_object_record[703:640] == 64'd16777216) &&
        (local_object_record[735:704] == NO_ID) &&
        (remote_object_record[735:704] == NO_ID) &&
        (local_object_record[1023:768] == 256'd0) &&
        (remote_object_record[1023:768] == 256'd0);

    wire counter_record_valid =
        (counter_record[31:0] == 32'h4433_4154) &&
        (counter_record[47:32] == 16'h000c) &&
        (counter_record[55:48] == 8'd1) &&
        (counter_record[63:56] == 8'd0) &&
        (counter_record[95:64] == 32'd128) &&
        (counter_record[127:96] == 32'd0) &&
        (counter_record[255:128] == {4{NO_ID}}) &&
        (counter_record[287:256] == 32'd129) &&
        (counter_record[319:288] == 32'd0) &&
        (counter_record[351:320] == 32'd64) &&
        (counter_record[383:352] == 32'd64) &&
        (counter_record[415:384] == counter_crc) &&
        (counter_record[511:416] == 96'd0) &&
        (counter_record[575:528] == 48'd0) &&
        (counter_record[1023:960] == 64'd0);

    wire counter_semantics_valid =
        (counter_descriptor_id == COUNTER_ID) &&
        (counter_record[519:512] == 8'd10) &&
        (counter_record[527:520] == 8'd3) &&
        (counter_record[607:576] == 32'h0a00_0001) &&
        (counter_record[639:608] == 32'h0a00_0002) &&
        (counter_record[671:640] == 32'h0a00_0003) &&
        (counter_record[959:672] == {9{NO_ID}});

    wire issue_metadata_valid =
        (issue_pc == EXPECTED_PC) &&
        (issue_major == EXPECTED_MAJOR) &&
        (issue_sub == EXPECTED_SUB) &&
        (issue_descriptor_id == COMMUNICATION_ID);

    wire communication_semantics_valid =
        (comm_flags == 32'd0) &&
        (comm_primary_object_id == LOCAL_OBJECT_ID) &&
        (comm_secondary_object_id == REMOTE_OBJECT_ID) &&
        (comm_numeric_profile_id == NO_ID) &&
        (comm_schedule_id == NO_ID) &&
        (comm_permissions == 32'd35) &&
        (comm_owner_scope_id == 32'd0) &&
        (comm_collective_op == ot_a3_link_pkg::COLL_BROADCAST) &&
        (comm_ordering == ot_a3_link_pkg::ORDERING_RELEASE) &&
        (comm_integrity_mode == ot_a3_link_pkg::INTEGRITY_CRC32C) &&
        (comm_virtual_channel == 8'd0) &&
        (comm_source_node == 16'd0) &&
        (comm_destination_node == 16'd0) &&
        (comm_group_id == 32'd0) &&
        (comm_route_class == 32'd0) &&
        (comm_local_object_id == LOCAL_OBJECT_ID) &&
        (comm_remote_object_id == REMOTE_OBJECT_ID) &&
        (comm_local_offset == 64'd0) &&
        (comm_remote_offset == 64'd0) &&
        (comm_byte_extent == PAYLOAD_BYTES) &&
        (comm_credit_bound == 32'd8) &&
        (comm_retry_bound == 32'd3) &&
        (comm_timeout_class == 32'd1) &&
        (comm_completion_event_id == NO_ID) &&
        (comm_reduction_numeric_id == NO_ID) &&
        (comm_counter_class_id == COUNTER_ID) &&
        (comm_participant_count == PARTICIPANTS) &&
        (comm_chunk_bytes == 32'd4096) &&
        (comm_participant_scope == ot_a3_link_pkg::PARTICIPANT_TILE);

    reg [7:0] admission_reason;
    always @* begin
        if (!issue_metadata_valid)
            admission_reason = REFUSE_ISSUE_METADATA;
        else if (observed_view_count != 32'd0)
            admission_reason = REFUSE_VIEW_CONTRACT;
        else if (state_descriptor_count != 32'd0)
            admission_reason = REFUSE_STATE_CONTRACT;
        else if (!comm_record_valid)
            admission_reason = REFUSE_COMM_RECORD;
        else if (!communication_semantics_valid)
            admission_reason = REFUSE_COMM_SEMANTICS;
        else if (!topology_record_valid)
            admission_reason = REFUSE_TOPOLOGY_RECORD;
        else if (!topology_semantics_valid)
            admission_reason = REFUSE_TOPOLOGY;
        else if (!local_record_valid)
            admission_reason = REFUSE_LOCAL_RECORD;
        else if (!remote_record_valid)
            admission_reason = REFUSE_REMOTE_RECORD;
        else if (!memory_semantics_valid)
            admission_reason = REFUSE_MEMORY_BINDING;
        else if (!counter_record_valid)
            admission_reason = REFUSE_COUNTER_RECORD;
        else if (!counter_semantics_valid)
            admission_reason = REFUSE_COUNTER_BINDING;
        else
            admission_reason = REFUSE_NONE;
    end

    // ------------------------------------------------------------------
    // One physical endpoint, time-multiplexed over the 255 binomial-tree edges.
    // ------------------------------------------------------------------
    reg [31:0] link_buffer [0:PAYLOAD_WORDS-1];
    reg [13:0] source_word_index;
    reg [13:0] root_word_index;
    // One extra bit is required for the PAYLOAD_WORDS sentinel.  Using only
    // the 14 address bits would wrap 16,383 -> 0 and enqueue duplicate flits
    // while the final receive drains.
    reg [14:0] send_word_index;
    reg [13:0] receive_word_index;
    reg [2:0]  tree_round;
    reg [7:0]  tree_edge;

    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_READ_REQ   = 4'd1;
    localparam [3:0] S_READ_RSP   = 4'd2;
    localparam [3:0] S_ROOT_COPY  = 4'd3;
    localparam [3:0] S_NETWORK    = 4'd4;
    localparam [3:0] S_EDGE_RESET = 4'd5;
    localparam [3:0] S_FINISH     = 4'd6;
    localparam [3:0] S_FAILED     = 4'd7;
    reg [3:0] state;
    reg finish_after_reset;

    wire [8:0] edges_this_round = 9'd1 << tree_round;
    wire [8:0] tree_destination_wide = edges_this_round + {1'b0, tree_edge};
    wire [7:0] tree_source = tree_edge;
    wire [7:0] tree_destination = tree_destination_wide[7:0];

    wire tx_in_valid;
    wire tx_in_ready;
    wire [63:0] tx_in_flit;
    wire tx_w_valid;
    wire [63:0] tx_w_flit;
    wire [7:0] tx_w_seq;
    wire [31:0] tx_w_crc;
    wire rx_w_valid;
    wire [63:0] rx_w_flit;
    wire [7:0] rx_w_seq;
    wire [31:0] rx_w_crc;
    wire endpoint_ack;
    wire [7:0] endpoint_ack_seq;
    wire [1:0] endpoint_credit;
    wire endpoint_nak;
    wire [7:0] endpoint_nak_seq;
    wire tx_ack;
    wire [7:0] tx_ack_seq;
    wire [1:0] tx_credit;
    wire tx_nak;
    wire [7:0] tx_nak_seq;
    wire rx_out_valid;
    wire [63:0] rx_out_flit;
    wire rx_out_ready;
    wire endpoint_timeout;
    wire endpoint_error;
    wire [31:0] endpoint_flits_transmitted;
    wire [31:0] endpoint_replayed_flits;
    wire [31:0] endpoint_retry_events;
    wire [31:0] endpoint_credit_stalls;
    wire [31:0] endpoint_crc_errors;
    wire [31:0] endpoint_sequence_errors;
    wire [31:0] endpoint_flits_delivered;

    assign tx_in_valid = (state == S_NETWORK) && busy && !failed &&
                         (send_word_index < PAYLOAD_WORDS);
    assign tx_in_flit = ot_a3_link_pkg::flit_pack(
        link_buffer[send_word_index[13:0]],
        tree_destination[3:0], tree_destination[7:4],
        tree_source[3:0], tree_source[7:4],
        ot_a3_link_pkg::KIND_GATHER,
        {5'd0, tree_round});

    // Each scheduled edge is a distinct physical source/destination endpoint
    // pair on the spatial wafer.  Since this focused implementation reuses one
    // endpoint in time, its protocol state is reset between logical edges; not
    // doing so would incorrectly carry one physical link's replay window into
    // another physical link.
    wire endpoint_rst_n = rst_n && (state != S_EDGE_RESET);

    ot_a3_link_endpoint #(
        .FLIT_W(64), .CREDITS(8), .RETRY_MAX(3),
        .ACK_TIMEOUT(ACK_TIMEOUT)
    ) u_link_endpoint (
        .clk(clk), .rst_n(endpoint_rst_n),
        .tx_in_valid(tx_in_valid), .tx_in_ready(tx_in_ready),
        .tx_in_flit(tx_in_flit),
        .tx_w_valid(tx_w_valid), .tx_w_flit(tx_w_flit),
        .tx_w_seq(tx_w_seq), .tx_w_crc(tx_w_crc),
        .tx_r_ack(tx_ack), .tx_r_ack_seq(tx_ack_seq),
        .tx_r_credit(tx_credit), .tx_r_nak(tx_nak),
        .tx_r_nak_seq(tx_nak_seq),
        .rx_w_valid(rx_w_valid), .rx_w_flit(rx_w_flit),
        .rx_w_seq(rx_w_seq), .rx_w_crc(rx_w_crc),
        .rx_r_ack(endpoint_ack), .rx_r_ack_seq(endpoint_ack_seq),
        .rx_r_credit(endpoint_credit), .rx_r_nak(endpoint_nak),
        .rx_r_nak_seq(endpoint_nak_seq),
        .rx_out_valid(rx_out_valid), .rx_out_flit(rx_out_flit),
        .rx_out_ready(rx_out_ready),
        .inject_crc_error(inject_crc_error),
        .flits_transmitted(endpoint_flits_transmitted),
        .replayed_flits(endpoint_replayed_flits),
        .retry_events(endpoint_retry_events),
        .credit_stall_cycles(endpoint_credit_stalls),
        .crc_errors(endpoint_crc_errors),
        .sequence_errors(endpoint_sequence_errors),
        .flits_delivered(endpoint_flits_delivered),
        .timeout(endpoint_timeout), .error(endpoint_error)
    );

    ot_a3_link_wire #(.FLIT_W(64), .CYCLES(WIRE_CYCLES)) u_forward_wire (
        .clk(clk), .rst_n(endpoint_rst_n),
        .in_valid(tx_w_valid), .in_flit(tx_w_flit),
        .in_seq(tx_w_seq), .in_crc(tx_w_crc),
        .out_valid(rx_w_valid), .out_flit(rx_w_flit),
        .out_seq(rx_w_seq), .out_crc(rx_w_crc)
    );

    ot_a3_link_return #(.CYCLES(WIRE_CYCLES)) u_return_wire (
        .clk(clk), .rst_n(endpoint_rst_n),
        .in_ack(endpoint_ack), .in_ack_seq(endpoint_ack_seq),
        .in_credit(endpoint_credit), .in_nak(endpoint_nak),
        .in_nak_seq(endpoint_nak_seq),
        .out_ack(tx_ack), .out_ack_seq(tx_ack_seq),
        .out_credit(tx_credit), .out_nak(tx_nak),
        .out_nak_seq(tx_nak_seq)
    );

    wire received_flit_metadata_valid =
        (rx_out_flit[63:60] == 4'd0) &&
        (ot_a3_link_pkg::flit_src_x(rx_out_flit) == tree_source[3:0]) &&
        (ot_a3_link_pkg::flit_src_y(rx_out_flit) == tree_source[7:4]) &&
        (ot_a3_link_pkg::flit_dest_x(rx_out_flit) == tree_destination[3:0]) &&
        (ot_a3_link_pkg::flit_dest_y(rx_out_flit) == tree_destination[7:4]) &&
        (ot_a3_link_pkg::flit_kind(rx_out_flit) ==
         ot_a3_link_pkg::KIND_GATHER) &&
        (ot_a3_link_pkg::flit_tag(rx_out_flit) == {5'd0, tree_round});

    assign source_read_valid = (state == S_READ_REQ) && busy && !failed;
    assign source_read_object_id = LOCAL_OBJECT_ID;
    assign source_read_offset = {48'd0, source_word_index, 2'b00};
    assign source_response_ready = (state == S_READ_RSP) && busy && !failed;

    wire root_write = (state == S_ROOT_COPY) && busy && !failed;
    wire network_write = (state == S_NETWORK) && busy && !failed &&
                         rx_out_valid && received_flit_metadata_valid;
    assign remote_write_valid = root_write || network_write;
    assign remote_write_object_id = REMOTE_OBJECT_ID;
    assign remote_write_participant = root_write
        ? 16'd0 : {8'd0, tree_destination};
    assign remote_write_offset = root_write
        ? {48'd0, root_word_index, 2'b00}
        : ({48'd0, tree_destination} * PAYLOAD_BYTES) +
          {48'd0, receive_word_index, 2'b00};
    assign remote_write_data = root_write
        ? link_buffer[root_word_index]
        : ot_a3_link_pkg::flit_payload(rx_out_flit);
    assign rx_out_ready = (state == S_NETWORK) && busy && !failed &&
                          received_flit_metadata_valid && remote_write_ready;

    reg [31:0] accumulated_flits_transmitted;
    reg [31:0] accumulated_replayed_flits;
    reg [31:0] accumulated_retry_events;
    reg [31:0] accumulated_credit_stalls;
    reg [31:0] accumulated_crc_errors;
    reg [31:0] accumulated_sequence_errors;
    reg [31:0] accumulated_flits_delivered;

    wire endpoint_is_reset = (state == S_EDGE_RESET);
    assign payload_flits_delivered = accumulated_flits_delivered +
        (endpoint_is_reset ? 32'd0 : endpoint_flits_delivered);
    assign wire_flits_transmitted = accumulated_flits_transmitted +
        (endpoint_is_reset ? 32'd0 : endpoint_flits_transmitted);
    assign replayed_flits = accumulated_replayed_flits +
        (endpoint_is_reset ? 32'd0 : endpoint_replayed_flits);
    assign retry_events = accumulated_retry_events +
        (endpoint_is_reset ? 32'd0 : endpoint_retry_events);
    assign credit_stall_cycles = accumulated_credit_stalls +
        (endpoint_is_reset ? 32'd0 : endpoint_credit_stalls);
    assign crc_errors = accumulated_crc_errors +
        (endpoint_is_reset ? 32'd0 : endpoint_crc_errors);
    assign sequence_errors = accumulated_sequence_errors +
        (endpoint_is_reset ? 32'd0 : endpoint_sequence_errors);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            failed <= 1'b0;
            trap_class <= 16'd0;
            refusal_reason <= REFUSE_NONE;
            source_word_index <= 14'd0;
            root_word_index <= 14'd0;
            send_word_index <= 15'd0;
            receive_word_index <= 14'd0;
            tree_round <= 3'd0;
            tree_edge <= 8'd0;
            finish_after_reset <= 1'b0;
            messages_sent <= 32'd0;
            messages_received <= 32'd0;
            bytes_sent <= 64'd0;
            bytes_received <= 64'd0;
            remote_write_count <= 32'd0;
            accumulated_flits_transmitted <= 32'd0;
            accumulated_replayed_flits <= 32'd0;
            accumulated_retry_events <= 32'd0;
            accumulated_credit_stalls <= 32'd0;
            accumulated_crc_errors <= 32'd0;
            accumulated_sequence_errors <= 32'd0;
            accumulated_flits_delivered <= 32'd0;
        end else begin
            done <= 1'b0;

            // A second issue while this command is in flight is an internal
            // sequencing violation.  Like every other failure it suppresses
            // all subsequent memory side effects until reset.
            if (start && busy) begin
                state <= S_FAILED;
                busy <= 1'b0;
                failed <= 1'b1;
                trap_class <= LINK_TRAP;
                refusal_reason <= REFUSE_REENTRY;
            end else if (busy && endpoint_error) begin
                state <= S_FAILED;
                busy <= 1'b0;
                failed <= 1'b1;
                trap_class <= LINK_TRAP;
                refusal_reason <= REFUSE_LINK_ENDPOINT;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (start && !failed) begin
                            if (admission_reason != REFUSE_NONE) begin
                                state <= S_FAILED;
                                failed <= 1'b1;
                                trap_class <= LINK_TRAP;
                                refusal_reason <= admission_reason;
                            end else begin
                                state <= S_READ_REQ;
                                busy <= 1'b1;
                                trap_class <= 16'd0;
                                refusal_reason <= REFUSE_NONE;
                                source_word_index <= 14'd0;
                                root_word_index <= 14'd0;
                                send_word_index <= 15'd0;
                                receive_word_index <= 14'd0;
                                tree_round <= 3'd0;
                                tree_edge <= 8'd0;
                                finish_after_reset <= 1'b0;
                                messages_sent <= 32'd0;
                                messages_received <= 32'd0;
                                bytes_sent <= 64'd0;
                                bytes_received <= 64'd0;
                                remote_write_count <= 32'd0;
                                accumulated_flits_transmitted <= 32'd0;
                                accumulated_replayed_flits <= 32'd0;
                                accumulated_retry_events <= 32'd0;
                                accumulated_credit_stalls <= 32'd0;
                                accumulated_crc_errors <= 32'd0;
                                accumulated_sequence_errors <= 32'd0;
                                accumulated_flits_delivered <= 32'd0;
                            end
                        end
                    end

                    S_READ_REQ: begin
                        if (source_read_valid && source_read_ready)
                            state <= S_READ_RSP;
                    end

                    S_READ_RSP: begin
                        if (source_response_valid && source_response_ready) begin
                            if (source_response_error) begin
                                state <= S_FAILED;
                                busy <= 1'b0;
                                failed <= 1'b1;
                                trap_class <= LINK_TRAP;
                                refusal_reason <= REFUSE_SOURCE_MEMORY;
                            end else begin
                                link_buffer[source_word_index] <=
                                    source_response_data;
                                if (source_word_index == PAYLOAD_WORDS-1) begin
                                    root_word_index <= 14'd0;
                                    state <= S_ROOT_COPY;
                                end else begin
                                    source_word_index <= source_word_index + 1'b1;
                                    state <= S_READ_REQ;
                                end
                            end
                        end
                    end

                    S_ROOT_COPY: begin
                        if (remote_write_valid && remote_write_ready) begin
                            remote_write_count <= remote_write_count + 32'd1;
                            if (root_word_index == PAYLOAD_WORDS-1) begin
                                tree_round <= 3'd0;
                                tree_edge <= 8'd0;
                                send_word_index <= 15'd0;
                                receive_word_index <= 14'd0;
                                state <= S_NETWORK;
                            end else begin
                                root_word_index <= root_word_index + 1'b1;
                            end
                        end
                    end

                    S_NETWORK: begin
                        if (tx_in_valid && tx_in_ready)
                            send_word_index <= send_word_index + 1'b1;

                        if (rx_out_valid && !received_flit_metadata_valid) begin
`ifndef SYNTHESIS
                            $display("A3_WAFER_MULTICAST_METADATA_FAULT round=%0d edge=%0d src=%0d dst=%0d send=%0d recv=%0d flit=%h",
                                     tree_round, tree_edge, tree_source,
                                     tree_destination, send_word_index,
                                     receive_word_index, rx_out_flit);
`endif
                            state <= S_FAILED;
                            busy <= 1'b0;
                            failed <= 1'b1;
                            trap_class <= LINK_TRAP;
                            refusal_reason <= REFUSE_FLIT_METADATA;
                        end else if (remote_write_valid && remote_write_ready) begin
                            remote_write_count <= remote_write_count + 32'd1;
                            if (receive_word_index == PAYLOAD_WORDS-1) begin
                                messages_sent <= messages_sent + 32'd1;
                                messages_received <= messages_received + 32'd1;
                                bytes_sent <= bytes_sent + PAYLOAD_BYTES;
                                bytes_received <= bytes_received + PAYLOAD_BYTES;
                                // The receive channel increments its delivered
                                // counter on this same edge, so include the
                                // just-accepted final word explicitly before
                                // resetting this logical edge's endpoint.
                                accumulated_flits_transmitted <=
                                    accumulated_flits_transmitted +
                                    endpoint_flits_transmitted;
                                accumulated_replayed_flits <=
                                    accumulated_replayed_flits +
                                    endpoint_replayed_flits;
                                accumulated_retry_events <=
                                    accumulated_retry_events +
                                    endpoint_retry_events;
                                accumulated_credit_stalls <=
                                    accumulated_credit_stalls +
                                    endpoint_credit_stalls;
                                accumulated_crc_errors <=
                                    accumulated_crc_errors +
                                    endpoint_crc_errors;
                                accumulated_sequence_errors <=
                                    accumulated_sequence_errors +
                                    endpoint_sequence_errors;
                                accumulated_flits_delivered <=
                                    accumulated_flits_delivered +
                                    endpoint_flits_delivered + 32'd1;
                                send_word_index <= 15'd0;
                                receive_word_index <= 14'd0;
                                if ((tree_round == TREE_ROUNDS-1) &&
                                    ({1'b0, tree_edge} + 9'd1 ==
                                     edges_this_round)) begin
                                    finish_after_reset <= 1'b1;
                                end else if ({1'b0, tree_edge} + 9'd1 ==
                                             edges_this_round) begin
                                    tree_round <= tree_round + 1'b1;
                                    tree_edge <= 8'd0;
                                    finish_after_reset <= 1'b0;
                                end else begin
                                    tree_edge <= tree_edge + 1'b1;
                                    finish_after_reset <= 1'b0;
                                end
                                state <= S_EDGE_RESET;
                            end else begin
                                receive_word_index <= receive_word_index + 1'b1;
                            end
                        end
                    end

                    S_EDGE_RESET: begin
                        // endpoint_rst_n is low throughout this state.  At the
                        // next edge the reused instance therefore starts with
                        // exactly the state of the distinct spatial endpoint
                        // that it represents.
                        if (finish_after_reset)
                            state <= S_FINISH;
                        else
                            state <= S_NETWORK;
                    end

                    S_FINISH: begin
                        // RELEASE completion is observed only after the final
                        // destination write has been accepted.
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= S_IDLE;
                    end

                    S_FAILED: begin
                        // Sticky fail-stop state.  Only rst_n may make this
                        // adapter issue another read, write, or link packet.
                        busy <= 1'b0;
                    end

                    default: begin
                        state <= S_FAILED;
                        busy <= 1'b0;
                        failed <= 1'b1;
                        trap_class <= LINK_TRAP;
                        refusal_reason <= REFUSE_LINK_ENDPOINT;
                    end
                endcase
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (WIRE_CYCLES < 1)
            $error("ot_a3_wafer_multicast_adapter requires a registered wire");
        if (ACK_TIMEOUT < 8)
            $error("ot_a3_wafer_multicast_adapter ACK_TIMEOUT is too small");
    end
`endif
endmodule
