"""C25c: repair common-master VMS-glue and wq0 pin faces from a complete partner census.
No RTL/cycle changes; no per-instance pin variant. Requires c25c_face_diagnose.py output on the SAME plan.
usage: c25c_shared_face_repair.py SRC OUT DIAGNOSIS.json
"""
import hashlib,json,re,sys
from pathlib import Path
from c25c_pins import face,snap,orient
D,O,F=map(Path,sys.argv[1:4]);P=json.load(open(D/'die_plan.json'));A=json.load(open(F));O.mkdir(exist_ok=True,parents=True);(O/'cores').mkdir(exist_ok=True)
assert A['source_sha256']==hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'partner census belongs to a different plan'
mods={'hfd_hgi_vms_glue_nw_t','hnx_vms_bank_q0_faces__vecd4ae'}
choices={(q['module'],q['port']):q['best_shared_face'] for q in A['master_port_constraints'] if q['module'] in mods and q['feasible_non_away']}
report={'cycles_added':0,'shared_master_changes':[],'station_endpoint_changes':[]}
cache={}
for tn,t in P['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c['module'] not in mods:continue
  key=c['pins_file'];w,h=c['outline_um'];old=json.load(open(D/key))
  if key not in cache:
   new=json.loads(json.dumps(old));changed=[]
   for q in new:
    base=re.sub(r'\[\d+\]$','',q['name']);f=choices.get((c['module'],base))
    if f and face(q,w,h)!=f:q['_target_face']=f;changed.append(q['name'])
   if not changed:continue
   for f in 'WENS':
    group=[q for q in new if q.get('_target_face',face(q,w,h))==f]
    # Keep every clock-class coordinate/rectangle exactly fixed.
    fixed=[q for q in group if re.search(r'(^clk|^ck_|_clk$|_ck$)',q['name']) or q.get('h',0)>=.48]
    qs=[q for q in group if q not in fixed];axis='y' if f in 'WE' else 'x';length=h if f in 'WE' else w
    qs.sort(key=lambda q:(q.get('_target_face') is not None,q[axis],q['name']))
    assert (len(qs)-1)*.144<length-10,(c['module'],f,'capacity')
    pos=[]
    for i,q in enumerate(qs):
     v=snap(5+i*(length-10)/max(1,len(qs)-1))
     for shift in (0,.048,-.048,.096,-.096,.144,-.144):
      vv=snap(v+shift)
      if all(abs(vv-z[axis])>=.096-1e-7 for z in fixed) and (not pos or vv-pos[-1]>=.096-1e-7):v=vv;break
     else:raise ValueError((c['module'],f,q['name'],'clock collision'))
     pos.append(v);q.update(layer='M4' if f in 'WE' else 'M5');q[axis]=v;q['x' if f in 'WE' else 'y']=.096 if f in 'WS' else round((w if f=='E' else h)-.096,4)
   for q in new:q.pop('_target_face',None)
   nf='cores/'+Path(key).stem+'__c25c_face.json';(O/nf).write_text(json.dumps(new,indent=1)+'\n');cache[key]=(old,new,nf)
   report['shared_master_changes'].append({'module':c['module'],'source_pins':key,'new_pins':nf,'ports':{port:f for (mod,port),f in choices.items() if mod==c['module']},'pins_changed_face':len(changed),'pins_total':len(new)})
  old,new,nf=cache[key];x,y=c['origin_um'];dx,dy=c.get('track_offset_um',[0,0]);o=c.get('orient','R0')
  pm={}
  for a,b in zip(old,new):
   ax,ay=orient(a['x'],a['y'],w,h,o);bx,by=orient(b['x'],b['y'],w,h,o);pm[(round(x+dx+ax,4),round(y+dy+ay,4))]=[round(x+dx+bx,4),round(y+dy+by,4)]
  n=0
  for st in t.get('internal_stations',[]):
   for endpoint,ref in (('from_um','launch'),('to_um','capture')):
    if st.get(ref,'').startswith(c['inst']) and endpoint in st:
     k=tuple(round(v,4) for v in st[endpoint])
     if k in pm and st[endpoint]!=pm[k]:st[endpoint]=pm[k];n+=1
  report['station_endpoint_changes'].append({'type':tn,'core':c['inst'],'exact_pin_endpoints_updated':n})
  c['pins_file']=nf;c.pop('lef',None);c.pop('lib',None);c['note']=c.get('note','')+' | C25c shared-master face repair from complete partner census (no per-instance variant)'
(O/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n');(O/'c25c_shared_faces_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
