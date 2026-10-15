`timescale 1ns/1ps
`default_nettype none
// HBM F20 target52+qid: real 1536b programme assembler for cfg37 issuer.
// Address[11:9]=0, [8:3]=instruction row, [2:0]=segment. Segments0..5
// carry low-to-high256b uop; segment6 carries metadata[63:0], upper192=0.
// Seven unique frames in any order complete ONE row. No next row while drain
// runs: host compiler leaves55edges after the final frame before next frame.
// Drain emits53 registered commands then1guard; no ready/queue/backpressure.
// Descriptor base/limit are INSTRUCTION indices. loops=1 only; actual native
// issuer metadata retains32bit loop counts. Unsupported loops fault.
// Fresh reset is required to install a different programme. Writes to complete
// rows, partial row changes, launch before completion, and active writes fault.
module ot_hgi_coll_static_program_target #(
    parameter [7:0] TARGET=8'd52,
    parameter integer MUT_DATA=0
)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,program_active,
    input wire issuer_busy,issuer_fault,issuer_uop_v,
    input wire [5:0] issuer_uop_pc,
    output reg [36:0] issuer_cfg,
    output reg issuer_start,
    output reg [5:0] issuer_start_pc,
    output reg configured,init_busy,fault
);
    // Input capture is the first transport rung. Processing and registered
    // cfg/start outputs are the second. Every exported signal is flop Q.
    reg cv,dv,lv;
    reg [7:0] target_q;
    reg [11:0] addr_q,base_q;
    reg [12:0] limit_q;
    reg [15:0] loops_q;
    reg [255:0] data_q;
    always @(posedge clk)begin
        target_q<=cfg_target;addr_q<=cfg_addr;data_q<=cfg_data;
        base_q<=desc_base;limit_q<=desc_limit;loops_q<=desc_loops;
    end
    reg [1535:0] assembly;
    reg [63:0] metadata;
    reg [6:0] seen;
    reg [5:0] row;
    reg [63:0] loaded;
    reg draining;
    reg [5:0] step;
    reg [5:0] base;
    reg [6:0] limit;
    reg all_loaded;
    always @* begin
        all_loaded=1'b1;
        for(integer i=0;i<64;i=i+1)
            if(i>=base && i<limit && !loaded[i])all_loaded=1'b0;
    end
    wire occupied=program_active || issuer_busy || issuer_start;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cv<=0;dv<=0;lv<=0;issuer_cfg<=0;issuer_start<=0;
            issuer_start_pc<=0;configured<=0;init_busy<=0;fault<=0;
            seen<=0;loaded<=0;row<=0;draining<=0;step<=0;
            base<=0;limit<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            issuer_cfg<=0;issuer_start<=0;
            if(issuer_fault)fault<=1;
            if(issuer_uop_v && (!configured || issuer_uop_pc<base || {1'b0,issuer_uop_pc}>=limit))fault<=1;
            if(draining)begin
                if(step<51)begin
                    if(step%17==0)issuer_cfg<={1'b1,4'd0,24'b0,2'(step/17),row};
                    else issuer_cfg<={1'b1,4'd1,assembly[(step/17)*512+(step%17-1)*32+:32] ^ ((MUT_DATA!=0 && step==1)?32'b1:32'b0)};
                end else if(step==51)issuer_cfg<={1'b1,4'd2,metadata[31:0]};
                else if(step==52)issuer_cfg<={1'b1,4'd3,metadata[63:32]};
                // step53 ensures the issuer has sampled its final metadata.
                if(step==53)begin
                    draining<=0;loaded[row]<=1;seen<=0;init_busy<=0;
                end else step<=step+1'b1;
            end
            if(cv && target_q==TARGET)begin
                if(occupied || lv || draining || fault || dv || addr_q[11:9]!=0 ||
                   addr_q[2:0]==7 || loaded[addr_q[8:3]] ||
                   (seen!=0 && row!=addr_q[8:3]) || seen[addr_q[2:0]] ||
                   (addr_q[2:0]==6 && (data_q[255:64]!=0 || data_q[63:51]!=0)))fault<=1;
                else begin
                    row<=addr_q[8:3];seen[addr_q[2:0]]<=1;init_busy<=1;
                    if(addr_q[2:0]==6)metadata<=data_q[63:0];
                    else assembly[addr_q[2:0]*256+:256]<=data_q;
                    if((seen | (7'b1<<addr_q[2:0]))==7'h7f)begin draining<=1;step<=0;end
                end
            end
            if(dv && target_q==TARGET)begin
                if(occupied || lv || draining || seen!=0 || fault || cv ||
                   base_q>=64 || limit_q>64 || limit_q<={1'b0,base_q} || loops_q!=1)fault<=1;
                else begin base<=base_q[5:0];limit<=limit_q[6:0];configured<=1;end
            end
            if(lv && configured)begin
                if(occupied || draining || seen!=0 || fault || cv || dv || !all_loaded)fault<=1;
                else begin issuer_start<=1;issuer_start_pc<=base;end
            end else if(lv && (seen!=0 || draining))fault<=1;
        end
    end
endmodule
`default_nettype wire
