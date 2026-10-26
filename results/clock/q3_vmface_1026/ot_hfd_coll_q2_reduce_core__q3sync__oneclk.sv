// GENERATED opt-in clock adapter: inner RTL/reset/data unchanged.
`timescale 1ns/1ps
`default_nettype none
module ot_hfd_coll_q2_reduce_core__q3sync__oneclk (
    input wire clk,
    input wire reduce_rst_n,
    input wire reduce_clear,
    input wire reduce_in_v,
    input wire [544:0] reduce_in_flit,
    input wire reduce_load_v,
    input wire [3:0] reduce_load_tag,
    input wire reduce_add_read,
    input wire [3:0] reduce_read_tag,
    input wire reduce_add_issue,
    input wire reduce_pub_read,
    input wire [3:0] reduce_pub_tag_a,
    input wire [3:0] reduce_pub_tag_b,
    input wire reduce_pub_bf16,
    input wire [23:0] reduce_pub_meta,
    input wire reduce_pub_release,
    input wire reduce_pub_issue,
    output wire reduce_out_v,
    output wire [544:0] reduce_out_flit,
    output wire reduce_fault
);
    ot_hfd_coll_q2_reduce_core__q3sync u_core (
        .reduce_clk_control(clk),
        .reduce_clk_state({16{clk}}),
        .reduce_clk_add({16{clk}}),
        .reduce_rst_n(reduce_rst_n),
        .reduce_clear(reduce_clear),
        .reduce_in_v(reduce_in_v),
        .reduce_in_flit(reduce_in_flit),
        .reduce_load_v(reduce_load_v),
        .reduce_load_tag(reduce_load_tag),
        .reduce_add_read(reduce_add_read),
        .reduce_read_tag(reduce_read_tag),
        .reduce_add_issue(reduce_add_issue),
        .reduce_pub_read(reduce_pub_read),
        .reduce_pub_tag_a(reduce_pub_tag_a),
        .reduce_pub_tag_b(reduce_pub_tag_b),
        .reduce_pub_bf16(reduce_pub_bf16),
        .reduce_pub_meta(reduce_pub_meta),
        .reduce_pub_release(reduce_pub_release),
        .reduce_pub_issue(reduce_pub_issue),
        .reduce_out_v(reduce_out_v),
        .reduce_out_flit(reduce_out_flit),
        .reduce_fault(reduce_fault)
    );
endmodule
`default_nettype wire
