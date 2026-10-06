#!/usr/bin/env python3
"""Reuse mapped32 cells to bind actual library loads, with no timing rerun."""
import hashlib,json,subprocess,sys,re
from collections import Counter
from pathlib import Path
import run_abi3_physical as D
src,out=map(Path,sys.argv[1:3]);reuse=Path(sys.argv[4]) if len(sys.argv)>3 and sys.argv[3]=='--reuse-parse' else None;assert not out.exists()
r=json.loads((src/'result.json').read_text());assert r['exit']==0
mapped=next(src.glob('work/orfs/results/asap7/*/base/1_2_yosys.v'))
assert hashlib.sha256(mapped.read_bytes()).hexdigest()==r['artifacts'][str(mapped.relative_to(src))]['sha256']
out.mkdir(parents=True)
top=next(Path(f).stem for f in r['sources_sha256'] if Path(f).name.startswith('ot_gpu_coll_item9_context32'))
ys='read_verilog /objects/'+str(mapped.relative_to(src))+'\nhierarchy -top '+top+'\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nflatten\nwrite_json /work/mapped.json\n'
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
if reuse:
 for name in ('mapped.json','library_input_caps_ff.json'):
  subprocess.run(['cp','--reflink=auto',str(reuse/name),str(out/name)],check=True)
 (out/'parse_reuse.json').write_text(json.dumps(dict(source=str(reuse),source_artifacts_preserved=True))+'\n')
else:
 with (out/'parse.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 if rc:raise SystemExit(rc)
net=json.loads((out/'mapped.json').read_text())['modules'][top]
# Yosys has removed the public rsp_data alias. Bind the actual source register pins,
# including the inverted output phase; do not invent a substitute port/load.
response=[None]*4096
for name,cell in net['cells'].items():
 m=re.fullmatch(r'g_on\.u_ep\.g_on\.g_rxs\[(\d+)\]\.g_on\.a_q\[(\d+)\].*',name)
 if not m:continue
 index=int(m[1])*256+int(m[2]);assert response[index] is None
 response[index]=cell['connections']['QN'][0]
assert all(isinstance(x,int) for x in response) and len(set(response))==4096
# Trace the real unary BUF/INV tree, not a guessed 32x flop load.
unary={};unary_cells={}
for name,cell in net['cells'].items():
 if not cell['type'].startswith(('INV','BUF')):continue
 conn=cell['connections']
 if len(conn.get('A',[]))==1 and len(conn.get('Y',[]))==1:
  unary.setdefault(conn['A'][0],[]).append(conn['Y'][0]);unary_cells[name]=conn['A'][0]
response_trees=[]
for bit in response:
 seen={bit};todo=[bit]
 while todo:
  x=todo.pop()
  for y in unary.get(x,[]):
   assert y not in seen,('unary reconvergence/loop',bit,y)
   seen.add(y);todo.append(y)
 response_trees.append(seen)
clock=net['ports']['clk_sm']['bits'][0]
caps=json.loads((out/'library_input_caps_ff.json').read_text())
summary=dict(mapped_sha256=hashlib.sha256(mapped.read_bytes()).hexdigest(),corners={},units='fF',actual_library_pin_loads=True,wire_RC_included=False,propagated_clocks=False,physical_qualified=False,adopted=False)
for corner,lib in caps.items():
 loads={bit:0. for tree in response_trees for bit in tree};count=Counter();leafloads=Counter();leafcount=Counter();clockload=0.;clockpins=0
 for name,cell in net['cells'].items():
  typ=cell['type']
  if typ=='$scopeinfo':
   assert not cell['connections'];continue # Yosys metadata, no physical pins or cell
  assert typ in lib,(typ,name)
  for pin,bits in cell['connections'].items():
   if pin not in lib[typ]:continue
   for bit in bits:
    if bit in loads:
     loads[bit]+=lib[typ][pin];count[bit]+=1
     if name not in unary_cells:leafloads[bit]+=lib[typ][pin];leafcount[bit]+=1
    if bit==clock:clockload+=lib[typ][pin];clockpins+=1
 data=[loads[x] for x in response];counts=[count[x] for x in response]
 shared=[max(tree,key=lambda y:count[y]) for tree in response_trees]
 leaf_loads=[sum(leafloads[x] for x in tree) for tree in response_trees]
 leaf_counts=[sum(leafcount[x] for x in tree) for tree in response_trees]
 shared_load=[loads[x] for x in shared];shared_count=[count[x] for x in shared]
 assert min(counts)>0
 summary['corners'][corner]=dict(response_input_pin_count_min=min(counts),response_input_pin_count_max=max(counts),response_library_load_fF_min=min(data),response_library_load_fF_max=max(data),response_total_library_load_fF=sum(data),actual_shared_branch_input_pins_min=min(shared_count),actual_shared_branch_input_pins_max=max(shared_count),actual_shared_branch_library_load_fF_min=min(shared_load),actual_shared_branch_library_load_fF_max=max(shared_load),actual_response_buffer_tree_nodes_min=min(map(len,response_trees)),actual_response_buffer_tree_nodes_max=max(map(len,response_trees)),actual_response_leaf_pin_load_fF_min=min(leaf_loads),actual_response_leaf_pin_load_fF_max=max(leaf_loads),actual_response_leaf_pin_count_min=min(leaf_counts),actual_response_leaf_pin_count_max=max(leaf_counts),clk_sm_total_connected_input_pin_load_fF=clockload,clk_sm_connected_input_pins=clockpins)
 summary['corners'][corner]['response_per_bit_remote']='response_'+corner+'.json'
 (out/('response_'+corner+'.json')).write_text(json.dumps(dict(source_QN_load_fF=data,source_QN_input_pin_count=counts,shared_branch_load_fF=shared_load,shared_branch_input_pin_count=shared_count,actual_source_bits=response,actual_shared_branch_bits=shared,leaf_loads_fF=leaf_loads,leaf_counts=leaf_counts,actual_buffer_tree_net_bits=[sorted(tree) for tree in response_trees]))+'\n')
summary['artifacts']={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file() and p.name in ('mapped.json','library_input_caps_ff.json','pins.ys','extract.py')}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary['corners']))
