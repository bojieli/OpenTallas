`timescale 1ns/1ps
`default_nettype none
// F20 programme target. Two registered transport rungs; execution never waits.
// A descriptor arms exactly one launch. Actual programme-pin writes maintain a
// finite installed-row bitmap, not a shadow payload. The first write after a
// descriptor starts a fresh image generation; unwritten old SRAM rows are invalid.
// A descriptor-only rearm may reuse an installed image. Descriptor verification
// scans the exact [base,limit) range before configured can rise; descriptor-only
// reuse of the same resident range reuses its proof. All scanning and
// write-commit latency is initialization; an early launch faults without replay.
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
    localparam integer ROWS=1<<PCW;
    initial if(PCW<8 || PCW>12)$fatal(1,"programme target PCW must be8..12");
    // External reset reaches two synchronizer pins, not the entire valid bitmap.
    (* async_reg = "true" *) reg reset_meta,reset_live;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin reset_meta<=0;reset_live<=0;end
        else begin reset_meta<=1;reset_live<=reset_meta;end
    reg cv,dv,lv;
    reg [7:0] target;
    reg [11:0] address,base;
    reg [PCW-1:0] stored_base;
    reg [255:0] data_q;
    reg [12:0] limit;
    reg [PCW:0] stored_limit;
    reg [15:0] loops,stored_loops;
    reg [ROWS-1:0] installed;
    reg install_open,armed,scanning,validated,missing;
    reg [PCW-1:0] scan_row;
    reg [PCW:0] scan_limit;
    reg [1:0] commit;
    wire launch_ready=armed&&validated&&!scanning&&commit==0&&!program_active&&!fault;
    always @(posedge clk)begin
        target<=cfg_target;address<=cfg_addr;data_q<=cfg_data;
        base<=desc_base;limit<=desc_limit;loops<=desc_loops;
    end
    always @(posedge clk or negedge reset_live)
        if(!reset_live)begin
            cv<=0;dv<=0;lv<=0;program_cfg_we<=0;program_start_v<=0;configured<=0;fault<=0;
            installed<=0;install_open<=0;armed<=0;scanning<=0;validated<=0;missing<=0;
            scan_row<=0;scan_limit<=0;commit<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            program_cfg_we<=0;program_start_v<=0;
            configured<=launch_ready&&!lv&&!((cv||dv)&&target==TARGET);
            // Observe the real registered programme-write pins. The neighbour's
            // capture and SRAM write consume two further edges; commit masks both.
            commit<={commit[0],program_cfg_we};
            if(program_cfg_we)begin
                if(!install_open)installed<=({{(ROWS-1){1'b0}},1'b1}<<program_cfg_addr);
                else installed[program_cfg_addr]<=1'b1;
                install_open<=1;
            end
            if(cv && target==TARGET)begin
                armed<=0;validated<=0;configured<=0;
                if(program_active || scanning || lv || {1'b0,address}>=(13'd1<<PCW) ||
                   data_q[255:240]!=16'hc7a1 || data_q[239:224]!={4'b0,address})fault<=1;
                else begin program_cfg_we<=1;program_cfg_addr<=address[PCW-1:0];program_cfg_data<=data_q;end
            end
            if(dv && target==TARGET)begin
                armed<=0;validated<=0;configured<=0;install_open<=0;
                if(program_active || scanning || lv || cv || loops==0 || limit<={1'b0,base} || limit>(13'd1<<PCW))fault<=1;
                else begin
                    stored_base<=base[PCW-1:0];stored_limit<=limit[PCW:0];stored_loops<=loops;
                    armed<=1;missing<=0;
                    if(validated && base==stored_base && limit==stored_limit)begin
                        // Same range in the unchanged resident generation: reuse
                        // the completed row proof, not a stale descriptor arm.
                        validated<=1;scanning<=0;
                    end else begin
                        scanning<=1;scan_row<=base[PCW-1:0];scan_limit<=limit[PCW:0];
                    end
                end
            end
            if(scanning)begin
                if(!installed[scan_row])missing<=1;
                if({1'b0,scan_row}+1'b1==scan_limit)begin
                    scanning<=0;
                    if(missing || !installed[scan_row])fault<=1;
                    else validated<=1;
                end else scan_row<=scan_row+1'b1;
            end
            if(lv && armed)begin
                armed<=0;configured<=0;
                if(!launch_ready || cv || dv)fault<=1;
                else begin
                    program_start_v<=1;program_start_base<=stored_base;
                    program_start_limit<=stored_limit;program_start_loops<=stored_loops;
                end
            end
        end
endmodule
`default_nettype wire
