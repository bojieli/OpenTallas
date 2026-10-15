#!/usr/bin/env python3
"""Check actual OpenROAD BTerm rectangles against requested tracks and PG escape."""
import argparse,collections,csv,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('actual',type=Path);p.add_argument('coordinates',type=Path);p.add_argument('--out',type=Path)
a=p.parse_args();d=json.loads(a.actual.read_text());plan={x['port']:x for x in csv.DictReader(a.coordinates.open(),delimiter='\t')}
pg=[(name,layer,rect)for name,_,typ,_,boxes in d['bterms']if typ in ['POWER','GROUND']for layer,rect in boxes]
shifts=[];overlaps=[];pitch=[];used=collections.defaultdict(list);missing=[]
for name,_,typ,_,boxes in d['bterms']:
 if typ in ['POWER','GROUND']:continue
 if name not in plan or len(boxes)!=1:missing.append(name);continue
 q=plan[name];face=q['face'];layer,rect=boxes[0];c=(rect[0]+rect[2])/2 if face in ['N','S'] else (rect[1]+rect[3])/2
 if abs(c-float(q['center_um']))>.0001:shifts.append([name,float(q['center_um']),c])
 used[face].append([c,name])
 for pn,pl,pr in pg:
  if layer==pl:
   lo,hi=(pr[0],pr[2])if face in ['N','S']else(pr[1],pr[3]);x,y=(rect[0],rect[2])if face in ['N','S']else(rect[1],rect[3])
   if y+.072>lo+1e-6 and x-.072<hi-1e-6:overlaps.append([name,pn,rect,pr])
for face,cs in used.items():
 cs.sort()
 for (x,n),(y,m)in zip(cs,cs[1:]):
  if y-x<.0959:pitch.append([face,n,m,y-x])
r={'scope':'actual signal BTerm PORT rectangles, requested actual ODB routingtrack indices, and both VDD/VSS PG contact projections','actual_sha256':hashlib.sha256(a.actual.read_bytes()).hexdigest(),'coordinates_sha256':hashlib.sha256(a.coordinates.read_bytes()).hexdigest(),'outline_um':d['die'],'scalar_pins':len(plan),'PG_contact_shapes':len(pg),'face_pins':{f:len(v)for f,v in used.items()},'clock_port':next(x for x in d['bterms']if x[0]=='clk'),'shifted_actual_pins':shifts,'PG_clearance_violations':overlaps,'signal_pitch_violations':pitch,'missing_or_multiple_rectangles':missing,'pass':not(shifts or overlaps or pitch or missing)}
if a.out:a.out.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:(len(v)if k in ['shifted_actual_pins','PG_clearance_violations','signal_pitch_violations','missing_or_multiple_rectangles']else v)for k,v in r.items()},indent=2));raise SystemExit(0 if r['pass']else 1)
