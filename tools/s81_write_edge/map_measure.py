#!/usr/bin/env python3
"""Map actual static VM write leaves; area only, no physical/timing qualification.
Run inside an ORFS container through fleet ot-run; outputs remain in scratch.
"""
import argparse,gzip,hashlib,json,re,subprocess
from pathlib import Path

def block(s,pos):
 a=s.index('{',pos);n=1;i=a+1
 while n:
  n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[pos:i]
def merge_lib(paths):
 prefix=None;extra=[];cells={};sources=[]
 for j,p in enumerate(paths):
  raw=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text()
  sources.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  head=raw[:re.search(r'\bcell\s*\(',raw).start()]
  for m in list(re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(([^)]+)\)',head)):
   old=m[2].strip().strip('"');raw=re.sub(r'\b'+re.escape(old)+r'\b',f's{j}_{old}',raw)
  head=raw[:re.search(r'\bcell\s*\(',raw).start()]
  if prefix is None:prefix=head
  else:extra += [block(head,m.start()) for m in re.finditer(r'\b(lu_table_template|power_lut_template)\s*\(',head)]
  for m in re.finditer(r'\bcell\s*\(([^)]+)\)',raw):
   name=m[1].strip().strip('"');assert name not in cells,name
   cells[name]=block(raw,m.start())
 return prefix+'\n'.join(extra+list(cells.values()))+'\n}\n',sources

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--kind',choices=['dispatch','stage','header','payload','control'],required=True);ap.add_argument('--base',type=int,default=0);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 top={'dispatch':'dsfd_vm_static_wdispatch128','stage':'dsfd_vm_static_wstage128','header':'dsfd_vm_static_w0_header','payload':'dsfd_vm_static_w0_payload','control':'dsfd_vm_static_wcontrol'}[a.kind]
 src=a.source/('dsfd_vm_static_w0.sv' if a.kind in ['header','payload'] else top+'.sv');libdir=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
 libs=sorted(p for p in libdir.glob('*RVT_TT*') if 'FAKE' not in p.name and p.name.split('_')[1] in ['AO','OA','SIMPLE','SEQ','INVBUF'])
 assert len(libs)==5,[p.name for p in libs]
 merged,sources=merge_lib(libs);lib=a.out/'mapped.lib';lib.write_text(merged)
 params={'NSRC':53,'NBANK':8,'BANK_BASE':a.base} if a.kind=='dispatch' else ({'DEPTH':3} if a.kind=='stage' else {'NSRC':53})
 (a.out/'input.sv').write_bytes(src.read_bytes())
 common=f'read_verilog -sv {a.out}/input.sv\nchparam '+ ' '.join(f'-set {k} {v}' for k,v in params.items())+f' {top}\nhierarchy -top {top}\nsynth -top {top} -flatten -noabc\n'
 ys=common+f'write_json {a.out}/generic.json\ndffunmap\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\nstat -liberty {lib}\nwrite_json {a.out}/mapped.json\nwrite_verilog {a.out}/mapped.v\n'
 (a.out/'map.ys').write_text(ys)
 cmd=['yosys','-s',str(a.out/'map.ys')]
 with (a.out/'map.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 receipt=dict(schema='opentallas.s81.vm-write-edge-map.v1',top=top,parameters=params,returncode=r.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),libraries=sources,command=cmd,status='MAPPED_AREA_ONLY_NOT_CTS_TIMING_OR_PHYSICAL_QUALIFICATION')
 if r.returncode==0:
  gen=json.loads((a.out/'generic.json').read_text())['modules'][top];net=json.loads((a.out/'mapped.json').read_text())['modules'][top]
  areas={m[1].strip().strip('"'):float(re.search(r'\barea\s*:\s*([\d.eE+-]+)',block(merged,m.start()))[1]) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',merged)}
  types={};fftypes={}
  for c in net['cells'].values():types[c['type']]=types.get(c['type'],0)+1
  for c in gen['cells'].values():
   if 'DFF' in c['type']:fftypes[c['type']]=fftypes.get(c['type'],0)+1
  unmapped={k:v for k,v in types.items() if k not in areas};assert not unmapped,unmapped
  # Enrolled native 1x LEF: DFFHQNx1 area=1.08*0.27=0.2916, matching Liberty.
  area=sum(v*areas[k] for k,v in types.items())
  receipt.update(generic_cell_count=len(gen['cells']),generic_ff_bits=sum(fftypes.values()),generic_ff_types=fftypes,mapped_cell_count=len(net['cells']),mapped_cell_types=types,mapped_ff_bits=sum(v for k,v in types.items() if 'DFF' in k),mapped_area_lib_units=area,mapped_area_native_um2=area,port_bits={p:dict(direction=v['direction'],width=len(v['bits'])) for p,v in net['ports'].items()})
  receipt['total_port_bits']=sum(v['width'] for v in receipt['port_bits'].values())
 for name in ['input.sv','map.ys','map.log','generic.json','mapped.json','mapped.v','mapped.lib']:
  p=a.out/name
  if p.exists():receipt.setdefault('artifacts',{})[name]=hashlib.sha256(p.read_bytes()).hexdigest()
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
