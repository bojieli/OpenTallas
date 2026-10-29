"""Compose unsigned current VM calendar geometry d93518bfa in one die event.
All4 replicas share one pin/outline/slice. Endpoint proxy rows are rescaled to
the same face of the new core, and reported as requiring actual-source rebind.
Never retain a stale LEF/lib or call proxy rows an exact routed-bit proof.
"""
import copy,hashlib,json,shutil,sys
from pathlib import Path
SRC,PKT,OUT=map(Path,sys.argv[1:4]);P=json.loads((SRC/'die_plan.json').read_text());cm=json.load(open(SRC/'core_macros.json'));entries=json.load(open(SRC/'entries.json'));MOD='hfd_hgi_vm_calendar_f20';OLD=[241.92,116.64];NEW=[216.,112.32]
pins=json.load(open(PKT/'pins.json'));sl=json.load(open(PKT/'master_slice.json'));cl=next(p for p in pins if p['name']=='clk');newclk=[cl['x'],cl['y']];rep={'schema':'hbm-calendar-compose.v1','source_plan':hashlib.sha256((SRC/'die_plan.json').read_bytes()).hexdigest(),'packet_commit':'d93518bfa261d23e6bc97d537a0e27f410151b06','replicas':[],'source_cycles_added':0,'requires':['fresh actual-source station mapping','clock tree and reset/START/CA recomposition','G2 pin access and actual placement review']}
def fwd(pt,c,wh):
 x,y=pt;w,h=wh;o=c.get('orient','R0')
 if o in ['MY','R180']:x=w-x
 if o in ['MX','R180']:y=h-y
 return [round(c['origin_um'][0]+x,6),round(c['origin_um'][1]+y,6)]
def local(pt,c):
 x,y=pt[0]-c['origin_um'][0],pt[1]-c['origin_um'][1];o=c.get('orient','R0')
 if o in ['MY','R180']:x=OLD[0]-x
 if o in ['MX','R180']:y=OLD[1]-y
 return x,y
for tn,t in P['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c['module']!=MOD:continue
  assert all(abs(a-b)<1e-6 for a,b in zip(c['outline_um'],OLD));inst=c['inst'];o=copy.deepcopy(c);c['outline_um']=NEW[:];c['pins_file']='cores/hfd_hgi_vm_calendar_f20__216x112.32__c25c.json';stale={k:c.pop(k) for k in ['lef','lib'] if k in c}
  changed=[]
  for row in t.get('internal_stations',[]):
   for fld,role in [('from_um','launch'),('to_um','capture')]:
    a=row[fld];lx,ly=local(a,o)
    # Exact existing endpoint lies in this replica. Original labels omit qN.
    if not(-.5<=lx<=OLD[0]+.5 and -.5<=ly<=OLD[1]+.5):continue
    if 'calendar_Q' not in row.get(role,'') and 'calendar_Q' not in row['conn']:continue
    q=[round(lx*NEW[0]/OLD[0],6),round(ly*NEW[1]/OLD[1],6)];b=fwd(q,c,NEW);row[fld]=b;changed.append({'conn':row['conn'],'endpoint':fld,'old':a,'new':b,'kind':'geometric-face-proxy; actual-source rebind required'})
  for v in t.get('contents',[]):
   if v.get('inst')==inst:
    v['outline_um']=NEW[:]
    for key in ['lef','lib']:v.pop(key,None)
  for tap in t.get('clock',{}).get('taps',[]):
   if tap['name'].split('.')[0]==inst:tap['xy']=fwd(newclk,c,NEW)
  rep['replicas'].append({'type':tn,'inst':inst,'origin_um':c['origin_um'],'orient':c.get('orient','R0'),'old_view_dropped':stale,'clock_global_um':fwd(newclk,c,NEW),'station_endpoints':changed})
assert len(rep['replicas'])==4
cm['cores'][MOD]['outline_um']=NEW;cm['cores'][MOD]['status']='PENDING-VIEW';cm['cores'][MOD]['basis']='unsigned compact source-identical geometry d93518bfa; fresh actual placement required'
entries[MOD]={'source':'d93518bfa compact calendar actual main clk pin/island; refresh current tree before route','xy':newclk}
clock_entries=json.load(open(SRC/'clock_entries.json'))
for tn,vals in clock_entries.items():
 for name,c in vals.items():
  if c.get('module')!=MOD:continue
  c['xy_um']=newclk[:]
  if 'island_um' in c:c['island_um']=[round(v+(4.32 if i%2 else 0),6)for i,v in enumerate(c['island_um'])]
  c['source']='d93518bfa compact current calendar: two islands north4.32; reprice actual clock'
shutil.copytree(SRC,OUT);(OUT/'clock_entries.json').write_text(json.dumps(clock_entries,indent=1)+'\n');(OUT/'cores/hfd_hgi_vm_calendar_f20__216x112.32__c25c.json').write_text(json.dumps(pins,indent=1)+'\n');(OUT/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n');(OUT/'core_macros.json').write_text(json.dumps(cm,indent=1)+'\n');(OUT/'entries.json').write_text(json.dumps(entries,indent=1)+'\n');(OUT/'calendar_master_slice.json').write_text(json.dumps(sl,indent=1)+'\n');rep['plan_sha256']=hashlib.sha256((OUT/'die_plan.json').read_bytes()).hexdigest();(OUT/'calendar_composition.json').write_text(json.dumps(rep,indent=1)+'\n');print('CALENDAR composed',len(rep['replicas']),'replicas',sum(len(r['station_endpoints'])for r in rep['replicas']),'proxy endpoints; no route approval',rep['plan_sha256'])
