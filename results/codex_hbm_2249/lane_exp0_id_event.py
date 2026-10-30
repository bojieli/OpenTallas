#!/usr/bin/env python3
"""PREP: existing1.8 static-ID contract for actual lane-exp0 free-ID master; no reset/cycle changes.
Requires matching native cut, recipe alias and explicit strap noFF/false-path flow support before adoption.
"""
import sys,json,copy,re,os,hashlib
from pathlib import Path
src,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False);r=json.loads((src/'die_plan.json').read_text())
old='ot_hbm_su_static_pgslice_lg__lane_exp0';new=old+'_id';tables={};changes=[]
for tn,t in r['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h.get('module')!=old:continue
  pf=h['pins_file'];npf='cores/'+new+'__440.64x207.36__static_id11.json'
  if pf not in tables:
   js=json.loads((src/pf).read_text());pins=js['pins']if isinstance(js,dict)else js
   assert not any('lane_lane_id'in str(x.get('name'))for x in pins)
   occupied=[p['x']for p in pins if p.get('layer')=='M5'and p.get('y',999)<1.]
   xs=[]
   for k in range(23,2200):
    x=round(k*.192,4)
    if x>436.32:break
    if all(abs(x-a)>=.192-1e-6 for a in occupied+xs):xs.append(x)
    if len(xs)==11:break
   assert len(xs)==11
   for i,x in enumerate(xs):pins.append(dict(name=f'lane_lane_id[{i}]',layer='M5',x=x,y=.096))
   if tables:
    assert pins==next(iter(tables.values()))[1],('oldlane0pinmapsdiffer',pf)
   tables[pf]=(npf,pins)
  q=int(re.search(r'_Q(\d+)_lane_exp0$',h['inst']).group(1));v=16*q;assert v in(0,16)
  h.update(module=new,pins_file=npf,parent_id_straps={'lane_lane_id':{'width':11,'value':v}})
  h['note']=h.get('note','')+' | CODEX static-ID canonical master; no clock/reset/data-cycle change; flow/cut support owed before adoption'
  for key in('lef','lib'):h.pop(key,None)
  for c in t.get('contents',[]):
   if c.get('inst')==h['inst']:c['module']=new
  for tap in t.get('clock',{}).get('taps',[]):
   if tap.get('budget_owner')==old and tap.get('name','').split('.')[0]==h['inst']:tap['budget_owner']=new
  changes.append(dict(type=tn,inst=h['inst'],old_master=old,new_master=new,strap=v,pins=npf))
assert len(changes)==4
(out/'cores').mkdir()
for f in (src/'cores').iterdir():os.symlink(f.resolve(),out/'cores'/f.name)
for _,(pf,pins)in tables.items():
 p=out/pf
 if not p.exists():p.write_text(json.dumps(pins,indent=1)+'\n')
for f in src.iterdir():
 if f.name in('die_plan.json','cores','core_macros.json','clock_entries.json','entries.json','gen','lat')or f.name.startswith('g0'):continue
 os.symlink(f.resolve(),out/f.name)
for fn in('core_macros.json','clock_entries.json','entries.json'):
 x=json.loads((src/fn).read_text())
 if fn=='core_macros.json':
  tab=x.get('cores',x)
  if old in tab:tab[new]=copy.deepcopy(tab[old]);tab[new]['note']='Same SRAM sites and outline; source ID canonicalization PREP only'
 elif fn=='entries.json':
  if old in x:x[new]=copy.deepcopy(x[old])
 else:
  for c in changes:
   if c['inst']in x.get(c['type'],{}):x[c['type']][c['inst']]['module']=new
 (out/fn).write_text(json.dumps(x,indent=1)+'\n')
(out/'die_plan.json').write_text(json.dumps(r,indent=1)+'\n')
rep=dict(state='PREP_NOT_ADOPTED',changes=changes,model=dict(data_cycles_added=0,outline_delta_um=[0,0],additional_quasi_static_pins_per_master=11,native_cell_count='NOT RUN'),recipe_override=dict(module=new,canonical_pin_map={'lane_lane_id':'lane_lane_id'},required_no_ff_false_path=['lane_lane_id']),requires=['canonical free-ID source wrapper','all-used-value0/16 lockstep+mutant','explicit strap shell and SDC support','native parent-cut alias','synthesis/LEC and new physical qualification'],sha=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest())
(out/'lane_exp0_id_report.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(rep))
