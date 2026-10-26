#!/usr/bin/env python3
"""Fold exact MP1 named geometry into actual bound cohorts and recompose landings.

Uses actual part identity plus the declared landing/split base-type chain.
Functional interfaces, station counts and indexed site ordering are preserved;
forward/status pins and ring/collector coordinates are recomputed together.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import clock_landing_plan as C
p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('geometry');p.add_argument('landing');p.add_argument('--out',required=True);p.add_argument('--landing-out',required=True);p.add_argument('--report',required=True);a=p.parse_args()
raw=json.load(open(a.plan));geo=json.load(open(a.geometry));land=json.load(open(a.landing));before=copy.deepcopy(raw)
gparts={p['name']:p for p in geo['partitions']};parts={p['name']:p for p in raw['partitions']};assert set(parts)==set(gparts)
slotkeys=['regs_um','bit_sites_um','bit_site_cell_um','in_window_um','out_window_um'];buskeys=['window_um','face','leaf_um'];type_rows=[]
for tn,t in raw['partition_types'].items():
 names=[pn for pn,p in parts.items() if p['type']==tn];assert names
 bases={gparts[pn]['type'] for pn in names};assert len(bases)==1,(tn,bases);base=next(iter(bases));chain=[tn];cur=tn
 while cur in raw['partition_types']:
  nxt=raw['partition_types'][cur].get('landing_base_type') or raw['partition_types'][cur].get('split_of')
  if not nxt or nxt in chain:break
  chain.append(nxt);cur=nxt
 if base not in chain:raise ValueError(f'{tn}: actual part base {base} absent from declared lineage {chain}')
 gt=geo['partition_types'][base];assert t['outline_um']==gt['outline_um'],tn
 for pn in names:assert parts[pn]['origin_um']==gparts[pn]['origin_um'] and parts[pn].get('orient','R0')==gparts[pn].get('orient','R0'),pn
 hc={x['inst']:x for x in t.get('hard_cores',[])};gh={x['inst']:x for x in gt.get('hard_cores',[])};assert set(hc)==set(gh),tn
 for name in hc:
  for k in ['module','origin_um','outline_um','orient']:assert hc[name].get(k)==gh[name].get(k),(tn,name,k)
 ss={s['name']:s for s in gt.get('ft_slots',[])};changed=0
 assert {s['name'] for s in t.get('ft_slots',[])}==set(ss),tn
 for s in t.get('ft_slots',[]):
  gs=ss[s['name']];assert s['width']==gs['width'] and s['stations']==gs['stations'],(tn,s['name'])
  changed+=any(s.get(k)!=gs.get(k) for k in slotkeys)
  for k in slotkeys:
   if k in gs:s[k]=copy.deepcopy(gs[k])
   else:s.pop(k,None)
 gb={b['name']:b for b in gt.get('buses',[])}
 for b in t.get('buses',[]):
  if b['name'] not in gb:continue
  src=gb[b['name']];assert b.get('width')==src.get('width') and b.get('dir')==src.get('dir'),(tn,b['name'])
  for k in buskeys:
   if k in src:b[k]=copy.deepcopy(src[k])
 # Old forwarded clock/status objects must not survive beside new coordinates.
 clock=t.setdefault('clock',{});clock.pop('landing_contract',None);clock['edge_clocks']=[e for e in clock.get('edge_clocks',[]) if not e['port'].startswith('fclk_')]
 t.pop('_cland_geom',None)
 type_rows.append(dict(type=tn,actual_base=base,lineage=chain,changed_slots=changed,parts=names))
gports={p['id']:p for p in geo['ports']};windows=[]
for pr in raw['ports']:
 if pr['id'] not in gports:continue
 gp=gports[pr['id']]
 for k in ['src','dst','width','kind','layers','face']:assert pr.get(k)==gp.get(k),(pr['id'],k)
 for k in ['window_um']:
  if k in gp:
   if pr.get(k)!=gp[k]:windows.append(dict(port=pr['id'],kind=pr.get('kind'),previous=pr.get(k),current=gp[k]))
   pr[k]=copy.deepcopy(gp[k])
raw['clock'].pop('landing_network',None)
obs=land['collector']['observer'];spec={k:obs[k] for k in ['module','instance_suffix','fault_port','ready_port']}
combined,table=C.compose(raw,land,Path(a.out),observer_part=obs['part'],observer=spec)
from kv_land_refresh import refresh
collector_refresh=refresh(table)
for tn,t in combined['partition_types'].items():
 if 'landing_contract' in t.get('clock',{}):t['clock']['landing_contract']['collector_local_sources']=copy.deepcopy(table['collector']['types'][tn]['local_sources'])
# Recomposition may refine metadata cohorts; indexed geometry must stay exact.
for pp in combined['partitions']:
 tt=combined['partition_types'][pp['type']];gt=geo['partition_types'][gparts[pp['name']]['type']];gs={s['name']:s for s in gt.get('ft_slots',[])}
 for s in tt.get('ft_slots',[]):
  src=gs[s['name']];assert s['width']==src['width'] and s['stations']==src['stations']
  for k in slotkeys:assert s.get(k)==src.get(k),(pp['name'],s['name'],k)
oldparts={p['name']:p for p in before['partitions']};changed_contract=[]
for pp in combined['partitions']:
 old=before['partition_types'][oldparts[pp['name']]['type']].get('clock',{}).get('landing_contract')
 new=combined['partition_types'][pp['type']].get('clock',{}).get('landing_contract')
 if old!=new:changed_contract.append(pp['name'])
report=dict(kind='ONE_KV_EVENT_CANDIDATE',types=type_rows,changed_port_windows=windows,changed_landing_contract_parts=changed_contract,
 previous_boot_budget=land['collector'].get('boot_budget'),current_boot_budget=table['collector']['boot_budget'],FT_station_delta=0,FT_cycle_delta=0,
 collector_retarget=collector_refresh,physical_qualified=False,placement_failures=table['collector']['placement_failures'],native_landing_ff_expected=63794)
for path,d in [(a.out,combined),(a.landing_out,table),(a.report,report)]:
 with open(path,'w') as f:json.dump(d,f,indent=1);f.write('\n')
print(json.dumps(dict(types_before=len(before['partition_types']),types_after=len(combined['partition_types']),changed_port_windows=len(windows),changed_landing_contract_parts=len(changed_contract),placement_failures=len(report['placement_failures']),old_boot=report['previous_boot_budget']['ready_at_glue_max_cycles'],new_boot=report['current_boot_budget']['ready_at_glue_max_cycles'],FT_cycles_added=0)))
