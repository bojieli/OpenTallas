`timescale 1ps/1fs
// Model: hbm_pcwb_actual_parent_20261005; cold POR only. One real PC.
// The 72 column seats are prepaid by 64 consumer credits and eight WRITE leases.
module ot_hbm_pcwb_prepaid_column #(parameter integer ENABLE=0, PC=0)(
 input wire service_clk,por_n,context_valid,
 input wire [63:0] operation,
 input wire [31:0] phase,generation,
 input wire wr_v,output wire wr_r,
 input wire [4:0] wr_bank,wr_col,input wire [18:0] wr_row,input wire [255:0] wr_data,
 output wire wq_v,input wire wq_r,
 input wire col_v,col_we,input wire [4:0] col_bank,col_col,
 input wire [18:0] col_row,input wire [255:0] col_data,
 output wire phy_col_v,input wire phy_col_r,output wire phy_we,
 output wire [4:0] phy_bank,phy_col,output wire [18:0] phy_row,
 output wire [255:0] phy_data,output wire [198:0] phy_receipt,
 input wire visible_v,output wire visible_r,input wire [198:0] visible_receipt,
 output wire wr_visible_v,input wire wr_visible_r,output wire [198:0] wr_visible_receipt,
 output wire [6:0] queued,output wire [3:0] inflight,visible_not_returned,
 output wire all_writes_drained,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE) begin:off
  assign wr_r=0;assign wq_v=0;assign phy_col_v=0;assign phy_we=0;
  assign phy_bank=0;assign phy_col=0;assign phy_row=0;assign phy_data=0;assign phy_receipt=0;
  assign visible_r=0;assign wr_visible_v=0;assign wr_visible_receipt=0;
  assign queued=0;assign inflight=0;assign visible_not_returned=0;assign all_writes_drained=0;assign fault=0;
 end else begin:on
  localparam [2:0] FREE=0,QUEUED=1,CONTROLLER_ISSUED=2,PHY_ACCEPTED=3,VISIBLE_NOT_RETURNED=4;
  reg [288:0] fifo[0:71];reg [6:0] wp,rp,count;
  reg [457:0] pending[0:7],pending_n[0:7];reg [575:0] seal[0:7];
  reg [2:0] allocate_q,issue_q;reg [3:0] live_q;
  reg sticky;
  wire [288:0] head=fifo[rp];
  wire [2:0] head_slot=head[287:285];
  wire [198:0] head_receipt=pending[head_slot][198:0];
  reg code_bad,event_bad;reg [3:0] live_count,flight_count,visible_count;
  integer return_slot;reg have_return;
  wire [2:0] visible_slot=visible_receipt[36:34];
  wire visible_match=pending[visible_slot][457:455]==PHY_ACCEPTED &&
    pending[visible_slot][198:0]==visible_receipt;
  always @* begin
   code_bad=0;live_count=0;flight_count=0;visible_count=0;have_return=0;return_slot=0;
   for(integer k=0;k<8;k=k+1) begin
    if(pending[k][457:455]!=FREE)live_count=live_count+1;
    if(pending[k][457:455]==PHY_ACCEPTED)flight_count=flight_count+1;
    if(pending[k][457:455]==VISIBLE_NOT_RETURNED) begin
     visible_count=visible_count+1;if(!have_return)begin have_return=1;return_slot=k;end
    end
    for(integer w=0;w<8;w=w+1) begin
     reg [511:0] padded;reg [65:0] decoded;
     padded={54'b0,pending[k]};decoded=decode64(seal[k][w*72+:72]);
     if(decoded[65]||decoded[63:0]!=padded[w*64+:64])code_bad=1;
    end
   end
  end
  wire safe=context_valid&&!sticky&&!code_bad;
  assign wq_v=wr_v&&safe&&pending[allocate_q][457:455]==FREE;
  assign wr_r=safe&&pending[allocate_q][457:455]==FREE&&wq_r;
  wire ingress=wr_v&&wr_r;
  assign phy_col_v=count!=0&&safe;
  wire pop=phy_col_v&&phy_col_r;
  assign phy_we=head[288];assign phy_bank=head[284:280];assign phy_row=head[279:261];
  assign phy_col=head[260:256];assign phy_data=head[255:0];
  assign phy_receipt=phy_we?head_receipt:199'b0;
  assign visible_r=safe&&visible_match;
  wire vis_accept=visible_v&&visible_r;
  assign wr_visible_v=safe&&(have_return||vis_accept);
  assign wr_visible_receipt=have_return?pending[return_slot][198:0]:visible_receipt;
  wire receipt_accept=wr_visible_v&&wr_visible_r;
  wire [2:0] retire_slot=have_return?3'(return_slot):visible_slot;
  assign queued=count;assign inflight=flight_count;assign visible_not_returned=visible_count;
  assign all_writes_drained=(live_count==0);assign fault=sticky||code_bad;
  wire [33:0] sector={wr_row,wr_bank[4:2],wr_col,wr_bank[1:0],5'(PC)};
  wire [198:0] ingress_receipt={operation,phase,sector,generation,allocate_q,5'(PC),wr_bank,wr_row,wr_col};
  always @* begin
   event_bad=0;
   for(integer k=0;k<8;k=k+1)pending_n[k]=pending[k];
   if(visible_v&&(!context_valid||!visible_match))event_bad=1;
   if(vis_accept)pending_n[visible_slot][457:455]=VISIBLE_NOT_RETURNED;
   if(receipt_accept)pending_n[retire_slot][457:455]=FREE;
   if(ingress)pending_n[allocate_q]={QUEUED,wr_data,ingress_receipt};
   if(col_v) begin
    if(!context_valid || (count==72&&!pop))event_bad=1;
    if(col_we) begin
     if(pending[issue_q][457:455]!=QUEUED ||
       pending[issue_q][198:0]!={operation,phase,{col_row,col_bank[4:2],col_col,col_bank[1:0],5'(PC)},generation,issue_q,5'(PC),col_bank,col_row,col_col} ||
       pending[issue_q][454:199]!=col_data)event_bad=1;
     else pending_n[issue_q][457:455]=CONTROLLER_ISSUED;
    end
   end
   if(pop&&phy_we) begin
    if(pending[head_slot][457:455]!=CONTROLLER_ISSUED ||
      head_receipt[28:24]!=phy_bank || head_receipt[23:5]!=phy_row || head_receipt[4:0]!=phy_col ||
      pending[head_slot][454:199]!=phy_data)event_bad=1;
    else pending_n[head_slot][457:455]=PHY_ACCEPTED;
   end
  end
  always @(posedge service_clk or negedge por_n)
   if(!por_n) begin
    wp<=0;rp<=0;count<=0;allocate_q<=0;issue_q<=0;live_q<=0;sticky<=0;
    for(integer k=0;k<8;k=k+1)begin pending[k]<=0;seal[k]<=0;end
   end else begin
    if(code_bad||event_bad)sticky<=1;
    if(safe&&!event_bad) begin
     for(integer k=0;k<8;k=k+1) begin
      reg [511:0] padded;padded={54'b0,pending_n[k]};pending[k]<=pending_n[k];
      for(integer w=0;w<8;w=w+1)seal[k][w*72+:72]<=encode64(padded[w*64+:64]);
     end
     if(ingress)allocate_q<=allocate_q+3'd1;
     if(col_v&&col_we)issue_q<=issue_q+3'd1;
     case({ingress,receipt_accept})2'b10:live_q<=live_q+1;2'b01:live_q<=live_q-1;default:;endcase
     if(col_v)begin fifo[wp]<={col_we,(col_we?issue_q:3'b0),col_bank,col_row,col_col,col_data};wp<=wp==71?0:wp+1;end
     if(pop)rp<=rp==71?0:rp+1;
     case({col_v,pop})2'b10:count<=count+1;2'b01:count<=count-1;default:;endcase
    end
   end
 end endgenerate
endmodule
