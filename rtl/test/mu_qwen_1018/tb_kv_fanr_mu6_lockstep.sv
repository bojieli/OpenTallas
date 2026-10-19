`timescale 1ns/1ps
// KV-SRAM-CTL 10-19 (mu6): qkd_kv_es_fan_root2_b PH1C 1 (ph1 -> 17 kept copies, constant-index 2:1 lane muxes) + RCOPIES 28
// in lockstep with PH1C 0 / RCOPIES 1 (the mu5 form).  Random es / expected / boot / cfg words with dense writer events
// (ev_now -> ph1 sequences incl. back-to-back events, boot words on and off event edges, bad cfg words), random resets;
// h and fault compared on every edge.  PASS: PASS KV_FANR_MU6_LOCKSTEP ...; FAIL KV_FANR_MU6_LOCKSTEP mismatches<n> ...
module tb_kv_fanr_mu6_lockstep;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0;reg[4*288-1:0]es=0;reg[19:0]dpc=0,epc=0;reg[1:0]dst=0,gen=0,est=0,egen=0;reg[58:0]id=0,eid=0;reg[28:0]ea=0;
 reg[3:0]ev=0;reg ss=0;reg[17:0]tok=0;reg[15:0]ep=0;reg cw=0;reg[7:0]ca=0;reg[63:0]cd=0;reg[292:0]bw=0;
 wire[783:0]ha,hb;wire fa,fb;
 `define FANR_CONN(H,F) (.ck(ck),.rst_n(rst_n),.es(es),.dest_pc(dpc),.dest_stack(dst),.identity(id),.generation(gen),\
  .expected_valid(ev),.expected_pc(epc),.expected_stack(est),.expected_identity(eid),.expected_generation(egen),\
  .expected_address(ea),.emb_start(ss),.emb_token(tok),.emb_epoch(ep),.cfg_we(cw),.cfg_addr(ca),.cfg_data(cd),.bw(bw),\
  .h(H),.fault(F))
 qkd_kv_es_fan_root2_b #(.MUT(0)) ref0 `FANR_CONN(ha,fa);
 qkd_kv_es_fan_root2_b #(.MUT(0),.RCOPIES(28),.PH1C(1)) dut `FANR_CONN(hb,fb);
 integer mism=0,cycles=0,ph=0,bts=0,flt=0,i,k,md;
 always @(posedge ck)begin
  #0.1;cycles=cycles+1;
  if({ha,fa}!=={hb,fb})begin mism=mism+1;if(mism<=5)$display("MISMATCH cyc %0d ref %h/%b dut %h/%b",cycles,ha,fa,hb,fb);end
  if(ref0.ph1)ph=ph+1;if(ha[783])bts=bts+1;if(fa)flt=flt+1;
 end
 function automatic [31:0] r32;input integer d;r32=$urandom;endfunction
 initial begin
  for(i=0;i<400000;i=i+1)begin
   @(negedge ck);
   if(i%20000==0)rst_n=0;else if(i%20000==5)rst_n=1;
   for(k=0;k<36;k=k+1)es[32*k+:32]=$urandom;
   // writer valid bits es[0/288/576/864] and expected valids.  Per reset period (20,000 edges): mode 1 = events on even
   // edges only (ph1 phases without the ev_now && ph1 fault), mode 2 = no events + boot words + good cfg words,
   // mode 0 (last 2,000 edges) = dense random events / boot / bad cfg (fault paths).
   md=((i%20000)>=18000)?0:(((i/256)%2)?2:1);
   es[0]=($urandom%3==0);es[288]=($urandom%4==0);es[576]=($urandom%5==0);es[864]=($urandom%5==0);
   ev=($urandom%4==0)?4'($urandom):4'd0;
   if(md==2||(md==1&&i%2==1))begin es[0]=0;es[288]=0;es[576]=0;es[864]=0;ev=0;end
   dpc=$urandom;epc=$urandom;dst=$urandom;gen=$urandom;est=$urandom;egen=$urandom;
   id={$urandom,$urandom};eid={$urandom,$urandom};ea=$urandom;ss=$urandom;tok=$urandom;ep=$urandom;
   cw=($urandom%7==0);ca=$urandom;cd={$urandom,$urandom};if(md!=0||$urandom%2)cd[63:18]=0;
   for(k=0;k<9;k=k+1)bw[32*k+:32]=$urandom;bw[292:288]=$urandom;bw[0]=(md!=1)&&($urandom%3==0);
  end
  if(mism!=0||ph<10000||bts<5000||flt<20||flt>cycles/2)begin
   $display("FAIL KV_FANR_MU6_LOCKSTEP mismatches%0d cycles %0d ph1 %0d boot %0d fault %0d",mism,cycles,ph,bts,flt);
  end else
   $display("PASS KV_FANR_MU6_LOCKSTEP mismatches0 cycles %0d ph1_edges %0d boot_words %0d fault_edges %0d",cycles,ph,bts,flt);
  $finish;
 end
endmodule
