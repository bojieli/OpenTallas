#!/usr/bin/env python3
"""Reserve wider physical SVG relay crosses without reducing usable logic area."""
import json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
base=ROOT/'results/arch/hbm_release_r16_1021/planlM'
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
for f in base.iterdir():
 if f.is_file() and f.name not in ['plan.png','report.json']:shutil.copyfile(f,out/f.name)
g=json.load(open(out/'grants_d4g.json'));p=json.load(open(out/'compact.P.json'))
slots={s['name']:s for s in g['slots']};records=[]
# Remove the old local SW5/6 upward escape: the wider cross now needs the
# same legal south band as its peers, below the unchanged SM bodies.
for k in ['SW5','SW6']:
 p['pc_'+k]['y']=round(p['pc_'+k]['y']-194.4,6)
 slots['cp_svg_'+k]['origin']['y']=round(slots['cp_svg_'+k]['origin']['y']-194.4,6)
# Reserve actual side whitespace for the existing tiny fixed leaves. Move
# the old WBK body along its existing SM-column corridor, without resizing it.
for n,x,y in [('fs_SW',9363.6,1987.2),('fs_NE',15055.2,30952.8),('fs_SE',15055.2,1998.),('sfault_SE',15055.2,1954.8)]:
 slots[n]['origin'].update(x=x,y=y)
slots['wbk_SW']['origin']['y']=round(slots['wbk_SW']['origin']['y']+432,6)
for name,s in sorted(slots.items()):
 if not name.startswith('grid_svg_'):continue
 qk=name[len('grid_svg_'):];box=p['pc_'+qk];north=qk.startswith('N')
 old=dict(w=s['outline']['w'],h=s['outline']['h'],x=s['origin']['x'],y=s['origin']['y'])
 old_usable=(old['w']-43.2)*(old['h']-43.2)
 w,h=round(old['w']+172.8,6),round(old['h']+172.8,6)
 assert abs((w-216)*(h-216)-old_usable)<.001
 # Preserve PC centre; side margins now accommodate actual XC and VMKS boxes.
 box['x']=round(box['x']-43.2,6);box['w']=round(box['w']+86.4,6)
 if not north:
  box['h']=round(box['h']+172.8,6)
  slots['cp_svg_'+qk]['origin']['y']=round(slots['cp_svg_'+qk]['origin']['y']+172.8,6)
 else:box['h']=round(box['h']+172.8,6)
 x=round(round((box['x']+(box['w']-w)/2)/.216)*.216,3)
 y=round(box['y']+4.32,3) if north else round(box['y']+box['h']-h-4.32,3)
 s['outline']=dict(w=w,h=h);s['origin'].update(x=x,y=y)
 cx,cy=round((w-216)/2,6),round((h-216)/2,6)
 s['reserved_channels']=[dict(kind='feedthrough_relay_column',x_um=[cx,round(cx+216,6)],y_um=[0,h],owner='die',master_keepout='hard placement + M5/M6 route'),dict(kind='feedthrough_relay_row',x_um=[0,w],y_um=[cy,round(cy+216,6)],owner='die',master_keepout='hard placement + M5/M6 route')]
 s['notes']='R16M actual L capacity-failure correction: 216um relay cross; same four solid quadrants and exact usable area. SYNTH physical reservation only; hardened successor must implement matching keepouts. No CLOSED/source promotion.'
 records.append(dict(instance='svg_'+qk,before=old,after=dict(w=w,h=h,x=x,y=y),old_usable_um2=old_usable,new_usable_um2=(w-216)*(h-216),solid_quadrants_um=[cx,cy],PC_band=box))
assert len(records)==16
actual=json.load(open(sys.argv[2]))['placement'];updates={}
for r in records:
 updates[r['instance']]=dict(actual[r['instance']],**r['after'])
for n in ['cp_'+r['instance'] for r in records]+['fs_SW','fs_NE','fs_SE','sfault_SE','wbk_SW']:
 updates[n]=dict(actual[n],**{k:slots[n]['origin'][k] for k in ['x','y']})
new=dict(actual,**updates);checks=[]
for n,a in updates.items():
 bad=[];dynamic=[]
 for k,b in new.items():
  if k==n:continue
  dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])
  dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
  if dx>.001 and dy>.001:
   (dynamic if b['rule'].startswith('region ') else bad).append(k)
 assert not bad,(n,bad)
 checks.append(dict(instance=n,after=a,overlaps_fixed=bad,dynamic_normal_firstfit_rehome=dynamic))
model=dict(status='PHYSICAL_GEOMETRY_MODEL_NOT_CAPACITY_PASS',base_source='e5f1c81dd/L',actual_failure=dict(hops=54,forced=308,windows=18,north_worst=[2.201,2.102]),die_um=g['floorplan']['die_um'],SVG_cross_um=216,usable_area_change_um2=0,records=records,actual_fixed_box_checks=checks,rtl_changes=0,cycle_credit=0,WBK='Old source only; c9 newbody area/native/functional qualification separate, no alias',required='Actual GEN placement legality + P/Q + strict S4 capacity; no failed geometry routing')
g['floorplan']['r16m_svg_cross']=model
for fn,d in [('grants_d4g.json',g),('compact.P.json',p),('svg_cross_model.json',model)]: (out/fn).write_text(json.dumps(d,indent=1)+'\n')
print('SVG_CROSS_MODEL16 usable_area_delta0; actualGEN/S4 pending')
