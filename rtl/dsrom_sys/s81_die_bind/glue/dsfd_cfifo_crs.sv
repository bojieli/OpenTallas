// Additive, opt-in S81 static x2-pair CFIFO. No default die instance binds this master.
// cr and cr_s are continuously running phase-0 roots of the same PLL, with real
// compensated entry delivery. xd/xd2 capture on xf/xf2; ri/st capture on cr.
// North cr owns xa/xb/cc/x2/rs; south cr_s owns ingress core stages and rd.
// Relative to legacy dsfd_cfifo: ri->rd adds one fixed edge and 66 capture bits;
// the separate south reset adds two FF. The reset frontier adds two initialization
// edges versus r3, zero further state or streaming edges. Forwarded markers must
// arrive after the fourth corresponding root edge following raw rst release.
// No ready/occupancy/training; every bubble follows the same fixed calendar.
// Parent clock branches, literal pins and compiler calendars require explicit
// integration. Existing dsfd_cfifo RTL and generator defaults remain unchanged.
`timescale 1ns/1ps
module dsfd_cfifo_crs (
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
    input wire [565:0] xd,
    input wire xf,
    output wire [535:0] x2,
    input wire [537:0] xd2,
    input wire xf2
);
    // r3 CR SPLIT (S-ELEM-PQ 2026-10-16, closure-first after south96 native FAIL: cr R 222.2 / spread 70.9, launch xb 247.6,
    // capture ri 339.0): two CTS roots of the SAME PLL clock at phase 0 -- cr (north: ri/st pin capture, xa/xb/cc/x2
    // output flops, rs) and cr_s (south: column ingress core side, status word rr -> rd).  ri gets a pin register on cr
    // (+1 edge on ri -> rd, now 2 edges like st; the compiler's status calendar takes the fixed +1).  Each root has its
    // own reset synchroniser; r4 below stages south reset from the registered north reset.
    reg [1:0] rsync_q; always @(posedge cr or negedge rst) if (!rst) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    // r4 reset frontier: raw north rst terminates in the north synchronizer.
    // South reset observes its registered release through its own two flops.
    // +2 initialization edges versus r3; no data/status edge change. Recovery
    // and removal from rsync to cr_s remain ordinary timed related-root paths.
    reg [1:0] rsyncs_q; always @(posedge cr_s or negedge rsync) if (!rsync) rsyncs_q <= 2'b00; else rsyncs_q <= {rsyncs_q[0], 1'b1};
    wire rsync_s = rsyncs_q[1];
    reg [65:0] ri_q; always @(posedge cr) ri_q <= ri;      // ri pin register (north root)
    // --bf-x2-static (S-BIND 2026-10-15, owner static-cycle rule): column entry = ot_s81_static_column_ingress
    // (pin capture of the forwarded record on xf, fixed epoch shift from the forwarded reset marker, no
    // occupancy / ready / credit).  xd = {x2 536 | cc 15 | x1 266 | x0 283 | v | rst_n}: one packed word.
    assign rs = rsync;
    reg [1:0] sti; always @(posedge cr) sti <= st;
    wire [1100:0] xw_; wire xflt;
    wire [564:0] oa_; wire [536:0] ob_; wire fa_, fb_;
    ot_s81_static_column_ingress #(.W(565)) u_x (.f_ck(xf), .i(xd), .ck(cr_s), .rst_n(rsync_s), .o(oa_), .fault(fa_));
    ot_s81_static_column_ingress #(.W(537)) u_x2 (.f_ck(xf2), .i(xd2), .ck(cr_s), .rst_n(rsync_s), .o(ob_), .fault(fb_));
    assign xw_ = {ob_[536:1], oa_}; assign xflt = fa_ | fb_ | (oa_[0] ^ ob_[0]);
    wire xv = xw_[0];
    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [535:0] x2_r;
    always @(posedge cr) begin xa_r <= {xw_[283] & xv, xw_[282:1]}; xb_r <= xw_[549:284];
        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};
        x2_r <= {xw_[1100:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}; end
    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;
    reg [67:0] rr; reg flt;
    always @(posedge cr_s or negedge rsync_s) if (!rsync_s) begin rr <= 68'd0; flt <= 1'b0; end
        else begin rr <= {sti[1] | flt, sti[0], ri_q}; flt <= flt | xflt; end
    assign rd = {rr, rr[0], rsync_s};   // {status, root word, valid = root o_v, rst_n}
endmodule
