import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"tools/die_plan"))
import check as C
R=Path("/srv/opentallas-scratch2/claude/codex-qc-event-1351-1027/combined")
raw=json.load(open(R/"plan.json"));result,summary=C.run(raw,plan_dir=ROOT/"physical/die_plan/qwen_compute",completeness=True)
rep=dict(errors=len(result.errors()),warnings=len(result.items)-len(result.errors()),summary=summary,findings=result.items)
(R/"g0c_with_views.json").write_text(json.dumps(rep,indent=1)+"\n")
print("G0C",rep["errors"],rep["warnings"],flush=True);raise SystemExit(bool(rep["errors"]))
