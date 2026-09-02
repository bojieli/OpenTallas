`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 COMMUNICATION decode and fail-closed standalone-link admission.
//
// `record_valid` covers every byte of the complete 192-byte COMMUNICATION
// record.  `numeric_record_valid` independently covers every byte of the
// complete 128-byte NUMERIC record.  Neither result implies that this bounded
// mesh can execute the decoded command.  `command_admitted` additionally
// proves that every command semantic is either implemented by this block or
// explicitly neutral in the record, and that the participant set, data
// extent, flit-sized chunks, elaborated storage and complete numeric profile
// match what the RTL consumes.
//
// The algorithm remains an explicit non-ABI sideband.  The reduction-order
// sideband is retained only as an integration cross-check: the engine control
// is always derived from the validated NUMERIC record, never from the sideband.
// This standalone block has no TOPOLOGY table, so it admits only all-node
// membership (NODE scope and NO_ID group).
// ---------------------------------------------------------------------------
module ot_a3_communication_decoder #(
    parameter integer MESH_X = 4,
    parameter integer MESH_Y = 4,
    parameter integer VEC_LEN = 16,
    parameter integer CREDITS = 8,
    parameter integer RETRY_MAX = 3,
    parameter integer TIMEOUT_CLASS = 1,
    parameter integer VIRTUAL_CHANNEL_COUNT = 4
) (
    input  wire [1535:0] descriptor_record,
    input  wire [1023:0] numeric_descriptor_record,
    input  wire [7:0]    instruction_subopcode,
    input  wire [1:0]    algorithm,
    input  wire [31:0]   numeric_descriptor_id,
    input  wire [7:0]    numeric_reduction_order,

    output wire          record_valid,
    output wire          numeric_record_valid,
    output wire          numeric_semantics_supported,
    output wire [7:0]    numeric_refusal_reason,
    output wire          command_admitted,
    output reg  [7:0]    refusal_reason,
    output wire [15:0]   trap_class,

    // Common 64-byte COMMUNICATION header.
    output wire [31:0]   magic,
    output wire [15:0]   descriptor_type,
    output wire [7:0]    type_major,
    output wire [7:0]    type_minor,
    output wire [31:0]   total_bytes,
    output wire [31:0]   flags,
    output wire [31:0]   primary_object_id,
    output wire [31:0]   secondary_object_id,
    output wire [31:0]   numeric_profile_id,
    output wire [31:0]   schedule_id,
    output wire [31:0]   permissions,
    output wire [31:0]   owner_scope_id,
    output wire [31:0]   payload_offset,
    output wire [31:0]   payload_bytes,
    output wire [31:0]   supplied_crc,
    output wire [31:0]   calculated_crc,

    // Fixed 128-byte COMMUNICATION payload.
    output wire [7:0]    collective_op,
    output wire [7:0]    ordering,
    output wire [7:0]    integrity_mode,
    output wire [7:0]    virtual_channel,
    output wire [15:0]   source_node,
    output wire [15:0]   destination_node,
    output wire [31:0]   group_id,
    output wire [31:0]   route_class,
    output wire [31:0]   local_object_id,
    output wire [31:0]   remote_object_id,
    output wire [63:0]   local_offset,
    output wire [63:0]   remote_offset,
    output wire [63:0]   byte_extent,
    output wire [31:0]   credit_bound,
    output wire [31:0]   retry_bound,
    output wire [31:0]   timeout_class,
    output wire [31:0]   completion_event_id,
    output wire [31:0]   reduction_numeric_id,
    output wire [31:0]   counter_class_id,
    output wire [31:0]   participant_count,
    output wire [31:0]   chunk_bytes,
    output wire [7:0]    participant_scope,

    // NUMERIC structure and all arithmetic controls consumed by this engine.
    output wire [15:0]   numeric_descriptor_type,
    output wire [31:0]   numeric_total_bytes,
    output wire [31:0]   numeric_payload_bytes,
    output wire [31:0]   numeric_supplied_crc,
    output wire [31:0]   numeric_calculated_crc,
    output wire [7:0]    numeric_input_dtype,
    output wire [7:0]    numeric_second_input_dtype,
    output wire [7:0]    numeric_accumulator_dtype,
    output wire [7:0]    numeric_output_dtype,
    output wire [7:0]    numeric_rounding_mode,
    output wire [7:0]    numeric_decoded_reduction_order,
    output wire [7:0]    numeric_saturate,
    output wire [7:0]    numeric_nan_policy,
    output wire [31:0]   numeric_epsilon_bits,
    output wire [31:0]   numeric_scale_bits,
    output wire [31:0]   numeric_flags,
    output wire          numeric_contract_digest_zero,

    // Controls consumed by the collective engine.
    output reg  [7:0]    engine_op,
    output wire [7:0]    engine_reduction_order,
    output reg  [3:0]    engine_root_x,
    output reg  [3:0]    engine_root_y
);
    localparam integer NODES = MESH_X * MESH_Y;
    localparam [63:0] DATA_CAPACITY_BYTES = VEC_LEN * 4;
    localparam [7:0] ENGINE_BARRIER = 8'hff;
    localparam integer CONFIG_SUPPORTED =
        (MESH_X >= 1) && (MESH_X <= 16) &&
        (MESH_Y >= 1) && (MESH_Y <= 16) &&
        ((MESH_X & (MESH_X - 1)) == 0) &&
        ((MESH_Y & (MESH_Y - 1)) == 0) &&
        (NODES >= 2) && (NODES <= 256) &&
        (VEC_LEN >= 1) && (VEC_LEN <= 256) &&
        (CREDITS >= 2) && (CREDITS <= 64) &&
        (RETRY_MAX >= 0) && (RETRY_MAX <= 3) &&
        (VIRTUAL_CHANNEL_COUNT >= 1) &&
        (VIRTUAL_CHANNEL_COUNT <= 256);

    // -- COMMUNICATION decode ----------------------------------------------
    assign magic               = descriptor_record[31:0];
    assign descriptor_type     = descriptor_record[47:32];
    assign type_major          = descriptor_record[55:48];
    assign type_minor          = descriptor_record[63:56];
    assign total_bytes         = descriptor_record[95:64];
    assign flags               = descriptor_record[127:96];
    assign primary_object_id   = descriptor_record[159:128];
    assign secondary_object_id = descriptor_record[191:160];
    assign numeric_profile_id  = descriptor_record[223:192];
    assign schedule_id         = descriptor_record[255:224];
    assign permissions         = descriptor_record[287:256];
    assign owner_scope_id      = descriptor_record[319:288];
    assign payload_offset      = descriptor_record[351:320];
    assign payload_bytes       = descriptor_record[383:352];
    assign supplied_crc        = descriptor_record[415:384];

    assign collective_op       = descriptor_record[519:512];
    assign ordering            = descriptor_record[527:520];
    assign integrity_mode      = descriptor_record[535:528];
    assign virtual_channel     = descriptor_record[543:536];
    assign source_node         = descriptor_record[559:544];
    assign destination_node    = descriptor_record[575:560];
    assign group_id            = descriptor_record[607:576];
    assign route_class         = descriptor_record[639:608];
    assign local_object_id     = descriptor_record[671:640];
    assign remote_object_id    = descriptor_record[703:672];
    assign local_offset        = descriptor_record[767:704];
    assign remote_offset       = descriptor_record[831:768];
    assign byte_extent         = descriptor_record[895:832];
    assign credit_bound        = descriptor_record[927:896];
    assign retry_bound         = descriptor_record[959:928];
    assign timeout_class       = descriptor_record[991:960];
    assign completion_event_id = descriptor_record[1023:992];
    assign reduction_numeric_id= descriptor_record[1055:1024];
    assign counter_class_id    = descriptor_record[1087:1056];
    assign participant_count   = descriptor_record[1119:1088];
    assign chunk_bytes         = descriptor_record[1151:1120];
    assign participant_scope   = descriptor_record[1159:1152];

    wire [1535:0] crc_record = {
        descriptor_record[1535:416], 32'h0000_0000,
        descriptor_record[383:0]
    };
    assign calculated_crc = ot_crc_pkg::crc32c(
        1536, {{(4096-1536){1'b0}}, crc_record}
    );

    wire header_reserved_bad = |descriptor_record[511:416];
    wire payload_reserved_bad = |descriptor_record[1535:1160];
    wire permission_reserved_bad = |permissions[31:8];
    wire permission_conflict = permissions[7] &&
        (permissions[1] || permissions[3] || permissions[4]);
    wire collective_op_legal = collective_op <=
        ot_a3_link_pkg::COLL_REDUCE_SCATTER;
    wire ordering_legal = ordering <= ot_a3_link_pkg::ORDERING_SEQUENTIAL;
    wire integrity_mode_legal = integrity_mode <=
        ot_a3_link_pkg::INTEGRITY_CRC_AND_ECC;
    wire participant_scope_legal = participant_scope <=
        ot_a3_link_pkg::PARTICIPANT_TILE;

    reg [7:0] record_reason;
    always @* begin
        if (magic != ot_a3_link_pkg::DESCRIPTOR_MAGIC)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_MAGIC;
        else if (descriptor_type != ot_a3_link_pkg::DESC_COMMUNICATION)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_TYPE;
        else if ((type_major != ot_a3_link_pkg::DESCRIPTOR_TYPE_MAJOR) ||
                 (type_minor > ot_a3_link_pkg::DESCRIPTOR_TYPE_MINOR))
            record_reason = ot_a3_link_pkg::COMM_REFUSE_VERSION;
        else if (total_bytes != ot_a3_link_pkg::DESCRIPTOR_TOTAL_BYTES)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_TOTAL_BYTES;
        else if ((payload_offset !=
                  ot_a3_link_pkg::DESCRIPTOR_PAYLOAD_OFFSET) ||
                 (payload_bytes !=
                  ot_a3_link_pkg::COMMUNICATION_PAYLOAD_BYTES))
            record_reason = ot_a3_link_pkg::COMM_REFUSE_PAYLOAD_GEOMETRY;
        else if (header_reserved_bad)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_HEADER_RESERVED;
        else if (payload_reserved_bad)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_PAYLOAD_RESERVED;
        else if (calculated_crc != supplied_crc)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_RECORD_CRC;
        else if (permission_reserved_bad || permission_conflict)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_PERMISSIONS;
        else if (!collective_op_legal)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_COLLECTIVE_OP;
        else if (!ordering_legal)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_ORDERING;
        else if (!integrity_mode_legal)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_INTEGRITY_MODE;
        else if (!participant_scope_legal)
            record_reason = ot_a3_link_pkg::COMM_REFUSE_PARTICIPANT_SCOPE;
        else
            record_reason = ot_a3_link_pkg::COMM_REFUSE_NONE;
    end
    assign record_valid =
        record_reason == ot_a3_link_pkg::COMM_REFUSE_NONE;

    // -- NUMERIC decode -----------------------------------------------------
    wire [31:0] numeric_magic = numeric_descriptor_record[31:0];
    assign numeric_descriptor_type = numeric_descriptor_record[47:32];
    wire [7:0] numeric_type_major = numeric_descriptor_record[55:48];
    wire [7:0] numeric_type_minor = numeric_descriptor_record[63:56];
    assign numeric_total_bytes = numeric_descriptor_record[95:64];
    wire [31:0] numeric_header_flags = numeric_descriptor_record[127:96];
    wire [31:0] numeric_primary_object_id =
        numeric_descriptor_record[159:128];
    wire [31:0] numeric_secondary_object_id =
        numeric_descriptor_record[191:160];
    wire [31:0] numeric_profile_reference =
        numeric_descriptor_record[223:192];
    wire [31:0] numeric_schedule_reference =
        numeric_descriptor_record[255:224];
    wire [31:0] numeric_permissions = numeric_descriptor_record[287:256];
    wire [31:0] numeric_owner_scope_id = numeric_descriptor_record[319:288];
    wire [31:0] numeric_payload_offset = numeric_descriptor_record[351:320];
    assign numeric_payload_bytes = numeric_descriptor_record[383:352];
    assign numeric_supplied_crc = numeric_descriptor_record[415:384];

    assign numeric_input_dtype = numeric_descriptor_record[519:512];
    assign numeric_second_input_dtype = numeric_descriptor_record[527:520];
    assign numeric_accumulator_dtype = numeric_descriptor_record[535:528];
    assign numeric_output_dtype = numeric_descriptor_record[543:536];
    assign numeric_rounding_mode = numeric_descriptor_record[551:544];
    assign numeric_decoded_reduction_order =
        numeric_descriptor_record[559:552];
    assign numeric_saturate = numeric_descriptor_record[567:560];
    assign numeric_nan_policy = numeric_descriptor_record[575:568];
    assign numeric_epsilon_bits = numeric_descriptor_record[607:576];
    assign numeric_scale_bits = numeric_descriptor_record[639:608];
    assign numeric_flags = numeric_descriptor_record[671:640];
    assign numeric_contract_digest_zero =
        numeric_descriptor_record[1023:768] == 256'd0;

    wire [1023:0] numeric_crc_record = {
        numeric_descriptor_record[1023:416], 32'h0000_0000,
        numeric_descriptor_record[383:0]
    };
    assign numeric_calculated_crc = ot_crc_pkg::crc32c(
        1024, {{(4096-1024){1'b0}}, numeric_crc_record}
    );

    function automatic dtype_legal;
        input [7:0] dtype;
        begin
            case (dtype)
                ot_a3_link_pkg::DTYPE_U8,
                ot_a3_link_pkg::DTYPE_I8,
                ot_a3_link_pkg::DTYPE_U16,
                ot_a3_link_pkg::DTYPE_I16,
                ot_a3_link_pkg::DTYPE_U32,
                ot_a3_link_pkg::DTYPE_I32,
                ot_a3_link_pkg::DTYPE_U64,
                ot_a3_link_pkg::DTYPE_I64,
                ot_a3_link_pkg::DTYPE_BF16,
                ot_a3_link_pkg::DTYPE_FP16,
                ot_a3_link_pkg::DTYPE_FP32,
                ot_a3_link_pkg::DTYPE_FP64,
                ot_a3_link_pkg::DTYPE_FP8_E4M3FN,
                ot_a3_link_pkg::DTYPE_FP8_E5M2,
                ot_a3_link_pkg::DTYPE_MXFP4_E2M1,
                ot_a3_link_pkg::DTYPE_E8M0_SCALE: dtype_legal = 1'b1;
                default: dtype_legal = 1'b0;
            endcase
        end
    endfunction

    wire numeric_header_reserved_bad = |numeric_descriptor_record[511:416];
    wire numeric_payload_reserved_bad = |numeric_descriptor_record[767:672];
    wire numeric_permission_reserved_bad = |numeric_permissions[31:8];
    wire numeric_permission_conflict = numeric_permissions[7] &&
        (numeric_permissions[1] || numeric_permissions[3] ||
         numeric_permissions[4]);
    wire numeric_registry_legal =
        dtype_legal(numeric_input_dtype) &&
        dtype_legal(numeric_second_input_dtype) &&
        dtype_legal(numeric_accumulator_dtype) &&
        dtype_legal(numeric_output_dtype) &&
        (numeric_rounding_mode <= ot_a3_link_pkg::ROUND_STOCHASTIC) &&
        (numeric_decoded_reduction_order <=
         ot_a3_link_pkg::ORDER_BLOCKED_ASCENDING) &&
        (numeric_saturate <= 8'd1);

    reg [7:0] numeric_reason;
    always @* begin
        if (numeric_magic != ot_a3_link_pkg::DESCRIPTOR_MAGIC)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_MAGIC;
        else if (numeric_descriptor_type != ot_a3_link_pkg::DESC_NUMERIC)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_TYPE;
        else if ((numeric_type_major !=
                  ot_a3_link_pkg::DESCRIPTOR_TYPE_MAJOR) ||
                 (numeric_type_minor >
                  ot_a3_link_pkg::DESCRIPTOR_TYPE_MINOR))
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_VERSION;
        else if (numeric_total_bytes !=
                 ot_a3_link_pkg::NUMERIC_TOTAL_BYTES)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_TOTAL_BYTES;
        else if ((numeric_payload_offset !=
                  ot_a3_link_pkg::DESCRIPTOR_PAYLOAD_OFFSET) ||
                 (numeric_payload_bytes !=
                  ot_a3_link_pkg::NUMERIC_PAYLOAD_BYTES))
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_PAYLOAD_GEOMETRY;
        else if (numeric_header_reserved_bad)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_HEADER_RESERVED;
        else if (numeric_payload_reserved_bad)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_PAYLOAD_RESERVED;
        else if (numeric_calculated_crc != numeric_supplied_crc)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_RECORD_CRC;
        else if (numeric_permission_reserved_bad ||
                 numeric_permission_conflict)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_PERMISSIONS;
        else if (!numeric_registry_legal)
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_NUMERIC_SEMANTICS;
        else
            numeric_reason = ot_a3_link_pkg::COMM_REFUSE_NONE;
    end
    assign numeric_refusal_reason = numeric_reason;
    assign numeric_record_valid =
        numeric_reason == ot_a3_link_pkg::COMM_REFUSE_NONE;

    // Zero references/digest make this a deliberately local arithmetic
    // contract instead of borrowing the meaning of a frozen deployment
    // contract that this engine does not implement.
    wire numeric_header_neutral =
        (numeric_header_flags == 32'd0) &&
        (numeric_primary_object_id == ot_a3_link_pkg::NO_ID) &&
        (numeric_secondary_object_id == ot_a3_link_pkg::NO_ID) &&
        (numeric_profile_reference == ot_a3_link_pkg::NO_ID) &&
        (numeric_schedule_reference == ot_a3_link_pkg::NO_ID) &&
        (numeric_owner_scope_id == 32'd0);
    assign numeric_semantics_supported = numeric_record_valid &&
        numeric_header_neutral && numeric_contract_digest_zero &&
        (numeric_input_dtype == ot_a3_link_pkg::DTYPE_FP32) &&
        (numeric_second_input_dtype == ot_a3_link_pkg::DTYPE_FP32) &&
        (numeric_accumulator_dtype == ot_a3_link_pkg::DTYPE_FP32) &&
        (numeric_output_dtype == ot_a3_link_pkg::DTYPE_FP32) &&
        (numeric_rounding_mode == ot_a3_link_pkg::ROUND_NEAREST_EVEN) &&
        (numeric_saturate == 8'd0) &&
        (numeric_nan_policy == 8'd0) &&
        (numeric_epsilon_bits == 32'd0) &&
        (numeric_scale_bits == 32'd0) &&
        (numeric_flags == 32'd0);

    // -- Standalone execution boundary ------------------------------------
    wire is_barrier = instruction_subopcode == ot_a3_link_pkg::LINK_BARRIER;
    wire is_collective = instruction_subopcode ==
                         ot_a3_link_pkg::LINK_COLLECTIVE;
    wire is_multicast = instruction_subopcode ==
                        ot_a3_link_pkg::LINK_MULTICAST;
    wire is_reduction = (collective_op == ot_a3_link_pkg::COLL_SUM) ||
                        (collective_op == ot_a3_link_pkg::COLL_MAX) ||
                        (collective_op == ot_a3_link_pkg::COLL_MIN);
    wire supported_op = is_barrier ||
        ((is_collective || is_multicast) &&
         (is_reduction ||
          (collective_op == ot_a3_link_pkg::COLL_BROADCAST)));
    wire subopcode_supported = is_barrier || is_collective || is_multicast;
    wire subopcode_op_agrees = !is_multicast ||
        (collective_op == ot_a3_link_pkg::COLL_BROADCAST);
    wire object_binding_ok =
        (primary_object_id == local_object_id) &&
        (secondary_object_id == remote_object_id);
    wire source_node_ok =
        (collective_op == ot_a3_link_pkg::COLL_BROADCAST) ?
            (source_node < NODES) :
            ((source_node == ot_a3_link_pkg::NO_NODE) ||
             (source_node < NODES));
    wire numeric_id_binding_ok =
        (reduction_numeric_id != ot_a3_link_pkg::NO_ID) &&
        (numeric_descriptor_id == reduction_numeric_id);
    wire numeric_order_binding_ok =
        numeric_reduction_order == numeric_decoded_reduction_order;
    wire algorithm_legal =
        (algorithm == ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING) ||
        (algorithm == ot_a3_link_pkg::ALG_HALVING_DOUBLING);
    wire sum_order_supported = (collective_op != ot_a3_link_pkg::COLL_SUM) ||
        is_barrier ||
        ((algorithm == ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING &&
          numeric_decoded_reduction_order ==
              ot_a3_link_pkg::ORDER_PAIRWISE_TREE) ||
         (algorithm == ot_a3_link_pkg::ALG_HALVING_DOUBLING &&
          numeric_decoded_reduction_order ==
              ot_a3_link_pkg::ORDER_BLOCKED_ASCENDING &&
          NODES == 16));
    wire shard_geometry_ok =
        (algorithm != ot_a3_link_pkg::ALG_HALVING_DOUBLING) ||
        !is_reduction ||
        ((VEC_LEN >= NODES) && ((VEC_LEN % NODES) == 0));
    wire command_metadata_ok =
        (flags == 32'd0) &&
        (numeric_profile_id == ot_a3_link_pkg::NO_ID) &&
        (schedule_id == ot_a3_link_pkg::NO_ID) &&
        (permissions == 32'd0) &&
        (owner_scope_id == 32'd0) &&
        (ordering == ot_a3_link_pkg::ORDERING_NONE) &&
        (virtual_channel == 8'd0) &&
        (destination_node == ot_a3_link_pkg::NO_NODE) &&
        (route_class == 32'd0) &&
        (completion_event_id == ot_a3_link_pkg::NO_ID) &&
        (counter_class_id == ot_a3_link_pkg::NO_ID) &&
        (!is_barrier ||
         ((primary_object_id == ot_a3_link_pkg::NO_ID) &&
          (secondary_object_id == ot_a3_link_pkg::NO_ID) &&
          (local_object_id == ot_a3_link_pkg::NO_ID) &&
          (remote_object_id == ot_a3_link_pkg::NO_ID) &&
          (reduction_numeric_id == ot_a3_link_pkg::NO_ID) &&
          (chunk_bytes == 32'd0)));

    always @* begin
        if (record_reason != ot_a3_link_pkg::COMM_REFUSE_NONE)
            refusal_reason = record_reason;
        else if (!CONFIG_SUPPORTED)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_CONFIGURATION;
        else if (!subopcode_supported || !subopcode_op_agrees)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_SUBOPCODE;
        else if (integrity_mode != ot_a3_link_pkg::INTEGRITY_CRC32C)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_INTEGRITY_SUPPORT;
        else if (virtual_channel >= VIRTUAL_CHANNEL_COUNT)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_VIRTUAL_CHANNEL;
        else if (credit_bound != CREDITS)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_CREDIT_BOUND;
        else if (retry_bound != RETRY_MAX)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_RETRY_BOUND;
        else if (timeout_class != TIMEOUT_CLASS)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_TIMEOUT_CLASS;
        else if (participant_scope != ot_a3_link_pkg::PARTICIPANT_NODE)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_SCOPE_SUPPORT;
        else if (group_id != ot_a3_link_pkg::NO_ID)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_GROUP_SUPPORT;
        else if ((participant_count != NODES) || (participant_count < 2))
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_PARTICIPANTS;
        else if (!object_binding_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_OBJECT_BINDING;
        else if (!source_node_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_SOURCE_NODE;
        else if (!supported_op)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_UNSUPPORTED_OP;
        else if (is_barrier && (byte_extent != 64'd0))
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_BARRIER_EXTENT;
        else if (!is_barrier && (byte_extent != DATA_CAPACITY_BYTES))
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_DATA_EXTENT;
        else if (!is_barrier && (chunk_bytes != 32'd4))
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_CHUNK_BYTES;
        else if (!is_barrier &&
                 ((local_offset != 64'd0) || (remote_offset != 64'd0)))
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_DATA_OFFSET;
        else if (!command_metadata_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_CONTROL_METADATA;
        else if (is_reduction && !is_barrier && !numeric_id_binding_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_NUMERIC_BINDING;
        else if (is_reduction && !is_barrier && !numeric_record_valid)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_NUMERIC_RECORD;
        else if (is_reduction && !is_barrier &&
                 !numeric_semantics_supported)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_NUMERIC_SEMANTICS;
        else if (is_reduction && !is_barrier && !numeric_order_binding_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_NUMERIC_BINDING;
        else if (!algorithm_legal && !is_barrier)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_ALGORITHM;
        else if (!sum_order_supported)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_REDUCTION_ORDER;
        else if (!shard_geometry_ok)
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_SHARD_GEOMETRY;
        else
            refusal_reason = ot_a3_link_pkg::COMM_REFUSE_NONE;
    end

    assign command_admitted =
        refusal_reason == ot_a3_link_pkg::COMM_REFUSE_NONE;
    assign trap_class = command_admitted ? 16'd0 :
                        ot_a3_link_pkg::TRAP_LINK_OR_NOC;
    assign engine_reduction_order = numeric_decoded_reduction_order;

    integer root_rank;
    always @* begin
        engine_op = is_barrier ? ENGINE_BARRIER : collective_op;
        engine_root_x = 4'd0;
        engine_root_y = 4'd0;
        if ((collective_op == ot_a3_link_pkg::COLL_BROADCAST) &&
            source_node_ok) begin
            root_rank = source_node;
            engine_root_x = root_rank % MESH_X;
            engine_root_y = root_rank / MESH_X;
        end else begin
            root_rank = 0;
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (!CONFIG_SUPPORTED)
            $error("ot_a3_communication_decoder: unsupported elaboration parameters");
    end
`endif
endmodule
