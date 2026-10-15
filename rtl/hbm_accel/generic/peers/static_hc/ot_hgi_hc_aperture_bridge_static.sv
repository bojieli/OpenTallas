`timescale 1ns/1ps
`default_nettype none
// Opt-in static HC weight route from the real eight-bank staging delivery.
// Descriptor is compiler-issued before the block. Each 2048-sector delivery is
// 256 ordinal slots, eight banks per slot. Position base 0/256 selects the first
// or second half of one HC weight slot. No queue/credits/ready or beat arbitration.
// dq[b]={v,source_sector16,data256,mask8}; ap[b]={v,slot,bank3,position9,data256,mask8}.
// Source sector = descriptor base + ordinal*8+b; aperture position=base+ordinal.
// Pin registers -> registered output: sample n, ap at n+1.
module ot_hgi_hc_aperture_bridge_static #(
    parameter integer MUT=0 // 1: wrong aperture quarter, caught at SRAM readback
)(
    input wire clk,rst_n,
    input wire desc_v,
    input wire [15:0] desc_source_base,
    input wire desc_slot,
    input wire [8:0] desc_position_base,
    input wire [2247:0] dq,
    output wire [2223:0] ap,
    output reg fault
);
    reg configured,slot_q;
    reg [15:0] base_q;
    reg [8:0] pos_q;
    reg [2247:0] dq_d;
    reg [7:0] dq_v,ap_v;
    reg [2223:0] ap_d;
    always @(posedge clk) dq_d<=dq;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin configured<=0;slot_q<=0;base_q<=0;pos_q<=0;dq_v<=0;ap_v<=0;fault<=0;end
        else begin
            if(desc_v)begin
                configured<=1;slot_q<=desc_slot;base_q<=desc_source_base;pos_q<=desc_position_base;
                if(desc_source_base[4:0]!=0||desc_position_base[7:0]!=0)fault<=1;
            end
            for(integer b=0;b<8;b=b+1)begin
                dq_v[b]<=dq[b*281+280];ap_v[b]<=dq_v[b];
                if(dq_v[b])begin
                    if(!configured||dq_d[b*281+264+:16]<base_q||
                       {1'b0,dq_d[b*281+264+:16]}-{1'b0,base_q}>=17'd2048||
                       dq_d[b*281+264+:3]!=3'(b))fault<=1;
                end
            end
        end
    end
    for(genvar b=0;b<8;b=b+1)begin:bank
        wire [15:0] delta=dq_d[b*281+264+:16]-base_q;
        wire [8:0] position=(pos_q+delta[11:3])^(MUT==1?9'd1:9'd0);
        always @(posedge clk)ap_d[b*278+:277]<=
            {slot_q,3'(b),position,dq_d[b*281+:264]};
        assign ap[b*278+:278]={ap_v[b],ap_d[b*278+:277]};
    end
endmodule
`default_nettype wire
