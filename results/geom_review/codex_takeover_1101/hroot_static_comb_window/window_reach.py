from pathlib import Path
import json,sys,re,copy
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');plan=json.load(open('/home/ubuntu/OpenTallas/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json'));sp=schema.Plan(plan);port=next(p for p in plan['ports'] if p['id']=='L1376_0');prefix='u_cland_i_kvpc_Q_N_o_next/';rows=[];actual_pins={int(re.search(r'\[(\d+)\]',p['name'])[1]):p for p in D.pins if p['name'].startswith('i_kvpc_Q_N_o_next[')}
for label,window in [('current',port['window_um']),('left_only_86p4',[1294.2717,1380.6717])]:
 p=copy.deepcopy(port);p['window_um']=window;pins={b:(ln,x) for b,ln,x in schema.pin_positions(p,sp.layers)};details=[]
 for cid,c in D.cells.items():
  if c[0]!='S' or prefix not in c[6]:continue
  n=c[6].replace(chr(92),'');m=re.search(r's_d\[(\d+)\]\[(\d+)\]',n)
  if not m:continue
  slot,bit=int(m[1]),int(m[2]);ln,x=pins[bit];cx,cy=g.ctr(c);dist=abs(cx-x)+abs(cy-actual_pins[bit]['y']) # preserve actual BTerm normal coordinate
  if label=='current':assert abs(x-actual_pins[bit]['x'])<1e-6
  details.append(dict(bit=bit,slot=slot,layer=ln,pin_x=x,capture_xy=[cx,cy],distance_um=round(dist,4)))
 rows.append(dict(option=label,window_um=window,existing_storage_ff=len(details),max_pin_to_slot_um=max(r['distance_um'] for r in details),count_over150=sum(r['distance_um']>150 for r in details),pg_blocked_tracks=sum(schema.pg_blocked(ln,x) for ln,x in pins.values()),scope='Exact current four native slot FF centres vs production PG-safe300-pin tracks; no source-PC/internal/output or forward-clock/START qualification',worst=sorted(details,key=lambda z:-z['distance_um'])[:8]))
(P/'window_reach.json').write_text(json.dumps(rows,indent=1)+'\n');print(rows)
