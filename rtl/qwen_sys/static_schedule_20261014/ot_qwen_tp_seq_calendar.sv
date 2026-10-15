`timescale 1ns/1ps
// Actual three-segment production sequencer. Core/VM/COLL observations can fault
// but never choose an issue edge or prolong a segment/stage. PW961..972 carries
// {start32,end32}, {tx_first32,rx_first32}, {zero32,rx_stride16,tx_stride16},
// and the EXACT real DW64 descriptor for each segment. PW973={SGT1,stop32},
// PW974={SGTS,zero23,requires_cbuf1,stage6,count2}, PW975=0. Dense footer1023 seals.
module ot_qwen_tp_seq_calendar #(
 parameter integer VRL=19,N=8,NW=18,PAW=12,VWA=20,DAW=6,FW=512,RB=3
)(
 input wire clk,rst_n,rst_nw,start,input wire[NW-1:0]token,pos,input wire[5:0]stage,
 input wire pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,
 output reg done,output reg[NW-1:0]next_token,output reg[31:0]next_val,
 output wire fault,output wire image_ready,output wire requires_cbuf,output wire coll_busy,
 output wire core_start,output wire[NW-1:0]core_token,core_pos,
 input wire core_done,input wire[NW-1:0]core_next_token,input wire[31:0]core_next_val,input wire core_fault,
 output wire[PAW-1:0]prog_base,output wire desc_re,output wire[DAW-1:0]desc_addr,input wire[63:0]desc_q,
 output wire vm_re,output wire[VWA-1:0]vm_raddr,input wire[FW-1:0]vm_rq,input wire vm_rvalid,
 output reg vm_we,output reg[VWA-1:0]vm_waddr,output reg[FW-1:0]vm_wdata,
 output wire c_valid,input wire c_ready,output wire[FW-1:0]c_data,output wire c_last,c_mode,output wire[31:0]c_tag,
 input wire r_valid,input wire[FW-1:0]r_data,input wire r_last,input wire[RB-1:0]r_rank,input wire r_err
);
 reg[63:0]cfg[0:11];reg[11:0]loaded;reg[31:0]stop_q;reg[1:0]count_q;reg[5:0]stage_q;
 reg header_seen,meta_seen,pad_seen,sealed,cfg_fault;reg cbuf_q;
 assign requires_cbuf=cbuf_q;
 integer i;reg bad;
 wire begin_cfg=pw_v&&pw_addr==0;
 wire row_w=pw_v&&pw_addr>=961&&pw_addr<=972;
 wire footer=pw_v&&pw_addr==1023;
 reg active;reg[31:0]cycle;
 always @*begin
  bad=!header_seen||!meta_seen||!pad_seen||count_q==0||count_q>3;
  for(integer k=0;k<3;k=k+1)begin
   if(k<count_q)begin
    if(loaded[4*k+:4]!==4'b1111)bad=1;
    if(cfg[4*k][31:0]<3||cfg[4*k][63:32]<=cfg[4*k][31:0]||cfg[4*k][63:32]>=stop_q)bad=1;
    if(cfg[4*k+2][63:32]!=0)bad=1;
    if(k!=0&&cfg[4*k][31:0]<=cfg[4*k-4][63:32])bad=1;
    if(k==count_q-1&&cfg[4*k+3][1:0]==1)bad=1;
    if(cfg[4*k+3][1:0]==0&&(cfg[4*k+1]!=0||cfg[4*k+2]!=0))bad=1;
    if(cfg[4*k+3][1:0]==1&&cfg[4*k+1][31:0]<=VRL+1)bad=1;
    if(cfg[4*k+3][1:0]>2||(k!=count_q-1&&cfg[4*k+3][1:0]!=1))bad=1;
    if(cfg[4*k+3][1:0]!=0&&(cfg[4*k+2][15:0]==0||cfg[4*k+2][31:16]==0||cfg[4*k+1][31:0]<=cfg[4*k][63:32]||cfg[4*k+1][63:32]<=cfg[4*k][63:32]))bad=1;
   end else if(cfg[4*k]!==0||cfg[4*k+1]!==0||cfg[4*k+2]!==0||cfg[4*k+3]!==0)bad=1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;stop_q<=0;count_q<=0;stage_q<=0;cbuf_q<=0;header_seen<=0;meta_seen<=0;pad_seen<=0;sealed<=0;cfg_fault<=0;end
  else if(begin_cfg)begin
   if(active)cfg_fault<=1;
   else begin loaded<=0;header_seen<=0;meta_seen<=0;pad_seen<=0;sealed<=0;count_q<=0;stop_q<=0;cbuf_q<=0;end
  end else begin
   if(row_w)begin cfg[pw_addr-961]<=pw_data;loaded[pw_addr-961]<=1;if(active||sealed)cfg_fault<=1;end
   if(pw_v&&pw_addr==973)begin stop_q<=pw_data[31:0];header_seen<=1;if(pw_data[63:32]!=32'h53475431||active||sealed)cfg_fault<=1;end
   if(pw_v&&pw_addr==974)begin count_q<=pw_data[1:0];stage_q<=pw_data[7:2];cbuf_q<=pw_data[8];meta_seen<=1;if(pw_data[63:32]!=32'h53475453||pw_data[31:9]!=0||active||sealed)cfg_fault<=1;end
   if(pw_v&&pw_addr==975)begin pad_seen<=1;if(pw_data!=0||active||sealed)cfg_fault<=1;end
   if(footer)begin sealed<=1;if(bad||pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[11:6]!=stage_q||pw_data[1:0]!=2||active||sealed)cfg_fault<=1;end
  end
 end
 reg runtime_fault;reg[NW-1:0]tok_q,pos_q,core_result_token;reg[31:0]core_result_val;reg[31:0]best_v;reg[NW-1:0]best_i;
 reg[8:0]tx_index[0:2],rx_index[0:2],rd_index[0:2];
 reg[31:0]next_tx[0:2],next_rx[0:2],next_read[0:2];
 reg[VRL-1:0]rd_pipe;reg core_done_q;
 reg[FW-1:0]queue[0:3];reg[1:0]q_w,q_r;reg[2:0]q_count;
 reg[1:0]seg;reg start_slot,end_slot,tx_slot,rx_slot,read_slot,fetch_slot,check_slot;
 reg[63:0]descriptor;reg[8:0]words;reg[31:0]tx_first,rx_first;reg[15:0]tx_stride,rx_stride;
 reg[8:0]ti,ri,di;reg[DAW-1:0]fetch_index;
 wire observed_core_done=core_done&&!core_done_q;
 wire expected_read=rd_pipe[VRL-1];
 always @*begin
  seg=0;descriptor=0;words=0;tx_first=0;rx_first=0;tx_stride=0;rx_stride=0;ti=0;ri=0;di=0;
  start_slot=0;end_slot=0;tx_slot=0;rx_slot=0;read_slot=0;fetch_slot=0;check_slot=0;fetch_index=0;
  for(integer k=0;k<3;k=k+1)if(active&&k<count_q)begin
   if(cycle>=cfg[4*k][31:0]-3)begin
    seg=2'(k);descriptor=cfg[4*k+3];
    words=cfg[4*k+3][1:0]==1?(cfg[4*k+3][17:10]==0?9'd256:{1'b0,cfg[4*k+3][17:10]}):9'd1;
    tx_first=cfg[4*k+1][31:0];rx_first=cfg[4*k+1][63:32];tx_stride=cfg[4*k+2][15:0];rx_stride=cfg[4*k+2][31:16];
    ti=tx_index[k];ri=rx_index[k];di=rd_index[k];
   end
   if(cycle==cfg[4*k][31:0])start_slot=1;
   if(cycle==cfg[4*k][63:32])end_slot=1;
   if(cycle==cfg[4*k][31:0]-3)begin fetch_slot=1;fetch_index=DAW'(k);end
   if(cycle==cfg[4*k][31:0]-1)check_slot=1;
  end
  if(active&&descriptor[1:0]!=0)begin
   tx_slot=ti<words&&cycle==next_tx[seg];
   rx_slot=ri<(descriptor[1:0]==1?words:N)&&cycle==next_rx[seg];
   read_slot=descriptor[1:0]==1&&di<words&&cycle==next_read[seg];
  end
 end
 assign core_start=start_slot;
 assign core_token=tok_q;assign core_pos=pos_q;
 assign prog_base=descriptor[32+:PAW];assign desc_re=fetch_slot;assign desc_addr=fetch_index;
 assign vm_re=read_slot;
 assign vm_raddr=VWA'({descriptor[31:20],descriptor[9:2]}+di);
 assign c_valid=tx_slot;assign c_last=ti==words-1;assign c_mode=descriptor[1:0]==2;
 wire[NW-1:0]row0={descriptor[19:18],descriptor[63:48]};
 assign c_data=c_mode?{{(FW-32-NW){1'b0}},core_result_token+row0,core_result_val}:queue[q_r];
 assign c_tag={tok_q,pos_q[7:0],6'(seg)};
 assign image_ready=sealed&&!cfg_fault;assign fault=cfg_fault|runtime_fault;
 assign coll_busy=active&&descriptor[1:0]!=0&&cycle>cfg[4*seg][63:32];
 function automatic[31:0]okey(input[31:0]v);okey=v[31]?~v:{1'b1,v[30:0]};endfunction
 wire[NW-1:0]g_idx=r_data[32+:NW];wire[31:0]g_val=r_data[31:0];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;cycle<=0;done<=0;runtime_fault<=0;tok_q<=0;pos_q<=0;core_done_q<=0;rd_pipe<=0;q_w<=0;q_r<=0;q_count<=0;next_token<=0;next_val<=0;best_v<=0;best_i<=0;core_result_token<=0;core_result_val<=0;vm_we<=0;vm_waddr<=0;
   for(i=0;i<3;i=i+1)begin tx_index[i]<=0;rx_index[i]<=0;rd_index[i]<=0;next_tx[i]<=0;next_rx[i]<=0;next_read[i]<=0;end
  end else begin
   done<=0;vm_we<=0;core_done_q<=core_done;rd_pipe<=(rd_pipe<<1)|read_slot;
   if(start)begin
    if(active||!image_ready||stage!=stage_q)runtime_fault<=1;
    active<=1;cycle<=0;tok_q<=token;pos_q<=pos;q_w<=0;q_r<=0;q_count<=0;best_v<=0;best_i<=0;
    for(i=0;i<3;i=i+1)begin tx_index[i]<=0;rx_index[i]<=0;rd_index[i]<=0;next_tx[i]<=cfg[4*i+1][31:0];next_rx[i]<=cfg[4*i+1][63:32];next_read[i]<=cfg[4*i+1][31:0]-VRL-1;end
   end else if(active)begin
    cycle<=cycle+1;
    if(observed_core_done!==end_slot||core_fault||vm_rvalid!==expected_read||r_valid!==rx_slot)runtime_fault<=1;
    if(check_slot&&desc_q!==descriptor)runtime_fault<=1;
    if(read_slot)begin rd_index[seg]<=rd_index[seg]+1'b1;next_read[seg]<=next_read[seg]+tx_stride;end
    if(expected_read)begin queue[q_w]<=vm_rq;q_w<=q_w+1'b1;end
    if(tx_slot)begin next_tx[seg]<=next_tx[seg]+tx_stride;tx_index[seg]<=tx_index[seg]+1'b1;if(!c_mode)begin q_r<=q_r+1'b1;if(q_count==0)runtime_fault<=1;end end
    q_count<=q_count+expected_read-(tx_slot&&!c_mode);
    if(q_count>4)runtime_fault<=1;
    if(end_slot)begin core_result_token<=core_next_token;core_result_val<=core_next_val;end
    if(end_slot&&descriptor[1:0]==0)begin next_token<=core_next_token+row0;next_val<=core_next_val;end
    if(rx_slot)begin
     next_rx[seg]<=next_rx[seg]+rx_stride;rx_index[seg]<=rx_index[seg]+1'b1;
     if(!r_valid||r_err||r_last!==(ri==(descriptor[1:0]==1?words:N)-1))runtime_fault<=1;
     if(descriptor[1:0]==1)begin vm_we<=1;vm_waddr<=VWA'({descriptor[31:20],descriptor[9:2]}+ri);end
     else begin
      if(r_rank!=ri)runtime_fault<=1;
      if(ri==0||okey(g_val)>okey(best_v))begin best_v<=g_val;best_i<=g_idx;end
      if(ri==N-1)begin
       if(okey(g_val)>okey(best_v))begin next_val<=g_val;next_token<=g_idx;end
       else begin next_val<=best_v;next_token<=best_i;end
      end
     end
    end
    if(cycle==stop_q)begin active<=0;done<=1;end
   end
  end
 end
 always @(posedge clk or negedge rst_nw)
 if(!rst_nw)vm_wdata<=0;else if(rx_slot&&descriptor[1:0]==1)vm_wdata<=r_data;
endmodule
