`timescale 1ns/1ps
`default_nettype none
// Bench-only adapter: presents ot_hgi_coll_ring_ag under the ring_v5 component name and port
// set (tx_gather=0), so the UNCHANGED tb_hgi_coll_pring_captured_static suite (6 waves x 8 tags
// all-reduce + 11 reservation-fault scenarios) checks that the successor keeps ring_v5 timing.
module ot_hgi_coll_pring_captured_static #(
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0, MUT_CARRY=0, MUT_TAG=0
)(
    input wire clk, rst_n, input wire [7:0] clk_state, clk_add, input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i, output wire [279:0] cw_o, ccw_o,
    input wire lp_we, input wire [2:0] lp_tag, input wire [255:0] lp_data,
    input wire state_read_add, state_read_tx, state_read_rr,
    input wire [2:0] state_add_tag, state_tx_tag, state_rr_tag, input wire [1:0] state_add_src,
    input wire state_add_rhs_acc, state_tx_acc,
    input wire add_v, input wire [2:0] add_tag, input wire [1:0] add_src, input wire add_rhs_acc,
    input wire [1:0] tx_inject, tx_forward, input wire [2:0] tx_tag, input wire [1:0] tx_dst,
    input wire tx_result, tx_acc, input wire [1:0] rx_slot, input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag, input wire rr_local, input wire [2:0] rr_local_tag,
    output wire rr_v, output wire [2:0] rr_tag, output wire [255:0] rr_d, output wire fault
);
    wire [1:0] ag_v;wire [3:0] ag_src;wire [5:0] ag_tag;wire [511:0] ag_d;
    ot_hgi_coll_ring_ag #(.NT(NT),.LAT(LAT),.SPLIT_CLOCKS(SPLIT_CLOCKS),.AG(`RING_AG),.MUT_CARRY(MUT_CARRY),.MUT_TAG(MUT_TAG)) u(
        .clk_ctl(clk),.tx_gather(1'b0),.tx_ttl(4'd0),.*);
endmodule
`default_nettype wire
