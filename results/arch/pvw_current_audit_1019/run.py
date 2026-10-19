import json,subprocess,hashlib
from pathlib import Path
D=Path('/srv/opentallas-scratch/claude/pvw-current-audit-1019')
base=['python3',str(D/'audit.py'),'--root','/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-4db097403-codexmub','--report','/srv/opentallas-scratch/claude/kv-exact-padgap-1019/gen7_strict/port_bind_v2.json','--out',str(D/'roles.json')]
results=[]
for mutant,pattern in [(None,'PVW_ROLE_AUDIT_PASS'),('primary_bit','AssertionError'),('relay_bit','RELAY_BIT_IDENTITY'),('status_reader','AssertionError')]:
 name=mutant or 'positive';p=subprocess.run(base+(['--mutant',mutant] if mutant else []),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(D/(name+'.log')).write_text(p.stdout)
 ok=(p.returncode!=0 if mutant else p.returncode==0) and pattern in p.stdout;results.append(dict(case=name,exit=p.returncode,expected_pattern=pattern,pass_=ok,log_sha256=hashlib.sha256(p.stdout.encode()).hexdigest()));print(name,'PASS' if ok else 'FAIL',p.returncode,flush=True)
 if not ok:print(p.stdout,flush=True);break
(D/'checks.json').write_text(json.dumps(results,indent=2)+'\n');assert len(results)==4 and all(r['pass_'] for r in results)
