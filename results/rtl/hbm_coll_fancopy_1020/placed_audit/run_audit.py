#!/usr/bin/env python3
import sys,subprocess
from pathlib import Path
R=Path(sys.argv[1]);gate=Path(sys.argv[2]);top=sys.argv[3];tag=sys.argv[4]
img="sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29"
odb=f"/frozen/routes/gate/work/orfs/results/asap7/opentallas_{top}_asap7_ref_gate/base/5_1_grt.odb"
base=["docker","run","--rm","-v",str(R)+":/audit","-v",str(gate)+":/frozen:ro"]
for name,script,lang in [("original_pg","audit_native_pg.tcl","tcl"),("classes","classify.py","python"),("diagnostic_bind","diagnostic_bind.tcl","tcl"),("sequential_reach","sequential_reach.py","python")]:
 if (R/(tag+"_"+name+".json")).exists():
  print(tag,name,"EXISTING_PRESERVED",flush=True);continue
 env=["-e","AUDIT_ODB="+odb,"-e","AUDIT_OUT=/audit/"+tag+"_"+name+".json","-e","OT_PG_AUDIT_ODB="+odb,"-e","OT_PG_AUDIT_REPORT=/audit/"+tag+"_"+name+".json"]
 cmd=base+env+["--entrypoint","/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad",img,"-exit"]+(["-python"] if lang=="python" else [])+["/audit/"+script]
 with (R/(tag+"_"+name+".log")).open("w") as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(tag,name,rc,flush=True)
 if rc and not (R/(tag+"_"+name+".json")).exists():sys.exit(rc)
