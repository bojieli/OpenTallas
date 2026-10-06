"""Native OpenDB geometry and routing-grid evidence, no timing/route claim."""
import bisect, collections, hashlib, json, os
from pathlib import Path
import odb
D=odb.dbDatabase.create();odb.read_db(D,os.environ.get('OT_DIAGNOSTIC_ODB','/work/real_leaf_overlay.odb'))
b=D.getChip().getBlock();scale=b.getDbUnitsPerMicron();tracks={}
for layer in D.getTech().getLayers():
 if not layer.getRoutingLevel():continue
 g=b.findTrackGrid(layer)
 if g:tracks[layer.getName()]=dict(X=list(g.getGridX()),Y=list(g.getGridY()),direction=str(layer.getDirection()))
rows=[];counts=collections.Counter();boxes=[]
for i in b.getInsts():
 bb=i.getBBox();boxes.append((bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax(),i.getName()))
 if i.getMaster().getName() not in ('ot_hbm_accel_bd_col','ot_hbm_accel_tc16'):continue
 m=i.getMaster();ori=str(i.getOrient());x,y=bb.xMin(),bb.yMin();w,h=m.getWidth(),m.getHeight();bad=[];pins=0;faces=collections.Counter()
 for t in i.getITerms():
  if t.getSigType() in ('POWER','GROUND'):continue
  pins+=1;ok=False;have=False
  for mp in t.getMTerm().getMPins():
   for r in mp.getGeometry():
    ly=r.getTechLayer()
    if not ly or ly.getName() not in tracks:continue
    have=True;a,c=r.xMin(),r.xMax();e,f=r.yMin(),r.yMax()
    if ori in ('MY','R180'):a,c=w-c,w-a
    if ori in ('MX','R180'):e,f=h-f,h-e
    a,c,e,f=a+x,c+x,e+y,f+y
    grid=tracks[ly.getName()];axis='Y' if grid['direction']=='HORIZONTAL' else 'X';lo,hi=(e,f) if axis=='Y' else (a,c)
    g=grid[axis];j=bisect.bisect_left(g,lo)
    if j<len(g) and g[j]<=hi:ok=True
    ds={'W':a-x,'E':x+w-c,'S':e-y,'N':y+h-f};faces[min(ds,key=ds.get)]+=1
  if not have or not ok:bad.append(t.getMTerm().getName())
 counts[m.getName()]+=1
 rows.append(dict(instance=i.getName(),master=m.getName(),box_DBU=[x,y,x+w,y+h],orientation=ori,signal_pin_count=pins,pins_without_native_track_count=len(bad),pins_without_native_track_examples=bad[:20],pin_face_counts=dict(faces)))
# Sweep native real geometry; opaque parent SM shells have been removed explicitly.
active=[];overlaps=[];outside=[];die=b.getDieArea()
for z in sorted(boxes):
 a,e,c,f,n=z
 if a<die.xMin() or e<die.yMin() or c>die.xMax() or f>die.yMax():outside.append(n)
 active=[q for q in active if q[2]>a]
 for aa,ee,cc,ff,nn in active:
  if ee<f and e<ff:overlaps.append([nn,n])
 active.append(z)
result=dict(scope='NATIVE_PLACEMENT_GRID_DIAGNOSTIC_ONLY',DBU=scale,real_macro_counts=dict(counts),instances=len(boxes),overlap_count=len(overlaps),overlap_examples=overlaps[:30],outside=outside,real_leaf_signal_pins=sum(r['signal_pin_count'] for r in rows),pins_without_native_track=sum(r['pins_without_native_track_count'] for r in rows),routing_grid={k:{axis:(v[axis][:4] if axis in ('X','Y') else v[axis]) for axis in v} for k,v in tracks.items()},real_leaves=rows,wire_RC_included=False,propagated_CTS=False,SSFF_signoff=False,IR_signoff=False,functional_leaf_connectivity=False)
Path(os.environ.get('OT_DIAGNOSTIC_REPORT','/work/native_geometry.json')).write_text(json.dumps(result,indent=1)+'\n');print({k:v for k,v in result.items() if k not in ('real_leaves','routing_grid')})
