`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical probe for ot_dispatch_tree: a self-contained block whose only ports
// are the descriptor write port and the root's observation counters.
//
// WHY A PROBE AT ALL. The distributor's leaf interface is LEAVES x (start, k,
// scale, tile) out and LEAVES x (done, obs) in. At LEAVES=1076 that is over
// 30,000 top-level pins, which no floorplan can place; and driving `done` from
// a handful of shared input ports would re-create the very 1,076-load net this
// design exists to remove, on the input side. So each leaf terminates in a
// cycle-accurate MODEL of the compute unit it would drive:
//
//     start -> busy for (cfg_k + 14) cycles -> done
//
// which is exactly ot_compute_unit's measured cost (270 cycles at K=256, per
// rtl/test/tb_kernel_dispatch_throughput.sv), and it returns the one-bit
// descriptor signature the leaf folds into the tree's reduction, so nothing in
// the leaf's output path can be optimised away.
//
// The model is a K_W+1 bit down-counter and a comparator -- about two orders of
// magnitude smaller than the 7,381 um2 of standard cells in a real
// ot_compute_unit, and it carries none of the unit's two SRAM macros. Its cost
// is ATTRIBUTED rather than assumed: the campaign synthesises the tree with and
// without the models and records both, so the tree's own area is a measurement
// and the routed number for this probe is an upper bound on it.
// ---------------------------------------------------------------------------

/* verilator lint_off DECLFILENAME */

module ot_dtree_unit_model #(
    parameter integer K_W    = 9,
    parameter integer SC_W   = 8,
    parameter integer TILE_W = 4,
    parameter integer OVH    = 14      // fill + drain, measured on the real unit
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [K_W-1:0]    cfg_k,
    input  wire [SC_W-1:0]   cfg_scale,
    input  wire [TILE_W-1:0] tile,
    output wire              busy,
    output reg               done,
    output reg               obs
);
    reg [K_W:0] cnt;
    reg         run;
    assign busy = run;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cnt <= {(K_W+1){1'b0}}; run <= 1'b0; done <= 1'b0; obs <= 1'b0;
        end else begin
            obs <= start ? (^{tile, cfg_scale, cfg_k}) : 1'b0;
            if (run) begin
                if (cnt <= {{K_W{1'b0}}, 1'b1}) begin
                    run <= 1'b0; done <= 1'b1;
                end else begin
                    cnt <= cnt - 1'b1; done <= 1'b0;
                end
            end else begin
                //: The counter is reloaded UNCONDITIONALLY while idle, so `start`
                //: drives exactly two registers in this model -- `run` and the
                //: signature -- which is the one-or-two loads a real
                //: ot_compute_unit presents on its own `start` port.
                //:
                //: This is not cosmetic. The first version of this model used
                //: `start` as the enable of the K_W+1 bit counter load, so a
                //: leaf's launch register drove sixteen units x ten enable muxes
                //: = about 190 gate inputs instead of sixteen, and pre-layout STA
                //: put 1.11 ns of the 1.34 ns critical path on that one net. That
                //: would have been MY probe setting the routed frequency of the
                //: design under test.
                cnt  <= {1'b0, cfg_k} + OVH[K_W:0];
                run  <= start;
                done <= 1'b0;
            end
        end
endmodule


module ot_probe_dispatch_tree #(
    parameter integer LEAVES  = 16,
    parameter integer GROUP   = 1,
    parameter integer RADIX   = 16,
    parameter integer CREDITS = 2,
    parameter integer TILE_W  = $clog2(LEAVES * GROUP),
    parameter integer K_W     = 9,
    parameter integer SC_W    = 8,
    parameter integer PASS_W  = 6
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              desc_valid,
    output wire              desc_ready,
    input  wire [K_W-1:0]    desc_k,
    input  wire [SC_W-1:0]   desc_scale,
    input  wire [PASS_W-1:0] desc_passes,
    input  wire [TILE_W-1:0] desc_tile_base,
    output wire [31:0]       descriptors_retired,
    output wire [31:0]       passes_launched,
    output wire [31:0]       unit_completions,
    output wire [31:0]       root_stall_cycles,
    output wire [31:0]       cluster_cycles,
    output wire [31:0]       starved_cycles,
    output wire              payload_signature
);
    localparam integer UNITS = LEAVES * GROUP;
    wire [LEAVES-1:0]        cu_start;
    //: the per-leaf new-tile flag.  It reaches a unit model's `obs` term below
    //: rather than being left dangling, because an unconnected output would let
    //: synthesis delete the leaf flop that drives it and the routed area would
    //: then understate the distributor by exactly the thing being added.
    wire [LEAVES-1:0]        cu_wgt_reload;
    wire [UNITS-1:0]         cu_done, cu_obs;
    wire [LEAVES*K_W-1:0]    cu_cfg_k;
    wire [LEAVES*SC_W-1:0]   cu_cfg_scale;
    wire [LEAVES*TILE_W-1:0] cu_tile;

    ot_dispatch_tree #(.LEAVES(LEAVES), .GROUP(GROUP), .TILE_W(TILE_W),
                       .RADIX(RADIX), .CREDITS(CREDITS), .K_W(K_W),
                       .SC_W(SC_W), .PASS_W(PASS_W)) u_tree (
        .clk(clk), .rst_n(rst_n),
        .desc_valid(desc_valid), .desc_ready(desc_ready),
        .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
        .desc_tile_base(desc_tile_base),
        .cu_start(cu_start), .cu_wgt_reload(cu_wgt_reload),
        .cu_cfg_k(cu_cfg_k), .cu_cfg_scale(cu_cfg_scale),
        .cu_tile_base(cu_tile), .cu_done(cu_done), .cu_obs(cu_obs),
        .descriptors_retired(descriptors_retired),
        .passes_launched(passes_launched),
        .unit_completions(unit_completions),
        .root_stall_cycles(root_stall_cycles),
        .cluster_cycles(cluster_cycles), .starved_cycles(starved_cycles),
        .payload_signature(payload_signature));

    //: one model per COMPUTE UNIT, so a GROUP of sixteen is sixteen models on
    //: one leaf's launch register -- the sixteen loads ot_cluster_dispatcher was
    //: routed at.
    genvar g, j;
    generate
        for (g = 0; g < LEAVES; g = g + 1) begin : lf
            for (j = 0; j < GROUP; j = j + 1) begin : um
                ot_dtree_unit_model #(.K_W(K_W), .SC_W(SC_W),
                                      .TILE_W(TILE_W)) u_m (
                    .clk(clk), .rst_n(rst_n),
                    .start(cu_start[g]), .cfg_k(cu_cfg_k[g*K_W +: K_W]),
                    .cfg_scale({cu_cfg_scale[g*SC_W +: SC_W-1],
                                cu_cfg_scale[g*SC_W + SC_W-1]
                                ^ cu_wgt_reload[g]}),
                    .tile(cu_tile[g*TILE_W +: TILE_W]),
                    .busy(), .done(cu_done[g*GROUP + j]),
                    .obs(cu_obs[g*GROUP + j]));
            end
        end
    endgenerate

    //: NO wide observation here. A running sum of LEAVES busy bits is a
    //: LEAVES-deep adder chain, which at LEAVES=1076 would be the slowest path
    //: in the block and would be MY scaffolding rather than the design's: it
    //: measured 1.23 ns at LEAVES=68 and set the critical path. Array
    //: utilisation is measured in rtl/test/tb_dispatch_tree_throughput.sv, where
    //: it costs the design nothing, and the routed block carries only what a
    //: real distributor carries.
endmodule


// ---------------------------------------------------------------------------
// Area attribution wrapper: the distributor ALONE, with the leaf interface
// brought out as ports and no unit models behind it.
//
// ot_probe_dispatch_tree's routed area is an upper bound on the distributor's,
// because it also contains one cycle-accurate unit model per leaf. Synthesising
// this module and that one under the same flow attributes the difference, so the
// figure quoted as "the distributor costs this fraction of the compute it feeds"
// is a measurement and not an estimate. Not routable as-is -- at LEAVES=1076 the
// leaf interface is over thirty thousand pins, which is exactly why the routed
// probe terminates its leaves internally.
// ---------------------------------------------------------------------------
module ot_probe_dtree_bare #(
    parameter integer LEAVES  = 16,
    parameter integer GROUP   = 1,
    parameter integer RADIX   = 16,
    parameter integer CREDITS = 2,
    parameter integer TILE_W  = $clog2(LEAVES * GROUP),
    parameter integer K_W     = 9,
    parameter integer SC_W    = 8,
    parameter integer PASS_W  = 6
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire                      desc_valid,
    output wire                      desc_ready,
    input  wire [K_W-1:0]            desc_k,
    input  wire [SC_W-1:0]           desc_scale,
    input  wire [PASS_W-1:0]         desc_passes,
    input  wire [TILE_W-1:0]         desc_tile_base,
    output wire [LEAVES-1:0]         cu_start,
    output wire [LEAVES-1:0]         cu_wgt_reload,
    output wire [LEAVES*K_W-1:0]     cu_cfg_k,
    output wire [LEAVES*SC_W-1:0]    cu_cfg_scale,
    output wire [LEAVES*TILE_W-1:0]  cu_tile,
    input  wire [LEAVES*GROUP-1:0]   cu_done,
    input  wire [LEAVES*GROUP-1:0]   cu_obs,
    output wire [31:0]               descriptors_retired,
    output wire [31:0]               passes_launched,
    output wire [31:0]               unit_completions,
    output wire [31:0]               root_stall_cycles,
    output wire [31:0]               cluster_cycles,
    output wire [31:0]               starved_cycles,
    output wire                      payload_signature
);
    ot_dispatch_tree #(.LEAVES(LEAVES), .GROUP(GROUP), .TILE_W(TILE_W),
                       .RADIX(RADIX), .CREDITS(CREDITS), .K_W(K_W),
                       .SC_W(SC_W), .PASS_W(PASS_W)) u_tree (
        .clk(clk), .rst_n(rst_n),
        .desc_valid(desc_valid), .desc_ready(desc_ready),
        .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
        .desc_tile_base(desc_tile_base),
        .cu_start(cu_start), .cu_wgt_reload(cu_wgt_reload),
        .cu_cfg_k(cu_cfg_k), .cu_cfg_scale(cu_cfg_scale),
        .cu_tile_base(cu_tile), .cu_done(cu_done), .cu_obs(cu_obs),
        .descriptors_retired(descriptors_retired),
        .passes_launched(passes_launched),
        .unit_completions(unit_completions),
        .root_stall_cycles(root_stall_cycles),
        .cluster_cycles(cluster_cycles), .starved_cycles(starved_cycles),
        .payload_signature(payload_signature));
endmodule
