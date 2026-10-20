import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch/claude/ref_gate/qkd_pv_fin_s32-20261020-052451/src/tools')
import textbook_lint as TL
base=Path('/srv/opentallas-scratch/claude/ref_gate/qkd_pv_fin_s32-20261020-052451')
p=base/'routes/gate/work/orfs/native_census.json'
d=json.loads(p.read_text());g,top=TL.flatten(TL.parse_verilog(Path(d['netlist']['path'].replace('/work/',str(base/'routes/gate/work/orfs')+'/')).read_text()),d['top'])
outs={"Y","SN","CON","QN","Q","Z"};drivers={};loads={}
for ci,(typ,name,pins) in enumerate(g.cells):
 for pn,ns in pins.items():
  for n in ns:
   n=g.find(n)
   if pn in outs:drivers[n]=(ci,pn)
   else:loads.setdefault(n,[]).append((ci,pn))
out=[]
for v in d['violations']:
 root=g.find(g.net_id[v['net']]);ci,pn=drivers[root];typ,name,pins=g.cells[ci]
 row={'driver':v['driver'],'loads':v['loads'],'net':v['net'],'driver_master':typ,'driver_pins':{p:[str(g.find(x)) for x in ns] for p,ns in pins.items()},'load_pins':[]}
 for ci,pn in loads.get(root,[]):
  typ,name,pins=g.cells[ci];row['load_pins'].append({'instance':name,'master':typ,'pin':pn})
 out.append(row)
print(json.dumps(out,indent=2))
