`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DEPTH-entry registered queue (credited receiver) for the local K arbitration
// partition: in_rdy is !full from a register; out_d comes from the queue's own
// registers and stays stable while out_v && !out_rdy.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_qn #(
    parameter integer W     = 8,
    parameter integer DEPTH = 3
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    output wire         in_rdy,
    input  wire [W-1:0] in_d,
    output wire         out_v,
    input  wire         out_rdy,
    output wire [W-1:0] out_d
);
    localparam integer PW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer NW = $clog2(DEPTH + 1);
    reg [W-1:0]  m [0:DEPTH-1];
    reg [PW-1:0] rp, wp;
    reg [NW-1:0] n;
    wire push = in_v && in_rdy;
    wire pop  = out_v && out_rdy;
    assign in_rdy = (n != NW'(DEPTH));
    assign out_v  = (n != '0);
    assign out_d  = m[rp];
    always @(posedge clk) if (push) m[wp] <= in_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rp <= '0; wp <= '0; n <= '0; end
        else begin
            if (push) wp <= (wp == PW'(DEPTH - 1)) ? '0 : wp + 1'b1;
            if (pop)  rp <= (rp == PW'(DEPTH - 1)) ? '0 : rp + 1'b1;
            n <= n + NW'(push) - NW'(pop);
        end
endmodule
