// Opt-in structural prototype. Four dedicated input captures, +1 cr edge
// on landed data before the existing xa/xb/cc/x2 stage. Strap lk is named
// strap_lk in this opt-in successor; no pin coordinates or values change.
// Original dsfd_cfifo_crs4 and ot_s81_land remain unchanged.
`timescale 1ns/1ps
module dsfd_cfifo_crs4_pin_capture (
    output wire [14:0] cc,
    input wire cr,
    input wire cr_s,
    output wire [69:0] rd,
    input wire [65:0] ri,
    output wire rs,
    input wire rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    output wire [535:0] x2,
    input wire [275:0] xl0,      // lane k word = {old xd2, xd}[276k +: 276] (S81-DIE7/CRS4 10-18: one port per lane, so
    input wire [275:0] xl1,      // every lane port belongs to exactly ONE forwarded-clock domain xk[k] in the hardened
    input wire [275:0] xl2,      // view's multi-root ownership check; dsfd_cfifo_crs's xd / xd2 split lane 2 across
    input wire [275:0] xl3,      // two ports).  Bit order and S-face pin order unchanged.
    input wire [3:0] xk,         // lane k forwarded clock (lane k's last station ck_o)
    input wire [11:0] strap_lk         // lane k read offset K = lk[3k +: 3] (identity strap, die STA window rule L5)
);
    (* keep=1 *) reg [1:0] rsync_q; always @(posedge cr or negedge rst) if (!rst) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    (* keep=1 *) reg [1:0] rsyncs_q; always @(posedge cr_s or negedge rsync) if (!rsync) rsyncs_q <= 2'b00; else rsyncs_q <= {rsyncs_q[0], 1'b1};
    wire rsync_s = rsyncs_q[1];
    reg [65:0] ri_q; always @(posedge cr) ri_q <= ri;
    // Separate output Q, same D/clock/reset as the original rsync stage.
    (* keep=1 *) reg rs_port;
    always @(posedge cr or negedge rst)
        if (!rst) rs_port<=1'b0; else rs_port<=rsync_q[0];
    assign rs = rs_port;
    reg [1:0] sti; always @(posedge cr) sti <= st;
    // ---- per-lane landing (contract L1-L3): ring on xk[k], read on cr from the rsync release
    wire [1103:0] xin = {xl3, xl2, xl1, xl0};
    wire [1103:0] xl;
    wire [3:0] lf;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_lane
`ifdef OT_CRS4_MUT_NBR   // bench mutant: the dsfd_cfifo_crs gap -- lanes 0 / 3 written on the neighbour lane's clock
        wire ckl = xk[g == 0 ? 1 : (g == 3 ? 2 : g)];
`else
        wire ckl = xk[g];
`endif
        ot_s81_land_pin_capture #(.W(276), .D(4)) u_l (.k(strap_lk[3 * g +: 3]), .ck_f(ckl), .i(xin[276 * g +: 276]), .ck(cr), .rs(rsync),
                                           .o(xl[276 * g +: 276]), .fault(lf[g]));
    end endgenerate
    // bundle words as dsfd_cfifo_crs's ingress delivered them ({W:1} of each, marker stripped), bubbles before the marker
    wire [564:0] oa_ = xl[565:1] & {565{xl[0]}};
    wire [536:0] ob_ = xl[1103:567] & {537{xl[566]}};
    wire [1100:0] xw_ = {ob_[536:1], oa_};
    wire xflt = (|lf) | (oa_[0] ^ ob_[0]);
    wire xv = xw_[0];
    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [535:0] x2_r;
    always @(posedge cr) begin xa_r <= {xw_[283] & xv, xw_[282:1]}; xb_r <= xw_[549:284];
        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};
        x2_r <= {xw_[1100:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}; end
    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;
    (* keep=1 *) reg [67:0] rr; reg flt;
    always @(posedge cr_s or negedge rsync_s) if (!rsync_s) begin rr <= 68'd0; flt <= 1'b0; end
        else begin rr <= {sti[1] | flt, sti[0], ri_q}; flt <= flt | xflt; end
    // rd[2] keeps rr[0]; rd[1] and rd[0] get private zero-cycle Q copies.
    (* keep=1 *) reg rd1_port;
    (* keep=1 *) reg rd0_port;
    always @(posedge cr_s or negedge rsync_s)
        if(!rsync_s) rd1_port<=1'b0; else rd1_port<=ri_q[0];
    always @(posedge cr_s or negedge rsync)
        if(!rsync) rd0_port<=1'b0; else rd0_port<=rsyncs_q[0];
    assign rd = {rr, rd1_port, rd0_port};
endmodule
