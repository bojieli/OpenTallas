`timescale 1ns/1ps
`default_nettype none
// SYS1 shared-shell static HC successor, W32, production K20480.
// Compiler reserves residual landing, weight aperture fills, each row launch,
// accumulator reads, tail launch, and both Sinkhorn clock-domain slots.
// x_wave is 32 consecutive sectors (32 chunks of8 FP32 BF16-valued residuals)
// already in logical lane order; the VM-side fixed permutation is upstream.
// PMAX8: exactly64 weight128x256 SRAMs plus16 residual1024x256 SRAMs.
// A row command reuses its weights across all npos positions without a command
// gap, and each position retains its own24mixes for the scheduled tail.
// No inferred operand
// memory substitute. Phy prefetch/staging, VM bridges and record lowering
// are outside this component boundary and need native composition evidence.
module ot_hgi_hc_engine_sys1_split_mtp_static #(
    parameter integer MUT_PRE=0
)(
    input wire clk,reduction_clk,scalar_clk,sink_clk,rst_n,
    input wire [31:0] weight_clk,input wire [15:0] residual_clk,
    input wire [7:0] bank_clk,
    input wire [31:0] mac_clk,
    input wire clear,
    input wire [2223:0] weight_ap,
    input wire x_wave_v,
    input wire [9:0] x_wave_word,
    input wire [8191:0] x_wave,
    input wire row_launch,row_raw_read,row_weight_slot,
    input wire [4:0] row_id,
    input wire [3:0] row_npos,
    input wire [31:0] norm_eps,
    input wire gathered_mix_v,
    input wire [4:0] gathered_mix_row,
    input wire [2:0] gathered_mix_pos,
    input wire [31:0] gathered_mix_data,
    input wire tail_launch,sink_launch,sink_capture,
    input wire [2:0] tail_position,
    input wire [767:0] bases,
    input wire [95:0] scales,
    output wire row_result_v,
    output wire [4:0] row_result_id,
    output wire [2:0] row_result_pos,
    output wire [31:0] row_result,
    output wire result_v,
    output reg [2:0] tail_result_pos,
    output wire [767:0] result,
    output wire tail_e_ready,
    output wire fault
);
    reg [4:0] tag;
    reg [8*768-1:0] mixes;
    reg [8*24-1:0] have;
    reg own_fault;
    wire pf,tf;
    assign row_result_id=tag;
    assign fault=own_fault|pf|tf;
    ot_hgi_hc_projection_sys1_split_static projection(
        .clk(clk),.reduction_clk(reduction_clk),.scalar_clk(scalar_clk),.bank_clk(bank_clk),.weight_clk(weight_clk),.residual_clk(residual_clk),.mac_clk(mac_clk),.rst_n(rst_n),
        .weight_ap(weight_ap),.x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),
        .launch(row_launch),.raw_read(row_raw_read),.weight_slot(row_weight_slot),.npos(row_npos),.eps(norm_eps),
        .result_v(row_result_v),.result_pos(row_result_pos),.result_data(row_result),.fault(pf));
    ot_hgi_hc_tail_static #(.MUT_PRE(MUT_PRE)) tail(
        .clk(scalar_clk),.sink_clk(sink_clk),.rst_n(rst_n),.launch(tail_launch),
        .mixes(mixes[tail_position*768+:768]),.bases(bases),.scales(scales),.sink_launch(sink_launch),.sink_capture(sink_capture),
        .e_ready(tail_e_ready),.result_v(result_v),.result(result),.fault(tf));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin have<=0;own_fault<=0;tag<=0;tail_result_pos<=0;end
        else begin
            if(clear)have<=0;
            if(row_launch)begin
                tag<=row_id;
                if(row_id>=24||row_npos<1||row_npos>8)own_fault<=1;
            end
            if(row_result_v)begin
                if(tag>=24)own_fault<=1;
                else begin mixes[(row_result_pos*24+tag)*32+:32]<=row_result;have[row_result_pos*24+tag]<=1;end
            end
            if(gathered_mix_v)begin
                if(gathered_mix_row>=24)own_fault<=1;
                else begin
                    mixes[(gathered_mix_pos*24+gathered_mix_row)*32+:32]<=gathered_mix_data;
                    have[gathered_mix_pos*24+gathered_mix_row]<=1;
                end
                if(row_result_v&&tag==gathered_mix_row&&row_result_pos==gathered_mix_pos)own_fault<=1;
            end
            if(tail_launch)begin
                tail_result_pos<=tail_position;
                if(have[tail_position*24+:24]!=24'hffffff)own_fault<=1;
            end
            if(x_wave_v)begin
                if(x_wave_word>=640)own_fault<=1;
                for(integer l=0;l<256;l=l+1)if(x_wave[l*32+:16]!=0)own_fault<=1;
            end
        end
    end
endmodule
`default_nettype wire
