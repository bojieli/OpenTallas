`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// RE8: the 8-leaf binary32 pairwise-tree endpoint
// (docs/CHIP_ARCHITECTURE_DESIGN.md sections 4.3 item 2 and 4.4 "The tree";
// RTL module order 11.4 item 2).
//
// The K-block tree of the adopted association combines the block partials
// P_0 .. P_{B-1} of one output element by ReductionOrder.PAIRWISE_TREE over
// ascending block index, exactly as runtime/sim/engines/reduction.py folds
// them:
//
//     while more than one node:
//         node i <- RNE32(node 2i + node 2i+1)      one binary32 RNE add each
//         an odd tail is carried unchanged            (a mux, not an add)
//
// This endpoint executes three consecutive levels of that recurrence over
// one ALIGNED group of at most LEAVES = 8 consecutive nodes: with m valid
// leaves (leaves [0, m) a contiguous prefix in ascending index) it folds
// m -> ceil(m/2) -> ceil(ceil(m/2)/2) -> 1 with the odd-tail carry at every
// level, so m = 1 passes the leaf through, m = 4 finishes at level 2 and
// carries through level 3, and m = 8 performs 4 + 2 + 1 adds.  Endpoints are
// chained as the tree: stage s splits the previous stage's n nodes into
// ceil(n / 8) aligned groups, one endpoint each, and the endpoint outputs in
// ascending group index are the next stage's nodes.  Because the recurrence
// pairs indices (2i, 2i+1) and carries only the last element, node j after
// three levels depends only on leaves 8j .. 8j+7 with the carry rule applied
// inside the last group, so the chained endpoints are bit-identical to the
// flat recurrence (tools/am_e1_lane_reference.py::re8_chain asserts it against
// pairwise_tree, which is asserted against reduction.ordered_sum).
// K = 4,096 (32 leaves): stage 1 [8, 8, 8, 8], stage 2 [4] -- 5 endpoints,
// 31 adds.  K = 12,288 (96 leaves): 12 x [8], then [8, 4], then [2] -- 15
// endpoints, 95 adds, the design's 12 -> 6 -> 3 -> 2 -> 1.
//
// The adder is the lane's (rtl/abi3/ot_a3_lane_pkg.sv acc_align /
// acc_sum_normalise / acc_round_pack, the cut that closed at 6.0 ns asap7 in
// the routed lane), with the right operand presented in the lane's group
// form: a 24-bit significand normalised to bit 47 and a power such that
// value = mag * 2**pow -- an exact shift, so every add is one binary32 RNE of
// the exact sum with subnormals kept.  Both operands are canonical: a -0.0
// leaf is canonicalised to +0.0 at the input (no lane partial is ever -0.0;
// reduction.py would carry a -0.0 tail as -0.0, and that is the only case in
// which this endpoint and numpy could differ, so the reference refuses it).
//
// Pipeline: unpack (1) + 3 levels x ADDER_STAGES + pack (1) cycles; one leaf
// vector (one column) accepted per cycle, outputs in input order.
//
// Faults, sticky and fail-closed (classes from ot_a3_lane_pkg, details of
// this module): a valid leaf with exponent field 0xff (NaN / infinity) ->
// DETAIL_TREE_LEAF_NONFINITE, class ERR_OPERAND_NONFINITE; an add whose
// rounded result would reach 2**128 -> DETAIL_TREE_ADD_RANGE, class
// ERR_ACCUMULATE_RANGE; in_leaf_count 0 or above LEAVES ->
// DETAIL_TREE_LEAF_COUNT, class ERR_SHAPE.  A fault travels with its vector
// and commits at the output stage in input order: every vector before it
// has been emitted, the faulting vector and everything after it emit
// nothing, error_* hold (class, detail, level 0 = leaf / 1..3 = tree level,
// tag) until clear, and input is ignored until clear.  Both numeric faults
// are trap 6 at the engine, as reduction.py's np.seterr(over="raise") and
// narrow() make them.
//
// Package constants are referred to by scope, never by wildcard import (OI-43).
// ---------------------------------------------------------------------------
module ot_a3_tree_endpoint_fp32 #(
    parameter integer LEAVES       = 8,   // a power of two; the design's endpoint is 8
    parameter integer ADDER_STAGES = 3,   // L: register stages per tree level (1, 2 or 3)
    parameter integer TAG_W        = 16
) (
    input  wire                 clk,
    input  wire                 rst_n,

    input  wire                 in_valid,
    input  wire [3:0]           in_leaf_count,   // 1 .. LEAVES, leaves [0, count) valid
    input  wire [32*LEAVES-1:0] in_leaf,         // leaf k at [32 k +: 32], ascending block index
    input  wire [TAG_W-1:0]     in_tag,          // column / pass identifier, returned with the result
    input  wire                 in_last,
    input  wire                 clear,           // restart after a fault

    output reg                  out_valid,
    output reg  [31:0]          out_data,
    output reg  [TAG_W-1:0]     out_tag,
    output reg                  out_last,

    output reg  [7:0]           error_code,      // ot_a3_lane_pkg class
    output reg  [7:0]           error_detail,    // DETAIL_TREE_*
    output reg  [1:0]           error_level,     // 0: leaf, 1..3: tree level
    output reg  [TAG_W-1:0]     error_tag,
    output wire                 busy,            // a vector is in flight
    output reg  [31:0]          adds_count,      // binary32 adds retired (m - 1 per committed vector)
    output reg  [31:0]          combines_count   // vectors committed
);
    localparam integer L      = ADDER_STAGES;
    localparam integer LEVELS = (LEAVES > 8) ? 4 : ((LEAVES > 4) ? 3 : ((LEAVES > 2) ? 2 : 1));
    localparam integer NODES  = LEAVES - 1;              // adders over all levels
    localparam integer CNT_W  = 4;

    localparam [7:0] ERR_NONE              = ot_a3_lane_pkg::ERR_NONE;
    localparam [7:0] ERR_OPERAND_NONFINITE = ot_a3_lane_pkg::ERR_OPERAND_NONFINITE;
    localparam [7:0] ERR_ACCUMULATE_RANGE  = ot_a3_lane_pkg::ERR_ACCUMULATE_RANGE;
    localparam [7:0] ERR_SHAPE             = ot_a3_lane_pkg::ERR_SHAPE;
    localparam [7:0] DETAIL_NONE           = ot_a3_lane_pkg::DETAIL_NONE;
    // Tree details start at 24: 0..12 are the lane's, 16..17 the LQ8's, 18..23 the tile's.
    localparam [7:0] DETAIL_TREE_LEAF_NONFINITE = 8'd24;
    localparam [7:0] DETAIL_TREE_ADD_RANGE      = 8'd25;
    localparam [7:0] DETAIL_TREE_LEAF_COUNT     = 8'd26;

    // Elaboration-time guards.
    generate
        if ((LEAVES != 2) && (LEAVES != 4) && (LEAVES != 8) && (LEAVES != 16)) begin : gen_bad_leaves
            initial $error("ot_a3_tree_endpoint_fp32: LEAVES must be 2, 4, 8 or 16");
        end
        if ((ADDER_STAGES < 1) || (ADDER_STAGES > 3)) begin : gen_bad_stages
            initial $error("ot_a3_tree_endpoint_fp32: ADDER_STAGES must be 1, 2 or 3");
        end
    endgenerate

    // -- token: {valid, last, tag, detail, level, adds, add mask} -------------------
    //    The add mask has one bit per adder over all levels, level lv's nodes
    //    at [MASK_OFF(lv) +: LEAVES >> (lv + 1)]: set when that node adds two
    //    valid inputs, clear when it carries its left input (or is absent).
    localparam integer TOKEN_BITS = 1 + 1 + TAG_W + 8 + 2 + CNT_W + NODES;

    function automatic integer mask_off;
        input integer level;
        begin
            mask_off = LEAVES - (LEAVES >> level);
        end
    endfunction

    function automatic [TOKEN_BITS-1:0] make_token;
        input             valid;
        input             last;
        input [TAG_W-1:0] tag;
        input [7:0]       detail;
        input [1:0]       level;
        input [CNT_W-1:0] adds;
        input [NODES-1:0] mask;
        begin
            make_token = {valid, last, tag, detail, level, adds, mask};
        end
    endfunction
    function automatic token_valid;
        input [TOKEN_BITS-1:0] token;
        begin token_valid = token[TOKEN_BITS-1]; end
    endfunction
    function automatic token_last;
        input [TOKEN_BITS-1:0] token;
        begin token_last = token[TOKEN_BITS-2]; end
    endfunction
    function automatic [TAG_W-1:0] token_tag;
        input [TOKEN_BITS-1:0] token;
        begin token_tag = token[TOKEN_BITS-3 -: TAG_W]; end
    endfunction
    function automatic [7:0] token_detail;
        input [TOKEN_BITS-1:0] token;
        begin token_detail = token[NODES+CNT_W+2 +: 8]; end
    endfunction
    function automatic [1:0] token_level;
        input [TOKEN_BITS-1:0] token;
        begin token_level = token[NODES+CNT_W +: 2]; end
    endfunction
    function automatic [CNT_W-1:0] token_adds;
        input [TOKEN_BITS-1:0] token;
        begin token_adds = token[NODES +: CNT_W]; end
    endfunction
    function automatic [NODES-1:0] token_mask;
        input [TOKEN_BITS-1:0] token;
        begin token_mask = token[NODES-1:0]; end
    endfunction
    // Merge a level's range faults into the token leaving that level.
    function automatic [TOKEN_BITS-1:0] token_with_range;
        input [TOKEN_BITS-1:0] token;
        input                  range_fault;
        input [1:0]            level;
        begin
            token_with_range = token;
            if (range_fault && (token_detail(token) == DETAIL_NONE)) begin
                token_with_range[NODES+CNT_W+2 +: 8] = DETAIL_TREE_ADD_RANGE;
                token_with_range[NODES+CNT_W +: 2] = level;
            end
        end
    endfunction

    // -- a binary32 node in the lane adder's group form ----------------------------
    //    {zero, sign, mag[47:0], pow[11:0]}: value = mag * 2**pow with the
    //    leading one of mag at bit 47.  Normals: mag = significand << 24,
    //    pow = exponent - 174; subnormals are normalised by their leading
    //    zero count.  Exact (a shift); zero is canonical positive.
    function automatic [61:0] code_to_group;
        input [31:0] code;
        reg [7:0]  e;
        reg [23:0] m;
        reg        zero;
        reg        sign;
        reg [47:0] mag;
        integer    pow;
        integer    lz;
        begin
            e = code[30:23];
            m = (e == 8'h00) ? {1'b0, code[22:0]} : {1'b1, code[22:0]};
            zero = (m == 24'b0);
            sign = zero ? 1'b0 : code[31];
            pow = (e == 8'h00) ? -149 : ({24'b0, e} - 150);
            lz = zero ? 0 : (47 - ot_a3_lane_pkg::msb24(m));
            mag = zero ? 48'b0 : ({24'b0, m} << lz);
            pow = zero ? 0 : (pow - lz);
            code_to_group = {zero, sign, mag, pow[11:0]};
        end
    endfunction

    // -- unpack (combinational on the inputs) ----------------------------------------
    reg               faulted;
    wire              count_ok = (in_leaf_count != 4'd0) && ({28'b0, in_leaf_count} <= LEAVES);
    wire              accept   = in_valid && !faulted;

    // Per-level valid node counts and the add mask, from the leaf count.
    reg [NODES-1:0]   u_mask;
    reg [CNT_W-1:0]   u_adds;
    integer           um_level, um_node, um_count;
    always @* begin
        u_mask = {NODES{1'b0}};
        um_count = count_ok ? {28'b0, in_leaf_count} : 0;
        for (um_level = 0; um_level < LEVELS; um_level = um_level + 1) begin
            for (um_node = 0; um_node < (LEAVES >> (um_level + 1)); um_node = um_node + 1)
                u_mask[mask_off(um_level) + um_node] = ((2 * um_node + 1) < um_count);
            um_count = (um_count + 1) >> 1;
        end
        u_adds = count_ok ? (in_leaf_count - 4'd1) : 4'd0;
    end

    // Leaf unpack: one register per leaf (gen_leaf[k]); an invalid leaf is
    // +0.0, a -0.0 leaf is canonicalised, a nonfinite valid leaf is flagged.
    wire [32*LEAVES-1:0] leaf_code;        // unpacked, registered leaves = level-0 nodes
    wire [LEAVES-1:0]    leaf_nonfinite_r;
    genvar gk;
    generate
        for (gk = 0; gk < LEAVES; gk = gk + 1) begin : gen_leaf
            wire        leaf_valid = count_ok && (gk < {28'b0, in_leaf_count});
            wire [31:0] raw        = in_leaf[32*gk +: 32];
            wire        nonfinite  = leaf_valid && (raw[30:23] == 8'hff);
            wire [31:0] canonical  = (!leaf_valid || nonfinite || (raw[30:0] == 31'b0)) ? 32'b0 : raw;
            reg  [31:0] leaf_r;
            reg         nonfinite_r;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    leaf_r <= 32'b0;
                    nonfinite_r <= 1'b0;
                end else begin
                    leaf_r <= accept ? canonical : 32'b0;
                    nonfinite_r <= accept && nonfinite;
                end
            end
            assign leaf_code[32*gk +: 32] = leaf_r;
            assign leaf_nonfinite_r[gk]   = nonfinite_r;
        end
    endgenerate

    // The unpack-stage token; its leaf faults are decided from the registered flags.
    reg  [TOKEN_BITS-1:0] tok_u;
    wire [7:0] u_detail = (token_detail(tok_u) != DETAIL_NONE) ? token_detail(tok_u)
                        : ((|leaf_nonfinite_r) ? DETAIL_TREE_LEAF_NONFINITE : DETAIL_NONE);
    wire [TOKEN_BITS-1:0] tok_u_final = make_token(token_valid(tok_u), token_last(tok_u),
                                                   token_tag(tok_u), u_detail, 2'd0,
                                                   token_adds(tok_u), token_mask(tok_u));

    // -- the tree: LEVELS levels of adders, L register stages each -------------------
    //    node_code holds every level's nodes: level lv's node n at
    //    [32 * (LEAVES * lv + n) +: 32]; level 0 is the leaves.
    wire [32*LEAVES*(LEVELS+1)-1:0] node_code;
    wire [NODES-1:0]                node_range;    // an add at that node overflowed
    reg  [TOKEN_BITS-1:0]           tok_pipe [0:LEVELS*L-1];
    wire [TOKEN_BITS*(LEVELS+1)-1:0] level_tok;   // token entering each level; [LEVELS] leaves the tree

    assign node_code[32*LEAVES-1:0] = leaf_code;
    assign level_tok[TOKEN_BITS-1:0] = tok_u_final;

    genvar glv, gnd;
    generate
        for (glv = 0; glv < LEVELS; glv = glv + 1) begin : gen_level
            localparam integer NODES_HERE = LEAVES >> (glv + 1);
            localparam integer OFF        = LEAVES - (LEAVES >> glv);
            localparam [1:0]      LEVEL_ID   = glv + 1;
            wire [TOKEN_BITS-1:0] tok_out    = tok_pipe[glv*L + L - 1];
            wire [NODES-1:0]      mask_out   = token_mask(tok_out);
            wire                  range_here = |(node_range[OFF +: NODES_HERE] & mask_out[OFF +: NODES_HERE]);
            assign level_tok[TOKEN_BITS*(glv+1) +: TOKEN_BITS] =
                token_with_range(tok_out, range_here, LEVEL_ID);
            for (gnd = 0; gnd < NODES_HERE; gnd = gnd + 1) begin : gen_node
                wire [31:0]  left  = node_code[32*(LEAVES*glv + 2*gnd) +: 32];
                wire [31:0]  right = node_code[32*(LEAVES*glv + 2*gnd + 1) +: 32];
                wire [61:0]  rg    = code_to_group(right);
                wire [118:0] piece1 = ot_a3_lane_pkg::acc_align(left, rg[61], rg[60], rg[59:12], rg[11:0]);
                wire [31:0]  add_code;
                wire [1:0]   add_error;
                reg  [31:0]  carry [0:L-1];        // the left input, delayed L, for the carry mux
                integer      ci;
                always @(posedge clk) begin
                    carry[0] <= left;
                    for (ci = 1; ci < L; ci = ci + 1)
                        carry[ci] <= carry[ci-1];
                end
                if (L >= 3) begin : gen_l3
                    reg [118:0] r1;
                    reg [65:0]  r2;
                    reg [33:0]  r3;
                    always @(posedge clk) begin
                        r1 <= piece1;
                        r2 <= ot_a3_lane_pkg::acc_sum_normalise(r1);
                        r3 <= ot_a3_lane_pkg::acc_round_pack(r2);
                    end
                    assign add_code = r3[31:0];
                    assign add_error = r3[33:32];
                end else if (L == 2) begin : gen_l2
                    reg [118:0] r1;
                    reg [33:0]  r2;
                    always @(posedge clk) begin
                        r1 <= piece1;
                        r2 <= ot_a3_lane_pkg::acc_round_pack(
                                  ot_a3_lane_pkg::acc_sum_normalise(r1));
                    end
                    assign add_code = r2[31:0];
                    assign add_error = r2[33:32];
                end else begin : gen_l1
                    reg [33:0] r1;
                    always @(posedge clk) begin
                        r1 <= ot_a3_lane_pkg::acc_round_pack(
                                  ot_a3_lane_pkg::acc_sum_normalise(piece1));
                    end
                    assign add_code = r1[31:0];
                    assign add_error = r1[33:32];
                end
                // The carry is a mux, never an add with zero.
                wire is_add = mask_out[OFF + gnd];
                assign node_code[32*(LEAVES*(glv+1) + gnd) +: 32] = is_add ? add_code : carry[L-1];
                assign node_range[OFF + gnd] = (add_error != 2'd0);
            end
            // Absent nodes of the next level (indices >= NODES_HERE) are +0.0.
            if (NODES_HERE < LEAVES) begin : gen_absent
                assign node_code[32*(LEAVES*(glv+1) + LEAVES) - 1 : 32*(LEAVES*(glv+1) + NODES_HERE)] =
                    {(32*(LEAVES - NODES_HERE)){1'b0}};
            end
        end
    endgenerate

    wire [TOKEN_BITS-1:0] tok_root  = level_tok[TOKEN_BITS*LEVELS +: TOKEN_BITS];
    wire [31:0]           root_code = node_code[32*LEAVES*LEVELS +: 32];

    // -- busy: any token in flight from unpack to the last level -------------------
    reg  busy_r;
    integer bi;
    always @* begin
        busy_r = token_valid(tok_u);
        for (bi = 0; bi < LEVELS*L; bi = bi + 1)
            busy_r = busy_r | token_valid(tok_pipe[bi]);
    end
    assign busy = busy_r;

    // -- sequential: token pipeline, output stage, sticky fault --------------------
    integer si, sl;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            faulted <= 1'b0;
            tok_u <= {TOKEN_BITS{1'b0}};
            for (si = 0; si < LEVELS*L; si = si + 1)
                tok_pipe[si] <= {TOKEN_BITS{1'b0}};
            out_valid <= 1'b0;
            out_data <= 32'b0;
            out_tag <= {TAG_W{1'b0}};
            out_last <= 1'b0;
            error_code <= ERR_NONE;
            error_detail <= DETAIL_NONE;
            error_level <= 2'd0;
            error_tag <= {TAG_W{1'b0}};
            adds_count <= 32'b0;
            combines_count <= 32'b0;
        end else begin
            // Advance.
            tok_u <= make_token(accept, in_last, in_tag,
                                (accept && !count_ok) ? DETAIL_TREE_LEAF_COUNT : DETAIL_NONE,
                                2'd0, u_adds, u_mask);
            for (sl = 0; sl < LEVELS; sl = sl + 1) begin
                tok_pipe[sl*L] <= level_tok[TOKEN_BITS*sl +: TOKEN_BITS];
                for (si = 1; si < L; si = si + 1)
                    tok_pipe[sl*L + si] <= tok_pipe[sl*L + si - 1];
            end

            // Output stage: commit in input order.
            out_valid <= 1'b0;
            if (token_valid(tok_root) && !faulted) begin
                if (token_detail(tok_root) != DETAIL_NONE) begin
                    faulted <= 1'b1;
                    error_detail <= token_detail(tok_root);
                    error_level <= token_level(tok_root);
                    error_tag <= token_tag(tok_root);
                    case (token_detail(tok_root))
                        DETAIL_TREE_LEAF_NONFINITE: error_code <= ERR_OPERAND_NONFINITE;
                        DETAIL_TREE_ADD_RANGE:      error_code <= ERR_ACCUMULATE_RANGE;
                        default:                    error_code <= ERR_SHAPE;
                    endcase
                    // Everything behind the faulting vector is dropped.
                    tok_u <= {TOKEN_BITS{1'b0}};
                    for (si = 0; si < LEVELS*L; si = si + 1)
                        tok_pipe[si] <= {TOKEN_BITS{1'b0}};
                end else begin
                    out_valid <= 1'b1;
                    out_data <= root_code;
                    out_tag <= token_tag(tok_root);
                    out_last <= token_last(tok_root);
                    adds_count <= adds_count + {28'b0, token_adds(tok_root)};
                    combines_count <= combines_count + 32'd1;
                end
            end

            if (clear) begin
                faulted <= 1'b0;
                error_code <= ERR_NONE;
                error_detail <= DETAIL_NONE;
                error_level <= 2'd0;
                error_tag <= {TAG_W{1'b0}};
                out_valid <= 1'b0;
                tok_u <= {TOKEN_BITS{1'b0}};
                for (si = 0; si < LEVELS*L; si = si + 1)
                    tok_pipe[si] <= {TOKEN_BITS{1'b0}};
            end
        end
    end
endmodule
