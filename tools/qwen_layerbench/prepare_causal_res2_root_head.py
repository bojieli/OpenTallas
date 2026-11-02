#!/usr/bin/env python3
"""Build an isolated real RES2/reducer/ROOT/H component packet; never dispatch."""
import argparse,hashlib,json,re,shutil,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--base',type=Path,required=True);a=p.parse_args()
 base=a.base;out=a.out;out.mkdir();inp=out/'input';inp.mkdir()
 sys.path.insert(0,str(a.repo/'tools/qwen_layerbench'));import dv_lower as D
 m=json.loads((base/'mu_table_input.json').read_text())
 import residual2_calendar_candidate as R
 pair_checks=R.verify_native_pair(m)
 srcs=[];seen={};tags=[]
 def copy(src,name=None):
  name=name or src.name;blob=src.read_bytes();h=hashlib.sha256(blob).hexdigest()
  if name in seen:
   if seen[name]!=h:raise ValueError('different same-name source '+name)
   return
  seen[name]=h;t=inp/name;t.write_bytes(blob);srcs.append(t)
 for src in sorted((base/'native_res2_packet/gate1/input').glob('*')):
  if src.name=='tb_mu_native.sv':continue
  copy(src)
 # Add only real ROOT dependencies absent from SU packet; helpers share identical module names.
 existing='\n'.join(t.read_text() for t in srcs)
 names=set(re.findall(r'\bmodule\s+(\w+)',existing))
 for src in sorted((base/'root_prearm_packet1/src').glob('*.sv')):
  mods=set(re.findall(r'\bmodule\s+(\w+)',src.read_text()))
  if src.name=='tb_native_root.sv' or mods <= names:continue
  if mods&names:raise ValueError('partial module collision '+src.name)
  copy(src);names|=mods
 for name in ('qfd_dv_s5_red2_leaf.sv','qfd_dv_s5_red2_k79.sv','qfd_dv_s5_red2_k79_helpers.sv'):
  src=a.repo/'rtl/qwen_dv/s5'/name
  frozen={'qfd_dv_s5_red2_leaf.sv':'825eaf6a1a50517ba0796e9d8903654d4a97b7e4cb0442b28ba2f46fdcb77e64','qfd_dv_s5_red2_k79.sv':'e92a6764b9422924996e40b5d99469f8b75088f5925700f1fcad591722f050e4','qfd_dv_s5_red2_k79_helpers.sv':'f4acdc20e57a6c194e0bef662890fbd689e189caaf95d54881e62ac5ff23c1fd'}
  if hashlib.sha256(src.read_bytes()).hexdigest()!=frozen[name]:raise ValueError('not frozen821 reducer '+name)
  mods=set(re.findall(r'\bmodule\s+(\w+)',src.read_text()))
  if not mods<=names:copy(src);names|=mods
 comp=inp/'032_native_su_component.sv';s=comp.read_text();old='assign rd_v=0,red_busy=0,red_fault=0,red_we=0,red_addr=0,red_data=0;'
 assert s.count(old)==1
 s=s.replace(old,"""qfd_dv_s5_red2_leaf u_red(.ck(ck),.rst_n(rst_n),.l_ov(L_l_ov),.l_out(L_l_out),
 .l_red0(L_l_red[1:0]),.l_redsq0(L_l_redsq[0]),.l_last0(L_l_last[0]),.l_raddr0(L_l_raddr[23:0]),
 .red_we(red_we),.red_addr(red_addr),.red_data(red_data),.rd_v(rd_v),.busy(red_busy),.fault(red_fault));""");comp.write_text(s)
 init=[]
 for sl in m['stages'][0]['slices']:
  si=sl['slice']
  for u in range(4):
   payload=int(sl['prog_users'][u][1]['payload_hex'],16);f=D.su_unpack(payload&((1<<512)-1))
   if f['nout']!=(3 if si<8 else 2) or f['nin']!=128 or f['red']!=1 or f['redsq']!=1:raise ValueError('unexpected kernel')
   if u==0:tags.extend(f['rb']+i*f['rso'] for i in range(f['nout']))
   init.append(f"pairs[{si}][{u}]=1024'h{payload:0256x};")
   init.append(f"r1pairs[{si}][{u}]=1024'h{sl['prog_users'][u][0]['payload_hex']};")
 if sorted(tags)!=list(range(0xc00000,0xc00020)):raise ValueError('not exact32 ROOT tags')
 htb=(base/'native_head_packet3/input/tb_mu_native.sv').read_text()
 for line in htb.splitlines():
  if re.match(r'(prog|gains|gold)\[11\]',line):init.append(line.replace('[11]','[0]',1))
 tb=Path(__file__).with_name('native_causal_res2_root_head.sv').read_text().replace('// INITIALIZERS','\n'.join(init))
 (inp/'tb_causal.sv').write_text(tb);srcs.append(inp/'tb_causal.sv')
 (out/'source.f').write_text(''.join('input/'+t.name+'\n' for t in srcs))
 shutil.copy2(base/'native_res2_packet/gate1/defines.f',out/'defines.f')
 shutil.copy2(Path(__file__).with_name('run_causal_res2_root_head.sh'),out/'run_gate.sh')
 (out/'run_gate.sh').chmod(0o755)
 (out/'packet.sha256').write_text(''.join(hashlib.sha256(t.read_bytes()).hexdigest()+'  input/'+t.name+'\n' for t in srcs)+''.join(hashlib.sha256((out/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ('source.f','defines.f','run_gate.sh')))
 report=dict(status='PREP_ONLY',native_pair_checks=pair_checks,manifest_sha256=hashlib.sha256((base/'mu_table_input.json').read_bytes()).hexdigest(),native_root_tags=tags,files=len(srcs),bytes=sum(t.stat().st_size for t in srcs),scope='48 real residual/reducer contexts,32 unique ROOT tags/user,4 slice11 HEAD consumers; direct component wires, no production spatial/calendar claim')
 (out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
