"""QC START perimeter candidate; provisional clock stubs, no loaded phase claim."""
import json,sys,math
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251');O=R/'perimeter1';O.mkdir(exist_ok=True)
OLD=Path('/srv/opentallas-scratch2/claude/codex-qc-start-provider-1029')
Q=Path('/srv/opentallas-scratch2/claude/codex-qc-1029')
sys.path.insert(0,str(R/'src407/tools/die_plan'))
import count_align_plan as P,count_align_bind as B,die_sta_related as D
cached=json.load(open(R/'plan.json'));gg=json.load(open(R/'perimeter_geometry.json'))
rows=[]
for c in cached['crossings']:
 r={k:c[k] for k in ['port','src','dst','src_part','dst_part','d_ps','p_dn_ps','p_up_ps']}
 # The previous cached-hull pass already conservatively expanded rounded wander.
 # Expand a second 0.05ps to avoid a second rounding narrowing.
 r.update(unshared_sta_ps=(c['wander_ps']+.0500001)/.05,_named=True,margin_ps=c['old_ring_margin_ps']);rows.append(r)
ctx=P.clock_contexts(OLD/'actual26/proof',Q/'physical_event/plan_start_native_h800.json',['TT','FF'],'spice_edge','table','shared',OLD/'actual26/proof/droop_regions.json',202.5,'inv')
nom=ctx['TT'];D.CPPR_LCA=True
for corner,c in ctx.items():
 for region,v in gg.items():
  key=D.virtual_tap(c['meta'],c['taps'],region[3:],D.tap_leg(c['meta'],c['taps']),D.tap_leg_fall(c['meta'],c['taps']))
  c['taps'][key]['xy_um']=v['anchor_xy_um']
def tap(region,old=None):return '__st__'+region[3:] if region.startswith('st:') else old

def pair(a,b,ak,bk):
 ivs=[];fvs=[]
 for c in ctx.values():
  for k in [ak,bk]:
   if k.startswith('__st__') and k not in c['taps']:
    D.virtual_tap(c['meta'],c['taps'],k[6:],D.tap_leg(c['meta'],c['taps']),D.tap_leg_fall(c['meta'],c['taps']))
  t=c['taps'];ivs.append(D.ca_pair_interval(t[ak],t[bk],ak,bk,c['rng'],c['ocv']))
  fvs.append(D.ca_pair_interval(t[ak],t[bk],ak,bk,c['rng'],c['ocv'],'fall'))
 lo=min(x[0] for x in ivs);hi=max(x[1] for x in ivs);flo=min(x[0] for x in fvs);fhi=max(x[1] for x in fvs)
 A=nom['taps'][ak];BB=nom['taps'][bk]
 dn=.5*(BB['late_ps']+BB['early_ps']-A['late_ps']-A['early_ps']);dn=min(max(dn,lo),hi)
 axy=A.get('xy_um',nom['meta']['node_xy_um'].get(A['tree_path']));bxy=BB.get('xy_um',nom['meta']['node_xy_um'].get(BB['tree_path']))
 hop=sum(abs(x-y) for x,y in zip(axy,bxy))
 q=dict(port=f'start:{a}->{b}',src=a,dst=b,launch=ak,capture=bk,launch_part=None,capture_part=BB.get('part'),retime=b.startswith('st:'),hop_um=hop,d_ps=dn,p_dn_ps=dn-lo,p_up_ps=hi-dn,fall_lo=flo,fall_hi=fhi,unshared_a_ps=0,unshared_b_ps=0,scope='PROVISIONAL: new clock stub; actual loaded stage clock required')
 ck=dict(q,lo=lo,hi=hi);choice=P.sync_choice_iv(ck,833,833/8)
 q['clean_ok']=choice[0]==1 and P.width_robust(ck,833,833/8,0) and hop<=400
 return q
new=[];replaced=0
for e in cached['start_edges']:
 if e['clean_ok']:new.append(dict(e));continue
 aliases=sorted((r for r,v in gg.items() if v['replaced_port']==e['port']),key=lambda r:0 if '@qcperimeter0_' in r else 1)
 assert len(aliases)==2
 chain=[e['src'],*aliases,e['dst']]
 for a,b in zip(chain,chain[1:]):new.append(pair(a,b,tap(a,e['launch']),tap(b,e['capture'])))
 replaced+=1
summ,cross,regs=P.plan(rows,start_root=cached['summary']['tree_root'],start_edges=new)
summ.update(period_ps=833,aperture_ps=833/8,sync_aperture_ps=26.5,scope='PROVISIONAL perimeter geometry: clocks source actual nets, new stub arrivals NOT measured',replaced_native_edges=replaced,extra_stages=len(gg),cached_hull_source=str(R/'plan.json'))
doc=dict(summary=summ,crossings=cross,regions=regs,start_edges=new)
(O/'plan.json').write_text(json.dumps(doc));(O/'stage_placement_overrides.json').write_text(json.dumps(gg));print('SUMMARY',json.dumps(summ),flush=True)
if summ['fail'] or summ['start_tree']['start_fail']:raise SystemExit('perimeter provisional planning FAIL; artifacts retained')
b=B.bind(doc,parts=B.ocv_parts(rows));(O/'bind.json').write_text(json.dumps(b));print('BIND',len(b['start_ports']),len(b['regions']),max(r['origin_cycles'] for r in regs),flush=True)
