`timescale 1ns/1ps
// KV-GRP-CTL/MU5 10-19: qkd_kv_native_programme VMAP 1 with SRAM 1 + RCOPIES 3 (root table in one SRAM macro, row read on
// the start edge, 3 kept reset copies; the mu5 u_wprg) in lockstep with SRAM 0 / RCOPIES 1 (the flop table; every other
// view).  Same boot words (random valid root tables; some corrupted images), random starts of stages 1..36 (and invalid
// starts: stage 0 / 37, start while active, cfg write after the seal); every output compared on every edge.
// PASS line: PASS KV_WPRG_MU5_LOCKSTEP ...; any difference: FAIL KV_WPRG_MU5_LOCKSTEP mismatches<n> ...
module tb_kv_wprg_mu5_lockstep;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,we=0,st=0;reg[7:0]addr=0;reg[63:0]data=0;reg[5:0]stg=0;reg[15:0]ep=0;reg[17:0]tok=0;reg[12:0]pos=0;reg[1:0]gen=0;
 wire a_s,b_s,a_k,b_k,a_cf,b_cf,a_ac,b_ac,a_dn,b_dn,a_ft,b_ft;wire[1:0]a_wi,b_wi,a_cg,b_cg,a_eg,b_eg,a_es,b_es;
 wire[58:0]a_ci,b_ci,a_ei,b_ei;wire[31:0]a_cy,b_cy;wire[3:0]a_ev,b_ev;wire[19:0]a_ep,b_ep;wire[28:0]a_ea,b_ea;
 `define WPRG_CONN(p) (.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.start(st),.stage(stg),.epoch(ep),\
  .token(tok),.position(pos),.generation(gen),.compiled_word_slot(p``s),.compiled_word_index(p``wi),.compiled_identity(p``ci),\
  .compiled_generation(p``cg),.kvn_word_slot(p``k),.configured(p``cf),.active(p``ac),.done(p``dn),.fault(p``ft),.cycle(p``cy),\
  .expected_valid(p``ev),.expected_pc(p``ep),.expected_stack(p``es),.expected_identity(p``ei),.expected_generation(p``eg),\
  .expected_address(p``ea))
 qkd_kv_native_programme #(.MUT(0),.VMAP(1)) ref0 `WPRG_CONN(a_);
 qkd_kv_native_programme #(.MUT(0),.VMAP(1),.RCOPIES(3),.SRAM(1)) dut `WPRG_CONN(b_);
 wire[255:0]va={a_s,a_k,a_cf,a_ac,a_dn,a_ft,a_wi,a_cg,a_eg,a_es,a_ci,a_ei,a_cy,a_ev,a_ep,a_ea};
 wire[255:0]vb={b_s,b_k,b_cf,b_ac,b_dn,b_ft,b_wi,b_cg,b_eg,b_es,b_ci,b_ei,b_cy,b_ev,b_ep,b_ea};
 integer mism=0,cycles=0,slots=0,dones=0,faults=0,boots=0,runs=0;
 always @(posedge ck)begin
  #0.1;cycles=cycles+1;
  if(va!==vb)begin mism=mism+1;if(mism<=5)$display("MISMATCH cyc %0d ref %h dut %h",cycles,va,vb);end
  if(a_s)slots=slots+1;if(a_dn&&!a_ft)dones=dones+1;
 end
 reg[31:0]T[0:35][0:4];integer s,w,a,n,ep_i,i;
 task tick;begin @(negedge ck);end endtask
 task make;begin
  for(s=0;s<36;s=s+1)begin
   T[s][0]=4+$urandom%20;for(w=1;w<4;w=w+1)T[s][w]=T[s][w-1]+1+$urandom%30;T[s][4]=T[s][3]+3+$urandom%40;
  end
 end endtask
 task boot(input integer bad);begin
  n=$urandom%181;
  for(a=0;a<181;a=a+1)begin
   tick();we=1;addr=a;data=(a<180)?{32'd0,T[a/5][a%5]}:64'h514b565052473336;
   if(bad&&a==n)case($urandom%3)0:data[63:32]=1;1:data[31:0]=1;default:data[3:0]=data[3:0]^4'h5;endcase
  end
  tick();we=0;repeat(3)tick();boots=boots+1;
 end endtask
 task reset;begin tick();rst_n=0;we=0;st=0;repeat(4)tick();rst_n=1;repeat(3)tick();end endtask
 task go(input[5:0]sg);begin
  tick();st=1;stg=sg;ep=$urandom;tok=$urandom;pos=$urandom;gen=$urandom;tick();st=0;stg=$urandom;runs=runs+1;
 end endtask
 initial begin
  for(ep_i=0;ep_i<60;ep_i=ep_i+1)begin
   reset();make();boot(ep_i%6==5);
   for(i=0;i<12;i=i+1)begin
    go(1+$urandom%36);
    if(ep_i%4==3&&$urandom%3==0)begin repeat($urandom%40)tick();go($urandom%38);end   // stage 0 / 37 / start while active
    tick();tick();                                   // active rises two edges after the start pin
    while(a_ac&&!a_ft)tick();
    repeat($urandom%4)tick();
    if(ep_i%5==4&&i==6)begin tick();we=1;addr=$urandom;data=$urandom;tick();we=0;end  // cfg write after the seal
   end
   if(a_ft)faults=faults+1;
  end
  repeat(4)tick();
  if(mism!=0||dones<300||slots<1000||faults<5)
   $display("FAIL KV_WPRG_MU5_LOCKSTEP mismatches%0d dones%0d slots%0d faults%0d",mism,dones,slots,faults);
  else $display("PASS KV_WPRG_MU5_LOCKSTEP mismatches0 boots%0d starts%0d dones%0d slots%0d faults%0d cycles%0d",
   boots,runs,dones,slots,faults,cycles);
  $finish;
 end
endmodule
