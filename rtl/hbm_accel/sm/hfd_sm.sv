`default_nettype none
// hfd_sm: HBM die master of one SM (H-DIE 10-14, contract v14 sm_native_abi).  Wires only: the die bundles of
// tools/die_top_lint.py real_blocks('hbm') hfd_sm binding onto the native hierarchical SM ot_hbm_accel_smh (production
// parameters).  Bit 0 of every bundle first.
//   d 1,099 in   {rsp_data 1088, rsp_tag 10, rsp_v}
//   q    44      {req_ready (in), req_tag 10, req_addr 32, req_v}            (bits 0-42 out, bit 43 in)
//   x 2,063 in   {xw_data 2048, xw_grp 7, xw_addr 7, xw_en}
//   r   269 out  {rdata 256, rrow 12, rv}             (fault rides the control leaf to the record, its RTL consumer)
//   c   111      {fault, arrive, d_ready, start_ready (out) | cg_en, release_in, d_lines 24, d_base 32, d_valid, op_xb 7,
//                 op_fmt 2, op_gs, op_g 8, op_c 16, op_rows 13, start (in)}  = ot_hgi_sm_record sm_cmd 106 + sm_cg_en + sm_ret 4
// Production defines (results/arch/hbm_native_1013/sm/component.json) include OT_SMH_CG: cg_en is a real input.
// busy / released have no RTL consumer on the die (left open, never tied).
module hfd_sm (
    input  wire          ck,
    input  wire          rst,
    input  wire [1098:0] d,
    inout  wire [43:0]   q,
    input  wire [2062:0] x,
    output wire [268:0]  r,
    inout  wire [110:0]  c
);
    wire busy_open, released_open;
    ot_hbm_accel_smh u_sm (
        .clk(ck), .rst_n(rst),
        .start(c[0]), .start_ready(c[107]),
        .op_rows(c[13:1]), .op_c(c[29:14]), .op_g(c[37:30]), .op_gs(c[38]), .op_fmt(c[40:39]), .op_xb(c[47:41]),
        .busy(busy_open),
        .d_valid(c[48]), .d_ready(c[108]), .d_base(c[80:49]), .d_lines(c[104:81]),
        .req_v(q[0]), .req_ready(q[43]), .req_addr(q[32:1]), .req_tag(q[42:33]),
        .rsp_v(d[0]), .rsp_tag(d[10:1]), .rsp_data(d[1098:11]),
        .xw_en(x[0]), .xw_addr(x[7:1]), .xw_grp(x[14:8]), .xw_data(x[2062:15]),
        .rv(r[0]), .rrow(r[12:1]), .rdata(r[268:13]),
        .fault(c[110]), .arrive(c[109]),
        .release_in(c[105]), .released(released_open)
`ifdef OT_SMH_CG
        , .cg_en(c[106])
`endif
    );
endmodule
`default_nettype wire
