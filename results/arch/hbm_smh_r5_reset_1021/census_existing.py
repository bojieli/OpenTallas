import json,subprocess,os,shlex,hashlib
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/codex-smh-r5-reset-1340-retry-1021')
image=subprocess.check_output(['docker','image','inspect','openroad/orfs:latest','--format','{{.Id}}']).decode().strip()
print('EXISTING_NATIVE_IMAGE',image,flush=True)
rc=0
for f,old in [('n_m','smh_rp5n_m-20261021-132207'),('n_f','smh_rp5n_f-20261021-132221')]:
 work=root/('native_'+f)
 previous=json.loads((Path('/srv/opentallas-scratch/claude/ref_gate')/old/'routes/gate/work/orfs/native_census.json').read_text())
 net=Path(previous['netlist']['path']);hostnet=work/net.relative_to('/work')
 print('EXISTING_MAPPED_SHA256',f,hashlib.sha256(hostnet.read_bytes()).hexdigest(),flush=True)
 args=['python3','/src/tools/ref_tile/native_census.py','--netlist',str(net),'--top',previous['top'],'--out','/work/native_census_existing.json','--kit','smh_rp5'+f]
 for lib in previous['liberty']:args+=['--liberty',lib['path']]
 cmd=['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}','-v',f'{root}/src:/src:ro','-v',f'{work}:/work',image]+args
 one=subprocess.call(cmd);rc=max(rc,one)
 print('EXISTING_NATIVE_EXIT',f,one,flush=True)
 if (work/'native_census_existing.json').exists():
  d=json.loads((work/'native_census_existing.json').read_text());print('EXISTING_NATIVE_RESULT',f,d['status'],d['max_dynamic_loads'],len(d['violations']),len(d['role_errors']),flush=True)
raise SystemExit(rc)
