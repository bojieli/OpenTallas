`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-15: N statically scheduled e-quad reads per edge on the actual EP SO/SI ABI.
// Same binding as qkd_astk_native_er_service (one read per EP per edge, the EP's own three read stages), widened to
// N parallel ports. The compiler calendar places the N reads of an edge on N distinct EP owners (read_addr[5:3]);
// two reads of one owner on one edge are an integrity FAULT, never arbitration. A legacy ECTL read is a fault.
module qkd_astk_native_er_service_w #(
    parameter integer N=4, ERL=3
) (
    input wire ck,rst_n,
    input wire [N-1:0] read_v,
    input wire [11*N-1:0] read_addr,
    input wire [8*425-1:0] engine_so,
    output reg [8*425-1:0] astk_so,
    input wire [8*634-1:0] astk_si,
    output wire [8*634-1:0] engine_si,
    output wire [N-1:0] response_v,
    output wire [11*N-1:0] response_addr,
    output wire [64*N-1:0] response_data,
    output reg fault
);
    reg [N-1:0] val[0:ERL-1];
    reg [10:0] tag[0:ERL-1][0:N-1];
    reg collide;
    integer i,j,e;
    always @* begin
        astk_so=engine_so;
        collide=1'b0;
        for(e=0;e<8;e=e+1) astk_so[425*e+:13]=13'd0;
        for(j=0;j<N;j=j+1)
            if(read_v[j]) begin
                for(i=0;i<j;i=i+1)
                    if(read_v[i] && read_addr[11*i+3+:3]==read_addr[11*j+3+:3]) collide=1'b1;
                astk_so[425*read_addr[11*j+3+:3]+:13]={1'b0,read_addr[11*j+:11],1'b1};
            end
    end
    always @(posedge ck or negedge rst_n)
        if(!rst_n)begin for(i=0;i<ERL;i=i+1)val[i]<=0;fault<=0;end
        else begin
            val[0]<=read_v;for(i=1;i<ERL;i=i+1)val[i]<=val[i-1];
            if(collide)fault<=1;
            for(e=0;e<8;e=e+1)if(engine_so[425*e])fault<=1;
        end
    always @(posedge ck)begin
        for(j=0;j<N;j=j+1)begin tag[0][j]<=read_addr[11*j+:11];for(i=1;i<ERL;i=i+1)tag[i][j]<=tag[i-1][j];end
    end
    assign engine_si=astk_si;
    genvar g;
    generate for(g=0;g<N;g=g+1)begin:g_rsp
        wire [2:0] owner=tag[ERL-1][g][5:3];
        assign response_v[g]=val[ERL-1][g];
        assign response_addr[11*g+:11]=tag[ERL-1][g];
        assign response_data[64*g+:64]=astk_si[634*owner+569+:64];
    end endgenerate
    initial if(ERL!=3 || N<1 || N>8) $fatal(1,"native EP ABI requires ERL3, 1<=N<=8");
endmodule
