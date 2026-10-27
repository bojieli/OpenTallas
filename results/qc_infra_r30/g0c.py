import sys,json
repo,plan,out,pdir=sys.argv[1:5]
sys.path.insert(0,repo+"/tools/die_plan")
import check as C
from pathlib import Path
raw=json.load(open(plan));result,summary=C.run(raw,plan_dir=Path(pdir),completeness=True)
rep=dict(errors=len(result.errors()),warnings=len(result.items)-len(result.errors()),summary=summary,findings=result.items)
Path(out).write_text(json.dumps(rep,indent=1,default=str)+"\n")
print("G0C",rep["errors"],rep["warnings"],flush=True)
for f in result.errors()[:40]: print(f)
