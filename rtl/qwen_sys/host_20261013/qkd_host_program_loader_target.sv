`timescale 1ns/1ps
// Explicit external program-service boundary, separate from native_pr (HC copy).
// Stages an ordered image, checks its external epoch/digest authorization, then
// replays writes on fixed consecutive cycles. No ready/credit scheduling.
// The digest detects transfer errors; auth_* must come from the trusted external
// service, not from this digest output. This leaf is not a cryptographic verifier.
// kvsys lead r8 2026-10-15 (HOST root mapping: ck_program_loader carried 66,392 FF
// incl. the 65,536-bit program image as flops, a >15k-sink clock root): the 1024 x 64
// program image is now four real 256 x 64 1RW SRAM macros (ot_sram_1rw_256x64_m4_r2c2;
// LOAD writes, REPLAY reads, never both). The macro read is registered, so replay
// emits each program write one edge after its read; a one-edge REPLAY_W keeps the
// descriptor writes contiguous after the last program write (same 1032-cycle replay,
// +1 edge before the first write). Repair ports tied off (no BIST repair), as every
// r2c2 macro instance in the tree.
// KV-TOK 10-26 (B33 BOOT_FAULT@655): the length table below is the SAME external boot ABI as the die dispatcher
// (qkd_static_kv_boot_dispatch*: word_count), so it carries the dispatcher's ABI parameters: MU 1 = the native MU ISA
// image (target 1 = 471 words: 326 SU words + 144-word GAP block + seal, qkd_static_kv_boot_dispatch_mu*), AGES 1 = the
// native die-cfg image with the 19 boot ages (target 10 = 32+NRST+1+DIECAP+19 = 96).  The old fixed 327/77 table refused
// the first native BEGIN (target 10, pw 96 -> target_bad -> sticky fault) and so every image.  Defaults = the old table.
module qkd_host_program_loader_target # (parameter integer MUT=0,parameter integer MU=0,parameter integer AGES=0,
 parameter integer NRST=43,parameter integer DIECAP=1)(
 input wire ck,rst_n,begin_image,input wire[15:0]image_epoch,
 input wire[3:0]image_target,auth_target,output reg[3:0]replay_target,
 input wire[10:0]pw_count,input wire[3:0]dw_count,
 input wire word_v,word_desc,input wire[9:0]word_addr,input wire[63:0]word_data,
 input wire seal,auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire execution_active,
 output reg[142:0]pr,output reg program_ready,fault,
 output reg[63:0]digest,output reg[15:0]program_epoch,
 output reg authorized_footer_valid,output reg[63:0]authorized_footer);
 // Non-ISA image lengths are part of the external boot ABI, never defaults.
 function automatic [10:0]target_words(input[3:0]t);
  case(t)1:target_words=(MU!=0)?11'd471:11'd327;2:target_words=181;3:target_words=4;
   4,5:target_words=192;6,7,8,9:target_words=1024;
   // KVJ-G2b 10-17: static KV die dispatcher targets 10 (die cfg 32 + NRST 43 + seal), 11 (link calendar 66),
   // 12 (PC chain players 1024), 13 (join4 beat calendar 8)
   // KV-HROOT 10-18 (LB2-QWEN-KV F-K1): the die dispatcher is built DIECAP=1 (word_count 32+NRST+1+1 = 77: die cfg
   // capability word), so target 10 is 77 words; 76 made the loader refuse every die-cfg image.
   10:target_words=11'(32+NRST+1+((DIECAP!=0)?1:0)+((AGES!=0)?19:0));11:target_words=66;12:target_words=1024;13:target_words=8;default:target_words=0;endcase
 endfunction
 // DIE-KV-70 prompt form (two strikes, RE-FORM): every service input passes two edges, s1 (pin register) then s3 (apply).
 // The length/order checks are computed between them, from s1 and from the image counters np/nd/got_p/got_d, which move at
 // the s1 -> s3 edge, so each word's check sees the words before it.  A counter moved by a word or BEGIN that is then
 // refused does no harm: the refusal is a sticky fault.
 reg s1_begin,s1_word_v,s1_seal,s1_auth_v,s3_begin,s3_word_v,s3_seal,s3_auth_v;
 reg[15:0]s1_image_epoch,s3_image_epoch,s1_auth_epoch,s3_auth_epoch;
 reg[3:0]s1_image_target,s3_image_target,s1_auth_target,s3_auth_target,s1_dw;
 reg[10:0]s1_pw;reg s1_desc,s3_desc;reg[9:0]s1_addr,s3_addr;reg[63:0]s1_data,s3_data,s1_auth_digest,s3_auth_digest;
 reg s3_begin_bad,s3_word_bad,s3_seal_bad;
 wire target_bad=s1_image_target>13||(s1_image_target==0?(s1_dw==0||s1_dw>8):
  (s1_dw!=0||s1_pw!=target_words(s1_image_target)));
 localparam IDLE=0,LOAD=1,SEALED=2,REPLAY_P=3,REPLAY_D=4,READY=5,REPLAY_W=6;
 reg footer_staged;
 reg[2:0]state;reg[10:0]np,got_p,index_p;reg[3:0]nd,got_d,index_d;
 reg[63:0]dm[0:7];
 // ---- program image: 4 x ot_sram_1rw_256x64_m4_r2c2 -------------------------------
 wire p_bad=s1_desc?(got_p!=np||got_d>=nd||s1_addr!={6'b0,got_d}):(got_p>=np||got_d!=0||{1'b0,s1_addr}!=got_p);
 wire p_wr=rst_n&&!s3_begin&&!fault&&s3_word_v&&!s3_desc&&state==LOAD&&!execution_active&&!s3_word_bad;
 wire p_rd=rst_n&&!s3_begin&&!fault&&state==REPLAY_P&&!execution_active;
 wire[9:0] p_addr=p_wr?s3_addr:index_p[9:0];
 wire[63:0] p_q[0:3];
 genvar gb;
 generate for(gb=0;gb<4;gb=gb+1)begin:g_pm
  ot_sram_1rw_256x64_m4_r2c2 u_pm(.clk(ck),.ce_in((p_wr||p_rd)&&p_addr[9:8]==gb),.we_in(p_wr),.addr_in(p_addr[7:0]),
   .wd_in(s3_data),.w_mask_in({64{1'b1}}),.rd_out(p_q[gb]),.rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
 end endgenerate
 reg rv_q;reg[9:0]ri_q;
 wire[63:0]next_digest={digest[56:0],digest[63:57]} ^ s3_data ^ {53'b0,s3_desc,s3_addr};
 always @(posedge ck)begin
  s1_image_epoch<=image_epoch;s1_image_target<=image_target;s1_pw<=pw_count;s1_dw<=dw_count;s1_desc<=word_desc;s1_addr<=word_addr;s1_data<=word_data;
  s1_auth_epoch<=auth_epoch;s1_auth_target<=auth_target;s1_auth_digest<=auth_digest;
  s3_image_epoch<=s1_image_epoch;s3_image_target<=s1_image_target;s3_desc<=s1_desc;s3_addr<=s1_addr;s3_data<=s1_data;
  s3_auth_epoch<=s1_auth_epoch;s3_auth_target<=s1_auth_target;s3_auth_digest<=s1_auth_digest;
  s3_begin_bad<=s1_pw==0||s1_pw>1024||target_bad;s3_word_bad<=p_bad;s3_seal_bad<=got_p!=np||got_d!=nd;
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin s1_begin<=0;s1_word_v<=0;s1_seal<=0;s1_auth_v<=0;s3_begin<=0;s3_word_v<=0;s3_seal<=0;s3_auth_v<=0;np<=0;nd<=0;got_p<=0;got_d<=0;end
  else begin
   s1_begin<=begin_image;s1_word_v<=word_v;s1_seal<=seal;s1_auth_v<=auth_v;s3_begin<=s1_begin;s3_word_v<=s1_word_v;s3_seal<=s1_seal;s3_auth_v<=s1_auth_v;
   if(s1_begin)begin np<=s1_pw;nd<=s1_dw;got_p<=0;got_d<=0;end
   else if(s1_word_v)begin if(s1_desc)got_d<=got_d+1'b1;else got_p<=got_p+1'b1;end
  end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin authorized_footer_valid<=0;authorized_footer<=0;footer_staged<=0;replay_target<=0;state<=IDLE;pr<=0;program_ready<=0;fault<=0;digest<=0;program_epoch<=0;index_p<=0;index_d<=0;rv_q<=0;ri_q<=0;end
  else begin
   pr<=0;
   // registered macro read: the program write of the read issued last edge (suppressed by a fault this edge)
   rv_q<=p_rd;ri_q<=index_p[9:0];
   if(rv_q&&!fault&&!s3_begin&&!execution_active&&MUT!=1)pr[74:0]<={1'b1,ri_q,p_q[ri_q[9:8]]};
   if(s3_begin)begin
    authorized_footer_valid<=0;authorized_footer<=0;footer_staged<=0;program_ready<=0;
    if(execution_active||state==LOAD||state==SEALED||state==REPLAY_P||state==REPLAY_W||state==REPLAY_D||s3_begin_bad)begin fault<=1;state<=IDLE;end
    else if(!fault)begin state<=LOAD;digest<=64'h51484f5354505247 ^ {60'b0,s3_image_target};program_epoch<=s3_image_epoch;replay_target<=s3_image_target;end
   end else if(!fault)begin
    if(s3_word_v)begin
     if(state!=LOAD||execution_active||s3_word_bad)begin fault<=1;program_ready<=0;state<=IDLE;end
     else begin
      digest<=next_digest;
      if(s3_desc)dm[s3_addr[2:0]]<=s3_data;
      else begin                        // image word written into the macro by p_wr
       if(s3_addr==1023&&replay_target==0)begin footer_staged<=1;authorized_footer<=s3_data^64'(MUT==2);end end
     end
    end
    if(s3_seal)begin
     if(state!=LOAD||s3_word_v||s3_seal_bad)begin fault<=1;state<=IDLE;end
     else state<=SEALED;
    end
    if(s3_auth_v)begin
     if(state!=SEALED||(MUT!=3&&s3_auth_target!=replay_target)||s3_auth_epoch!=program_epoch||s3_auth_digest!=digest||execution_active)begin fault<=1;state<=IDLE;program_ready<=0;end
     else begin authorized_footer_valid<=replay_target==0&&footer_staged&&np==1024;state<=REPLAY_P;index_p<=0;index_d<=0;end
    end
    if(state==REPLAY_P)begin
     if(execution_active)begin fault<=1;state<=IDLE;end
     else begin
      if(index_p+1'b1==np)state<=REPLAY_W;else index_p<=index_p+1'b1;
     end
    end
    if(state==REPLAY_W)begin   // the last program write leaves the macro pipeline this edge
     if(execution_active)begin fault<=1;state<=IDLE;end else state<=(nd==0)?READY:REPLAY_D;
    end
    if(state==REPLAY_D)begin
     if(execution_active)begin fault<=1;state<=IDLE;end
     else begin pr[142:75]<={1'b1,index_d[2:0],dm[index_d[2:0]]};
      if(index_d+1'b1==nd)state<=READY;else index_d<=index_d+1'b1;
     end
    end
    // One cycle after the last actual output write, never at authorization.
    if(state==READY)program_ready<=!(s3_word_v||s3_seal||s3_auth_v);
   end else begin
    authorized_footer_valid<=0;program_ready<=0;
   end
  end
 end
endmodule
