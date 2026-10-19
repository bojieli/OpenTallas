#!/usr/bin/env python3
"""Uncapped logical-pin census of emitted Yosys JSON; generic/native labelled."""
import collections,json,re,sys
from pathlib import Path
j=json.load(open(sys.argv[1]));top=j["modules"]["qfd_dv_typed_witness_control"]
cells=top["cells"];sinks=collections.defaultdict(list);drivers=collections.defaultdict(list);trans={};aliases=collections.defaultdict(list)
def ff(t):return bool(re.search(r"DFF|SDFF",t,re.I))
def transparent(t):return t in ("$_NOT_","$_BUF_") or bool(re.match(r"^(BUF|INV|HB)[x0-9_]",t,re.I))
for n,v in top["netnames"].items():
 for k,b in enumerate(v["bits"]):aliases[b].append(n+(f"[{k}]" if len(v["bits"])>1 else ""))
for n,v in top["ports"].items():
 for k,b in enumerate(v["bits"]):
  label=f"port:{n}[{k}]"
  if v["direction"]=="input":drivers[b].append((label,"input"))
  else:sinks[b].append((label,"port",n))
for n,c in cells.items():
 t=c["type"];role="ff" if ff(t) else "macro" if re.search(r"sram",t,re.I) else "tie" if re.search(r"TIE|LOGIC[01]",t,re.I) else "comb"
 outs=[b for p,bs in c["connections"].items() if c["port_directions"].get(p)=="output" for b in bs]
 if transparent(t):
  for p,bs in c["connections"].items():
   if c["port_directions"].get(p)=="input":
    for b in bs:trans.setdefault(b,[]).extend(outs)
  continue
 for p,bs in c["connections"].items():
  for k,b in enumerate(bs):
   label=f"{n}/{p}[{k}]"
   if c["port_directions"].get(p)=="output":drivers[b].append((label,role))
   elif not (ff(t) and p.upper() in ("C","CLK","CK","CP")):sinks[b].append((label,role,p))
for literal in ("0","1","x","z"):
 if literal in sinks or literal in trans:drivers[literal].append(("constant:"+literal,"constant"))
rows=[]
for b,ds in drivers.items():
 if any(label.startswith("port:ck[") for label,_ in ds):continue
 reached=set();endpoints={};queue=[b]
 while queue:
  x=queue.pop()
  if x in reached:continue
  reached.add(x);endpoints.update((v[0],v) for v in sinks[x]);queue.extend(trans.get(x,[]))
 label,role=ds[0] if len(ds)==1 else ("|".join(x[0] for x in ds),"multidriver")
 rows.append(dict(root=label,role=role,loads=len(endpoints),aliases=aliases[b][:8],examples=list(endpoints)[:8]))
rows.sort(key=lambda r:(-r["loads"],r["root"]))
summary={"source":sys.argv[1],"scope":"all emitted roles including top/reset, BUF/INV transparent, clock-only pins excluded", "roots":len(rows),"violations_over32":sum(r["loads"]>32 for r in rows),"role_counts":dict(collections.Counter(r["role"] for r in rows)),"role_max":{role:max(r["loads"] for r in rows if r["role"]==role) for role in set(r["role"] for r in rows)},"ff_cells":sum(ff(c["type"]) for c in cells.values()),"cells":len(cells),"counter_vectors":{n:len(v["bits"]) for n,v in top["netnames"].items() if n.startswith("cycle[")},"top50":rows[:50]}
Path(sys.argv[2]+".json").write_text(json.dumps(summary,indent=2)+"\n")
with open(sys.argv[2]+".tsv","w")as f:
 f.write("root\trole\tloads\taliases\texamples\n")
 for r in rows:f.write(f"{r['root']}\t{r['role']}\t{r['loads']}\t{','.join(r['aliases'])}\t{','.join(r['examples'])}\n")
print(json.dumps({k:v for k,v in summary.items() if k not in ("top50","counter_vectors")}))
