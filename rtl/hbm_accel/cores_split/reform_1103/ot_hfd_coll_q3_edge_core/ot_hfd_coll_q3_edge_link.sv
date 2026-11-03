`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/SPLIT 11-03 (RE-FORM, HBM-RF1 / d44v): LINK = one q3 edge link (ot_hgi_coll_link_e_pr, 4 x
// ot_sram_1r1w_64x512_m1_r2c2 generated macros), cut out of ot_hfd_coll_q3_edge_core on its member boundary.
// Three identical replicas per q3 edge (links 0..2).  The uncut core has no member-to-member wire, so there is no new seam:
// every port here is a core pin, 0 added cycles.  One clock: the member's 5 clock bits (ctl + 4 banks) are the one plan
// clock (as ot_hfd_coll_q3_edge_core__wrap).  fault_cause is unconnected in the uncut core (dropped here too).
module ot_hfd_coll_q3_edge_link (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         epoch_begin,
    input  wire [7:0]   epoch_new,
    input  wire [7:0]   held_epoch,
    input  wire         wr_v,
    input  wire         wr_observed_v,
    input  wire [15:0]  wr_seq,
    input  wire [544:0] wr_flit,
    input  wire         rd_v,
    input  wire [15:0]  rd_seq,
    input  wire         rx_expect_v,
    input  wire [15:0]  rx_expect_seq,
    input  wire         phy_up,
    input  wire         rx_pin_v,
    input  wire [611:0] rx_pin_flit,
    output wire         tx_pin_v,
    output wire [611:0] tx_pin_flit,
    output wire         rx_v,
    output wire [544:0] rx_flit,
    output wire         epoch_abort,
    output wire         retry_requested
);
    wire [10:0] fault_cause_nc;
    ot_hgi_coll_link_e_pr u_link (
        .ck({5{clk}}), .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch_new(epoch_new), .held_epoch(held_epoch),
        .wr_v(wr_v), .wr_observed_v(wr_observed_v), .wr_seq(wr_seq), .wr_flit(wr_flit),
        .rd_v(rd_v), .rd_seq(rd_seq), .rx_expect_v(rx_expect_v), .rx_expect_seq(rx_expect_seq), .phy_up(phy_up),
        .tx_pin_v(tx_pin_v), .tx_pin_flit(tx_pin_flit), .rx_pin_v(rx_pin_v), .rx_pin_flit(rx_pin_flit),
        .rx_v(rx_v), .rx_flit(rx_flit), .epoch_abort(epoch_abort), .retry_requested(retry_requested),
        .fault_cause(fault_cause_nc));
endmodule
`default_nettype wire
