from pathlib import Path
import re
import json,sys,argparse,hashlib
p=argparse.ArgumentParser();p.add_argument('--programme',type=Path,required=True);p.add_argument('--bound',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--capture-stage',type=int,choices=(0,1),default=1);p.add_argument('--local-ctrl',type=int,choices=(0,1),default=1);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(a.programme/'src/tools/qwen_layerbench'));import programme_store as P
manifest=a.programme/'rank0/lowered/mu_table_input.json';m=json.loads(manifest.read_text());images=P.logical_images(m);masks=a.programme/'rank0/masks'
counts=[]
for sl in (0,1):
 records=[];ncase=[]
 for stage in (1,36):
  for u in range(4):
   n=0
   for addr in P.read_rows(stage,u):
    w=images[sl][addr]
    if not(w>>1024)&1:continue
    kind=(w>>1025)&3;local=w>>1027;off=(0,272,344,416)[u] if kind==2 else u*(64 if kind==3 else 128)
    packed=(w&((1<<1024)-1))|((local+off)<<1024)|(kind<<1048)
    records.append(f'{packed:0263x}\n');n+=1
   ncase.append(n)
 assert len(set(ncase))==1
 counts.append(ncase[0]);(a.out/f'expected{sl}.hex').write_text(''.join(records))
defparams=[]
for sl in (0,1):
 for k in range(4):defparams.append(f'defparam u{sl}.m{k}.VIAMAP="{masks}/table_s{sl}_m{k}.viamap.hex";')
sv='''`timescale 1ns/1fs
module tb_table_alias;
reg ck=0;always #0.4165 ck=~ck;reg rst_n=0,start=0;reg[5:0]stage=1;reg[1:0]user_id=0;
wire[1:0]we,busy,done,fault;wire[1:0]kind[0:1];wire[23:0]addr[0:1];wire[1023:0]data[0:1];
reg[1049:0]expected0[0:TOTAL0-1],expected1[0:TOTAL1-1];integer count0=0,count1=0,caseno=0,st,u,cycles=0,checks=0;
qfd_dv_table_rom_loader #(.SLICE(0),.BTAB_COMPACT(1),.CAPTURE_STAGE(1),.LOCAL_CTRL(1),.WE_COPIES(67)) u0(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[0]),.tw_kind(kind[0]),.tw_addr(addr[0]),.tw_data(data[0]),.busy(busy[0]),.done(done[0]),.fault(fault[0]));
qfd_dv_table_rom_loader #(.SLICE(0),.BTAB_COMPACT(1),.CAPTURE_STAGE(1),.LOCAL_CTRL(1),.WE_COPIES(67)) u1(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we[1]),.tw_kind(kind[1]),.tw_addr(addr[1]),.tw_data(data[1]),.busy(busy[1]),.done(done[1]),.fault(fault[1]));
DEFPARAMS
initial begin
 $readmemh("EXPECTED0",expected0);$readmemh("EXPECTED1",expected1);
 #0.001;
 if($test$plusargs("MUT_ALIAS"))begin ALIAS_READS end
 if($test$plusargs("MUT_PAYLOAD"))u1.m0.arr[0][0]=~u1.m0.arr[0][0];
 repeat(32)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);
 for(st=0;st<2;st=st+1)for(u=0;u<4;u=u+1)begin
  stage=(st==0)?6'd1:6'd36;user_id=2'(u);count0=0;count1=0;start=1;
  @(negedge ck);start=0;repeat(128)@(negedge ck);
  if(count0!=COUNT0||count1!=COUNT1||fault!=0)$fatal(1,"TABLE_COVERAGE case%0d count%0d/%0d fault%b",caseno,count0,count1,fault);
  $display("TABLE_CASE_PASS stage%0d user%0d writes%0d/%0d",stage,user_id,count0,count1);caseno=caseno+1;
 end
 $display("TABLE_ALIAS_PASS bothSLICE0 distinctphysicalmasks stage1and36 fourusers checks%0d period833ps",checks);$finish;
end
always @(negedge ck)begin
 cycles=cycles+1;
 if(rst_n)begin
  if(we[0])begin
   if(count0==0)$display("TABLE_FIRST got=%h expected=%h",{kind[0],addr[0],data[0]},expected0[caseno*COUNT0+count0]);
   if({kind[0],addr[0],data[0]}!==expected0[caseno*COUNT0+count0])$fatal(1,"TABLE_PAYLOAD_MISMATCH loader0 case%0d index%0d",caseno,count0);
   count0=count0+1;checks=checks+1;
  end
  if(we[1])begin
   if({kind[1],addr[1],data[1]}!==expected1[caseno*COUNT1+count1])$fatal(1,"TABLE_PAYLOAD_MISMATCH loader1 case%0d index%0d",caseno,count1);
   count1=count1+1;checks=checks+1;
  end
 end
end
endmodule
'''
for old,new in [('TOTAL0',str(counts[0]*8)),('TOTAL1',str(counts[1]*8)),('COUNT0',str(counts[0])),('COUNT1',str(counts[1])),('DEFPARAMS','\n'.join(defparams)),('EXPECTED0',str(a.out/'expected0.hex')),('EXPECTED1',str(a.out/'expected1.hex')),('ALIAS_READS','\n'.join(f'$readmemh("{masks}/table_s0_m{k}.viamap.hex",u1.m{k}.arr);' for k in range(4)))]:sv=sv.replace(old,new)
sv=sv.replace('.CAPTURE_STAGE(1)',f'.CAPTURE_STAGE({a.capture_stage})').replace('.LOCAL_CTRL(1)',f'.LOCAL_CTRL({a.local_ctrl})')
(a.out/'tb_table_alias.sv').write_text(sv)
names=json.loads((a.bound/'bind_names.json').read_text());mapping=[]
for key,val in names.items():
 match=__import__('re').fullmatch(r'dvs_([WE])(\d)\.u_core\.u_sub\.u_stm',val)
 if not match:continue
 side,n=match[1],int(match[2]);sl=5-n if side=='W' else 6+n
 for k in range(4):mapping.append((sl,k,f'defparam tb_qcdie.u_qc.{key}.u_tload.u_ld.m{k}.VIAMAP="{masks}/table_s{sl}_m{k}.viamap.hex";'))
assert len(mapping)==48 and len({(s,k) for s,k,_ in mapping})==48
(a.out/'qc_table_viamap.svh').write_text('// Actual bound slice identity to mask filename only; numeric SLICE unchanged. Do not use global OT_ROM_DIR.\n'+'\n'.join(v for _,_,v in sorted(mapping))+'\n')
(a.out/'mapping.json').write_text(json.dumps(dict(bound=str(a.bound),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),instances=48,slices=12,numeric_slice_unchanged=True,btab_layout=[0,272,344,416],scope='Simulation filename mapping; not physical/canonical parameter adoption or programme execution'),indent=2)+'\n')
# Shared parents retain SLICE0; file identities are scoped initializer data.
import table_roms as T
p=a.out/'tb_table_alias.sv';text=p.read_text();text=re.sub(r'^defparam .*\n','',text,flags=re.M);p.write_text(text)
cases=T.bindings(a.bound,['tb_qcdie.u_qc','tb_kvslice.u_qc'])
for sl in (0,1):
 for k in range(4):cases[f'tb_table_alias.u{sl}.m{k}']=f'table_s{sl}_m{k}.viamap.hex'
base=a.bound.parent/'stage1/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v'
(a.out/'sim_ot_rom_4096x266_table.v').write_text(T.namespace(base,cases))
(a.out/'qc_table_viamap.svh').write_text('// UNQUALIFIED: nested defparams collapse shared parent specializations. Use the scoped initialization namespace.\n')
d=json.loads((a.out/'mapping.json').read_text());d.update(CAPTURE_STAGE=a.capture_stage,LOCAL_CTRL=a.local_ctrl,runtime_plusarg='OT_QC_TABLE_ROM_DIR',instance_scope_cases=cases,deep_defparams_qualified=False)
(a.out/'mapping.json').write_text(json.dumps(d,indent=2)+'\n')
