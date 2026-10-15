`timescale 1ns/1ps
`default_nettype none
// Actual local configuration/launch consumer for the F20 engine programme
// broadcast. Two registered transport rungs; no per-cycle execution handshake.
// Targets not configured for this kernel remain inactive at the global launch.
module ot_static_program_target #(parameter [7:0] TARGET=8'd48,parameter integer PCW=10)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    input wire program_active,
    output reg program_cfg_we,
    output reg [PCW-1:0] program_cfg_addr,
    output reg [255:0] program_cfg_data,
    output reg program_start_v,
    output reg [PCW-1:0] program_start_base,
    output reg [PCW:0] program_start_limit,
    output reg [15:0] program_start_loops,
    output reg configured,fault
);
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    reg cv,dv,lv;
    reg [7:0] target;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    always @(posedge clk)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            cv<=0;dv<=0;lv<=0;program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            program_cfg_we<=0;program_start_v<=0;
            if(cv && target==TARGET)begin
                if(program_active || lv || {1'b0,address}>=(13'd1<<PCW))fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==TARGET)begin
                if(program_active || lv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;configured<=1;end
            end
            if(lv && configured)begin
                if(program_active || fault)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base[PCW-1:0];
                    program_start_limit<=stored_limit[PCW:0];program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire
