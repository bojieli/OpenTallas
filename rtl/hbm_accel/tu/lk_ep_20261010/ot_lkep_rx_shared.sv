`timescale 1ns/1ps
// Keep existing FIFO heads, strict round-robin merge and output capture in one hard leaf.
// No combinational FIFO head crosses its physical boundary; all outward data/credits retain their original edge.
module ot_lkep_rx_shared #(parameter integer NS=3,W=545,OFD=4,RL=2,SL=64,MUT_RX=0)(
 input wire clk,rst_n,
 input wire [NS-1:0] oh_vt,
 input wire [NS*W-1:0] oh_dt_flat,
 output wire [NS-1:0] ocrq,
 output reg r_v,
 output reg [W-1:0] r_flit
);
 reg [1:0] rs; reg rrx;
 always @(posedge clk or negedge rst_n) if(!rst_n) rs<=0;else rs<={rs[0],1'b1};
 always @(posedge clk) rrx<=rs[1];
 genvar g;
    // ---------------------------------------------------------------- tile out stage 1 -> consumer FIFO -> strict round-robin merge
    wire [NS-1:0]    oh_v;
    wire [W-1:0]     oh_d [0:NS-1];
    reg  [NS-1:0]    opop;
    generate for (g = 0; g < NS; g = g + 1) begin : g_out
        ot_lkep_sinkc #(.W(W), .D(OFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_c(rrx), .i_v(oh_vt[g]), .i_d(oh_dt_flat[g*W +: W]),
            .h_v(oh_v[g]), .h_d(oh_d[g]), .pop(opop[g]), .crq(ocrq[g]));
    end endgenerate
    reg  [1:0]    msel;
    reg  [W-1:0]  o_d;
    integer       u;
    always @(*) begin
        opop = 0;
`ifndef OT_LKEP_MUT_MERGE
        for (u = 0; u < NS; u = u + 1) if (msel == u) opop[u] = oh_v[u];
`else
        for (u = 0; u < NS; u = u + 1) if (msel == u) opop[u] = oh_v[u];   // mutant: an empty turn takes the first non-empty sub
        if (opop == 0) for (u = NS - 1; u >= 0; u = u - 1) if (oh_v[u]) opop = {{(NS-1){1'b0}}, 1'b1} << u;
`endif
        o_d = {W{1'b0}};
        for (u = 0; u < NS; u = u + 1) o_d = o_d | ({W{opop[u]}} & oh_d[u]);
    end
    always @(posedge clk) r_flit <= o_d ^ ((MUT_RX != 0 && (|opop)) ? {{(W-1){1'b0}},1'b1} : {W{1'b0}});
    always @(posedge clk or negedge rrx)
        if (!rrx) begin r_v <= 1'b0; msel <= 0; end
        else begin
            r_v <= |opop;
            if (oh_v[msel]) msel <= (msel == NS - 1) ? 2'd0 : msel + 1'b1;
        end

endmodule
