// dsfd_cfifo, static x2-pair column entry (S-ELEM-PQ/COLL 2026-10-16, VIS-ROM finding S81F-02).
// Module text of of the die glue the current die binds: c21h (ot-epyc4 s81-die-iter/c21h/nl/die_glue.sv,
// sha256 80fe6f54..., module text sha256 e892a5bb...) with TWO edits: (1) the 1-bit ports (cr rs rst xf xf2) are declared scalar
// instead of [0:0] (same width; the ref_tile flow names 1-bit pins by base name); (2) the two CLOCK FEED-THROUGHS of
// the die glue are removed: ck -> co (column clock root) and cr -> rf (return-lane forwarded clock) were wires through
// the hard tile (no sink inside; a hard view cannot own a clock feed-through as a registered IO domain).  The die drives
// ck_col_<r> and the rd return-lane clock from its own column clock root instead (S-DIE REBIND REQUEST 2026-10-16).
// Emitted by tools/dsrom_s81_fulldie.py with
// --bf-x2-static --bf-x2-pair --cfifo-colck (branch 'mst == dsfd_cfifo and BF_X2_STATIC', BF_X2_PAIR).
// Ports = die.v binding: xd2[537:0] / xf2 (the x2 extension lane) present; every data input is pin-captured
// (xd on xf, xd2 on xf2 inside ot_s81_static_column_ingress, ri/st on cr) and every data output is a flop
// (xa/xb/cc/x2/rd/rs).  Clock roots: cr (core), xf, xf2 (forwarded lane clocks).
// Static: no occupancy, ready or credit (owner static-cycle rule).
`timescale 1ns/1ps
module dsfd_cfifo (
    output wire [14:0] cc,
    input wire cr,
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
    reg [1:0] rsync_q; always @(posedge cr or negedge rst) if (!rst) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    // --bf-x2-static (S-BIND 2026-10-15, owner static-cycle rule): column entry = ot_s81_static_column_ingress
    // (pin capture of the forwarded record on xf, fixed epoch shift from the forwarded reset marker, no
    // occupancy / ready / credit).  xd = {x2 536 | cc 15 | x1 266 | x0 283 | v | rst_n}: one packed word.
    assign rs = rsync;
    reg [1:0] sti; always @(posedge cr) sti <= st;
    wire [1100:0] xw_; wire xflt;
    wire [564:0] oa_; wire [536:0] ob_; wire fa_, fb_;
    ot_s81_static_column_ingress #(.W(565)) u_x (.f_ck(xf), .i(xd), .ck(cr), .rst_n(rsync), .o(oa_), .fault(fa_));
    ot_s81_static_column_ingress #(.W(537)) u_x2 (.f_ck(xf2), .i(xd2), .ck(cr), .rst_n(rsync), .o(ob_), .fault(fb_));
    assign xw_ = {ob_[536:1], oa_}; assign xflt = fa_ | fb_ | (oa_[0] ^ ob_[0]);
    wire xv = xw_[0];
    reg [282:0] xa_r; reg [265:0] xb_r; reg [14:0] cc_r; reg [535:0] x2_r;
    always @(posedge cr) begin xa_r <= {xw_[283] & xv, xw_[282:1]}; xb_r <= xw_[549:284];
        cc_r <= {xw_[564:552], xw_[551] & xv, xw_[550] & xv};
        x2_r <= {xw_[1100:570], xw_[569] & xv, xw_[568:566], xw_[565] & xv}; end
    assign xa = xa_r; assign xb = xb_r; assign cc = cc_r; assign x2 = x2_r;
    reg [67:0] rr; reg flt;
    always @(posedge cr or negedge rsync) if (!rsync) begin rr <= 68'd0; flt <= 1'b0; end
        else begin rr <= {sti[1] | flt, sti[0], ri}; flt <= flt | xflt; end
    assign rd = {rr, rr[0], rsync};   // {status, root word, valid = root o_v, rst_n}
endmodule
