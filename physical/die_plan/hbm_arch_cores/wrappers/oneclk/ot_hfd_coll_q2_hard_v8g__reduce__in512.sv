// DIE-HBM-65 11-04: d44v part 9 pin table: in_flit[544:512] are unread by the RTL (16 x 32 bits read, ot_hgi_coll_reduce_static.sv) and were already dropped by the face shell in the signed record.
// Planned common-root wiring of existing native cut; pin table 07982cfbef37edd49280a29e1b6e3963e734969a260e057a2f4bb3c728253534.
// Clock replicas clk_reduce[33]; arithmetic and other terminal wiring unchanged.
`default_nettype none
module ot_hfd_coll_q2_hard_v8g__reduce (
    input wire u_reduce_pub_bf16,
    input wire u_reduce_pub_issue,
    input wire u_reduce_pub_read,
    input wire u_reduce_pub_release,
    output wire u_reduce_fault,
    input wire [3:0] u_reduce_load_tag,
    input wire [3:0] u_reduce_pub_tag_a,
    input wire [3:0] u_reduce_pub_tag_b,
    input wire [3:0] u_reduce_read_tag,
    input wire [23:0] u_reduce_pub_meta,
    input wire clk,
    input wire rst_n,
    input wire u_reduce_add_issue,
    input wire u_reduce_add_read,
    input wire u_reduce_clear,
    input wire u_reduce_in_v,
    input wire u_reduce_load_v,
    input wire [511:0] u_reduce_in_flit,
    output wire u_reduce_out_v,
    output wire [544:0] u_reduce_out_flit
);
    wire c_reduce_out_v;
    wire [544:0] c_reduce_out_flit;
    wire c_reduce_fault;
    ot_hfd_coll_q2_reduce_core u_core (
        .reduce_clk_control(clk),
        .reduce_clk_state({16{clk}}),
        .reduce_clk_add({16{clk}}),
        .reduce_rst_n(rst_n),
        .reduce_clear(u_reduce_clear),
        .reduce_in_v(u_reduce_in_v),
        .reduce_in_flit({33'd0, u_reduce_in_flit}),
        .reduce_load_v(u_reduce_load_v),
        .reduce_load_tag(u_reduce_load_tag[3:0]),
        .reduce_add_read(u_reduce_add_read),
        .reduce_read_tag(u_reduce_read_tag[3:0]),
        .reduce_add_issue(u_reduce_add_issue),
        .reduce_pub_read(u_reduce_pub_read),
        .reduce_pub_tag_a(u_reduce_pub_tag_a[3:0]),
        .reduce_pub_tag_b(u_reduce_pub_tag_b[3:0]),
        .reduce_pub_bf16(u_reduce_pub_bf16),
        .reduce_pub_meta(u_reduce_pub_meta[23:0]),
        .reduce_pub_release(u_reduce_pub_release),
        .reduce_pub_issue(u_reduce_pub_issue),
        .reduce_out_v(c_reduce_out_v),
        .reduce_out_flit(c_reduce_out_flit),
        .reduce_fault(c_reduce_fault));
    assign u_reduce_fault = c_reduce_fault;
    assign u_reduce_out_v = c_reduce_out_v;
    assign u_reduce_out_flit = c_reduce_out_flit[544:0];
endmodule
`default_nettype wire
