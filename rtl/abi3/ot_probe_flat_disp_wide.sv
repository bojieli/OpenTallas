`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// The FLAT dispatcher at array width, built for exactly the same measurement as
// ot_probe_dispatch_tree so the two are comparable gate for gate.
//
// ot_cluster_dispatcher is the incumbent. It has a routed record at UNITS=16
// (results/physical_abi3/asap7/cluster_dispatcher/pnr.json, 1,290 MHz, 828 um2
// core) and none above it, and tools/audit_control_path_throughput.py needs
// UNITS as high as 1,076. This probe puts the same cycle-accurate unit models
// behind it that the tree probe uses, so what is being compared is the
// DISTRIBUTION STRUCTURE and nothing else:
//
//   flat   one cu_start register drives UNITS loads; one combinational
//          (done_mask | cu_done) == all-ones gathers UNITS bits in one cycle;
//          one combinational popcount sums UNITS busy bits.
//   tree   every net drives at most RADIX loads and every level is registered.
//
// Same unit models, same ports, same corner, same flow.
// ---------------------------------------------------------------------------
module ot_probe_flat_disp_wide #(
    parameter integer UNITS   = 16,
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
    output wire [31:0]       descriptors_retired,
    output wire [31:0]       passes_launched,
    output wire [63:0]       unit_busy_cycles,
    output wire [31:0]       cluster_cycles,
    output wire [31:0]       starved_cycles
);
    wire             cu_start;
    wire [K_W-1:0]   cu_cfg_k;
    wire [SC_W-1:0]  cu_cfg_scale;
    wire [UNITS-1:0] cu_busy, cu_done;

    ot_cluster_dispatcher #(.UNITS(UNITS), .QUEUE_LOG2(3), .PASS_W(PASS_W)) u_d (
        .clk(clk), .rst_n(rst_n),
        .desc_valid(desc_valid), .desc_ready(desc_ready),
        .desc_k(desc_k), .desc_scale(desc_scale), .desc_passes(desc_passes),
        .cu_start(cu_start), .cu_cfg_k(cu_cfg_k), .cu_cfg_scale(cu_cfg_scale),
        .cu_busy(cu_busy), .cu_done(cu_done),
        .descriptors_retired(descriptors_retired),
        .passes_launched(passes_launched),
        .unit_busy_cycles(unit_busy_cycles), .cluster_cycles(cluster_cycles),
        .starved_cycles(starved_cycles));

    genvar g;
    generate
        for (g = 0; g < UNITS; g = g + 1) begin : um
            //: TILE_W is 1 here because the flat dispatcher has no sub-range to
            //: give a unit: every unit is handed exactly the same descriptor.
            //: That is a capability difference, not a modelling shortcut.
            wire obs_unused;
            ot_dtree_unit_model #(.K_W(K_W), .SC_W(SC_W), .TILE_W(1)) u_m (
                .clk(clk), .rst_n(rst_n),
                .start(cu_start), .cfg_k(cu_cfg_k), .cfg_scale(cu_cfg_scale),
                .tile(1'b0),
                .busy(cu_busy[g]), .done(cu_done[g]), .obs(obs_unused));
        end
    endgenerate
endmodule
