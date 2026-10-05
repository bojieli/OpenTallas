`timescale 1ns/1ps
// Flow calibration, post-route. The simplest register-to-register path there is,
// replicated wide enough to floorplan and to carry a real clock tree.
//
// ot_probe_floor (a single flop) reports 8,691 MHz, but that is PRE-LAYOUT STA on
// an ideal clock, and it cannot be place-and-routed at all -- one flop does not fit
// a legal core area. A pre-layout number is not a ceiling for anything that has to
// be routed, which is the same reason synth-only timing was rejected for the MAC
// lanes.
//
// This is a 256-stage shift register: no combinational logic between stages, so
// whatever this closes at post-route is the practical ceiling of ASAP7 plus this
// flow, including clock-tree insertion delay and skew. No RTL restructuring can
// exceed it, and the gap between it and a real block is the part that is the
// design's own doing.
module ot_probe_floor_wide #(parameter integer STAGES = 256) (
    input  wire clk, input wire rst_n, input wire d, output wire q
);
    reg [STAGES-1:0] chain;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) chain <= {STAGES{1'b0}};
        else        chain <= {chain[STAGES-2:0], d};
    assign q = chain[STAGES-1];
endmodule
