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

// Integrated clock gate: gclk follows clk while en was high at the clock's
// last low phase, and stays low otherwise, so a gated register sees exactly
// the rising edges at which en was 1 -- the same edges at which an enabled
// register would load.  Synthesis maps it onto the platform's latch-based ICG
// cell; the model below is that cell's function (a latch transparent while
// clk is low, ANDed with clk), so simulation clocks the gated registers
// exactly as the cell will.  The instance keeps the name u_icg: the sign-off
// activity mapping annotates the cell's ENA pin from this module's `en`.
// Every user ORs !rst_n into `en`: the reset is asynchronous in silicon, but a
// simulator that starts with rst_n already low sees no negedge and applies it
// only on clock edges, so the gated registers must be clocked during reset.
module ot_hdc_cg (
    input  wire clk,
    input  wire en /*verilator clock_enable*/,
    output wire gclk
);
`ifdef SYNTHESIS
    ICGx1_ASAP7_75t_R u_icg (.CLK(clk), .ENA(en), .SE(1'b0), .GCLK(gclk));
`else
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!clk) en_l = en;   // transparent while clk is low
    /* verilator lint_on COMBDLY */
    assign gclk = clk & en_l;
`endif
endmodule
