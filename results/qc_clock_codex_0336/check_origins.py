import json,sys
from pathlib import Path
import odb
r=Path("/srv/opentallas-scratch2/claude/codex-qc-clock-0336");p=json.load(open("/srv/opentallas-scratch2/claude/die-qc-46/plan/plan_qc45.json"));d=odb.dbDatabase.create();odb.read_db(d,str(r/"nativekit/native_target.odb"));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron();bad=[]
for q in p["partitions"]:
 i=b.findInst(q["name"]);bb=i.getBBox();xy=[bb.xMin()/u,bb.yMin()/u]
 if any(abs(a-c)>1e-6 for a,c in zip(xy,q["origin_um"])):bad.append(dict(part=q["name"],actual=xy,plan=q["origin_um"]))
x=dict(checked=len(p["partitions"]),off_origin=len(bad),bad=bad,verdict="PASS"if not bad else"FAIL",scope="partition origins only; per-bit pin abutment not run here")
(r/"nativekit/origins.json").write_text(json.dumps(x,indent=1));print(x)
