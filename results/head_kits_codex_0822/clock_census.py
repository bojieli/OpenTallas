#!/usr/bin/env python3
"""Complete FT clock inventory with the planned synchronous reset/START relay bodies before build."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
# Runtime standalone copy may live outside the repository.
if not (Path(__file__).resolve().parents[2]/'tools/die_plan').is_dir():sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-kits-0822/tools/die_plan')
import schema as S,gen_phys as G,reset_tree as R
src=Path(sys.argv[1]);out=Path(sys.argv[2]);raw=S.load(src);records=[]
if '--freeze-inputs' in sys.argv:
 baseline=S.Plan(raw,src);choices=R.wf_solve(baseline)['choice']
 raw['reset']['in_sites']={n:list(xy) for n,xy in choices.items()}
 frozen=S.Plan(raw,src);again=R.wf_solve(frozen)['choice']
 if choices!=again:raise SystemExit('published reset input coordinate changed by explicit siting')
 out.parent.mkdir(parents=True,exist_ok=True)
 out.with_suffix('.reset_choices.json').write_text(json.dumps(raw['reset']['in_sites'],indent=1)+'\n')
 print('preserved published reset input coordinates',len(choices),flush=True)

def model(tn):
 while True:
  P=S.Plan(raw,src);coords={(round(x,6),round(y,6)) for _,x,y in R._taps(P,tn)}
  rt=raw['partition_types'][tn].setdefault('reset',{})
  rows=rt.get('local_taps_um',[]);keep=[p for p in rows if tuple(round(v,6) for v in p) not in coords]
  if len(keep)==len(rows):return P
  print('deduplicate reset consumers',tn,len(rows)-len(keep),flush=True)
  rt['local_taps_um']=keep

for tn in sys.argv[3].split(','):
 ck=raw['partition_types'][tn]['clock'];initial=model(tn);old=R._wf_type_tree(initial,tn);added=set();it=0
 while True:
  P=model(tn);T=R._wf_type_tree(P,tn);taps=G.clock_pins(P,tn)
  points=sorted(set(tuple(r['xy']) for r in T['relays']))
  missing=[xy for xy in points if min(abs(xy[0]-x)+abs(xy[1]-y) for _,x,y in taps)>150.]
  worst=max((min(abs(a-x)+abs(b-y) for _,x,y in taps) for a,b in points),default=0)
  if not missing:break
  rows=ck.setdefault('sink_sites_um',[]);before=len(rows)
  for xy in missing:
   key=(round(xy[0],4),round(xy[1],4))
   if key not in added:rows.append([*key,2]);added.add(key)
  if len(rows)==before:raise SystemExit(f'{tn}: planner cannot cover declared relay census, worst={worst}')
  it+=1
  print('census pass',tn,it,'new sites',len(missing),'worst',worst,flush=True)
 records.append(dict(type=tn,passes=it,added_sink_sites=len(added),taps=len(taps),max_planned_relay_tap_um=round(worst,3),old_reset_depth=old['depth'],new_reset_depth=T['depth'],boot_delta=T['depth']-old['depth']))
print(json.dumps(records[-1]),flush=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(raw,indent=1)+'\n');out.with_suffix('.clock_census.json').write_text(json.dumps(records,indent=1)+'\n');print(json.dumps(records))
