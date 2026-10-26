import json,subprocess,sys
S='/home/ubuntu/scratch/binder4-1023/s81'; B='/home/ubuntu/wt/binder4-s81-1023/tools/die_plan/bind.py'
P=f'{S}/physical/die_plan/s81/die_plan.json'; O=f'{S}/b3r8'
plan=json.load(open(P)); r=json.load(open(f'{O}/bind_report.json'))
splits={t['type']:len(t['variants']) for t in r['type_splits']}
jobs=[]
for t,d in plan['partition_types'].items():
    if d.get('hard'): continue
    jobs.append((t,None,f'{O}/kit_rtl/{t}'))
    for k in range(1,splits.get(t,1)):
        jobs.append((t,f'{t}__v{k}',f'{O}/kit_rtl/{t}__v{k}'))
from concurrent.futures import ThreadPoolExecutor
def one(j):
    t,v,k=j
    cmd=['python3',B,'kit-rtl',P,'--out',O,'--type',t,'--kit',k,'--asbuilt',f'{S}/asb/asbuilt_v3_r8.json']+(['--variant',v] if v else [])
    p=subprocess.run(cmd,capture_output=True,text=True)
    last=(p.stdout+p.stderr).strip().splitlines()[-1] if (p.stdout+p.stderr).strip() else ''
    try: return (v or t, p.returncode, json.loads(last))
    except Exception: return (v or t, p.returncode, last[:300])
res=list(ThreadPoolExecutor(8).map(one,jobs))
json.dump(res,open(f'{O}/kit_rtl_summary.json','w'),indent=0)
bad=[x for x in res if x[1]!=0 or not isinstance(x[2],dict)]
print('kits',len(res),'failed',len(bad)); [print(b) for b in bad[:15]]
print('unbound',sum(x[2].get('unbound',0) for x in res if isinstance(x[2],dict)),'spare_out',sum(x[2].get('spare_out',0) for x in res if isinstance(x[2],dict)),'narrow',sum(x[2].get('narrow',0) for x in res if isinstance(x[2],dict)))
