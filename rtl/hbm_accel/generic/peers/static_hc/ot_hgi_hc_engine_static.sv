`timescale 1ns/1ps
`default_nettype none
// Real static HC arithmetic/storage composition, W32, production K20480.
// Compiler reserves residual landing, weight aperture fills, each row launch,
// accumulator reads, tail launch, and both Sinkhorn clock-domain slots.
// x_wave is 32 consecutive sectors (32 chunks of8 FP32 BF16-valued residuals)
// already in logical lane order; the VM-side fixed permutation is upstream.
// There are exactly64 weight SRAMs plus16 residual SRAMs, no inferred operand
// memory substitute. Phy prefetch/staging, VM bridges and record lowering
// are outside this component boundary and need native composition evidence.
module ot_hgi_hc_engine_static #(
    parameter integer MUT_PRE=0
)(
    input wire clk,sink_clk,rst_n,
    input wire clear,
    input wire [2223:0] weight_ap,
    input wire x_wave_v,
    input wire [6:0] x_wave_row,
    input wire [8191:0] x_wave,
    input wire row_launch,row_raw_read,row_weight_slot,
    input wire [4:0] row_id,
    input wire [31:0] norm_eps,
    input wire gathered_mix_v,
    input wire [4:0] gathered_mix_row,
    input wire [31:0] gathered_mix_data,
    input wire tail_launch,sink_launch,sink_capture,
    input wire [767:0] bases,
    input wire [95:0] scales,
    output wire row_result_v,
    output wire [4:0] row_result_id,
    output wire [31:0] row_result,
    output wire result_v,
    output wire [767:0] result,
    output wire tail_e_ready,
    output wire fault
);
    wire [7:0] wr,xr,wdone,rv;
    wire [127:0] wa,xa;
    wire [55:0] wrow;
    wire [8191:0] wraw;
    reg [8191:0] wd;
    wire [4095:0] xraw;
    reg [4095:0] xd;
    reg slot;
    reg [4:0] tag;
    reg [767:0] mixes;
    reg [23:0] have;
    reg own_fault;
    wire wf,pf,tf;
    wire [7:0] rslot={8{slot}};
    assign row_result_id=tag;
    assign fault=own_fault|wf|pf|tf;
    always @(posedge clk)begin wd<=wraw;xd<=xraw;end
    for(genvar b=0;b<8;b=b+1)begin:bank
        assign wrow[b*7+:7]=wa[b*16+:7];
        for(genvar m=0;m<2;m=m+1)begin:half
            wire [255:0] data;
            for(genvar l=0;l<16;l=l+1)begin:lane
                // VM sector lane l owns one chunk; term b goes to bank b.
                assign data[l*16+:16]=x_wave[(m*16+l)*256+b*32+16+:16];
            end
            ot_sram_1r1w_128x256_m1_r2c2 u_x(
                .clk(clk),.r_ce_in(xr[b]),.r_addr_in(xa[b*16+:7]),
                .rd_out(xraw[b*512+m*256+:256]),
                .w_ce_in(x_wave_v),.w_addr_in(x_wave_row),.wd_in(data),.w_mask_in({256{1'b1}}),
                .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
        end
    end
    ot_hgi_hc_aperture_static weight_store(
        .clk(clk),.rst_n(rst_n),.ap(weight_ap),.write_done(wdone),
        .read_v(wr),.read_slot(rslot),.read_row(wrow),.read_valid(rv),.raw_weight(wraw),.fault(wf));
    ot_hgi_hc_projection_static #(.PMAX(1),.OMAX(2),.DF(4)) projection(
        .clk(clk),.rst_n(rst_n),.launch(row_launch),.raw_read(row_raw_read),
        .npos(2'd1),.nout(2'd1),.nchunk(16'd2560),.scale(1'b1),.nf(32'h46a00000),
        .eps(norm_eps),.wbase(16'd0),.xbase(16'd0),
        .w_re(wr),.x_re(xr),.w_addr(wa),.x_addr(xa),.w_data(wd),.x_data(xd),
        .result_v(row_result_v),.result_last(),.result_pos(),.result_row(),.result_data(row_result),.fault(pf));
    ot_hgi_hc_tail_static #(.MUT_PRE(MUT_PRE)) tail(
        .clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),.launch(tail_launch),
        .mixes(mixes),.bases(bases),.scales(scales),.sink_launch(sink_launch),.sink_capture(sink_capture),
        .e_ready(tail_e_ready),.result_v(result_v),.result(result),.fault(tf));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin have<=0;own_fault<=0;slot<=0;tag<=0;end
        else begin
            if(clear)have<=0;
            if(row_launch)begin
                slot<=row_weight_slot;tag<=row_id;
                if(row_id>=24)own_fault<=1;
            end
            if(row_result_v)begin
                if(tag>=24)own_fault<=1;
                else begin mixes[tag*32+:32]<=row_result;have[tag]<=1;end
            end
            if(gathered_mix_v)begin
                if(gathered_mix_row>=24)own_fault<=1;
                else begin
                    mixes[gathered_mix_row*32+:32]<=gathered_mix_data;
                    have[gathered_mix_row]<=1;
                end
                if(row_result_v&&tag==gathered_mix_row)own_fault<=1;
            end
            if(tail_launch&&have!=24'hffffff)own_fault<=1;
            if(x_wave_v)begin
                if(x_wave_row>=80)own_fault<=1;
                for(integer l=0;l<256;l=l+1)if(x_wave[l*32+:16]!=0)own_fault<=1;
            end
        end
    end
endmodule
`default_nettype wire
