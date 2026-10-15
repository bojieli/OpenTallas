`timescale 1ns/1ps
`default_nettype none
module ot_hgi_b2_swap_grp_static #(
    parameter integer MUT=0
)(
    input wire clk,rst_n,
    input wire g_v,g_last,
    input wire [1:0] g_q,
    input wire [226:0] g_mv,
    input wire [31:0] g_issue_at,g_drain_at,
    input wire g_wb_bank,
    input wire [15:0] g_wb_epoch,
    output wire [31:0] cycle,
    output wire fence_quiet,done,fault,
    output wire [3:0] e_src,e_busy,
    output wire [4*8*17-1:0] rq,
    input wire [4*8*257-1:0] rr,
    output wire [3:0] wb_reserve_v,wb_reserve_bank,wb_fill_bank,
    output wire [63:0] wb_reserve_epoch,wb_fill_epoch,
    output wire [4*12-1:0] wb_reserve_sectors,
    output wire [4*32-1:0] wb_reserve_base,
    output wire [3:0] wb_fill_start,
    input wire [3:0] wb_ready,
    output wire [4*8*289-1:0] wd,
    input wire [47:0] wa
);
    wire [4*309-1:0] dn;wire [11:0] up;
    ot_hgi_b2_swap_disp_static dispatcher(.clk(clk),.rst_n(rst_n),.g_v(g_v),.g_last(g_last),.g_q(g_q),.g_mv(g_mv),
        .g_issue_at(g_issue_at),.g_drain_at(g_drain_at),.g_wb_bank(g_wb_bank),.g_wb_epoch(g_wb_epoch),.cycle(cycle),.dn(dn),.up(up),.fence_quiet(fence_quiet),.done(done),.fault(fault));
    for(genvar q=0;q<4;q=q+1)begin:Q
        wire src,quiet,bad;
        ot_hgi_dma_back_static #(.STK(q),.QID(q),.MUT(MUT)) engine(.clk(clk),.rst_n(rst_n),.cycle(cycle),
            .mv_v(dn[q*309]),.mv(dn[q*309+82+:227]),.issue_at(dn[q*309+50+:32]),.drain_at(dn[q*309+18+:32]),
            .mv_wb_bank(dn[q*309+17]),.mv_wb_epoch(dn[q*309+1+:16]),
            .mv_src(src),.mv_done(),.mv_fault(bad),.quiet(quiet),.busy(e_busy[q]),
            .rq(rq[q*136+:136]),.rr(rr[q*2056+:2056]),
            .wb_reserve_v(wb_reserve_v[q]),.wb_reserve_bank(wb_reserve_bank[q]),.wb_fill_bank(wb_fill_bank[q]),
            .wb_reserve_epoch(wb_reserve_epoch[q*16+:16]),.wb_fill_epoch(wb_fill_epoch[q*16+:16]),.wb_reserve_sectors(wb_reserve_sectors[q*12+:12]),.wb_reserve_base(wb_reserve_base[q*32+:32]),
            .wb_fill_start(wb_fill_start[q]),.wb_ready(wb_ready[q]),.wd(wd[q*2312+:2312]),.wa(wa[q*12+:12]));
        assign up[q*3+:3]={bad,quiet,src};assign e_src[q]=src;
    end
endmodule
`default_nettype wire
