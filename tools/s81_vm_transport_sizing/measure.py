#!/usr/bin/env python3
"""Actual static duplex relay mapping; native pin sizing only, never signoff."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
TOP='dsfd_vm_static_relay128_b8'
SOURCE_COMMIT='cd1242953'
EXPECTED_SHA256={'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128.sv': '389a09f45fb0543854f96d4d950fd329cb556c88430c1e5fea82147c56034f1e', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128_b4.sv': 'ee7b3813da68aad059991350d8624f961500168fc8168d3d7aa3db3eb747f9a4', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128_b8.sv': '907e24fe89386104b6831611223779bdd540e62292077ef5efe6308f837824a3', 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128_b16.sv': '32d61eaa7429345a6dd812ada736d21ec00310da21851b43683d59b551440217'}
SOURCES=list(EXPECTED_SHA256)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--top',choices=['dsfd_vm_static_relay128_b4','dsfd_vm_static_relay128_b8','dsfd_vm_static_relay128_b16'],required=True);a.add_argument('--root',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--lef',type=Path,required=True);v=a.parse_args();global TOP;TOP=v.top;v.out.mkdir(parents=True,exist_ok=False)
 src=[v.root/p for p in SOURCES]
 for n,p in zip(SOURCES,src):
  if sha(p)!=EXPECTED_SHA256[n]:raise ValueError('source pin mismatch: '+n)
 libs=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT_nldm*.lib'));assert len(libs)==5
 seq=next(p for p in libs if 'SEQ_' in p.name);flags=' '.join('-liberty '+str(p) for p in libs)
 provenance={'source_commit':SOURCE_COMMIT,'measurement_script_sha256':sha(Path(__file__)),'sources_sha256':{n:sha(p) for n,p in zip(SOURCES,src)},'libraries_sha256':{p.name:sha(p) for p in libs},'lef_sha256':sha(v.lef),'tool':subprocess.check_output(['yosys','-V'],text=True).strip(),'parameters':{'NBANK':4 if TOP.endswith('b4') else 8 if TOP.endswith('b8') else 16},'scope':'Actual full native-pin-register leaf RVT TT ABC mapping and cell census only; no route/timing/parent adoption'}
 (v.out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 ys='read_verilog -sv -DSYNTHESIS '+' '.join(map(str,src))+f'\nhierarchy -check -top {TOP}\nsynth -top {TOP} -flatten -noabc\n'+''.join('read_liberty -lib '+str(p)+'\n' for p in libs)+f'dfflibmap -liberty {seq}\nabc {flags} -D 833\nclean\ncheck -assert\nstat {flags}\nwrite_json {v.out}/mapped.json\n'
 (v.out/'map.ys').write_text(ys)
 with (v.out/'map.log').open('w') as log:r=subprocess.run(['yosys','-s',str(v.out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 mod=json.loads((v.out/'mapped.json').read_text())['modules'][TOP];cells=collections.Counter(c['type'] for c in mod['cells'].values() if c['type']!='$scopeinfo');areas={}
 for m in re.finditer(r'MACRO\s+(\S+)\s+(.*?)(?=\nMACRO|\Z)',v.lef.read_text(),re.S):
  q=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',m[2])
  if q:areas[m[1]]=float(q[1])*float(q[2])
 unknown={t:n for t,n in cells.items() if t not in areas};area=sum(areas.get(t,0)*n for t,n in cells.items());width=height=129.6 if TOP.endswith('b4') else 172.8 if TOP.endswith('b8') else 345.6
 res={'status':'MAPPED_AREA_ONLY' if not unknown else 'UNMAPPED','source_commit':SOURCE_COMMIT,'top':TOP,'abc_target_ps':833,'cell_area_um2':area,'cells':dict(cells),'cell_count':sum(cells.values()),'mapped_FF_cells':sum(n for t,n in cells.items() if 'DFF' in t),'unknown_cells':unknown,'ports':{p:{'direction':q['direction'],'bits':len(q['bits'])} for p,q in mod['ports'].items()},'candidate_outline_um':[width,height],'outline_area_um2':width*height,'raw_utilization':area/(width*height),'core_inset_um':2.16,'inset_core_area_um2':(width-4.32)*(height-4.32),'inset_core_utilization':area/((width-4.32)*(height-4.32)),'parent_fit_proven':False,'timing_proven':False,'pin_assignment_proven':False,'clock_root_limit':15000,'adoption_requires':['exact assigned per-bit pins and pin-capacity check','CTS insertion/spread and native TT setup/FF hold/DRC','parent connectivity-aware placement with actual bank face pins','production static-schedule composition visibility and throughput']}
 (v.out/'area.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:x for k,x in res.items() if k!='cells'},indent=2));raise SystemExit(bool(unknown))
if __name__=='__main__':main()
