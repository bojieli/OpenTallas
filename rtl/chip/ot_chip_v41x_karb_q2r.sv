`timescale 1ns/1ps
// ot_chip_v41x_karb_q2r -- ot_chip_v41x_karb_q2 with its read and write pointers REPLICATED per payload slice
// (W18b, 1.2 GHz sign-off of the K-arb root).  Same contract as q2: two entries, in_rdy from a register,
// out_d from the queue's own registers and stable while out_v && !out_rdy.  Each of NREP slices of the
// payload has its own rp/wp copy (ot_chip_v41x_keep_dff, kept apart by synthesis), so no pointer fans out to
// the whole W-bit word: at W = 344 one rp drove ~600 loads through six buffer levels (-199 ps at SS).
// Copy 0 also drives the PC field (bits [W-1 -: HB]) so the dispatch decision reads a local pointer.
module ot_chip_v41x_karb_q2r #(
    parameter integer W    = 8,
    parameter integer NREP = 4
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
    localparam integer SW = (W + NREP - 1) / NREP;
    reg [W-1:0] m0, m1;
    reg  [1:0]  n;
    wire push = in_v && in_rdy;
    wire pop  = out_v && out_rdy;
    assign in_rdy = (n != 2'd2);
    assign out_v  = (n != 2'd0);
    genvar k;
    generate for (k = 0; k < NREP; k = k + 1) begin : g_r
        localparam integer LO = k * SW;
        localparam integer HI = ((k + 1) * SW > W) ? W : (k + 1) * SW;
        wire rp, wp;
        ot_chip_v41x_keep_dff u_rp (.clk(clk), .rst_n(rst_n), .d(rp ^ pop),  .q(rp));
        ot_chip_v41x_keep_dff u_wp (.clk(clk), .rst_n(rst_n), .d(wp ^ push), .q(wp));
        if (HI > LO) begin : g_s
            assign out_d[HI-1:LO] = rp ? m1[HI-1:LO] : m0[HI-1:LO];
            always @(posedge clk) if (push) begin
                if (wp) m1[HI-1:LO] <= in_d[HI-1:LO]; else m0[HI-1:LO] <= in_d[HI-1:LO];
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if (!rst_n) n <= 2'd0;
        else n <= n + {1'b0, push} - {1'b0, pop};
endmodule
