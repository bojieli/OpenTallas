import json,sys,collections
from pathlib import Path
W=Path(sys.argv[1]);O=Path(sys.argv[2]);sys.path.insert(0,str(W/"tools/die_plan"))
import check as C
key=lambda i:json.dumps(i,sort_keys=True)
res={}
for name in sys.argv[3:]:
    raw=json.loads((O/(name+".json")).read_text())
    r,summary=C.run(raw,plan_dir=O,completeness=True)
    res[name]=r.errors();(O/(name+"_g0c.json")).write_text(json.dumps({"errors":r.errors(),"summary":summary},indent=1,default=list))
    print(name,len(r.errors()),flush=True)
b={key(i) for i in res[sys.argv[3]]}
for n,e in res.items():
    new=[i for i in e if key(i) not in b];print(n,"errors",len(e),"new",len(new),"gone",len(b-{key(i) for i in e}),collections.Counter(i.get("check") for i in new));print(json.dumps(new[:8],default=list)[:3000])
