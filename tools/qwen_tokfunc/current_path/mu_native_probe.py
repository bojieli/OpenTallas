from pathlib import Path
import argparse,json,re,hashlib
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--flat',type=Path,required=True);p.add_argument('--closure',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
m=json.loads(a.manifest.read_text());s=m['stages'][0]['slices'][0]
assert m['stages'][0]['stage']==1 and s['slice']==0
pairs=[]
for u in range(4):
 r=next(x for x in s['prog_users'][u] if x['addr']==5);pairs.append(int(r['payload_hex'],16))
ports=re.findall(r'input\s+wire(?:\s*\[[^]]+\])?\s+(\w+)',a.flat.read_text().split(');',1)[0]);signals={'ck':'ck','rst_n':'rst_n','cmd_i':'cmd'}
conn=','.join('.%s(%s)'%(n,signals.get(n,"'0")) for n in ports)
sv='''`timescale 1ns/1fs
module tb_mu_native;
reg ck=0;always #0.416500 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;
reg wv=0,tv=0;reg[23:0]wa=0,ta=0;reg[511:0]wd=0;reg[1023:0]td=0;
reg[1023:0]pairs[0:3];integer u,j,l,k,active=-1,count=0,checks=0;reg[127:0]seen=0;reg[23:0]out_a;reg[31:0]out_d,expected;
qfd_dv_s8_flat dut (CONNECTIONS);
initial begin
 force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;
 force dut.tw_we=tv;force dut.tw_kind=2'd3;force dut.tw_addr=ta;force dut.tw_data=td;
 PAIRS
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  for(j=0;j<128;j=j+16)begin
   wv=1;wa=24'(1344+4096*u+j);
   for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h3f000000|(32'(u)<<16)|32'(j+l);
   if($test$plusargs("MUT_PAYLOAD")&&u==1&&j==0)wd[3*32+3]=~wd[3*32+3];
   @(negedge ck);
  end
  wv=0;tv=1;ta=24'(5+64*u);td=pairs[u];
  if($test$plusargs("MUT_BANK")&&u==1)td[512+:457]=pairs[0][512+:457];
  @(negedge ck);tv=0;repeat(32)@(negedge ck);
 end
 repeat(64)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  active=u;seen=0;count=0;
  cmd=(116'(11+128*u)<<4)|116'd3;
  if($test$plusargs("MUT_PIDX")&&u==1)cmd=(116'd11<<4)|116'd3;
  @(negedge ck);cmd=0;
  repeat(300)@(negedge ck);
  if(count!=128||seen!=={128{1'b1}})$fatal(1,"MU_COVERAGE user=%0d count=%0d seen=%h idle=%b sufault=%b vmfault=%b",u,count,seen,dut.su_idle,dut.su_fault,dut.vm_fault);
  if(dut.su_fault||dut.vm_fault)$fatal(1,"MU_NATIVE_FAULT user=%0d",u);
  $display("MU_USER_PASS user=%0d writes=%0d",u,count);active=-1;
 end
 $display("MU_NATIVE_XA_PASS users4 literalwords512 checks=%0d precision1fs period833ps MEMALIGN3 MIF0",checks);$finish;
end
always @(negedge ck)begin
 if(rst_n&&active>=0)begin
  for(k=0;k<8;k=k+1)if(dut.L_vm_we[k])begin
   out_a=dut.L_vm_waddr[24*k+:24];out_d=dut.L_vm_wdata[32*k+:32];
   if(out_a[23:22]!=2'd1||out_a[21:0]>=128)$fatal(1,"MU_DEST_MISMATCH user%0d addr%h",active,out_a);
   j=integer'(out_a[21:0]);expected=32'h3f000000|(32'(active)<<16)|32'(j);
   if(out_d!==expected||seen[j])$fatal(1,"MU_PAYLOAD_MISMATCH user%0d index%0d got%h expected%h duplicate%b",active,j,out_d,expected,seen[j]);
   seen[j]=1;count=count+1;checks=checks+1;
  end
 end
end
endmodule
'''.replace('CONNECTIONS',conn).replace('PAIRS','\n '.join("pairs[%d]=1024'h%0256x;"%(u,v) for u,v in enumerate(pairs)))
(a.out/'tb_mu_native.sv').write_text(sv)
files=[str((a.closure/line).resolve()) for line in (a.closure/'files.f').read_text().splitlines()]
files.append(str(a.flat.resolve()));files.append(str((a.out/'tb_mu_native.sv').resolve()))
(a.out/'source.f').write_text('\n'.join(files)+'\n')
(a.out/'source.json').write_text(json.dumps(dict(manifest=str(a.manifest),manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),flat_sha256=hashlib.sha256(a.flat.read_bytes()).hexdigest(),stage=1,slice=0,instruction=11,fixture='native tw/w16 preload pins via bench force, native cmd_i execution, actual native S8 SU/VM/eightheads; excludes controller/globalcalendar'),indent=2)+'\n')
# Smallest actual SU/VM/eight-head composition: discard the unused station,
# stream and XS-fabric portion of the flat parent. Their idle status inputs
# are explicit fixture constants; copied native SU/head instances are intact.
original=a.flat.read_text();prefix=original.split('    qfd_dv_s5_sc2_leaf u_sc',1)[0]
assert prefix!=original and prefix.count('qfd_dv_lane_h_safe2 #(')==8
# Keep only the active native SU/VM/lane/SFU composition. The unrelated
# gate-mapped reducer/control blocks made GCC PCH compilation unbounded.
inst=re.compile(r'^    (\w+)\b(?:(?!;).)*?\b(u_\w+)\s*\(.*?;\n',re.M|re.S)
kept=[];removed=[]
def select(m):
 name=m.group(2)
 if name=='u_suvm' or re.fullmatch(r'u_(?:lrly|head|exp|rcp|rsq)[0-7]',name):
  kept.append(name);return m.group(0)
 removed.append(name);return ''
