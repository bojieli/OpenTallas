`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hardware barrier network node of the GPU-organised HBM die.
//
// Sense-reversing, toggle-coded: every participant's `arrive` toggles once
// per barrier (ot_gpu_issue raises it when the SM's op results are
// committed).  A node's `up` toggles, one register later, when every child
// has toggled to the new sense; the root's `up` is the release, which each
// node re-registers and fans out to its children.  No counters, no shared
// memory, no polling: arrival costs one register per tree level plus the
// registered wire stages between levels (ot_gpu_barrier_link, sized from the
// floorplan distances), and so does the release.
// ---------------------------------------------------------------------------
module ot_gpu_barrier_node #(
    parameter integer K = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [K-1:0] arr,        // children's arrival senses
    output reg          up,         // this subtree's arrival sense
    input  wire         rel_in,     // release sense from the parent (the root ties it to its own up)
    output reg  [K-1:0] rel         // release sense to each child (registered fan-out)
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            up <= 1'b0;
            rel <= {K{1'b0}};
        end else begin
            if (arr == {K{~up}}) up <= ~up;
            rel <= {K{rel_in}};
        end
    end
endmodule

// Registered wire of D stages (D = 0 is a wire): one per floorplan segment.
module ot_gpu_barrier_link #(
    parameter integer D = 1
) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    ot_hdc_delay #(.W(1), .D(D), .RESET(1)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
