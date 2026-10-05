`timescale 1ps/1fs
// True addressed hardware bit-store.4owners; registered store->retirement.
// Ownership survives sector retire until actual controller reversecredit grant.
// Whole-opcode IRS is not a sector credit. No timing-derived completion input.
module ot_hbm_sector_completion_store #(parameter integer ENABLE=0)(
 input wire clk,rst_n,clear,input wire reserve_v,output wire reserve_r,
 input ot_hbm_r14_pkg::identity_t reserve_id,
 input wire visible_v,output wire visible_r,input ot_hbm_r14_pkg::owned_t visible,
 input wire cancel_v,input ot_hbm_r14_pkg::identity_t cancel_id,
 output wire retire_v,input wire retire_r,output ot_hbm_r14_pkg::owned_t retire,
 output wire retire_cancelled,
 input wire grant_v,output wire grant_r,input ot_hbm_r14_pkg::owned_t grant,
 output wire [271:0] completed,output wire [8:0] count,output wire drained,output wire fault);
 import ot_hbm_r14_pkg::*;
 generate if(!ENABLE)begin:off
   assign reserve_r=0;assign visible_r=0;assign retire_v=0;assign retire='0;assign retire_cancelled=0;
   assign grant_r=0;assign completed=0;assign count=0;assign drained=1;assign fault=0;
 end else begin:on
   reg [3:0] live,cancelled,stored,terminal;identity_t ids[0:3];
   reg [271:0] bits;reg [8:0] n;reg sticky;
   reg [1:0] free_slot,hit,grant_hit;reg free_v,hit_v,grant_hit_v;
   reg [1:0] phase,slot;owned_t packet;reg held_cancel;
   always @*begin
     free_slot=0;free_v=0;hit=0;hit_v=0;grant_hit=0;grant_hit_v=0;
     for(integer k=3;k>=0;k=k-1)begin
       if(!live[k])begin free_slot=2'(k);free_v=1;end
       if(live[k]&&ids[k]==visible.id)begin hit=2'(k);hit_v=1;end
       if(live[k]&&terminal[k]&&ids[k]==grant.id)begin grant_hit=2'(k);grant_hit_v=1;end
     end
   end
   assign reserve_r=free_v&&reserve_id.caller<272&&!bits[reserve_id.caller[8:0]];
   assign visible_r=phase==0&&hit_v&&!stored[hit];
   assign retire_v=phase==3;assign retire=packet;assign retire_cancelled=held_cancel;
   assign grant_r=grant_hit_v;assign completed=bits;assign count=n;assign drained=live==0&&phase==0;assign fault=sticky;
   integer k;
   always @(posedge clk or negedge rst_n)begin
     if(!rst_n)begin live<=0;cancelled<=0;stored<=0;terminal<=0;bits<=0;n<=0;sticky<=0;phase<=0;packet<='0;held_cancel<=0;slot<=0;
       for(k=0;k<4;k=k+1)ids[k]<='0;
     end else begin
       if(clear)begin if(!drained)sticky<=1;else begin bits<=0;n<=0;end end
       if(reserve_v&&reserve_r)begin live[free_slot]<=1;ids[free_slot]<=reserve_id;cancelled[free_slot]<=0;stored[free_slot]<=0;terminal[free_slot]<=0;end
       if(cancel_v)for(k=0;k<4;k=k+1)if(live[k]&&ids[k]==cancel_id)cancelled[k]<=1;
       if(visible_v&&visible_r)begin packet<=visible;slot<=hit;held_cancel<=cancelled[hit];phase<=1;end
       if(phase==1)begin
         if(!held_cancel)begin
           if(bits[packet.id.caller[8:0]])sticky<=1;
           else begin bits[packet.id.caller[8:0]]<=1;n<=n+1'b1;end
         end
         stored[slot]<=1;phase<=2;
       end
       if(phase==2)begin terminal[slot]<=1;phase<=3;end
       if(retire_v&&retire_r)phase<=0;
       if(grant_v&&grant_r)begin live[grant_hit]<=0;stored[grant_hit]<=0;terminal[grant_hit]<=0;cancelled[grant_hit]<=0;end
       if(visible_v&&!hit_v)sticky<=1;
       if(grant_v&&!grant_hit_v)sticky<=1;
     end
   end
 end endgenerate
endmodule
