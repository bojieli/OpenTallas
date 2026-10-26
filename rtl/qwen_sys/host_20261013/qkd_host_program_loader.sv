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
module qkd_host_program_loader # (parameter integer MUT=0)(
 input wire ck,rst_n,begin_image,input wire[15:0]image_epoch,
 input wire[10:0]pw_count,input wire[3:0]dw_count,
 input wire word_v,word_desc,input wire[9:0]word_addr,input wire[63:0]word_data,
 input wire seal,auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire execution_active,
 output reg[142:0]pr,output reg program_ready,fault,
 output reg[63:0]digest,output reg[15:0]program_epoch,
 output reg authorized_footer_valid,output reg[63:0]authorized_footer);
 localparam IDLE=0,LOAD=1,SEALED=2,REPLAY_P=3,REPLAY_D=4,READY=5,REPLAY_W=6;
 reg footer_staged;
 reg[2:0]state;reg[10:0]np,got_p,index_p;reg[3:0]nd,got_d,index_d;
 reg[63:0]dm[0:7];
 // ---- program image: 4 x ot_sram_1rw_256x64_m4_r2c2 -------------------------------
 wire p_bad=word_desc?(got_p!=np||got_d>=nd||word_addr!={6'b0,got_d}):(got_p>=np||got_d!=0||{1'b0,word_addr}!=got_p);
 wire p_wr=rst_n&&!begin_image&&!fault&&word_v&&!word_desc&&state==LOAD&&!execution_active&&!p_bad;
 wire p_rd=rst_n&&!begin_image&&!fault&&state==REPLAY_P&&!execution_active;
 wire[9:0] p_addr=p_wr?word_addr:index_p[9:0];
 wire[63:0] p_q[0:3];
 genvar gb;
 generate for(gb=0;gb<4;gb=gb+1)begin:g_pm
  ot_sram_1rw_256x64_m4_r2c2 u_pm(.clk(ck),.ce_in((p_wr||p_rd)&&p_addr[9:8]==gb),.we_in(p_wr),.addr_in(p_addr[7:0]),
   .wd_in(word_data),.w_mask_in({64{1'b1}}),.rd_out(p_q[gb]),.rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
 end endgenerate
 reg rv_q;reg[9:0]ri_q;
 wire[63:0]next_digest={digest[56:0],digest[63:57]} ^ word_data ^ {53'b0,word_desc,word_addr};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin authorized_footer_valid<=0;authorized_footer<=0;footer_staged<=0;state<=IDLE;pr<=0;program_ready<=0;fault<=0;digest<=0;program_epoch<=0;np<=0;nd<=0;got_p<=0;got_d<=0;index_p<=0;index_d<=0;rv_q<=0;ri_q<=0;end
  else begin
   pr<=0;
   // registered macro read: the program write of the read issued last edge (suppressed by a fault this edge)
   rv_q<=p_rd;ri_q<=index_p[9:0];
   if(rv_q&&!fault&&!begin_image&&!execution_active&&MUT!=1)pr[74:0]<={1'b1,ri_q,p_q[ri_q[9:8]]};
   if(begin_image)begin
    authorized_footer_valid<=0;authorized_footer<=0;footer_staged<=0;program_ready<=0;
    if(execution_active||state==LOAD||state==SEALED||state==REPLAY_P||state==REPLAY_W||state==REPLAY_D||pw_count==0||pw_count>1024||dw_count==0||dw_count>8)begin fault<=1;state<=IDLE;end
    else if(!fault)begin state<=LOAD;np<=pw_count;nd<=dw_count;got_p<=0;got_d<=0;digest<=64'h51484f5354505247;program_epoch<=image_epoch;end
   end else if(!fault)begin
    if(word_v)begin
     if(state!=LOAD||execution_active||p_bad)begin fault<=1;program_ready<=0;state<=IDLE;end
     else begin
      digest<=next_digest;
      if(word_desc)begin dm[word_addr[2:0]]<=word_data;got_d<=got_d+1'b1;end
      else begin got_p<=got_p+1'b1;     // image word written into the macro by p_wr
       if(word_addr==1023)begin footer_staged<=1;authorized_footer<=word_data^64'(MUT==2);end end
     end
    end
    if(seal)begin
     if(state!=LOAD||word_v||got_p!=np||got_d!=nd)begin fault<=1;state<=IDLE;end
     else state<=SEALED;
    end
    if(auth_v)begin
     if(state!=SEALED||auth_epoch!=program_epoch||auth_digest!=digest||execution_active)begin fault<=1;state<=IDLE;program_ready<=0;end
     else begin authorized_footer_valid<=footer_staged&&np==1024;state<=REPLAY_P;index_p<=0;index_d<=0;end
    end
    if(state==REPLAY_P)begin
     if(execution_active)begin fault<=1;state<=IDLE;end
     else begin
      if(index_p+1'b1==np)state<=REPLAY_W;else index_p<=index_p+1'b1;
     end
    end
    if(state==REPLAY_W)begin   // the last program write leaves the macro pipeline this edge
     if(execution_active)begin fault<=1;state<=IDLE;end else state<=REPLAY_D;
    end
    if(state==REPLAY_D)begin
     if(execution_active)begin fault<=1;state<=IDLE;end
     else begin pr[142:75]<={1'b1,index_d[2:0],dm[index_d[2:0]]};
      if(index_d+1'b1==nd)state<=READY;else index_d<=index_d+1'b1;
     end
    end
    // One cycle after the last actual output write, never at authorization.
    if(state==READY)program_ready<=!(word_v||seal||auth_v);
   end else begin
    authorized_footer_valid<=0;program_ready<=0;
   end
  end
 end
endmodule
