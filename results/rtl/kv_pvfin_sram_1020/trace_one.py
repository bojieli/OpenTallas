import sys,json
from pathlib import Path
sys.path.insert(0,"tools")
import textbook_lint as TL
p=Path("results/rtl/kv_pvfin_sram_1020/native_qkd_pv_fin_s32_census.json")
d=json.loads(p.read_text());g,top=TL.flatten(TL.parse_verilog(Path(d["netlist"]["path"].replace("/work/","")).read_text()),d["top"])
outs={"Y","SN","CON","QN","Q","Z"};drivers={};loads={}
for ci,(typ,name,pins) in enumerate(g.cells):
 for pn,ns in pins.items():
  for n in ns:
   n=g.find(n)
   if pn in outs:drivers[n]=(ci,pn)
   else:loads.setdefault(n,[]).append((ci,pn))
v=d["violations"][int(sys.argv[1]) if len(sys.argv)>1 else 0];root=g.find(g.net_id[v["net"]]);print("ROOT",v["driver"],v["net"])
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
 if not front or len(found)>40:break
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
 if not front or len(found)>40:break
