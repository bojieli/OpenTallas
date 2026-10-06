`timescale 1ns/1ps
module ot_dsrom_su_swiglu #(
    parameter integer QLAT = 5,         // the quantisers' scale multiply latency (5 | 6)
    parameter integer W = 1024,
    parameter integer NIN = 33,
    parameter integer NOUT = 23,
    parameter integer ROUTED = 1,
    parameter integer LM = 5,
    parameter integer LA = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire [32*W-1:0]   g,
    input  wire [32*W-1:0]   u,
    input  wire [32*W-1:0]   w,          // the lane's routing weight (its expert's), unused when ROUTED = 0
    input  wire [31:0]       lim,
    output wire              vo,
    output wire [8*W-1:0]    q,          // FP8 E4M3 codes
    output wire [10*W/32-1:0] e,         // per block: scale exponent (signed)
    output wire [16*W-1:0]   y,          // dequantised BF16 (qdq_fp8)
    output wire              fault
);
    // TEST ONLY: deliberate two-edge deterministic boundary golden.
    initial if(LM!=5 || LA!=4 || QLAT!=5 || NIN!=33 || NOUT!=23 || ROUTED!=1)
        $fatal(1,"adapter differs from selected adopted engine parameters");
    reg pending, valid_out, packet_fault;
    reg [8*W-1:0] codes;
    reg [10*W/32-1:0] scales;
    reg [16*W-1:0] bf16;
    assign vo=valid_out;assign q=codes;assign e=scales;assign y=bf16;
    assign fault=valid_out ? packet_fault : 1'bx;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin pending<=0;valid_out<=0;packet_fault<=0;end
        else begin
            pending<=v;valid_out<=pending;
            if(v)begin
                packet_fault<=lim[31];
                for(integer k=0;k<W;k=k+1)begin
                    codes[8*k+:8]<=g[32*k+:8];
                    bf16[16*k+:16]<=u[32*k+:16];
                end
                for(integer b=0;b<W/32;b=b+1)scales[10*b+:10]<=w[1024*b+:10];
            end
        end
    end
endmodule
