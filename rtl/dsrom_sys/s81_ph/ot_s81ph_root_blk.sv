`timescale 1ns/1ps
// ot_s81ph_root_blk -- one S81 return region root as a hardened sub-block of dsfd_sp_gather (CLAUDE S81-PH).
// The unchanged W10 ot_v41_ret_root (D = QD = ROOTD, 128 as the field / S81 physical return contract) between a
// pin input register and a pin output register.  i = node word {e, d32, t32, v}; o = {e, pos3, row16, fp32, v}.
// rs: active-low reset, synchronised by the parent (one copy per 16 roots).
module ot_s81ph_root_blk #(parameter integer ROOTD = 128) (
    input  wire [0:0]  ck,
    input  wire [0:0]  rs,
    input  wire [65:0] i,
    output reg  [52:0] o,
    output reg  [0:0]  f
);
    reg [65:0] iq;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) iq <= 66'd0; else iq <= i;
    wire rv, re, rf; wire [15:0] rrow, rbf; wire [2:0] rpos; wire [31:0] rfp;
    ot_v41_ret_root #(.D(ROOTD), .QD(ROOTD)) u_root (.clk(ck[0]), .rst_n(rs[0]), .i_v(iq[0]), .i_t(iq[32:1]), .i_d(iq[64:33]),
        .i_e(iq[65]), .r_v(rv), .r_row(rrow), .r_pos(rpos), .r_fp32(rfp), .r_bf16(rbf), .r_e(re), .fault(rf));
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) begin o[0] <= 1'b0; f <= 1'b0; end else begin o[0] <= rv; f <= rf; end
    always @(posedge ck[0]) o[52:1] <= {re, rpos, rrow, rfp};
endmodule
