#!/usr/bin/env python3
"""Collect existing CUT-B evidence only. Never compile or execute a replay."""
from pathlib import Path
import json, subprocess
HERE=Path(__file__).resolve().parent
HOST='ot-epyc9'
REMOTE='/srv/opentallas-scratch/claude/codex-tok-head-b-connected-2100'

def remote(script):
    return subprocess.run(['ssh',HOST,'python3','-'],input=script,text=True,capture_output=True,check=True).stdout

status=json.loads(remote("""from pathlib import Path
import json
r=Path('/srv/opentallas-scratch/claude/codex-tok-head-b-connected-2100/out')
print(json.dumps({n:(r/n).exists() for n in ['result.json','b.log','b_mut_rec.log','b_mut_slice.log','binary_b.sha256','binary_b_mut_slice.sha256']}))
"""))
print(json.dumps(status,sort_keys=True))
if not all(status.values()):
    raise SystemExit('PENDING existing run; no complete receipt collected')
for sub in ['raw','build/obj_b','build/obj_b_mut_slice']:
    (HERE/sub).mkdir(parents=True,exist_ok=True)
subprocess.run(['rsync','-a','--include=*/','--include=*.json','--include=*.log','--include=*.time','--include=*.exit','--include=*.hex','--include=*.txt','--include=*.sha256','--exclude=obj_*/','--exclude=gold/','--exclude=a_mut/','--exclude=*',f'{HOST}:{REMOTE}/out/',str(HERE/'raw')+'/'],check=True)
for obj in ['obj_b','obj_b_mut_slice']:
    subprocess.run(['rsync','-a','--include=Vtb_s81hd_diecut__verFiles.dat','--include=Vtb_s81hd_diecut.mk','--include=Vtb_s81hd_diecut__ver.d','--exclude=*',f'{HOST}:{REMOTE}/out/{obj}/',str(HERE/'build'/obj)+'/'],check=True)
identity=remote("""from pathlib import Path
import json,hashlib,subprocess,re
r=Path('/srv/opentallas-scratch/claude/codex-tok-head-b-connected-2100')
result={'binaries':{},'runtime':{},'tools':{},'source_mismatches':[]}
manifest=json.loads((r/'source_identity.json').read_text())
result['source_identity_sha256']=hashlib.sha256((r/'source_identity.json').read_bytes()).hexdigest()
for entry in manifest['files']:
 if hashlib.sha256((r/entry['staged']).read_bytes()).hexdigest()!=entry['sha256']:result['source_mismatches'].append(entry['staged'])
result['extra_inputs']={}
for pattern in ('tools/*.py','tools/*.sv','bind/*','img/*','out/a.json','out/rec.hex','out/verilator_version.txt'):
 for q in r.glob(pattern):
  if q.is_file():result['extra_inputs'][str(q.relative_to(r))]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
for n in ('b','b_mut_slice'):
 p=r/'out'/('obj_'+n)/'Vtb_s81hd_diecut'
 result['binaries'][n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 t=subprocess.run(['ldd',str(p)],capture_output=True,text=True,check=True).stdout
 result['runtime'][n]={'ldd':t,'libraries':{}}
 for path in re.findall(r'(?:=> )?(/[^ \\n]+)',t):
  q=Path(path)
  if q.is_file():result['runtime'][n]['libraries'][str(q)]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'bytes':q.stat().st_size}
for cmd in (['g++','--version'],['ldd','--version'],['uname','-a']):
 result['tools'][' '.join(cmd)]=subprocess.run(cmd,text=True,capture_output=True,check=True).stdout
print(json.dumps(result,indent=2))
""")
(HERE/'build'/'binary_runtime_identity.json').write_text(identity)
print('Collected existing completed CUT-B evidence; no replay launched.')
