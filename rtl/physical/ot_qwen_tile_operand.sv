`timescale 1ns/1ps
// Consumer-owned A0 operand stages, fixed G=4, W=16, HIER=2, WCONV=1, KV_LOCAL=0.
// A leaf owns the 8 lanes feeding ONE LSL: mq_wrom, s1b_gm/wsrc, then s2_w's high16.
// Existing MEM_PIPE/S2 edges, zero added stages. No change to arithmetic or to zero-KV semantics.
module ot_qwen_tile_operand (
    input wire clk,
    input wire [127:0] w_d,
    input wire [3:0] gm_d,
    input wire wsrc_d,
    output wire [127:0] w_q
);
    (* keep *) reg [127:0] mq;
    (* keep *) reg [3:0] gm;
    (* keep *) reg wsrc;
    (* keep *) reg [127:0] s2;
    always @(posedge clk) begin
        mq <= w_d;
        gm <= gm_d;
        wsrc <= wsrc_d;
    end
    genvar k;
    generate for (k=0;k<8;k=k+1) begin:g_lane
        always @(posedge clk) s2[16*k +:16] <= (!gm[k/2] || wsrc) ? 16'd0 : mq[16*k +:16];
    end endgenerate
    assign w_q=s2;
endmodule
