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
module hbfd_rrl_pad33 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(33)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad34 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(34)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad35 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(35)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad36 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(36)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad37 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(37)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad38 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(38)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad39 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(39)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad40 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(40)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad41 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(41)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad42 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(42)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad43 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(43)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad44 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(44)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad45 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(45)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad46 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(46)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad47 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(47)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad48 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(48)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad49 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(49)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad50 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(50)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad51 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(51)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad52 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(52)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad53 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(53)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad54 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(54)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad55 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(55)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad56 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(56)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad57 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(57)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad58 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(58)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad59 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(59)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad60 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(60)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad61 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(61)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad62 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(62)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad63 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(63)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad64 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(64)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad65 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(65)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad66 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(66)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad67 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(67)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad68 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(68)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad69 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(69)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad70 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(70)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad71 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(71)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad72 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(72)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad73 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(73)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad74 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(74)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad75 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(75)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad76 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(76)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad77 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(77)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad78 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(78)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad79 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(79)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad80 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(80)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad81 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(81)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad82 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(82)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad83 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(83)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad84 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(84)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad85 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(85)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad86 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(86)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad87 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(87)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad88 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(88)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad89 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(89)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad90 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(90)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad91 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(91)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad92 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(92)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad93 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(93)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad94 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(94)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad95 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(95)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad96 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(96)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad97 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(97)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad98 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(98)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad99 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(99)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad100 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(100)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad101 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(101)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad102 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(102)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad103 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(103)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad104 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(104)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad105 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(105)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad106 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(106)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad107 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(107)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad108 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(108)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad109 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(109)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad110 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(110)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad111 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(111)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad112 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(112)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad113 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(113)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad114 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(114)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad115 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(115)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad116 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(116)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad117 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(117)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad118 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(118)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad119 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(119)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad120 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(120)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad121 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(121)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad122 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(122)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad123 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(123)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad124 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(124)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad125 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(125)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad126 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(126)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad127 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(127)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
module hbfd_rrl_pad128 (input wire clk, input wire rst_n_in, output wire rst_n);
    hbfd_rrl_stages #(.N(128)) u (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
endmodule
`default_nettype wire
