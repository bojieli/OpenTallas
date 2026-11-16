import json,os,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2]
code="import json,sys;sys.path[:0]=[\"tools/qwen_kv_die\",\"tools\"];import kv_static_programme as k;print(json.dumps(dict(rope=k.LINK_ROPE,ovl=k.LINK_ROPE_OVL,args=k.LINK_ARGS,image=k.LINK_IMAGE)))"
rows=[]
for name,rope,ovl in [("default",0,0),("selected_sfm_rope",1,0),("legacy_ovl",0,1)]:
 e=dict(os.environ)
 for k in list(e):
  if k.startswith("OT_KV_"):del e[k]
 e.update(OT_KV_MU="1",OT_KV_ROPE=str(rope),OT_KV_ROPE_OVL=str(ovl),PYTHONDONTWRITEBYTECODE="1")
 if rope or ovl:e.update(OT_KV_EMB_WIN="1627",OT_KV_ATTN_R16="1")
 p=subprocess.run([sys.executable,"-c",code],cwd=r,env=e,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(name+": "+p.stderr)
 x=json.loads(p.stdout.strip().splitlines()[-1]);assert x["rope"]==bool(rope or ovl);assert x["ovl"]==bool(ovl);assert ("--rope" in x["args"])==bool(rope or ovl)
 rows.append(dict(case=name,**x))
print(json.dumps(dict(verdict="PASS",scope="actual compiler imports/default compatibility/selected RoPE flag; not final native programme qualification",cases=rows),indent=2))
