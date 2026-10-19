from pathlib import Path
import json,math,sys
from collections import Counter
P=Path('.').resolve()
code=(P/'reset_sink_reach.py').read_text();exec(code[:code.index('locations=q')])
graph=json.loads((P/'reset_sink_repair.json').read_text());pos=graph['positions'];connected=set(graph['parents']);buck.clear()
for n in connected:
 x,y,*_=pos[n];buck[int(x//B),int(y//B)].append(n)
table=json.loads((P.parent/'src/results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json').read_text());masters=table['masters'];blocks=plan['blocks'];rows=[];fail=[]
def buried(x,y,own):return any(b['name']!=own and b['x']+.5<x<b['x']+b['w']-.5 and b['y']+.5<y<b['y']+b['h']-.5 for b in blocks)
for b in blocks:
 m=masters[b['master']];reset=m.get('rst')
 if not reset:continue
 module=m['module'];rp,pol=reset
 if module in inventory:
  rr=inventory[module]['pins'].get(rp)
  if not rr:fail.append({'block':b['name'],'why':'closed reset pin missing','module':module,'pin':rp});continue
  rect=shift(rr,b['x'],b['y']);hit=serve(rect)
  if hit:rows.append({'block':b['name'],'module':module,'pin':rp,'kind':'actual_closed_LEF','source':hit[1],'min_rect_um':hit[0],'rectangles':rect,'polarity':pol})
  else:fail.append({'block':b['name'],'why':'actual closed reset pin unserved','rectangles':rect})
 else:
  x,y,w,h=b['x'],b['y'],b['w'],b['h'];cand=[(x+w/2,y)]
  for f in range(1,40):
   t=f/40.;cand.extend([(x+w*t,y),(x+w*t,y+h),(x,y+h*t),(x+w,y+h*t)])
  candidates=[]
  for k,(px,py) in enumerate(cand):
   if buried(px,py,b['name']):continue
   hit=serve([(px,py,px,py)])
   if hit:candidates.append((k!=0,hit[0],px,py,hit[1]))
  if not candidates:fail.append({'block':b['name'],'why':'standin perimeter has no connected source'})
  else:
   _,d,px,py,parent=min(candidates)
   rows.append({'block':b['name'],'module':module,'pin':rp,'kind':'flexible_STANDIN_no_hardened_parent_fit','source':parent,'min_rect_um':d,'point':[px,py],'polarity':pol,'inverter_required':pol=='high'})
summary={'scope':'BLOCK_RESET_SOURCE_PIN_GEOMETRY_DIAGNOSTIC_NOT_NEW_BIND_OR_HARDENED_PARENT_FIT','reset_blocks':len(rows)+len(fail),'served':len(rows),'failures':fail,'models':dict(Counter(r['kind'] for r in rows)),'max_min_rect_um':max(r['min_rect_um'] for r in rows),'inverter_required':[r['block'] for r in rows if r.get('inverter_required')],'remaining':'Standin port geometry/active-high inverter must be emitted and physically checked; root2/new calendars/actual wire obstacles, RC, native clocks and child slot fit remain OWED.'}
(P/'reset_block_reach.json').write_text(json.dumps({'summary':summary,'blocks':rows},indent=1)+'\n');print(json.dumps(summary,indent=2));raise SystemExit(1 if fail else 0)
