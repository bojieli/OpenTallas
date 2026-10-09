`timescale 1ns/1ps
// cont-takeover 2026-10-09: registered ready/valid input boundary (two-entry skid, full throughput).  i_ready is a flop
// output, i_data/i_valid land in flops with one 2:1 mux in front; the consumer sees o_valid/o_data straight from flops.
// Adds one cycle of latency on the channel; order, values and back-pressure behaviour are unchanged.
module ot_dsrom_hc_skid #(parameter integer W=8)(
    input wire clk,rst_n,
    input wire i_valid,output wire i_ready,input wire [W-1:0] i_data,
    output wire o_valid,input wire o_ready,output wire [W-1:0] o_data
);
    reg v0,v1;
    reg [W-1:0] d0,d1;
    assign i_ready=!v1;
    assign o_valid=v0;
    assign o_data=d0;
    wire push=i_valid&&!v1;
    wire pop=v0&&o_ready;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin v0<=1'b0;v1<=1'b0;end
        else if(pop) begin
            if(v1) begin v1<=1'b0;end           // push is 0 while v1: d1 moves up, v0 stays set
            else v0<=push;
        end else if(push) begin
            if(!v0) v0<=1'b1; else v1<=1'b1;
        end
    always @(posedge clk)
        if(pop) begin
            if(v1) d0<=d1; else if(push) d0<=i_data;
        end else if(push) begin
            if(!v0) d0<=i_data; else d1<=i_data;
        end
endmodule
