`timescale 1ns/1ps
`default_nettype none
// Fixed HC tail->native VM eight-bank write producer. One scheduled store
// takes three contiguous256-bit sectors (24FP32words), mapped to their native
// bank bits. Program reserves that same slot independently of result_v.
// n -> registered localwq n, farHCtapcommit at its consumer sample+15.
// Incorrect/missing result identity faults; schedule never waits for valid.
// HBM-NEXT-UNITS 2026-10-19 (hnx fork, N-row records): position p's 3 sectors go to base + p*row_stride + j;
// row_stride == 0 = the d4g dense form (stride 3).  A nonzero stride below 3 (overlapping rows) faults.
// MUT_STRIDE (bench) = the store ignores row_stride.
module ot_hnx_hgi_hc_result_vm #(parameter integer MUT_STRIDE=0)(
    input wire clk,rst_n,store_slot,
    input wire [15:0] base_sector,
    input wire [15:0] row_stride,
    input wire [2:0] store_position,
    input wire result_v,
    input wire [2:0] result_position,
    input wire [767:0] result,
    output reg [2247:0] local_wq,
    output reg [7:0] local_write,
    output reg fault
);
    reg [2247:0] packed_wq;
    reg [7:0] selected;
    wire [15:0] rs=(row_stride==16'd0||MUT_STRIDE!=0)?16'd3:row_stride;
    always @*begin
        packed_wq=0;selected=0;
        for(integer j=0;j<3;j=j+1)begin:sector
            reg [15:0] s;
            s=base_sector+store_position*rs+j;
            packed_wq[s[2:0]*281+:281]={store_slot,s,result[j*256+:256],8'hff};
            selected[s[2:0]]=store_slot;
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin local_wq<=0;local_write<=0;fault<=0;end
        else begin
            local_wq<=packed_wq;local_write<=selected;
            if(store_slot&&(!result_v||result_position!=store_position||rs<16'd3||(32'(base_sector)+32'(store_position)*32'(rs)+3)>32768))fault<=1;
            if(result_v&&!store_slot)fault<=1;
        end
    end
endmodule
`default_nettype wire
