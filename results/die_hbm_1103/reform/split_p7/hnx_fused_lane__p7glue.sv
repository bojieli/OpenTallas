// DIE-HBM-61/SPLIT d44v part 6 (u_core -> hnx_fused_lane__p7comp); from gen_core_kit_hbm.py (ELEM-HBM): pass-through wrapper, plan pins -> RTL top; wires only.
`default_nettype none
module hnx_fused_lane__fcore (
    input wire clk,
    input wire [127:0] dn_d,
    input wire [2:0] dn_op,
    input wire dn_v,
    input wire [7:0] dn_x,
    output wire fin,
    output wire flt,
    input wire [4:0] lid,
    input wire [31:0] r_d,
    input wire r_v,
    output wire [15:0] rq_s,
    output wire rq_v,
    input wire [255:0] rr_d,
    input wire rr_v,
    input wire rst_n,
    output wire [255:0] up_d,
    output wire up_t,
    output wire up_v,
    output wire [9:0] up_x,
    output wire [255:0] wq_d,
    output wire [15:0] wq_s,
    output wire wq_v
);
    hnx_fused_lane__p7comp u_core (
        .clk(clk),
        .dn_d(dn_d),
        .dn_op(dn_op),
        .dn_v(dn_v),
        .dn_x(dn_x),
        .fin(fin),
        .flt(flt),
        .lid(lid),
        .r_d(r_d),
        .r_v(r_v),
        .rq_s(rq_s),
        .rq_v(rq_v),
        .rr_d(rr_d),
        .rr_v(rr_v),
        .rst_n(rst_n),
        .up_d(up_d),
        .up_t(up_t),
        .up_v(up_v),
        .up_x(up_x),
        .wq_d(wq_d),
        .wq_s(wq_s),
        .wq_v(wq_v));
endmodule
`default_nettype wire

// DIE-HBM-61/SPLIT d44v part 6: plan module hnx_fused_lane = thin parent glue of the split hard core (wires only; the
// sub-cores of hnx_fused_lane__p7comp are the hard cores, each with its own kit face shell).  Ports open in the composition: none.
`default_nettype none
module hnx_fused_lane (
    input wire clk,
    input wire [127:0] dn_d,
    input wire [2:0] dn_op,
    input wire dn_v,
    input wire [7:0] dn_x,
    output wire fin,
    output wire flt,
    input wire [4:0] lid,
    input wire [31:0] r_d,
    input wire r_v,
    output wire [15:0] rq_s,
    output wire rq_v,
    input wire [255:0] rr_d,
    input wire rr_v,
    input wire rst_n,
    output wire [255:0] up_d,
    output wire up_t,
    output wire up_v,
    output wire [9:0] up_x,
    output wire [255:0] wq_d,
    output wire [15:0] wq_s,
    output wire wq_v
);
    hnx_fused_lane__fcore u_fcore (.clk(clk), .dn_d(dn_d), .dn_op(dn_op), .dn_v(dn_v), .dn_x(dn_x), .fin(fin), .flt(flt), .lid(lid), .r_d(r_d), .r_v(r_v), .rq_s(rq_s), .rq_v(rq_v), .rr_d(rr_d), .rr_v(rr_v), .rst_n(rst_n), .up_d(up_d), .up_t(up_t), .up_v(up_v), .up_x(up_x), .wq_d(wq_d), .wq_s(wq_s), .wq_v(wq_v));
endmodule
`default_nettype wire
