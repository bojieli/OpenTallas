`timescale 1ns/1ps
// Two-flop level synchronizer.  Multi-bit payloads use this only for a stable
// control vector held by the source until an acknowledgement; it is not a bus
// sampling primitive.
module ot_sync_bits #(
    parameter integer WIDTH = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [WIDTH-1:0]     async_in,
    output wire [WIDTH-1:0]     sync_out
);
    (* async_reg = "true" *) reg [WIDTH-1:0] sync_ff1;
    (* async_reg = "true" *) reg [WIDTH-1:0] sync_ff2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_ff1 <= {WIDTH{1'b0}};
            sync_ff2 <= {WIDTH{1'b0}};
        end else begin
            sync_ff1 <= async_in;
            sync_ff2 <= sync_ff1;
        end
    end
    assign sync_out = sync_ff2;
endmodule
