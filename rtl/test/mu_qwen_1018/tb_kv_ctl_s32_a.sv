`timescale 1ns/1ps
// KV-CTL3 S32-A 10-20: the writer programme + writer role of qkd_kvs_ctl as bound today (A: qkd_kv_native_programme
// VMAP 1 SRAM 1 CTLSRAM 1 RCOPIES 16 -> qkd_kv_static_writer_native_mu VMAP 1 MU 1 RST_COPIES 10) in lockstep with the
// S32 forms (B: qkd_kv_native_programme_s32 -> qkd_kv_static_writer_native_mu_s32 through compiled_word_slot_c /
// compiled_word_index_c, NC 4).  Same boot words (random valid root tables, some corrupted images), random starts of
// stages 1..36 (+ invalid starts / start while active / cfg after seal), writer words aligned to chain A's compiled slots
// (valid, header, identity, generation) with single-field corruptions in every third episode, random payloads, resets between episodes and
// inside runs.  Every output of both modules compared on every edge; B's copy outputs must equal its main outputs.
// PASS line: PASS KV_S32_A_LOCKSTEP ...; any difference: FAIL KV_S32_A_LOCKSTEP mismatches<n> ...
module tb_kv_ctl_s32_a;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,we=0,st=0;reg[7:0]addr=0;reg[63:0]data=0;reg[5:0]stg=0;reg[15:0]ep=0;reg[17:0]tok=0;reg[12:0]pos=0;reg[1:0]gen=0;
 wire a_s,b_s,a_k,b_k,a_cf,b_cf,a_ac,b_ac,a_dn,b_dn,a_ft,b_ft;wire[1:0]a_wi,b_wi,a_cg,b_cg,a_eg,b_eg,a_es,b_es;
 wire[58:0]a_ci,b_ci,a_ei,b_ei;wire[31:0]a_cy,b_cy;wire[3:0]a_ev,b_ev;wire[19:0]a_ep,b_ep;wire[28:0]a_ea,b_ea;
 wire[3:0]b_sc;wire[7:0]b_ic;
 `define WPRG_CONN(p) (.ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),.start(st),.stage(stg),.epoch(ep),\
  .token(tok),.position(pos),.generation(gen),.compiled_word_slot(p``s),.compiled_word_index(p``wi),.compiled_identity(p``ci),\
  .compiled_generation(p``cg),.kvn_word_slot(p``k),.configured(p``cf),.active(p``ac),.done(p``dn),.fault(p``ft),.cycle(p``cy),\
  .expected_valid(p``ev),.expected_pc(p``ep),.expected_stack(p``es),.expected_identity(p``ei),.expected_generation(p``eg),\
  .expected_address(p``ea))
 qkd_kv_native_programme #(.MUT(0),.VMAP(1),.RCOPIES(16),.SRAM(1),.CTLSRAM(1)) wa `WPRG_CONN(a_);
 qkd_kv_native_programme_s32 #(.MUT(0),.VMAP(1),.RCOPIES(16),.SRAM(1),.CTLSRAM(1),.NC(4)) wb (.ck(ck),.rst_n(rst_n),
  .cfg_we(we),.cfg_addr(addr),.cfg_data(data),.start(st),.stage(stg),.epoch(ep),.token(tok),.position(pos),.generation(gen),
  .compiled_word_slot(b_s),.compiled_word_index(b_wi),.compiled_word_slot_c(b_sc),.compiled_word_index_c(b_ic),
  .compiled_identity(b_ci),.compiled_generation(b_cg),.kvn_word_slot(b_k),.configured(b_cf),.active(b_ac),.done(b_dn),
  .fault(b_ft),.cycle(b_cy),.expected_valid(b_ev),.expected_pc(b_ep),.expected_stack(b_es),.expected_identity(b_ei),
  .expected_generation(b_eg),.expected_address(b_ea));
 // writer words aligned to chain A's compiled slots, with single-field corruptions
 reg c_v=0,c_t=0,c_i=0,c_g=0,cen=0;reg[3:0]c_tb=0;reg[5:0]c_ib=0;reg[511:0]wdata=0;
 wire wvalid=a_s^c_v;
 wire[10:0]wtag={3'b010,5'd0,a_wi[1],1'b0,a_wi[0]}^(c_t?(11'd1<<c_tb):11'd0);
 wire[58:0]wident=a_ci^(c_i?(59'd1<<(c_ib+6'd6)):59'd0);
 wire[1:0]wgen=a_cg^{1'b0,c_g};
 wire[1151:0]xa_es,xb_es;wire[19:0]xa_dpc,xb_dpc,xa_epc,xb_epc;wire[1:0]xa_dst,xb_dst,xa_g,xb_g,xa_est,xb_est,xa_eg,xb_eg;
 wire[58:0]xa_id,xb_id,xa_eid,xb_eid;wire[3:0]xa_ev,xb_ev;wire[28:0]xa_ea,xb_ea;wire xa_f,xb_f;wire[7:0]xa_fc,xb_fc;
 qkd_kv_static_writer_native_mu #(.MUT(0),.VMAP(1),.MU(1),.RST_COPIES(10)) xa (.ck(ck),.rst_n(rst_n),.word_valid(wvalid),
  .word_tag(wtag),.word_data(wdata),.word_identity(wident),.word_generation(wgen),.compiled_word_slot(a_s),
  .compiled_word_index(a_wi),.compiled_identity(a_ci),.compiled_generation(a_cg),.es(xa_es),.dest_pc(xa_dpc),
  .dest_stack(xa_dst),.identity(xa_id),.generation(xa_g),.expected_valid(xa_ev),.expected_pc(xa_epc),
  .expected_stack(xa_est),.expected_identity(xa_eid),.expected_generation(xa_eg),.expected_address(xa_ea),
  .fault(xa_f),.fault_code(xa_fc));
 qkd_kv_static_writer_native_mu_s32 #(.MUT(0),.VMAP(1),.MU(1),.NC(4),.RST_COPIES(12)) xb (.ck(ck),.rst_n(rst_n),
  .word_valid(wvalid),.word_tag(wtag),.word_data(wdata),.word_identity(wident),.word_generation(wgen),
  .compiled_word_slot(b_s),.compiled_word_index(b_wi),.compiled_word_slot_c(b_sc),.compiled_word_index_c(b_ic),
  .compiled_identity(b_ci),.compiled_generation(b_cg),.es(xb_es),.dest_pc(xb_dpc),
  .dest_stack(xb_dst),.identity(xb_id),.generation(xb_g),.expected_valid(xb_ev),.expected_pc(xb_epc),
  .expected_stack(xb_est),.expected_identity(xb_eid),.expected_generation(xb_eg),.expected_address(xb_ea),
  .fault(xb_f),.fault_code(xb_fc));
 wire[255:0]va={a_s,a_k,a_cf,a_ac,a_dn,a_ft,a_wi,a_cg,a_eg,a_es,a_ci,a_ei,a_cy,a_ev,a_ep,a_ea};
 wire[255:0]vb={b_s,b_k,b_cf,b_ac,b_dn,b_ft,b_wi,b_cg,b_eg,b_es,b_ci,b_ei,b_cy,b_ev,b_ep,b_ea};
 wire[1407:0]ra={xa_es,xa_dpc,xa_dst,xa_id,xa_g,xa_ev,xa_epc,xa_est,xa_eid,xa_eg,xa_ea,xa_f,xa_fc};
 wire[1407:0]rb={xb_es,xb_dpc,xb_dst,xb_id,xb_g,xb_ev,xb_epc,xb_est,xb_eid,xb_eg,xb_ea,xb_f,xb_fc};
 integer mism=0,cmis=0,cycles=0,slots=0,dones=0,faults=0,boots=0,runs=0,writes=0,wfaults=0,rsts=0;
 always @(posedge ck)begin
  #0.1;cycles=cycles+1;
  if(va!==vb||ra!==rb)begin mism=mism+1;if(mism<=5)$display("MISMATCH cyc %0d wprg %0d writer %0d",cycles,va!==vb,ra!==rb);end
  if(b_sc!=={4{b_s}}||b_ic!=={4{b_wi}})begin cmis=cmis+1;if(cmis<=5)$display("COPY MISMATCH cyc %0d",cycles);end
  if(a_s)slots=slots+1;if(a_dn&&!a_ft)dones=dones+1;
  if(xa_es[0])writes=writes+1;
 end
 always @(negedge ck)begin
  wdata<={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,
          $urandom,$urandom,$urandom,$urandom};
  c_v<=cen&&($urandom%400)==0;c_t<=cen&&($urandom%60)==0;c_i<=cen&&($urandom%60)==0;c_g<=cen&&($urandom%120)==0;
  c_tb<=$urandom%11;c_ib<=$urandom%53;
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
 task reset;begin tick();rst_n=0;we=0;st=0;repeat(4)tick();rst_n=1;repeat(3)tick();rsts=rsts+1;end endtask
 task go(input[5:0]sg);begin
  tick();st=1;stg=sg;ep=$urandom;tok=$urandom;pos=$urandom;gen=$urandom;tick();st=0;stg=$urandom;runs=runs+1;
 end endtask
 initial begin
  for(ep_i=0;ep_i<60;ep_i=ep_i+1)begin
   reset();make();boot(ep_i%6==5);cen=(ep_i%3==2);
   for(i=0;i<12;i=i+1)begin
    go(1+$urandom%36);
    if(ep_i%4==3&&$urandom%3==0)begin repeat($urandom%40)tick();go($urandom%38);end
    tick();tick();
    if(ep_i%7==6&&i==8)begin repeat($urandom%30)tick();reset();boot(0);end   // reset inside a run
    while(a_ac&&!a_ft)tick();
    repeat($urandom%4)tick();
    if(ep_i%5==4&&i==6)begin tick();we=1;addr=$urandom;data=$urandom;tick();we=0;end
   end
   if(a_ft)faults=faults+1;if(xa_f)wfaults=wfaults+1;
  end
  repeat(4)tick();
  if(mism!=0||cmis!=0||dones<300||slots<1000||faults<5||writes<600||wfaults<5)
   $display("FAIL KV_S32_A_LOCKSTEP mismatches%0d copy%0d dones%0d slots%0d faults%0d writes%0d wfaults%0d",mism,cmis,dones,slots,faults,writes,wfaults);
  else $display("PASS KV_S32_A_LOCKSTEP mismatches0 copy0 boots%0d starts%0d resets%0d dones%0d slots%0d lane0_writes%0d faults%0d writer_fault_episodes%0d cycles%0d",
   boots,runs,rsts,dones,slots,writes,faults,wfaults,cycles);
  $finish;
 end
endmodule
