import json,sys
from pathlib import Path
sys.path.insert(0,'tools/die_plan');import die_sta_related as S
b=Path(sys.argv[1]);target=json.load(open(b/'clock/targets.json'));result=dict(source=str(b),routing='actual2W2S(.08width/.08spacing) M8/M9GRT50+PGobstructions',source_mismatch=sys.argv[3] if len(sys.argv)>3 else 'stagefit calibratedold1x;NDRmayrequirefreshfit',corners={})
for c in ('TT','FF'):
 rows={}
 for l in (b/f'out_{c}'/f'arr_{c}.txt').read_text().splitlines():
  a=l.split()
  if a and a[0]=='T':rows[a[1]]=list(map(float,a[2:]))
 f=S.spice_cal_factor(c,'inv');vals=[]
 for n,v in rows.items():
  tap=n.split('__',1)[1];early=target.get(tap,{}).get(c,0);vals.append(dict(tap=tap,late_raw_ps=v[0],core_early_ps=early,raw_effective_ps=v[0]+early,shared_model_effective_ps=v[0]*f+early,slew_ps=v[2]))
 result['corners'][c]=dict(taps=len(vals),shared_scale=f,raw_effective_window_ps=max(v['raw_effective_ps'] for v in vals)-min(v['raw_effective_ps'] for v in vals),shared_model_effective_window_ps=max(v['shared_model_effective_ps'] for v in vals)-min(v['shared_model_effective_ps'] for v in vals),min_raw=min(vals,key=lambda x:x['raw_effective_ps']),max_raw=max(vals,key=lambda x:x['raw_effective_ps']),min_shared=min(vals,key=lambda x:x['shared_model_effective_ps']),max_shared=max(vals,key=lambda x:x['shared_model_effective_ps']),max_slew_ps=max(v['slew_ps'] for v in vals),rows=vals)
 print(c,json.dumps({k:v for k,v in result['corners'][c].items() if k!='rows'}))
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
