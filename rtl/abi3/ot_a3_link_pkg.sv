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

    // -- spec/abi3/registries.json : reduction_orders ------------------------
    localparam [7:0] ORDER_SEQUENTIAL_ASCENDING = 8'd0;
    localparam [7:0] ORDER_PAIRWISE_TREE        = 8'd1;
    localparam [7:0] ORDER_BLOCKED_ASCENDING    = 8'd2;

    // -- spec/abi3/registries.json : topology_classes ------------------------
    localparam [7:0] TOPOLOGY_SINGLE_CHIP          = 8'd0;
    localparam [7:0] TOPOLOGY_CLUSTER_32           = 8'd1;
    localparam [7:0] TOPOLOGY_WAFER_LOGICAL_DEVICE = 8'd2;

    // -- spec/abi3/registries.json : trap_classes ----------------------------
    // Class 11 is LINK_OR_NOC; every fail-closed exit in this fabric raises it.
    localparam [15:0] TRAP_LINK_OR_NOC = 16'd11;

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
            fp32_max = (fp32_order_key(a) >= fp32_order_key(b)) ? a : b;
        end
    endfunction

    function automatic [31:0] fp32_min;
        input [31:0] a;
        input [31:0] b;
        begin
            fp32_min = (fp32_order_key(a) <= fp32_order_key(b)) ? a : b;
        end
    endfunction

endpackage
