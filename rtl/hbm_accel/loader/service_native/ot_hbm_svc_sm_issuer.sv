`timescale 1ns/1ps
`default_nettype none
// H-DIE 2026-10-15: per-SM HBM service ISSUER -- the hardware that issues the SM service group's block descriptors
// (reserve), landing->cache copies (start) and programme launches (go).  Until now the testbench issued them; in the
// die they were 816 exposed band/delivery command inputs.  The compiler writes a descriptor table at initialization
// (host loader, desc_*); one run launch then issues run_count descriptors in table order with no further input:
//   reserve  desc[i] as soon as its landing block is free (reserve_ready: the block's previous copy drained);
//   start    copy i into cache bank i.bank[0] once its landing block is RESIDENT (block_ready: the HBM data arrived --
//            the elastic off-die HBM boundary, HANDOFF 0az) and that cache bank is no longer owned;
//   go       programme [prog_base, prog_limit) x loops once cache bank i.bank[0] is ready, after the previous programme
//            reported done.  The programme itself is the fixed-cycle SM calendar.
// Descriptor word (256 b, one ot_sram_1r1w_128x256 row): [31:0] base, [46:32] row_base, [48:47] landing index,
// [64:49] epoch, [71:65] rows, [81:72] tag_base, [91:82] prog_base, [102:92] prog_limit, [118:103] loops,
// [255:240] magic 5d15, [239:233] row identity, other bits zero.  total = ceil(rows*136/128)*4 sectors (the feed's rule).
// fault: bad word, an issue the feed refuses, or a launch while running.
module ot_hbm_svc_sm_issuer #(parameter integer LBANKS=4, parameter integer LB=(LBANKS>2)?2:1, parameter integer QD=4)(
 input wire clk,rst_n,
 input wire desc_we,input wire[6:0]desc_addr,input wire[255:0]desc_data,
 input wire run_v,input wire[6:0]run_base,input wire[7:0]run_count,
 output reg running,run_done,fault,
 output wire reserve_v,input wire reserve_ready,output wire[31:0]reserve_base,output wire[14:0]reserve_row_base,
 output wire[11:0]reserve_total,output wire[LB-1:0]reserve_bank,output wire[15:0]reserve_epoch,output wire[6:0]reserve_rows,
 output wire[9:0]reserve_tag_base,
 input wire[LBANKS-1:0]block_ready,input wire[1:0]cache_ready,cache_owned,
 output wire start_v,output wire[LB-1:0]start_bank,output wire[15:0]start_epoch,
 output wire program_start_v,output wire[9:0]program_start_base,output wire[10:0]program_start_limit,output wire[15:0]program_start_loops,
 input wire program_done
);
 // descriptor table: one actual 128x256 SRAM, registered write port (as the programme calendar)
 reg desc_we_q;reg[6:0]desc_addr_q;reg[255:0]desc_data_q;
 always @(posedge clk)begin desc_addr_q<=desc_addr;desc_data_q<=desc_data;end
 always @(posedge clk or negedge rst_n)if(!rst_n)desc_we_q<=0;else desc_we_q<=desc_we;
 reg rd_q;reg[6:0]rp,rp_q;wire[255:0]rd;
 wire rd_go;
 ot_sram_1r1w_128x256_m1_r2c2 u_desc(.clk(clk),.r_ce_in(rd_go),.r_addr_in(rp),.rd_out(rd),
  .w_ce_in(desc_we_q&&!running),.w_addr_in(desc_addr_q),.wd_in(desc_data_q),.w_mask_in({256{1'b1}}),
  .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 // reserve stage
 reg[7:0]n_res,n_go;reg st_v;reg[118:0]st;
 wire[6:0]st_rows=st[71:65];
 wire[12:0]st_total=(((st_rows*136)+127)>>7)<<2;
 assign rd_go=running&&n_res!=0&&!st_v&&!rd_q;
 assign reserve_v=st_v&&reserve_ready;
 assign reserve_base=st[31:0];assign reserve_row_base=st[46:32];assign reserve_total=st_total[11:0];
 assign reserve_bank=st[47+:LB];assign reserve_epoch=st[64:49];assign reserve_rows=st_rows;assign reserve_tag_base=st[81:72];
 // start / go queues: {loops16,limit11,base10,epoch16,landing LB}
 localparam integer QW=16+11+10+16+LB;
 reg[QW-1:0]sq[0:QD-1],gq[0:QD-1];reg[2:0]sq_n,gq_n;reg[1:0]sq_r,sq_w,gq_r,gq_w;
 wire[QW-1:0]sh=sq[sq_r],gh=gq[gq_r];
 wire[LB-1:0]sh_land=sh[LB-1:0];wire[LB-1:0]gh_land=gh[LB-1:0];
`ifdef OT_ISSUER_MUT_NORESIDENT
 assign start_v=sq_n!=0&&gq_n<QD&&!cache_owned[sh_land[0]];   // mutant: copy before the HBM data is resident
`else
 assign start_v=sq_n!=0&&gq_n<QD&&block_ready[sh_land]&&!cache_owned[sh_land[0]];
`endif
 assign start_bank=sh_land;assign start_epoch=sh[LB+:16];
 reg go_busy;
 assign program_start_v=gq_n!=0&&!go_busy&&cache_ready[gh_land[0]];
 assign program_start_base=gh[LB+16+:10];assign program_start_limit=gh[LB+26+:11];assign program_start_loops=gh[LB+37+:16];
 wire push_s=reserve_v,pop_s=start_v,push_g=start_v,pop_g=program_start_v;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   running<=0;run_done<=0;fault<=0;rd_q<=0;rp<=0;rp_q<=0;n_res<=0;n_go<=0;st_v<=0;st<=0;
   sq_n<=0;gq_n<=0;sq_r<=0;sq_w<=0;gq_r<=0;gq_w<=0;go_busy<=0;
  end else begin
   run_done<=0;
   if(run_v)begin
    if(running||run_count==0)fault<=1;
    else begin running<=1;rp<=run_base;n_res<=run_count;n_go<=run_count;end
   end
   rd_q<=rd_go;rp_q<=rp;
   if(rd_go)rp<=rp+7'd1;
   if(rd_q)begin
    st<=rd[118:0];st_v<=1;
    if(rd[255:240]!=16'h5d15||rd[239:233]!=rp_q||rd[232:119]!=0)fault<=1;
   end
   if(reserve_v)begin st_v<=0;n_res<=n_res-8'd1;end
   if(push_s)begin sq[sq_w]<={st[118:103],st[102:92],st[91:82],st[64:49],st[47+:LB]};sq_w<=sq_w+2'd1;end
   if(pop_s)sq_r<=sq_r+2'd1;
   sq_n<=sq_n+(push_s?3'd1:3'd0)-(pop_s?3'd1:3'd0);
   if(push_g)begin gq[gq_w]<=sh;gq_w<=gq_w+2'd1;end
   if(pop_g)gq_r<=gq_r+2'd1;
   gq_n<=gq_n+(push_g?3'd1:3'd0)-(pop_g?3'd1:3'd0);
   if(push_s&&sq_n==QD&&!pop_s)fault<=1;
   if(pop_g)go_busy<=1;
   if(program_done)begin
    if(!go_busy)fault<=1;
    go_busy<=0;
    if(running&&n_go==1)begin running<=0;run_done<=1;end
    n_go<=n_go-8'd1;
   end
  end
 end
endmodule
`default_nettype wire
