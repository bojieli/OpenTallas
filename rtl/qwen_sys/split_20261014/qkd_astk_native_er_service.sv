`timescale 1ns/1ps
// Native external P.V profile: one statically scheduled e-quad read per edge.
// Storage and the three read stages remain inside the actual qkd_astk_ep.
// This adapter only binds that existing SO/SI ABI and carries the request tag.
// A legacy ECTL read in this profile is an integrity fault, never arbitration.
module qkd_astk_native_er_service #(
    parameter integer ERL=3, ROUTE_MUT=0, TAG_MUT=0, LATENCY_MUT=0
) (
    input wire ck,rst_n,
    input wire read_v,
    input wire [10:0] read_addr,
    input wire [8*425-1:0] engine_so,
    output reg [8*425-1:0] astk_so,
    input wire [8*634-1:0] astk_si,
    output wire [8*634-1:0] engine_si,
    output wire response_v,
    output wire [10:0] response_addr,
    output wire [63:0] response_data,
    output reg fault
);
    wire [2:0] owner=read_addr[5:3];
    wire [2:0] routed_owner=owner ^ 3'(ROUTE_MUT);
    reg [ERL-1:0] val;
    reg [10:0] tag[0:ERL-1];
    integer i;
    always @* begin
        astk_so=engine_so;
        for(integer e=0;e<8;e=e+1)begin
            astk_so[425*e+:13]=13'd0;
            if(read_v && routed_owner==e)
                astk_so[425*e+:13]={1'b0,read_addr,1'b1};
        end
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin val<=0;fault<=0;end
        else begin
            val<={val,read_v};
            for(integer e=0;e<8;e=e+1)if(engine_so[425*e])fault<=1;
        end
    always @(posedge ck)begin
        tag[0]<=read_addr;
        for(i=1;i<ERL;i=i+1)tag[i]<=tag[i-1];
    end
    assign engine_si=astk_si;
    assign response_v=val[ERL-1-LATENCY_MUT];
    assign response_addr=tag[ERL-1-LATENCY_MUT];
    wire [2:0] returned_owner=tag[ERL-1-TAG_MUT][5:3];
    assign response_data=astk_si[634*returned_owner+569+:64];
    initial if(ERL!=3 || TAG_MUT<0 || TAG_MUT>1 || LATENCY_MUT<0 || LATENCY_MUT>1)
        $fatal(1,"native EP ABI requires ERL3");
endmodule