prefix=inst.sub(select,prefix)
assert len(kept)==41,(kept,removed)
projection=prefix+'''\n    // Fixture adapter at the native SU command/table/write interfaces.
    assign su_cmd={cmd_i[0] && cmd_i[3:1]==3'd1,cmd_i[12:4]};
    assign rp_tw_we=tw_we,rp_tw_kind=tw_kind,rp_tw_addr=tw_addr,rp_tw_data=tw_data;
    assign rd_v=0,red_busy=0,red_fault=0,red_we=0,red_addr=0,red_data=0;
    assign fch0=0,fch1=0,fch2=0,fch3=0,tap_fault=0;
    assign stm_fault=0,tld_fault=0,sc_busy=0,sc_fault=0;
    assign sc_w1_we=0,sc_w1_addr=0,sc_w1_data=0;
    assign tok_v=0,tok_own=0,tok_idx=0,tok_val=0,tok_user=0;
    assign rv0=0,ri0=0,rl0=0,r_d0=0,r_d1=0,r_d2=0,r_d3=0,r_d4=0,r_d5=0,r_d6=0,r_d7=0;
    assign oc0=0,fl0=0;
endmodule\n'''
projected=a.out/'native_su_component.sv';projected.write_text(projection)
# Read only transitive selected files. Verilator otherwise parses the entire
# 116MB whole-QC closure before discarding unrelated column/HEAD bodies.
paths=[Path(x) for x in files[:-2]]+[projected]
clean={};modules={}
for path in paths:
 txt=path.read_text();txt=re.sub(r'/\*.*?\*/|//[^\n]*',' ',txt,flags=re.S);clean[path]=txt
 for name in re.findall(r'\bmodule\s+(\w+)',txt):modules.setdefault(name,path)
selected=set();todo=[projected]
while todo:
 path=todo.pop()
 if path in selected:continue
 selected.add(path)
 for name in set(re.findall(r'\b[A-Za-z_]\w*\b',clean[path]))&modules.keys():
  dep=modules[name]
  if dep not in selected:todo.append(dep)
ordered=[path for path in paths if path in selected]
(a.out/'source.f').write_text('\n'.join(str(x) for x in ordered+[a.out/'tb_mu_native.sv'])+'\n')
p=a.out/'tb_mu_native.sv';sv=p.read_text().replace('repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);','repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);\n cmd=116\'d15;@(negedge ck);cmd=0;repeat(16)@(negedge ck);');p.write_text(sv)
p=a.out/'source.json';doc=json.loads(p.read_text());doc.update(projection='exact native SU/VM plus eight head/lane/SFU instances; native SU command adapter; inactive reduction/CTL/stream/XS planes excluded',selected_files=len(ordered),selected_bytes=sum(x.stat().st_size for x in ordered),native_su_heads=8,kept_instances=kept,excluded_instances=removed,projection_sha256=hashlib.sha256(projection.encode()).hexdigest());p.write_text(json.dumps(doc,indent=2)+'\n')
