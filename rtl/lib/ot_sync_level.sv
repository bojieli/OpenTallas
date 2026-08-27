`timescale 1ns/1ps
// Two-flop synchronizer followed by destination-domain stable-state
// qualification.  Use for low-rate levels only, never for an encoded payload.
module ot_sync_level #(
    parameter integer WIDTH = 1,
    parameter integer QUAL_CYCLES = 3,
    parameter [WIDTH-1:0] RESET_VALUE = {WIDTH{1'b0}},
    parameter integer COUNT_W = (QUAL_CYCLES <= 1) ? 1 : $clog2(QUAL_CYCLES+1)
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [WIDTH-1:0]         async_in,
    output reg [WIDTH-1:0]          sync_out
`ifdef FORMAL
    , output wire [WIDTH-1:0]       formal_sync_ff2
    , output wire [WIDTH-1:0]       formal_candidate
    , output wire [COUNT_W-1:0]     formal_stable_count
`endif
);
    (* async_reg = "true" *) reg [WIDTH-1:0] sync_ff1;
    (* async_reg = "true" *) reg [WIDTH-1:0] sync_ff2;
    reg [WIDTH-1:0] candidate;
    reg [COUNT_W-1:0] stable_count;
`ifdef FORMAL
    assign formal_sync_ff2 = sync_ff2;
    assign formal_candidate = candidate;
    assign formal_stable_count = stable_count;
`endif

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sync_ff1 <= RESET_VALUE;
            sync_ff2 <= RESET_VALUE;
            candidate <= RESET_VALUE;
            stable_count <= {COUNT_W{1'b0}};
            sync_out <= RESET_VALUE;
        end else begin
            sync_ff1 <= async_in;
            sync_ff2 <= sync_ff1;
            if (sync_ff2 != candidate) begin
                candidate <= sync_ff2;
                stable_count <= {{(COUNT_W-1){1'b0}},1'b1};
            end else if (stable_count < QUAL_CYCLES) begin
                if (stable_count == QUAL_CYCLES-1)
                    sync_out <= candidate;
                stable_count <= stable_count + 1'b1;
            end else begin
                sync_out <= candidate;
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (WIDTH < 1 || QUAL_CYCLES < 2)
            $error("ot_sync_level requires WIDTH >= 1 and QUAL_CYCLES >= 2");
    end
`endif
endmodule
