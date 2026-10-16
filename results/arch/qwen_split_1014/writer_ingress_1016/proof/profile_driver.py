import hashlib,json,re,subprocess
from pathlib import Path
base=Path('/var/tmp/codex-writer-ingress-0905/current')
binary=base/'obj_0_0_0/Vtb_qkd_static_writer_ingress'
profiles=[]
physical_group=[2,3,4,5,0,1,6,7]
for s in range(4):
 for g in range(8):
  p=subprocess.run([str(binary),f'+S={s}',f'+G={g}'],cwd=base,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  line=next((x for x in p.stdout.splitlines()if x.startswith('WRITER_INGRESS PASS')),'')
  match=re.search(r'cases(\d+) slots(\d+) sectors(\d+) transported(\d+) expected(\d+)',line)
  pos=[(s<<7)|i for i in range(128)]+[128,511,512,4095,4096,8190,8191]
  predicted=36*2*sum(4 for t in pos for logical in (t&7,((t>>4)&3)*2+(t&1))if ((t>>7)&3)==s and physical_group[logical]==g)
  record=dict(stack=s,group=g,rc=p.returncode,independently_expected_transfers=predicted,result=line)
  if match:record.update(cases=int(match[1]),slots=int(match[2]),global_sectors=int(match[3]),transported=int(match[4]),expected=int(match[5]))
  profiles.append(record)
  (base/'profiles.json').write_text(json.dumps(profiles,indent=2)+'\n')
  if p.returncode!=0 or not match or record['transported']!=predicted or record['expected']!=predicted:
   (base/'profile_FAIL.log').write_text(p.stdout);print(p.stdout,flush=True);raise SystemExit(1)
 print(f'WRITER_STACK_PASS stack={s} profiles={len(profiles)} transported={sum(x["transported"]for x in profiles)}',flush=True)
summary=dict(source='9d4b7505b',binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),profiles=32,layer_runs=32*36*2,cohorts=sum(x['cases']for x in profiles),global_sectors=sum(x['global_sectors']for x in profiles),local_transported=sum(x['transported']for x in profiles),all128_destination_PC_faces_exercised=True,production_qualified=False)
(base/'profile_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
