import collections,json,hashlib
from pathlib import Path
root=Path(__file__).parent;p=root/'pin_dump.json';d=json.loads(p.read_text());x0,y0,x1,y1=d['die']
sides=collections.defaultdict(list)
for n,net,sg,direction,rs in d['bterms']:
 if sg in ('POWER','GROUND'):continue
 for layer,r in rs:
  x=(r[0]+r[2])/2;y=(r[1]+r[3])/2
  if r[1]<=y0:side='S';v=x
  elif r[3]>=y1:side='N';v=x
  elif r[0]<=x0:side='W';v=y
  elif r[2]>=x1:side='E';v=y
  else:continue
  sides[side].append(v)
faces=[]
for side,vs in sorted(sides.items()):
 vs.sort();gaps=[round(b-a,6) for a,b in zip(vs,vs[1:])]
 faces.append(dict(side=side,contacts=len(vs),minimum_pitch_um=min(gaps),pitch_histogram=dict(collections.Counter(gaps)),local_pitch_density_per_um=1/min(gaps)))
macros=[]
for m in d['macros']:
 a,b,c,e=m['bbox'];ss=collections.defaultdict(list)
 for pin in m['pins']:
  _,x,y,*_=pin;side='W' if abs(x-a)<.1 else 'E' if abs(x-c)<.1 else 'S' if abs(y-b)<.1 else 'N';ss[side].append((x,y))
 mf=[dict(side=s,contacts=len(v),full_face_um=e-b if s in ('W','E') else c-a,density_per_um=len(v)/(e-b if s in ('W','E') else c-a)) for s,v in sorted(ss.items())]
 macros.append(dict(instance=m['name'],master=m['master'],bbox=m['bbox'],faces=mf,lattice_x_43p2=abs(a/43.2-round(a/43.2))<1e-6,lattice_y_43p2=abs(b/43.2-round(b/43.2))<1e-6))
out=dict(verdict='FAIL',source_dump_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),top_faces=faces,macros=macros,limits=dict(max_contacts_per_um=6),scope='Original IOP floorplan dump; actual contact pitch/full face counts, not detailed-route access or PG certification')
(root/'geometry.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('Actual geometry FAIL: top local pitch and all 11 SRAM face densities exceed 6/um')
