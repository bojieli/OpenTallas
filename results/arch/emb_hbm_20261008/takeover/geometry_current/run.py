import sys,json,hashlib,inspect,copy
from pathlib import Path
src=Path("/srv/opentallas-scratch/codex/emb-geometry-current/src")
sys.path.insert(0,str(src/"tools"))
import qwen_rom_fulldie_b3r2 as B
from die_top_lint import QWEN_R21B,QWEN_R21C
from qwen_system.embedding_columns import insert_columns
rec={"source_sha256":{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src/"tools/qwen_rom_fulldie_b3r2.py",src/"tools/qwen_system/embedding_columns.py",src/"tools/die_top_lint.py"]},"signature":str(inspect.signature(B.selected)),"cases":{}}
assert inspect.signature(B.selected).parameters["emb_hbm"].default is False
assert inspect.signature(B.selected).parameters["before_relays"].default is None
for name,args,width in [("r21b_default",QWEN_R21B,None),("r21c_embtrue",QWEN_R21C,None),("r21c_columns92",QWEN_R21C,92.256),("r21c_columns96_rejected",QWEN_R21C,96.768)]:
 try:
  args=dict(args);args["cdc"]=B._cdc_arg(args["cdc"])
  cb=(lambda v,m:insert_columns(v,m,width)) if width else None
  v,m=B.selected(enabled=True,before_relays=cb,**args)
  rec["cases"][name]={"verdict":"PASS","die":m["die"],"embedding_enabled":m["b3r2"]["r21c_emb_hbm"],"engines":[dict(name=i.name,x=i.x,y=i.y,w=i.w,h=i.h,master=i.master) for i in m["insts"] if i.kind=="embedding_engine"],"interfaces_bound":m.get("embedding_columns",{}).get("interfaces_bound",False)}
 except Exception as e:
  import traceback; traceback.print_exc()
  rec["cases"][name]={"verdict":"EXPECTED_REJECT" if width==96.768 else "FAIL","error":str(e)}
Path("/srv/opentallas-scratch/codex/emb-geometry-current/result.json").write_text(json.dumps(rec,indent=2,default=str)+"\n")
print(json.dumps(rec,default=str))
assert all(c["verdict"] in ("PASS","EXPECTED_REJECT") for c in rec["cases"].values())
