`timescale 1ns/1ps
// M5 answer leaves extracted from the pinned region. Each original FSW32
// slice keeps its select/enable stages and samples data on the same hclk.
module ot_qfd_vm_row128_t #(
    parameter integer MUT=0
)(
    input wire clk,
    input wire [3:0] rtg,
    input wire [5:0] rdc,
    input wire [1023:0] bx,
    output reg [127:0] ro
);
    genvar k;
    generate for(k=0;k<4;k=k+1)begin:g_slice
        (* keep="true",dont_touch="true" *) reg [5:0] rs1;
        (* keep="true",dont_touch="true" *) reg [1:0] rs2;
        reg [63:0] t1,t1n;
        always @(posedge clk or negedge rtg[k])
            if(!rtg[k])begin rs1<=0;rs2<=0;end
            else begin rs1<=rdc;rs2<=rs1[5:4];end
        integer h,i;
        always @*begin
            t1n=0;
            for(h=0;h<2;h=h+1)for(i=0;i<4;i=i+1)
                t1n[h*32+:32]=t1n[h*32+:32]|(bx[(4*h+i)*128+k*32+:32]&{32{rs1[i]}});
        end
        always @(posedge clk)t1<=t1n;
        always @(posedge clk)if(rs2[1])ro[k*32+:32]<=(rs2[0]^(MUT!=0))?t1[32+:32]:t1[0+:32];
    end endgenerate
endmodule

module ot_qfd_vm_su1024_t #(
    parameter integer MUT=0
)(
    input wire clk,
    input wire rtg,
    input wire svc,
    input wire [1023:0] sx,
    output reg [1023:0] so
);
    (* keep="true",dont_touch="true" *) reg sg;
    always @(posedge clk or negedge rtg)if(!rtg)sg<=0;else sg<=svc;
    genvar k;
    generate for(k=0;k<32;k=k+1)begin:g_slice
        (* keep="true",dont_touch="true" *) reg sv_k;
        always @(posedge clk or negedge rtg)if(!rtg)sv_k<=0;else sv_k<=sg;
        always @(posedge clk)if(sv_k)so[k*32+:32]<=sx[((k+((MUT!=0)?1:0))%32)*32+:32];
    end endgenerate
endmodule
