`timescale 1ns/1ps
// SCREEN FIXTURE ONLY (DS-ROM recovery lever "field" spine screen): a register-bounded stand-in for the PINNED
// quantiser rtl/hdc/v41/ot_hdc_actquant.sv, which the PQ spine instantiates unchanged from the pinned spine.  It is
// not new hardware and is not screened here; its outputs come from registers, as the real module's do, so the new
// spine logic that consumes them is timed register to register.  Not functional.
module ot_hdc_actquant (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          fp4,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [255:0]  q,
    output reg  signed [9:0] e,
    output reg  [511:0]  y,
    output reg           fault
);
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vo <= 1'b0; fault <= 1'b0; end
        else begin vo <= v; fault <= fp4 & v; end
    always @(posedge clk) begin
        for (i = 0; i < 32; i = i + 1) q[8*i +: 8] <= x[32*i + 24 +: 8] ^ x[32*i +: 8];
        e <= x[1023:1014]; y <= x[511:0] ^ x[1023:512];
    end
endmodule
