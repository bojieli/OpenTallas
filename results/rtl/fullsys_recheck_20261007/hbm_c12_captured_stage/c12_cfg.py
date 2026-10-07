# fullsys-recheck: captured DS1M/Qwen8K CP+c12 stage (tools/hbm_integrated_su_c12_stage.py) with c12 params overridden
import json,sys,os
from pathlib import Path
name=sys.argv[1]; over=json.loads(sys.argv[2]); T=Path("/srv/opentallas-scratch2/scratch/claude/fullsys-recheck")
sys.path.insert(0,str(T/"wt-su/tools")); os.chdir(T/"wt-su")
import hbm_su_c12 as C12
C12.P.update(over)
import hbm_integrated_su_c12_stage as S
# OWNER 2026-10-06 21:35: load cap is 3 x cores (memory is the hard limit); the tool hard-codes load+16 < 110 -> scale load by 1/3
import types as _t; _os=S.os; S.os=_t.SimpleNamespace(**{k:getattr(_os,k) for k in dir(_os) if not k.startswith("__")}); S.os.getloadavg=lambda: tuple(x/3 for x in _os.getloadavg())
spec=json.loads((T/"c12cases/prepared.json").read_text())
for t,c in spec["cases"].items(): c["directory"]=str(T/"c12cases"/t)
sp=T/f"c12spec_{name}.json"; sp.write_text(json.dumps(spec))
W=T/f"c12_{name}"
S.prepare(sp,W,"dpi_beh")
rc=S.run(W,24,3000000000,16,False,"all")
print("RC",rc,"P",C12.P); sys.exit(rc)
