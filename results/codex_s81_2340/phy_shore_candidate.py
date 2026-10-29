#!/usr/bin/env python3
"""Prepare ES-only shoreline source variants for planning; no physical adoption."""
import copy,importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,gen_phys as G,die_trial as D,clock_landing_plan as CL,die_io as IO
sp=importlib.util.spec_from_file_location('s12','results/die_s81_19_1028/scripts/recompose_s12.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
raw,_=m.uncompose(json.load(open(sys.argv[1])));est=json.load(open(sys.argv[2]));P=S.Plan(raw);changed=[]
for part in ('lk_ES0','lk_ES1'):
 old=P.parts[part]['type'];new=old+'_es_shore';t=copy.deepcopy(P.types[old]);t['module']=t['module']+'_es_shore'
 t['note']=t.get('note','')+'; SOURCE CANDIDATE ONLY: shoreline PHY moved with same guard, four-side digital frame; no physical adoption'
 for c in t['contents']:
  if c['inst']=='u_phy':c['origin_um']=est['macro_um'][:2]
 t['clock']['keepouts_um']=[est['domain_um']]
 t['clock']['tap_um']=[est['outline_um'][0]-58.8,460.576]
 if part=='lk_ES0':
  for slot in t['ft_slots']:
   e=next(x for x in est['slots'] if x['name']==slot['name']);slot['stations']=e['stations'];slot['bit_site_cell_um']=[1.08,.27]
   slot['bit_sites_um']=[[[round((c[0]+(bit%16-7.5)*1.08)/.054)*.054,round((c[1]+(bit//16-15.5)*.27)/.27)*.27] for bit in range(slot['width']+1)] for c in e['bank_centres_um']]
  t['die_ft_bands']=[dict(dir='EW',span_um=[0,32.4],layers=['M4','M5','M6','M7'],die_share=.8),dict(dir='NS',span_um=[0,32.4],layers=['M4','M5','M6','M7'],die_share=.8)]
  t['note']+='; FT0+6cycles and FT1+1cycle, explicit bit sites; .8 W/S routing reservation proposed, partition complement not yet generated'
 raw['partition_types'][new]=t
 for p in raw['partitions']:
  if p['name']==part:p['type']=new
 raw['reset']['in_sites'][new]=copy.deepcopy(raw['reset']['in_sites'][old])
 changed.append(dict(part=part,before_type=old,after_type=new))
P=S.Plan(raw)
def box(part,r):
 a=P.to_die(part,r[:2]);b=P.to_die(part,r[2:]);return [min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
for part in ('lk_ES0','lk_ES1'):
 d=next(d for d in raw['die']['pg']['domains'] if d['name']=='phy_'+part);io=next(d for d in raw['die']['io'] if d['part']==part and d['iface']=='serdes');d['rect_um']=box(part,est['domain_um']);d['phy_macro_um']=box(part,est['macro_um']);d['bumps']['rect_um']=d['phy_macro_um'];d['core_strip_um']=[box(part,r) for r in ([0,0,2885.76,32.4],[0,32.4,32.4,1084.16],[2768.16,32.4,2885.76,1084.16],[0,1084.16,2885.76,1226.88])];io['rect_um']=d['phy_macro_um'];io['sites']=IO.count_sites(io['rect_um'],io['pitch_um'],io.get('bump_exclude_um',()))
P=S.Plan(raw)
# Compare uncomposed predecessor to avoid counting removed landing cycles.
base,_=m.uncompose(json.load(open(sys.argv[1])));B=S.Plan(base);diff={n:P.lane_natural(n)['cycles']-B.lane_natural(n)['cycles'] for n in P.lanes};diff={n:v for n,v in diff.items() if v}
Path(sys.argv[3]).write_text(json.dumps(raw,indent=1));print(json.dumps(dict(changed=changed,lane_natural_cycle_delta=diff,clock_taps={n:len(S.tap_grid(P,P.parts[n]['type'])) for n in ('lk_ES0','lk_ES1')})),flush=True)
if len(sys.argv)>5:
 new,sc=CL.compose(raw,json.load(open(sys.argv[4])),plan_path=sys.argv[3],observer_part=m.OBS_PART,observer=dict(m.OBS));Path(sys.argv[5]).write_text(json.dumps(new,indent=1));Path(sys.argv[5]+'.sidecar.json').write_text(json.dumps(sc,indent=1));print(json.dumps(dict(collector={k:sc['collector'][k] for k in ('placement_failures','max_die_hop_um','boot_budget')})),flush=True)
