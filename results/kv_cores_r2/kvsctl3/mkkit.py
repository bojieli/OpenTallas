# KV-KVSCTL-3: repo-relative hub_C kit_rtl for the landed qkd_kvs_ctl cut (parent binds the cut core, not the native module)
import json,os,re
src="/srv/opentallas-scratch2/claude/kvsctl-r2/kit_rtl2/kv3_hub_C/kit_rtl.json"
D="results/kv_cores_r2/kvsctl3/kit_rtl/kv3_hub_C/"; C="results/kv_cores_r2/kvsctl3/rtl/"
j=json.load(open(src))
core=json.load(open(C+"qkd_kvs_ctl_core.json"))
def rel(f):
    if "/kit_rtl2/kv3_hub_C/" in f: return D+os.path.basename(f)
    if f.endswith("/b32/rtl/bind_cells.sv"): return C+"bind_cells.sv"
    m=re.search(r"/wt/kvsctl-src/(.*)$",f)
    if m: return m.group(1)
    raise SystemExit("unmapped "+f)
fs=[]
for f in j["files"]:
    if f.endswith("/qkd_kvs_ctl_nc32.sv"):          # native full-port qkd_kvs_ctl -> the cut core (wrapper + leaf)
        fs += [C+"qkd_kvs_ctl.sv", C+"qkd_kvs_ctl_nc32__leaf.sv"]; continue
    fs.append(rel(f))
for f in core["files"]:
    if f not in fs: fs.append(f)
for f in fs: assert os.path.exists(f),f
j["files"]=fs; j["bind_out"]="results/kv_cores_r2/kvsctl3/kit_rtl (KV-KVSCTL-3 rebind of codex-kv-pv-1026/b32 hub_C)"
for k,v in j["hard_macros"].items():
    for kk in list(v):
        if isinstance(v[kk],str): v[kk]=rel(v[kk])
        elif isinstance(v[kk],list): v[kk]=[rel(x) for x in v[kk]]
j.pop("sim_files",None)
s=json.dumps(j,indent=1); assert "/srv/" not in s and "/home/" not in s
open(D+"kit_rtl.json","w").write(s+"\n"); open(D+"kit_rtl.f","w").write("\n".join(fs)+"\n"); print(len(fs))
