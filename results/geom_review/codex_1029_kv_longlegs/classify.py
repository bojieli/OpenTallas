from pathlib import Path
import json,re,collections,importlib.util
sp=importlib.util.spec_from_file_location('geom_rules','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
out=Path(__file__).parent
for part in ['ahub','kvspc']:
 D=g.Design(str(out/(part+'.tsv')));face=collections.defaultdict(list)
 for p in D.pins:
  if p['sig'] in ('POWER','GROUND','CLOCK') or g.CLOCK_PIN_RE.search(p['name']) or p['name'].startswith('strap_'):continue
  ni=D.pin_net.get(p['k'])
  if ni is None:continue
  q=[(ni,0)];seen=set()
  while q:
   n,dep=q.pop()
   if n in seen or dep>4:continue
   seen.add(n)
   refs=([D.nets[n][1]] if p['io']=='OUTPUT' else D.nets[n][2])
   for s in refs:
    if not s or s[0]!='i' or s[2]:continue
    c=s[1]
    if D.kind(c)=='S':face[c].append(p['name'])
    elif D.kind(c)=='B':
     nex=([a[0] for a in D.cell_in[c] if not a[1]] if p['io']=='OUTPUT' else D.drives[c]);q.extend((nn,dep+1) for nn in nex)
 (out/(part+'_face_ff.json')).write_text(json.dumps([dict(id=cid,name=D.cells[cid][6],xy=g.ctr(D.cells[cid]),pins=pins,status=D.extra['status'].get(cid,'PLACED')) for cid,pins in face.items()],indent=2))
 byname={c[6]:cid for cid,c in D.cells.items()};r=json.load(open(out/(part+'_long_legs.json')))
 for a in r:
  for end in ['source','capture']:
   c=byname[a[end]];a[end+'_status']=D.extra['status'].get(c,'PLACED');a[end+'_pins']=face.get(c,[])
 (out/(part+'_long_legs_classified.json')).write_text(json.dumps(r,indent=2))
 print(part,'faceFF',len(face),'violations fixedface source/capture/both',sum(bool(a['source_pins']) for a in r),sum(bool(a['capture_pins']) for a in r),sum(bool(a['source_pins']) and bool(a['capture_pins']) for a in r));print('source_detail',[(nm,len([a for a in r if a['source']==nm]),D.extra['status'].get(byname[nm],'PLACED'),face.get(byname[nm],[]),g.ctr(D.cells[byname[nm]])) for nm in collections.Counter(a['source'] for a in r).keys()][:25]);print('face-to-face',[a for a in r if a['source_pins'] and a['capture_pins']][:5])
 # relaxed geometry lower-bound test: all nonface registers co-located in core centre, no macro/body feasibility claim
 changes={};x=(D.die[0]+D.die[2])/2;y=(D.die[1]+D.die[3])/2
 for cid,c in list(D.cells.items()):
  if c[0]=='S' and cid not in face:
   changes[cid]=c;w=c[4]-c[2];h=c[5]-c[3];D.cells[cid]=(c[0],c[1],x-w/2,y-h/2,x+w/2,y+h/2,c[6])
 print('RELAXED_ALL_INTERNAL_AT_CENTER',g.r2r_metrics(D))
