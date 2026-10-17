`timescale 1ps/1fs
// KVJ-D 2026-10-17: per-group control tile qkd_kv_grp_ctl.  Composes the three component proofs on the ONE tile:
// (1) tb_static_phase_launch's 36 explicitly phased packets on all 3 lanes with an independent HBM edge-index
// scoreboard (fixed edge + held metadata) and the unsafe-phase abort; (2) tb_static_boot_cdc's 32-word image through
// ALL FIVE boot CDCs at once (cdc0 front calendar HAS_SEAL 0: no seal; cdc1..4 pc calendars: seal + application age);
// (3) the drain guard: quiet -> drained, an HBM fault observation -> sticky fault.  MUT 1: cdc2 address flip;
// MUT 2: phase metadata flip.  Core 625u / HBM 768u, the component benches' declared clocks.
module tb_kv_grp_ctl #(parameter integer MUT=0);
 reg ck=0,hck=0,rst_n=0,hrst_n=0;
 initial begin #1000;forever begin ck=1;#312.5;ck=0;#312.5;end end
 initial begin #142;forever begin hck=1;#384;hck=0;#384;end end
 reg cg=0,kg=0,vg=0;reg[13:0]ctx=1;reg[15:0]ep=0;reg[5:0]layer=0;
 wire ch,kh,vh,fc,fh,ic,ih;wire[13:0]cth;wire[15:0]eph;wire[5:0]lh;
 reg [3:0] ci=4'hf, ri=4'hf, chi=4'hf, fhi=4'hf, rhi=4'hf, fhbm=0;
 reg uq=0, uf=0;
 wire drained, dfault;
 reg [4:0] we=0,last=0; reg [39:0] addr=0; reg [319:0] data=0;
 wire [4:0] sw,seal,applied,bfh,bfc; wire [39:0] sa; wire [319:0] sd;
 qkd_kv_grp_ctl #(.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.hck(hck),.hrst_n(hrst_n),
  .ctrl_go(cg),.kgo(kg),.vgo(vg),.ctx_t(ctx),.epoch(ep),.layer(layer),
  .ctrl_go_h(ch),.kgo_h(kh),.vgo_h(vh),.ctx_t_h(cth),.epoch_h(eph),.layer_h(lh),
  .ph_fault_core(fc),.ph_idle_core(ic),.ph_fault_hbm(fh),.ph_idle_hbm(ih),
  .ctrl_idle_core(ci),.ring_idle_core(ri),.ctrl_idle_hbm(chi),.front_idle_hbm(fhi),.ring_idle_hbm(rhi),
  .ctrl_fault_core(4'd0),.ctrl_completion_fault_core(4'd0),.ctrl_intake_fault_core(4'd0),.ring_fault_core(4'd0),
  .ctrl_fault_hbm(fhbm),.ctrl_output_fault_hbm(4'd0),.ctrl_calendar_fault_hbm(4'd0),.ring_fault_hbm(4'd0),
  .front_fault_overflow_hbm(4'd0),.front_fault_go_hbm(4'd0),.front_hold_hbm(4'd0),
  .upstream_quiet(uq),.upstream_fault(uf),.drained(drained),.drain_fault(dfault),
  .cfg_we(we),.cfg_addr(addr),.cfg_data(data),.cfg_last(last),
  .sink_we(sw),.sink_addr(sa),.sink_data(sd),.sink_seal(seal),.applied_hbm(applied),.boot_fault_hbm(bfh),.boot_fault_core(bfc));
 // ---- phase launch scoreboard (tb_static_phase_launch) ----
 integer core_i=-1,hbm_i=-7,received=0,scheduled=0;
 reg[2:0]em[0:4095];reg[35:0]meta[0:4095];integer z;
 initial for(z=0;z<4096;z=z+1)begin em[z]=0;meta[z]=0;end
 always @(posedge ck)core_i<=core_i+1;
 always @(posedge hck)begin
  hbm_i=hbm_i+1;#1;
  if(hbm_i>=0)begin
   if({vh,kh,ch}!==em[hbm_i])$fatal(1,"fixed HBM edge differs index%0d actual%h expected%h",hbm_i,{vh,kh,ch},em[hbm_i]);
   if(em[hbm_i]!=0)begin
    if({cth,eph,lh}!==meta[hbm_i])$fatal(1,"actual held metadata changed");
    received=received+1;
   end
  end
 end
 // ---- boot CDC scoreboard (tb_static_boot_cdc, x5) ----
 integer seen[0:4],seals[0:4],age[0:4],k;
 initial for(k=0;k<5;k=k+1)begin seen[k]=0;seals[k]=0;age[k]=0;end
 always @(posedge hck)begin
  #1;
  for(k=0;k<5;k=k+1)begin
   if(sw[k])begin
    if(sa[8*k+:8]!=8'(seen[k])||sd[64*k+:64]!=(64'h1234567800000000^64'(seen[k]+256*k)))$fatal(1,"actual CDC%0d word differs",k);
    if(seen[k]>=32||seals[k]!=0)$fatal(1,"late/duplicate boot word cdc%0d",k);seen[k]=seen[k]+1;
   end
   if(seal[k])begin if(k==0||seen[k]!=32||seals[k]!=0)$fatal(1,"seal law cdc%0d",k);seals[k]=seals[k]+1;age[k]=0;end
   else if(seals[k]!=0)age[k]=age[k]+1;
   if(applied[k]&&(seen[k]!=32||(k!=0&&(seals[k]!=1||age[k]<2))))$fatal(1,"applied before actual child acceptance cdc%0d",k);
  end
 end
 task tick;begin @(posedge ck);#1;end endtask
 task send_safe(input integer p);integer gap,toggle_i,first,out;reg found;reg[2:0]mask;begin
  found=0;
  while(!found)begin
   @(negedge ck);toggle_i=core_i+2;
   gap=768-(((toggle_i-6)*625)%768);
   found=gap>=200&&gap<=600;
  end
  mask=3'(1+p%7);ctx=14'(1+p*17);ep=16'(1234+p);layer=6'(p%36);
  {vg,kg,cg}=mask;
  first=((toggle_i-6)*625)/768+1;out=first+2;
  if(out<0||out>=4096||em[out]!=0)$fatal(1,"invalid declared test schedule");
  em[out]=mask;meta[out]={ctx,ep,layer};scheduled=scheduled+1;
  tick();@(negedge ck);cg=0;kg=0;vg=0;
  repeat(12)tick();
  if(fc||fh)$fatal(1,"valid explicitly phased launch faulted");
 end endtask
 integer p,gap,ti,a;reg found;
 initial begin
  repeat(5)tick();@(negedge ck);rst_n=1;hrst_n=1;repeat(20)tick();
  // boot images on all five CDCs at once
  for(a=0;a<32;a=a+1)begin
   @(negedge ck);we=5'h1f;last={5{a==31}};
   for(k=0;k<5;k=k+1)begin addr[8*k+:8]=8'(a);data[64*k+:64]=64'h1234567800000000^64'(a+256*k);end
  end
  @(negedge ck);we=0;last=0;repeat(60)@(negedge ck);
  for(k=0;k<5;k=k+1)if(seen[k]!=32||seals[k]!=(k==0?0:1)||!applied[k]||bfc[k]||bfh[k])$fatal(1,"CDC%0d did not apply exact complete image",k);
  // phase launch
  for(p=0;p<36;p=p+1)send_safe(p);
  repeat(12)tick();if(received!=scheduled||!ic||!ih)$fatal(1,"real launch debt did not drain");
  // drain guard: quiet -> drained, then an HBM fault observation -> sticky fault
  uq=1;repeat(8)tick();if(!drained||dfault)$fatal(1,"drain guard did not report drained");
  fhbm=4'h4;repeat(6)tick();fhbm=0;repeat(4)tick();if(drained||!dfault)$fatal(1,"drain guard missed HBM fault");
  // unsafe phase abort
  found=0;while(!found)begin @(negedge ck);ti=core_i+2;gap=768-(((ti-6)*625)%768);found=gap<200||gap>600;end
  cg=1;tick();@(negedge ck);cg=0;repeat(10)tick();
  if(!fc)$fatal(1,"unsafe phase accepted without explicit fault");
  if(received!=scheduled)$fatal(1,"unsafe phase was dynamically deferred");
  $display("GRP_CTL PASS boot 5x32 words (4 sealed), phase 36 packets/%0d HBM events, drain+fault, unsafe abort MUT=%0d",received,MUT);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
