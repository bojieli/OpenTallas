"""Compose the approved complete SPB PHY/street tuple on both explicit physical types.
Does not claim the legacy internal station skeleton is the native four-stage transport.
That skeleton's residuals are reported for replacement by the source-qualified native banks.
usage: compose_spb_street.py SRC OUT
"""
import copy,hashlib,json,shutil,sys
from pathlib import Path
SRC,OUT=map(Path,sys.argv[1:3]);P=json.loads((SRC/'die_plan.json').read_text());before=copy.deepcopy(P)
D=103.68;report={'schema':'hbm-spb-street.v2','source_sha256':hashlib.sha256((SRC/'die_plan.json').read_bytes()).hexdigest(),'delta_um':D,'types':{},'data_cycle_delta':0,'requires':['native SPB bank/clock/reset source composition','full PG solve','full image review and actual pin access']}
for tn in ['q_spb0','q_spb0__physical_v1']:
 t=P['partition_types'][tn];core=next(h for h in t['hard_cores'] if h['inst']=='u_lk_S0');assert core['origin_um']==[0.,34.56],(tn,core['origin_um']);core['origin_um'][0]=D
 for c in t.get('contents',[]):
  if c.get('inst')=='u_lk_S0' and 'origin_um' in c:c['origin_um'][0]=round(c['origin_um'][0]+D,4)
 for tap in t.get('clock',{}).get('taps',[]):
  if tap['name'].split('.')[0]=='u_lk_S0':tap['xy'][0]=round(tap['xy'][0]+D,4)
 old=t['clock']['keepouts_um'];assert old==[[0.,0.,663.688,1113.64],[0.,0.,600.048,1050.]]
 # The old physical PHY begins at partition x0 while its dedicated PG halo
 # extends -63.64. Moving the entire tuple D makes the new PG edge40.04.
 t['clock']['keepouts_um']=[[40.04,0.,767.368,1113.64],[103.68,0.,703.728,1050.]]
 changes=[]
 for s in t.get('internal_stations',[]):
  for point,role in [('from_um','launch'),('to_um','capture')]:
   if s.get(role,'').startswith('u_lk_S0'):
    a=s[point][:];s[point][0]=round(a[0]+D,4);changes.append({'conn':s['conn'],'endpoint':point,'old':a,'new':s[point]})
  # Core/PHY spaces prohibit FFs, while native M6/M7 signal wires can cross
  # the M5 EP. Never silently accept old FF centres inside full PHY/PG.
 bad=[]
 for i,s in enumerate(t.get('internal_stations',[])):
  for k,(x,y) in enumerate(s.get('regs_um',[])):
   if 40.04<=x<=767.368 and 0<=y<=1113.64:bad.append({'index':i,'conn':s['conn'],'stage':k,'xy':[x,y]})
 report['types'][tn]={'endpoints_followed':changes,'legacy_station_pg_intersections':bad,'native_bank_replacement_required':bool(bad)}
sm=P['partition_types']['q_sm2']['clock']['keepouts_um'];clip=[5771.52,0.,5806.08,1113.64];assert clip in sm;sm.remove(clip)
for rows,key in [(P['die']['io'],'io'),(P['die']['pg']['domains'],'pg')]:
 for r in rows:
  if r['name'] not in [f'{"io" if key=="io" else "phy"}_{side}_spb0_u_lk_S0' for side in ['NW','NE']]:continue
  delta=D if '_NW_' in r['name'] else -D
  r['rect_um']=[round(v+(delta if k in (0,2) else 0),4) for k,v in enumerate(r['rect_um'])]
  if key=='pg':r['bumps']['rect_um']=[round(v+(delta if k in (0,2) else 0),4) for k,v in enumerate(r['bumps']['rect_um'])]
# Both explicit physical variants carry the identical PHY tuple, and dedicated
# bump+domain boxes follow it. Every SM hard core remains byte-identical.
for tn,t in P['partition_types'].items():
 if tn.startswith('q_sm'):assert t['hard_cores']==before['partition_types'][tn]['hard_cores']
OUT.mkdir(parents=True,exist_ok=False)
for f in SRC.iterdir():
 if f.name!='die_plan.json':
  if f.is_dir():shutil.copytree(f,OUT/f.name)
  else:shutil.copy2(f,OUT/f.name)
(OUT/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n');report['plan_sha256']=hashlib.sha256((OUT/'die_plan.json').read_bytes()).hexdigest();(OUT/'spb_street_composition.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
