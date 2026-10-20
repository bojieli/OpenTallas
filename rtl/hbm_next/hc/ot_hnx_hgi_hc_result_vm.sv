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
// HUB-SAFE2 2026-10-20 (kit hnx_hcq_hub_safe2_1020, SAFE-DESIGN item 3; zero added edges, local_wq bit-identical):
// the bank routing (st_v / st_hdr / st_sel) is decoded by the calendar (ot_hnx_hc_cal) from its capture register on the
// calendar's edge, so local_wq[b] = {st_v[b], st_hdr[b] & st_v[b], OR_j (st_sel[j][b][lane group] & result[j]), 8 x st_v[b]}
// is one AND-OR level of kept one-hot copies (<= 32 loads each).  local_wq / local_write keep their edge.  Only the bank
// write flags (local_wq valid bit, local_write) and the fault are reset: the 2,248 data / address flops were on one reset
// copy (census safe1019 store.rst_n 2,193 loads) and are now data (zero whenever no store slot, as before).
// The fault check reads the calendar fields (base / row_stride / position), as before.
module ot_hnx_hgi_hc_result_vm #(parameter integer MUT_STRIDE=0)(
    input wire clk,rst_n,store_slot,
    input wire [15:0] base_sector,
    input wire [15:0] row_stride,
    input wire [2:0] store_position,
    input wire [7:0] st_v,
    input wire [8*16-1:0] st_hdr,
    input wire [3*8*8-1:0] st_sel,
    input wire result_v,
    input wire [2:0] result_position,
    input wire [767:0] result,
    output wire [2247:0] local_wq,
    output reg [7:0] local_write,
    output reg fault
);
    wire [15:0] rs=(row_stride==16'd0||MUT_STRIDE!=0)?16'd3:row_stride;
    reg [7:0] wv;                         // local_wq valid bits (reset)
    reg [8*16-1:0] wa;                    // sector addresses (data)
    reg [8*256-1:0] wd;                   // sector data (data)
    reg [8*8-1:0] we;                     // byte enables (data: 8'hff with the valid bit, else 0)
    for(genvar b=0;b<8;b=b+1)begin:g_b
        for(genvar g=0;g<8;g=g+1)begin:g_g
            wire [31:0] d=({32{st_sel[(0*8+b)*8+g]}}&result[0*256+g*32+:32])|
                          ({32{st_sel[(1*8+b)*8+g]}}&result[1*256+g*32+:32])|
                          ({32{st_sel[(2*8+b)*8+g]}}&result[2*256+g*32+:32]);
            always @(posedge clk)wd[b*256+g*32+:32]<=d;
        end
        always @(posedge clk)begin wa[b*16+:16]<=st_hdr[b*16+:16]&{16{st_v[b]}};we[b*8+:8]<={8{st_v[b]}};end
        assign local_wq[b*281+:281]={wv[b],wa[b*16+:16],wd[b*256+:256],we[b*8+:8]};
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin wv<=0;local_write<=0;fault<=0;end
        else begin
            wv<=st_v;local_write<=st_v;
            if(store_slot&&(!result_v||result_position!=store_position||rs<16'd3||(32'(base_sector)+32'(store_position)*32'(rs)+3)>32768))fault<=1;
            if(result_v&&!store_slot)fault<=1;
        end
    end
endmodule
`default_nettype wire
