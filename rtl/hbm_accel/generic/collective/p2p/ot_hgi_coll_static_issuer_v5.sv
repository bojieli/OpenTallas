`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/COLL-CTL 1045: timing successor of ot_hgi_coll_static_issuer (that file is unchanged and keeps
// ot_hgi_coll_static_program_bank, which this module instantiates). Cycle-exact on every port (busy, done, fault,
// uop_v, uop, iteration, uop_pc) for every programme the original accepts, including several loop-ending rows that
// share a loop id (miter tb_hgi_coll_static_issuer_v5_miter.sv).
//
// The original next-pc recurrence is pc -> meta[pc] (64:1 x 64b) -> lid -> loops[lid] (64:1 x 32b) -> 32b compare
// with count-1 -> pc / loops[lid]+1, in one edge (issuer gate: 19 levels, reg->reg -365 ps). Here:
//  * the CURRENT row's fields are registers (cur_*), loaded with the successor row's fields when pc moves, so no
//    64:1 mux precedes the decision;
//  * loops[] is held per ROW (rowloops[r] == loops[lid(r)] at every edge; every row whose lid equals the visited
//    row's lid is written together), so the successor's loop value is ONE 64:1 read, forwarded when the successor
//    shares the visited row's lid;
//  * cur_loops / cur_cm1 (count-1) are registers: the decision is one 32b compare of two flops;
//  * both successors' fields (target, next) are read in parallel with the decision and the decision only selects.
// No async reset on rowloops / meta / the cur_* data registers: start loads all of them before the first fetch, and
// no fetch happens without a successful start (the original's reset of loops[] is unobservable). Control flops and
// the row-valid bits keep the original's async reset.
module ot_hgi_coll_static_issuer_v5 #(
    parameter integer MUT_DATA=0, MUT_BRANCH=0, MUT_RELOAD=0
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
    reg [31:0] rowloops[0:63];
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
    // current row (the row at pc): registered fields
    reg [5:0] cur_lid,cur_target,cur_next;
    reg cur_halt,cur_has;
    reg [31:0] cur_cm1,cur_loops;
    for(genvar b=0;b<3;b=b+1)begin:g_mem
        ot_hgi_coll_static_program_bank #(.MUT_DATA(MUT_DATA && b==0)) u_bank(
            .clk(clk_mem[b]),.read_v(fetch_v),.read_row(fetch_pc),
            .write_v(write_v[b]),.write_row(write_row),.write_data(write_data),
            .data(uop[b*512+:512]));
    end
    // ---- the decision (two flops into one compare)
    wire take=cur_has && ((MUT_RELOAD!=0) ? (cur_loops<=cur_cm1) : (cur_loops<cur_cm1)) && MUT_BRANCH==0;
    wire [31:0] wv=take ? cur_loops+32'd1 : 32'd0;             // loops[cur_lid] after this visit (when cur_has)
    wire advance=fetching && !cur_halt;
    wire upd=advance && cur_has && MUT_BRANCH==0;              // loops[cur_lid] is written this edge
    // ---- both successors, read in parallel with the decision
    wire [63:0] mt=meta[cur_target], mn=meta[cur_next];
    wire [31:0] lt=(upd && mt[50:45]==cur_lid) ? wv : rowloops[cur_target];
    wire [31:0] ln=(upd && mn[50:45]==cur_lid) ? wv : rowloops[cur_next];
    wire [63:0] ms=meta[start_pc];
    wire [63:0] m=meta[pc];
    always @(posedge clk_control)begin
        // data registers without reset (loaded by start before any fetch)
        if(start && !(busy || cfg[36] || fragment!=0))begin
            for(integer i=0;i<64;i=i+1)rowloops[i]<=0;
            cur_lid<=ms[50:45];cur_target<=ms[11:6];cur_next<=ms[5:0];cur_halt<=ms[44];
            cur_has<=ms[43:12]!=0;cur_cm1<=ms[43:12]-32'd1;cur_loops<=0;
        end
        if(advance)begin
            if(upd)for(integer i=0;i<64;i=i+1)if(meta[i][50:45]==cur_lid)rowloops[i]<=wv;
            if(take)begin
                cur_lid<=mt[50:45];cur_target<=mt[11:6];cur_next<=mt[5:0];cur_halt<=mt[44];
                cur_has<=mt[43:12]!=0;cur_cm1<=mt[43:12]-32'd1;cur_loops<=lt;
            end else begin
                cur_lid<=mn[50:45];cur_target<=mn[11:6];cur_next<=mn[5:0];cur_halt<=mn[44];
                cur_has<=mn[43:12]!=0;cur_cm1<=mn[43:12]-32'd1;cur_loops<=ln;
            end
        end
    end
    always @(posedge clk_control or negedge rst_n)begin
        if(!rst_n)begin
            busy<=0;done<=0;fault<=0;fetching<=0;fetch_v<=0;v1<=0;uop_v<=0;
            h0<=0;h1<=0;cfg_selected<=0;fragment<=0;write_v<=0;
            meta_lo_valid<=0;meta_hi_valid<=0;iteration<=0;uop_pc<=0;
            for(integer b=0;b<3;b=b+1)word_valid[b]<=0;
        end else begin
            done<=0;write_v<=0;fetch_v<=0;
            v1<=fetch_v;uop_v<=v1;
            pc1<=fetch_pc;uop_pc<=pc1;it1<=it0;iteration<=it1;h1<=h0;
            if(v1 && h1)begin busy<=0;done<=1;end
            if(start)begin
                if(busy || cfg[36] || fragment!=0)fault<=1;
                else begin
                    pc<=start_pc;busy<=1;fetching<=1;
                end
            end
            if(fetching)begin
                if(!word_valid[0][pc] || !word_valid[1][pc] || !word_valid[2][pc] ||
                   !meta_lo_valid[pc] || !meta_hi_valid[pc])fault<=1;
                fetch_v<=1;fetch_pc<=pc;it0<=cur_loops;h0<=cur_halt;
                if(m[63:51]!=0)fault<=1;
                if(cur_halt)fetching<=0;
                else pc<=take ? cur_target : cur_next;
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
`default_nettype wire
