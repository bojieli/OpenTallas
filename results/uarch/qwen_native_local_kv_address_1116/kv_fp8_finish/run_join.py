#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
H=Path(sys.argv[1]);res={}
for c in json.load(open(H/'join_cases.json')):
    o=H/'join'/(c['name']+'.out')
    subprocess.run([str(H/'obj1/Vtb_svc_local_dim'),f"+INPUT={H/'join'/c['name']/'stim.hex'}",f"+OUTPUT={o}"],check=True,capture_output=True,timeout=250)
    L=o.read_text().splitlines();w=[l.split()[3] for l in L if l.startswith('WORD')];f=[l for l in L if l.startswith(('FAULT','KVINBAD'))]
    exp=c['expect_words'];ok=(w==exp and not f and c['rtl_equals_golden_fp32']);res[c['name']]=dict(ok=ok,words=len(w),faults=len(f),rtl_equals_golden=c['rtl_equals_golden_fp32'])
v=dict(all_ok=all(x['ok'] for x in res.values()),cases=res);(H/'join_verdict.json').write_text(json.dumps(v,indent=1)+'\n')
for n,x in res.items():print(n,x)
print('KV_FP8_FINISH_JOIN','PASS' if v['all_ok'] else 'FAIL')
