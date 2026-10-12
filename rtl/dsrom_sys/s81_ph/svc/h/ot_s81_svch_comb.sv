`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: one LEVEL of the q.k lane tree ABOVE the quadrants' D = 128 engines.  Score beat
// {row 16, mask 4, y NL x H x FP32, flags NL x H} from operand a (the LEFT subtree, lower dims) and b (RIGHT):
//   y = ot_hdc_v41x_qaddf(a, b) (LAT FX, F12: the engine's lane-tree adder, v tied 1 as there),
//   f = delay_FX(fa | fb) | adder fault          -- ot_hdc_v41x_attn_s g_node exactly.
// Both operands must carry the same row / mask (the quadrants' engines see the same beats in the same order; a
// mismatch is a sticky fault).  Valid/ready in, valid/ready out through an OD-beat FIFO: an operand pair enters the
// adders only with a reserved FIFO slot, so the pipeline never stalls (no enable on the adders).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_comb #(
    parameter integer NL = 4,
    parameter integer H = 16,
    parameter integer FX = 5,
    parameter integer F12 = 1,
    parameter integer OD = 8
) (
    input  wire                        clk,
    input  wire                        rst_n,
    input  wire                        a_v,
    output wire                        a_r,
    input  wire [20+NL*H*33-1:0]       a_d,
    input  wire                        b_v,
    output wire                        b_r,
    input  wire [20+NL*H*33-1:0]       b_d,
    output wire                        o_v,
    input  wire                        o_r,
    output wire [20+NL*H*33-1:0]       o_d,
    output reg                         fault
);
    localparam integer W = 20 + NL*H*33, N = NL*H, OA = $clog2(OD);
    reg [OA:0] resv;
    wire fire = a_v && b_v && 32'(resv) < OD;
    assign a_r = fire; assign b_r = fire;
    wire [N-1:0] fa = a_d[N-1:0], fb = b_d[N-1:0];
    wire [N*32-1:0] ya = a_d[N +: N*32], yb = b_d[N +: N*32];
    wire [N*32-1:0] y; wire [N-1:0] af, fd;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_a
        ot_hdc_v41x_qaddf #(.LAT(FX), .F12(F12)) u_a (.clk(clk), .rst_n(rst_n), .v(1'b1), .a(ya[g*32 +: 32]),
                                                     .b(yb[g*32 +: 32]), .y(y[g*32 +: 32]), .fault(af[g]));
    end endgenerate
    wire [19:0] fd_tag;
    ot_hdc_v41x_dly #(.W(N + 20), .D(FX)) u_fd (.clk(clk), .d({a_d[W-1 -: 20], fa | fb}), .q({fd_tag, fd}));
    wire ov;
    ot_hdc_v41x_vdly #(.D(FX)) u_v (.clk(clk), .rst_n(rst_n), .d(fire), .q(ov));
    // output FIFO
    reg [W-1:0] mem [0:OD-1];
    reg [OA:0] wp, rp;
    assign o_v = wp != rp;
    assign o_d = mem[rp[OA-1:0]];
    always @(posedge clk) if (ov) mem[wp[OA-1:0]] <= {fd_tag, y, fd | af};
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin resv <= 0; wp <= 0; rp <= 0; fault <= 1'b0; end
        else begin
            if (ov) wp <= wp + 1'b1;
            if (o_v && o_r) rp <= rp + 1'b1;
            resv <= resv + (OA+1)'(fire) - (OA+1)'(o_v && o_r);
            if (fire && a_d[W-1 -: 20] != b_d[W-1 -: 20]) fault <= 1'b1;
        end
endmodule
