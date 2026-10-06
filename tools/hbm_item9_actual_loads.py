#!/usr/bin/env python3
"""Reuse mapped32 cells to bind actual library loads, with no timing rerun."""
import hashlib,json,subprocess,sys
from collections import Counter
from pathlib import Path
import run_abi3_physical as D
src,out=map(Path,sys.argv[1:]);assert not out.exists()
r=json.loads((src/'result.json').read_text());assert r['exit']==0
mapped=next(src.glob('work/orfs/results/asap7/*/base/1_2_yosys.v'))
assert hashlib.sha256(mapped.read_bytes()).hexdigest()==r['artifacts'][str(mapped.relative_to(src))]['sha256']
out.mkdir(parents=True)
ys='read_verilog /objects/'+str(mapped.relative_to(src))+'\nhierarchy -top ot_gpu_coll_item9_context32_txctrl\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /work/mapped.json\n'
(out/'pins.ys').write_text(ys)
# Actual corner libraries only, not guessed loads. Store normalized pin caps remotely.
extract='''from pathlib import Path
import gzip,re,json
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
result={}
for corner in ('SS','FF'):
 cells={}
 for path in p.glob('*_RVT_'+corner+'_*.lib*'):
  text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
  assert re.search(r'capacitive_load_unit\\s*\\(\\s*1\\s*,\\s*ff\\s*\\)',text)
  for m in re.finditer(r'cell\\s*\\(\\s*(\\w+)\\s*\\)\\s*\\{(.*?)(?=\\n\\s*cell\\s*\\(|\\Z)',text,re.S):
   name,body=m.groups();pins={}
   for pin,part in re.findall(r'pin\\s*\\(\\s*(\\w+)\\s*\\)\\s*\\{(.*?)(?=\\n\\s*pin\\s*\\(|\\Z)',body,re.S):
    direction=re.search(r'direction\\s*:\\s*(\\w+)',part)
    cap=re.search(r'\\bcapacitance\\s*:\\s*([0-9.eE+-]+)',part)
    if direction and direction[1]=='input':
     assert cap,(name,pin)
     pins[pin]=float(cap[1])
   cells[name]=pins
 result[corner]=cells
Path('/work/library_input_caps_ff.json').write_text(json.dumps(result)+'\\n')
'''
(out/'extract.py').write_text(extract)
cmd=['docker','run','--rm','-v',f'{src}:/objects:ro','-v',f'{out}:/work','-w','/OpenROAD-flow-scripts/flow',D.ORFS_IMAGE,'bash','-lc',"trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -s /work/pins.ys && python3 /work/extract.py"]
with (out/'parse.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
if rc:raise SystemExit(rc)
net=json.loads((out/'mapped.json').read_text())['modules']['ot_gpu_coll_item9_context32_txctrl']
response=net['netnames']['g_on.rsp_data']['bits'];assert len(response)==4096 and len(set(response))==4096
clock=net['ports']['clk_sm']['bits'][0]
caps=json.loads((out/'library_input_caps_ff.json').read_text())
summary=dict(mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),corners={},units='fF',actual_library_pin_loads=True,wire_RC_included=False,propagated_clocks=False,physical_qualified=False,adopted=False)
for corner,lib in caps.items():
 loads={bit:0. for bit in response};count=Counter();clockload=0.;clockpins=0
 for name,cell in net['cells'].items():
  typ=cell['type'];assert typ in lib,(typ,name)
  for pin,bits in cell['connections'].items():
   if pin not in lib[typ]:continue
   for bit in bits:
    if bit in loads:loads[bit]+=lib[typ][pin];count[bit]+=1
    if bit==clock:clockload+=lib[typ][pin];clockpins+=1
 data=[loads[x] for x in response];counts=[count[x] for x in response]
 assert min(counts)>0
 summary['corners'][corner]=dict(response_input_pin_count_min=min(counts),response_input_pin_count_max=max(counts),response_library_load_fF_min=min(data),response_library_load_fF_max=max(data),response_total_library_load_fF=sum(data),clk_sm_total_connected_input_pin_load_fF=clockload,clk_sm_connected_input_pins=clockpins)
 summary['corners'][corner]['response_per_bit_remote']='response_'+corner+'.json'
 (out/('response_'+corner+'.json')).write_text(json.dumps(dict(load_fF=data,input_pin_count=counts))+'\n')
summary['artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file() and p.name in ('mapped.json','library_input_caps_ff.json','pins.ys','extract.py')}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary['corners']))
