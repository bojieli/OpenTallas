`timescale 1ps/1fs
// KVJ-D 2026-10-17: per-group control tile qkd_kv_grp_ctl.  Composes the three component proofs on the ONE tile:
// (1) tb_static_phase_launch's 36 explicitly phased packets on all 3 lanes with an independent HBM edge-index
// scoreboard (fixed edge + held metadata) and the unsafe-phase abort; (2) tb_static_boot_cdc's 32-word image through
// ALL FIVE boot CDCs at once (cdc0 front calendar HAS_SEAL 0: no seal; cdc1..4 pc calendars: seal + application age);
// (3) the drain guard: quiet -> drained, an HBM fault observation -> sticky fault.  MUT 1: cdc2 address flip;
// MUT 2: phase metadata flip.  Core 625u / HBM 768u, the component benches' declared clocks.
// KV-NATIVE 2026-10-17 (tb_kv_grp_ctl_p): the pin-registered successor qkd_kv_grp_ctl_p (dut, MUT under test) against
// the closed qkd_kv_grp_ctl (ref_, MUT 0) fed the SAME core-domain stimulus delayed by exactly one ck edge (hck-domain
// hrst_n undelayed).  The stimulus is driven one core edge earlier than tb_kv_grp_ctl (rst_n release, toggle index
// core_i+3), so ref_ sees tb_kv_grp_ctl's timing and every tb_kv_grp_ctl scoreboard check is applied to it unchanged;
// every output of dut must equal ref_'s on every ck and hck edge after reset.  MUT 3: dut cfg_we bypasses its pin flop.
module tb_kv_grp_ctl_p #(parameter integer MUT=0);
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
 qkd_kv_grp_ctl_p #(.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.hck(hck),.hrst_n(hrst_n),
  .ctrl_go(cg),.kgo(kg),.vgo(vg),.ctx_t(ctx),.epoch(ep),.layer(layer),
  .ctrl_go_h(d_ch),.kgo_h(d_kh),.vgo_h(d_vh),.ctx_t_h(d_cth),.epoch_h(d_eph),.layer_h(d_lh),
  .ph_fault_core(d_fc),.ph_idle_core(d_ic),.ph_fault_hbm(d_fh),.ph_idle_hbm(d_ih),
  .ctrl_idle_core(ci),.ring_idle_core(ri),.ctrl_idle_hbm(chi),.front_idle_hbm(fhi),.ring_idle_hbm(rhi),
  .ctrl_fault_core(4'd0),.ctrl_completion_fault_core(4'd0),.ctrl_intake_fault_core(4'd0),.ring_fault_core(4'd0),
  .ctrl_fault_hbm(fhbm),.ctrl_output_fault_hbm(4'd0),.ctrl_calendar_fault_hbm(4'd0),.ring_fault_hbm(4'd0),
  .front_fault_overflow_hbm(4'd0),.front_fault_go_hbm(4'd0),.front_hold_hbm(4'd0),
  .upstream_quiet(uq),.upstream_fault(uf),.drained(d_drained),.drain_fault(d_dfault),
  .cfg_we(we),.cfg_addr(addr),.cfg_data(data),.cfg_last(last),
  .sink_we(d_sw),.sink_addr(d_sa),.sink_data(d_sd),.sink_seal(d_seal),.applied_hbm(d_applied),.boot_fault_hbm(d_bfh),.boot_fault_core(d_bfc));
 qkd_kv_grp_ctl #(.MUT(0)) ref_(.ck(ck),.rst_n(r_rst_n),.hck(hck),.hrst_n(hrst_n),
  .ctrl_go(r_cg),.kgo(r_kg),.vgo(r_vg),.ctx_t(r_ctx),.epoch(r_ep),.layer(r_layer),
  .ctrl_go_h(ch),.kgo_h(kh),.vgo_h(vh),.ctx_t_h(cth),.epoch_h(eph),.layer_h(lh),
  .ph_fault_core(fc),.ph_idle_core(ic),.ph_fault_hbm(fh),.ph_idle_hbm(ih),
  .ctrl_idle_core(r_ci),.ring_idle_core(r_ri),.ctrl_idle_hbm(r_chi),.front_idle_hbm(r_fhi),.ring_idle_hbm(r_rhi),
  .ctrl_fault_core(4'd0),.ctrl_completion_fault_core(4'd0),.ctrl_intake_fault_core(4'd0),.ring_fault_core(4'd0),
  .ctrl_fault_hbm(r_fhbm),.ctrl_output_fault_hbm(4'd0),.ctrl_calendar_fault_hbm(4'd0),.ring_fault_hbm(4'd0),
  .front_fault_overflow_hbm(4'd0),.front_fault_go_hbm(4'd0),.front_hold_hbm(4'd0),
  .upstream_quiet(r_uq),.upstream_fault(r_uf),.drained(drained),.drain_fault(dfault),
  .cfg_we(r_we),.cfg_addr(r_addr),.cfg_data(r_data),.cfg_last(r_last),
  .sink_we(sw),.sink_addr(sa),.sink_data(sd),.sink_seal(seal),.applied_hbm(applied),.boot_fault_hbm(bfh),.boot_fault_core(bfc));

 wire d_ch,d_kh,d_vh,d_fc,d_fh,d_ic,d_ih,d_drained,d_dfault;wire[13:0]d_cth;wire[15:0]d_eph;wire[5:0]d_lh;
 wire [4:0] d_sw,d_seal,d_applied,d_bfh,d_bfc; wire [39:0] d_sa; wire [319:0] d_sd;
 // one-ck-edge delay line of every core-domain input (sampled at posedge, re-driven at the next negedge)
 reg p_rst_n=0,r_rst_n=0,p_cg=0,r_cg=0,p_kg=0,r_kg=0,p_vg=0,r_vg=0;reg[13:0]p_ctx=1,r_ctx=1;reg[15:0]p_ep=0,r_ep=0;reg[5:0]p_layer=0,r_layer=0;
 reg[3:0]p_ci=4'hf,r_ci=4'hf,p_ri=4'hf,r_ri=4'hf,p_chi=4'hf,r_chi=4'hf,p_fhi=4'hf,r_fhi=4'hf,p_rhi=4'hf,r_rhi=4'hf,p_fhbm=0,r_fhbm=0;
 reg p_uq=0,r_uq=0,p_uf=0,r_uf=0;reg[4:0]p_we=0,r_we=0,p_last=0,r_last=0;reg[39:0]p_addr=0,r_addr=0;reg[319:0]p_data=0,r_data=0;
 always @(posedge ck)begin p_rst_n<=rst_n;p_cg<=cg;p_kg<=kg;p_vg<=vg;p_ctx<=ctx;p_ep<=ep;p_layer<=layer;p_ci<=ci;p_ri<=ri;
  p_chi<=chi;p_fhi<=fhi;p_rhi<=rhi;p_fhbm<=fhbm;p_uq<=uq;p_uf<=uf;p_we<=we;p_last<=last;p_addr<=addr;p_data<=data;end
 always @(negedge ck)begin r_rst_n<=p_rst_n;r_cg<=p_cg;r_kg<=p_kg;r_vg<=p_vg;r_ctx<=p_ctx;r_ep<=p_ep;r_layer<=p_layer;r_ci<=p_ci;r_ri<=p_ri;
  r_chi<=p_chi;r_fhi<=p_fhi;r_rhi<=p_rhi;r_fhbm<=p_fhbm;r_uq<=p_uq;r_uf<=p_uf;r_we<=p_we;r_last<=p_last;r_addr<=p_addr;r_data<=p_data;end
 // cycle-exact comparison of every output after both resets are released
 integer cmp_ck=0,cmp_hck=0;reg cmp_on=0;
 wire [431:0] o_ref={ch,kh,vh,cth,eph,lh,fc,fh,ic,ih,drained,dfault,sw,sa,sd,seal,applied,bfh,bfc};
 wire [431:0] o_dut={d_ch,d_kh,d_vh,d_cth,d_eph,d_lh,d_fc,d_fh,d_ic,d_ih,d_drained,d_dfault,d_sw,d_sa,d_sd,d_seal,d_applied,d_bfh,d_bfc};
 always @(posedge ck)begin #2;if(cmp_on)begin cmp_ck=cmp_ck+1;if(o_dut!==o_ref)begin
  $display("GRP_CTL_P FAIL dut != ref at ck edge %0d (core_i %0d) diff %h MUT=%0d",cmp_ck,core_i,o_dut^o_ref,MUT);$fatal(1,"GRP_CTL_P FAIL");end end end
 always @(posedge hck)begin #2;if(cmp_on)begin cmp_hck=cmp_hck+1;if(o_dut!==o_ref)begin
  $display("GRP_CTL_P FAIL dut != ref at hck edge %0d diff %h MUT=%0d",cmp_hck,o_dut^o_ref,MUT);$fatal(1,"GRP_CTL_P FAIL");end end end
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
   @(negedge ck);toggle_i=core_i+3;
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
  repeat(4)tick();@(negedge ck);rst_n=1;tick();@(negedge ck);hrst_n=1;repeat(3)tick();cmp_on=1;repeat(16)tick();
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
  found=0;while(!found)begin @(negedge ck);ti=core_i+3;gap=768-(((ti-6)*625)%768);found=gap<200||gap>600;end
  cg=1;tick();@(negedge ck);cg=0;repeat(10)tick();
  if(!fc)$fatal(1,"unsafe phase accepted without explicit fault");
  if(received!=scheduled)$fatal(1,"unsafe phase was dynamically deferred");
  $display("GRP_CTL_P PASS dut == ref (one ck edge later) on %0d ck / %0d hck edges; ref: boot 5x32 words (4 sealed), phase 36 packets/%0d HBM events, drain+fault, unsafe abort MUT=%0d",cmp_ck,cmp_hck,received,MUT);$finish;
 end
 initial begin #20000000;$fatal(1,"timeout");end
endmodule
