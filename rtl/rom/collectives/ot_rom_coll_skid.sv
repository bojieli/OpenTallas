`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Two-entry elastic register slice: full rate, registered data AND registered
// ready, so no ready path crosses it.  Every stage boundary of the collective
// engines is one of these; the data registers carry no reset.
// ---------------------------------------------------------------------------
module ot_rom_coll_skid #(
    parameter integer W = 8
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [W-1:0] in_data,
    output wire         out_valid,
    input  wire         out_ready,
    output wire [W-1:0] out_data
);
    reg [W-1:0] d0, d1;
    reg         v0, v1;
    assign out_valid = v0;
    assign out_data  = d0;
    assign in_ready  = !v1;
    wire push = in_valid && !v1;
    wire free = !v0 || out_ready;          // d0 is empty or drains this cycle
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            v0 <= 1'b0; v1 <= 1'b0;
        end else if (free) begin
            v0 <= v1 || push;
            v1 <= 1'b0;
        end else if (push) begin
            v1 <= 1'b1;
        end
    end
    always @(posedge clk) begin
        if (free) d0 <= v1 ? d1 : in_data;
        if (!free && push) d1 <= in_data;
    end
endmodule
