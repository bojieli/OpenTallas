`timescale 1ns/1fs
module tb_causal;
reg ck=0;always #0.416500 ck=~ck;reg rst_n=0;
reg[115:0]cmd=0,rcmd=0;reg wv=0,tv=0;reg[1:0]tk=0;reg[23:0]wa=0,ta=0;
reg[511:0]wd=0;reg[1023:0]td=0;
reg[1023:0]pairs[0:11][0:3],r1pairs[0:11][0:3],prog[0:0][0:3],gains[0:0][0:23];reg[31:0]gold[0:0][0:383];
integer s,u,j,l,k,phase=0,count=0,total=0,n,tag,gotroot=0,partials=0,cyc=0,cfgcyc,rootcyc;
reg[31:0]tags=0;reg[383:0]seen=0;reg[31:0]expected,actual;reg[23:0]oa;
wire rwe;wire[23:0]rwa;wire[31:0]rwd;wire[100:0]scfg;wire busy,sfault;
qfd_dv_s8_flat dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
wire drop=$test$plusargs("MUT_DROP_PARTIAL")&&dut.red_addr[4:0]==31;
native_root_component root(.ck(ck),.rst_n(rst_n),.cmd_i(rcmd),.red_we(dut.red_we&&!drop),.red_addr(dut.red_addr),.red_data(dut.red_data),.am_chain(48'd0),
.sc_cfg(scfg),.sc_busy(busy),.sc_fault(sfault),.w1_we(rwe),.w1_addr(rwa),.w1_data(rwd));
function automatic[115:0] rootcfg(input integer user);
 rootcfg=116'd7|(116'd1<<4)|(116'd32<<5)|(116'(384+4096*user)<<11)|(116'd1<<35)|
 (116'(400+4096*user)<<36)|(116'h358637bd<<60)|(116'd12<<92)|(116'd6<<97);
endfunction
initial begin
 force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;
 force dut.tw_we=tv;force dut.tw_kind=tk;force dut.tw_addr=ta;force dut.tw_data=td;
 force dut.w1_we=rwe&&!$test$plusargs("MUT_DROP_RSTD");force dut.w1_addr=rwa;force dut.w1_data=rwd;
 // INITIALIZERS
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 rcmd=116'd15;@(negedge ck);rcmd=0;repeat(64)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  tags=0;partials=0;gotroot=0;rcmd=rootcfg(u);@(negedge ck);rcmd=0;
  repeat(64)@(negedge ck);if(!scfg[100]&&sfault)$fatal(1,"ROOT_CONFIG_FAULT");
  for(s=0;s<12;s=s+1)begin
   n=(s<8)?384:256;
   for(j=0;j<n;j=j+16)begin
    wv=1;wa=24'(4096*u+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h41800000+32'(u*8388608);@(negedge ck);
    wa=24'(4096*u+416+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h41000000+32'(u*8388608);@(negedge ck);
   end
   wv=0;tv=1;tk=1;
   for(j=0;j<n/16;j=j+1)begin
    ta=24'(128*u+j);for(l=0;l<16;l=l+1)td[64*l+:64]=64'h3f800000;@(negedge ck);
    ta=24'(128*u+24+j);for(l=0;l<16;l=l+1)td[64*l+:64]=64'h40000000;@(negedge ck);
   end
   tk=3;ta=24'(64*u);td=r1pairs[s][u];@(negedge ck);ta=24'(64*u+1);td=pairs[s][u];@(negedge ck);tv=0;repeat(32)@(negedge ck);
   count=0;seen=0;phase=1;
   cmd=(116'(2+128*u)<<4)|116'd3;
   if($test$plusargs("MUT_OLD_CALLER"))begin
    // Actual row0 is loaded with the selected residual1 half; dispatch instruction1.
    cmd=(116'(1+128*u)<<4)|116'd3;
   end
   @(negedge ck);cmd=0;repeat(1024)@(negedge ck);phase=0;
   if(count!=n)$fatal(1,"RESIDUAL_COVERAGE s%0d u%0d count%0d",s,u,count);
  end
  if(tags!==32'hffffffff||partials!=32)$fatal(1,"ROOT_TAG_COVERAGE %h %0d",tags,partials);
  repeat(1024)@(negedge ck);
  if(gotroot!=1||busy||sfault)$fatal(1,"ROOT_COMPLETION user%0d count%0d busy%b fault%b",u,gotroot,busy,sfault);
  // Final slice11 residual is still in its real VM. Only gain/program tables are written now.
  tv=1;tk=1;
  for(j=0;j<16;j=j+1)begin ta=24'(128*u+68+j);td=gains[0][j];@(negedge ck);end
  tk=3;ta=24'(64*u+8);td=prog[0][u];@(negedge ck);tv=0;repeat(32)@(negedge ck);
  count=0;seen=0;phase=2;cmd=(116'(16+128*u)<<4)|116'd3;@(negedge ck);cmd=0;repeat(512)@(negedge ck);phase=0;
  if(count!=256||dut.su_fault||dut.vm_fault||dut.red_fault)$fatal(1,"CAUSAL_HEAD_COVERAGE user%0d count%0d",u,count);
  $display("CAUSAL_USER_PASS user%0d native_residual4096 native_partials32 ROOTbits%h native_HEAD256 cfg_to_return%0d",u,rwd,rootcyc-cfgcyc);
 end
 if(total!=1024)$fatal(1,"HEAD_TOTAL");
 $display("NATIVE_CAUSAL_RES2_ROOT_HEAD_PASS users4 contexts48 residual16384 partials128 ROOT4 HEAD1024 period833ps component_wires_only");$finish;
end
always @(negedge ck)if(rst_n)begin
 cyc=cyc+1;
 if(scfg[100])cfgcyc=cyc;
 if(dut.red_we)begin
  tag=integer'(dut.red_addr&24'h3fffff);
  if(dut.red_addr[23:22]!==2'b11||tag<0||tag>31||tags[tag])$fatal(1,"NATIVE_PARTIAL_TAG %h",dut.red_addr);
  expected=32'h48000000+32'(u*16777216); // 128*(32*2^u)^2
  if(dut.red_data!==expected)$fatal(1,"NATIVE_PARTIAL_VALUE u%0d tag%0d got%h expected%h",u,tag,dut.red_data,expected);
  tags[tag]=1;partials=partials+1;
 end
 if(rwe)begin
  expected=ROOT_GOLD_BASE-32'(u*8388608);
  if(rwa!==24'(400+4096*u)||rwd!==expected)$fatal(1,"NATIVE_ROOT_RETURN u%0d addr%h got%h expected%h",u,rwa,rwd,expected);
  gotroot=gotroot+1;rootcyc=cyc;
 end
 if(phase!=0)for(k=0;k<8;k=k+1)if(dut.L_vm_we[k])begin
  oa=dut.L_vm_waddr[24*k+:24];actual=dut.L_vm_wdata[32*k+:32];
  if(phase==1)begin
   j=integer'(oa)-4096*u;expected=32'h42000000+32'(u*8388608);
  end else begin
   j=(integer'(oa)-4194304)/1536*128+(integer'(oa)-4194304)%128;
   if(oa[23:22]!==2'b01||(integer'(oa)-4194304)/128%12!=11)$fatal(1,"HEAD_ADDRESS %h",oa);
   expected=gold[0][j];
  end
  if(j<0||j>=((phase==1)?n:256)||seen[j]||actual!==expected)$fatal(1,"CAUSAL_VALUE phase%0d s%0d u%0d j%0d got%h expected%h",phase,s,u,j,actual,expected);
  seen[j]=1;count=count+1;if(phase==2)total=total+1;
 end
end
endmodule
