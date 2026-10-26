import json,subprocess
from concurrent.futures import ThreadPoolExecutor
S='/home/ubuntu/scratch/binder4-1023/s81'; B='/home/ubuntu/wt/binder4-s81-1023/tools/die_plan/bind.py'
P=f'{S}/physical/die_plan/s81/die_plan.json'; O=f'{S}/b3r8'
plan=json.load(open(P)); r=json.load(open(f'{O}/bind_report.json'))
res=json.load(open(f'{O}/kit_rtl_summary.json'))
fail=[n for n,rc,d in res if rc!=0 and 'different parameters' in str(d)]
spl={t['type']:t['variants'] for t in r['type_splits']}
jobs=[]
for n in fail:
    t,_,v=n.partition('__v'); t=n.split('__v')[0]
    if t in spl:
        k=int(n.split('__v')[1]) if '__v' in n else 0
        insts=spl[t][k]
    else:
        insts=[p['name'] for p in plan['partitions'] if p['type']==t]
    for i in insts: jobs.append((t, n if '__v' in n else None, i))
def one(j):
    t,v,i=j
    cmd=['python3',B,'kit-rtl',P,'--out',O,'--type',t,'--instance',i,'--kit',f'{O}/kit_rtl/{v or t}@{i}','--asbuilt',f'{S}/asb/asbuilt_v3_r8.json']+(['--variant',v] if v else [])
    p=subprocess.run(cmd,capture_output=True,text=True); o=(p.stdout+p.stderr).strip().splitlines()
    try: return (f'{v or t}@{i}',p.returncode,json.loads(o[-1]))
    except Exception: return (f'{v or t}@{i}',p.returncode,o[-1][:300] if o else '')
out=list(ThreadPoolExecutor(8).map(one,jobs))
res=[x for x in res if x[0] not in fail]+out
json.dump(res,open(f'{O}/kit_rtl_summary.json','w'),indent=0)
bad=[x for x in res if x[1]!=0]
print('jobs',len(jobs),'kits total',len(res),'failed',len(bad)); [print(b) for b in bad[:10]]
