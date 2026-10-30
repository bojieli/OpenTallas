"""Fix QC relay START export sharing without adding any count-frame cycle."""
import argparse,json,sys,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--sidecar',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools)
from clock_landings import Landings
import schema
raw=json.load(open(a.plan));side=json.load(open(a.sidecar));L=Landings(raw,side);changes={};cost=collections.Counter();parts=collections.Counter(v['type'] for v in L.parts.values())
for tn,cat in L.ca_type.items():
 if cat['role'][0]!='relay':continue
 ty=raw['partition_types'][tn];ty['landing_relay_start_copy']=True
 exports=list(L.by_type[tn]['outputs']);nt=len(exports)+bool(L.tstart and L.tstart['type_pins'].get(tn,{}).get('cland_tstart_out'))
 changes[tn]=dict(landing_relay_start_copy=True,private_fstart_outputs=exports,new_flops_per_copy=nt,copies=parts[tn],added_data_cycles=0,added_start_cycles=0)
 cost['types']+=1;cost['partitions']+=parts[tn];cost['added_flops_die']+=nt*parts[tn]
N=Landings(raw,side)
for tn in changes:
 spec=N.land_slots(tn)['buses']['cland_rstart_in'];assert spec['form']=='origin_start' and spec['origin']=='u_cland_rstart_rx'
 assert len(spec.get('copies',[]))==changes[tn]['new_flops_per_copy']
err=schema.validate(raw)
if err:raise ValueError(err[:20])
o=Path(a.out);o.mkdir(parents=True,exist_ok=True);json.dump(raw,open(o/'plan_ring.json','w'),indent=1);json.dump(dict(changes=changes,cost=dict(cost),data_cycles=0,start_cycles=0,schema='PASS',scope='Fix-only candidate; needs composite G0C/strict bind and new kits before adoption'),open(o/'ring_delta.json','w'),indent=2)
print(json.dumps(dict(cost=dict(cost),schema='PASS',data_cycles=0,start_cycles=0),indent=1))
