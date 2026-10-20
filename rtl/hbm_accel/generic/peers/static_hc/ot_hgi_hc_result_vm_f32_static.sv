`timescale 1ns/1ps
`default_nettype none
// HBM-HCBANK6 10-20 (QHUB SAFE 2, native32): ot_hgi_hc_result_vm_static with the per-lane store packing driven by KEPT
// lane-select copies wsel (from the programme calendar register, ot_hbm_hc_qcal_static FAN32: wsel[(j*8+b)*NWS+k] = sector j
// of this store maps to LG lane b, computed from the same base / position fields on the edge they load) instead of one
// 3-bit sector decode per sector fanned to 281 lane bits.  Same ports (+ wsel), edges and local_wq / local_write / fault
// values on every edge.  Lane b = OR over sectors j of wsel(j, b) & {store_slot, sector j address, result word j, 8'hff}.
module ot_hgi_hc_result_vm_f32_static #(parameter integer NWS=9)(
    input wire clk,rst_n,store_slot,
    input wire [15:0] base_sector,
    input wire [2:0] store_position,
    input wire [24*NWS-1:0] wsel,
    input wire result_v,
    input wire [2:0] result_position,
    input wire [767:0] result,
    output reg [2247:0] local_wq,
    output reg [7:0] local_write,
    output reg fault
);
    initial if(NWS*32<281)$fatal(1,"NWS copies must cover the 281 lane bits at <= 32 each");
    wire [15:0] s [0:2];
    for(genvar j=0;j<3;j=j+1)begin:g_s
        assign s[j]=base_sector+store_position*3+j;
    end
    reg [2247:0] packed_wq;
    reg [7:0] selected;
    always @*begin
        packed_wq=0;selected=0;
        for(integer b=0;b<8;b=b+1)
            for(integer j=0;j<3;j=j+1)begin
                for(integer i=0;i<281;i=i+1)begin
                    reg vbit;
                    vbit=(i>=280)?store_slot:(i>=264)?s[j][i-264]:(i>=8)?result[j*256+i-8]:1'b1;
                    packed_wq[b*281+i]=packed_wq[b*281+i]|(wsel[(j*8+b)*NWS+i/32]&vbit);
                end
                selected[b]=selected[b]|(wsel[(j*8+b)*NWS+NWS-1]&store_slot);
            end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin local_wq<=0;local_write<=0;fault<=0;end
        else begin
            local_wq<=packed_wq;local_write<=selected;
            if(store_slot&&(!result_v||result_position!=store_position||({1'b0,base_sector}+store_position*3+3)>32768))fault<=1;
            if(result_v&&!store_slot)fault<=1;
        end
    end
endmodule
`default_nettype wire
