import collections, hashlib, json
from pathlib import Path
p=Path("/tmp/codex-hbfd-pad-1019-0c3eecf04")
out={"scope":"Yosys 0.68 generic synthesized netlist, not technology mapped or routed", "sources":{}, "shapes":{}}
for f in [*p.glob("*.sv"),p/"macro_bb.v"]:
 out["sources"][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
for f in sorted(p.glob("synth_*.json")):
 d=json.loads(f.read_text()); m=d["modules"]["hbfd_pad"]; loads=collections.defaultdict(list); names=collections.defaultdict(list)
 for n,z in m["netnames"].items():
  for i,b in enumerate(z["bits"]):
   if isinstance(b,int):names[b].append(f"{n}[{i}]")
 for n,c in m["cells"].items():
  for port,bits in c["connections"].items():
   if c["port_directions"].get(port) in ("input","inout"):
    for i,b in enumerate(bits):
     if isinstance(b,int):loads[b].append(f"{n}.{port}[{i}]")
 for n,c in m["ports"].items():
  if c["direction"]=="output":
   for i,b in enumerate(c["bits"]):loads[b].append(f"PORT:{n}[{i}]")
 rows=[];macros=collections.Counter()
 for n,c in m["cells"].items():
  if c["type"].startswith("ot_sram"):macros[c["type"]]+=1
  if "DFF" in c["type"]:
   for port,bits in c["connections"].items():
    if c["port_directions"].get(port)=="output":
     for i,b in enumerate(bits):rows.append({"cell":n,"type":c["type"],"port":port,"bit":b,"names":names[b],"loads":len(loads[b]),"load_pins":loads[b]})
 rows.sort(key=lambda x:x["loads"],reverse=True)
 out["shapes"][f.stem]={"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"cells":len(m["cells"]),"ff_outputs":len(rows),"macro_counts":dict(macros),"max_q_loads":rows[0]["loads"],"over32_count":sum(x["loads"]>32 for x in rows),"all_q":rows}
print(json.dumps(out,indent=2))
