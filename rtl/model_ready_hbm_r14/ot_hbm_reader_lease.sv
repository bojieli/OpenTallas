`timescale 1ps/1fs
// Addressed publication/reader ledger; actual IRS pulses are inputs from the
// pinned genericIRS, not a model callback.4readers survive actual return/retire.
module ot_hbm_reader_lease #(parameter integer ENABLE=0)(
 input wire clk,rst_n,clear,
 input wire [8:0] writer_count,input wire writer_drained,
 input wire publish_prior,input wire [63:0] producer,input wire [31:0] transport,
 input wire irs_v,input wire irs_fault,input wire [4:0] irs_slot,input wire [31:0] irs_serial,input wire [31:0] irs_event,
 input wire bind_v,input wire [4:0] bind_slot,input wire [31:0] bind_serial,input wire [2:0] bind_kind,
 input wire result_commit_v,input wire [2:0] result_commit_kind,
 input wire [63:0] result_commit_producer,input wire [31:0] result_commit_transport,
 input wire acquire_v,output wire acquire_r,output wire lease_live,
 input wire reader_v,output wire reader_r,input ot_hbm_r14_pkg::identity_t reader_id,
 input wire result_v,output wire result_r,input ot_hbm_r14_pkg::owned_t result,
 input wire retire_v,input ot_hbm_r14_pkg::identity_t retire_id,
 input wire reverse_v,input ot_hbm_r14_pkg::identity_t reverse_id,
 input wire cancel_v,input wire discard_v,input wire [2:0] discard_kind,
 input wire [4:0] discard_slot,input wire [31:0] discard_serial,
 input wire [63:0] discard_producer,input wire [31:0] discard_transport,
 input wire release_v,output wire release_r,output wire [9:0] count,output wire fault);
 import ot_hbm_r14_pkg::*;
 generate if(!ENABLE)begin:off
   assign acquire_r=0;assign lease_live=0;assign reader_r=0;assign result_r=0;assign release_r=0;assign count=0;assign fault=0;
 end else begin:on
   reg prior,leased,cancelling,sticky;reg [63:0] epoch;reg [31:0] transfer;
   reg [5:0] bound,irs_done,discarded,result_committed;reg [4:0] slots[0:5];reg [31:0] serials[0:5];
   reg [3:0] live,seen,retired;identity_t ids[0:3];reg [287:0] bitmap;reg [9:0] n;
   reg free_v,hit_v,retire_hit,reverse_hit;reg [1:0] free_slot,hit,retire_slot,reverse_slot;
   always @*begin
     free_v=0;free_slot=0;hit_v=0;hit=0;retire_hit=0;retire_slot=0;reverse_hit=0;reverse_slot=0;
     for(integer k=3;k>=0;k=k-1)begin
       if(!live[k])begin free_v=1;free_slot=2'(k);end
       if(live[k]&&ids[k]==result.id)begin hit_v=1;hit=2'(k);end
       if(live[k]&&ids[k]==retire_id)begin retire_hit=1;retire_slot=2'(k);end
       if(live[k]&&ids[k]==reverse_id)begin reverse_hit=1;reverse_slot=2'(k);end
     end
   end
   assign acquire_r=prior&&!leased&&writer_count==272&&writer_drained&&irs_done[0]&&irs_done[1];
   assign lease_live=leased;
   assign reader_r=leased&&!cancelling&&free_v&&reader_id.producer==epoch&&reader_id.transport==transfer&&reader_id.caller<288&&!bitmap[reader_id.caller[8:0]];
   assign result_r=leased&&hit_v&&!seen[hit];
   assign release_r=leased&&live==0&&((!cancelling&&n==288&&(&irs_done[5:2]))||(cancelling&&(!bound[2]||irs_done[2])&&(!bound[3]||discarded[3])&&(!bound[4]||discarded[4])&&(!bound[5]||discarded[5])));
   assign count=n;assign fault=sticky;
   integer k;
   always @(posedge clk or negedge rst_n)begin
     if(!rst_n)begin prior<=0;leased<=0;cancelling<=0;sticky<=0;epoch<=0;transfer<=0;bound<=0;irs_done<=0;discarded<=0;result_committed<=0;
       live<=0;seen<=0;retired<=0;bitmap<=0;n<=0;
       for(k=0;k<6;k=k+1)begin slots[k]<=0;serials[k]<=0;end
       for(k=0;k<4;k=k+1)ids[k]<='0;
     end else begin
       if(clear)begin if(leased||live!=0)sticky<=1;else begin prior<=0;bound<=0;irs_done<=0;discarded<=0;result_committed<=0;bitmap<=0;n<=0;cancelling<=0;end end
       if(publish_prior)begin if(writer_count!=272||!writer_drained||!irs_done[0]||!irs_done[1])sticky<=1;
         else begin prior<=1;epoch<=producer;transfer<=transport;bound[1:0]<=0;irs_done[1:0]<=0;end end
       if(bind_v)begin
         if(bind_kind>=6||bound[bind_kind])sticky<=1;
         else begin bound[bind_kind]<=1;slots[bind_kind]<=bind_slot;serials[bind_kind]<=bind_serial;end
       end
       if(irs_v)begin
         for(k=0;k<6;k=k+1)if(bound[k]&&slots[k]==irs_slot&&serials[k]==irs_serial)begin
           if(irs_event!=32'(10+k)||irs_done[k]||
              (k==0&&(writer_count!=272||!writer_drained))||
              (k==1&&!irs_done[0])||(k==2&&n!=288&&!(cancelling&&irs_fault&&live==0))||
              (k>=3&&!result_committed[k])||(k==3&&!irs_done[2])||
              (k==4&&!irs_done[3])||(k==5&&(!irs_done[2]||!irs_done[4])))sticky<=1;else irs_done[k]<=1;
         end
       end
       if(result_commit_v)begin
         if(!leased||result_commit_producer!=epoch||result_commit_transport!=transfer||result_commit_kind<3||result_commit_kind>5||result_committed[result_commit_kind])sticky<=1;
         else result_committed[result_commit_kind]<=1;
       end
       if(acquire_v&&acquire_r)begin leased<=1;epoch<=producer;transfer<=transport;end
       if(reader_v&&reader_r)begin live[free_slot]<=1;seen[free_slot]<=0;retired[free_slot]<=0;ids[free_slot]<=reader_id;end
       if(result_v&&result_r)seen[hit]<=1;
       if(retire_v)begin if(!retire_hit||!seen[retire_slot]||retired[retire_slot])sticky<=1;else retired[retire_slot]<=1;end
       if(reverse_v)begin
         if(!reverse_hit||!retired[reverse_slot])sticky<=1;
         else begin live[reverse_slot]<=0;seen[reverse_slot]<=0;retired[reverse_slot]<=0;
           if(!cancelling)begin if(bitmap[reverse_id.caller[8:0]])sticky<=1;
             else begin bitmap[reverse_id.caller[8:0]]<=1;n<=n+1'b1;end end
         end
       end
       if(cancel_v&&leased)cancelling<=1;
       if(discard_v)begin if(!cancelling||discard_kind>=6||!bound[discard_kind]||slots[discard_kind]!=discard_slot||serials[discard_kind]!=discard_serial||discard_producer!=epoch||discard_transport!=transfer)sticky<=1;else discarded[discard_kind]<=1;end
       if(release_v)begin if(!release_r)sticky<=1;else begin leased<=0;cancelling<=0;end end
     end
   end
 end endgenerate
endmodule
