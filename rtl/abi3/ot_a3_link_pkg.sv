`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 inter-chip link: shared encodings.
//
// Every constant here transcribes a frozen ABI 3.0 registry
// (`spec/abi3/registries.json`) or a frozen descriptor payload field
// (`spec/abi3/descriptor_payloads.json` -> COMMUNICATION).  Nothing in this
// package is a local invention; where the RTL needs a value the ABI does not
// name -- the on-wire flit layout -- the field is declared here so that no
// block can quietly choose a different one.
//
// WHAT THIS PACKAGE IS NOT: it carries no timing.  A flit is one cycle wide on
// this fabric by construction; how many picoseconds that cycle is, and how far
// a hop physically reaches, are outside every module in this directory.
// ---------------------------------------------------------------------------
package ot_a3_link_pkg;

    // -- Common descriptor header ------------------------------------------
    // The ABI itself is version 3.0.  Typed descriptors have their own
    // independently versioned payload contract, currently 1.0.
    localparam [31:0] DESCRIPTOR_MAGIC       = 32'h4433_4154; // "TA3D", LE
    localparam [15:0] DESC_COMMUNICATION     = 16'h0006;
    localparam [15:0] DESC_NUMERIC           = 16'h0003;
    localparam [7:0]  DESCRIPTOR_TYPE_MAJOR = 8'd1;
    localparam [7:0]  DESCRIPTOR_TYPE_MINOR = 8'd0;
    localparam [31:0] DESCRIPTOR_TOTAL_BYTES = 32'd192;
    localparam [31:0] DESCRIPTOR_PAYLOAD_OFFSET = 32'd64;
    localparam [31:0] COMMUNICATION_PAYLOAD_BYTES = 32'd128;
    localparam [31:0] NUMERIC_TOTAL_BYTES    = 32'd128;
    localparam [31:0] NUMERIC_PAYLOAD_BYTES  = 32'd64;
    localparam [31:0] NO_ID = 32'hffff_ffff;
    localparam [15:0] NO_NODE = 16'hffff;

    // -- spec/abi3/registries.json : collective_ops --------------------------
    localparam [7:0] COLL_POINT_TO_POINT = 8'd0;
    localparam [7:0] COLL_SUM            = 8'd1;
    localparam [7:0] COLL_MAX            = 8'd2;
    localparam [7:0] COLL_MIN            = 8'd3;
    localparam [7:0] COLL_CONCAT         = 8'd4;
    localparam [7:0] COLL_BROADCAST      = 8'd5;
    localparam [7:0] COLL_ALL_GATHER     = 8'd6;
    localparam [7:0] COLL_REDUCE_SCATTER = 8'd7;

    // -- spec/abi3/registries.json : integrity_modes -------------------------
    localparam [7:0] INTEGRITY_NONE        = 8'd0;
    localparam [7:0] INTEGRITY_CRC32C      = 8'd1;
    localparam [7:0] INTEGRITY_ECC         = 8'd2;
    localparam [7:0] INTEGRITY_CRC_AND_ECC = 8'd3;

    // -- spec/abi3/registries.json : ordering -------------------------------
    localparam [7:0] ORDERING_NONE            = 8'd0;
    localparam [7:0] ORDERING_ACQUIRE         = 8'd1;
    localparam [7:0] ORDERING_RELEASE         = 8'd2;
    localparam [7:0] ORDERING_ACQUIRE_RELEASE = 8'd3;
    localparam [7:0] ORDERING_SEQUENTIAL      = 8'd4;

    // -- spec/abi3/registries.json : participant_scopes ---------------------
    localparam [7:0] PARTICIPANT_NODE     = 8'd0;
    localparam [7:0] PARTICIPANT_RETICLE = 8'd1;
    localparam [7:0] PARTICIPANT_TILE     = 8'd2;

    // -- spec/abi3/registries.json : LINK subopcodes ------------------------
    localparam [7:0] LINK_SEND       = 8'd0;
    localparam [7:0] LINK_RECEIVE    = 8'd1;
    localparam [7:0] LINK_REMOTE_DMA = 8'd2;
    localparam [7:0] LINK_MULTICAST  = 8'd3;
    localparam [7:0] LINK_GATHER     = 8'd4;
    localparam [7:0] LINK_SCATTER    = 8'd5;
    localparam [7:0] LINK_COLLECTIVE = 8'd6;
    localparam [7:0] LINK_BARRIER    = 8'd7;

    // -- spec/abi3/registries.json : reduction_orders ------------------------
    localparam [7:0] ORDER_SEQUENTIAL_ASCENDING = 8'd0;
    localparam [7:0] ORDER_PAIRWISE_TREE        = 8'd1;
    localparam [7:0] ORDER_BLOCKED_ASCENDING    = 8'd2;

    // -- spec/abi3/registries.json : dtypes / rounding_modes ---------------
    localparam [7:0] DTYPE_U8         = 8'h00;
    localparam [7:0] DTYPE_I8         = 8'h01;
    localparam [7:0] DTYPE_U16        = 8'h02;
    localparam [7:0] DTYPE_I16        = 8'h03;
    localparam [7:0] DTYPE_U32        = 8'h04;
    localparam [7:0] DTYPE_I32        = 8'h05;
    localparam [7:0] DTYPE_U64        = 8'h06;
    localparam [7:0] DTYPE_I64        = 8'h07;
    localparam [7:0] DTYPE_BF16       = 8'h10;
    localparam [7:0] DTYPE_FP16       = 8'h11;
    localparam [7:0] DTYPE_FP32       = 8'h12;
    localparam [7:0] DTYPE_FP64       = 8'h13;
    localparam [7:0] DTYPE_FP8_E4M3FN = 8'h20;
    localparam [7:0] DTYPE_FP8_E5M2   = 8'h21;
    localparam [7:0] DTYPE_MXFP4_E2M1 = 8'h30;
    localparam [7:0] DTYPE_E8M0_SCALE = 8'h31;
    localparam [7:0] DTYPE_FP4_E2M1_S16_E4M3 = 8'h32;
    localparam [7:0] ROUND_NEAREST_EVEN = 8'd0;
    localparam [7:0] ROUND_TOWARD_ZERO  = 8'd1;
    localparam [7:0] ROUND_STOCHASTIC   = 8'd2;

    // -- spec/abi3/registries.json : topology_classes ------------------------
    localparam [7:0] TOPOLOGY_SINGLE_CHIP          = 8'd0;
    localparam [7:0] TOPOLOGY_CLUSTER_32           = 8'd1;
    localparam [7:0] TOPOLOGY_WAFER_LOGICAL_DEVICE = 8'd2;

    // -- spec/abi3/registries.json : trap_classes ----------------------------
    localparam [15:0] TRAP_NUMERIC_OR_EXCEPTIONAL_VALUE = 16'd6;
    localparam [15:0] TRAP_LINK_OR_NOC = 16'd11;

    // -- COMMUNICATION decoder refusal reasons -----------------------------
    // These are observability codes for the standalone RTL campaign, not ABI
    // registry values.  Every nonzero reason fails closed with LINK_OR_NOC.
    localparam [7:0] COMM_REFUSE_NONE             = 8'd0;
    localparam [7:0] COMM_REFUSE_MAGIC            = 8'd1;
    localparam [7:0] COMM_REFUSE_TYPE             = 8'd2;
    localparam [7:0] COMM_REFUSE_VERSION          = 8'd3;
    localparam [7:0] COMM_REFUSE_TOTAL_BYTES      = 8'd4;
    localparam [7:0] COMM_REFUSE_PAYLOAD_GEOMETRY = 8'd5;
    localparam [7:0] COMM_REFUSE_HEADER_RESERVED  = 8'd6;
    localparam [7:0] COMM_REFUSE_PAYLOAD_RESERVED = 8'd7;
    localparam [7:0] COMM_REFUSE_RECORD_CRC       = 8'd8;
    localparam [7:0] COMM_REFUSE_PERMISSIONS      = 8'd9;
    localparam [7:0] COMM_REFUSE_COLLECTIVE_OP    = 8'd10;
    localparam [7:0] COMM_REFUSE_ORDERING         = 8'd11;
    localparam [7:0] COMM_REFUSE_INTEGRITY_MODE   = 8'd12;
    localparam [7:0] COMM_REFUSE_PARTICIPANT_SCOPE= 8'd13;
    localparam [7:0] COMM_REFUSE_SUBOPCODE        = 8'd14;
    localparam [7:0] COMM_REFUSE_INTEGRITY_SUPPORT= 8'd15;
    localparam [7:0] COMM_REFUSE_VIRTUAL_CHANNEL  = 8'd16;
    localparam [7:0] COMM_REFUSE_CREDIT_BOUND     = 8'd17;
    localparam [7:0] COMM_REFUSE_RETRY_BOUND      = 8'd18;
    localparam [7:0] COMM_REFUSE_TIMEOUT_CLASS    = 8'd19;
    localparam [7:0] COMM_REFUSE_PARTICIPANTS     = 8'd20;
    localparam [7:0] COMM_REFUSE_OBJECT_BINDING   = 8'd21;
    localparam [7:0] COMM_REFUSE_SOURCE_NODE      = 8'd22;
    localparam [7:0] COMM_REFUSE_NUMERIC_BINDING  = 8'd23;
    localparam [7:0] COMM_REFUSE_REDUCTION_ORDER  = 8'd24;
    localparam [7:0] COMM_REFUSE_ALGORITHM        = 8'd25;
    localparam [7:0] COMM_REFUSE_UNSUPPORTED_OP   = 8'd26;
    localparam [7:0] COMM_REFUSE_BARRIER_EXTENT   = 8'd27;
    localparam [7:0] COMM_REFUSE_SCOPE_SUPPORT    = 8'd28;
    localparam [7:0] COMM_REFUSE_GROUP_SUPPORT    = 8'd29;
    localparam [7:0] COMM_REFUSE_DATA_EXTENT      = 8'd30;
    localparam [7:0] COMM_REFUSE_CHUNK_BYTES      = 8'd31;
    localparam [7:0] COMM_REFUSE_NUMERIC_RECORD   = 8'd32;
    localparam [7:0] COMM_REFUSE_NUMERIC_SEMANTICS= 8'd33;
    localparam [7:0] COMM_REFUSE_CONFIGURATION    = 8'd34;
    localparam [7:0] COMM_REFUSE_DATA_OFFSET      = 8'd35;
    localparam [7:0] COMM_REFUSE_SHARD_GEOMETRY   = 8'd36;
    localparam [7:0] COMM_REFUSE_CONTROL_METADATA = 8'd37;

    // -- The collective algorithm the engine runs ----------------------------
    // These are NOT ABI values.  The ABI names the collective (`collective_op`)
    // and the arithmetic order (`reduction_numeric_id` -> reduction_order); it
    // does not name the fabric algorithm, and the two published choices differ
    // by 2x in traversals and by lg(P)/2 in wire bytes.  The selector is
    // explicit so that a measurement always records which one it measured.
    //
    //   ALG_RECURSIVE_DOUBLING  latency-optimal: lg(P) steps, whole payload
    //                           every step.  Distance walked is exactly the
    //                           mesh diameter.
    //   ALG_HALVING_DOUBLING    bandwidth-optimal (Rabenseifner): recursive-
    //                           halving reduce-scatter then recursive-doubling
    //                           all-gather, 2 lg(P) steps, 2(P-1)/P of the
    //                           payload in total.  Distance walked is exactly
    //                           twice the mesh diameter.
    localparam [1:0] ALG_RECURSIVE_DOUBLING = 2'd0;
    localparam [1:0] ALG_HALVING_DOUBLING   = 2'd1;

    // -- Flit layout ---------------------------------------------------------
    // One flit is one packet on this fabric: dimension-ordered routing over
    // single-flit packets cannot deadlock and needs no virtual channel to stay
    // live, so the endpoint's credit and retry behaviour is observed without a
    // wormhole confound.  Multi-flit messages are sequences of these.
    localparam integer FLIT_PAYLOAD_W = 32;
    localparam integer FLIT_COORD_W   = 4;   // up to a 16 x 16 mesh
    localparam integer FLIT_KIND_W    = 4;
    localparam integer FLIT_TAG_W     = 8;
    localparam integer FLIT_W         = 64;

    // field offsets inside a flit
    localparam integer FLIT_PAYLOAD_LSB = 0;   // [31:0]
    localparam integer FLIT_DEST_X_LSB  = 32;  // [35:32]
    localparam integer FLIT_DEST_Y_LSB  = 36;  // [39:36]
    localparam integer FLIT_SRC_X_LSB   = 40;  // [43:40]
    localparam integer FLIT_SRC_Y_LSB   = 44;  // [47:44]
    localparam integer FLIT_KIND_LSB    = 48;  // [51:48]
    localparam integer FLIT_TAG_LSB     = 52;  // [59:52]
    // [63:60] reserved, transmitted as zero and checked as zero.

    // flit kinds
    localparam [3:0] KIND_UNICAST  = 4'd0;
    localparam [3:0] KIND_EXCHANGE = 4'd1;  // collective step payload
    localparam [3:0] KIND_BARRIER  = 4'd2;
    localparam [3:0] KIND_GATHER   = 4'd3;  // all-gather / broadcast payload

    function automatic [FLIT_W-1:0] flit_pack;
        input [31:0] payload;
        input [3:0]  dest_x;
        input [3:0]  dest_y;
        input [3:0]  src_x;
        input [3:0]  src_y;
        input [3:0]  kind;
        input [7:0]  tag;
        begin
            flit_pack = {4'b0, tag, kind, src_y, src_x, dest_y, dest_x, payload};
        end
    endfunction

    function automatic [31:0] flit_payload;
        input [FLIT_W-1:0] f;
        begin flit_payload = f[31:0]; end
    endfunction

    function automatic [3:0] flit_dest_x;
        input [FLIT_W-1:0] f;
        begin flit_dest_x = f[35:32]; end
    endfunction

    function automatic [3:0] flit_dest_y;
        input [FLIT_W-1:0] f;
        begin flit_dest_y = f[39:36]; end
    endfunction

    function automatic [3:0] flit_src_x;
        input [FLIT_W-1:0] f;
        begin flit_src_x = f[43:40]; end
    endfunction

    function automatic [3:0] flit_src_y;
        input [FLIT_W-1:0] f;
        begin flit_src_y = f[47:44]; end
    endfunction

    function automatic [3:0] flit_kind;
        input [FLIT_W-1:0] f;
        begin flit_kind = f[51:48]; end
    endfunction

    function automatic [7:0] flit_tag;
        input [FLIT_W-1:0] f;
        begin flit_tag = f[59:52]; end
    endfunction

    // -- binary32 ordering ---------------------------------------------------
    // MAX and MIN need a total order over the finite binary32 codes the LINK
    // engine admits.  The monotone map below is the standard sign-magnitude to
    // two's-complement rewrite: it orders every finite code exactly as the
    // real numbers order their values, and it maps the two zeros to the same
    // key so that MAX(-0.0, +0.0) cannot depend on operand order.
    function automatic [31:0] fp32_order_key;
        input [31:0] code;
        reg [31:0] value;
        begin
            value = (code[30:0] == 31'd0) ? 32'h0000_0000 : code;
            fp32_order_key = value[31] ? (~value) : (value | 32'h8000_0000);
        end
    endfunction

    function automatic [31:0] fp32_max;
        input [31:0] a;
        input [31:0] b;
        begin
            if ((a[30:0] == 31'd0) && (b[30:0] == 31'd0))
                fp32_max = 32'h0000_0000;
            else
                fp32_max = (fp32_order_key(a) >= fp32_order_key(b)) ? a : b;
        end
    endfunction

    function automatic [31:0] fp32_min;
        input [31:0] a;
        input [31:0] b;
        begin
            if ((a[30:0] == 31'd0) && (b[30:0] == 31'd0))
                fp32_min = 32'h0000_0000;
            else
                fp32_min = (fp32_order_key(a) <= fp32_order_key(b)) ? a : b;
        end
    endfunction

endpackage
