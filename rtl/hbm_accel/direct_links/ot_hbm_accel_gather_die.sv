`timescale 1ns/1ps
// HA2 finite snapshot endpoint. Each global port connects equal lane numbers
// across six groups; each local port connects all other lanes in this group.
// One word/rank/transaction; no hidden queues or early response. HA3 consumes
// rank-major ready/valid output and MUST retain tag through its last consumer.
// Physical PHY/CDC/credit service remains an external, explicitly priced boundary.
module ot_hbm_accel_gather_die #(
 parameter integer ENABLE=0, RANK=0, FW=512, TAGW=32,
 parameter integer PW=FW+TAGW+7
)(
 input wire clk, rst_n,
 input wire in_valid, output wire in_ready,
 input wire [FW-1:0] in_data, input wire [TAGW-1:0] in_tag,
 output reg [19:0] tx_valid, input wire [19:0] tx_ready,
 output reg [20*PW-1:0] tx_record,
 input wire [19:0] rx_valid, output wire [19:0] rx_ready,
 input wire [20*PW-1:0] rx_record,
 output wire out_valid, input wire out_ready,
 output wire [FW-1:0] out_data, output wire [6:0] out_rank,
 output wire [TAGW-1:0] out_tag, output wire out_last,
 output reg fault
);
 generate if (ENABLE) begin: on
 localparam integer GROUP=RANK/16, LANE=RANK%16;
 reg active;
 reg [TAGW-1:0] tag;
 reg [FW-1:0] own, gathered[0:95];
 reg [95:0] seen;
 reg [19:0] pending;
 reg [4:0] relay_valid;
 reg [PW-1:0] relay[0:4];
 reg [14:0] relay_pending[0:4];
 reg [6:0] cursor;
 integer p,g,r,src,peer_group,peer_lane;
 integer selected[0:19];
 reg [2:0] relay_cursor[0:14];
 reg drained;
 reg [PW-1:0] rec;
 reg bad;
 wire complete=&seen;
 always @* begin
   drained=(pending==0);
   for(integer k=0;k<5;k=k+1) drained=drained && (relay_pending[k]==0);
 end
 assign in_ready=!active && !fault;
 assign rx_ready={20{active && !fault && !complete}};
 assign out_valid=active && complete && drained && !fault;
 assign out_data=gathered[cursor];
 assign out_rank=cursor;
 assign out_tag=tag;
 assign out_last=cursor==95;
 always @* begin
   tx_valid=0; tx_record=0;
   for(p=0;p<20;p=p+1) begin
     selected[p]=-1;
     if(p<15 && relay_cursor[p]<5)
       if(relay_valid[relay_cursor[p]] && relay_pending[relay_cursor[p]][p]) selected[p]=int'(relay_cursor[p]);
     if(active && !fault) begin
       if(pending[p]) begin
         tx_valid[p]=1; tx_record[p*PW+:PW]={tag,7'(RANK),own};
       end else if(selected[p]>=0) begin
         tx_valid[p]=1; tx_record[p*PW+:PW]=relay[selected[p]];
       end
     end
   end
 end
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin
     active<=0; tag<=0; own<=0; seen<=0; pending<=0;
     relay_valid<=0; cursor<=0; fault<=0;
     for(g=0;g<5;g=g+1) relay_pending[g]<=0;
     for(r=0;r<15;r=r+1) relay_cursor[r]<=0;
   end else begin
     if(in_valid && in_ready) begin
       active<=1; tag<=in_tag; own<=in_data; seen<=0;
       seen[RANK]<=1; gathered[RANK]<=in_data; pending<='1; cursor<=0;
       relay_valid<=0;
       for(g=0;g<5;g=g+1) relay_pending[g]<=0;
     for(r=0;r<15;r=r+1) relay_cursor[r]<=0;
     end
     for(p=0;p<20;p=p+1) if(tx_valid[p] && tx_ready[p]) begin
       if(pending[p]) pending[p]<=0;
       else begin
         if(selected[p]>=0) begin relay_pending[selected[p]][p]<=0; relay_cursor[p]<=relay_cursor[p]+1'b1; end
       end
     end
     for(p=0;p<20;p=p+1) if(rx_valid[p] && rx_ready[p]) begin
       rec=rx_record[p*PW+:PW]; src=int'(rec[FW+:7]);
       bad=rec[FW+7+:TAGW]!=tag || src>=96;
       if(src<96) bad=bad || seen[src];
       if(p<15) begin
         peer_lane=p+(p>=LANE);
         bad=bad || src%16!=peer_lane;
       end else begin
         peer_group=(p-15)+((p-15)>=GROUP);
         bad=bad || src!=peer_group*16+LANE || relay_valid[p-15];
       end
       if(bad) fault<=1;
       else begin
         gathered[src]<=rec[FW-1:0]; seen[src]<=1;
         if(p>=15) begin
           relay_valid[p-15]<=1; relay[p-15]<=rec; relay_pending[p-15]<='1;
         end
       end
     end
     if(out_valid && out_ready) begin
       if(cursor==95) begin active<=0; cursor<=0; end
       else cursor<=cursor+1'b1;
     end
   end
 end
 end else begin: off
 assign in_ready=0; assign rx_ready=0; assign out_valid=0;
 assign out_data=0; assign out_rank=0; assign out_tag=0; assign out_last=0;
 always @* begin tx_valid=0; tx_record=0; fault=0; end
 end endgenerate
endmodule
