`timescale 1ns/1ps
`default_nettype none
// Physical static capture lane. The input/flush registers formerly in the parent
// live inside this hard boundary. No cycle is added: parent flush is the combinational
// drained-edge predicate which previously fed the parent's flush register.
module dsfd_vm_static_cap_leaf #(parameter integer E=8, parameter integer PIPE=0) (
    input wire ck, rn,
    input wire [3:0] gid,
    input wire [831:0] f_c,
    input wire flush,
    output wire o_v, output wire [13:0] o_row,
    output wire [15:0] o_m, output wire [511:0] o_d,
    output wire [4:0] flt
);
    reg [831:0] pin_c;
    reg [3:0] pin_gid;
    reg pin_flush;
    always @(posedge ck) begin
        pin_c <= rn ? f_c : 832'd0;
        pin_gid <= gid;
        if (!rn) pin_flush <= 1'b0;
        else pin_flush <= flush;
    end
    generate if (PIPE == 0) begin : legacy
        dsfd_vm_static_capl #(.E(E)) u_l (.ck(ck), .rn(rn), .gid(pin_gid), .f_c(pin_c), .flush(pin_flush),
        .o_v(o_v), .o_row(o_row), .o_m(o_m), .o_d(o_d), .flt(flt));
    end else begin : staged
        dsfd_vm_static_capl_pipe #(.E(E)) u_l (.ck(ck), .rn(rn), .gid(pin_gid), .f_c(pin_c), .flush(pin_flush),
            .o_v(o_v), .o_row(o_row), .o_m(o_m), .o_d(o_d), .flt(flt));
    end endgenerate
endmodule
`default_nettype wire
