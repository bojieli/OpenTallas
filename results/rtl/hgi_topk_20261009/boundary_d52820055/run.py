import json,hashlib,pathlib,importlib.util,sys
r=pathlib.Path('/srv/opentallas-scratch/codex/hgi-topk-boundary-d52820055')
p=json.loads((r/'hgi-topk-boundary-source-d52820055.json').read_text())
for f,s in p['files'].items():assert hashlib.sha256(s.encode()).hexdigest()==p['sha256'][f],f
s=json.loads((r/'hgi-idx-topk-a-d52820055-tc-cx.json').read_text());assert s['source']['commit']==p['commit']
i=importlib.util.spec_from_file_location('rb',r/'rtl_boundary.py');b=importlib.util.module_from_spec(i);i.loader.exec_module(b)
b.TIMEOUT=None;b.SRC_CAP=float('inf');b.CACHE=r/'rtl_boundary_cache.json'
def show(commit,f):
 assert commit==p['commit'];return p['files'].get(f)
v=b.check(s,show);(r/'verdict.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v),flush=True)
sys.exit(0 if v['verdict']=='PASS' else 3)
