`timescale 1ns/1ps
`default_nettype none
// H-NETLIST 1815 (owner standard 10-16: regional SYNCHRONOUS reset trees with registered stages, no die-wide async
// fan-out): the HBM die reset forest tiles (tools/hbm_die_v16/reset_forest_layer.py builds the per (domain, region)
// trees).  Every tile asserts asynchronously and immediately (rst_n_in low clears it) and releases synchronously on clk,
// the regional root clock of the tile's position, so a release reaches every sink a FIXED number of edges after the
// root sees it (equal-age per domain: the layer pads short paths with hop tiles).
//   hbfd_rrl_sync : regional root; the por input is asynchronous: SYNC_STAGES=2 synchroniser + 1 relay flop
//                   (ot_rst_relay REGIONS=1): release age 3 edges.
//   hbfd_rrl_hop  : one registered stage (a reach hop, an equal-age pad or a leaf driving <= 2,048 sink reset pins):
//                   release age 1 edge.  OT_HBFD_RRL_MUT: two stages (bench mutant: a skewed leaf).
module hbfd_rrl_sync (input wire clk, input wire rst_n_in, output wire rst_n);
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_hop (input wire clk, input wire rst_n_in, output wire rst_n);
    (* keep = "true", dont_touch = "true" *) reg q;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) q <= 1'b0; else q <= 1'b1;
    assign rst_n = q;
endmodule
`default_nettype wire
