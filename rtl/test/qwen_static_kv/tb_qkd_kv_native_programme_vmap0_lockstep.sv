`timescale 1ns/1ps
// KVJ-A 10-17 lockstep: the VMAP successor at VMAP=0 (and MUT=0) against the
// pre-VMAP programme (73d265953, module renamed qkd_kv_native_programme_base by
// the gate script). Same pins every edge: boot image, then random starts with
// random roots, random stray cfg writes and resets. Every output compared on
// every edge. BAD=1 compares the base against VMAP=1 (must differ: mutant).
module tb_qkd_kv_native_programme_vmap0_lockstep;
 parameter integer BAD=0,EDGES=400000,SEED=1;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0,cfg_we=0,start=0;reg[7:0]cfg_addr=0;reg[5:0]stage=1;reg[63:0]cfg_data=0;
 reg[15:0]epoch=0;reg[17:0]token=0;reg[12:0]position=0;reg[1:0]generation=0;
 wire[223:0]oa,ob;
 `define PORTS(o) .ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),\
  .start(start),.stage(stage),.epoch(epoch),.token(token),.position(position),.generation(generation),\
  .compiled_word_slot(o[0]),.compiled_word_index(o[2:1]),.compiled_identity(o[61:3]),.compiled_generation(o[63:62]),\
  .kvn_word_slot(o[64]),.configured(o[65]),.active(o[66]),.done(o[67]),.fault(o[68]),.cycle(o[100:69]),\
  .expected_valid(o[104:101]),.expected_pc(o[124:105]),.expected_stack(o[126:125]),.expected_identity(o[185:127]),\
  .expected_generation(o[187:186]),.expected_address(o[216:188])
 qkd_kv_native_programme_base #(.MUT(0)) a(`PORTS(oa));
 qkd_kv_native_programme #(.MUT(0),.VMAP(BAD?1:0)) b(`PORTS(ob));
 assign oa[223:217]=0;assign ob[223:217]=0;
 reg[63:0]boot[0:180];integer hold=0,i,e,diffs=0,seed=SEED,starts=0,slots=0,evs=0;
 task step;begin @(negedge ck);if(oa!==ob)diffs=diffs+1;if(oa[0])slots=slots+1;if(|oa[104:101])evs=evs+1;end endtask
 task boot_image;begin
  for(i=0;i<181;i=i+1)begin cfg_we=1;cfg_addr=i;cfg_data=boot[i];step();end
  cfg_we=0;step();end endtask
 initial begin
  $readmemh("boot.hex",boot);
  rst_n=0;step();rst_n=1;repeat(3)step();boot_image();
  for(e=0;e<EDGES;e=e+1)begin
   start=0;cfg_we=0;
   if(hold>0)hold=hold-1;
   if(!oa[66]&&hold==0&&($random(seed)&7)==0)begin
    hold=3;
    start=1;stage=1+($unsigned($random(seed))%36);epoch=$random(seed);token=$random(seed);
    position=$random(seed);generation=$random(seed);starts=starts+1;
   end
   if(($random(seed)&18'h3ffff)==0)begin cfg_we=1;cfg_addr=$random(seed);cfg_data=$random(seed);end
   if(($random(seed)&15'h7fff)==0)begin rst_n=0;step();rst_n=1;repeat(3)step();boot_image();end
   step();
  end
  if(BAD)begin if(diffs==0)$fatal(1,"VMAP1 mutant escaped lockstep");$display("PASS observed negative VMAP1 diffs%0d",diffs);$finish;end
  if(diffs)$fatal(1,"FAIL lockstep diffs%0d",diffs);
  if(slots<1000||evs<100)$fatal(1,"weak stimulus slots%0d evs%0d",slots,evs);
  $display("PASS VMAP0 lockstep vs pre-VMAP programme edges%0d starts%0d slots%0d expected_events%0d diffs0",EDGES,starts,slots,evs);$finish;
 end
endmodule
