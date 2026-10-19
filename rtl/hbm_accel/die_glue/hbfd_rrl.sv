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
// FOREST2 10-19 (DIE-HBM-LEAD): equal-age padding inside the leaf.  hbfd_rrl_pad<N> = N registered release stages in one
// tile (same pins/footprint as hbfd_rrl_hop): asynchronous assertion of every stage, release age N edges.  The leaf of a
// short regional path takes pad<1 + pads> instead of 1 + pads separate hop tiles (no pad homes in crowded strips).
module hbfd_rrl_stages #(parameter integer N = 2) (input wire clk, input wire rst_n_in, output wire rst_n);
    (* keep = "true", dont_touch = "true" *) reg [N-1:0] q;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) q <= {N{1'b0}}; else q <= {q[N-2:0], 1'b1};
    assign rst_n = q[N-1];
endmodule
module hbfd_rrl_pad2 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(2)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad3 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(3)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad4 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(4)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad5 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(5)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad6 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(6)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad7 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(7)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad8 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(8)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad9 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(9)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad10 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(10)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad11 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(11)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad12 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(12)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad13 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(13)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad14 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(14)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad15 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(15)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad16 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(16)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad17 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(17)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad18 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(18)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad19 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(19)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad20 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(20)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad21 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(21)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad22 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(22)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad23 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(23)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad24 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(24)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad25 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(25)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad26 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(26)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad27 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(27)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad28 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(28)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad29 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(29)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad30 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(30)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad31 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(31)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad32 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(32)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
`default_nettype wire
