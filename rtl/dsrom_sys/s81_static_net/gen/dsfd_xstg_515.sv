`timescale 1ns/1ps
module dsfd_xstg_515 (
    input wire [0:0] ck,
    input wire [0:0] cw,
    input wire [514:0] i,
    output wire [514:0] o
);
    // S-NET --hend-static: end block (cw) -> band block (ck), same frequency, on the fixed calendar of
    // ot_s81_static_lane_end: pin register on cw (the old ir), epoch from the lane marker i[0], fixed
    // offset crossing; no meso FIFO / credits / trained placement.  o = {data, valid & live, live}.
    wire [513:0] xq; wire xl, xf_;
    ot_s81_static_lane_end #(.W(514)) u_x (.f_ck(cw[0]), .i(i), .ck(ck[0]), .rst_n(1'b1), .o(xq), .live(xl), .fault(xf_));
    reg [514:0] orr; always @(posedge ck[0]) orr <= {xq[513:1], xq[0] & xl, xl};
    assign o = orr;
endmodule
