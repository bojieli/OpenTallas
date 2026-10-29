#!/usr/bin/env python3
"""Apply a reviewed unsigned calendar proposal to an OWN plan-event staging tree.
No source RTL, latency count, parent relay or clock-tree construction is changed.
"""
import argparse, copy, json
from pathlib import Path
MOD='hfd_hgi_vm_calendar_f20';NEW=[216.,112.32]
def dump(p,d):p.write_text(json.dumps(d,indent=1)+'\n')
def apply(dst,proposal):
 dst=Path(dst);proposal=Path(proposal)
 plan=json.load(open(dst/'die_plan.json'));pnew=json.load(open(proposal/'pins.json'))
 hit=[];old_files=set()
 for tn,t in plan['partition_types'].items():
  for c in t.get('hard_cores',[]):
   if c['module']!=MOD:continue
   assert all(abs(a-b)<1e-6 for a,b in zip(c['outline_um'],[241.92,116.64])),(tn,c['inst'])
   old_files.add(c['pins_file']);hit.append((tn,c['inst']))
 assert len(hit)==4 and len(old_files)==1
 old_file=next(iter(old_files));pold=json.load(open(dst/old_file))
 assert [x['name'] for x in pold]==[x['name'] for x in pnew]
 target='cores/hfd_hgi_vm_calendar_f20__216x112.32__canon.json'
 # Never follow an old symlink to mutate the source snapshot.
 p=dst/target
 assert not p.exists()
 dump(p,pnew)
 for tn,t in plan['partition_types'].items():
  for c in t.get('hard_cores',[]):
   if c['module']!=MOD:continue
   c['outline_um']=NEW;c['pins_file']=target
   for stale in ['lef','lib']:c.pop(stale,None)
   c['status']='PENDING-VIEW';c['note']=c.get('note','')+' | VM_CAL compact unsigned proposal: no old view reuse; FT/taps/CA/PG require event recomposition'
  for c in t.get('contents',[]):
   if c.get('module')==MOD:c['outline_um']=NEW
 cm=json.load(open(dst/'core_macros.json'));cm['cores'][MOD]['outline_um']=NEW
 cm['cores'][MOD]['status']='PLAN-TRIAL';cm['cores'][MOD]['basis']='Compact proposal, same current one SRAM, no view/STA closure claim'
 # Alias clock island metadata follows the slice; actual per-instance taps are
 # left pending parent clock construction, never treated as a routed clock.
 ce=json.load(open(dst/'clock_entries.json'))
 for entries in ce.values():
  for name,c in entries.items():
   if name!='u_calendar_Q':continue
   c['xy_um'][1]=round(c['xy_um'][1]+4.32,6)
   c['island_um']=[round(v+(4.32 if i%2 else 0),6) for i,v in enumerate(c['island_um'])]
   c['source']=c.get('source','')+' | compact native entry north4.32; parent regional tap regeneration PENDING'
 for name,d in [('die_plan.json',plan),('core_macros.json',cm),('clock_entries.json',ce)]:
  p=dst/name
  if p.is_symlink():p.unlink()
  dump(p,d)
 return dict(status='PENDING_PARENT_FT_CLOCK_CA_PG',changed=hit,pins=558,cycles_added=0,old_pin_file=old_file,new_pin_file=target,removed_stale_views=True)
def main():
 a=argparse.ArgumentParser();a.add_argument('own_plan_stage',type=Path);a.add_argument('proposal',type=Path);x=a.parse_args();print(json.dumps(apply(x.own_plan_stage,x.proposal)))
if __name__=='__main__':main()
