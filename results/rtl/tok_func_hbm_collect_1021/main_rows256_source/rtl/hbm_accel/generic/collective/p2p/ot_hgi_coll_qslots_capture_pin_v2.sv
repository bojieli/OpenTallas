`timescale 1ns/1ps
`default_nettype none
// Additive physical candidate: every data/check input is captured at its pin.
// Payload and published reservation retain the exact original capture edge.
// The exceptional sticky capture-fault observation moves one edge later:
// source C -> fault C+1, before the normal qslots destination C+2 publication.
// This is an explicit fault ABI change, not parent/default adoption or a kill
// guarantee. Parent fault aggregation/visibility and physical delivery are OPEN.
module ot_hgi_coll_qslots_capture_pin_v2 #(
    parameter integer NS=1,PWT=545
)(
    input wire clk,rst_n,
    input wire [NS-1:0] src_v,capture_slot,
    input wire [NS*PWT-1:0] src_d,
    output reg [NS*PWT-1:0] captured,
    output reg [NS-1:0] captured_slot,
    output reg fault
);
    reg [NS-1:0] src_v_p;
    always @(posedge clk) captured <= src_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin src_v_p <= '0; captured_slot <= '0; fault <= 1'b0; end
        else begin
            src_v_p <= src_v;
            captured_slot <= capture_slot;
            if (src_v_p != captured_slot) fault <= 1'b1;
        end
endmodule
`default_nettype wire
