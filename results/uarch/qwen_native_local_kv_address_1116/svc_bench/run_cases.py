import json,subprocess,sys
from pathlib import Path
H=Path('/srv/opentallas-scratch2/claude/tok-verify-2/svcb');gold=json.load(open(H/'fp8_inverse/golden256.json'))['word512_hex_msb_first']
ad=sys.argv[1] if len(sys.argv)>1 else '1'
res={}
for c in json.load(open(H/'cases.json')):
    o=H/f"{c['name']}.out"
    r=subprocess.run([str(H/f'obj{ad}/Vtb_svc_local_dim'),f"+INPUT={H/c['name']/'stim.hex'}",f"+OUTPUT={o}"],capture_output=True,text=True,timeout=250)
    L=o.read_text().splitlines();w=[l.split() for l in L if l.startswith('WORD')];f=[l for l in L if l.startswith('FAULT')];k=[l for l in L if l.startswith('KVINBAD')];sf=[l for l in L if l.startswith('SVCFAULT')]
    d=[x[3] for x in w]
    st='PASS' if d==gold and not f and not k else 'FAULT' if (f or k) else 'TYPED_DATA_FAIL' if len(d)==4 and d!=gold and not f and not k else 'OTHER'
    res[c['name']]=dict(expect=c['expect'],got=st,ok=st==c['expect'],words=len(w),tags=[x[2] for x in w],faults=len(f),kvinbad=len(k),svcfault=len(sf),rc=r.returncode)
v=dict(adapter=ad,all_ok=all(x['ok'] for x in res.values()),cases=res);(H/f'verdict{ad}.json').write_text(json.dumps(v,indent=1)+'\n')
for n,x in res.items():print(n,x)
print('SVC_LOCAL_DIM',ad,'PASS' if v['all_ok'] else 'FAIL')
