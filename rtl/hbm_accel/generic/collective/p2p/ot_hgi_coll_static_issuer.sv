`timescale 1ns/1ps
`default_nettype none
// Actual program SRAM issuer. Configuration is exceptional initialization;
// normal execution fetches one 1536b micro-op every edge on its fixed timeline.
// Three native 64x512 macros, no behavioral/DPI replacement memory.
// cfg = {v,cmd4,data32}: 0 selects row[5:0]/bank[7:6]; 1 writes
// sixteen low-to-high 32b fragments; 2/3 write low/high metadata for row.
// metadata = {reserved13,loop_id6,halt1,repeat_count32,targetPC6,nextPC6}.
// count includes total visits of the loop-ending row. Body rows use the same
// loop_id (normally ending PC); ending fetch increments that counter before
// the next body fetch. Last visit resets it and falls through nextPC.
// Native SRAM read plus registered memory-leaf output costs two edges from
// registered fetch request. First uop = start+3; then exactly one per cycle.
module ot_hgi_coll_static_issuer #(
    parameter integer MUT_DATA=0, MUT_BRANCH=0
)(
    input wire clk_control,
    input wire [2:0] clk_mem,
    input wire rst_n,
    input wire [36:0] cfg,
    input wire start,
    input wire [5:0] start_pc,
    output reg busy,done,fault,
    output reg uop_v,
    output wire [1535:0] uop,
    output reg [31:0] iteration,
    output reg [5:0] uop_pc
);
    reg [63:0] meta[0:63];
    reg [31:0] loops[0:63];
    reg [63:0] word_valid[0:2];
    reg [63:0] meta_lo_valid,meta_hi_valid;
    reg [5:0] cfg_row,pc;
    reg [1:0] cfg_bank;
    reg cfg_selected;
    reg [3:0] fragment;
    reg [511:0] assemble;
    reg [2:0] write_v;
    reg [5:0] write_row;
    reg [511:0] write_data;
    reg fetching,fetch_v,v1,h0,h1;
    reg [5:0] fetch_pc,pc1;
    reg [31:0] it0,it1;
    wire [63:0] m=meta[pc];
    wire [5:0] lid=m[50:45];
    wire [31:0] count=m[43:12];
    for(genvar b=0;b<3;b=b+1)begin:g_mem
        ot_hgi_coll_static_program_bank #(.MUT_DATA(MUT_DATA && b==0)) u_bank(
            .clk(clk_mem[b]),.read_v(fetch_v),.read_row(fetch_pc),
            .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),
            .data(uop[b*512+:512]));
    end
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            busy<=0;done<=0;fault<=0;fetching<=0;fetch_v<=0;v1<=0;uop_v<=0;
            h0<=0;h1<=0;cfg_selected<=0;fragment<=0;write_v<=0;
            meta_lo_valid<=0;meta_hi_valid<=0;iteration<=0;uop_pc<=0;
            for(integer b=0;b<3;b=b+1)word_valid[b]<=0;
            for(integer i=0;i<64;i=i+1)loops[i]<=0;
        end else begin
            done<=0;write_v<=0;fetch_v<=0;
            v1<=fetch_v;uop_v<=v1;
            pc1<=fetch_pc;uop_pc<=pc1;it1<=it0;iteration<=it1;h1<=h0;
            if(v1 && h1)begin busy<=0;done<=1;end
            if(start)begin
                if(busy || cfg[36] || fragment!=0)fault<=1;
                else begin
                    pc<=start_pc;busy<=1;fetching<=1;
                    for(integer i=0;i<64;i=i+1)loops[i]<=0;
                end
            end
            if(fetching)begin
                // Missing rows fault at the assigned fetch edge, with no wait.
                if(!word_valid[0][pc] || !word_valid[1][pc] || !word_valid[2][pc] ||
                   !meta_lo_valid[pc] || !meta_hi_valid[pc])fault<=1;
                fetch_v<=1;fetch_pc<=pc;it0<=loops[lid];h0<=m[44];
                if(m[63:51]!=0)fault<=1;
                if(m[44])fetching<=0;
                else if(count!=0 && MUT_BRANCH==0)begin
                    if(loops[lid]<count-1'b1)begin pc<=m[11:6];loops[lid]<=loops[lid]+1'b1;end
                    else begin pc<=m[5:0];loops[lid]<=0;end
                end else pc<=m[5:0];
            end
            if(cfg[36])begin
                if(busy || start)fault<=1;
                else case(cfg[35:32])
                    4'd0:begin
                        if(fragment!=0 || cfg[31:8]!=0 || cfg[7:6]==3)fault<=1;
                        cfg_row<=cfg[5:0];cfg_bank<=cfg[7:6];cfg_selected<=cfg[7:6]!=3;
                        fragment<=0;
                    end
                    4'd1:begin
                        if(!cfg_selected || cfg_bank==3)fault<=1;
                        else begin
                            assemble[fragment*32+:32]<=cfg[31:0];fragment<=fragment+1'b1;
                            if(fragment==15)begin
                                write_v[cfg_bank]<=1;write_row<=cfg_row;
                                write_data<={cfg[31:0],assemble[479:0]};
                                word_valid[cfg_bank][cfg_row]<=1;
                            end
                        end
                    end
                    4'd2:begin
                        if(!cfg_selected || fragment!=0)fault<=1;
                        else begin meta[cfg_row][31:0]<=cfg[31:0];meta_lo_valid[cfg_row]<=1;end
                    end
                    4'd3:begin
                        if(!cfg_selected || fragment!=0 || cfg[31:19]!=0)fault<=1;
                        else begin meta[cfg_row][63:32]<=cfg[31:0];meta_hi_valid[cfg_row]<=1;end
                    end
                    default:fault<=1;
                endcase
            end
        end
    end
endmodule

// True hardenable macro leaf: one actual catalog SRAM, registered face data.
// Request/address and write command originate at control registers. Each leaf
// clock must have the same logical edge, with physical insertion compensated.
// XDIE-HBM4 (10-19): ROWS 128 = two 64-row macros (row[6] selects; the read half is registered with the macro read so
// the output select is a flop -> 2:1 mux -> face flop). ROWS 64 (default): the original single macro, unchanged.
// TW2-COLLAR (10-19): the low macro is ALWAYS u_sram, outside any generate block, so ROWS 64 elaborates to the pre-XDIE
// instance path (u_bank.u_sram: closed hcoll_v5_issuer / q2-q3 LP kits place it by that exact name); only the upper
// macro and the hi_q select flop live in g128 (u_bank.g128.u_sram_hi). The row-6 gate is a constant 0 at ROWS 64.
module ot_hgi_coll_static_program_bank #(parameter integer MUT_DATA=0, parameter integer ROWS=64,
    parameter integer PW=(ROWS>64)?7:6)(   // PW derived; never override
    input wire clk,read_v,write_v,
    input wire [PW-1:0] read_row,write_row,
    input wire [511:0] write_data,
    output reg [511:0] data
);
    wire [511:0] rq,rq_lo;
    wire [7:0] rrow=read_row,wrow=write_row;          // zero-extended: bit 6 exists only for ROWS 128
    wire r_hi=(ROWS>64)&&rrow[6],w_hi=(ROWS>64)&&wrow[6];
    ot_sram_1r1w_64x512_m1_r2c2 u_sram(
        .clk(clk),.r_ce_in(read_v && !r_hi),.r_addr_in(rrow[5:0]),.rd_out(rq_lo),
        .w_ce_in(write_v && !w_hi),.w_addr_in(wrow[5:0]),.wd_in(write_data),.w_mask_in({512{1'b1}}),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
    generate if(ROWS>64)begin:g128
    wire [511:0] rq_hi;reg hi_q;
    always @(posedge clk)if(read_v)hi_q<=r_hi;
    ot_sram_1r1w_64x512_m1_r2c2 u_sram_hi(
        .clk(clk),.r_ce_in(read_v && r_hi),.r_addr_in(rrow[5:0]),.rd_out(rq_hi),
        .w_ce_in(write_v && w_hi),.w_addr_in(wrow[5:0]),.wd_in(write_data),.w_mask_in({512{1'b1}}),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
    assign rq=hi_q?rq_hi:rq_lo;
    end else begin:g64
    assign rq=rq_lo;
    end endgenerate
    always @(posedge clk)data<=rq^(MUT_DATA?512'b1:512'b0);
endmodule
`default_nettype wire
