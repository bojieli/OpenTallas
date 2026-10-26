`timescale 1ns/1ps
`default_nettype none
// ot_s81_static_lane_end -- equal-frequency (mesochronous) lane end on the fixed calendar (S-NET, 2026-10-15).
//
// Static successor of the ot_meso_fifo hub-end / crossing-stage FIFOs (dsfd_m2l_*, dsfd_xstg_515): no alignment
// training, no credits, no ready, no occupancy.  It is ot_s81_static_column_ingress (S-BIND, owner static rule) with the
// epoch exposed: i = {record W bits, marker}; the record is captured by a source pin register on the rising edge of the
// forwarded clock f_ck together with its marker; the destination epoch follows the captured marker through two ck
// flops; ot_s81_static_lane_cross (EPOCH_SHIFT 1, OFFSET 4, DEPTH 8) delivers source edge j at destination edge
// j + OFFSET - 1 for every word, bubbles included.  live = the destination epoch is running (the downstream lane's
// rst_n); fault = epoch slip / identity mismatch (assertion only, never re-times).
// rst_n is the destination root reset; it must release before the marker (the die reset tree guarantees it; tied 1
// where the stage has no own reset, then the marker alone defines the epoch).
module ot_s81_static_lane_end #(parameter integer W = 64, parameter integer OFFSET = 4) (
    input  wire         f_ck,
    input  wire [W:0]   i,
    input  wire         ck,
    input  wire         rst_n,
    output wire [W-1:0] o,
    output wire         live,
    output wire         fault
);
    reg [W:0] pin;
    always @(posedge f_ck) pin <= i;
    (* async_reg = "true" *) reg [1:0] epoch_reset;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) epoch_reset <= 2'b00;
        else epoch_reset <= {epoch_reset[0], pin[0]};
    assign live = epoch_reset[1];
    ot_s81_static_lane_cross #(.W(W), .OFFSET(OFFSET), .EPOCH_SHIFT(1)) u_cross (
        .w_ck(f_ck), .w_rst_n(pin[0]), .i(pin[W:1]),
        .r_ck(ck), .r_rst_n(epoch_reset[1]), .o(o), .fault(fault));
endmodule
`default_nettype wire
