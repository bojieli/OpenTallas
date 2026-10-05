`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Two-entry registered queue for the local K arbitration partition
// (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md).  in_rdy is !full from a
// register, so no ready path crosses the queue combinationally; with one entry
// resident a push and a pop on the same edge keep initiation interval 1.
// Output data come from the queue's own registers and stay stable while
// out_v && !out_rdy.
// ---------------------------------------------------------------------------
module ot_chip_v41x_karb_q2 #(
    parameter integer W = 8
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
    reg [W-1:0] m0, m1;
    reg         rp, wp;
    reg  [1:0]  n;
    wire push = in_v && in_rdy;
    wire pop  = out_v && out_rdy;
    assign in_rdy = (n != 2'd2);
    assign out_v  = (n != 2'd0);
    assign out_d  = rp ? m1 : m0;
    always @(posedge clk) if (push) begin
        if (wp) m1 <= in_d; else m0 <= in_d;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rp <= 1'b0; wp <= 1'b0; n <= 2'd0; end
        else begin
            if (push) wp <= !wp;
            if (pop)  rp <= !rp;
            n <= n + {1'b0, push} - {1'b0, pop};
        end
endmodule
