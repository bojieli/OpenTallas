`timescale 1ns/1ps
// Opt-in successor of G1. Adds one result edge; the compiler must price and
// deskew the leaf result independently of the through lanes before adoption.
// Kept copies capture the source valid directly: no shared valid register
// drives the 48-bit result mux. A six-bit group consumes <=12 mapped mux loads.
module ot_rp4_g1_capture #(
    parameter integer TAGW = 16,
    parameter integer GROUP = 6,
    parameter integer MUT = 0,
    parameter integer MASKPIPE = 0
) (
    input wire clk, rst_n,
    input wire bov, fov, bfault, ffault,
    input wire [31:0] by, fy,
    input wire [TAGW-1:0] btag, ftag,
    output reg gv, gf,
    output wire [31:0] gy,
    output wire [TAGW-1:0] gt
);
    localparam integer W = 32 + TAGW;
    localparam integer N = (W + GROUP - 1) / GROUP;
    (* keep *) reg [N-1:0] select_q;
    (* keep *) reg [W-1:0] b_q, f_q;
    reg v_q, fault_q;
    reg [W-1:0] result_q;
    reg v_mask, fault_mask;
    always @(posedge clk) begin
        select_q <= {N{bov}};
        b_q <= {by, btag};
        f_q <= {fy, ftag};
        if (!rst_n) begin
            v_q <= 1'b0;
            fault_q <= 1'b0;
            v_mask <= 1'b0;
            fault_mask <= 1'b0;
            gv <= 1'b0;
            gf <= 1'b0;
        end else begin
            v_q <= bov | fov;
            fault_q <= bfault | ffault | (bov & fov);
            v_mask <= v_q;
            fault_mask <= fault_q;
            gv <= MUT == 1 ? (bov | fov) : (MASKPIPE ? v_mask : v_q);
            gf <= MUT == 2 ? 1'b0 : (MASKPIPE ? fault_mask : fault_q);
        end
    end
    genvar k;
    generate for (k = 0; k < W; k = k + 1) begin : g_result
        if (MASKPIPE) begin : g_masks
            // Both branches perform useful selection before the final OR.
            // This is a three-stage compute pipeline, not result padding.
            (* keep *) reg b_mask, f_mask;
            always @(posedge clk) begin
                b_mask <= b_q[k] & select_q[k / GROUP];
                f_mask <= f_q[k] & ~select_q[k / GROUP];
                result_q[k] <= b_mask | f_mask;
            end
        end else begin : g_direct
            always @(posedge clk)
                result_q[k] <= select_q[k / GROUP] ? b_q[k] : f_q[k];
        end
    end endgenerate
    assign {gy, gt} = result_q;
endmodule
