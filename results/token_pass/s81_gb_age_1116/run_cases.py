from pathlib import Path
import json,subprocess as S,time
r=Path(__file__).resolve().parent;out=r/'runs';out.mkdir(exist_ok=False)
rep=json.load(open(r/'programme/programme.json'));end=max(x['end'] for x in rep['programmes'].values())+22+64
cases=[('original_direct','old',0,[]),('current_direct','old',1,[]),('candidate','advance1',2,[]),('wrong_date','old',2,[]),('wrong_tag','advance1',2,['+bad_tag=1']),('counterfactual_retime','advance1',2,['+fix_tag=1']),('skew','advance1',2,['+skew=1'])]
rows=[]
for dd in [0,12,13,22]:
 d=out/f'dd{dd}';d.mkdir()
 for name,programme,leg,extra in cases:
  cmd=[str(r/'obj/Vtb_native_go_split'),f'+leg={leg}',f'+gb={int(leg>0)}',f'+dd={dd}',f'+T={end}',f'+OT_ROM_DIR={r/"programme"/programme}',*extra]
  t=time.monotonic()
  with (d/(name+'.log')).open('w') as f:p=S.run(cmd,stdout=f,stderr=S.STDOUT)
  rows.append(dict(dd=dd,name=name,returncode=p.returncode,seconds=time.monotonic()-t))
(r/'runtime.json').write_text(json.dumps({'cases':rows,'cycles_per_case':end},indent=2)+'\n')
print('COLLECTED_NATIVE_GB_CASES',len(rows),'cycles',end,'unexpected_process_errors',[x for x in rows if x['returncode']!=0])
