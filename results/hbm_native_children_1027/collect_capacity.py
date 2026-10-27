#!/usr/bin/env python3
import collections,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def modules(p):
 out={}; current=None
 for line in p.read_text().splitlines():
  m=re.match(r'module\s+(\\?\S+)\s*\(',line)
  if m:
   current=m[1].lstrip("\\");out[current]=collections.Counter()
  elif line.strip()=="endmodule":current=None
  elif current is not None:
   m=re.match(r'^\s{2}(\\?\S+)\s+(\\?\S+)\s*\($',line)
   if m and m[1] not in {"if","for","while","case"}:out[current][m[1].lstrip("\\")]+=1
 return out
def counts(top,allmods,hard):
 total=collections.Counter()
 for typ,n in allmods[top].items():
  if typ in hard:total["hard:"+typ]+=n
  elif "_ASAP7_" in typ:total["std:"+typ]+=n
  elif typ.startswith("ot_sram_"):total["macro:"+typ]+=n
  elif typ in allmods:
   for k,v in counts(typ,allmods,hard).items():total[k]+=n*v
  else:total["unknown:"+typ]+=n
 return total
def ports(p,top):
 result=[];on=False
 for line in p.read_text().splitlines():
  if line.startswith("module "):on=line.rstrip().split(" ",1)[1].lstrip("\\")==top
  elif on and line=="end":on=False
  elif on and line.strip().startswith("wire "):
   m=re.search(r'\b(input|output|inout) (\d+) \\(\S+)',line)
   if m:
    w=re.search(r'\bwidth (\d+)',line)
    result.append(dict(name=m[3],direction=m[1],width=int(w[1]) if w else 1,port_id=int(m[2])))
 return sorted(result,key=lambda x:x["port_id"])
report={}
for p in ROOT.glob("*/profile.json"):
 d=p.parent;j=json.loads(p.read_text());name=d.name
 mapped=next(d.glob("run/results/asap7/*/base/1_2_yosys.v"),None)
 canonical=next(d.glob("run/results/asap7/*/base/1_1_yosys_canonicalize.rtlil"),None)
 if mapped:
  ms=modules(mapped);ct=counts(j["top"],ms,set(j["blackbox_children"]))
  po=ports(canonical,j["top"]) if canonical else []
  report[name]=dict(**j,mapped=True,std_cells=sum(v for k,v in ct.items() if k.startswith("std:")),macros={k[6:]:v for k,v in ct.items() if k.startswith("macro:")},hard_children={k[5:]:v for k,v in ct.items() if k.startswith("hard:")},unknown={k[8:]:v for k,v in ct.items() if k.startswith("unknown:")},port_buses=po,port_bits={di:sum(x["width"] for x in po if x["direction"]==di) for di in ["input","output","inout"]},histogram=dict(ct))
 else:report[name]=dict(**j,mapped=False)
(ROOT/"capacity.json").write_text(json.dumps(report,indent=2)+"\n")
for k,v in sorted(report.items()):print(k,v.get("std_cells","RUNNING"),v.get("macros"),v.get("hard_children"),v.get("port_bits"))
