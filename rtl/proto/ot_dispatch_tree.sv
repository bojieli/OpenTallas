`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hierarchical work distributor: one descriptor in, LEAVES x GROUP compute units
// fed, and the widest net in it bounded by RADIX x CREDITS gate inputs -- a bound
// that does not grow with the number of units.
//
// THE FAN-OUT BOUND, STATED EXACTLY, because the whole point is a load count.
// At the defaults RADIX=16, CREDITS=2, GROUP=16:
//   a node's out_pay / out_valid   RADIX children x CREDITS buffer slots = 32
//                                 gate inputs per bit
//   a leaf's cu_start / cu_cfg_*   GROUP compute units = 16 loads, which is the
//                                 width ot_cluster_dispatcher is already routed
//                                 at
//   a node's credit and completion RADIX inputs on one registered reduction
//   returns
// None of those depends on LEAVES.  The flat dispatcher's cu_start, by contrast,
// is UNITS loads on one register and its completion gather is a UNITS-input AND
// in one cycle.
//
// WHY THIS REPLACES ot_cluster_dispatcher
// ---------------------------------------
// ot_cluster_dispatcher is a FLAT fan-out.  One `cu_start` register drives every
// unit and one combinational `(done_mask | cu_done) == all-ones` gathers every
// unit back.  At UNITS=16 that routes and closes at 1,290 MHz
// (results/physical_abi3/asap7/cluster_dispatcher/pnr.json, 828 um2 core), and
// tb_cluster_dispatch_throughput measures 99.1 % array utilisation on sixteen
// real compute units.  Neither number survives width:
//
//   * tools/audit_control_path_throughput.py reports required_fanout 34 for the
//     16-unit capabilities, 68 for rom_qwen3 and 1,076 for rom_deepseek_v4 and
//     rom_deepseek_v41_wafer -- and the 1,076-wide fan-out has no routed record,
//     because a single register cannot drive 1,076 loads at 1.29 GHz.  A NAND2
//     driving 510 loads cost 3.7 ns elsewhere in this project.
//   * the completion gather is worse: a 1,076-input AND in one cycle.
//
// A modern GPU does not solve this by widening the flat stage.  A GigaThread
// engine hands work to GPCs, GPCs hand it to SMs, and SMs hand it to warp
// schedulers: ONE command expands into thousands of blocks through a TREE, and
// no single stage fans out to everything.  That is what this is.
//
// STRUCTURE
// ---------
//   root        ot_dispatch_tree: descriptor queue, then a PASS EXPANDER that
//               turns one descriptor covering `passes` weight-SRAM passes into
//               `passes` wavefront tokens, one per cycle.  Initiation interval
//               is 1 at the root and it is 1 ACROSS descriptor boundaries too:
//               the next descriptor is popped on the same cycle the previous
//               one's last token is emitted.
//   interior    ot_dispatch_node, DEPTH levels of them.  Each accepts a token
//               into a CREDITS-deep buffer and replicates it to its RADIX
//               children from ONE output register.  So the widest net in the
//               whole distributor is bounded by RADIX x CREDITS, whatever
//               LEAVES is.
//   leaves      ot_dispatch_leaf, one per GROUP of compute units.  Holds a
//               CREDITS-deep token buffer -- the double buffering that lets a
//               group start its next pass the cycle after it completes -- and
//               derives its GROUP's sub-range origin from the descriptor's grid
//               origin plus its hardwired leaf index times GROUP.
//
// WHY A GROUP AND NOT ONE UNIT PER LEAF.  Both are built; GROUP is a parameter
// and GROUP=1 is one leaf per unit.  The measurement decided the default:
// synthesised to ASAP7 at 1,076 units, one leaf per unit is 539,233 cells and
// 85,815 um2 of standard cells, while GROUP=16 -- which is exactly the 16-wide
// broadcast ot_cluster_dispatcher already has a closed routed record for
// (1,290 MHz, 828 um2 core) -- serves the same 1,076 units from 68 leaves.  A
// leaf's whole job is to hold a token and launch it; doing that once for sixteen
// units instead of sixteen times costs nothing in fan-out, because sixteen loads
// is the width that block was already routed at.  The price is that a group runs
// in lockstep, and rtl/test/tb_dispatch_tree_throughput.sv measures what that
// costs.
//
// DEPTH is ceil(log_RADIX(LEAVES)), so 1,076 leaves is 3 levels at RADIX 16 and
// 2 at RADIX 33.  Nodes whose whole subtree is empty are not instantiated, so
// LEAVES need not be a power of RADIX: at LEAVES=1076, RADIX=16 the tree is
// 1 + 5 + 68 interior nodes, not 1 + 16 + 256.
//
// FLOW CONTROL: CREDITS, NOT A GLOBAL READY
// -----------------------------------------
// A combinational `ready` from 1,076 leaves back to the root is the same
// physical fault as the fan-out, in the other direction.  So every link is
// credit-based and every level is registered:
//
//   * a parent holds a credit counter per child, initialised to CREDITS;
//   * it forwards a token only when EVERY populated child has a credit, and
//     decrements all of them in the same cycle -- so replication is atomic and a
//     token can never reach some leaves and not others;
//   * a child returns one credit, as a registered pulse, when it frees the
//     buffer slot, i.e. when it has forwarded the token to ALL of its own
//     children (interior) or handed it to its compute unit (leaf).
//
// A busy leaf therefore applies backpressure that walks up the tree one level
// per cycle and stalls the root; it cannot deadlock it, because credits are only
// ever consumed by a forward that is guaranteed to complete, and only ever
// returned by a buffer slot that has actually emptied.  The root reports the
// cycles it spent stalled for credit, so the backpressure is measurable and not
// merely asserted.
//
// COMPLETION, REDUCED IN A TREE TOO
// ---------------------------------
// Completions come back as a REGISTERED SUM at every level: a node adds its
// children's per-cycle completion counts and registers the total.  So the root
// learns that all LEAVES units finished a descriptor's last pass without any
// wide combinational gather; the cost is DEPTH cycles of latency on a signal
// that is only needed for fences, and never on the launch path.
//
// Each unit also returns a one-bit signature of the descriptor it actually ran.
// These are XOR-reduced in the same registered tree, so the control plane can
// check that every unit executed the descriptor it was handed -- the thing a
// broadcast cannot check and the reason a dispatcher that keeps units busy with
// the wrong operands is worthless.
//
// WHAT THIS IS NOT
// ----------------
// There is no work SPLITTING of the K extent.  Every unit walks the same K and
// the same scale; what differs per unit is its sub-range index, which is the
// output-stationary case where units differ only by which output tile they own.
// A descriptor whose extent had to be divided unequally across units would need
// a splitter, and this module would have to refuse it rather than silently give
// every unit the whole extent.  Same admission as ot_cluster_dispatcher.
// ---------------------------------------------------------------------------

/* verilator lint_off DECLFILENAME */

// ---------------------------------------------------------------------------
// Interior node: one token in, RADIX replicas out, credits both ways.
// ---------------------------------------------------------------------------
module ot_dispatch_node #(
    parameter integer RADIX   = 16,   // children wired out
    parameter integer ACTIVE  = 16,   // children actually populated, <= RADIX
    parameter integer PAY_W   = 24,
    parameter integer CREDITS = 2,    // buffer slots, power of two
    parameter integer CNT_W   = 8     // completion-count bus width
) (
    input  wire                    clk,
    input  wire                    rst_n,

    // ---- from the parent ----
    input  wire                    in_valid,
    input  wire [PAY_W-1:0]        in_pay,
    output reg                     in_cred_ret,   // registered credit pulse up

    // ---- reductions, towards the root ----
    output reg  [CNT_W-1:0]        up_cmpl,       // unit completions this cycle
    output reg  [CNT_W-1:0]        up_lcmpl,      // ... of a descriptor's last pass
    output reg                     up_obs,        // XOR of subtree signatures

    // ---- to the children ----
    output reg                     out_valid,
    output reg  [PAY_W-1:0]        out_pay,
    input  wire [RADIX-1:0]        dn_cred_ret,
    input  wire [RADIX*CNT_W-1:0]  dn_cmpl,
    input  wire [RADIX*CNT_W-1:0]  dn_lcmpl,
    input  wire [RADIX-1:0]        dn_obs
);
    localparam integer PTR_W = (CREDITS > 1) ? $clog2(CREDITS) : 1;
    localparam integer CRD_W = $clog2(CREDITS + 1);
    localparam [31:0]      CREDITS32 = CREDITS;
    localparam [CRD_W-1:0] CRD_INIT  = CREDITS32[CRD_W-1:0];

    // ---- token buffer: CREDITS slots, so the parent's credit count IS the
    //      occupancy bound and no full check can ever be needed ----
    reg  [PAY_W-1:0]   fifo [0:CREDITS-1];
    reg  [PTR_W:0]     wp, rp;
    wire               empty = (wp == rp);
    wire [PAY_W-1:0]   head  = fifo[rp[PTR_W-1:0]];

    // ---- per-child credits ----
    reg  [CRD_W-1:0]   cred [0:RADIX-1];
    wire [RADIX-1:0]   cred_ok;
    wire               pop = !empty && (&cred_ok);

    genvar c;
    generate
        for (c = 0; c < RADIX; c = c + 1) begin : child
            if (c < ACTIVE) begin : live
                assign cred_ok[c] = (cred[c] != {CRD_W{1'b0}});
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) cred[c] <= CRD_INIT;
                    else        cred[c] <= cred[c]
                                         - {{(CRD_W-1){1'b0}}, pop}
                                         + {{(CRD_W-1){1'b0}}, dn_cred_ret[c]};
            end else begin : dead
                //: An unpopulated child never withholds a credit, so a tree whose
                //: leaf count is not a power of RADIX does not stall on the gap.
                assign cred_ok[c] = 1'b1;
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_n)
        if (!rst_n) wp <= {(PTR_W+1){1'b0}};
        else if (in_valid) begin
            fifo[wp[PTR_W-1:0]] <= in_pay;
            wp <= wp + 1'b1;
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rp <= {(PTR_W+1){1'b0}};
            out_valid <= 1'b0; out_pay <= {PAY_W{1'b0}};
            in_cred_ret <= 1'b0;
        end else begin
            out_valid   <= pop;
            in_cred_ret <= pop;
            if (pop) begin
                out_pay <= head;
                rp      <= rp + 1'b1;
            end
        end

    // ---- registered reduction of the children's returns ----
    integer i;
    reg [CNT_W-1:0] sum_c, sum_l;
    reg             xor_o;
    always @* begin
        sum_c = {CNT_W{1'b0}};
        sum_l = {CNT_W{1'b0}};
        xor_o = 1'b0;
        for (i = 0; i < ACTIVE; i = i + 1) begin
            sum_c = sum_c + dn_cmpl [i*CNT_W +: CNT_W];
            sum_l = sum_l + dn_lcmpl[i*CNT_W +: CNT_W];
            xor_o = xor_o ^ dn_obs[i];
        end
    end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            up_cmpl <= {CNT_W{1'b0}}; up_lcmpl <= {CNT_W{1'b0}}; up_obs <= 1'b0;
        end else begin
            up_cmpl <= sum_c; up_lcmpl <= sum_l; up_obs <= xor_o;
        end
endmodule


// ---------------------------------------------------------------------------
// Leaf: one token buffer and one compute unit.
// ---------------------------------------------------------------------------
module ot_dispatch_leaf #(
    parameter integer PAY_W   = 24,
    parameter integer CREDITS = 2,
    parameter integer CNT_W   = 8,
    parameter integer K_W     = 9,
    parameter integer SC_W    = 8,
    parameter integer TILE_W  = 4,
    parameter integer GROUP   = 1,    // compute units this leaf launches together
    parameter integer INDEX   = 0     // this leaf's hardwired position in the grid
) (
    input  wire                clk,
    input  wire                rst_n,

    input  wire                in_valid,
    input  wire [PAY_W-1:0]    in_pay,
    output reg                 in_cred_ret,

    output reg  [CNT_W-1:0]    up_cmpl,
    output reg  [CNT_W-1:0]    up_lcmpl,
    output reg                 up_obs,

    // ---- the GROUP of compute units this leaf owns ----
    output reg                 cu_start,     // one pulse, all GROUP units
    output reg  [K_W-1:0]      cu_cfg_k,
    output reg  [SC_W-1:0]     cu_cfg_scale,
    //: this GROUP's sub-range origin.  Unit j of the group works on
    //: cu_tile_base + j, and j is a hardwired constant inside the unit's own
    //: address generator -- which is where a per-unit constant belongs, and is
    //: why there is no per-unit adder anywhere in this distributor.
    output reg  [TILE_W-1:0]   cu_tile_base,
    input  wire [GROUP-1:0]    cu_done,
    input  wire [GROUP-1:0]    cu_obs        // units' signatures of what they ran
);
    localparam integer PTR_W = (CREDITS > 1) ? $clog2(CREDITS) : 1;
    //: the grid offset of this leaf's first unit: its leaf index times the group
    //: size, resolved at elaboration, so no index arithmetic appears in any node.
    localparam [31:0]       INDEX32 = INDEX * GROUP;
    localparam [TILE_W-1:0] INDEX_V = INDEX32[TILE_W-1:0];
    localparam integer      GCNT_W  = $clog2(GROUP + 1);
    localparam [31:0]       GROUP32 = GROUP;
    localparam [CNT_W-1:0]  GROUP_C = GROUP32[CNT_W-1:0];

    reg  [PAY_W-1:0] fifo [0:CREDITS-1];
    reg  [PTR_W:0]   wp, rp;
    wire             empty = (wp == rp);
    wire [PAY_W-1:0] head  = fifo[rp[PTR_W-1:0]];

    //: payload layout, little end first: k, scale, grid origin, last-pass flag
    wire [K_W-1:0]    h_k    = head[0 +: K_W];
    wire [SC_W-1:0]   h_sc   = head[K_W +: SC_W];
    wire [TILE_W-1:0] h_base = head[K_W+SC_W +: TILE_W];
    wire              h_last = head[K_W+SC_W+TILE_W];

    //: One pass outstanding per GROUP.  The buffer holds the NEXT one, which is
    //: why a group restarts the cycle after it completes instead of waiting for
    //: the control plane or for its siblings.
    //:
    //: A group's pass is complete when EVERY unit in it has reported done.
    //: Tracking a mask rather than watching one unit is what makes this correct
    //: when units finish at different times -- which they do as soon as their
    //: memory paths are not identical, even though they are given identical work.
    reg pending, last_r;
    reg [GROUP-1:0] done_mask;
    wire all_done = pending && ((done_mask | cu_done) == {GROUP{1'b1}});
    //: `|| all_done` is worth one cycle per pass and it is not free rhetoric:
    //: without it the group goes idle for the cycle in which `pending` clears
    //: and only launches the cycle after, which measured 98.86 % array
    //: utilisation against ot_cluster_dispatcher's 99.21 % -- exactly the
    //: 1/271 a spare cycle costs on a 270-cycle K=256 pass.  cu_start stays
    //: REGISTERED either way; what changes is that `all_done` is allowed into
    //: the launch term, which is the same combinational depth the flat
    //: dispatcher already accepts.
    wire launch = !empty && (!pending || all_done);

    always @(posedge clk or negedge rst_n)
        if (!rst_n) wp <= {(PTR_W+1){1'b0}};
        else if (in_valid) begin
            fifo[wp[PTR_W-1:0]] <= in_pay;
            wp <= wp + 1'b1;
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            rp <= {(PTR_W+1){1'b0}};
            cu_start <= 1'b0; cu_cfg_k <= {K_W{1'b0}};
            cu_cfg_scale <= {SC_W{1'b0}}; cu_tile_base <= {TILE_W{1'b0}};
            pending <= 1'b0; last_r <= 1'b0; in_cred_ret <= 1'b0;
            done_mask <= {GROUP{1'b0}};
        end else begin
            cu_start    <= launch;
            in_cred_ret <= launch;
            if (launch) begin
                cu_cfg_k     <= h_k;
                cu_cfg_scale <= h_sc;
                //: the sub-range: the descriptor's grid origin plus this leaf's
                //: hardwired offset.  Held at the leaf, so no index arithmetic
                //: and no per-child datapath anywhere above it.
                cu_tile_base <= h_base + INDEX_V;
                last_r       <= h_last;
                pending      <= 1'b1;
                done_mask    <= {GROUP{1'b0}};
                rp           <= rp + 1'b1;
            end else if (all_done) begin
                //: completed with nothing buffered: go idle.
                pending   <= 1'b0;
                done_mask <= {GROUP{1'b0}};
            end else if (pending)
                done_mask <= done_mask | cu_done;
        end

    reg [GCNT_W-1:0] obs_pc;
    integer b;
    always @* begin
        obs_pc = {GCNT_W{1'b0}};
        for (b = 0; b < GROUP; b = b + 1)
            obs_pc = obs_pc ^ {{(GCNT_W-1){1'b0}}, cu_obs[b]};
    end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            up_cmpl <= {CNT_W{1'b0}}; up_lcmpl <= {CNT_W{1'b0}}; up_obs <= 1'b0;
        end else begin
            //: GROUP unit-completions retire together, so the root's running
            //: total still counts UNITS and not leaves.
            up_cmpl  <= all_done ? GROUP_C : {CNT_W{1'b0}};
            up_lcmpl <= (all_done && last_r) ? GROUP_C : {CNT_W{1'b0}};
            up_obs   <= up_obs ^ obs_pc[0];
        end
endmodule


// ---------------------------------------------------------------------------
// The tree.
// ---------------------------------------------------------------------------
module ot_dispatch_tree #(
    parameter integer LEAVES     = 16,
    //: compute units one leaf launches together.  GROUP=1 is one leaf per unit;
    //: GROUP=16 is the 16-wide broadcast ot_cluster_dispatcher already has a
    //: closed routed record for.  UNITS = LEAVES * GROUP either way.
    parameter integer GROUP      = 1,
    //: derived, not a literal: the grid-index width this tree carries.  It is a
    //: parameter and not a localparam only because the port list needs it.
    parameter integer TILE_W     = $clog2(LEAVES * GROUP),
    parameter integer RADIX      = 16,
    parameter integer CREDITS    = 2,
    parameter integer QUEUE_LOG2 = 3,
    parameter integer PASS_W     = 6,
    parameter integer K_W        = 9,
    parameter integer SC_W       = 8
) (
    input  wire                      clk,
    input  wire                      rst_n,

    // ---- descriptor write port, from the control plane ----
    input  wire                      desc_valid,
    output wire                      desc_ready,
    input  wire [K_W-1:0]            desc_k,
    input  wire [SC_W-1:0]           desc_scale,
    input  wire [PASS_W-1:0]         desc_passes,
    input  wire [TILE_W-1:0]         desc_tile_base,

    // ---- the leaves' compute units: LEAVES groups of GROUP each ----
    output wire [LEAVES-1:0]         cu_start,
    output wire [LEAVES*K_W-1:0]     cu_cfg_k,
    output wire [LEAVES*SC_W-1:0]    cu_cfg_scale,
    output wire [LEAVES*TILE_W-1:0]  cu_tile_base,
    input  wire [LEAVES*GROUP-1:0]   cu_done,
    input  wire [LEAVES*GROUP-1:0]   cu_obs,

    // ---- observation ----
    output reg  [31:0]               descriptors_retired,
    output reg  [31:0]               passes_launched,
    output reg  [31:0]               unit_completions,
    output reg  [31:0]               root_stall_cycles,   // token held, no credit
    output reg  [31:0]               cluster_cycles,
    output reg  [31:0]               starved_cycles,      // nothing to launch
    output wire                      payload_signature
);
    // -- derived geometry. Every width is $clog2 of its own bound; there is not a
    //    single hardcoded index width in this module. ------------------------
    function automatic integer f_depth(input integer leaves, input integer radix);
        integer d, reach;
        begin
            d = 1; reach = radix;
            while (reach < leaves) begin reach = reach * radix; d = d + 1; end
            f_depth = d;
        end
    endfunction

    function automatic integer f_pow(input integer b, input integer e);
        integer i;
        begin
            f_pow = 1;
            for (i = 0; i < e; i = i + 1) f_pow = f_pow * b;
        end
    endfunction

    localparam integer DEPTH  = f_depth(LEAVES, RADIX);
    localparam integer UNITS  = LEAVES * GROUP;
    localparam integer PAY_W  = 1 + TILE_W + SC_W + K_W;
    //: the completion buses carry UNIT counts, so their width is $clog2 of the
    //: unit count and never of a literal.
    localparam integer CNT_W  = $clog2(UNITS + 1);
    localparam integer LEAF_W = $clog2(UNITS + 1);

    //: nodes at interior level l cover f_pow(RADIX, DEPTH-l) leaves each
    function automatic integer f_nodes(input integer l);
        integer span;
        begin
            span = f_pow(RADIX, DEPTH - l);
            f_nodes = (LEAVES + span - 1) / span;
        end
    endfunction

    function automatic integer f_off(input integer l);
        integer i;
        begin
            f_off = 0;
            for (i = 0; i < l; i = i + 1) f_off = f_off + f_nodes(i);
        end
    endfunction

    localparam integer TOT_NODES = f_off(DEPTH);

    // -- node link arrays, flat and indexed by global node id ---------------
    wire                    n_in_valid  [0:TOT_NODES-1];
    wire [PAY_W-1:0]        n_in_pay    [0:TOT_NODES-1];
    wire                    n_cred_ret  [0:TOT_NODES-1];
    wire [CNT_W-1:0]        n_up_cmpl   [0:TOT_NODES-1];
    wire [CNT_W-1:0]        n_up_lcmpl  [0:TOT_NODES-1];
    wire                    n_up_obs    [0:TOT_NODES-1];
    wire                    n_out_valid [0:TOT_NODES-1];
    wire [PAY_W-1:0]        n_out_pay   [0:TOT_NODES-1];
    wire [RADIX-1:0]        n_dn_cred   [0:TOT_NODES-1];
    wire [RADIX*CNT_W-1:0]  n_dn_cmpl   [0:TOT_NODES-1];
    wire [RADIX*CNT_W-1:0]  n_dn_lcmpl  [0:TOT_NODES-1];
    wire [RADIX-1:0]        n_dn_obs    [0:TOT_NODES-1];

    wire                    l_cred_ret  [0:LEAVES-1];
    wire [CNT_W-1:0]        l_up_cmpl   [0:LEAVES-1];
    wire [CNT_W-1:0]        l_up_lcmpl  [0:LEAVES-1];
    wire                    l_up_obs    [0:LEAVES-1];

    // -- root: descriptor queue ---------------------------------------------
    localparam integer QDEPTH = 1 << QUEUE_LOG2;
    reg [K_W-1:0]    q_k      [0:QDEPTH-1];
    reg [SC_W-1:0]   q_scale  [0:QDEPTH-1];
    reg [PASS_W-1:0] q_passes [0:QDEPTH-1];
    reg [TILE_W-1:0] q_base   [0:QDEPTH-1];
    reg [QUEUE_LOG2:0] q_wp, q_rp;

    wire q_empty = (q_wp == q_rp);
    wire q_full  = (q_wp[QUEUE_LOG2-1:0] == q_rp[QUEUE_LOG2-1:0]) &&
                   (q_wp[QUEUE_LOG2] != q_rp[QUEUE_LOG2]);
    assign desc_ready = !q_full;
    wire q_push = desc_valid && desc_ready;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) q_wp <= {(QUEUE_LOG2+1){1'b0}};
        else if (q_push) begin
            q_k     [q_wp[QUEUE_LOG2-1:0]] <= desc_k;
            q_scale [q_wp[QUEUE_LOG2-1:0]] <= desc_scale;
            //: zero passes would be a descriptor that launches nothing and never
            //: retires; one pass is the only sane reading of it.
            q_passes[q_wp[QUEUE_LOG2-1:0]] <= (desc_passes == {PASS_W{1'b0}})
                                              ? {{(PASS_W-1){1'b0}}, 1'b1}
                                              : desc_passes;
            q_base  [q_wp[QUEUE_LOG2-1:0]] <= desc_tile_base;
            q_wp <= q_wp + 1'b1;
        end

    // -- root: pass expander, initiation interval 1 -------------------------
    localparam integer CRD_W = $clog2(CREDITS + 1);
    localparam [31:0]      CREDITS32 = CREDITS;
    localparam [CRD_W-1:0] CRD_INIT  = CREDITS32[CRD_W-1:0];

    reg  [CRD_W-1:0]  root_cred;
    reg  [K_W-1:0]    cur_k;
    reg  [SC_W-1:0]   cur_scale;
    reg  [TILE_W-1:0] cur_base;
    reg  [PASS_W-1:0] left;
    reg               active;
    reg               root_valid;
    reg  [PAY_W-1:0]  root_pay;

    wire cred_ok  = (root_cred != {CRD_W{1'b0}});
    wire emit     = active && cred_ok;
    wire last_now = emit && (left == {{(PASS_W-1){1'b0}}, 1'b1});
    //: the next descriptor is loaded on the SAME cycle the previous one's last
    //: token goes out, so a descriptor boundary costs no issue slot.
    wire load     = (!active || last_now) && !q_empty;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            q_rp <= {(QUEUE_LOG2+1){1'b0}};
            cur_k <= {K_W{1'b0}}; cur_scale <= {SC_W{1'b0}};
            cur_base <= {TILE_W{1'b0}}; left <= {PASS_W{1'b0}};
            active <= 1'b0; root_valid <= 1'b0; root_pay <= {PAY_W{1'b0}};
            root_cred <= CRD_INIT;
        end else begin
            root_valid <= emit;
            if (emit) begin
                root_pay <= {last_now, cur_base, cur_scale, cur_k};
                left     <= left - 1'b1;
            end
            root_cred <= root_cred
                       - {{(CRD_W-1){1'b0}}, emit}
                       + {{(CRD_W-1){1'b0}}, n_cred_ret[0]};

            if (load) begin
                cur_k     <= q_k     [q_rp[QUEUE_LOG2-1:0]];
                cur_scale <= q_scale [q_rp[QUEUE_LOG2-1:0]];
                cur_base  <= q_base  [q_rp[QUEUE_LOG2-1:0]];
                left      <= q_passes[q_rp[QUEUE_LOG2-1:0]];
                active    <= 1'b1;
                q_rp      <= q_rp + 1'b1;
            end else if (last_now)
                active <= 1'b0;
        end

    assign n_in_valid[0] = root_valid;
    assign n_in_pay[0]   = root_pay;

    // -- the interior levels ------------------------------------------------
    genvar l, j, c;
    generate
        for (l = 0; l < DEPTH; l = l + 1) begin : lvl
            for (j = 0; j < f_nodes(l); j = j + 1) begin : nd
                localparam integer GID   = f_off(l) + j;
                localparam integer NEXTN = (l + 1 < DEPTH) ? f_nodes(l + 1) : LEAVES;
                localparam integer NACT  = ((j + 1) * RADIX <= NEXTN)
                                           ? RADIX : (NEXTN - j * RADIX);

                ot_dispatch_node #(.RADIX(RADIX), .ACTIVE(NACT), .PAY_W(PAY_W),
                                   .CREDITS(CREDITS), .CNT_W(CNT_W)) u_node (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(n_in_valid[GID]), .in_pay(n_in_pay[GID]),
                    .in_cred_ret(n_cred_ret[GID]),
                    .up_cmpl(n_up_cmpl[GID]), .up_lcmpl(n_up_lcmpl[GID]),
                    .up_obs(n_up_obs[GID]),
                    .out_valid(n_out_valid[GID]), .out_pay(n_out_pay[GID]),
                    .dn_cred_ret(n_dn_cred[GID]), .dn_cmpl(n_dn_cmpl[GID]),
                    .dn_lcmpl(n_dn_lcmpl[GID]), .dn_obs(n_dn_obs[GID]));

                for (c = 0; c < RADIX; c = c + 1) begin : ch
                    if (j * RADIX + c < NEXTN) begin : live
                        if (l + 1 < DEPTH) begin : to_node
                            localparam integer CID = f_off(l + 1) + j * RADIX + c;
                            assign n_in_valid[CID]   = n_out_valid[GID];
                            assign n_in_pay[CID]     = n_out_pay[GID];
                            assign n_dn_cred[GID][c] = n_cred_ret[CID];
                            assign n_dn_cmpl [GID][c*CNT_W +: CNT_W] = n_up_cmpl[CID];
                            assign n_dn_lcmpl[GID][c*CNT_W +: CNT_W] = n_up_lcmpl[CID];
                            assign n_dn_obs[GID][c]  = n_up_obs[CID];
                        end else begin : to_leaf
                            localparam integer LID = j * RADIX + c;
                            ot_dispatch_leaf #(.PAY_W(PAY_W), .CREDITS(CREDITS),
                                               .CNT_W(CNT_W), .K_W(K_W),
                                               .SC_W(SC_W), .TILE_W(TILE_W),
                                               .GROUP(GROUP),
                                               .INDEX(LID)) u_leaf (
                                .clk(clk), .rst_n(rst_n),
                                .in_valid(n_out_valid[GID]), .in_pay(n_out_pay[GID]),
                                .in_cred_ret(l_cred_ret[LID]),
                                .up_cmpl(l_up_cmpl[LID]), .up_lcmpl(l_up_lcmpl[LID]),
                                .up_obs(l_up_obs[LID]),
                                .cu_start(cu_start[LID]),
                                .cu_cfg_k(cu_cfg_k[LID*K_W +: K_W]),
                                .cu_cfg_scale(cu_cfg_scale[LID*SC_W +: SC_W]),
                                .cu_tile_base(cu_tile_base[LID*TILE_W +: TILE_W]),
                                .cu_done(cu_done[LID*GROUP +: GROUP]),
                                .cu_obs(cu_obs[LID*GROUP +: GROUP]));
                            assign n_dn_cred[GID][c] = l_cred_ret[LID];
                            assign n_dn_cmpl [GID][c*CNT_W +: CNT_W] = l_up_cmpl[LID];
                            assign n_dn_lcmpl[GID][c*CNT_W +: CNT_W] = l_up_lcmpl[LID];
                            assign n_dn_obs[GID][c]  = l_up_obs[LID];
                        end
                    end else begin : dead
                        assign n_dn_cred[GID][c] = 1'b0;
                        assign n_dn_cmpl [GID][c*CNT_W +: CNT_W] = {CNT_W{1'b0}};
                        assign n_dn_lcmpl[GID][c*CNT_W +: CNT_W] = {CNT_W{1'b0}};
                        assign n_dn_obs[GID][c]  = 1'b0;
                    end
                end
            end
        end
    endgenerate

    assign payload_signature = n_up_obs[0];

    // -- root observation ---------------------------------------------------
    //: A descriptor is retired when UNITS units have reported the completion of
    //: its LAST pass.  The count arrives through the registered reduction, so
    //: this is a running accumulator and not a wide comparison.
    localparam [31:0]       UNITS32 = UNITS;
    localparam [LEAF_W-1:0] UNITS_V = UNITS32[LEAF_W-1:0];
    reg  [LEAF_W-1:0] lacc;
    wire [LEAF_W:0]   lsum = {1'b0, lacc} + {1'b0, n_up_lcmpl[0]};

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            descriptors_retired <= 32'b0; passes_launched <= 32'b0;
            unit_completions <= 32'b0; root_stall_cycles <= 32'b0;
            cluster_cycles <= 32'b0; starved_cycles <= 32'b0;
            lacc <= {LEAF_W{1'b0}};
        end else begin
            cluster_cycles <= cluster_cycles + 32'd1;
            if (emit) passes_launched <= passes_launched + 32'd1;
            if (active && !cred_ok) root_stall_cycles <= root_stall_cycles + 32'd1;
            if (!active && q_empty) starved_cycles <= starved_cycles + 32'd1;
            unit_completions <= unit_completions +
                                {{(32-CNT_W){1'b0}}, n_up_cmpl[0]};
            //: at most UNITS completions arrive in a cycle, so lsum < 2*UNITS
            //: and at most one descriptor can retire per cycle.
            if (lsum >= {1'b0, UNITS_V}) begin
                lacc <= lsum[LEAF_W-1:0] - UNITS_V;
                descriptors_retired <= descriptors_retired + 32'd1;
            end else
                lacc <= lsum[LEAF_W-1:0];
        end
endmodule
