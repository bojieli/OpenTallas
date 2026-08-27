`timescale 1ns/1ps
// Atomic multi-sink transaction-credit reservation.  A reservation succeeds
// only when every named terminal has a free slot; release returns each credit
// exactly once.  Widened arithmetic and sticky diagnostics make wraparound
// impossible to hide in the public reference.
module ot_credit_manager #(
    parameter integer SINKS = 8,
    parameter integer DEPTH = 16,
    parameter integer CREDIT_W = (DEPTH <= 2) ? 1 : $clog2(DEPTH+1)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         reserve_valid,
    output wire                         reserve_ready,
    input  wire [SINKS-1:0]             reserve_mask,
    input  wire                         release_valid,
    input  wire [SINKS-1:0]             release_mask,
    output wire [SINKS*CREDIT_W-1:0]    free_count,
    output reg                          overflow_error,
    output reg                          underflow_error,
    output reg                          conservation_error
);
    reg [CREDIT_W-1:0] free [0:SINKS-1];
    integer i;
    reg all_available;
    reg [CREDIT_W:0] next_count;
    reg [CREDIT_W-1:0] free_value;
    wire reserve_fire;
    wire release_fire = release_valid;

    always @* begin
        all_available = 1'b1;
        for (i = 0; i < SINKS; i = i + 1)
            // A terminal release in this cycle can fund the atomic replacement
            // reservation, avoiding a bubble at full occupancy.
            if (reserve_mask[i] && (free[i] == 0) &&
                !(release_valid && release_mask[i]))
                all_available = 1'b0;
    end
    assign reserve_ready = all_available;
    assign reserve_fire = reserve_valid && reserve_ready;
    genvar g;
    generate
        for (g = 0; g < SINKS; g = g + 1) begin : GEN_FREE
            assign free_count[g*CREDIT_W +: CREDIT_W] = free[g];
        end
    endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            overflow_error <= 1'b0;
            underflow_error <= 1'b0;
            conservation_error <= 1'b0;
            for (i = 0; i < SINKS; i = i + 1)
                free[i] <= DEPTH;
        end else begin
            for (i = 0; i < SINKS; i = i + 1) begin
                next_count = free[i];
                if (release_fire && release_mask[i]) begin
                    if (next_count >= DEPTH) begin
                        overflow_error <= 1'b1;
                        conservation_error <= 1'b1;
                    end else begin
                        next_count = next_count + 1'b1;
                    end
                end
                if (reserve_fire && reserve_mask[i]) begin
                    if (next_count == 0) begin
                        underflow_error <= 1'b1;
                        conservation_error <= 1'b1;
                    end else begin
                        next_count = next_count - 1'b1;
                    end
                end
                free[i] <= next_count[CREDIT_W-1:0];
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (SINKS < 1 || DEPTH < 2)
            $error("ot_credit_manager requires positive sinks and depth >= 2");
    end
`endif
endmodule
