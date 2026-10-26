`timescale 1ns/1ps
`default_nettype none
// GEO-H LG port group (v15 engine_lg_port_group_rule): one registered VM port cluster per bank pair.
// Bit slices follow the contract: rq [(2k)*17,(2k+2)*17), rr [(2k)*257,(2k+2)*257), wq [(2k)*281,(2k+2)*281).
// Pure fixed one-edge registers in each direction; the compiler/engine prices them (+1 rq, +1 rr, +1 wq).
// No ready, credit or arbitration. Only validity bits are reset; payload is bounded latency state.
// Own clock entry so each group is a separate physical leaf placed facing its bank pair (link < 500 um).
module ot_hgi_qdq_lg_port_group #(parameter integer BANKS=2)(
    input wire clk, rst_n,
    input wire [BANKS*17-1:0] rq_i, output reg [BANKS*17-1:0] rq_o,
    input wire [BANKS*257-1:0] rr_i, output reg [BANKS*257-1:0] rr_o,
    input wire [BANKS*281-1:0] wq_i, output reg [BANKS*281-1:0] wq_o
);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+16]<=0;rr_o[b*257+256]<=0;wq_o[b*281+280]<=0;end
        else for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+16]<=rq_i[b*17+16];rr_o[b*257+256]<=rr_i[b*257+256];wq_o[b*281+280]<=wq_i[b*281+280];end
    always @(posedge clk)
        for(integer b=0;b<BANKS;b=b+1) begin rq_o[b*17+:16]<=rq_i[b*17+:16];rr_o[b*257+:256]<=rr_i[b*257+:256];wq_o[b*281+:280]<=wq_i[b*281+:280];end
endmodule
`default_nettype wire
