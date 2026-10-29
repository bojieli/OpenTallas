// HBM-CORES-REBAL-5 lane cut of hnx_rp4lp4_leaf_selfcontained.sv (gen_lane_cut.py)
// The source is elaborated as a separate compilation unit by Slang. Keep the
// reset-edge macro local; read_verilog historically inherited it from hnx_rp4_leafh.
// The module bodies below are byte-identical to the 4d6f5439dc recipe source.
`ifndef OT_RP4_AR
`ifdef OT_SMH_RP4_SRST
`define OT_RP4_AR(c, r) posedge c
`else
`define OT_RP4_AR(c, r) posedge c or negedge r
`endif
`endif

module lx_gate (
    input wire clk, input wire r_bdc, input wire r_tcc, input wire r_g, input wire r_x,
    input wire iv_b, input wire ifirst, input wire ilast, input wire ifp4, input wire [15:0] itag,
    input wire [531:0] iwb, input wire [531:0] ixb_p,
    input wire sv_f, input wire sfirst, input wire slast, input wire [15:0] stag,
    input wire [255:0] swf, input wire [255:0] sxf,
    output wire [49:0] g
);
    localparam integer TAGW = 16, LBS = 2, LSB = 16;
    // XREL stations of lane p (the d4g leafh's xb_* / xf_*, per lane)
    reg xb_first, xb_last, xb_fp4, xf_first, xf_last;
    reg [TAGW-1:0] xb_tag, xf_tag;
    reg [LBS*266-1:0] xb_w, xb_x;
    reg [LSB*16-1:0] xf_w, xf_x;
`ifdef OT_SMH_RP4_SRST
    // HBM-CORES-REBAL-12 pin-registered valid stations (pinreg_cut.py): sync-reset gate behind the flops
    reg xb_vr, xf_vr, x_rq;
    always @(posedge clk) begin xb_vr <= iv_b; xf_vr <= sv_f; x_rq <= r_x; end
    wire xb_v = xb_vr, xf_v = x_rq & xf_vr;
`else
    reg xb_v, xf_v;
    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xb_v <= 0; else xb_v <= iv_b;
    always @(`OT_RP4_AR(clk, r_x)) if (!r_x) xf_v <= 0; else xf_v <= sv_f;
`endif
    always @(posedge clk) begin
        xb_first <= ifirst; xb_last <= ilast; xb_fp4 <= ifp4; xb_tag <= itag;
        xb_w <= iwb; xb_x <= ixb_p;
        xf_first <= sfirst; xf_last <= slast; xf_tag <= stag;
        xf_w <= swf; xf_x <= sxf;
    end
    wire bov, bfault, fov, ffault;
    wire [31:0] by, fy;
    wire [TAGW-1:0] btag, ftag;
    ot_hbm_accel_smh_bdc u_bdc (.clk(clk), .rst_a(r_bdc), .i_v(xb_v), .i_first(xb_first), .i_last(xb_last), .i_fp4(xb_fp4),
        .i_tag(xb_tag), .i_w(xb_w), .i_x(xb_x), .ov(bov), .y(by), .otag(btag), .fault(bfault));
    hnx_rp4_tcc u_tcc (.clk_hard({3{clk}}), .rst_a(r_tcc), .i_v(xf_v), .i_first(xf_first), .i_last(xf_last), .i_tag(xf_tag),
        .i_w(xf_w), .i_x(xf_x), .ov(fov), .y(fy), .otag(ftag), .fault(ffault));
    reg gv_q, gf_q;
    reg [31:0] gy_q;
    reg [TAGW-1:0] gt_q;
    always @(`OT_RP4_AR(clk, r_g))
        if (!r_g) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= bov | fov; gf_q <= bfault | ffault | (bov & fov); end
    always @(posedge clk) begin gy_q <= bov ? by : fy; gt_q <= bov ? btag : ftag; end
    wire gv = gv_q, gf = gf_q; wire [31:0] gy = gy_q; wire [15:0] gt = gt_q;
    assign g = {gv, gf, gy, gt};
endmodule
