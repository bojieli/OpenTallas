#!/usr/bin/env python3
"""Held source proposal: close the measured F0/F1 lower cut of the UCIe repack.

The four-type full G0C failed108vs96: F1S inherited unshifted F0N pins,
replicated F1/F2 pin tables differed, and START provider boundary copies were
stale. Move the complete existing F0 N bank+25.92um (no footprint/type/data
stage addition), then refresh literal START boundary endpoints and refuse any
new405um envelope violation. Paired collector/reset rederive is required AFTER
this stage and must use the exact complete fleet GEN/bind factory.
"""
import argparse,copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/die_plan'))
import schema as S
import start_provider_plan as SP
from propose_coll_ucie_north_align_1101 import move_bus_landing

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('held',type=Path);ap.add_argument('out',type=Path);ap.add_argument('--proposal-only',action='store_true',required=True);a=ap.parse_args()
 raw=json.load(open(a.held/'PROPOSAL_NOT_RELEASED.json'));side=json.load(open(a.held/'sidecar.json'));report=json.load(open(a.held/'proposal.json'))
 tn='coll_ft__cl78c7b300';t=raw['partition_types'][tn];changes=[]
 assert [p['name']for p in raw['partitions']if p['type']==tn]==['coll_f0']
 for sl in t['ft_slots']:
  for stem in ['in','out']:
   if sl[stem+'_face']!='N':continue
   bus=sl['name']+('_i'if stem=='in'else '_o');key=stem+'_window_um';old=copy.deepcopy(sl.get(key))
   if old is not None:sl[key]=[round(x+25.92,6)for x in old]
   move_bus_landing(raw,side,tn,bus,25.92,stem)
   changes.append(dict(bus=bus,before=old,after=sl.get(key),landing_translation_um=25.92))
 errors=S.validate(raw)
 if errors:raise ValueError(errors)
 P=S.Plan(raw);provider=raw['clock']['landing_network']['start_tree']['provider'];boundary=[]
 for e in provider['edges']:
  if 'part'not in e:continue
  key='dst_rect_um'if e['pin']=='cland_tstart_in'else 'src_rect_um';old=e[key];new=SP.pin_rect(P,e['part'],e['pin'])
  if old!=new:
   e[key]=new;boundary.append(dict(part=e['part'],pin=e['pin'],before=old,after=new))
 start=SP.check(P,provider)
 report.update(verdict='STAGED_REQUIRES_EXACT_FACTORY_REDERIVE',modified_types=[*report['modified_types'],tn],south_window_remap=changes,start_provider_boundary_remap=boundary,start_provider_check=start,required_scope_extension='existing F0 N face +25.92um; no new footprint/type/stage; all collector/reset trees require exact complete fleet rederive')
 if start['errors']:report['verdict']='REJECT_START_PROVIDER'
 a.out.mkdir(parents=True,exist_ok=True)
 for n,x,ind in [('PROPOSAL_NOT_RELEASED.json',raw,None),('sidecar.json',side,1),('proposal.json',report,1)]:
  (a.out/n).write_text(json.dumps(x,indent=ind)+'\n')
 print(json.dumps(dict(verdict=report['verdict'],south_bank_interfaces=len(changes),start_boundary_changes=boundary,start_provider_check=start),indent=1))
 return bool(start['errors'])
if __name__=='__main__':sys.exit(main())
