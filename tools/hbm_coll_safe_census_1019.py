#!/usr/bin/env python3
"""Exact release-shape SAFE-delay source census; execute synthesis only on fleet."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
SRC=['rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_hard_v5.sv','rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ctl_v5.sv','rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_fixed_delay_sram.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/lib/ot_rst_relay.sv']
BB=['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v','physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v']
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--shape',choices=['n1s0','n2s1'],required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--safephys',action='store_true');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 src=SRC if not a.safephys else ['rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ctl_release_safephys.sv','rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ctl_v5_safephys.sv','rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_fixed_delay_sram_safephys.sv']+SRC[3:]
 top='ot_hgi_coll_ctl_v5r_'+a.shape+('_safephys' if a.safephys else '');ys='read_verilog -defer -sv -D SYNTHESIS '+' '.join(src)+'\nread_verilog -lib -sv '+' '.join(BB)+'\nchparam -set VM_RT 74 -set SAFE_DELAY 1 '+top+'\nhierarchy -check -top '+top+'\nproc\nopt\nmemory_dff\nmemory_collect\nopt_clean\nwrite_json '+str(a.out/'retained.json')+'\nflatten\ntechmap\nopt\nabc -g simple\nopt_clean\nwrite_json '+str(a.out/'mapped.json')+'\nstat\n'
 (a.out/'census.ys').write_text(ys)
 with (a.out/'yosys.log').open('w') as f:q=subprocess.run(['/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys','-s',str(a.out/'census.ys')],stdout=f,stderr=subprocess.STDOUT)
 if q.returncode:raise SystemExit(q.returncode)
 mods=json.loads((a.out/'mapped.json').read_text())['modules'];m=mods[top];cells=m['cells'];fan=collections.Counter();drivers={};ff=[];macros=[];names=collections.defaultdict(list)
 for n,v in m['netnames'].items():
  for i,b in enumerate(v['bits']):
   if isinstance(b,int):names[b].append(n if len(v['bits'])==1 else n+'['+str(i)+']')
 for n,v in cells.items():
  typ=v['type'];ports=v['connections'];dirs=v['port_directions']
  for p,bs in ports.items():
   for b in bs:
    if not isinstance(b,int):continue
    if dirs[p]=='input':fan[b]+=1
    elif dirs[p]=='output':drivers[b]=(n,p,typ)
  if typ.startswith('$_') and ('DFF' in typ or 'SDFF' in typ):ff.append(dict(instance=n,type=typ,clock=ports.get('C'),reset=ports.get('R'),q=ports['Q']))
  elif typ in mods and int(mods[typ].get('attributes',{}).get('blackbox','0'),2):macros.append(dict(instance=n,type=typ,clock=ports.get('clk')))
 rows=[]
 for b,nload in fan.most_common():
  if nload>16:rows.append(dict(bit=b,loads=nload,names=names.get(b,[]),driver=drivers.get(b)))
 memories=[]
 for mn,mod in mods.items():
  for cn,cell in mod.get('cells',{}).items():
   if cell['type'].startswith('$mem'):memories.append(dict(module=mn,cell=cn,type=cell['type'],parameters=cell.get('parameters')))
 r=dict(schema='opentallas.hbm_coll_safe_census_1019.v1',shape=a.shape,top=top,params=dict(VM_RT=74,SAFE_DELAY=1),source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in src+BB},cell_count=len(cells),ff_bits=sum(len(v['q']) for v in ff),ff_cells=ff,macro_instances=macros,remaining_memories=memories,fanout_over16=rows,scope='Post-techmap ABC generic-gate census; not ASAP7 mapped area, placement or native timing qualification',physical_qualified=False)
 (a.out/'receipt.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(dict(shape=a.shape,ff_bits=r['ff_bits'],macros=len(macros),memory_cells=len(memories),max_fanout=rows[0]['loads'] if rows else 0)))
if __name__=='__main__':main()
