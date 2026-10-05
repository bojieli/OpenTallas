`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// A MESH_X x MESH_Y mesh of ABI 3.0 link nodes, wired nearest-neighbour with no
// switch, which is the fabric `docs/METHODOLOGY.md` section 6 prices a stitched
// wafer collective on.
//
// Everything observable is aggregated here so that both simulators read the
// same numbers: total wire flits, total Manhattan hop-distance offered,
// retries, CRC errors, credit stalls, and the slowest node's busy cycles (a
// collective is finished when its slowest participant is).
//
// `HOP_CYCLES` is the declared wire occupancy of one hop.  It is a parameter of
// this experiment; nothing in this file measures it.
// ---------------------------------------------------------------------------
module a3_link_mesh_top #(
    parameter integer FLIT_W      = 64,
    parameter integer MESH_X      = 4,
    parameter integer MESH_Y      = 4,
    parameter integer VEC_LEN     = 16,
    parameter integer CREDITS     = 8,
    parameter integer RETRY_MAX   = 3,
    parameter integer TIMEOUT_CLASS = 1,
    parameter integer ACK_TIMEOUT = 512,
    parameter integer HOP_CYCLES  = 1
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    input  wire [1535:0] communication_descriptor,
    input  wire [1023:0] numeric_descriptor,
    input  wire [7:0]  instruction_subopcode,
    input  wire [1:0]  alg,
    input  wire [31:0] numeric_descriptor_id,
    input  wire [7:0]  numeric_reduction_order,

    output wire        descriptor_valid,
    output wire        numeric_descriptor_valid,
    output wire        numeric_semantics_supported,
    output wire [7:0]  numeric_refusal_reason,
    output wire        command_admitted,
    output wire [7:0]  refusal_reason,
    output wire [31:0] decoded_magic,
    output wire [15:0] decoded_descriptor_type,
    output wire [7:0]  decoded_type_major,
    output wire [7:0]  decoded_type_minor,
    output wire [31:0] decoded_total_bytes,
    output wire [31:0] decoded_flags,
    output wire [31:0] decoded_primary_object_id,
    output wire [31:0] decoded_secondary_object_id,
    output wire [31:0] decoded_numeric_profile_id,
    output wire [31:0] decoded_schedule_id,
    output wire [31:0] decoded_permissions,
    output wire [31:0] decoded_owner_scope_id,
    output wire [31:0] decoded_payload_offset,
    output wire [31:0] decoded_payload_bytes,
    output wire [31:0] decoded_supplied_crc,
    output wire [31:0] decoded_calculated_crc,
    output wire [7:0]  decoded_collective_op,
    output wire [7:0]  decoded_ordering,
    output wire [7:0]  decoded_integrity_mode,
    output wire [7:0]  decoded_virtual_channel,
    output wire [15:0] decoded_source_node,
    output wire [15:0] decoded_destination_node,
    output wire [31:0] decoded_group_id,
    output wire [31:0] decoded_route_class,
    output wire [31:0] decoded_local_object_id,
    output wire [31:0] decoded_remote_object_id,
    output wire [63:0] decoded_local_offset,
    output wire [63:0] decoded_remote_offset,
    output wire [63:0] decoded_byte_extent,
    output wire [31:0] decoded_credit_bound,
    output wire [31:0] decoded_retry_bound,
    output wire [31:0] decoded_timeout_class,
    output wire [31:0] decoded_completion_event_id,
    output wire [31:0] decoded_reduction_numeric_id,
    output wire [31:0] decoded_counter_class_id,
    output wire [31:0] decoded_participant_count,
    output wire [31:0] decoded_chunk_bytes,
    output wire [7:0]  decoded_participant_scope,
    output wire [15:0] decoded_numeric_descriptor_type,
    output wire [31:0] decoded_numeric_total_bytes,
    output wire [31:0] decoded_numeric_payload_bytes,
    output wire [31:0] decoded_numeric_supplied_crc,
    output wire [31:0] decoded_numeric_calculated_crc,
    output wire [7:0]  decoded_numeric_input_dtype,
    output wire [7:0]  decoded_numeric_second_input_dtype,
    output wire [7:0]  decoded_numeric_accumulator_dtype,
    output wire [7:0]  decoded_numeric_output_dtype,
    output wire [7:0]  decoded_numeric_rounding_mode,
    output wire [7:0]  decoded_numeric_reduction_order,
    output wire [7:0]  decoded_numeric_saturate,
    output wire [7:0]  decoded_numeric_nan_policy,
    output wire [31:0] decoded_numeric_epsilon_bits,
    output wire [31:0] decoded_numeric_scale_bits,
    output wire [31:0] decoded_numeric_flags,
    output wire        decoded_numeric_contract_digest_zero,
    output wire [7:0]  decoded_engine_op,
    output wire [3:0]  decoded_root_x,
    output wire [3:0]  decoded_root_y,

    output wire        all_done,
    output wire        any_busy,
    output wire        any_trap,
    output wire [15:0] first_trap_class,

    input  wire        load_valid,
    input  wire [7:0]  load_node,
    input  wire [7:0]  load_index,
    input  wire [31:0] load_data,

    input  wire [7:0]  read_node,
    input  wire [7:0]  read_index,
    output wire [31:0] read_data,

    input  wire        inject_valid,
    input  wire [7:0]  inject_node,
    input  wire [1:0]  inject_dir,

    output reg  [31:0] total_wire_flits,
    output reg  [31:0] total_hop_distance,
    output reg  [31:0] total_engine_flits_sent,
    output reg  [31:0] total_replayed_flits,
    output reg  [31:0] total_retry_events,
    output reg  [31:0] total_credit_stall_cycles,
    output reg  [31:0] total_crc_errors,
    output reg  [31:0] total_sequence_errors,
    output reg  [31:0] total_steps,
    output reg  [31:0] max_serial_traversals,
    output reg  [31:0] max_busy_cycles,
    output wire        any_link_error,
    output wire        any_misroute
);
    localparam integer NODES = MESH_X * MESH_Y;

    wire [15:0] decoder_trap_class;
    wire [7:0] engine_reduction_order;
    ot_a3_communication_decoder #(
        .MESH_X(MESH_X), .MESH_Y(MESH_Y), .VEC_LEN(VEC_LEN),
        .CREDITS(CREDITS), .RETRY_MAX(RETRY_MAX),
        .TIMEOUT_CLASS(TIMEOUT_CLASS)
    ) u_communication_decoder (
        .descriptor_record(communication_descriptor),
        .numeric_descriptor_record(numeric_descriptor),
        .instruction_subopcode(instruction_subopcode),
        .algorithm(alg),
        .numeric_descriptor_id(numeric_descriptor_id),
        .numeric_reduction_order(numeric_reduction_order),
        .record_valid(descriptor_valid),
        .numeric_record_valid(numeric_descriptor_valid),
        .numeric_semantics_supported(numeric_semantics_supported),
        .numeric_refusal_reason(numeric_refusal_reason),
        .command_admitted(command_admitted),
        .refusal_reason(refusal_reason),
        .trap_class(decoder_trap_class),
        .magic(decoded_magic),
        .descriptor_type(decoded_descriptor_type),
        .type_major(decoded_type_major),
        .type_minor(decoded_type_minor),
        .total_bytes(decoded_total_bytes),
        .flags(decoded_flags),
        .primary_object_id(decoded_primary_object_id),
        .secondary_object_id(decoded_secondary_object_id),
        .numeric_profile_id(decoded_numeric_profile_id),
        .schedule_id(decoded_schedule_id),
        .permissions(decoded_permissions),
        .owner_scope_id(decoded_owner_scope_id),
        .payload_offset(decoded_payload_offset),
        .payload_bytes(decoded_payload_bytes),
        .supplied_crc(decoded_supplied_crc),
        .calculated_crc(decoded_calculated_crc),
        .collective_op(decoded_collective_op),
        .ordering(decoded_ordering),
        .integrity_mode(decoded_integrity_mode),
        .virtual_channel(decoded_virtual_channel),
        .source_node(decoded_source_node),
        .destination_node(decoded_destination_node),
        .group_id(decoded_group_id),
        .route_class(decoded_route_class),
        .local_object_id(decoded_local_object_id),
        .remote_object_id(decoded_remote_object_id),
        .local_offset(decoded_local_offset),
        .remote_offset(decoded_remote_offset),
        .byte_extent(decoded_byte_extent),
        .credit_bound(decoded_credit_bound),
        .retry_bound(decoded_retry_bound),
        .timeout_class(decoded_timeout_class),
        .completion_event_id(decoded_completion_event_id),
        .reduction_numeric_id(decoded_reduction_numeric_id),
        .counter_class_id(decoded_counter_class_id),
        .participant_count(decoded_participant_count),
        .chunk_bytes(decoded_chunk_bytes),
        .participant_scope(decoded_participant_scope),
        .numeric_descriptor_type(decoded_numeric_descriptor_type),
        .numeric_total_bytes(decoded_numeric_total_bytes),
        .numeric_payload_bytes(decoded_numeric_payload_bytes),
        .numeric_supplied_crc(decoded_numeric_supplied_crc),
        .numeric_calculated_crc(decoded_numeric_calculated_crc),
        .numeric_input_dtype(decoded_numeric_input_dtype),
        .numeric_second_input_dtype(decoded_numeric_second_input_dtype),
        .numeric_accumulator_dtype(decoded_numeric_accumulator_dtype),
        .numeric_output_dtype(decoded_numeric_output_dtype),
        .numeric_rounding_mode(decoded_numeric_rounding_mode),
        .numeric_decoded_reduction_order(decoded_numeric_reduction_order),
        .numeric_saturate(decoded_numeric_saturate),
        .numeric_nan_policy(decoded_numeric_nan_policy),
        .numeric_epsilon_bits(decoded_numeric_epsilon_bits),
        .numeric_scale_bits(decoded_numeric_scale_bits),
        .numeric_flags(decoded_numeric_flags),
        .numeric_contract_digest_zero(
            decoded_numeric_contract_digest_zero),
        .engine_op(decoded_engine_op),
        .engine_reduction_order(engine_reduction_order),
        .engine_root_x(decoded_root_x),
        .engine_root_y(decoded_root_y)
    );

    wire engine_start = start && command_admitted;

    wire [3:0]          o_valid  [0:NODES-1];
    wire [4*FLIT_W-1:0] o_flit   [0:NODES-1];
    wire [4*8-1:0]      o_seq    [0:NODES-1];
    wire [4*32-1:0]     o_crc    [0:NODES-1];
    wire [3:0]          o_ack     [0:NODES-1];
    wire [4*8-1:0]      o_ack_seq [0:NODES-1];
    wire [4*2-1:0]      o_credit  [0:NODES-1];
    wire [3:0]          o_nak     [0:NODES-1];
    wire [4*8-1:0]      o_nak_seq [0:NODES-1];

    reg  [3:0]          i_valid  [0:NODES-1];
    reg  [4*FLIT_W-1:0] i_flit   [0:NODES-1];
    reg  [4*8-1:0]      i_seq    [0:NODES-1];
    reg  [4*32-1:0]     i_crc    [0:NODES-1];
    reg  [3:0]          i_ack     [0:NODES-1];
    reg  [4*8-1:0]      i_ack_seq [0:NODES-1];
    reg  [4*2-1:0]      i_credit  [0:NODES-1];
    reg  [3:0]          i_nak     [0:NODES-1];
    reg  [4*8-1:0]      i_nak_seq [0:NODES-1];

    // the delayed wire, one bundle per (node, outgoing direction)
    wire                w_valid  [0:NODES-1][0:3];
    wire [FLIT_W-1:0]   w_flit   [0:NODES-1][0:3];
    wire [7:0]          w_seq    [0:NODES-1][0:3];
    wire [31:0]         w_crc    [0:NODES-1][0:3];
    wire                w_ack     [0:NODES-1][0:3];
    wire [7:0]          w_ack_seq [0:NODES-1][0:3];
    wire [1:0]          w_credit  [0:NODES-1][0:3];
    wire                w_nak     [0:NODES-1][0:3];
    wire [7:0]          w_nak_seq [0:NODES-1][0:3];

    wire [31:0] n_steps    [0:NODES-1];
    wire [31:0] n_esent    [0:NODES-1];
    wire [31:0] n_hopdist  [0:NODES-1];
    wire [31:0] n_serial   [0:NODES-1];
    wire [31:0] n_busy     [0:NODES-1];
    wire [31:0] n_txflits  [0:NODES-1];
    wire [31:0] n_replay   [0:NODES-1];
    wire [31:0] n_retry    [0:NODES-1];
    wire [31:0] n_stall    [0:NODES-1];
    wire [31:0] n_crcerr   [0:NODES-1];
    wire [31:0] n_seqerr   [0:NODES-1];
    wire [31:0] n_readdata [0:NODES-1];
    wire        n_busy_f   [0:NODES-1];
    wire        n_done     [0:NODES-1];
    wire        n_trap     [0:NODES-1];
    wire [15:0] n_trapcls  [0:NODES-1];
    wire        n_linkerr  [0:NODES-1];
    wire        n_misroute [0:NODES-1];

    reg [NODES-1:0] done_latched;
    reg [NODES-1:0] busy_flags;
    reg [NODES-1:0] trap_flags;
    reg [NODES-1:0] linkerr_flags;
    reg [NODES-1:0] misroute_flags;
    reg [15:0] trap_class_latched;
    reg decode_refused_latched;

    assign all_done = decode_refused_latched || (&done_latched);
    assign any_busy = |busy_flags;
    assign any_trap = decode_refused_latched || (|trap_flags);
    assign first_trap_class = trap_class_latched;
    assign any_link_error = |linkerr_flags;
    assign any_misroute = |misroute_flags;
    assign read_data = n_readdata[read_node];

    genvar gx, gy, gd;
    generate
        for (gy = 0; gy < MESH_Y; gy = gy + 1) begin : GEN_Y
            for (gx = 0; gx < MESH_X; gx = gx + 1) begin : GEN_X
                localparam integer NI = gy * MESH_X + gx;
                wire [3:0] inject_mask =
                    (inject_valid && (inject_node == NI[7:0]))
                        ? (4'd1 << inject_dir) : 4'd0;

                ot_a3_link_node #(
                    .FLIT_W(FLIT_W), .MESH_X(MESH_X), .MESH_Y(MESH_Y),
                    .MY_X(gx), .MY_Y(gy), .VEC_LEN(VEC_LEN),
                    .CREDITS(CREDITS), .RETRY_MAX(RETRY_MAX),
                    .ACK_TIMEOUT(ACK_TIMEOUT)
                ) u_node (
                    .clk(clk), .rst_n(rst_n),
                    .start(engine_start), .op(decoded_engine_op), .alg(alg),
                    .reduction_order(engine_reduction_order),
                    .root_x(decoded_root_x), .root_y(decoded_root_y),
                    .busy(n_busy_f[NI]), .done(n_done[NI]),
                    .trap(n_trap[NI]), .trap_class(n_trapcls[NI]),
                    .load_valid(load_valid && (load_node == NI[7:0])),
                    .load_index(load_index), .load_data(load_data),
                    .read_index(read_index), .read_data(n_readdata[NI]),
                    .o_valid(o_valid[NI]), .o_flit(o_flit[NI]),
                    .o_seq(o_seq[NI]), .o_crc(o_crc[NI]),
                    .i_ack(i_ack[NI]), .i_ack_seq(i_ack_seq[NI]),
                    .i_credit(i_credit[NI]), .i_nak(i_nak[NI]),
                    .i_nak_seq(i_nak_seq[NI]),
                    .i_valid(i_valid[NI]), .i_flit(i_flit[NI]),
                    .i_seq(i_seq[NI]), .i_crc(i_crc[NI]),
                    .o_ack(o_ack[NI]), .o_ack_seq(o_ack_seq[NI]),
                    .o_credit(o_credit[NI]), .o_nak(o_nak[NI]),
                    .o_nak_seq(o_nak_seq[NI]),
                    .inject_crc_error(inject_mask),
                    .steps_taken(n_steps[NI]),
                    .engine_flits_sent(n_esent[NI]),
                    .engine_flits_received(),
                    .hop_distance_sent(n_hopdist[NI]),
                    .serial_traversals(n_serial[NI]),
                    .busy_cycles(n_busy[NI]),
                    .router_flits_forwarded(), .router_flits_local(),
                    .link_flits_transmitted(n_txflits[NI]),
                    .link_replayed_flits(n_replay[NI]),
                    .link_retry_events(n_retry[NI]),
                    .link_credit_stall_cycles(n_stall[NI]),
                    .link_crc_errors(n_crcerr[NI]),
                    .link_sequence_errors(n_seqerr[NI]),
                    .link_error(n_linkerr[NI]),
                    .router_misroute_error(n_misroute[NI])
                );

                for (gd = 0; gd < 4; gd = gd + 1) begin : GEN_WIRE
                    ot_a3_link_wire #(.FLIT_W(FLIT_W), .CYCLES(HOP_CYCLES)) u_w (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(o_valid[NI][gd]),
                        .in_flit(o_flit[NI][gd*FLIT_W +: FLIT_W]),
                        .in_seq(o_seq[NI][gd*8 +: 8]),
                        .in_crc(o_crc[NI][gd*32 +: 32]),
                        .out_valid(w_valid[NI][gd]),
                        .out_flit(w_flit[NI][gd]),
                        .out_seq(w_seq[NI][gd]),
                        .out_crc(w_crc[NI][gd])
                    );
                    ot_a3_link_return #(.CYCLES(HOP_CYCLES)) u_r (
                        .clk(clk), .rst_n(rst_n),
                        .in_ack(o_ack[NI][gd]),
                        .in_ack_seq(o_ack_seq[NI][gd*8 +: 8]),
                        .in_credit(o_credit[NI][gd*2 +: 2]),
                        .in_nak(o_nak[NI][gd]),
                        .in_nak_seq(o_nak_seq[NI][gd*8 +: 8]),
                        .out_ack(w_ack[NI][gd]),
                        .out_ack_seq(w_ack_seq[NI][gd]),
                        .out_credit(w_credit[NI][gd]),
                        .out_nak(w_nak[NI][gd]),
                        .out_nak_seq(w_nak_seq[NI][gd])
                    );
                end
            end
        end
    endgenerate

    // Neighbour wiring.  0 EAST, 1 WEST, 2 SOUTH, 3 NORTH; the opposite of d is
    // d^1, which is why the direction encoding pairs them.
    integer x, y, ni, nj;
    always @* begin
        for (y = 0; y < MESH_Y; y = y + 1) begin
            for (x = 0; x < MESH_X; x = x + 1) begin
                ni = y * MESH_X + x;
                i_valid[ni] = 4'b0;
                i_flit[ni] = {(4*FLIT_W){1'b0}};
                i_seq[ni] = {(4*8){1'b0}};
                i_crc[ni] = {(4*32){1'b0}};
                i_ack[ni] = 4'b0;
                i_ack_seq[ni] = {(4*8){1'b0}};
                i_credit[ni] = {(4*2){1'b0}};
                i_nak[ni] = 4'b0;
                i_nak_seq[ni] = {(4*8){1'b0}};

                // EAST input of this node is the WEST output of (x+1,y)
                if (x + 1 < MESH_X) begin
                    nj = y * MESH_X + (x + 1);
                    i_valid[ni][0] = w_valid[nj][1];
                    i_flit[ni][0*FLIT_W +: FLIT_W] = w_flit[nj][1];
                    i_seq[ni][0*8 +: 8] = w_seq[nj][1];
                    i_crc[ni][0*32 +: 32] = w_crc[nj][1];
                    i_ack[ni][0] = w_ack[nj][1];
                    i_ack_seq[ni][0*8 +: 8] = w_ack_seq[nj][1];
                    i_credit[ni][0*2 +: 2] = w_credit[nj][1];
                    i_nak[ni][0] = w_nak[nj][1];
                    i_nak_seq[ni][0*8 +: 8] = w_nak_seq[nj][1];
                end
                // WEST input is the EAST output of (x-1,y)
                if (x > 0) begin
                    nj = y * MESH_X + (x - 1);
                    i_valid[ni][1] = w_valid[nj][0];
                    i_flit[ni][1*FLIT_W +: FLIT_W] = w_flit[nj][0];
                    i_seq[ni][1*8 +: 8] = w_seq[nj][0];
                    i_crc[ni][1*32 +: 32] = w_crc[nj][0];
                    i_ack[ni][1] = w_ack[nj][0];
                    i_ack_seq[ni][1*8 +: 8] = w_ack_seq[nj][0];
                    i_credit[ni][1*2 +: 2] = w_credit[nj][0];
                    i_nak[ni][1] = w_nak[nj][0];
                    i_nak_seq[ni][1*8 +: 8] = w_nak_seq[nj][0];
                end
                // SOUTH input is the NORTH output of (x,y+1)
                if (y + 1 < MESH_Y) begin
                    nj = (y + 1) * MESH_X + x;
                    i_valid[ni][2] = w_valid[nj][3];
                    i_flit[ni][2*FLIT_W +: FLIT_W] = w_flit[nj][3];
                    i_seq[ni][2*8 +: 8] = w_seq[nj][3];
                    i_crc[ni][2*32 +: 32] = w_crc[nj][3];
                    i_ack[ni][2] = w_ack[nj][3];
                    i_ack_seq[ni][2*8 +: 8] = w_ack_seq[nj][3];
                    i_credit[ni][2*2 +: 2] = w_credit[nj][3];
                    i_nak[ni][2] = w_nak[nj][3];
                    i_nak_seq[ni][2*8 +: 8] = w_nak_seq[nj][3];
                end
                // NORTH input is the SOUTH output of (x,y-1)
                if (y > 0) begin
                    nj = (y - 1) * MESH_X + x;
                    i_valid[ni][3] = w_valid[nj][2];
                    i_flit[ni][3*FLIT_W +: FLIT_W] = w_flit[nj][2];
                    i_seq[ni][3*8 +: 8] = w_seq[nj][2];
                    i_crc[ni][3*32 +: 32] = w_crc[nj][2];
                    i_ack[ni][3] = w_ack[nj][2];
                    i_ack_seq[ni][3*8 +: 8] = w_ack_seq[nj][2];
                    i_credit[ni][3*2 +: 2] = w_credit[nj][2];
                    i_nak[ni][3] = w_nak[nj][2];
                    i_nak_seq[ni][3*8 +: 8] = w_nak_seq[nj][2];
                end
            end
        end
    end

    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            done_latched <= {NODES{1'b0}};
            trap_flags <= {NODES{1'b0}};
            linkerr_flags <= {NODES{1'b0}};
            misroute_flags <= {NODES{1'b0}};
            trap_class_latched <= 16'd0;
            decode_refused_latched <= 1'b0;
        end else begin
            if (start) begin
                done_latched <= {NODES{1'b0}};
                // A trap belongs to the collective that raised it.  A sticky
                // flag that outlived its case would make every later case
                // report the first case's refusal.
                trap_flags <= {NODES{1'b0}};
                decode_refused_latched <= !command_admitted;
                trap_class_latched <= command_admitted ? 16'd0 :
                                      decoder_trap_class;
            end
            for (k = 0; k < NODES; k = k + 1) begin
                if (n_done[k])
                    done_latched[k] <= 1'b1;
                if (n_trap[k]) begin
                    trap_flags[k] <= 1'b1;
                    if (!(|trap_flags))
                        trap_class_latched <= n_trapcls[k];
                end
                if (n_linkerr[k])
                    linkerr_flags[k] <= 1'b1;
                if (n_misroute[k])
                    misroute_flags[k] <= 1'b1;
            end
        end
    end

    integer a;
    always @* begin
        total_wire_flits = 32'd0;
        total_hop_distance = 32'd0;
        total_engine_flits_sent = 32'd0;
        total_replayed_flits = 32'd0;
        total_retry_events = 32'd0;
        total_credit_stall_cycles = 32'd0;
        total_crc_errors = 32'd0;
        total_sequence_errors = 32'd0;
        total_steps = 32'd0;
        max_serial_traversals = 32'd0;
        max_busy_cycles = 32'd0;
        for (a = 0; a < NODES; a = a + 1) begin
            busy_flags[a] = n_busy_f[a];
            total_wire_flits = total_wire_flits + n_txflits[a];
            total_replayed_flits = total_replayed_flits + n_replay[a];
            total_retry_events = total_retry_events + n_retry[a];
            total_credit_stall_cycles = total_credit_stall_cycles + n_stall[a];
            total_crc_errors = total_crc_errors + n_crcerr[a];
            total_sequence_errors = total_sequence_errors + n_seqerr[a];
            if (!decode_refused_latched) begin
                total_hop_distance = total_hop_distance + n_hopdist[a];
                total_engine_flits_sent = total_engine_flits_sent + n_esent[a];
                total_steps = total_steps + n_steps[a];
                if (n_busy[a] > max_busy_cycles)
                    max_busy_cycles = n_busy[a];
                if (n_serial[a] > max_serial_traversals)
                    max_serial_traversals = n_serial[a];
            end
        end
    end
endmodule
