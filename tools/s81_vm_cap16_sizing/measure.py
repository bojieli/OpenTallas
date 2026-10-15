#!/usr/bin/env python3
"""Actual cap16 native-pin-register leaf mapping; bounded sizing, never timing signoff."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
TOP='dsfd_vm_static_cap_leaf'
SOURCE_COMMIT='92154feb6'
EXPECTED_SHA256={'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl.sv': 'b6c23720c6dd34c3ec7296dfb44d41848abea4fe18f260ab75a7839660dba538', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap_leaf.sv': '192752ca88c4a93c661bfeeb7bb2a2aa152b5b6490330e096f7c05eeb0e50ecf'}
SOURCES=['rtl/dsrom_sys/s81_ph/vm/'+n+'.sv' for n in ['dsfd_vm_static_capl',TOP]]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--lef',type=Path,required=True);v=a.parse_args();v.out.mkdir(parents=True,exist_ok=False)
 src=[v.root/p for p in SOURCES]
 for n,p in zip(SOURCES,src):
  if sha(p)!=EXPECTED_SHA256[n]:raise ValueError('source pin mismatch: '+n)
 libs=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT_nldm*.lib'));assert len(libs)==5
 seq=next(p for p in libs if 'SEQ_' in p.name);flags=' '.join('-liberty '+str(p) for p in libs)
 provenance={'source_commit':SOURCE_COMMIT,'measurement_script_sha256':sha(Path(__file__)),'sources_sha256':{n:sha(p) for n,p in zip(SOURCES,src)},'libraries_sha256':{p.name:sha(p) for p in libs},'lef_sha256':sha(v.lef),'tool':subprocess.check_output(['yosys','-V'],text=True).strip(),'parameters':{'E':8},'scope':'Actual full native-pin-register leaf RVT TT ABC mapping and cell census only; no route/timing/parent adoption'}
 (v.out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 ys='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,src))+f'\nhierarchy -check -top {TOP}\nsynth -top {TOP} -flatten -noabc\ndfflibmap -liberty {seq}\nabc {flags} -D 1111\nclean\ncheck -assert\nstat {flags}\nwrite_json {v.out}/mapped.json\n'
 (v.out/'map.ys').write_text(ys)
 with (v.out/'map.log').open('w') as log:r=subprocess.run(['yosys','-s',str(v.out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 mod=json.loads((v.out/'mapped.json').read_text())['modules'][TOP];cells=collections.Counter(c['type'] for c in mod['cells'].values() if c['type']!='$scopeinfo');areas={}
 for m in re.finditer(r'MACRO\s+(\S+)\s+(.*?)(?=\nMACRO|\Z)',v.lef.read_text(),re.S):
  q=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',m[2])
  if q:areas[m[1]]=float(q[1])*float(q[2])
 unknown={t:n for t,n in cells.items() if t not in areas};area=sum(areas.get(t,0)*n for t,n in cells.items());width,height=80.64,230.04
 res={'status':'MAPPED_AREA_ONLY' if not unknown else 'UNMAPPED','source_commit':SOURCE_COMMIT,'top':TOP,'abc_target_ps':1111,'cell_area_um2':area,'cells':dict(cells),'cell_count':sum(cells.values()),'mapped_FF_cells':sum(n for t,n in cells.items() if 'DFF' in t),'unknown_cells':unknown,'ports':{p:{'direction':q['direction'],'bits':len(q['bits'])} for p,q in mod['ports'].items()},'candidate_outline_um':[width,height],'outline_area_um2':width*height,'raw_utilization':area/(width*height),'core_inset_um':2.16,'inset_core_area_um2':(width-4.32)*(height-4.32),'inset_core_utilization':area/((width-4.32)*(height-4.32)),'parent_fit_proven':False,'timing_proven':False,'pin_assignment_proven':False,'clock_root_limit':15000,'adoption_requires':['exact assigned per-bit pins and pin-capacity check','CTS insertion/spread and native TT setup/FF hold/DRC','parent containment disjoint from128banks and x34bridges','production static-schedule composition visibility and throughput']}
 (v.out/'area.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:x for k,x in res.items() if k!='cells'},indent=2));raise SystemExit(bool(unknown))
if __name__=='__main__':main()
