#!/usr/bin/env python3
"""Move whole xload control groups into real SU-column whitespace; unchanged outline/source."""
import copy,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/plangM'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
manifest=json.load(open(sys.argv[2]));actual=manifest['placement']
moves={}
for q,delta in [('NW',-2376.),('SW',-2376.),('NE',2505.6),('SE',2505.6)]:
 for suffix in ['ctl','aqhi','aqlo']:
  name='xl_'+q+'_'+suffix;moves[name]=round(actual[name]['x']+delta,6)
checks=[]
for name,x in moves.items():
 r=dict(actual[name],x=x);bad=[]
 for n,s in actual.items():
  if n==name:continue
  dx=min(r['x']+r['w'],s['x']+s['w'])-max(r['x'],s['x'])
  dy=min(r['y']+r['h'],s['y']+s['h'])-max(r['y'],s['y'])
  if dx>0.001 and dy>0.001:bad.append(n)
 assert not bad,(name,bad)
 checks.append(dict(name=name,before=actual[name],after=r,overlaps=bad))
for f in base.iterdir():
 if f.is_file():shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'))
for name,x in moves.items():
 slot=next(s for s in g['slots'] if s['name']==name)
 assert abs(slot['origin']['y']-actual[name]['y'])<0.001
 slot['origin']['x']=x;slot['notes']+='; R16H whole xload group moved into existing SU corridor, Y and shape unchanged'
 if name in p:p[name]['x']=x
model=dict(status='GEOMETRY_MODEL_ONLY',base='debd840d3/plangM',outline_um=g['floorplan']['die_um'],
 reason='Measured E xload/SU capacity1.477NW and1.239SW; relocate whole groups into actual free SU-column corridor',
 placement_checks=checks,all_other_blocks='unchanged',rtl_source='unchanged',cycle_credit=0,
 remaining='Actual GEN/pins/S4 required; no failed capacity route')
g['floorplan']['r16h_xload_corridor']=model
(out/'grants_d4g.json').write_text(json.dumps(g,indent=1)+'\n')
(out/'compact.P.json').write_text(json.dumps(p,indent=1)+'\n')
(out/'xload_corridor_model.json').write_text(json.dumps(model,indent=1)+'\n')
print('XLOAD_CORRIDOR_MODEL',json.dumps(model))
