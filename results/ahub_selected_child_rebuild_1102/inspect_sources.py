#!/usr/bin/env python3
"""Source/geometry reconstruction only; no frontend or physical tools invoked."""
from pathlib import Path
import subprocess,json,hashlib,re,tarfile
R=Path(__file__).resolve().parent
GIT=Path('/home/ubuntu/OpenTallas')
get=lambda c,p:subprocess.check_output(['git','show',c+':'+p],cwd=GIT)
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=[]
for name,commit,base,master in [('recip','922bf01f4','physical/ref_tile/qkh_recip_ref','ot_qkh_recip_leaf'),('zh','e5e8e058b','physical/ref_tile/ot_nhb_zh_m5','ot_nhb_zh')]:
 d=R/name;d.mkdir(exist_ok=True);spec=json.loads(get(commit,base+'/spec.json'));src=d/'recorded_sources';src.mkdir(exist_ok=True);sources=[]
 for p in spec['sources']:
  b=get(commit,p);target=src/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);sources.append({'recorded_path':p,'sha256':sha(b),'bytes':len(b)})
 # Selected view identity is the consumed current published file, not a new rendering.
 viewbase=base+'/views/'+master;lef=get('fb088fd94',viewbase+'/'+master+'.lef');(d/(master+'.lef')).write_bytes(lef)
 pins={};cur=None;layer=None
 for l in lef.decode().splitlines():
  m=re.match(r'\s*PIN\s+(\S+)',l)
  if m:cur=m[1];pins[cur]={'rects':[]}
  if cur:
   m=re.search(r'\bDIRECTION\s+(\w+)',l)
   if m:pins[cur]['direction']=m[1]
   m=re.search(r'\bUSE\s+(\w+)',l)
   if m:pins[cur]['use']=m[1]
   m=re.search(r'\bLAYER\s+(\w+)',l)
   if m:layer=m[1]
   m=re.search(r'\bRECT\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',l)
   if m:pins[cur]['rects'].append({'layer':layer,'rect_um':list(map(float,m.groups()))})
   if re.match(r'\s*END\s+'+re.escape(cur)+r'\s*$',l):cur=None
 size=list(map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef.decode()).groups()));signal={n:p for n,p in pins.items() if p.get('use') not in ('POWER','GROUND')};bad=[]
 for n,p in signal.items():
  for r in p['rects']:
   x,y,xx,yy=r['rect_um']
   if not(0<=x<xx<=size[0] and 0<=y<yy<=size[1]):bad.append((n,r))
 assert not bad
 overlaps=[];flat=[(n,r) for n,p in signal.items() for r in p['rects']]
 for i,(n,r) in enumerate(flat):
  a=r['rect_um']
  for m,s in flat[i+1:]:
   if m==n or s['layer']!=r['layer']:continue
   b=s['rect_um']
   if a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]:overlaps.append([n,m])
 for f in ('spec.json','floorplan.json','kit.env','clock.sdc','signoff.sdc'):(d/f).write_bytes(get(commit,base+'/'+f))
 snapshot=None
 if name=='zh':
  snap=get(commit,base+'/src/SNAPSHOT_COMMIT').decode().strip();snapshot={'base':snap,'snapshots':[]}
  for p in spec['m5rr']['snapshot']:
   b=get(commit,base+'/src/'+p);assert b==get(snap,p);snapshot['snapshots'].append({'path':p,'sha256':sha(b),'exact_base_snapshot':True})
 (d/'selected_pin_shapes.json').write_text(json.dumps({'master':master,'outline_um':size,'signal_pins':signal,'all_signal_rectangles_contained':True,'different_signal_pin_rect_overlaps':overlaps},indent=2)+'\n')
 with tarfile.open(d/'recorded_source_closure.tar.gz','w:gz') as t:t.add(src,arcname='recorded_sources')
 rows.append({'name':name,'master':master,'recorded_commit':commit,'source_files':sources,'source_snapshot':snapshot,'outline_um':size,'signal_bits':len(signal),'signal_rects':len(flat),'signal_rects_contained':True,'different_signal_pin_rect_overlap_count':len(overlaps),'selected_lef_sha256':sha(lef),'parameters':spec.get('params',{}),'native_archive':'NOT_RECOVERED; new native physics is required for a new witness','fresh_rebuild_input_feasibility':'SOURCE_AND_EXACT_PUBLISHED_PIN_GEOMETRY_AVAILABLE','limits':['Recorded source lineage is reconstructed from Git/spec; no original native DB/SPEF/clock graph is recovered.','A fresh build produces new placement/clock graph and MUST publish new LEF+TT/FF+witness together, then explicit new parent case.','Never attach the new graph to old selected libraries or replace them silently.','Legacy ref_tile flow is not a current signable kit; migrate these exact sources/outline/pin rectangles to normal core-kit input and current approved constraint context.','No compact138.24RECIP outline or Q6 full-face ZH pins substituted.','No synthesis/physical/STA/proof job is launched.']})
(R/'FEASIBILITY.json').write_text(json.dumps({'status':'SOURCE_INSPECTION_ONLY','qualified':False,'views':rows,'no_jobs':True},indent=2)+'\n');print([(x['name'],len(x['source_files']),x['outline_um'],x['signal_bits'],x['signal_rects'],x['different_signal_pin_rect_overlap_count']) for x in rows])
