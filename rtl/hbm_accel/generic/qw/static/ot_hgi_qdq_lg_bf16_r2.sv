`timescale 1ns/1ps
`default_nettype none
// Native quant writes carry BF16 words in the high half of FP32 slots.
// Keep that format expansion inside the leaf, rather than on die input pins.
// The existing capture/output registers and all their cycles are unchanged.
module ot_hgi_qdq_lg_bf16_r2 #(parameter integer BANKS=2, MUT=0)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output wire [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output wire [BANKS*257-1:0] rr_o,
    input wire [BANKS*153-1:0] wq_i, output wire [BANKS*281-1:0] wq_o
);
    wire [BANKS*281-1:0] expanded;
    for(genvar b=0;b<BANKS;b=b+1) begin: g_bank
        assign expanded[b*281+:8]=wq_i[b*153+:8];
        for(genvar k=0;k<8;k=k+1) begin: g_word
            assign expanded[b*281+8+k*32+:32]=
                {wq_i[b*153+8+k*16+:16], (MUT!=0 && b==0 && k==0 ? 16'h0001 : 16'h0000)};
        end
        assign expanded[b*281+264+:17]=wq_i[b*153+136+:17];
    end
    ot_hgi_qdq_lg_port_group_r2 #(.BANKS(BANKS)) u_regs(
        .clk(clk), .rst_n(rst_n), .rq_i(rq_i), .rq_o(rq_o),
        .rr_i(rr_i), .rr_o(rr_o), .wq_i(expanded), .wq_o(wq_o));
endmodule
`default_nettype wire
