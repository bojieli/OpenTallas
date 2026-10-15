`timescale 1ns/1ps
// q15 port-tiles (2026-10-15): plain 512-bit one-edge register bank master for the port_tiles parent's ck-domain
// pass-through / face registers (tw_q, ty_copy, ty_local, rq_q data, words output_q data).  No reset: those RTL
// registers have none, so the bank is exact (no tied reset pin, no added reset edge).  MUT (bench only): 1 bypass,
// 2 bit-0 inversion.
module qfd_slab_reg512 #(parameter integer MUT=0) (
    input  wire         ck,
    input  wire [511:0] d,
    output wire [511:0] q
);
    (* keep = "true" *) reg [511:0] data_q;
    always @(posedge ck) data_q <= d;
    assign q = (MUT==1) ? d : (MUT==2) ? (data_q ^ 512'd1) : data_q;
endmodule
