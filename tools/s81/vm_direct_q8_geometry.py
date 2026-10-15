#!/usr/bin/env python3
"""Source-bound direct q8 pin/placement screen; no native route/timing claim."""
import argparse,hashlib,json,re
from pathlib import Path
PIN=re.compile(r'place_pin -pin_name \{([^}]+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}')
def tclpins(path):
 return {m[0]:(float(m[2]),float(m[3])) for m in PIN.findall(path.read_text())}
def points(d,xy):
 out={};w,h=d['outline_um']
 for n,s in d['ports'].items():
  for i,(f,l,p,z) in enumerate(s['per_bit']):
   x,y=(p,h if f=='N' else 0) if f in 'NS' else (w if f=='E' else 0,p)
   out[n if s['bits']==1 else f'{n}[{i}]']=(x+xy[0],y+xy[1])
 return out
def shift(p,xy):return {n:(v[0]+xy[0],v[1]+xy[1]) for n,v in p.items()}
def pin(n,i,w):return n if w==1 else f'{n}[{i}]'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--edge-dir',type=Path,required=True);ap.add_argument('--direct-dir',type=Path,required=True);ap.add_argument('--bridge',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 inputs={};stages={};changes=[]
 for face in ['east','west']:
  p=a.edge_dir/f'dsfd_vm_static_wstage128_{face}.tcl';inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();old=tclpins(p);new=dict(old)
  names=[n for n in old if re.fullmatch(r'o_(v|row\[\d+\]|mask\[\d+\]|data\[\d+\]|tag\[\d+\])',n)]
  assert len(names)==155
  coords={n:(round(35.808+.096*i,6),.042) for i,n in enumerate(names)};new.update(coords)
  lines=[]
  for line in p.read_text().splitlines():
   m=PIN.search(line)
   if m and m[1] in coords:
    n=m[1];x,y=coords[n];line=f'place_pin -pin_name {{{n}}} -layer M5 -location {{{x:.6f} {y:.6f}}} -force_to_die_boundary'
   lines.append(line)
  assert all(new[n]==v for n,v in old.items() if n not in names)
  dest=a.out_dir/f'dsfd_vm_static_wstage128_{face}_south.tcl';dest.write_text('\n'.join(lines)+'\n');stages[face]=new
  changes.append(dict(variant=face,total_pins=len(old),moved_drain_bits=len(names),preserved_other_bits=len(old)-len(names),source_sha256=inputs[str(p)]))
 def assigned(name,xy):
  p=a.direct_dir/(name+'.json');inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return points(json.loads(p.read_text()),xy)
 out=assigned('dsfd_vm_static_scatter_b8_out',[302.4,648]);bp=json.loads(a.bridge.read_text());inputs[str(a.bridge)]=hashlib.sha256(a.bridge.read_bytes()).hexdigest();bridge=points(bp,[302.4,259.2]);edges=[]
 def add(kind,bank,sn,sp,tn,tp):
  dist=abs(sp[0]-tp[0])+abs(sp[1]-tp[1]);edges.append(dict(kind=kind,bank=bank,source=sn,target=tn,source_um=sp,target_um=tp,manhattan_um=round(dist,6)))
 
 for p in [a.edge_dir/'dsfd_vm_static_wdispatch128.tcl',a.edge_dir/'plan.json']:
  inputs[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 disp=shift(tclpins(a.edge_dir/'dsfd_vm_static_wdispatch128.tcl'),[108,820.8]);plan=json.loads((a.edge_dir/'plan.json').read_text())
 captures=[]
 for b in range(8):
  stage=shift(stages['east' if b<4 else 'west'],[864 if b<4 else 0,820.8+86.4*(b%4)])
  xy=[540+64.8*b if b<4 else 237.6-64.8*(b-4),756];captures.append(dict(bank=b,xy_um=xy,output_face='W' if b<4 else 'E'))
  cap=assigned('dsfd_vm_static_write_capture128_'+('W' if b<4 else 'E'),xy)
  for e in plan['edges']:
   if e['bank']==b:add('dispatch_to_storage',b,e['dispatch_pin'],disp[e['dispatch_pin']],e['stage_pin'],stage[e['stage_pin']])
  for f,w in [('v',1),('we',1),('row',14),('mask',4),('data',128),('tag',8)]:
   for i in range(w):
    s=pin('o_'+('v' if f=='we' else f),i,w);t=pin('i_'+f,i,w);add('storage_to_capture',b,s,stage[s],t,cap[t])
    s=pin('o_'+f,i,w);t=f'i_{f}[{b*w+i}]';add('capture_to_output',b,s,cap[s],t,out[t])
  for f,g,w in [('v','wv',1),('addr','wa',9),('mask','wm',4),('data','wd',128),('tag','wt',8)]:
   for i in range(w):
    s=f'o_{f}[{b*w+i}]';t=f'i_{g}[{b*w+i}]';add('output_to_bridge',b,s,out[s],t,bridge[t])
 stats={}
 for k in sorted(set(e['kind'] for e in edges)):
  ee=[e for e in edges if e['kind']==k];stats[k]=dict(bits=len(ee),max_manhattan_um=max(e['manhattan_um'] for e in ee),over500=sum(e['manhattan_um']>500 for e in ee),sum_bit_um=sum(e['manhattan_um'] for e in ee))
 report=dict(scope='PLANNED_EXACT_PIN_Q8_GEOMETRY_NOT_NATIVE',shape_um=[972,1166.4],captures=captures,pin_changes=changes,source_sha256=inputs,stats=stats,edges=edges,ages='Existing two scatter stages retained; zero additional cycles in this candidate',open=['Native timing/phi-R/CTS/PG and legal IO closure','All global read/write distribution and controls','Full traffic cuts including clock, PG and other services','Actual orientation approval; all shown R0'],unused_output='o_we is not connected by current direct parent')
 (a.out_dir/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(stats,indent=1))
if __name__=='__main__':main()
