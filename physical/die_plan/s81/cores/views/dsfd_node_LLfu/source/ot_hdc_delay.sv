`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule
