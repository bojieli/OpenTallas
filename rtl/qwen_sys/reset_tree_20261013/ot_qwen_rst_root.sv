`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// qwen-tp8 2026-10-13: root of a registered reset tree (ot_qwen_rst_rep nodes, DEPTH cycles from the root to every
// leaf, equal for every leaf of a domain).
//   (a) STRETCH  root_n is held asserted for at least HOLD = DEPTH + MARGIN cycles after ANY assertion of req_n (a
//       one-cycle pulse included), so the reset-less tree flops are flushed and every leaf of the tree is in reset
//       together for >= MARGIN cycles before the first one leaves it.
//   (b) START GATE  start_ok rises HOLD cycles after root_n is released (every leaf has been out of reset for
//       >= MARGIN cycles) and falls with req_n; traffic sources (the KV sequencer's inputs, the system reset
//       sequencer's sys_ready) are gated by it.
// req_n is synchronous to clk (ot_reset_sync output / sequencer flop); por_n is the asynchronous power-on reset.
// MUT (bench only): 1 = no stretch (root_n follows req_n), 2 = start_ok MARGIN cycles after release (ignores DEPTH).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_rst_root #(
    parameter integer DEPTH  = 160,
    parameter integer MARGIN = 8,
    parameter integer MUT    = 0,
    parameter integer HOLD   = DEPTH + MARGIN,
    parameter integer CW     = $clog2(HOLD + 1)
) (
    input  wire clk,
    input  wire por_n,
    input  wire req_n,
    output reg  root_n,
    output reg  start_ok
);
    reg [CW-1:0] hold, rel;
    always @(posedge clk or negedge por_n) begin
        if (!por_n) begin
            root_n <= 1'b0; start_ok <= 1'b0; hold <= CW'(HOLD); rel <= {CW{1'b0}};
        end else if (!req_n) begin
            root_n <= 1'b0; start_ok <= 1'b0; hold <= CW'(HOLD); rel <= {CW{1'b0}};
        end else if (hold != 0 && MUT != 1) begin
            root_n <= 1'b0; hold <= hold - 1'b1;
        end else begin
            root_n <= 1'b1;
            if (rel == CW'((MUT == 2) ? MARGIN : HOLD)) start_ok <= 1'b1;
            else rel <= rel + 1'b1;
        end
    end
endmodule
