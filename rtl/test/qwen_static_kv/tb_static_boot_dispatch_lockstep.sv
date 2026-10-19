`timescale 1ns/1ps
// KVJ-A 10-17 lockstep: dispatcher successor (front_last, 8-b controller_addr)
// against the 73d265953 dispatcher (renamed qkd_static_kv_boot_dispatch_base).
// Random HOST replays (exact images with random gaps, rare corruptions, random
// resets and random sink/local/fault inputs). Every base output equal on every
// edge; controller_addr[7:5]==0; front_last == front_we exactly when
// group_addr==5. MUT_B=4 (front_last never asserted) must fail.
module tb_static_boot_dispatch_lockstep;
 parameter integer MUT_B=0,REPLAYS=60,SEED=7;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg[142:0]pr=0;reg[3:0]target=1;reg ready=0,sfault=0,active=0,kfault=0;
 reg[15:0]epoch=123;reg[63:0]digest=0;reg[159:0]applied=0;reg[2:0]configured=0;
 wire[431:0]oa;wire[431:0]ob;wire[2:0]ob_hi;wire[31:0]flast;
 wire[127:0]cwa,cwb,cla,clb;wire[4:0]caa;wire[7:0]cab;wire[63:0]cda,cdb;wire sra,srb,fa,fb;wire[7:0]fca,fcb;wire[15:0]iea,ieb;wire[63:0]ida,idb;
 qkd_static_kv_boot_dispatch_base a(.ck(ck),.rst_n(rst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(sfault),
  .boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied),.local_configured(configured),.sink_fault(kfault),
  .layer_we(oa[0]),.layer_addr(oa[9:1]),.layer_data(oa[73:10]),.writer_we(oa[74]),.writer_addr(oa[82:75]),.writer_data(oa[146:83]),
  .ownership_we(oa[147]),.ownership_addr(oa[149:148]),.ownership_data(oa[181:150]),.landing_we(oa[213:182]),.front_we(oa[245:214]),
  .group_addr(oa[253:246]),.group_data(oa[317:254]),.controller_we(cwa),.controller_addr(caa),.controller_data(cda),.controller_last(cla),
  .setup_ready(sra),.fault(fa),.fault_code(fca),.installed_epoch(iea),.installed_isa_digest(ida));
 qkd_static_kv_boot_dispatch #(.MUT(MUT_B)) b(.ck(ck),.rst_n(rst),.boot_pr(pr),.boot_image_target(target),.boot_image_ready(ready),.boot_image_fault(sfault),
  .boot_image_epoch(epoch),.boot_image_digest(digest),.execution_active(active),.sink_applied(applied),.local_configured(configured),.sink_fault(kfault),
  .layer_we(ob[0]),.layer_addr(ob[9:1]),.layer_data(ob[73:10]),.writer_we(ob[74]),.writer_addr(ob[82:75]),.writer_data(ob[146:83]),
  .ownership_we(ob[147]),.ownership_addr(ob[149:148]),.ownership_data(ob[181:150]),.landing_we(ob[213:182]),.front_we(ob[245:214]),
  .group_addr(ob[253:246]),.group_data(ob[317:254]),.controller_we(cwb),.controller_addr(cab),.controller_data(cdb),.controller_last(clb),
  .front_last(flast),.setup_ready(srb),.fault(fb),.fault_code(fcb),.installed_epoch(ieb),.installed_isa_digest(idb));
 assign oa[431:318]=0;assign ob[431:318]=0;
 integer r,t,w,n,diffs=0,fl_bad=0,fl_seen=0,setups=0,faults=0,edges=0,seed=SEED;
 always @(negedge ck)begin
  edges=edges+1;
  if(oa!==ob||cwa!==cwb||{3'b0,caa}!==cab||cda!==cdb||cla!==clb||sra!==srb||fa!==fb||fca!==fcb||iea!==ieb||ida!==idb)diffs=diffs+1;
  if(flast!==((ob[253:246]==5)?ob[245:214]:32'd0))fl_bad=fl_bad+1;
  if(|flast)fl_seen=fl_seen+1;
  if(sra)setups=setups+1;
 end
 function automatic integer wc(input integer t);case(t)1:wc=327;2:wc=181;3:wc=4;4,5:wc=192;default:wc=1024;endcase endfunction
 task tick;begin @(posedge ck);#1;end endtask
 task gap;begin while(($random(seed)&3)==0)begin pr=0;tick();end end endtask
 task corrupt;begin
  case($unsigned($random(seed))%6)
   0:pr[73:64]=$random(seed);1:epoch=epoch+1;2:active=1;3:pr[142]=1;4:sfault=1;5:kfault=1;
  endcase end endtask
 initial begin
  for(r=0;r<REPLAYS;r=r+1)begin
   @(negedge ck);rst=0;pr=0;ready=0;sfault=0;active=0;kfault=0;applied=0;configured=0;epoch=100+r;tick();@(negedge ck);rst=1;tick();
   for(t=1;t<=10;t=t+1)begin
    @(negedge ck);ready=0;target=(t==10)?4'd0:4'(t);tick();
    if(t<10)for(w=0;w<wc(t);w=w+1)begin
     @(negedge ck);pr=0;pr[74]=1;pr[73:64]=10'(w);pr[63:0]={(t==3)?32'd0:$random(seed),$random(seed)};
     if(r%4==3&&($random(seed)&255)==0)corrupt();
     tick();@(negedge ck);active=0;pr=0;gap();
    end
    @(negedge ck);pr=0;ready=1;digest={$random(seed),$random(seed)};tick();tick();
   end
   @(negedge ck);configured=7;applied=(r%5==4)?{$random(seed)}:{160{1'b1}};tick();tick();
   if(fa)faults=faults+1;
  end
  if(MUT_B!=0)begin if(fl_bad==0)$fatal(1,"front_last mutant escaped");$display("PASS observed negative MUT%0d front_last_bad%0d",MUT_B,fl_bad);$finish;end
  if(diffs||fl_bad)$fatal(1,"FAIL lockstep diffs%0d front_last_bad%0d",diffs,fl_bad);
  if(setups==0||faults==0||fl_seen<32)$fatal(1,"weak stimulus setups%0d faults%0d front_last%0d",setups,faults,fl_seen);
  $display("PASS dispatcher lockstep vs 73d265953 replays%0d edges%0d setup_edges%0d faulted_replays%0d front_last_pulses%0d diffs0",REPLAYS,edges,setups,faults,fl_seen);$finish;
 end
endmodule
