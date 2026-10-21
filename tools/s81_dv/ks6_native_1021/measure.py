#!/usr/bin/env python3
"""Source-pinned KS6 RVT TT mapped cost and authoritative native census; no layout."""
import argparse, collections, hashlib, json, re, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[3];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
src=root/'rtl/dsrom_sys/s81_dv/unit/dsdv_static_ks6.sv';top='dsdv_static_ks6'
libs=sorted(Path('/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM').glob('*RVT_TT_nldm*.lib'));assert len(libs)==5
seq=next(x for x in libs if 'SEQ_' in x.name);flags=' '.join('-liberty '+str(x) for x in libs)
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
prov={'source_ref':'d64020ffb','source_sha256':sha(src),'script_sha256':sha(Path(__file__)),'library_sha256':{x.name:sha(x) for x in libs},'yosys':subprocess.check_output(['yosys','-V'],text=True).strip(),'top':top,'parameters':{'SPAN':1259408,'GRAPH_TAG':'218d375d','NOPS':128},'scope':'KS6 adapter only; no host qualification, no layout/timing/fit/adoption'}
(out/'provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
y=f'read_verilog -sv -DSYNTHESIS {src}\nhierarchy -check -top {top}\nsynth -top {top} -flatten -noabc\n'
y+=''.join('read_liberty -lib '+str(x)+'\n' for x in libs)
y+=f'dfflibmap -liberty {seq}\nabc {flags} -D 833\nclean\ncheck -assert\nstat {flags}\nwrite_json {out}/mapped.json\nwrite_verilog -noattr -noexpr {out}/mapped.v\n'
(out/'map.ys').write_text(y)
with (out/'map.log').open('w') as f:rc=subprocess.run(['yosys','-s',str(out/'map.ys')],stdout=f,stderr=subprocess.STDOUT).returncode
if rc:raise SystemExit(rc)
m=json.loads((out/'mapped.json').read_text())['modules'][top];cells=collections.Counter(c['type'] for c in m['cells'].values() if c['type']!='$scopeinfo');areas={}
for lib in libs:
 for name,body in re.findall(r'cell\s*\(\s*(\S+)\s*\)\s*\{(.*?)(?=\n  cell|\Z)',lib.read_text(),re.S):
  q=re.search(r'\barea\s*:\s*([\d.]+)',body)
  if q:areas[name]=float(q[1])
unknown={k:v for k,v in cells.items() if k not in areas}
res={'state':'MAPPED_COST_ONLY','source':prov,'cell_count':sum(cells.values()),'cells':dict(cells),'mapped_ff':sum(n for t,n in cells.items() if 'DFF' in t),'mapped_area_um2':sum(areas.get(k,0)*v for k,v in cells.items()),'unknown_cells':unknown,'new_SRAM_macros':0,'physical_qualified':False}
(out/'cost.json').write_text(json.dumps(res,indent=2)+'\n')
cmd=['python3',str(root/'tools/ref_tile/native_census.py'),'--netlist',str(out/'mapped.v'),'--top',top,'--out',str(out/'native_census.json')]
for lib in libs:cmd+=['--liberty',str(lib)]
rc=subprocess.run(cmd).returncode
print(json.dumps({k:v for k,v in res.items() if k not in ['cells','source']},indent=2))
raise SystemExit(rc or bool(unknown))
