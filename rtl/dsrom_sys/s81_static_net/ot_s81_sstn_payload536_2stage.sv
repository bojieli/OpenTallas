`timescale 1ns/1ps
// Opt-in two-stage successor of the 536-bit station payload: one capture/launch pair per bit.
// The extra stage adds exactly one data/calendar edge, no bandwidth change. Valid bits0/4 are the only reset state.
module ot_s81_sstn_payload536_2stage (
    input wire ck, rs,
    input wire [535:0] i,
    output wire [535:0] o
);
    reg [530:0] capture_hi, launch_hi;
    reg [2:0] capture_lo, launch_lo;
    reg [1:0] capture_valid, launch_valid;
    always @(posedge ck) begin
        capture_hi <= i[535:5];
        capture_lo <= i[3:1];
        launch_hi <= capture_hi;
        launch_lo <= capture_lo;
    end
    always @(posedge ck or negedge rs) begin
        if (!rs) begin capture_valid <= 2'b00; launch_valid <= 2'b00; end
        else begin capture_valid <= {i[4], i[0]}; launch_valid <= capture_valid; end
    end
    assign o = {launch_hi, launch_valid[1], launch_lo, launch_valid[0]};
endmodule
