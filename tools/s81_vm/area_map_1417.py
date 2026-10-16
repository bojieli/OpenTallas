#!/usr/bin/env python3
"""Map isolated53-source stripe leaves in ORFS, using calibrated native area."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'s81_write_edge'))
from map_measure import merge_lib, block

ap=argparse.ArgumentParser()
ap.add_argument('--root',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--kind',choices=['selector','data16','metadata26','benes16','idsel','iddata16','idmetadata26','a2control','a2header','a2payload','a2faultjoin'],required=True)
ap.add_argument('--base',type=int,default=0)
ap.add_argument('--dist',type=int,default=1)
a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
src=a.root/('tools/s81_vm/area_benes_rail.sv' if a.kind=='benes16' else ('tools/s81_vm/area_id_native.sv' if a.kind.startswith('id') else ('tools/s81_vm/area_id_native_join.sv' if a.kind=='a2faultjoin' else ('tools/s81_vm/area_a2_controlled.sv' if a.kind.startswith('a2') else 'tools/s81_vm/area_stripe_candidate.sv'))))
is_selector=a.kind in ('selector','idsel')
top='s81_area_selector' if is_selector else ('s81_area_benes_stage' if a.kind=='benes16' else 's81_area_stripe')
params={'NSRC':53,'BASE':a.base} if is_selector else ({'W':16,'DIST':a.dist} if a.kind=='benes16' else {'NSRC':53,'W':26 if 'metadata26' in a.kind else 16})
if a.kind=='a2control':top='s81_a2_controller';params={'NSRC':53,'BASE':a.base}
if a.kind=='a2faultjoin':top='s81_area_id_fault_join';params={}
if a.kind=='a2header':top='s81_a2_w0_header';params={'NSRC':53}
if a.kind=='a2payload':top='s81_a2_w0_payload';params={'NSRC':53}
libdir=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=sorted(p for p in libdir.glob('*RVT_TT*') if 'FAKE' not in p.name and p.name.split('_')[1] in ['AO','OA','SIMPLE','SEQ','INVBUF'])
assert len(libs)==5,[str(p) for p in libs]
merged,libraries=merge_lib(libs);lib=a.out/'mapped.lib';lib.write_text(merged)
(a.out/'input.sv').write_bytes(src.read_bytes())
ys=f'read_verilog -sv {a.out}/input.sv\n'
if params:ys+='chparam '+ ' '.join(f'-set {k} {v}' for k,v in params.items())+f' {top}\n'
ys+=f'hierarchy -top {top}\nsynth -top {top} -flatten -noabc\n'
ys+=f'write_json {a.out}/generic.json\ndffunmap\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\nstat -liberty {lib}\nwrite_json {a.out}/mapped.json\nwrite_verilog {a.out}/mapped.v\n'
(a.out/'map.ys').write_text(ys)
cmd=['yosys','-s',str(a.out/'map.ys')]
with (a.out/'map.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
receipt=dict(schema='opentallas.s81.vm-area-stripe-map.v1',kind=a.kind,top=top,parameters=params,
 returncode=r.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),libraries=libraries,command=cmd,
 status='MAPPED_CELL_AREA_FF_PORTS_ONLY_NO_CTS_TIMING_OR_PHYSICAL_QUALIFICATION',area_calibration_scale=1.0,
 calibration='Enrolled DFFHQNx1 LEF1.08x0.27=0.2916um2 matcheslibertyarea0.2916; no divide16',
 benched_by='results/arch/s81_vm_area_1417/'+('benes_rail.json' if a.kind=='benes16' else ('native_id_proof.json' if a.kind.startswith('id') else ('a2_controlled_proof.json' if a.kind.startswith('a2') else 'stripe_proof.json'))))
if a.kind=='a2faultjoin':receipt['benched_by']='results/arch/s81_vm_area_1417/fault_join_proof.json'
elif a.kind.startswith('id') or a.kind.startswith('a2'):
 receipt['benched_by']='results/arch/s81_vm_area_1417/a2_controlled_pinplain_proof.json'
if r.returncode==0:
 gen=json.loads((a.out/'generic.json').read_text())['modules'][top]
 net=json.loads((a.out/'mapped.json').read_text())['modules'][top]
 areas={m[1].strip().strip('"'):float(re.search(r'\barea\s*:\s*([\d.eE+-]+)',block(merged,m.start()))[1]) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',merged)}
 types={};fftypes={}
 for c in net['cells'].values():types[c['type']]=types.get(c['type'],0)+1
 for c in gen['cells'].values():
  if 'DFF' in c['type']:fftypes[c['type']]=fftypes.get(c['type'],0)+1
 assert not {k:v for k,v in types.items() if k not in areas}
 area=sum(v*areas[k] for k,v in types.items())
 receipt.update(generic_ff_bits=sum(fftypes.values()),mapped_ff_bits=sum(v for k,v in types.items() if 'DFF' in k),
  mapped_cell_count=len(net['cells']),mapped_cell_types=types,mapped_area_native_um2=area,
  port_bits={p:dict(direction=v['direction'],width=len(v['bits'])) for p,v in net['ports'].items()})
 receipt['total_port_bits']=sum(p['width'] for p in receipt['port_bits'].values())
 receipt['clock_root_ff_count_under15000']=receipt['mapped_ff_bits']<=15000
 # A raw input reaching a reset AND before the first DFF was invisible to the
 # older pin-flop selector. Explicitly classify every input bit's actual loads.
 loads={}
 for cname,cell in net['cells'].items():
  for pin,bits in cell['connections'].items():
   if cell.get('port_directions',{}).get(pin)=='output':continue
   for bit in bits:
    if isinstance(bit,int):loads.setdefault(bit,[]).append((cell['type'],pin,cname))
 direct=0;unused=0;bad=[];byport={}
 for pname,port in net['ports'].items():
  if port['direction']!='input' or pname in ['ck','ck_control']:continue
  counts=dict(plain_DFF_D=0,unreferenced=0,other_load=0)
  for idx,bit in enumerate(port['bits']):
   touched=loads.get(bit,[])
   if not touched:unused+=1;counts['unreferenced']+=1
   elif all('DFF' in typ and pin=='D' for typ,pin,_ in touched):direct+=1;counts['plain_DFF_D']+=1
   else:
    counts['other_load']+=1
    bad.append(dict(port=pname,bit=idx,loads=touched))
  byport[pname]=counts
 receipt['raw_input_boundary']=dict(status='PASS_ALL_MEANINGFUL_INPUTS_PLAIN_DFF_D' if not bad else 'FAIL_INPUT_COMBINATIONAL_OR_NON_D_LOAD',
  direct_plain_DFF_D_bits=direct,unreferenced_bits=unused,nonplain_bits=len(bad),
  by_port=byport,first20_nonplain=bad[:20],
  scope='Mapped connectivity only; no capture/launch timing, hold, clock insertion or physical pin-position proof')
for name in ['input.sv','map.ys','map.log','generic.json','mapped.json','mapped.v','mapped.lib']:
 p=a.out/name
 if p.exists():receipt.setdefault('artifacts',{})[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(r.returncode)
