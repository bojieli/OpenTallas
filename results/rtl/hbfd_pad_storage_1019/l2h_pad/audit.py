# All-Q fanout audit of flattened Yosys JSON. Kept-hierarchy leaf cells (hbfd_pad_icopy / hbfd_pad_rst_land) count as
# register drivers: their output-port bits are Q pins (each leaf holds only flops driving its output port).
import collections, hashlib, json, sys
from pathlib import Path
p=Path(sys.argv[1])
out={"scope":"Yosys 0.68 generic synth -flatten (keep_hierarchy leaves kept), not technology mapped","sources":{},"shapes":{}}
for f in sorted([*p.glob("*.sv"),p/"macro_bb.v"]):
  out["sources"][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
for f in sorted(p.glob("synth_*.json")):
  d=json.loads(f.read_text())
  top=[k for k,v in d["modules"].items() if v.get("attributes",{}).get("top")]; m=d["modules"][top[0]]
  loads=collections.defaultdict(list); names=collections.defaultdict(list)
  for n,z in m["netnames"].items():
    for i,b in enumerate(z["bits"]):
      if isinstance(b,int): names[b].append(f"{n}[{i}]")
  for n,c in m["cells"].items():
    for port,bits in c["connections"].items():
      if c.get("port_directions",{}).get(port) in ("input","inout"):
        for i,b in enumerate(bits):
          if isinstance(b,int): loads[b].append(f"{n}.{port}[{i}]")
  for n,c in m["ports"].items():
    if c["direction"]=="output":
      for i,b in enumerate(c["bits"]): loads[b].append(f"PORT:{n}[{i}]")
  rows=[]; macros=collections.Counter(); kept=collections.Counter()
  for n,c in m["cells"].items():
    t=c["type"]
    if t.startswith("ot_sram"): macros[t]+=1
    is_leaf=("hbfd_pad_icopy" in t) or ("hbfd_pad_rst_land" in t)
    if is_leaf: kept[t.split("\\")[-1][:60]]+=1
    if "DFF" in t or is_leaf:
      for port,bits in c["connections"].items():
        if c.get("port_directions",{}).get(port)=="output":
          for i,b in enumerate(bits):
            rows.append({"cell":n,"type":t,"port":port,"bit":b,"names":names[b][:3],"loads":len(loads[b])})
  pi=[len(loads[b]) for n,c in m["ports"].items() if c["direction"]=="input" and n!="ck" for b in c["bits"]]
  rows.sort(key=lambda x:x["loads"],reverse=True)
  out["shapes"][f.stem]={"top":top[0],"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"cells":len(m["cells"]),
    "ff_outputs":len(rows),"kept_cells":dict(kept),"macro_counts":dict(macros),"max_q_loads":rows[0]["loads"] if rows else 0,
    "over32_count":sum(x["loads"]>32 for x in rows),"max_input_port_loads":max(pi) if pi else 0,"top_q":rows[:40]}
print(json.dumps(out,indent=1))
