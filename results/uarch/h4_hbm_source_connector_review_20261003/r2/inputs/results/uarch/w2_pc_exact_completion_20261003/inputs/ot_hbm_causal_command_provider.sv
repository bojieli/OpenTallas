`timescale 1ps/1fs
// Default-off GPU stack provider.32PCs,64request/32return entries each,
// four WRITEresidence slots. Physical interface remains fullAW31 local
// after fullAW34 bounds checks; nativeLEN6/BEAT5,16wire-tag bits.
module ot_hbm_causal_command_provider #(parameter integer ENABLE=0,STACK=0,DIE=0)(
 input wire clk,rst_n,
 input wire req_v,output wire req_r,input ot_hbm_r14_pkg::request_t req,
 output wire cmd_v,input wire cmd_r,output ot_hbm_r14_pkg::command_t cmd,
 input wire [31:0] rsp_v,output wire [31:0] rsp_r,
 input wire [511:0] rsp_tag,input wire [159:0] rsp_beat,input wire [8191:0] rsp_data,
 input wire [31:0] commit_v,output wire [31:0] commit_r,
 input wire [63:0] commit_slot,
 output wire owned_v,input wire owned_r,output wire owned_we,output wire owned_credit,output ot_hbm_r14_pkg::owned_t owned,
 input wire credit_v,input wire credit_we,output wire credit_r,input ot_hbm_r14_pkg::identity_t credit_id,
 input wire [11:0] credit_tag,input wire [4:0] credit_beat,
 output wire fault,output wire [63:0] cycle,output wire [2:0] WRresidents,
 output wire [15:0] live_tags);
 import ot_hbm_r14_pkg::*;
 generate if(!ENABLE)begin:off
   assign req_r=0;assign cmd_v=0;assign cmd='0;assign rsp_r=0;assign commit_ready=0;
   assign owned_v=0;assign owned_we=0;assign owned_credit=0;assign owned='0;assign credit_r=0;
   assign fault=0;assign cycle=0;assign WRresidents=0;assign live_tags=0;
 end else begin:on
   reg [63:0] cyc;reg sticky_fault;
   reg [63:0] accepted_cycle;reg ingress;request_t accepted;reg [11:0] active_tag;reg [5:0] cursor;
   wire [31:0] qready,qvalid,pc_cmd_v,pc_cmd_r,reserve_v,reserve_r,return_v,pc_fault;reg [31:0] return_r;
   queued_t enqueued;command_t commands[0:31];returned_t returns[0:31];
   wire [471:0] reserve_word[0:31];queued_t reserve_queue[0:31];wire [1:0] pc_write_slot[0:31];
   wire [6:0] qcount[0:31];wire [5:0] rcount[0:31];
   wire [7:0] journal_kind[0:31];wire [471:0] journal_word[0:31];
   reg [3:0] wr_live,wr_backed,wr_mapped;queued_t wr_word[0:3];
   reg [4:0] wr_pc[0:3];reg [63:0] wr_column[0:3];reg wr_issued[0:3];
   reg [1:0] free_wr;reg free_wr_v;
   reg [4:0] reserve_pc,command_pc,return_pc;reg reserve_hit,command_hit,return_hit;
   reg [1:0] visible_slot;reg visible_hit;reg map_we,map_we_hold;
   reg [4:0] rr_cmd,rr_rsp;reg [2:0] return_arb;
   wire [11:0] next_tag;wire alloc_ready,alloc_valid;
   wire map_in_ready,map_out_valid;wire owned_t map_owned;
   reg [31:0] commit_ready;reg credit_match;reg grant_valid;owned_t grant_reg;
   reg map_in_valid;reg [4:0] map_pc;reg [11:0] map_tag;reg [4:0] map_beat;reg [255:0] map_data;
   wire legal=(req.id.stack==2'(STACK))&&(req.id.die==1'(DIE))&&req.len!=0&&req.len<=32&&
      ({1'b0,req.id.sector}+35'(req.len)<=CAPACITY_SECTORS);
   assign alloc_valid=req_v&&!ingress&&legal&&!sticky_fault;
   assign req_r=!ingress&&alloc_ready&&legal&&!sticky_fault;
   assign cycle=cyc;assign fault=sticky_fault||(|pc_fault)||owner_fault;
   assign WRresidents={2'b0,wr_live[0]}+{2'b0,wr_live[1]}+{2'b0,wr_live[2]}+{2'b0,wr_live[3]};
   assign enqueued='{we:accepted.we,sector:accepted.id.sector+34'(cursor),tag:{4'b0,active_tag},
      beat:5'(cursor),data:accepted.data,arrived:accepted_cycle,transport:accepted.id.transport,producer:accepted.id.producer};
   for(genvar g=0;g<32;g=g+1)begin:pc
     assign reserve_queue[g]=queued_t'(reserve_word[g]);
     assign qvalid[g]=ingress&&pc_of(enqueued.sector)==5'(g);
     assign pc_cmd_r[g]=cmd_r&&cmd_v&&command_hit&&command_pc==5'(g);
     assign reserve_r[g]=free_wr_v&&reserve_hit&&reserve_pc==5'(g);
     ot_hbm_r14_pc #(.PC(g)) unit(.clk(clk),.rst_n(rst_n),.cyc(cyc),.qv(qvalid[g]),.qr(qready[g]),.qi(enqueued),
       .cmd_v(pc_cmd_v[g]),.cmd_r(pc_cmd_r[g]),.cmd(commands[g]),
       .reserve_v(reserve_v[g]),.reserve_r(reserve_r[g]),.reserve_slot(free_wr),.reserve_word(reserve_word[g]),.write_slot(pc_write_slot[g]),
       .pv(rsp_v[g]),.ptag(rsp_tag[g*16+:16]),.pbeat(rsp_beat[g*5+:5]),.pdata(rsp_data[g*256+:256]),.pr(rsp_r[g]),
       .rv(return_v[g]),.rr(return_r[g]),.ro(returns[g]),.fault(pc_fault[g]),.qcount(qcount[g]),.rcount(rcount[g]),
       .journal_kind(journal_kind[g]),.journal_word(journal_word[g]));
   end
   wire owner_fault;
   ot_hbm_r14_tag_owner owner(.clk(clk),.rst_n(rst_n),.av(alloc_valid),.ar(alloc_ready),.req(req),.allocated_tag(next_tag),
      .iv(map_in_valid),.ir(map_in_ready),.ipc(map_pc),.itag(map_tag),.ibeat(map_beat),.idata(map_data),
      .ov(map_out_valid),.ore(owned_r&&!grant_valid),.owned(map_owned),.fault(owner_fault),.live_tags(live_tags));
   assign owned_v=map_out_valid||grant_valid;assign owned=grant_valid?grant_reg:map_owned;assign owned_we=!grant_valid&&map_we_hold;assign owned_credit=grant_valid;
   assign cmd_v=command_hit&&!sticky_fault&&!(|pc_fault)&&!owner_fault;assign cmd=commands[command_pc];
   assign credit_r=!grant_valid;assign commit_r=commit_ready;
   // One real command bus/stack. Arbitration under load is observable;
   // no32-way simultaneous commands or no-cost routing assumption.
   always @*begin
     free_wr_v=0;free_wr=0;for(integer w=3;w>=0;w=w-1)if(!wr_live[w])begin free_wr_v=1;free_wr=2'(w);end
     reserve_pc=0;reserve_hit=0;for(integer p=31;p>=0;p=p-1)if(reserve_v[p] && !wr_live[reserve_queue[p].tag[1:0]])begin reserve_hit=1;reserve_pc=5'(p);free_wr=reserve_queue[p].tag[1:0];free_wr_v=1;end
     command_pc=0;command_hit=0;
     for(integer k=31;k>=0;k=k-1)begin
       automatic integer p=(integer'(rr_cmd)+k)%32;
       automatic logic raw=0;
       for(integer w=0;w<4;w=w+1)if(wr_live[w]&&!wr_backed[w]&&wr_word[w].sector==commands[p].sector&&commands[p].op==RD)raw=1;
       if(pc_cmd_v[p]&&!raw)begin command_hit=1;command_pc=5'(p);end
     end
     visible_hit=0;visible_slot=0;
     for(integer w=3;w>=0;w=w-1)if(wr_live[w]&&wr_backed[w]&&!wr_mapped[w])begin visible_hit=1;visible_slot=2'(w);end
     return_hit=0;return_pc=0;
     for(integer k=31;k>=0;k=k-1)begin automatic integer p=(integer'(rr_rsp)+k)%32;
       if(return_v[p])begin return_hit=1;return_pc=5'(p);end end
     map_in_valid=0;map_pc=0;map_tag=0;map_beat=0;map_data=0;map_we=0;
     if(return_arb==6)begin
       if(visible_hit)begin map_in_valid=1;map_we=1;map_pc=wr_pc[visible_slot];map_tag=wr_word[visible_slot].tag[11:0];
          map_beat=wr_word[visible_slot].beat;map_data=wr_word[visible_slot].data;end
       else if(return_hit)begin map_in_valid=1;map_pc=return_pc;map_tag=returns[return_pc].tag[11:0];
          map_beat=returns[return_pc].beat;map_data=returns[return_pc].data;end
     end
     for(integer p=0;p<32;p=p+1)return_r[p]=map_in_valid&&map_in_ready&&!map_we&&return_pc==5'(p);
     commit_ready=0;
     for(integer p=0;p<32;p=p+1)for(integer w=0;w<4;w=w+1)
       if(wr_live[w]&&wr_issued[w]&&!wr_backed[w]&&wr_pc[w]==5'(p)&&
          2'(w)==commit_slot[p*2+:2])commit_ready[p]=1;
   end
   integer w;
   always @(posedge clk or negedge rst_n)begin
     if(!rst_n)begin cyc<=0;sticky_fault<=0;ingress<=0;accepted<='0;accepted_cycle<=0;active_tag<=0;cursor<=0;
       wr_live<=0;wr_backed<=0;wr_mapped<=0;rr_cmd<=0;rr_rsp<=0;return_arb<=0;map_we_hold<=0;grant_valid<=0;grant_reg<='0;
       for(w=0;w<4;w=w+1)begin wr_word[w]<='0;wr_pc[w]<=0;wr_column[w]<=0;wr_issued[w]<=0;end
     end else begin
       if(cyc>=64'hffffffffffffd8ef)sticky_fault<=1;else cyc<=cyc+1'b1; //guard10000COREedges before64bit wrap
       if(req_v&&!legal)sticky_fault<=1; // held fault; never allocate/pop/issue
       if(req_v&&req_r)begin accepted<=req;accepted_cycle<=cyc;active_tag<=next_tag;ingress<=1;cursor<=0;end
       if(ingress&&qready[pc_of(enqueued.sector)])begin
         if(cursor+1==accepted.len)ingress<=0;else cursor<=cursor+1'b1;
       end
       if(reserve_hit&&free_wr_v)begin wr_live[free_wr]<=1;wr_word[free_wr]<=queued_t'(reserve_word[reserve_pc]);
         wr_pc[free_wr]<=reserve_pc;wr_backed[free_wr]<=0;wr_mapped[free_wr]<=0;wr_issued[free_wr]<=0;end
       if(cmd_v&&cmd_r)begin rr_cmd<=command_pc+1'b1;
         if(cmd.op==WR)begin
           if(!wr_live[pc_write_slot[command_pc]])sticky_fault<=1;
           else begin wr_column[pc_write_slot[command_pc]]<=cyc;wr_issued[pc_write_slot[command_pc]]<=1;end
         end
       end
       for(integer p=0;p<32;p=p+1)if(commit_v[p]&&commit_r[p])begin
         for(w=0;w<4;w=w+1)if(wr_live[w]&&wr_issued[w]&&wr_pc[w]==5'(p)&&
           2'(w)==commit_slot[p*2+:2])begin
             if(cyc<wr_column[w]+8)sticky_fault<=1;else wr_backed[w]<=1;
           end
       end
       if(return_hit||visible_hit)begin if(return_arb<6)return_arb<=return_arb+1'b1;end
       else return_arb<=0;
       if(map_in_valid&&map_in_ready)begin
         map_we_hold<=map_we;return_arb<=0;
         if(map_we)wr_mapped[visible_slot]<=1;else rr_rsp<=return_pc+1'b1;
       end
       if(grant_valid&&owned_r)grant_valid<=0;
       if(credit_v&&credit_r)begin
         credit_match=0;
         if(!credit_we)begin credit_match=1;grant_valid<=1;grant_reg<='{id:credit_id,data:256'b0,physical_tag:credit_tag,beat:credit_beat};end
         for(w=0;w<4;w=w+1)if(credit_we&&wr_live[w]&&wr_mapped[w]&&wr_word[w].tag[11:0]==credit_tag&&
          wr_word[w].beat==credit_beat&&wr_word[w].sector==credit_id.sector&&
          wr_word[w].producer==credit_id.producer&&wr_word[w].transport==credit_id.transport&&credit_id.stack==2'(STACK))begin
            credit_match=1;grant_valid<=1;grant_reg<='{id:credit_id,data:256'b0,physical_tag:credit_tag,beat:credit_beat};
            wr_live[w]<=0;wr_backed[w]<=0;wr_mapped[w]<=0;wr_issued[w]<=0;
          end
         if(!credit_match)sticky_fault<=1;
       end
     end
   end
 end endgenerate
endmodule
