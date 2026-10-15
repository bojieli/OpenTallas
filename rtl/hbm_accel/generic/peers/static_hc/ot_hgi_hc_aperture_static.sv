`timescale 1ns/1ps
`default_nettype none
// Actual FP32 weight aperture memory successor for HC W32,RMAX128,PMAX8.
// Two slots x eight banks x four quarters x 128x256 SRAM = 64 real macros.
// Bank-fixed ap[b]278={v,slot1,bank3,position9,data256,mask8};
// position={row7,quarter2}. No held lanes, grants, ap_cr or completion waits.
// ap sampled n -> macro commit/done n+1. A read is sampled directly by the
// selected slot's four SRAMs; raw_weight is the synchronous macro output,
// selected using read_slot captured on that same edge. This is the actual
// g_wq apw seam: parent wd capture on the following edge retains HC ML=2.
// read_valid accompanies raw_weight. It does not grant or gate future reads.
module ot_hgi_hc_aperture_static(
    input wire clk,rst_n,
    input wire [2223:0] ap,
    output reg [7:0] write_done,
    input wire [7:0] read_v,
    input wire [7:0] read_slot,
    input wire [55:0] read_row,
    output reg [7:0] read_valid,
    output wire [8191:0] raw_weight,
    output reg fault
);
    reg [2223:0] ap_d;
    reg [7:0] ap_v,slot_q;
    wire [16383:0] macro_data;
    always @(posedge clk)begin ap_d<=ap;slot_q<=read_slot;end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin ap_v<=0;write_done<=0;read_valid<=0;fault<=0;end
        else begin
            read_valid<=read_v;write_done<=ap_v;
            for(integer b=0;b<8;b=b+1)begin
                ap_v[b]<=ap[b*278+277];
                if(ap_v[b]&&ap_d[b*278+273+:3]!=3'(b))fault<=1;
                if(ap_v[b]&&read_v[b]&&ap_d[b*278+276]==read_slot[b]&&ap_d[b*278+266+:7]==read_row[b*7+:7])fault<=1;
            end
        end
    end
    for(genvar s=0;s<2;s=s+1)begin:slot
        for(genvar b=0;b<8;b=b+1)begin:bank
            for(genvar q=0;q<4;q=q+1)begin:quarter
                localparam integer MI=(s*8+b)*4+q;
                wire [255:0] mask;
                for(genvar w=0;w<8;w=w+1)begin:word
                    assign mask[w*32+:32]={32{ap_d[b*278+w]}};
                end
                ot_sram_1r1w_128x256_m1_r2c2 u_weight(
                    .clk(clk),.r_ce_in(read_v[b]&&read_slot[b]==1'(s)),
                    .r_addr_in(read_row[b*7+:7]),.rd_out(macro_data[MI*256+:256]),
                    .w_ce_in(ap_v[b]&&ap_d[b*278+276]==1'(s)&&
                        ap_d[b*278+273+:3]==3'(b)&&ap_d[b*278+264+:2]==2'(q)),
                    .w_addr_in(ap_d[b*278+266+:7]),.wd_in(ap_d[b*278+8+:256]),.w_mask_in(mask),
                    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
            end
        end
    end
    for(genvar b=0;b<8;b=b+1)begin:weight_output
        assign raw_weight[b*1024+:1024]=slot_q[b]?macro_data[(8+b)*1024+:1024]:macro_data[b*1024+:1024];
    end
endmodule
`default_nettype wire
