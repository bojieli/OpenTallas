module dsfd_cfifo (
    output wire [14:0] cc,
    input wire [0:0] ck,
    output wire [0:0] co,
    output wire [69:0] rd,
    output wire [0:0] rf,
    input wire [65:0] ri,
    output wire [0:0] rs,
    input wire [0:0] rst,
    input wire [1:0] st,
    output wire [282:0] xa,
    output wire [265:0] xb,
    input wire [565:0] xd,
    input wire [0:0] xf
);
    reg [1:0] rsync_q; always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rsync_q <= 2'b00; else rsync_q <= {rsync_q[0], 1'b1};
    wire rsync = rsync_q[1];
    assign co = ck;          // column clock-tree root (option C region root)
    assign rs = rsync;
    wire xv, wl, rl, wf, rf_, wr; wire [563:0] xq;
    ot_meso_fifo #(.W(564), .ENABLE(1'b1)) u_x (.wclk(xf[0]), .wrst_n(xd[0]), .w_v(xd[1]), .w_rdy(wr), .w_d(xd[565:2]), .rclk(ck[0]), .rrst_n(rsync), .r_v(xv), .r_rdy(1'b1), .r_d(xq), .w_live(wl), .r_live(rl), .w_fault(wf), .r_fault(rf_));
    // lane stream {x0 283 | x1 266 | cc 15}; xs_v, go and cfg_go qualified by the FIFO valid
    assign xa = {xq[282] & xv, xq[281:0]};
    assign xb = xq[548:283];
    assign cc = {xq[563:551], xq[550] & xv, xq[549] & xv};
    reg [67:0] rr; reg flt;
    always @(posedge ck[0] or negedge rsync) if (!rsync) begin rr <= 68'd0; flt <= 1'b0; end
        else begin rr <= {st[1] | flt, st[0] | ~rl, ri}; flt <= flt | wf | rf_ | (xd[1] & ~wr); end
    assign rf = ck;
    assign rd = {rr, rr[0], rsync};   // {status, root word, valid = root o_v, rst_n}
endmodule
