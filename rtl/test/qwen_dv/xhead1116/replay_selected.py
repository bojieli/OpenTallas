import json,subprocess,re,hashlib
from pathlib import Path
P=Path(__file__).parent;meta=json.loads((P/'packets.json').read_text());results=[]
def point(op,lag=50,lead=30):
 record={'op':op,'go_lag':lag,'xpf_lead':lead,'cases':[],'pass':True}
 for sid in range(12):
  name=f'{op}_s{sid}';m=meta[name];rows=[int(x,16) for x in (P/(name+'.hex')).read_text().splitlines()];armword=rows[m['arm']]&((1<<453)-1);goword=rows[m['go']]&((1<<453)-1)
  rows=[w&~((1<<453)-1) for w in rows];arm=m['first_xt']-lead;go=m['last_xt']+lag
  if min(arm,go)<0:record['pass']=False;record['invalid_edge']=[arm,go];break
  rows[arm]|=armword;rows[go]|=goword
  fn=P/'probe.hex';fn.write_text('\n'.join(f'{w:0376x}' for w in rows)+'\n')
  for col in range(4):
   r=subprocess.run([str(P/'obj_actual/Vtb'),f'+input={fn}',f'+ncy={len(rows)}',f'+sid={sid}',f'+col={col}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   line=next((s for s in r.stdout.splitlines() if s.startswith('RESULT')),'');ok=r.returncode==0 and 'fault=0' in line and 'FAULT ' not in r.stdout
   record['cases'].append({'sid':sid,'col':col,'result':line,'pass':ok})
   if not ok:
    record['pass']=False;out=P/f'boundary_{op}_g{lag}_l{lead}_s{sid}_c{col}.log';out.write_text(r.stdout);record['failure_log']=out.name;break
  if not record['pass']:break
 results.append(record);(P/'selected_replay_progress.json').write_text(json.dumps(results,indent=2)+'\n');print(op,lag,lead,record['pass'],len(record['cases']),flush=True);return record['pass']
final=json.loads((P/'calibrated.json').read_text())['consumer']
for op,v in final.items():
 assert point(op,lag=v['go_lag'],lead=v['xpf_lead'])
 assert not point(op,lag=v['go_lag']-1,lead=v['xpf_lead'])
 assert not point(op,lag=v['go_lag'],lead=v['xpf_lead']-1)
(P/'selected_replay.json').write_text(json.dumps({'consumer':final,'points':results},indent=2)+'\n')
print('SELECTED_REPLAY_PASS',flush=True)
