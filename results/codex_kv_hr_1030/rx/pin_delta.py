#!/usr/bin/env python3
"""Create the approved RX259 pin-only candidate without changing canonical inputs."""
import argparse, copy, hashlib, json
from pathlib import Path

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def emit(obj,p): Path(p).write_text(json.dumps(obj,indent=1)+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--plan',type=Path,required=True);a.add_argument('--pins',type=Path,required=True);a.add_argument('--out',type=Path,required=True);ns=a.parse_args()
 ns.out.mkdir(parents=True,exist_ok=True)
 p=json.loads(ns.plan.read_text()); old=json.loads(ns.pins.read_text());new=copy.deepcopy(old)
 assert digest(ns.pins).startswith('b3c83a23fcbe'), 'wrong frozen source pin table'
 pins={x['name']:x for x in new['pins']};changes=[]
 target={'ownership_valid[0]':129.384,'rx_d[263]':254.424,'die_id[0]':128.760,'die_id[2]':130.488}
 for name,y in target.items():
  q=pins[name]; assert q['layer']=='M4';before=copy.deepcopy(q);q['y']=y;changes.append({'pin':name,'before':before,'after':copy.deepcopy(q),'manhattan_delta_um':round(abs(y-before['y']),3)})
 positions={}
 for q in new['pins']:
  pos=(q['layer'],q['x'],q['y']);assert pos not in positions,(q['name'],positions.get(pos));positions[pos]=q['name']
 # Source name/layer/x/other records are preserved; only these four y values change.
 assert [x for x,y in zip(old['pins'],new['pins']) if x!=y]==[x for x in old['pins'] if x['name'] in target]
 outfile=ns.out/'qkd_hr_core_rx_pins_r26q5_rx259sw.json';emit(new,outfile)
 np=copy.deepcopy(p);affected=[]
 for tn,t in np['partition_types'].items():
  for c in t.get('hard_cores',[]):
   if c.get('module')=='qkd_hr_core_rx':
    assert c['outline_um']==[259.2,259.2] and c['orient']=='R0'
    before=copy.deepcopy(c);c['pins_file']=str(outfile.resolve())
    affected.append({'type':tn,'inst':c['inst'],'origin_um':c['origin_um'],'outline_um':c['outline_um'],'orient':c['orient'],'changes':[dict(x,parent_before_um=[round(c['origin_um'][0]+x['before']['x'],3),round(c['origin_um'][1]+x['before']['y'],3)],parent_after_um=[round(c['origin_um'][0]+x['after']['x'],3),round(c['origin_um'][1]+x['after']['y'],3)]) for x in changes]})
    c['pins_file']=before['pins_file']
 assert np==p,'unintended neighbor or plan change';assert len(affected)==1
 report={'schema':'opentallas.kv.rx259_pin_delta.v1','base_plan_sha256':digest(ns.plan),'base_pin_sha256':digest(ns.pins),'candidate_pin_sha256':digest(outfile),'changed_pin_count':4,'cycles_added':0,'rtl_changed':False,'outline_changed':False,'clock_reset_pins_changed':False,'affected_cores':affected,'neighbor_entries_changed':0,'partition_bus_and_pin_records_changed':0,'parent_route_impact':'four internal hard-core signal endpoints move (includes rx_d[263], not only controls); source/destination identities unchanged. Parent wires must reroute; zero latency claim needs parent reach/STA recheck. Neighbor hard-core and partition pin coordinates are unchanged by this candidate.','gates':'candidate only: die owner runs G0C + exact-abutment clock and parent reach/STA before adoption'}
 emit(report,ns.out/'impact.json');print(json.dumps({k:report[k] for k in ['candidate_pin_sha256','changed_pin_count','neighbor_entries_changed']}))
if __name__=='__main__':main()
