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
for vi in d["violations"]:
 v=vi;root=g.find(g.net_id[v["net"]]);print("ROOT",v["driver"],v["net"])
 front=[root];seen=set();found=set()
 for depth in range(40):
  nf=[]
  for n in front:
   if n in seen:continue
   seen.add(n)
   if n not in drivers:continue
   ci,pn=drivers[n];typ,name,pins=g.cells[ci]
   if "DFF" in typ:
    if name not in found:print("SOURCE",depth,name,pn);found.add(name)
   else:
    for ip,ns in pins.items():
     if ip not in outs:
      nf.extend(g.find(x) for x in ns)
  front=nf
  if not front or len(found)>120:break
 front=[root];seen=set();found=set()
 for depth in range(40):
  nf=[]
  for n in front:
   if n in seen:continue
   seen.add(n)
   for ci,pn in loads.get(n,[]):
    typ,name,pins=g.cells[ci]
    if "DFF" in typ:
     if name not in found:print("SINK",depth,name,pn);found.add(name)
    else:
     for op,ns in pins.items():
      if op in outs:nf.extend(g.find(x) for x in ns)
  front=nf
  if not front or len(found)>120:break
