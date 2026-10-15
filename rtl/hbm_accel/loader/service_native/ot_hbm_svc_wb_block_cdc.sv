`default_nettype none
// All variable waits live inside this dual-clock HBM PHY boundary. Stream
// admission occurs once; a started block supplies eight fixed sectors/edge.
module ot_hbm_svc_wb_block_cdc #(parameter [1:0] STACK=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire reserve_v,output wire reserve_ready,input wire reserve_bank,
 input wire [15:0] reserve_epoch,input wire [31:0] reserve_base,input wire [11:0] reserve_total,
 input wire fill_start,fill_start_bank,input wire [15:0] fill_start_epoch,input wire [2311:0] wd,
 output reg fill_done,output reg done_v,done_bank,output reg [15:0] done_epoch,output reg [11:0] done_sectors,
 output wire [1:0] bank_owned,output wire fault,
 output reg [31:0] k_v,input wire [31:0] k_rdy,output reg [959:0] k_addr,
 output wire [127:0] k_len,output wire [543:0] k_tag,output wire [31:0] k_we,
 output reg [8191:0] k_wdata,output wire [1023:0] k_wstrb,input wire [31:0] k_wr_done
);
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 reg [1:0] allocated,started,staged;reg [15:0] epoch[0:1];
 reg [31:0] base[0:1];reg [11:0] total[0:1];
 reg filling,fill_bank,copy_active,copy_bank;reg [11:0] ordinal;
 reg stream_sticky,hbm_sticky;(* async_reg = "true" *) reg hf1,hf2,sf1,sf2;
 reg [8:0] copy_row[0:7];reg [7:0] read_pending;
 wire [7:0] fifo_full,fifo_empty,fifo_we,fifo_re,mem_read;
 wire [287:0] fifo_head[0:7];wire [255:0] mem_data[0:31];
 wire [28:0] meta_data,ack_data;wire meta_full,meta_empty,ack_full,ack_empty;
 wire meta_we,meta_re,ack_we,ack_re;
 reg meta_active,ack_pending;reg [28:0] meta_q;reg [11:0] ack_count;
 reg [31:0] req_valid,outstanding;reg [2:0] req_lane[0:31];
 reg [31:0] pick_v;reg [2:0] pick_lane[0:31];reg [7:0] pop;
 integer pc,l,acks;wire hbm_fault=hbm_sticky||sf2||!hrst;
 assign fault=stream_sticky||hf2;assign bank_owned=allocated;
 wire [32:0] reserve_end={3'b0,reserve_base[29:0]}+reserve_total;
 assign reserve_ready=srst&&!allocated[reserve_bank]&&!fault&&reserve_total!=0&&reserve_total<=2048&&
  reserve_base[31:30]==STACK&&reserve_end<=33'h040000000;
 wire start_copy=srst&&!copy_active&&(|staged)&&!meta_full&&!fault;
 wire choose_bank=!staged[0];
 assign meta_we=start_copy;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_meta(
 .wclk(stream_clk),.wrst_n(srst),.we(meta_we),.wdata({choose_bank,epoch[choose_bank],total[choose_bank]}),.full(meta_full),.rd_freed(),
 .rclk(hbm_clk),.rrst_n(hrst),.re(meta_re),.rdata(meta_data),.empty(meta_empty));
 assign meta_re=!meta_active&&!meta_empty&&!hbm_fault;
 assign ack_we=ack_pending&&!ack_full&&!hbm_fault;
 assign ack_re=srst&&!ack_empty&&!fault;
 ot_hbm_accel_cdc_fifo #(.W(29),.AW(2)) u_ack(
 .wclk(hbm_clk),.wrst_n(hrst),.we(ack_we),.wdata(meta_q),.full(ack_full),.rd_freed(),
 .rclk(stream_clk),.rrst_n(srst),.re(ack_re),.rdata(ack_data),.empty(ack_empty));
 genvar lane,m;
 generate for(lane=0;lane<8;lane=lane+1)begin:g_lane
  wire [8:0] row=copy_row[lane];
  wire [31:0] sector=base[copy_bank]+row*8+lane;
  assign mem_read[lane]=copy_active&&!read_pending[lane]&&row*8+lane<total[copy_bank]&&!fifo_full[lane]&&!fault;
  assign fifo_we[lane]=copy_active&&read_pending[lane]&&!fifo_full[lane]&&!fault;
  ot_hbm_accel_cdc_fifo #(.W(288),.AW(2)) u_fifo(
   .wclk(stream_clk),.wrst_n(srst),.we(fifo_we[lane]),
   .wdata({sector,mem_data[lane*4+{copy_bank,row[7]}]}),.full(fifo_full[lane]),.rd_freed(),
   .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re[lane]),.rdata(fifo_head[lane]),.empty(fifo_empty[lane]));
  for(m=0;m<4;m=m+1)begin:g_macro
   ot_sram_1r1w_128x256_m1_r2c2 u_payload(
    .clk(stream_clk),.r_ce_in(mem_read[lane]&&{copy_bank,row[7]}==m),.r_addr_in(row[6:0]),.rd_out(mem_data[lane*4+m]),
    .w_ce_in(filling&&!fault&&ordinal+lane<total[fill_bank]&&{fill_bank,ordinal[10]}==m&&wd[lane*289+288]),
    .w_addr_in(ordinal[9:3]),.wd_in(wd[lane*289+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
 end endgenerate
 integer s;
 always @(posedge stream_clk or negedge srst)begin
  if(!srst)begin
   allocated<=0;started<=0;staged<=0;filling<=0;fill_bank<=0;ordinal<=0;copy_active<=0;copy_bank<=0;
   stream_sticky<=0;hf1<=0;hf2<=0;read_pending<=0;fill_done<=0;done_v<=0;done_bank<=0;done_epoch<=0;done_sectors<=0;
   for(s=0;s<2;s=s+1)begin epoch[s]<=0;base[s]<=0;total[s]<=0;end
   for(s=0;s<8;s=s+1)copy_row[s]<=0;
  end else begin
   hf1<=hbm_sticky;hf2<=hf1;fill_done<=0;done_v<=0;
   if(reserve_v)begin
    if(!reserve_ready)stream_sticky<=1;
    else begin allocated[reserve_bank]<=1;started[reserve_bank]<=0;staged[reserve_bank]<=0;
     epoch[reserve_bank]<=reserve_epoch;base[reserve_bank]<=reserve_base;total[reserve_bank]<=reserve_total;end
   end
   if(fill_start)begin
    if(filling||!allocated[fill_start_bank]||started[fill_start_bank]||epoch[fill_start_bank]!=fill_start_epoch)stream_sticky<=1;
    else begin filling<=1;fill_bank<=fill_start_bank;ordinal<=0;started[fill_start_bank]<=1;end
   end
   if(filling&&!fault)begin
    for(s=0;s<8;s=s+1)begin
     if(ordinal+s<total[fill_bank])begin
      if(!wd[289*s+288]||wd[289*s+256+:32]!=(base[fill_bank]+ordinal+s))stream_sticky<=1;
     end else if(wd[289*s+288])stream_sticky<=1;
    end
    if(ordinal+8>=total[fill_bank])begin filling<=0;staged[fill_bank]<=1;fill_done<=1;end
    else ordinal<=ordinal+8;
   end else if(!fault&&|{wd[2311],wd[2022],wd[1733],wd[1444],wd[1155],wd[866],wd[577],wd[288]})stream_sticky<=1;
   if(start_copy)begin
    copy_active<=1;copy_bank<=choose_bank;staged[choose_bank]<=0;read_pending<=0;
    for(s=0;s<8;s=s+1)copy_row[s]<=0;
   end
   for(s=0;s<8;s=s+1)begin
    if(mem_read[s])read_pending[s]<=1;
    if(fifo_we[s])begin read_pending[s]<=0;copy_row[s]<=copy_row[s]+1'b1;end
   end
   if(ack_re)begin
    if(!copy_active||ack_data[28]!=copy_bank||ack_data[27:12]!=epoch[copy_bank]||ack_data[11:0]!=total[copy_bank])stream_sticky<=1;
    else begin allocated[copy_bank]<=0;copy_active<=0;done_v<=1;done_bank<=copy_bank;done_epoch<=epoch[copy_bank];done_sectors<=ack_data[11:0];end
   end
  end
 end
 function automatic [4:0] sector_pc(input [29:0] sector);
  begin sector_pc=sector[6:2]^sector[11:7]^sector[16:12];end
 endfunction
 assign fifo_re=pop;
 assign k_we=k_v;assign k_len={32{4'd1}};assign k_tag={32{{meta_q[28],meta_q[27:12]}}};assign k_wstrb={1024{1'b1}};
 always @*begin
  pick_v=0;pop=0;k_v=0;k_addr=0;k_wdata=0;acks=0;
  for(pc=0;pc<32;pc=pc+1)begin
   pick_lane[pc]=0;
   for(l=0;l<8;l=l+1)if(!pick_v[pc]&&!fifo_empty[l]&&sector_pc(fifo_head[l][285:256])==pc)begin pick_v[pc]=1;pick_lane[pc]=l;end
   if(meta_active&&req_valid[pc]&&!hbm_fault)begin
    k_v[pc]=1;k_addr[30*pc+:30]=fifo_head[req_lane[pc]][285:256];k_wdata[256*pc+:256]=fifo_head[req_lane[pc]][255:0];
    if(k_rdy[pc])pop[req_lane[pc]]=1;
   end
   if(k_wr_done[pc]&&(outstanding[pc]||(k_v[pc]&&k_rdy[pc])))acks=acks+1;
  end
 end
 integer h;
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin
   sf1<=0;sf2<=0;hbm_sticky<=0;meta_active<=0;meta_q<=0;ack_pending<=0;ack_count<=0;req_valid<=0;outstanding<=0;
   for(h=0;h<32;h=h+1)req_lane[h]<=0;
  end else begin
   sf1<=stream_sticky;sf2<=sf1;
   if(meta_re)begin meta_active<=1;meta_q<=meta_data;ack_count<=0;ack_pending<=0;end
   if(meta_active&&!hbm_fault)begin
    for(h=0;h<32;h=h+1)begin
     if(!req_valid[h]&&!outstanding[h]&&pick_v[h]&&!ack_pending)begin req_valid[h]<=1;req_lane[h]<=pick_lane[h];end
     if(k_v[h]&&k_rdy[h])begin req_valid[h]<=0;outstanding[h]<=1;end
     if(k_wr_done[h])begin
      if(!(outstanding[h]||(k_v[h]&&k_rdy[h])))hbm_sticky<=1;
      else outstanding[h]<=0;
     end
    end
    if(acks!=0)begin
     ack_count<=ack_count+acks;
     if(ack_count+acks>meta_q[11:0])hbm_sticky<=1;
     if(ack_count+acks==meta_q[11:0])ack_pending<=1;
    end
   end else if(|k_wr_done)hbm_sticky<=1;
   if(ack_we)begin ack_pending<=0;meta_active<=0;end
  end
 end
endmodule
`default_nettype wire
