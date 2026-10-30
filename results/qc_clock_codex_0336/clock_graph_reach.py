"""Census exact exported clock-cell origin hops; diagnostic geometry, not routed RC timing."""
import json,sys,collections
from pathlib import Path
p=Path(sys.argv[1]);t=json.loads(p.read_text());rows=[]
for cell,parent in t["parent_of"].items():
 a,b=t["sites"][cell],t["sites"][parent];d=sum(abs(x-y)for x,y in zip(a,b))
 n=cell[1:].split("_")[0]if cell.startswith("r")else cell[1:];nd=t["nodes"].get(n,{})
 rows.append(dict(cell=cell,parent=parent,manhattan_um=round(d,6),a=a,b=b,dme=nd.get("dme"),snake=bool(nd.get("snake")),physical_leg=bool(nd.get("physical_leg"))))
rows.sort(key=lambda x:-x["manhattan_um"])
x=dict(source=str(p),cells=len(t["sites"]),edges=len(rows),max_um=rows[0]["manhattan_um"],over405=sum(r["manhattan_um"]> 405 for r in rows),over450=sum(r["manhattan_um"]> 450 for r in rows),long_class=dict(collections.Counter("snake"if r["snake"]else"plain"for r in rows if r["manhattan_um"]>405)),worst=rows[:20],note="Cell-origin Manhattan spans only. This diagnoses raw geometry and does not replace actual-route reach or timing checks.")
Path(sys.argv[2]).write_text(json.dumps(x,indent=1)+"\n");print(json.dumps({k:v for k,v in x.items()if k!="worst"}))
