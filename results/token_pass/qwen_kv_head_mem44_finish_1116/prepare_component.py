from pathlib import Path
import json,shutil,importlib.util,hashlib,sys
import numpy as np
B=Path(__file__).resolve().parent;O=Path(sys.argv[1]);O.mkdir();(O/'input').mkdir()
for p in (B/'input').iterdir():
 if p.name!='tb.sv':shutil.copy2(p,O/'input'/p.name)
spec=importlib.util.spec_from_file_location('G',B/'hdc_golden.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
stage_path=B/'kv_finish_stage1_source1116.json';S=json.loads(stage_path.read_text())['stage']['slices']
f=lambda w,l,n:(w>>l)&((1<<n)-1)
pg=[];expected=[];initial=[];scalars=[];crom=[];cases=[]
for logical in [0,7]:
 for pos in [0,16,8191]:
  cid=len(cases);s=S[8];ws={2*r['addr']+h:(int(r['payload_hex'],16)>>(512*h))&((1<<457)-1)for r in s['prog_users'][0]for h in [0,1]}
  progs=[ws[i]for i in range(4,9)]+[int(S[10]['prog_users'][0][2]['payload_hex'],16)&((1<<457)-1)];pg.extend(f'{w:0128x}'for w in progs)
  x=np.array([(-1 if i%7==0 else 1)*2.**((i*3+pos)%5-2)for i in range(128)],dtype=np.float32)
  y=G.mul(x,np.float32(.5));r=G.reduce_chunked(G.mul(y,y));rsq=G.rsqrt(G.add(G.mul(r,np.float32(1/128)),G.from_bits(np.uint32(0x358637bd))))
  cr={r['addr']:int(r['payload_hex'],16)for r in s['crom']};gains=np.array([G.from_bits(np.uint32(f(cr[56+i//16],(i%16)*64,32)))for i in range(128)],dtype=np.float32)
  norm=G.mul(G.mul(y,rsq),gains);cos,sin,h=G.rope_tables(pos,128,1000000);kv=G.to_fp8(G.rope(norm,cos,sin,h));vv=G.to_fp8(y)
  for op in range(6):
   vals=y if op==0 else np.array([rsq])if op==1 else norm if op==2 else kv[:64]if op==3 else kv[64:]if op==4 else vv
   expected.extend(f'{int(G.bits(vals[i]))if i<len(vals)else 0:08x}'for i in range(128))
  initial.extend(f'{int(G.bits(v)):08x}'for v in x);scalars.extend([f'{int(G.bits(r)):08x}',f'{int(G.bits(rsq)):08x}'])
  for j in range(4):cr[64+j]=sum((int(G.bits(cos[16*j+i]))|(int(G.bits(sin[16*j+i]))<<32))<<(64*i)for i in range(16))
  crom.extend(f'{cr.get(j,0):0256x}'for j in range(68));cases.append(dict(case=cid,logical_head=logical,position=pos))
for name,data in [('program.hex',pg),('expected.hex',expected),('input.hex',initial),('scalar.hex',scalars),('crom.hex',crom)]: (O/name).write_text('\n'.join(data)+'\n')
TB=r'''`timescale 1ns/1fs
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
'''
(O/'input/tb.sv').write_text(TB);(O/'source.f').write_text(''.join('input/'+p.name+'\n'for p in sorted((O/'input').iterdir())))
(O/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb -f source.f --Mdir obj >build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb >run.log 2>&1
grep -q KV_MEM44_FINISH_COMPONENT_PASS run.log
for mutant in BAD_REPLY BAD_GAIN;do
 set +e
 ./obj/Vtb +"$mutant" >"${mutant}.log" 2>&1
 rc=$?
 set -e
 test "$rc" != 0
 grep -Eq 'KV_FINISH_PAYLOAD|KV_FINISH_COUNT|KV_FINISH_ADDRESS' "${mutant}.log"
done
echo KV_MEM44_FINISH_MUTANTS_CAUGHT
''')
(O/'preparation.json').write_text(json.dumps(dict(scope='One actual native MEM44 HEAD; finite synthetic activations; checkpoint six K/V programmes/gains. External cross-lane reduction supplied by independent golden. No global/physical/real-activation claim.',profile=dict(MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=44,SEGMENTED_MEMORY_DELAY=1,KV_WR_PIPE=1,MIF=1),stage_sha256=hashlib.sha256(stage_path.read_bytes()).hexdigest(),cases=cases,files={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest()for p in O.rglob('*')if p.is_file()}),indent=2)+'\n')
print(O)
