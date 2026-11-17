`timescale 1ns/1fs
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;reg w16=0,w1=0,tw=0;reg[23:0]w16a=0,w1a=0,twa=0;
reg[511:0]w16d=0;reg[31:0]w1d=0;reg[1023:0]twd=0;reg[1:0]twk=0;reg[2:0]logical_head=0;reg bad_reply=0;
native_su_component #(.PROBE_MIF(1)) dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0),
.preload16_we(w16),.preload16_addr(w16a),.preload16_data(w16d),.preload1_we(w1),.preload1_addr(w1a),.preload1_data(w1d),.install_we(tw),.install_kind(twk),.install_addr(twa),.install_data(twd),.logical_head(logical_head),.bad_reply(bad_reply));
reg[511:0]programs[0:35];reg[31:0]gold[0:4607],xin[0:767],scalars[0:11];reg[1023:0]crom[0:407];
integer cid=0,op=0,active=0,count=0,retires=0,j,k,t,idx,actual_addr,base_addr,expect_count,cy=0,total=0;reg bad_gain=0;reg[127:0]seen;
always @(posedge ck)begin
 cy=cy+1;
 if(active)begin
  if(dut.h0_retire)retires=retires+1;
  if((op<3&&dut.L_vm_we[0])||(op>=3&&dut.L_kv_we[0]))begin
   actual_addr=op<3?dut.L_vm_waddr[23:0]:dut.L_kv_waddr[23:0];
   base_addr=op==0?800:op==1?944:op==2?960:op==3?4194304:op==4?4194368:8388608;idx=actual_addr-base_addr;
   if(idx<0||idx>=128||seen[idx])$fatal(1,"KV_FINISH_ADDRESS c%0d op%0d a%h idx%0d",cid,op,actual_addr,idx);
   if((op<3?dut.L_vm_wdata[31:0]:dut.L_kv_wdata[31:0])!==gold[(cid*6+op)*128+idx])$fatal(1,"KV_FINISH_PAYLOAD c%0d op%0d idx%0d got%08x expected%08x",cid,op,idx,op<3?dut.L_vm_wdata[31:0]:dut.L_kv_wdata[31:0],gold[(cid*6+op)*128+idx]);
   seen[idx]=1;count=count+1;
  end
 end
end
task automatic poke(input integer a,input[31:0]v);begin w1=1;w1a=a;w1d=v;@(negedge ck);w1=0;end endtask
initial begin
 $readmemh("program.hex",programs);$readmemh("expected.hex",gold);$readmemh("input.hex",xin);$readmemh("scalar.hex",scalars);$readmemh("crom.hex",crom);
 bad_reply=$test$plusargs("BAD_REPLY");bad_gain=$test$plusargs("BAD_GAIN");
 for(cid=0;cid<6;cid=cid+1)begin
  active=0;cmd=0;w16=0;w1=0;tw=0;rst_n=0;repeat(64)@(negedge ck);logical_head=cid<3?0:7;rst_n=1;repeat(512)@(negedge ck);
  for(j=0;j<128;j=j+16)begin w16=1;w16a=800+j;for(k=0;k<16;k=k+1)w16d[32*k+:32]=xin[cid*128+j+k];@(negedge ck);end
  w16=0;poke(400,32'h3f000000);tw=1;twk=3;
  for(j=0;j<3;j=j+1)begin twa=j;twd={programs[cid*6+2*j+1],programs[cid*6+2*j]};@(negedge ck);end
  twk=1;for(j=0;j<68;j=j+1)begin twa=j;twd=crom[cid*68+j];if(bad_gain&&j==56)twd=twd^1024'h800000;@(negedge ck);end
  tw=0;repeat(128)@(negedge ck);
  for(op=0;op<6;op=op+1)begin
   // This component injects only cross-lane reduction from the independent golden.
   if(op==1)begin poke(928,scalars[2*cid]);repeat(32)@(negedge ck);end
   if(op==2&&logical_head!=0)begin poke(944,scalars[2*cid+1]);repeat(32)@(negedge ck);end
   if(op==5)begin for(j=0;j<128;j=j+16)begin w16=1;w16a=800+j;for(k=0;k<16;k=k+1)w16d[32*k+:32]=xin[cid*128+j+k];@(negedge ck);end w16=0;repeat(32)@(negedge ck);end
   if(op==1&&logical_head!=0)continue;
   count=0;retires=0;seen=0;active=1;cmd=(116'(op)<<4)|116'd3;@(negedge ck);cmd=0;expect_count=op==1?1:(op==3||op==4)?8:16;
   for(t=0;t<768;t=t+1)begin @(negedge ck);if(count==expect_count&&retires==expect_count&&dut.su_idle&&dut.u_suvm.u_su8.ready&&dut.u_suvm.u_su8.inflight==0)break;end
   if(count!=expect_count||retires!=expect_count||dut.su_fault||dut.vm_fault)$fatal(1,"KV_FINISH_COUNT c%0d op%0d words%0d retire%0d fault%0b/%0b",cid,op,count,retires,dut.su_fault,dut.vm_fault);
   $display("KV_FINISH_CASE c%0d op%0d head%0d words%0d cycles%0d",cid,op,logical_head,count,t);total=total+count;active=0;repeat(32)@(negedge ck);
  end
 end
 $display("KV_MEM44_FINISH_COMPONENT_PASS cases6 programmes33 words%0d SYNTHETIC_ACTIVATIONS CHECKPOINT_GAINS SOFTWARE_CROSSLANE_REDUCTION",total);$finish;
end
endmodule
