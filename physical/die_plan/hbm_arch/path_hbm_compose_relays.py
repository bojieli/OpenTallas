#!/usr/bin/env python3
"""Compose reviewed relay/core-origin proposals without replacing other plan fields.

Type interfaces are immutable here. Internal stations/reset are regenerated after
moving cores; clock taps and infra-first routing still need the clock owner.
"""
import argparse,copy,importlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools/die_plan'),str(HERE)]
import schema as S


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',required=True,type=Path);ap.add_argument('--overlay',action='append',required=True,help='JSON:type1,type2');ap.add_argument('--out',required=True,type=Path);ap.add_argument('--helper',type=Path);ap.add_argument('--retain-aux',action='store_true');a=ap.parse_args()
 if a.out.exists():raise SystemExit('output must be new')
 p=json.loads((a.base/'die_plan.json').read_text());before=S.Plan(copy.deepcopy(p));sources={};moved=[]
 for value in a.overlay:
  name,types=value.rsplit(':',1);other=json.loads(Path(name).read_text())
  for tn in types.split(','):
   old=p['partition_types'][tn];new=other['partition_types'][tn]
   if tn in sources:raise ValueError('duplicate overlay '+tn)
   assert old['outline_um']==new['outline_um'],tn+' outline changed'
   assert old['buses']==new['buses'],tn+' bus interface changed'
   acores={c['inst']:c for c in old['hard_cores']};bcores={c['inst']:c for c in new['hard_cores']};assert acores.keys()==bcores.keys()
   for inst,core in acores.items():
    proposed=bcores[inst]
    assert {k:v for k,v in core.items() if k!='origin_um'}=={k:v for k,v in proposed.items() if k!='origin_um'},tn+'/'+inst+' core interface changed'
    if core['origin_um']!=proposed['origin_um']:moved.append(tn+'/'+inst)
    core['origin_um']=proposed['origin_um']
   slots={s['name']:s for s in old['ft_slots']};target={s['name']:s for s in new['ft_slots']};assert slots.keys()==target.keys()
   geometry={'stations','regs_um','bit_sites_um','bit_site_cell_um'}
   for sn,slot in slots.items():
    replacement=target[sn]
    assert {k:v for k,v in slot.items() if k not in geometry}=={k:v for k,v in replacement.items() if k not in geometry},tn+'/'+sn+' FT interface changed'
    for k in geometry:
     if k in replacement:slot[k]=replacement[k]
     else:slot.pop(k,None)
   sources[tn]=name
 if a.retain_aux and moved:raise ValueError('core moves require auxiliary regeneration: '+str(moved))
 shutil.copytree(a.base,a.out)
 log=[];unroutable=[]
 if a.retain_aux:log.append('Retained existing auxiliary geometry: bus/core contracts and every core origin unchanged; FT site/depth overlay only')
 else:
  if not a.helper:raise ValueError('--helper is required when regenerating auxiliary geometry')
  sys.path.insert(0,str(a.helper.resolve()));B=importlib.import_module('b2o');BN=importlib.import_module('b2n')
  unroutable=B.internal_stations(p,a.out,list(sources),log)
  BN.reset_wavefront(p,log)
 after=S.Plan(p);p['latency']['lanes']={lid:after.lane_latency(lid) for lid in after.lanes}
 delta={lid:after.lane_latency(lid)['cycles']-before.lane_latency(lid)['cycles'] for lid in after.lanes if after.lane_latency(lid)['cycles']!=before.lane_latency(lid)['cycles']}
 (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
 report=dict(scope='geometry candidate, clock/PG/GRT pending',sources=sources,internal_unroutable=unroutable,lane_cycle_delta=delta,log=log)
 (a.out/'relay_composition_report.json').write_text(json.dumps(report,indent=1,default=str)+'\n');print(json.dumps(report,default=str),flush=True)
 return int(bool(unroutable))
if __name__=='__main__':raise SystemExit(main())
