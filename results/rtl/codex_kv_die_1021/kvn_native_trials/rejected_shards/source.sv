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
 (* keep=1,dont_touch=1 *)reg reset_capture;
 always @(posedge ck)begin reset_first<=rst_n;reset_last<=reset_first;reset_capture<=reset_last;end
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
 reg [60:0] owners[0:3];
 // Four real 16-bit storage/read shards. Their kept selector and write-control
 // flops are separate native drivers; synthesis buffers do not qualify them.
 (* keep=1,dont_touch=1 *)reg [1:0] read_user[0:3],check_user[0:3];
 (* keep=1,dont_touch=1 *)reg [3:0] load_owner[0:3];
 reg [60:0] owner_pending;
 wire [60:0] check_owner,chosen;
 genvar sh;
 generate for(sh=0;sh<4;sh=sh+1)begin:g_owner_shard
   localparam integer LO=sh*16, W=(61-LO<16)?61-LO:16;
   (* keep=1,dont_touch=1 *)reg reset_shard;
   always @(posedge ck)reset_shard<=reset_capture;
   always @(posedge ck)begin
     read_user[sh]<=cal_user_rx;check_user[sh]<=rx_user;
   end
   // A descriptor in the immediately preceding edge is authoritative too.
   // This bypass preserves replay protection for consecutive HEAD records.
   assign check_owner[LO+:W]=load_owner[sh][check_user[sh]]?
       owner_pending[LO+:W]:owners[check_user[sh]][LO+:W];
   assign chosen[LO+:W]=owners[read_user[sh]][LO+:W];
   integer b;
   always @(posedge ck or negedge reset_shard)
     if(!reset_shard)load_owner[sh]<=0;
     else if(reseed)load_owner[sh]<=0;
     else for(b=0;b<4;b=b+1)
       load_owner[sh][b]<=take&&legal&&!(have[uq]&&
         (owner[58:45]<check_owner[58:45]||
         (owner[58:45]==check_owner[58:45]&&owner!=check_owner)))&&
         (MUT_STALE==0||!have[uq])&&uq==b;
   always @(posedge ck)
     for(b=0;b<4;b=b+1)
       if(load_owner[sh][b])owners[b][LO+:W]<=owner_pending[LO+:W];
 end endgenerate
 always @(posedge ck)owner_pending<=owner;
 reg [3:0] have;
 reg [5:0] stage[0:3];
 wire [60:0] owner=hq[64:4];
 wire [35:0] header=hq[551:516];
 wire take=hq_valid&&(adm_q||MUT_BOOT!=0)&&header[30:27]==4'd12;
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
     if(cstart_q&&adm_q)begin
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
