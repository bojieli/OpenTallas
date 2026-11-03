`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03 (RE-FORM, HBM-RF1 / d44v): ARG = the q3 edge argmax member (ot_hgi_coll_argmax_m_tp192_pr, no
// macros), cut out of ot_hfd_coll_q3_edge_core on its member boundary.  No new seam (all ports are core pins): 0 added cycles.
module ot_hfd_coll_q3_edge_arg (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire         mode,
    input  wire [7:0]   cfg_g,
    input  wire [7:0]   cfg_gbase,
    input  wire [7:0]   cfg_rank,
    input  wire [3:0]   in_slot,
    input  wire [3:0]   in_v,
    input  wire [255:0] in_key,
    input  wire [131:0] in_meta,
    input  wire         flush_slot,
    input  wire         publish_slot,
    output wire         out_v,
    output wire [544:0] out_flit,
    output wire         fault
);
    ot_hgi_coll_argmax_m_tp192_pr u_arg (
        .clk(clk), .rst_n(rst_n), .start(start), .mode(mode), .cfg_g(cfg_g), .cfg_gbase(cfg_gbase), .cfg_rank(cfg_rank),
        .in_slot(in_slot), .in_v(in_v), .in_key(in_key), .in_meta(in_meta), .flush_slot(flush_slot),
        .publish_slot(publish_slot), .out_v(out_v), .out_flit(out_flit), .fault(fault));
endmodule
`default_nettype wire
