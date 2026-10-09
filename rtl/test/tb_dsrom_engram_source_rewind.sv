`timescale 1ns/1ps
// Minimum actual SOURCE event engine + released map/history; full64 users,
// literal36request/22response/52cfg, HARD responseextra2 and actual SRAM RD_PIPE.
module tb_dsrom_engram_source_rewind #(parameter integer DROP_REWIND=0)(input wire clk);
 reg rst_n=0;wire go;wire[20:0] tok,pos;wire[9:0] user;
 wire pr_re;wire[9:0] pr_user;wire[20:0] pr_pos;wire[3:0] pr_blk;
 wire[35:0] request={pr_re,pr_blk,pr_pos,pr_user};
 wire[51:0] config_word={10'd64,21'd1,21'd20};
 reg[21:0] responses[0:4];wire[21:0] response=responses[4];
 reg res_v=0;reg[9:0] res_u=0;reg[20:0] res_p=0,res_i=0;
 wire rfull,rb_v,rb_ready;wire[9:0] rb_user;wire[2:0] rb_n;
 wire ready,ov,od,os,fault,source_fault,done,tok_v,wfi,rej,sq;
 wire[67:0] ids;wire[11:0] ou;wire[20:0] op,ot,tp,ti;wire[9:0] tu;
 reg output_ready=1,issue_slot=0;
 wire death=(pos==3)||(pos==0 && user%5==0); // explicit prepared token-type fixture
 reg[16:0] released[0:129279];reg[16:0] golden[0:63][0:31];reg dead[0:63][0:31];
 reg valid[0:63][0:31];reg rewind_done[0:63];integer highest[0:63],phase[0:63],tail[0:63],cursor[0:63];
 reg[67:0] expected;reg[11:0] expected_u;reg[20:0] expected_p,expected_t;
 reg expected_dead,expected_slot;integer cycles=0,windows=0,rewinds=0,waits=0,finishes=0;
 integer u,p,k,b,hold_cycles=0,pick,raw;reg blocked;reg held=0;reg[9:0] held_u;reg[2:0] held_n;
 function automatic[20:0] prompt(input integer u,input integer p);
  prompt=(p==3||(p==0&&u%5==0))?21'd129264:21'(20+u*31+p*7);
 endfunction
 ot_rom_pkg_ctrl_wfc_tokpipe_src #(.ENGRAM_REWIND(1),.PROMPT_EXTRA(2),.NW(21),.USER_W(10),.UCW(10),.MAXU(64),.WIN(6),
  .REC_SRAM(1),.RD_PIPE(1),.STEPS_PIPE(1),.PRECOMP(1),.FANOUT_COPY(1),.SLEW_COPY(1)) scheduler(
  .clk(clk),.rst_n(rst_n),.cfg_users(config_word[51:42]),.cfg_prompt_len(config_word[41:21]),.cfg_gen_len(config_word[20:0]),
  .core_free(ready),.res_v(res_v),.res_u(res_u),.res_p(res_p),.res_i(res_i),.rfull(rfull),
  .pr_q(response[20:0]),.pr_qk(response[21]),.go(go),.tok(tok),.pos(pos),.user(user),
  .pr_re(pr_re),.pr_user(pr_user),.pr_pos(pr_pos),.pr_blk(pr_blk),
  .tok_v(tok_v),.tok_u(tu),.tok_p(tp),.tok_i(ti),.done(done),.fault(source_fault),.wfi(wfi),.rej(rej),.sq(sq),
  .eng_rb_v(rb_v),.eng_rb_user(rb_user),.eng_rb_n(rb_n),.eng_rb_ready(rb_ready));
 ot_dsrom_engram_lead_producer #(.PROTECT_HISTORY(0)) lead(.clk(clk),.rst_n(rst_n),
  .t_v(go),.t_ready(ready),.t_user({2'd0,user}),.t_pos(pos),.t_tok(tok),.t_first(pos==0),.t_dead(death),.t_slot(issue_slot),
  .rb_v(rb_v&&!DROP_REWIND),.rb_user({2'd0,rb_user}),.rb_n(rb_n),.rb_ready(rb_ready),
  .out_v(ov),.out_ready(output_ready),.out_ids(ids),.out_dead(od),.out_slot(os),.out_user(ou),.out_pos(op),.out_tok(ot),.fault(fault));
 always @(posedge clk) begin
  responses[0]<={1'b1,prompt(request[9:0],request[30:10])};
  for(k=1;k<5;k=k+1) responses[k]<=responses[k-1];
  if(rst_n) begin
   cycles=cycles+1;if(cycles>200000) $fatal(1,"SOURCE rewind drain timeout");
   if(fault||source_fault) $fatal(1,"actual SOURCE/lead fault");
   if(held && (!rb_v||rb_user!=held_u||rb_n!=held_n)) $fatal(1,"held SOURCE rewind context changed");
   held=rb_v&&!rb_ready;if(held) begin held_u=rb_user;held_n=rb_n;waits=waits+1;end
   if(rb_v&&rb_ready) begin
    if(rb_n!=5 || rb_user>=64) $fatal(1,"rejected issued-count mismatch");
    rewinds=rewinds+1;rewind_done[rb_user]=1;for(p=1;p<=5;p=p+1) valid[rb_user][p]=0;
   end
   if(go) begin
    if(!ready || user>=64 || pos>=20) $fatal(1,"actual SOURCE issue admission");
    golden[user][pos]=released[tok];dead[user][pos]=death;valid[user][pos]=1;
    expected=0;blocked=0;
    for(b=0;b<4;b=b+1) begin
     if(pos<b) blocked=1;else if(dead[user][pos-b]) blocked=1;
     expected[b*17+:17]=blocked?17'd2:golden[user][pos-b];
    end
    expected_u=user;expected_p=pos;expected_t=tok;expected_dead=death;expected_slot=issue_slot;
    issue_slot<=!issue_slot;if(pos>highest[user]) highest[user]=pos;
   end
   if(ov&&output_ready) begin
    if(ids!==expected || ou!=expected_u || op!=expected_p || ot!=expected_t || od!=expected_dead || os!=expected_slot)
     $fatal(1,"SOURCE rewind window mismatch user%0d pos%0d got%h expected%h",ou,op,ids,expected);
    windows=windows+1;
   end
   if(tok_v && done) finishes=finishes+1;
   if(finishes==64) begin
    if(windows!=1600 || rewinds!=64 || waits==0) $fatal(1,"SOURCE fullshape counts w%0d r%0d wait%0d",windows,rewinds,waits);
    $display("ENGRAM_SOURCE_REWIND PASS users64 windows1600 rejected5x64 HARDextra2 SRAMcapture heldWait%0d delayedSquashTails reissueIDs DEAD stalls",waits);$finish;
   end
  end
 end
 always @(negedge clk) begin
  if(rst_n) begin
   if(hold_cycles>0) hold_cycles=hold_cycles-1;
   output_ready=(hold_cycles==0)&&(cycles%13>2);res_v=0;pick=-1;
   if(!rfull) begin
    for(u=63;u>=0;u=u-1)
     if((phase[u]==0&&highest[u]>=5)||(phase[u]==1&&tail[u]<=5)||(phase[u]==2&&rewind_done[u]&&cursor[u]<20&&valid[u][cursor[u]])) pick=u;
    if(pick>=0 && cycles%3==0) begin
     res_v=1;res_u=pick;
     if(phase[pick]==0) begin
      res_p=0;res_i=21'(9000+pick);phase[pick]=1;tail[pick]=1;hold_cycles=40;output_ready=0;
     end else if(phase[pick]==1) begin
      res_p=tail[pick];res_i=21'(10000+pick+tail[pick]);tail[pick]=tail[pick]+1;
      if(tail[pick]==6) begin phase[pick]=2;cursor[pick]=1;end
     end else begin res_p=cursor[pick];res_i=prompt(pick,cursor[pick]+1);cursor[pick]=cursor[pick]+1;end
    end
   end
  end
 end
 initial begin
  string dir;if(!$value$plusargs("OT_ROM_DIR=%s",dir)) $fatal(1,"released images missing");
  $readmemh({dir,"/expected.hex"},released);
  for(u=0;u<64;u=u+1) begin highest[u]=-1;rewind_done[u]=0;phase[u]=0;tail[u]=1;cursor[u]=1;for(p=0;p<32;p=p+1) begin valid[u][p]=0;golden[u][p]=0;dead[u][p]=0;end end
  for(k=0;k<5;k=k+1) responses[k]=0;
  repeat(12) @(negedge clk);rst_n=1;
 end
endmodule
