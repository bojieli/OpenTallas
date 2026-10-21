`timescale 1ns/1ps
// Exact recurring Ckind12 authority, independent from received KVN data.
// Four small owner banks; no queues, credits, stalls or calendar adjustment.
module qkd_kvn_ctx_ovl_rope #(
 parameter integer MUT_USER=0, parameter integer MUT_STALE=0, parameter integer MUT_BOOT=0
)(
 input wire ck,rst_n,
 input wire [551:0] head_record,
 input wire [3:0] ovl_users,calrx,
 input wire adm_done,reseed,
 output reg [58:0] compiled_identity,
 output reg [1:0] compiled_generation,
 output reg fault
);
 (* keep=1,dont_touch=1 *)reg reset_first,reset_last;
 (* keep=1,dont_touch=1 *)reg reset_capture,reset_bank;
 always @(posedge ck)begin reset_first<=rst_n;reset_last<=reset_first;reset_capture<=reset_last;reset_bank<=reset_capture;end
 wire [1:0] rx_user=ovl_users[3:2], cal_user_rx=calrx[3:2];
 wire cal_start_rx=calrx[0],cal_seg_rx=calrx[1];
 reg [551:0] hq;
 reg [1:0] uq,cuser_q;
 reg cstart_q,cseg_q,adm_q,hq_valid;
 always @(posedge ck)begin
   hq<=head_record;uq<=rx_user;cuser_q<=cal_user_rx;
   cseg_q<=cal_seg_rx;
 end
 always @(posedge ck or negedge reset_capture)
   if(!reset_capture)begin cstart_q<=0;adm_q<=0;hq_valid<=0;end
   else begin cstart_q<=cal_start_rx;adm_q<=adm_done;hq_valid<=head_record[3];end
 (* keep=1,dont_touch=1 *)reg reseed_bank;
 always @(posedge ck or negedge reset_last)
   if(!reset_last)reseed_bank<=0;else reseed_bank<=reseed;
 wire [60:0] check_owner,chosen;
 wire write_accept=take&&legal&&!(have[uq]&&
   (owner[58:45]<check_owner[58:45]||
   (owner[58:45]==check_owner[58:45]&&owner!=check_owner)))&&
   (MUT_STALE==0||!have[uq]);
 genvar sh;
 generate for(sh=0;sh<4;sh=sh+1)begin:g_owner_shard
   localparam integer LO=sh*16,W=(61-LO<16)?61-LO:16;
   qkd_kvn_owner_shard #(.W(W)) bank(.ck(ck),.rst_n(reset_bank),
    .reseed(reseed_bank),.rx_user(rx_user),.cal_user(cal_user_rx),
    .write_accept(write_accept),.owner(owner[LO+:W]),
    .check_owner(check_owner[LO+:W]),.chosen(chosen[LO+:W]));
 end endgenerate
 reg [3:0] have;
 reg [5:0] stage[0:3];
 wire [60:0] owner=hq[64:4];
 wire [35:0] header=hq[551:516];
 wire take=reset_bank&&!reseed&&!reseed_bank&&hq_valid&&(adm_q||MUT_BOOT!=0)&&header[30:27]==4'd12;
 wire legal=header[35:31]==0&&header[26:21]==63&&header[4:0]==0&&
   header[20:5]==owner[58:43]&&owner[42:37]==0&&owner[5:0]==0&&owner[36:19]<151936&&
   (MUT_USER!=0||owner[44:43]==uq);
 integer i;
 // Owner bytes stay unreset; only validity and stage are control state.
 always @(posedge ck or negedge reset_last)
   if(!reset_last)begin have<=0;fault<=0;for(i=0;i<4;i=i+1)stage[i]<=0;end
   else if(reseed)begin have<=0;for(i=0;i<4;i=i+1)stage[i]<=0;end
   else begin
     if(take)begin
       if(!legal)fault<=1;
       else if(have[uq] && (owner[58:45]<check_owner[58:45] ||
         (owner[58:45]==check_owner[58:45] && owner!=check_owner)))fault<=1;
       else if(MUT_STALE==0||!have[uq])begin have[uq]<=1;end
     end
     if(cstart_q&&adm_q&&!reseed_bank)begin
       if(cseg_q)stage[cuser_q]<=1;
       else if(stage[cuser_q]==0||stage[cuser_q]>=36)fault<=1;
       else stage[cuser_q]<=stage[cuser_q]+1;
     end
   end
 // The selected RX user remains stable across the compiled KVN segment. Its
 // descriptor must arrive before the first KVN record; missing owner/stage is
 // deliberately invalid and is checked by the unchanged D2D KVN receiver.
 always @(posedge ck)begin
   compiled_identity<={chosen[58:43],have[cuser_q]&&!fault?stage[cuser_q]:6'd0,chosen[36:6],6'd0};
   compiled_generation<=chosen[60:59];
 end
endmodule

// This is a real registered storage partition, retained through synthesis.
// Each instance owns <=16 payload bits per user and local selector/control
// registers. Native census traverses its hierarchy and counts actual sinks.
(* keep_hierarchy=1 *)module qkd_kvn_owner_shard #(parameter integer W=16)(
 input wire ck,rst_n,reseed, input wire[1:0]rx_user,cal_user,
 input wire write_accept, input wire[W-1:0]owner,
 output wire[W-1:0]check_owner,chosen
);
 reg[W-1:0]owners[0:3],pending;
 reg[1:0]rx_q,cal_q;
 reg[3:0]load_owner;
 always @(posedge ck)begin rx_q<=rx_user;cal_q<=cal_user;pending<=owner;end
 integer b;
 always @(posedge ck or negedge rst_n)
   if(!rst_n)load_owner<=0;
   else if(reseed)load_owner<=0;
   else for(b=0;b<4;b=b+1)load_owner[b]<=write_accept&&rx_q==b;
 always @(posedge ck)for(b=0;b<4;b=b+1)if(load_owner[b])owners[b]<=pending;
 assign check_owner=load_owner[rx_q]?pending:owners[rx_q];
 assign chosen=owners[cal_q];
endmodule
