"""Open a right-hand street for q_sm2 final column, preserving every hardened core.
Estimate: 34.56um new right street; old 103.68um left street reduces to69.12um.
No core/pin/RTL or cycle change; clock taps follow shifted cores exactly.
usage: c25c_sm_street.py SRC OUT
"""
import hashlib,json,re,sys
from pathlib import Path
D,O=map(Path,sys.argv[1:3]);O.mkdir(parents=True,exist_ok=True);P=json.load(open(D/'die_plan.json'));t=P['partition_types']['q_sm2'];shift=-34.56
distributed='--distributed' in sys.argv[3:]
names={f'u_sm_t{r}{col}_{s}' for r in (0,1) for col in (range(1,8) if distributed else [7]) for s in 'ns'};rows=[]
def shift_for(n):return -17.28*min(int(re.search(r't[01]([0-7])_',n).group(1)),6) if distributed else -34.56
for c in t['hard_cores']:
 if c['inst'] not in names:continue
 old=c['origin_um'][0];shift=shift_for(c['inst']);c['origin_um'][0]=round(old+shift,4);c['note']=c.get('note','')+' | C25c: whitespace redistributed to open right street; hardened master unchanged'
 rows.append({'core':c['inst'],'old_origin_x':old,'new_origin_x':c['origin_um'][0]})
for c in t.get('contents',[]):
 if c['inst'] in names:c['origin_um'][0]=round(c['origin_um'][0]+shift_for(c['inst']),4)
for tp in t.get('clock',{}).get('taps',[]):
 if tp['name'].split('.')[0] in names:tp['xy'][0]=round(tp['xy'][0]+shift_for(tp['name'].split('.')[0]),4)
assert not t.get('internal_stations'), 'shifted station endpoints need explicit handling'
assert len(rows)==(28 if distributed else 4)
for c in t['hard_cores']:
 if c['inst'] not in names:continue
 a,b=c['origin_um'];w,h=c['outline_um']
 for q in t['hard_cores']:
  if q is c:continue
  x,y=q['origin_um'];qw,qh=q['outline_um']
  assert not (a<x+qw-1e-6 and x<a+w-1e-6 and b<y+qh-1e-6 and y<b+h-1e-6),(c['inst'],q['inst'])
(O/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n')
report={'source_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'changes':rows,'new_right_street_um':103.68 if distributed else 34.56,'remaining_final_left_street_um':103.68 if distributed else 69.12,'other_gaps_um':86.4 if distributed else 103.68,'core_halfwidth_um':315.36,'cycles_added':0,'status':'ESTIMATE: demand-mode streets.check must confirm connectivity/capacity on composed plan; no route approval'}
(O/'c25c_sm_street_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
