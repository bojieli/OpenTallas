import hashlib,json,re,subprocess
from pathlib import Path
base=Path('/var/tmp/codex-static-k-0815/head9ae')
binary=base/'obj_0/Vtb_qkd_static_k_issuer'
profiles=[]
for t in (1,128,1000,2048,4096,4300,4500,6144,8192):
 for s in range(4):
  for e in range(8):
   p=subprocess.run([str(binary),f'+T={t}',f'+S={s}',f'+E={e}'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   lines=[x for x in p.stdout.splitlines()if x.startswith('STATIC_K PASS')]
   rows=[int(re.search(r' req=(\d+)',x).group(1))for x in lines]
   r=dict(T=t,stack=s,engine=e,rc=p.returncode,layers=len(lines),rows_each=rows[0]if rows else None,rows_total=sum(rows))
   profiles.append(r)
   (base/'context_profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
   if p.returncode!=0 or len(lines)!=36:
    (base/'context_FAIL.log').write_text(p.stdout)
    print(json.dumps(r),flush=True);print(p.stdout,flush=True);raise SystemExit(1)
 print(f'HEAD_CONTEXT_PASS T={t} profiles={len(profiles)} rows={sum(x["rows_total"]for x in profiles)}',flush=True)
summary=dict(source='9ae48c437',binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),profiles=len(profiles),layers=len(profiles)*36,exact_rows=sum(x['rows_total']for x in profiles),production_qualified=False)
(base/'context_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
