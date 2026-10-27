"""Source-qualified current PV clock tap correction; preserves counts and clock period."""
import json,sys,copy
from pathlib import Path
R=Path(__file__).resolve().parent
raw=json.load(open(sys.argv[1]));scope=json.load(open(R/'pv_source_apply.json'));parts={p['name']:p for p in raw['partitions']};seen={};delta=[]
for row in scope['instances']:
 p=parts[row['partition']];assert p['type']==row['type'];t=raw['partition_types'][p['type']];hc=next(h for h in t['hard_cores'] if h['inst']==row['core']);assert hc['orient']==row['orient'] and hc['pins_file']==row['pins_file']
 key=(p['type'],row['core'])
 if key in seen:continue
 pins=json.load(open(Path(sys.argv[1]).parent/hc['pins_file']))['pins'];pins={x['name']:x for x in pins};w,h=hc['outline_um'];ox,oy=hc['origin_um'];dx,dy=hc.get('track_offset_um',[0,0])
 def xy(n):
  q=pins[n];x,y=q['x'],q['y'];o=hc['orient'];x,y={'R0':(x,y),'MX':(x,h-y),'MY':(w-x,y),'R180':(w-x,h-y)}[o];return [round(ox+dx+x,6),round(oy+dy+y,6)]
 name=row['core']+'.'+row['old_primary'];tap=next(v for v in t['clock']['taps'] if v['name']==name);old=xy(row['old_primary']);assert all(abs(a-b)<1e-5 for a,b in zip(old,tap['xy'])),(key,old,tap)
 before=copy.deepcopy(tap);tap['name']=row['core']+'.'+row['new_primary'];tap['xy']=xy(row['new_primary']);tap['note']='Q6 source-qualified R9/R8fMX native CLOCK-MTerm census: S1 live, S0 zero-load alias; same833ps domain, no RTL/cycle change. Receipt7371668398.';seen[key]=True;delta.append(dict(type=key[0],core=key[1],before=before,after=copy.deepcopy(tap)))
assert len(scope['instances'])==256
Path(sys.argv[2]).write_text(json.dumps(raw,indent=1)+'\n');(R/'pv_s1_delta.json').write_text(json.dumps(dict(actual_instances=256,type_core_deltas=len(delta),delta=delta),indent=1)+'\n');print('PV_S1_DONE',len(delta),256)
