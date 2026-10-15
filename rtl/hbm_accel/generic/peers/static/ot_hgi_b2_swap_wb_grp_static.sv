`timescale 1ps/1fs
`default_nettype none
// Real compiler DMA group -> two-buffer SRAM WB -> CDC -> actual PHY boundary.
// Reservation receipts affect only the one fixed-calendar block fault check.
// No per-lane ready or credit crosses from this boundary into on-chip DMA.
module ot_hgi_b2_swap_wb_grp_static #(
 parameter integer WB_PIPELINE=0,
 parameter integer MUT=0 // 1 premature whole-block completion (gate must fail)
)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire g_v,g_last,input wire [1:0] g_q,input wire [226:0] g_mv,
 input wire [31:0] g_issue_at,g_drain_at,input wire g_wb_bank,input wire [15:0] g_wb_epoch,
 output wire [31:0] cycle,output wire fence_quiet,done,fault,
 output wire [3:0] e_src,e_busy,wb_done_v,wb_fill_done,wb_fault,
 output wire [47:0] actual_posted_sectors,
 output wire [543:0] rq,input wire [8223:0] rr,
 output wire [4*32-1:0] k_v,input wire [4*32-1:0] k_rdy,
 output wire [4*960-1:0] k_addr,output wire [4*128-1:0] k_len,
 output wire [4*544-1:0] k_tag,output wire [4*32-1:0] k_we,
 output wire [4*8192-1:0] k_wdata,output wire [4*1024-1:0] k_wstrb,
 input wire [4*32-1:0] k_wr_done
);
 wire global_reset=stream_rst_n&&hbm_rst_n;wire stream_reset;
 ot_reset_sync sync_reset(.clk(stream_clk),.async_rst_n(global_reset),.sync_rst_n(stream_reset));
 wire [3:0] reserve,fill_start,reserve_bank,fill_bank,reserve_ready,block_ready;
 wire [63:0] reserve_epoch,fill_epoch;wire [47:0] reserve_total;wire [127:0] reserve_base;
 wire [9247:0] wd;wire [47:0] wa;wire group_fault,group_quiet;
 reg [3:0] reservation_fault;
 ot_hgi_b2_swap_grp_static dma(.clk(stream_clk),.rst_n(stream_reset),
 .g_v(g_v),.g_last(g_last),.g_q(g_q),.g_mv(g_mv),.g_issue_at(g_issue_at),.g_drain_at(g_drain_at),.g_wb_bank(g_wb_bank),.g_wb_epoch(g_wb_epoch),
 .cycle(cycle),.fence_quiet(group_quiet),.done(done),.fault(group_fault),.e_src(e_src),.e_busy(e_busy),.rq(rq),.rr(rr),
 .wb_reserve_v(reserve),.wb_reserve_bank(reserve_bank),.wb_fill_bank(fill_bank),.wb_reserve_epoch(reserve_epoch),.wb_fill_epoch(fill_epoch),
 .wb_reserve_sectors(reserve_total),.wb_reserve_base(reserve_base),.wb_fill_start(fill_start),.wb_ready(block_ready),.wd(wd),.wa(wa));
 assign fault=group_fault||(|wb_fault)||(|reservation_fault);
 assign fence_quiet=group_quiet&&!fault;
 assign actual_posted_sectors=wa;
 for(genvar q=0;q<4;q=q+1)begin:Q
  wire [1:0] owned;wire returned_bank;wire [15:0] returned_epoch;wire [11:0] returned_sectors;
  reg [1:0] accepted;reg [15:0] epoch[0:1];reg [11:0] total[0:1];
  assign block_ready[q]=accepted[fill_bank[q]]&&epoch[fill_bank[q]]==fill_epoch[q*16+:16]&&owned[fill_bank[q]];
  assign wa[q*12+:12]=MUT==1?(wb_fill_done[q]?reserve_total[q*12+:12]:12'd0):(wb_done_v[q]?returned_sectors:12'd0);
  if(WB_PIPELINE==0)begin:HISTORICAL_WB
  ot_hbm_svc_wb_block_cdc #(.STACK(2'(q))) wb(.stream_clk(stream_clk),.stream_rst_n(stream_reset),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
   .reserve_v(reserve[q]),.reserve_ready(reserve_ready[q]),.reserve_bank(reserve_bank[q]),.reserve_epoch(reserve_epoch[q*16+:16]),.reserve_base(reserve_base[q*32+:32]),.reserve_total(reserve_total[q*12+:12]),
   .fill_start(fill_start[q]),.fill_start_bank(fill_bank[q]),.fill_start_epoch(fill_epoch[q*16+:16]),.wd(wd[q*2312+:2312]),
   .fill_done(wb_fill_done[q]),.done_v(wb_done_v[q]),.done_bank(returned_bank),.done_epoch(returned_epoch),.done_sectors(returned_sectors),.bank_owned(owned),.fault(wb_fault[q]),
   .k_v(k_v[q*32+:32]),.k_rdy(k_rdy[q*32+:32]),.k_addr(k_addr[q*960+:960]),.k_len(k_len[q*128+:128]),.k_tag(k_tag[q*544+:544]),.k_we(k_we[q*32+:32]),
   .k_wdata(k_wdata[q*8192+:8192]),.k_wstrb(k_wstrb[q*1024+:1024]),.k_wr_done(k_wr_done[q*32+:32]));
  end else if(WB_PIPELINE==1)begin:PIPELINED_WB
  ot_hbm_svc_wb_pipeline_cdc #(.STACK(2'(q))) wb(.stream_fifo_clk({4{stream_clk}}),.stream_clk(stream_clk),.stream_rst_n(stream_reset),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
   .reserve_v(reserve[q]),.reserve_ready(reserve_ready[q]),.reserve_bank(reserve_bank[q]),.reserve_epoch(reserve_epoch[q*16+:16]),.reserve_base(reserve_base[q*32+:32]),.reserve_total(reserve_total[q*12+:12]),
   .fill_start(fill_start[q]),.fill_start_bank(fill_bank[q]),.fill_start_epoch(fill_epoch[q*16+:16]),.wd(wd[q*2312+:2312]),
   .fill_done(wb_fill_done[q]),.done_v(wb_done_v[q]),.done_bank(returned_bank),.done_epoch(returned_epoch),.done_sectors(returned_sectors),.bank_owned(owned),.fault(wb_fault[q]),
   .k_v(k_v[q*32+:32]),.k_rdy(k_rdy[q*32+:32]),.k_addr(k_addr[q*960+:960]),.k_len(k_len[q*128+:128]),.k_tag(k_tag[q*544+:544]),.k_we(k_we[q*32+:32]),
   .k_wdata(k_wdata[q*8192+:8192]),.k_wstrb(k_wstrb[q*1024+:1024]),.k_wr_done(k_wr_done[q*32+:32]));  end else begin:CUTTHROUGH_WB
  ot_hbm_svc_wb_cutthrough_cdc #(.STACK(2'(q))) wb(.stream_fifo_clk({4{stream_clk}}),.stream_clk(stream_clk),.stream_rst_n(stream_reset),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
   .reserve_v(reserve[q]),.reserve_ready(reserve_ready[q]),.reserve_bank(reserve_bank[q]),.reserve_epoch(reserve_epoch[q*16+:16]),.reserve_base(reserve_base[q*32+:32]),.reserve_total(reserve_total[q*12+:12]),
   .fill_start(fill_start[q]),.fill_start_bank(fill_bank[q]),.fill_start_epoch(fill_epoch[q*16+:16]),.wd(wd[q*2312+:2312]),
   .fill_done(wb_fill_done[q]),.done_v(wb_done_v[q]),.done_bank(returned_bank),.done_epoch(returned_epoch),.done_sectors(returned_sectors),.bank_owned(owned),.fault(wb_fault[q]),
   .k_v(k_v[q*32+:32]),.k_rdy(k_rdy[q*32+:32]),.k_addr(k_addr[q*960+:960]),.k_len(k_len[q*128+:128]),.k_tag(k_tag[q*544+:544]),.k_we(k_we[q*32+:32]),
   .k_wdata(k_wdata[q*8192+:8192]),.k_wstrb(k_wstrb[q*1024+:1024]),.k_wr_done(k_wr_done[q*32+:32]));
  end
  always @(posedge stream_clk or negedge stream_reset)
   if(!stream_reset)begin accepted<=0;epoch[0]<=0;epoch[1]<=0;total[0]<=0;total[1]<=0;reservation_fault[q]<=0;end
   else begin
    if(reserve[q])begin
     if(!reserve_ready[q])reservation_fault[q]<=1;
     else begin accepted[reserve_bank[q]]<=1;epoch[reserve_bank[q]]<=reserve_epoch[q*16+:16];total[reserve_bank[q]]<=reserve_total[q*12+:12];end
    end
    if(wb_done_v[q])begin
     if(!accepted[returned_bank]||epoch[returned_bank]!=returned_epoch||total[returned_bank]!=returned_sectors)reservation_fault[q]<=1;
     accepted[returned_bank]<=0;
    end
   end
 end
endmodule
`default_nettype wire
