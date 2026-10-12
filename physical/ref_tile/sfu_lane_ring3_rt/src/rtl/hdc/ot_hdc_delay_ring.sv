`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay_ring #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0,
    // RING (CLAUDE HBM-ABSTRACTS views agent, default off): D >= 4 as a ring of D-1 slots plus an output register
    // (slot written at edge e is read into q at edge e + D - 1: the same q as the shift line) -- no flop-to-flop chain
    // for hold repair, every slot written / read through its own one-hot enable
    parameter integer RING = 0
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
        end else if (RING != 0 && D >= 4) begin : g_ring
            localparam integer N = D - 1;
            reg [W-1:0] m [0:N-1];
            reg [N-1:0] oh;                       // one-hot slot of this edge (read, then written)
            reg [W-1:0] qr;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                else oh <= {oh[N-2:0], oh[N-1]};
            reg [W-1:0] rd;
            integer i;
            always @(*) begin
                rd = {W{1'b0}};
                for (i = 0; i < N; i = i + 1) rd = rd | (m[i] & {W{oh[i]}});
            end
            genvar j;
            for (j = 0; j < N; j = j + 1) begin : g_s
                if (RESET != 0) begin : g_rst
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) m[j] <= {W{1'b0}}; else if (oh[j]) m[j] <= d;
                end else begin : g_nrst
                    always @(posedge clk) if (oh[j]) m[j] <= d;
                end
            end
            if (RESET != 0) begin : g_qrst
                always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {W{1'b0}}; else qr <= rd;
            end else begin : g_qnrst
                always @(posedge clk) qr <= rd;
            end
            assign q = qr;
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
