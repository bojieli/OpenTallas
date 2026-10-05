`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical cut of one trunk segment of the pipelined local K arbitration
// (ot_chip_v41x_hbm_karb_pipe): the widest trunk word (the request chain: valid,
// local PC, AW = 30 address, length, tag, write flag, 256 data bits, 32 strobes
// = 342 bits) through two chain registers of ot_chip_v41x_karb_pipe.
// tools/v41x_karb_local_pnr.py places d on the west edge and q on the east
// edge of a die one segment long, with a large I/O delay so both registers sit
// at their pins: the routed register-to-register path is the segment.
// ---------------------------------------------------------------------------
module ot_v41x_karb_link_cut (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [341:0] d,
    output wire [341:0] q
);
    ot_chip_v41x_karb_pipe #(.W(342), .V(1), .N(2)) u_seg (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule
