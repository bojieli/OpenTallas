`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 inter-chip endpoint: the collective engine of one node.
//
// WHY THIS BLOCK EXISTS.  `docs/COMPARISON_FAIRNESS_AUDIT.md` found that both
// sides of the headline comparison now bind on `link_latency`, and that 58% of
// the combined step mass is collective cost.  The analytical model charges a
// collective as `traversals x hop_latency`, with `traversals` = 1.1 x the mesh
// diameter (`src/opentallas/roofline.py`, MESH_ALLREDUCE_DIAMETER_FACTOR).  No
// RTL implemented the collective that number prices.  This does.
//
// WHAT IT IMPLEMENTS.  Two published all-reduce algorithms over a 2-D mesh,
// selected explicitly, because they are NOT interchangeable and the model
// charges the latency of one and the bandwidth of the other:
//
//   ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING  lg(P) steps, partner = rank XOR (1<<k), whole
//                           payload every step.  Distance walked on the mesh is
//                           exactly the diameter.  Latency-optimal; moves
//                           lg(P) x payload per node.
//   ot_a3_link_pkg::ALG_HALVING_DOUBLING    Rabenseifner: recursive-halving reduce-scatter then
//                           recursive-doubling all-gather, 2 lg(P) steps.
//                           Distance walked is exactly twice the diameter.
//                           Bandwidth-optimal; moves 2(P-1)/P x payload.
//
// THE ARITHMETIC ORDER IS THE POINT, NOT A DETAIL.  Both algorithms combine
// partial sums as a balanced binary tree over ASCENDING participant rank, which
// is the frozen registry's `PAIRWISE_TREE` (spec/abi3/registries.json,
// reduction_orders).  Neither can produce `SEQUENTIAL_ASCENDING`: a fabric that
// honours a strictly sequential accumulation must combine along a path that
// visits participants in ascending rank, which on a P-node mesh is Theta(P)
// traversals, not Theta(sqrt(P)).  The engine therefore refuses to run an
// arithmetic collective whose declared reduction order it cannot honour,
// instead of returning different bits and calling it the same collective.
//
// CLAIM BOUNDARY.  This block establishes cycle counts, traversal counts and
// wire-byte counts for these algorithms under this endpoint contract.  It does
// not measure wire delay, it does not know how many seconds a cycle is, and it
// says nothing at all about the delay of a stitched or bonded reticle boundary.
// ---------------------------------------------------------------------------
module ot_a3_collective_engine #(
    parameter integer FLIT_W  = 64,
    parameter integer MESH_X  = 4,
    parameter integer MESH_Y  = 4,
    parameter integer MY_X    = 0,
    parameter integer MY_Y    = 0,
    parameter integer VEC_LEN = 16
) (
    input  wire                  clk,
    input  wire                  rst_n,

    // -- command ------------------------------------------------------------
    input  wire                  start,
    input  wire [7:0]            op,             // ot_a3_link_pkg COLL_*, or OP_BARRIER
    input  wire [1:0]            alg,            // ot_a3_link_pkg ALG_*
    input  wire [7:0]            reduction_order,// ot_a3_link_pkg ORDER_*
    input  wire [3:0]            root_x,
    input  wire [3:0]            root_y,
    output reg                   busy,
    output reg                   done,
    output reg                   trap,
    output reg  [15:0]           trap_class,

    // -- local buffer access (quiescent only) --------------------------------
    input  wire                  load_valid,
    input  wire [7:0]            load_index,
    input  wire [31:0]           load_data,
    input  wire [7:0]            read_index,
    output wire [31:0]           read_data,

    // -- network port --------------------------------------------------------
    output reg                   net_out_valid,
    output reg  [FLIT_W-1:0]     net_out_flit,
    input  wire                  net_out_ready,
    input  wire                  net_in_valid,
    input  wire [FLIT_W-1:0]     net_in_flit,
    output wire                  net_in_ready,

    // -- observation ---------------------------------------------------------
    output reg  [31:0]           steps_taken,
    output reg  [31:0]           flits_sent,
    output reg  [31:0]           flits_received,
    output reg  [31:0]           hop_distance_sent,  // sum of Manhattan hops offered
    output reg  [31:0]           serial_traversals,  // dependent hops on the critical path
    output reg  [31:0]           busy_cycles
);
    // The package is referenced by scope rather than wildcard-imported: a
    // wildcard import is not accepted by every open synthesis front end this
    // program pins, and a block that only elaborates in a simulator is not an
    // implementable block.

    localparam [7:0] OP_BARRIER = 8'hff;   // engine-local; not an ABI collective_op

    localparam integer P     = MESH_X * MESH_Y;
    localparam integer LGX   = (MESH_X <= 1) ? 0 : $clog2(MESH_X);
    localparam integer LGY   = (MESH_Y <= 1) ? 0 : $clog2(MESH_Y);
    localparam integer LG    = LGX + LGY;
    localparam integer MY_RANK = MY_Y * MESH_X + MY_X;
    localparam integer VW    = (VEC_LEN <= 1) ? 1 : $clog2(VEC_LEN);

    // WHY THE PEER BUFFER IS BANKED BY STEP.  Found by measurement, not by
    // review: with a one-cycle hop every node stays in lockstep and a single
    // peer buffer is enough, but at an eight-cycle hop one replayed flit is
    // enough to put a node a whole step behind its neighbours.  A node that has
    // moved on then sends the NEXT step's payload to a partner still finishing
    // the previous one, and a single unbanked buffer accepts it as this step's
    // data.  The result is a wrong all-reduce with no trap, no CRC error and no
    // dropped flit -- the arithmetic is simply different.  Banking the receive
    // buffer by the step tag the flit carries removes the race without a
    // barrier, and without back-pressuring a flit whose step has not arrived
    // yet, which would head-of-line block the shared input port and deadlock.
    localparam integer TAGS = (LG < 1) ? 1 : (2 * LG);
    reg [31:0] acc  [0:VEC_LEN-1];
    reg [31:0] peer [0:TAGS*VEC_LEN-1];
    reg [VW:0] recv_fill [0:TAGS-1];

    assign read_data = acc[read_index[VW-1:0]];

    // -- schedule ------------------------------------------------------------
    // `phase` 0 = the single sweep of recursive doubling, or the reduce-scatter
    // half of halving/doubling; `phase` 1 = the all-gather half.
    reg [3:0]  step;
    reg        phase;
    reg [7:0]  cur_op;
    reg [1:0]  cur_alg;
    reg [3:0]  cur_root_x;
    reg [3:0]  cur_root_y;

    reg [VW:0] blk_lo;
    reg [VW:0] blk_hi;

    reg [VW:0] send_lo;
    reg [VW:0] send_hi;
    reg [VW:0] keep_lo;
    reg [VW:0] keep_hi;
    reg [VW:0] recv_lo;
    reg [VW:0] recv_hi;
    reg        order_low;        // this node holds the lower-rank contribution
    reg        do_send;
    reg        do_recv;

    reg [VW:0] send_idx;
    reg [VW:0] recv_idx;
    reg [VW:0] comb_idx;

    reg [3:0]  peer_x;
    reg [3:0]  peer_y;

    localparam [2:0] S_IDLE = 3'd0, S_SETUP = 3'd1, S_XFER = 3'd2,
                     S_COMBINE = 3'd3, S_ADVANCE = 3'd4, S_DONE = 3'd5,
                     S_TRAP = 3'd6;
    reg [2:0] state;

    integer li;
    integer ti;

    // The step tag a flit carries.  Halving/doubling reuses step indices in its
    // second phase, so the tag is the phase-extended step and never collides.
    wire [7:0] cur_tag = phase ? (LG[7:0] + {4'd0, step}) : {4'd0, step};
    wire [7:0] in_tag = ot_a3_link_pkg::flit_tag(net_in_flit);
    wire in_tag_legal = (in_tag < TAGS[7:0]);

    // A flit is accepted whenever the engine is running.  Back-pressuring a
    // flit whose step has not started here yet would head-of-line block the
    // shared input port of the router and deadlock the mesh.
    assign net_in_ready = busy;

    wire [VW:0] recv_count = recv_hi - recv_lo;
    wire [VW:0] send_count = send_hi - send_lo;
    wire [VW:0] comb_peer_index = (cur_op == ot_a3_link_pkg::COLL_BROADCAST) ? comb_idx :
                                  ((cur_op == ot_a3_link_pkg::COLL_ALL_GATHER) || (phase == 1'b1))
                                      ? comb_idx : (comb_idx - recv_lo);
    wire [31:0] peer_word =
        peer[(cur_tag * VEC_LEN) + {{(32-VW-1){1'b0}}, comb_peer_index}];

    wire [33:0] add_result = ot_fp32_rne_pkg::fp32_add_rne(
        order_low ? acc[comb_idx[VW-1:0]] : peer_word,
        order_low ? peer_word : acc[comb_idx[VW-1:0]]);

    // partner rank for the current step, decomposed onto the mesh
    reg [7:0] peer_rank;
    always @* begin
        peer_rank = MY_RANK[7:0] ^ (8'd1 << step);
        peer_x = peer_rank[3:0] & (MESH_X - 1);
        peer_y = (peer_rank >> LGX) & (MESH_Y - 1);
    end

    wire [3:0] dist_x = (peer_x > MY_X[3:0]) ? (peer_x - MY_X[3:0]) : (MY_X[3:0] - peer_x);
    wire [3:0] dist_y = (peer_y > MY_Y[3:0]) ? (peer_y - MY_Y[3:0]) : (MY_Y[3:0] - peer_y);

    // rank relabelled by the broadcast root: the node whose relabelled rank is
    // zero is the one that starts with the payload.
    wire [7:0] root_rank = {4'b0, cur_root_y} * MESH_X + {4'b0, cur_root_x};
    wire [7:0] rprime = MY_RANK[7:0] ^ root_rank;
    wire bcast_have = (rprime < (8'd1 << step));
    wire bcast_take = ((rprime ^ (8'd1 << step)) < (8'd1 << step));

    wire is_reduction = (cur_op == ot_a3_link_pkg::COLL_SUM) || (cur_op == ot_a3_link_pkg::COLL_MAX) || (cur_op == ot_a3_link_pkg::COLL_MIN);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            trap <= 1'b0;
            trap_class <= 16'd0;
            step <= 4'd0;
            phase <= 1'b0;
            cur_op <= 8'd0;
            cur_alg <= 2'd0;
            cur_root_x <= 4'd0;
            cur_root_y <= 4'd0;
            blk_lo <= 0; blk_hi <= VEC_LEN[VW:0];
            send_lo <= 0; send_hi <= 0;
            keep_lo <= 0; keep_hi <= 0;
            recv_lo <= 0; recv_hi <= 0;
            send_idx <= 0; recv_idx <= 0; comb_idx <= 0;
            order_low <= 1'b0;
            do_send <= 1'b0;
            do_recv <= 1'b0;
            net_out_valid <= 1'b0;
            net_out_flit <= {FLIT_W{1'b0}};
            steps_taken <= 32'd0;
            flits_sent <= 32'd0;
            flits_received <= 32'd0;
            hop_distance_sent <= 32'd0;
            serial_traversals <= 32'd0;
            busy_cycles <= 32'd0;
            for (li = 0; li < VEC_LEN; li = li + 1)
                acc[li] <= 32'd0;
            for (li = 0; li < TAGS*VEC_LEN; li = li + 1)
                peer[li] <= 32'd0;
            for (ti = 0; ti < TAGS; ti = ti + 1)
                recv_fill[ti] <= 0;
        end else begin
            // `trap` and `done` are one-cycle events, not sticky state: the
            // consumer latches them against the command it issued.
            done <= 1'b0;
            trap <= 1'b0;
            if (busy)
                busy_cycles <= busy_cycles + 32'd1;

            if (load_valid && (state == S_IDLE))
                acc[load_index[VW-1:0]] <= load_data;


            case (state)
                S_IDLE: begin
                    net_out_valid <= 1'b0;
                    busy <= 1'b0;
                    if (start) begin
                        trap_class <= 16'd0;
                        cur_op <= op;
                        cur_alg <= alg;
                        cur_root_x <= root_x;
                        cur_root_y <= root_y;
                        // Recursive halving starts at the widest partner and
                        // works inward; every other schedule starts at the
                        // nearest partner and works outward.
                        step <= ((alg == ot_a3_link_pkg::ALG_HALVING_DOUBLING) &&
                                 ((op == ot_a3_link_pkg::COLL_SUM) || (op == ot_a3_link_pkg::COLL_MAX) ||
                                  (op == ot_a3_link_pkg::COLL_MIN)))
                                ? (LG[3:0] - 4'd1) : 4'd0;
                        phase <= 1'b0;
                        blk_lo <= 0;
                        blk_hi <= VEC_LEN[VW:0];
                        busy <= 1'b1;
                        // Every engine counter is per-collective: a campaign
                        // that had to subtract a snapshot could hide a case
                        // that contributed nothing.
                        steps_taken <= 32'd0;
                        serial_traversals <= 32'd0;
                        flits_sent <= 32'd0;
                        flits_received <= 32'd0;
                        hop_distance_sent <= 32'd0;
                        busy_cycles <= 32'd0;
                        for (ti = 0; ti < TAGS; ti = ti + 1)
                            recv_fill[ti] <= 0;
                        // A binary32 SUM may run only under a reduction order
                        // this fabric can actually produce.  MAX and MIN are
                        // associative over the finite codes the LINK engine
                        // admits, so their result does not depend on the
                        // association and any declared order is admissible.
                        //
                        //   ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING folds the LOWEST rank bit
                        //   first, which is the balanced tree over adjacent
                        //   ascending participants -- ot_a3_link_pkg::ORDER_PAIRWISE_TREE.
                        //
                        //   ot_a3_link_pkg::ALG_HALVING_DOUBLING folds the HIGHEST rank bit
                        //   first.  That is a different tree and a different
                        //   binary32 result.  It coincides with
                        //   ot_a3_link_pkg::ORDER_BLOCKED_ASCENDING only at P = 16, because
                        //   that order is defined on eight lanes and eight
                        //   lanes over sixteen terms IS the top-bit-first fold.
                        //   At any other participant count this fabric cannot
                        //   name the order it would produce, so it refuses.
                        if ((op == ot_a3_link_pkg::COLL_SUM) && !(
                                (alg == ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING &&
                                 reduction_order == ot_a3_link_pkg::ORDER_PAIRWISE_TREE) ||
                                (alg == ot_a3_link_pkg::ALG_HALVING_DOUBLING &&
                                 reduction_order == ot_a3_link_pkg::ORDER_BLOCKED_ASCENDING &&
                                 P == 16))) begin
                            trap <= 1'b1;
                            trap_class <= ot_a3_link_pkg::TRAP_LINK_OR_NOC;
                            state <= S_TRAP;
                        end else if (LG == 0) begin
                            state <= S_DONE;
                        end else begin
                            state <= S_SETUP;
                        end
                    end
                end

                S_SETUP: begin
                    send_idx <= 0;
                    recv_idx <= 0;
                    comb_idx <= 0;
                    order_low <= (((MY_RANK[7:0] >> step) & 8'd1) == 8'd0);
                    if (cur_op == OP_BARRIER) begin
                        // one zero-payload flit each way per step
                        send_lo <= 0; send_hi <= 1;
                        keep_lo <= 0; keep_hi <= 0;
                        recv_lo <= 0; recv_hi <= 1;
                        do_send <= 1'b1;
                        do_recv <= 1'b1;
                    end else if (cur_op == ot_a3_link_pkg::COLL_BROADCAST) begin
                        send_lo <= 0; send_hi <= VEC_LEN[VW:0];
                        keep_lo <= 0; keep_hi <= VEC_LEN[VW:0];
                        recv_lo <= 0; recv_hi <= VEC_LEN[VW:0];
                        do_send <= bcast_have;
                        do_recv <= bcast_take;
                    end else if ((cur_alg == ot_a3_link_pkg::ALG_RECURSIVE_DOUBLING) &&
                                 (cur_op != ot_a3_link_pkg::COLL_ALL_GATHER)) begin
                        send_lo <= 0; send_hi <= VEC_LEN[VW:0];
                        keep_lo <= 0; keep_hi <= VEC_LEN[VW:0];
                        recv_lo <= 0; recv_hi <= VEC_LEN[VW:0];
                        do_send <= 1'b1;
                        do_recv <= 1'b1;
                    end else if (phase == 1'b0 && cur_op != ot_a3_link_pkg::COLL_ALL_GATHER) begin
                        // recursive-halving reduce-scatter: give away the half
                        // of the block the partner will own.
                        if (((MY_RANK[7:0] >> step) & 8'd1) == 8'd0) begin
                            send_lo <= blk_lo + ((blk_hi - blk_lo) >> 1);
                            send_hi <= blk_hi;
                            keep_lo <= blk_lo;
                            keep_hi <= blk_lo + ((blk_hi - blk_lo) >> 1);
                            recv_lo <= blk_lo;
                            recv_hi <= blk_lo + ((blk_hi - blk_lo) >> 1);
                        end else begin
                            send_lo <= blk_lo;
                            send_hi <= blk_lo + ((blk_hi - blk_lo) >> 1);
                            keep_lo <= blk_lo + ((blk_hi - blk_lo) >> 1);
                            keep_hi <= blk_hi;
                            recv_lo <= blk_lo + ((blk_hi - blk_lo) >> 1);
                            recv_hi <= blk_hi;
                        end
                        do_send <= 1'b1;
                        do_recv <= 1'b1;
                    end else begin
                        // recursive-doubling all-gather: publish my block,
                        // take the partner's, and the block doubles.
                        send_lo <= blk_lo;
                        send_hi <= blk_hi;
                        keep_lo <= blk_lo;
                        keep_hi <= blk_hi;
                        if (((MY_RANK[7:0] >> step) & 8'd1) == 8'd0) begin
                            recv_lo <= blk_hi;
                            recv_hi <= blk_hi + (blk_hi - blk_lo);
                        end else begin
                            recv_lo <= blk_lo - (blk_hi - blk_lo);
                            recv_hi <= blk_lo;
                        end
                        do_send <= 1'b1;
                        do_recv <= 1'b1;
                    end
                    state <= S_XFER;
                end

                S_XFER: begin
                    // send
                    if (do_send && (send_idx < send_count)) begin
                        if (!net_out_valid || net_out_ready) begin
                            net_out_valid <= 1'b1;
                            net_out_flit <= ot_a3_link_pkg::flit_pack(
                                (cur_op == OP_BARRIER) ? 32'd0
                                                       : acc[(send_lo + send_idx) & {(VW+1){1'b1}}],
                                peer_x, peer_y, MY_X[3:0], MY_Y[3:0],
                                (cur_op == OP_BARRIER) ? ot_a3_link_pkg::KIND_BARRIER : ot_a3_link_pkg::KIND_EXCHANGE,
                                cur_tag);
                            send_idx <= send_idx + 1'b1;
                            flits_sent <= flits_sent + 32'd1;
                            hop_distance_sent <= hop_distance_sent +
                                {28'd0, dist_x} + {28'd0, dist_y};
                        end
                    end else if (net_out_valid && net_out_ready) begin
                        net_out_valid <= 1'b0;
                    end

                    if ((!do_send || (send_idx >= send_count)) &&
                        (!net_out_valid || net_out_ready) &&
                        (!do_recv || (recv_fill[cur_tag[3:0]] >= recv_count))) begin
                        net_out_valid <= 1'b0;
                        // The reduce branch walks absolute element indices over
                        // the kept range; the all-gather and broadcast branches
                        // walk a relative count over the received range.
                        comb_idx <= ((cur_op == ot_a3_link_pkg::COLL_BROADCAST) ||
                                     (cur_op == ot_a3_link_pkg::COLL_ALL_GATHER) ||
                                     (phase == 1'b1)) ? 0 : keep_lo;
                        state <= S_COMBINE;
                    end
                end

                S_COMBINE: begin
                    if (cur_op == OP_BARRIER) begin
                        state <= S_ADVANCE;
                    end else if (cur_op == ot_a3_link_pkg::COLL_BROADCAST) begin
                        if (!do_recv) begin
                            state <= S_ADVANCE;
                        end else if (comb_idx < VEC_LEN[VW:0]) begin
                            acc[comb_idx[VW-1:0]] <= peer_word;
                            comb_idx <= comb_idx + 1'b1;
                        end else begin
                            state <= S_ADVANCE;
                        end
                    end else if ((cur_op == ot_a3_link_pkg::COLL_ALL_GATHER) ||
                                 (phase == 1'b1)) begin
                        // all-gather half: adopt the partner's block verbatim
                        if (comb_idx < recv_count) begin
                            acc[(recv_lo + comb_idx) & {(VW+1){1'b1}}] <= peer_word;
                            comb_idx <= comb_idx + 1'b1;
                        end else begin
                            state <= S_ADVANCE;
                        end
                    end else begin
                        if (comb_idx < keep_hi) begin
                            case (cur_op)
                                ot_a3_link_pkg::COLL_SUM: acc[comb_idx[VW-1:0]] <= add_result[31:0];
                                ot_a3_link_pkg::COLL_MAX: acc[comb_idx[VW-1:0]] <=
                                    ot_a3_link_pkg::fp32_max(acc[comb_idx[VW-1:0]], peer_word);
                                ot_a3_link_pkg::COLL_MIN: acc[comb_idx[VW-1:0]] <=
                                    ot_a3_link_pkg::fp32_min(acc[comb_idx[VW-1:0]], peer_word);
                                default:  acc[comb_idx[VW-1:0]] <= acc[comb_idx[VW-1:0]];
                            endcase
                            comb_idx <= comb_idx + 1'b1;
                        end else begin
                            state <= S_ADVANCE;
                        end
                    end
                end

                S_ADVANCE: begin
                    steps_taken <= steps_taken + 32'd1;
                    // One step of the schedule is one dependent traversal of
                    // `dist` links: this is the quantity
                    // src/opentallas/roofline.py prices as
                    // `collective_traversals`, counted rather than derived.
                    if (do_send || do_recv)
                        serial_traversals <= serial_traversals +
                            {28'd0, dist_x} + {28'd0, dist_y};
                    if (cur_op == ot_a3_link_pkg::COLL_ALL_GATHER) begin
                        blk_lo <= (recv_lo < blk_lo) ? recv_lo : blk_lo;
                        blk_hi <= (recv_hi > blk_hi) ? recv_hi : blk_hi;
                        if (step + 1 >= LG[3:0]) state <= S_DONE;
                        else begin step <= step + 4'd1; state <= S_SETUP; end
                    end else if (cur_alg == ot_a3_link_pkg::ALG_HALVING_DOUBLING && is_reduction) begin
                        if (phase == 1'b0) begin
                            blk_lo <= keep_lo;
                            blk_hi <= keep_hi;
                            if (step == 4'd0) begin
                                phase <= 1'b1;
                                step <= 4'd0;
                                state <= S_SETUP;
                            end else begin
                                step <= step - 4'd1;
                                state <= S_SETUP;
                            end
                        end else begin
                            blk_lo <= (recv_lo < blk_lo) ? recv_lo : blk_lo;
                            blk_hi <= (recv_hi > blk_hi) ? recv_hi : blk_hi;
                            if (step + 1 >= LG[3:0]) state <= S_DONE;
                            else begin step <= step + 4'd1; state <= S_SETUP; end
                        end
                    end else begin
                        if (step + 1 >= LG[3:0]) state <= S_DONE;
                        else begin step <= step + 4'd1; state <= S_SETUP; end
                    end
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                S_TRAP: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase

            // Reassembly is by tag, in arrival order within the tag.  A step
            // has exactly one partner and one dimension-ordered path, so order
            // within a tag is the order the partner sent.
            //
            // This is deliberately placed AFTER the state machine: its refusal
            // path assigns `state`, and a refusal that the ordinary schedule
            // could overwrite in the same cycle would be a check that cannot
            // fire -- which is worse than no check at all.
            if (net_in_valid && net_in_ready) begin
                flits_received <= flits_received + 32'd1;
                if (!in_tag_legal ||
                    (recv_fill[in_tag[3:0]] >= VEC_LEN[VW:0])) begin
                    trap <= 1'b1;
                    trap_class <= ot_a3_link_pkg::TRAP_LINK_OR_NOC;
                    state <= S_TRAP;
                end else begin
                    peer[(in_tag * VEC_LEN) +
                         {{(32-VW-1){1'b0}}, recv_fill[in_tag[3:0]]}] <=
                        ot_a3_link_pkg::flit_payload(net_in_flit);
                    recv_fill[in_tag[3:0]] <= recv_fill[in_tag[3:0]] + 1'b1;
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if ((MESH_X & (MESH_X-1)) != 0 || (MESH_Y & (MESH_Y-1)) != 0)
            $error("ot_a3_collective_engine: mesh extents must be powers of two");
        if (VEC_LEN % P != 0)
            $error("ot_a3_collective_engine: VEC_LEN must be a whole number of participant shards");
    end
`endif
endmodule
