`timescale 1ns/1ps
// Experimental leaf-preserving VM glue. Not connected to the production VM.
// Physical spec: results/arch/qwen_tp8_1012/vm_distributed_plan_codex.json.
// Each 256-bit slice owns a local root: at most (256+7)*D flops, below 15k.
// D includes matched transport for BOTH mux alternatives and the selection tag.
// All paths advance on enabled ENGINE edges, never wall-clock edges. No drops,
// arithmetic changes, credits or memory scheduling changes occur in this helper.
module ot_qfd_vm_rotation_slice #(
    parameter integer W = 256,
    parameter integer SEL = 3,
    parameter integer D = 2,
    parameter integer MUT = 0
) (
    input wire clk, rst_n, me_ce, in_valid,
    input wire [5:0] in_rot,
    input wire [W-1:0] in_self, in_shifted,
    output wire out_valid,
    output wire [5:0] out_rot,
    output wire [W-1:0] out_data
);
    (* keep *) reg [D-1:0] valid_pipe;
    (* keep *) reg [5:0] rot_pipe [0:D-1];
    (* keep *) reg [W-1:0] data_pipe [0:D-1];
    integer k;
    initial begin
        if (D < 1 || (W+7)*D > 15000) $fatal(1,"invalid local VM root budget");
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) valid_pipe <= 0;
        else if (me_ce) begin
            valid_pipe[0] <= in_valid;
            for (k=1;k<D;k=k+1) valid_pipe[k] <= valid_pipe[k-1];
        end
    end
    always @(posedge clk) if (me_ce) begin
        rot_pipe[0] <= in_rot;
        data_pipe[0] <= (in_rot[SEL] ^ (MUT != 0)) ? in_shifted : in_self;
        for (k=1;k<D;k=k+1) begin
            rot_pipe[k] <= rot_pipe[k-1];
            data_pipe[k] <= data_pipe[k-1];
        end
    end
    assign out_valid=valid_pipe[D-1];
    assign out_rot=rot_pipe[D-1];
    assign out_data=data_pipe[D-1];
endmodule

// Six pipelined shifts implement exactly output bank i = input bank (i+rot)%64.
// The first three shifts replace coarse rotation; the last three replace fine.
// This module is a composition bench vehicle. Physical integration connects the
// independently rooted slices through the obstacle-aware registered corridors.
module ot_qfd_vm_regional_rotation #(
    parameter integer BANK_W=512,
    parameter integer SLICE_W=256,
    parameter integer D0=2, D1=2, D2=2, D3=2, D4=2, D5=2,
    parameter integer MUT=0
) (
    input wire clk, rst_n, me_ce, in_valid,
    input wire [5:0] in_rot,
    input wire [64*BANK_W-1:0] in_data,
    output wire out_valid,
    output wire [5:0] out_rot,
    output wire [64*BANK_W-1:0] out_data
);
    wire [64*BANK_W-1:0] data [0:6];
    wire [5:0] rot [0:6];
    wire valid [0:6];
    assign data[0]=in_data;
    assign rot[0]=in_rot;
    assign valid[0]=in_valid;
    genvar s,b,l;
    generate for(s=0;s<6;s=s+1) begin:g_stage
        localparam integer SEL=(s<3)?s+3:s-3;
        localparam integer SHIFT=1<<SEL;
        localparam integer LAT=(s==0)?D0:(s==1)?D1:(s==2)?D2:(s==3)?D3:(s==4)?D4:D5;
        wire [63:0] bank_valid;
        wire [64*6-1:0] bank_rot;
        for(b=0;b<64;b=b+1) begin:g_bank
            wire [BANK_W/SLICE_W-1:0] slice_valid;
            wire [(BANK_W/SLICE_W)*6-1:0] slice_rot;
            for(l=0;l<BANK_W/SLICE_W;l=l+1) begin:g_slice
                ot_qfd_vm_rotation_slice #(.W(SLICE_W),.SEL(SEL),.D(LAT),.MUT((s==0)?MUT:0)) u_slice (
                    .clk(clk),.rst_n(rst_n),.me_ce(me_ce),.in_valid(valid[s]),.in_rot(rot[s]),
                    .in_self(data[s][b*BANK_W+l*SLICE_W+:SLICE_W]),
                    .in_shifted(data[s][((b+SHIFT)%64)*BANK_W+l*SLICE_W+:SLICE_W]),
                    .out_valid(slice_valid[l]),.out_rot(slice_rot[l*6+:6]),
                    .out_data(data[s+1][b*BANK_W+l*SLICE_W+:SLICE_W]));
            end
            assign bank_valid[b]=slice_valid[0];
            assign bank_rot[b*6+:6]=slice_rot[0+:6];
        end
        assign valid[s+1]=bank_valid[0];
        assign rot[s+1]=bank_rot[0+:6];
    end endgenerate
    assign out_valid=valid[6];
    assign out_rot=rot[6];
    assign out_data=data[6];
    initial if(BANK_W%SLICE_W != 0) $fatal(1,"unaligned rotation slices");
endmodule
